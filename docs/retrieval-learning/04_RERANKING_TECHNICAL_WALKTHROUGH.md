# 04 — Cross-Encoder reranking: từ Hybrid candidates đến final evidence

## Phạm vi và cách đọc

Đây là chương tiếp theo của Hybrid RRF (historical/local reference; not included in this Task 8 publication), đối chiếu source ngày16/11/2026 trong `tillegal-ai-main/`. Đã đọc lại README và các chương01/02/03 trước khi viết. Giữ cách giải thích mục đích → cơ chế → dữ liệu → implementation → downstream; phụ lục có source ranges và code thật. Không dùng `ai_core/` làm implementation.

Phần mới là pair scoring, selection và orchestration post-Hybrid; BM25, Dense, RRF, chunks/source readers và Supabase infrastructure được tái sử dụng. Không nhận việc train model, crawler, passage indexing hay pgvector là implementation reranker. Ví dụ model-score live dưới đây đã chạy thật, còn ví dụ phép sắp xếp ghi ILLUSTRATIVE. Technical success không đồng nghĩa relevance hoặc hiệu lực pháp luật đã được chứng minh.

Các chương trước mô tả snapshot trước Task8: Hybrid kết thúc sau RRF và không có CE. Hiện điều đó vẫn đúng khi disabled; khi enabled có thêm stage mới. Line numbers service/bootstrap/CLI trong chương cũ là lịch sử, đã dịch chuyển do thêm code; không âm thầm sửa ba chương đó. Các ghi chú “chưa live” trong phiên viết cũ không phủ nhận technical E2E đã ghi ở engineering addendum hoặc Task8.

## A — Reranking nhận gì, và tại sao cần thêm bước này?

BM25 chấm term match; Dense so vector E5; RRF cộng các reciprocal ranks. RRF không đọc đồng thời query và content bằng model. Cross-Encoder nhận **cặp (query, chunk)** và cho một scalar relevance score. Vì query và passage đi chung một chuỗi, attention có thể trao đổi tín hiệu giữa hai phần trước khi classification head chấm điểm.

Không chạy model trên toàn corpus: chi phí forward tăng theo số pairs và sequence length. Retrieval tạo pool nhỏ trước, rồi CE chọn lại những candidates có sẵn. Candidate không có trong pool thì reranker không thể phục hồi. Tăng pool cải thiện cơ hội chứa evidence nhưng tăng CPU latency; chưa có labels để kết luận pool20 là tối ưu.

Request vẫn `RetrievalRequest(query,mode,top_k,as_of_date,allowed_usage_policies)`. Top-K là số evidence user muốn nhận; config.candidate_pool là số fused candidates nội bộ. Enabled với pool20 và request.top_k5 tạo internal request.top_k20; final response.top_k vẫn5. Với user xin30, pool20, internal lấy max(20,30)=30. Branch budgets vẫn mặc định20/20; overlap/filters có thể khiến số candidates nhỏ hơn requested pool. Không bypass policy hoặc tự refill.

Mỗi candidate là **UnifiedEvidence đã hydrate/validate**, không phải SparseSearchHit UUID/score. Có content, stored hash, source/chunk IDs, title/URL, locators, metadata, date/policy, RRF score và rank. Model adapter chỉ nhận tuple content, không nhận quyền thay metadata.

## B — Execution flow theo source hiện tại

```text
CLI main → validate request + RerankConfig → bootstrap read adapters + local scorer
 → RetrievalService.search(hybrid)
 → search_reranked [chỉ enabled]
    → internal request với top_k=max(final_k,pool)
    → run_hybrid closure → existing search_hybrid
       → BM25 đầy đủ → Dense đầy đủ → closing checks → RRF → HybridResponse
    → validate_candidates
    → LocalCrossEncoder.score_pairs → worker _score → _load nếu cold
    → select_candidates → final IDs/ranks
    → closing sparse/dense index checks sau inference
    → reorder fusion explanations + warnings + CE metadata
    → RerankedHybridRetrievalResponse → service → CLI JSON
```

### B1. Validation, mode và dependency injection

CLI vẫn tạo request trước dependencies, date/policies bắt buộc; flags mới chỉ opt-in. `--rerank` yêu cầu `--mode hybrid` và explicit `--rerank-model-path`, còn Hybrid vẫn cần `--dense-model-path`. Default mode vẫn bm25, top_k10, enabled=False. Constructor config keyword-only; không thêm global model hay đọc model path ngầm từ môi trường.

Bootstrap tạo `LocalCrossEncoder(config)` chỉ nếu enabled; constructor chưa import torch, chưa load weights. Service giữ một instance để tái sử dụng model. Với BM25/Dense-only, service đi branch cũ; CLI reject explicit --rerank non-hybrid để tránh người dùng tưởng đã rerank. Disabled Hybrid gọi đúng search_hybrid cũ, không expand pool, không thêm field `reranking` vào JSON.

**FROM** CLI `_configured_service` → **CALL** bootstrap `create_retrieval_service` → **TO** repositories + local scorer constructors → **ACTION** inject ports/config → **RETURN** một RetrievalService → **BACK TO** `main`, gọi `asyncio.run(service.search(request))`.

### B2. Candidate generation giữ nguyên guards

Service `search` tạo closure `run_hybrid(branch_request)` dùng existing search_hybrid, cùng readers, config và30s timeout. Enabled truyền closure cho `search_reranked`. Nó tạo internal request mới bằng model_validate, chỉ đổi top_k. Query/date/policies không đổi.

Existing Hybrid tuần tự chạy BM25 rồi Dense. Chương01 (historical/local reference; not included in this Task 8 publication) giải thích sparse RPC/tokenization/hydration; chương02 (historical/local reference; not included in this Task 8 publication) giải thích vector RPC và integrity checks. SQL vẫn đọc sparse_indexes/sparse_chunk_documents/sparse_postings hoặc dense_indexes/dense_chunk_embeddings, cùng retrieval_chunks/source_documents. **Không có RPC reranking hoặc SQL migration mới.**

Hybrid lỗi thì response.error được nâng thành RetrievalServiceError và final FAILED; scorer chưa được gọi. Hybrid thành công thì `validate_candidates` parse lại evidence, check unique UUID, consecutive rank, method hybrid, MATCHED_STORED và SHA-256 content. Missing text là contract error, không biến thành model operational fallback. Các kiểm tra này ở ngoài scoring fallback block.

## C — Cross-Encoder: từ pair đến scalar logit

### C1. Model local và load boundary

Checkpoint dùng `cross-encoder/mmarco-mMiniLMv2-L12-H384-v1`, snapshot `1427fd652930e4ba29e8149678df786c240d8825`. Runtime smoke và live đều đã load thành công trên CPU. Model file SHA-256 quan sát: `5daeca2481a76b5976a2bdc32f0a78532b6716da4f8cd3ff59460ef8d2f359b4`. Manifest nằm trong engineering evidence, không cần tải model.

`LocalCrossEncoder._load` dùng **AutoTokenizer + AutoModelForSequenceClassification**, không tự viết Transformer và không bắt buộc class phải tên CrossEncoder. Hai from_pretrained đều local_files_only=True, trust_remote_code=False. Model chuyển CPU/float32, eval. Guard kiểm tra model_type xlm-roberta, num_labels1, hidden384,12 layers và tokenizer limit đủ config.max_length. Guard không hash-attest mọi model path; metadata name/revision là checkpoint contract, verifier mới ghi hash của weights thật. Không nên coi dimension/check config là chứng minh tuyệt đối danh tính weights.

Local config cho12 heads, vocabulary250002, tokenizer XLMRobertaTokenizer, tokenizer max512; model max_position_embeddings514 không phải pair budget514. Khác E5 chương02: ở đây backbone XLM-R classification và head1 label, không tạo sentence vector để cosine search. Parameter hidden384 trùng E5 không có nghĩa embeddings/scoring dùng chung cơ chế.

### C2. Query và passage được tokenize thế nào?

Query vào scorer là `request.query.strip()`, giữ dấu/case; không NFC/lower/dedup như BM25 và không thêm `query:`/`passage:` prefix E5. `passages = tuple(c.content for c in candidates)` giữ đúng RRF order. Cùng positional index i phải xuyên suốt tokenizer batch, scores và original UUID.

`_score` đếm query_ids không special tokens, dùng `num_special_tokens_to_add(pair=True)` tính overhead. Query không còn chỗ cho passage trong max_length thì QUERY_TOO_LONG. Từng passage được tokenize không special để đánh dấu liệu query+passage+overhead vượt512; đây là boolean diagnostic, không rewrite stored content.

Batch tokenizer gọi hai lists: `[query]*len(batch)` và `list(batch)`, padding=True, truncation='only_second', max_length512, return_tensors='pt'. Tokenizer tự thêm pair separators theo checkpoint. Padding chỉ đến pair dài nhất trong batch, không mặc định512. Cắt đuôi **passage**, giữ nguyên câu hỏi; không cắt theo số từ vì một từ tiếng Việt có thể thành nhiều subwords. Đoạn ngoại lệ nằm cuối chunk có thể không đi vào model, dù evidence trả về vẫn giữ toàn content. Có warning RERANKING_TRUNCATED nếu ít nhất một candidate bị cắt.

### C3. Tensors và inference

Token là subword; input ID là số nguyên tra vocabulary; mask0 đánh dấu padding,1 đánh dấu nội dung/special tokens có hiệu lực. Với batch B<=4 và L<=512, input IDs/mask shape[B,L] (PyTorch integer), hidden states nội bộ[B,L,384]. Query/passages cùng sequence nên attention nhìn cả hai phía; classification head của model trả logits[B,1]. Repo không tự pooling mean như E5.

`torch.inference_mode()` tắt autograd bookkeeping; model.eval tắt training dropout. `_score` kiểm tra chính xác logits.shape==(len(batch),1), lấy `logits[:,0]`, `.cpu().tolist()`, ép từng giá trị thành float rồi nối scores theo batch order. Output `PairScores` gồm tuple scores, tuple truncated, cold flag, load_seconds, inference_seconds. Port PairScorer trả typed result thay bare tuple để mang diagnostics; ranking vẫn dựa một score/mỗi candidate.

Không sigmoid hay softmax trong application adapter. Logit có thể âm; score=-3 không phải “xác suất âm”. Lớn hơn chỉ nghĩa model cho relevance cao hơn tương đối. Dù sigmoid đưa vào0–1, không có calibration để gọi xác suất căn cứ đúng. Cross-Encoder không quyết định effective date, usage policy hoặc legal validity.

### C4. CPU, lock và timing

`score_pairs` dùng asyncio.to_thread; `_score` acquire threading.Lock nonblocking trước load và finally release sau toàn bộ worker. Busy nhận MODEL_BUSY. Nếu coroutine bị timeout/cancel, worker không tự dừng; lock còn giữ tới khi worker xong. Test cancellation xác nhận request sau không chạy chồng inference. Không queue model requests vô hạn, không tải model runtime, không cloud inference.

load_seconds cold bao import/load/check/eval; warm=0. inference_seconds đo batch tokenization+forward+conversion loop, **không** gồm pre-pass đếm query/passage tokens. elapsed của verifier bao toàn score_pairs, nên có thể lớn hơn tổng hai diagnostics. Đây là thời gian wall-clock CPU inference workload, không phải CPU cycles hoặc GPU latency.

## D — Sorting, response và fallback

### D1. Map score đúng chunk và giữ RRF

`select_candidates(candidates,scores,top_k)` kiểm tra count/finite/scalar/non-bool rồi sort indexes theo `(-scores[i], candidates[i].rank, str(UUID))`. CE hòa thì ưu tiên original RRF rank; UUID là tie cuối. Valid original ranks là unique nên tie UUID hiếm khi được dùng nhưng vẫn deterministic.

Ví dụ **ILLUSTRATIVE**: RRF=[A(rank1,score0.032),B(rank2,0.031),C(rank3,0.016)], CE scores=(-4,-1,-2). Order mới B,C,A; final_k2 chọn B,C, rank1/2. raw_score vẫn0.031/0.016; CE=-1/-2 nằm riêng metadata. Không cộng CE với RRF.

Selection tạo UnifiedEvidence bằng toàn payload gốc và chỉ thay rank; model_validate lại. Query/source/content/hash/dates/policies/locators không được thay đổi. Coordinator map fusion explanations theo UUID rồi reorder/filter theo selected evidence. `fusion.ranking` vẫn giải thích công thức RRF, còn `reranking.candidates` lưu **toàn pool** với original_rank/rrf_score/cross_encoder_score/final_rank (None cho candidate bị loại).

`RerankedHybridRetrievalResponse` kế thừa HybridRetrievalResponse, không nới validator cũ: RRF raw_score phải khớp contributions. Validator mới so candidate uniqueness/original ranks, diagnostic score alignment, final ID order/ranks và giữ điểm RRF. Model chỉ bảo vệ contract fields được serialize; nguồn metadata vẫn dựa integrity gates trước đó, không model nào chứng thực pháp luật.

Audit source consumer không tìm thấy consumer downstream sort final evidence theo raw_score; consumer hiện đã nối là CLI in model_dump_json giữ nguyên list. Test CLI dùng CE order cố ý khác RRF order xác nhận không bị đổi lại. **Consumer bên ngoài repo chưa được kiểm tra**; khi opt-in phải dùng evidence order/rank và parse subclass. Base response extra-forbid không nhận extension. Disabled vẫn trả schema cũ.

### D2. Failures không đánh đồng với no-match

| Case | Output thật |
|---|---|
| Empty candidates | Không gọi model, NO_MATCH/SKIPPED_EMPTY |
| Một candidate | Vẫn score; output identity không đổi |
| N<final_k | Trả N, không tự fill |
| Missing/load/tokenization/inference/model busy, wrong scores/NaN/Inf, CE deadline | FALLBACK, RRF order topK, warning RERANKING_FALLBACK + safe code |
| Bad content/hash/identity/duplicate, retrieval/policy error | FAILED, evidence rỗng; không model fallback che lỗi |
| Post-inference index changes hoặc read lỗi | FAILED, không trả evidence quan sát từ index đã đổi |
| Total enabled deadline | RERANK_PIPELINE_TIMEOUT, FAILED; không hứa fallback vượt deadline |
| External cancellation | Không catch BaseException; cancellation lan ra, worker giữ lock tới khi xong |

Adapter chỉ phát RerankingOperationalError với safe stage code; coordinator allowlist code trước ghi public response, không echo exception paths/credentials. Không có retry. Model errors nằm trong inner timeout10s; total enabled timeout40s bao cả Hybrid, CE và closing reads. Disabled vẫn timeout30s của flow cũ. Fallback cũng phải qua closing checks; nếu tổng deadline không còn thì fail.

Sau inference, `_check_closing_index` được gọi lại cho sparse/dense observations. Đây là guard thêm, không transaction snapshot; vẫn consistency=BEST_EFFORT. Source dates/policy giữ như quan sát lúc retrieval, không tự update date bằng model. Warnings chunk ngoài final IDs bị lọc, global warnings được giữ.

## E — Thực thi thật, evaluation và giới hạn bằng chứng

Đã chạy query **“Điều kiện để hợp đồng dân sự có hiệu lực là gì?”**, mode hybrid, as_of_date2026-11-16, policy EXPERIMENTAL_ONLY, budgets20/20, pool20, final5. Verifier dùng existing configured Supabase, chỉ cho6 read RPCs qua HTTP GET/get=True và chặn mọi method/RPC khác. Không crawl/re-ingest/ghi data hoặc schema. Production SDK POST transport không nằm trong live check này; repository mappings/service/model là thật dưới read-only instrumentation.

Kết quả live_cold và live_warm đều OK/APPLIED,20 candidates,5 final, không fallback, không truncation. Same scores/order được quan sát hai lần, không suy ra deterministic tuyệt đối trên mọi máy. Artifact task8-execution-evidence.json (historical/local reference; not included in this Task 8 publication) lưu20 UUID/original ranks/CE scores/final ranks, source identity/title/dates/policy, RPC sequence và timings; không lưu full content. Verifier thực sự dùng content từ RPC để inference, service hash-check trước và sau đó fusion/selection giữ payload.

Cold smoke pair2 khác live pool20: elapsed19.366s, load19.252s, batch inference0.100s; warm smoke elapsed0.0307s/inference0.0297s. Working set tăng từ36.6MB lên1.170GB (decimal bytes), không gọi đó là peak RAM hệ thống. Trên live pool20, new adapter load3.770s vì imports/OS caches đã warm sau smoke; batch inference1.970s, full Retrieval11.924s. Warm adapter inference1.816s/full Retrieval5.455s. E5 warmup riêng8.024s, không được cộng ngầm vào measured live Retrieval.

Timeout10s thực dụng cho measured warm pool này, **không đủ bảo đảm process-cold CE** đã đo19.25s load. Giữ default opt-in budgets để compatibility; khi thử cold process nên explicit --rerank-timeout30 --rerank-total-timeout70 hoặc warm scorer trước traffic ở controlled runtime. Đây là recipe theo hai runs, không production SLA; không có p95 từ hai samples. Late worker sau timeout vẫn có thể tiêu tốn RAM/CPU.

Evaluation harness ở `scripts/evaluate_retrieval.py`: đọc saved rankings và human qrels, cùng corpus manifest/query/date/policies; riêng RRF/CE dùng frozen Hybrid pool. Tính Precision@K, Recall@K, MRR@K và graded nDCG gain2^grade−1/log2(rank+1), candidate coverage. Harness còn yêu cầu pinned corpus manifest và reranking_status=APPLIED để không tính fallback như CE. Unjudged không tự biến thành negative; thiếu judgments thì excluded và metrics means=null. Dataset template mẫu là UNVERIFIED, chưa có labels thật để chạy quality comparisons. Không tuyên bố reranker tốt hơn BM25/Dense/Hybrid. Số scores âm hay đảo thứ tự không phải nhãn ground truth.

Error analysis cần người annotate: absent relevant chunk trong pool là generation failure; có trong pool nhưng CE hạ là reranking failure; kiểm tra khác điều luật/thời điểm/phủ định/ngoại lệ, truncation cuối chunk và disagreement branches. Giữ disabled default đến khi quality+latency evidence đủ.

## F — 15 câu hỏi vấn đáp

1. **Tại sao RRF chưa là CE reranking?** RRF chỉ nhận thứ hạng hai backend; CE forward query-content pair. Hai cơ chế có input và chi phí khác nhau.
2. **Reranker chèn ở đâu?** Sau existing Hybrid đã hydrate/check/fuse, trước final selection/response. Source service truyền closure run_hybrid cho search_reranked.
3. **Pool20 có làm trả20 khi xin5 không?** Không. Internal request20 để giữ candidates; response request.top_k5 và selection cắt5.
4. **Model nào đã thực sự chạy?** Local mMARCO MiniLMv2 snapshot1427fd6..., CPU float32; evidence ghi full revision/hash và actual logits, không download.
5. **Có tạo vector384 để cosine không?** Không. Hidden384 là token feature size; classifier output[B,1] thành scalar relevance. Không E5 pooling/cosine ở stage này.
6. **Scores có là probability không?** Raw logits, có thể âm. Không sigmoid và chưa calibration; không suy ra xác suất luật đúng.
7. **Tại sao giữ điểm RRF?** Để truy vết candidate generation/fusion và giữ contract score_kind RRF. CE score lưu riêng, final rank là thứ tự CE.
8. **Consumer có sort lại RRF không?** CLI giữ thứ tự, có test order khác RRF; chưa biết external consumers nên opt-in contract yêu cầu dùng rank/list order.
9. **Hòa CE thì sao?** Original RRF rank rồi UUID; không làm input order tùy ý quyết định nếu candidates violate ranks vì guard đã chặn.
10. **Model lỗi có mất evidence không?** Lỗi operational CE fallback RRF có warning; retrieval/integrity/index failures vẫn FAILED với zero evidence.
11. **Timeout có kill thread không?** Không. Await timeout/cancel không dừng synchronous worker; lock giữ tới finally, request sau có thể MODEL_BUSY.
12. **Cắt text có sửa citation không?** Chỉ tokenized passage input bị truncate; original evidence content/hash/metadata giữ nguyên. Điều đó cũng nghĩa model có thể chưa thấy ngoại lệ cuối chunk.
13. **Date/policy do model quyết định không?** Không. SQL+Python eligibility trước CE và index checks sau CE; model chỉ reorder allowed evidence.
14. **Đã cải thiện quality chưa?** Chưa có valid qrels nên chưa kết luận. Technical E2E và tests chứng minh flow/guards, không relevance improvement.
15. **Timeout10s có phù hợp CPU không?** Warm pool20 measured1.82s inference, nhưng first process load19.25s; cold cần budget lớn hơn hoặc controlled warmup, không chỉ nhìn warm latency.

## Phụ lục — Source trace có caller/callee và return path

Path relative với main. Exact line ranges lấy từ AST sau format; các function đề cập dưới đây đều tồn tại trong source hiện tại.

### `main`

- **Source/class/function/lines:** [scripts/search_legal_chunks.py:64–163](../../scripts/search_legal_chunks.py#L64), class `module-level`.
- **Caller/input:** process/CLI; argv.
- **Purpose/action/variables:** flags mới được validate trước dependencies; output serialization giữ list order.
- **Callee:** _configured_service, RetrievalService.search.
- **Output/downstream:** validated request/config rồi response JSON, quay về process/CLI; exception đi theo failure policy phầnD.
- **Return path:** FROM process/CLI → CALL `main` → TO `scripts/search_legal_chunks.py` → ACTION flags mới được validate trước dependencies; output serialization giữ list order → RETURN validated request/config rồi response JSON → BACK TO process/CLI.

### `create_retrieval_service`

- **Source/class/function/lines:** [src/retrieval_bootstrap.py:22–68](../../src/retrieval_bootstrap.py#L22), class `module-level`.
- **Caller/input:** CLI _configured_service; settings/dense path/rerank config.
- **Purpose/action/variables:** chỉ enabled tạo scorer; không load model ở constructor.
- **Callee:** repositories, E5QueryEncoder, LocalCrossEncoder constructors.
- **Output/downstream:** RetrievalService, quay về CLI _configured_service; exception đi theo failure policy phầnD.
- **Return path:** FROM CLI _configured_service → CALL `create_retrieval_service` → TO `src/retrieval_bootstrap.py` → ACTION chỉ enabled tạo scorer; không load model ở constructor → RETURN RetrievalService → BACK TO CLI _configured_service.

### `RetrievalService.search`

- **Source/class/function/lines:** [src/application/services/retrieval_service.py:192–305](../../src/application/services/retrieval_service.py#L192), class `RetrievalService`.
- **Caller/input:** CLI main; Hybrid branch callback; RetrievalRequest.
- **Purpose/action/variables:** dispatch mode; enabled Hybrid mới expand pool; BM25/Dense unchanged.
- **Callee:** search_reranked hoặc search_hybrid và existing branch helpers.
- **Output/downstream:** RetrievalResponse/HybridResponse/opt-in subclass, quay về CLI main; Hybrid branch callback; exception đi theo failure policy phầnD.
- **Return path:** FROM CLI main; Hybrid branch callback → CALL `RetrievalService.search` → TO `src/application/services/retrieval_service.py` → ACTION dispatch mode; enabled Hybrid mới expand pool; BM25/Dense unchanged → RETURN RetrievalResponse/HybridResponse/opt-in subclass → BACK TO CLI main; Hybrid branch callback.

### `search_reranked`

- **Source/class/function/lines:** [src/application/services/reranking.py:30–176](../../src/application/services/reranking.py#L30), class `module-level`.
- **Caller/input:** RetrievalService.search; request, run_hybrid, scorer/config/readers.
- **Purpose/action/variables:** internal request vs final request, scoring block fallback, closing checks, metadata/response assembly.
- **Callee:** run_hybrid, validate_candidates, score_pairs, select_candidates, _check_closing_index.
- **Output/downstream:** RerankedHybridRetrievalResponse, quay về RetrievalService.search; exception đi theo failure policy phầnD.
- **Return path:** FROM RetrievalService.search → CALL `search_reranked` → TO `src/application/services/reranking.py` → ACTION internal request vs final request, scoring block fallback, closing checks, metadata/response assembly → RETURN RerankedHybridRetrievalResponse → BACK TO RetrievalService.search.

```python
async def search_reranked(
    request: RetrievalRequest,
    *,
    run_hybrid: Callable[[RetrievalRequest], Awaitable[HybridRetrievalResponse]],
    scorer: PairScorer | None,
    config: RerankConfig,
    sparse_indexes: IndexReader,
    dense_indexes: IndexReader | None,
    hybrid_config: HybridConfig,
) -> RerankedHybridRetrievalResponse:
    pool = max(config.candidate_pool, request.top_k)
    response = None
    payload = None
    try:
        async with asyncio.timeout(config.total_timeout_seconds):
            internal = RetrievalRequest.model_validate({**request.model_dump(), "top_k": pool})
            response = await run_hybrid(internal)
            if response.error:
                raise RetrievalServiceError(response.error)
            candidates = response.evidence
            validate_candidates(candidates)
            diagnostics = None
            code = None
            scores = None
            selected = ()
            if candidates:
                try:
                    if scorer is None:
                        raise RerankingOperationalError("MODEL_NOT_CONFIGURED")
                    async with asyncio.timeout(config.inference_timeout_seconds):
                        diagnostics = PairScores.model_validate(
                            await scorer.score_pairs(
                                request.query.strip(),
                                tuple(c.content for c in candidates),
                            )
                        )
                    if len(diagnostics.truncated) != len(candidates):
                        raise RerankingOperationalError("INVALID_SCORES")
                    selected = select_candidates(candidates, diagnostics.scores, request.top_k)
                    scores = diagnostics.scores
                except (RerankingOperationalError, TimeoutError, ValidationError) as failure:
                    code = (
                        str(failure)
                        if isinstance(failure, RerankingOperationalError)
                        else ("RERANK_TIMEOUT" if isinstance(failure, TimeoutError) else "INVALID_SCORES")
                    )
                    # Only allow known, safe codes into public metadata.
                    allowed = {
                        "MODEL_NOT_CONFIGURED",
                        "MODEL_NOT_PROVISIONED",
                        "MODEL_LOAD_FAILED",
                        "MODEL_INCOMPATIBLE",
                        "MODEL_BUSY",
                        "QUERY_TOO_LONG",
                        "TOKENIZATION_FAILED",
                        "INFERENCE_FAILED",
                        "INVALID_SCORES",
                        "RERANK_TIMEOUT",
                    }
                    code = code if code in allowed else "INFERENCE_FAILED"
                    diagnostics = None
                    selected = select_candidates(candidates, None, request.top_k)
            # Extend existing index observations over model inference, including fallback.
            for branch, reader in zip(response.fusion.branches, (sparse_indexes, dense_indexes)):
                if reader is None or branch.index is None:
                    raise ValueError("Missing successful Hybrid index observation")
                await _check_closing_index(reader, branch.index)
            final_ids = {e.retrieval_chunk_id for e in selected}
            warnings = [
                w for w in response.warnings if w.retrieval_chunk_id is None or w.retrieval_chunk_id in final_ids
            ]
            if code:
                warnings.append(
                    RetrievalWarning(
                        code="RERANKING_FALLBACK", message="Cross-Encoder unavailable; RRF order retained."
                    )
                )
            if diagnostics and any(diagnostics.truncated):
                warnings.append(
                    RetrievalWarning(
                        code="RERANKING_TRUNCATED",
                        message="Some model inputs were truncated; stored evidence is unchanged.",
                    )
                )
            final_ranks = {e.retrieval_chunk_id: e.rank for e in selected}
            ranking = {row.retrieval_chunk_id: row for row in response.fusion.ranking}
            payload = {
                **response.model_dump(),
                **request.model_dump(),
                "evidence": selected,
                "warnings": tuple(warnings),
                "retrieved_at": utc_now(),
                "fusion": {
                    **response.fusion.model_dump(),
                    "ranking": tuple(ranking[e.retrieval_chunk_id] for e in selected),
                },
                "reranking": RerankingMetadata(
                    status="SKIPPED_EMPTY" if not candidates else "FALLBACK" if code else "APPLIED",
                    config=config,
                    requested_candidates=pool,
                    diagnostics=diagnostics,
                    failure_code=code,
                    candidates=tuple(
                        CandidateScore(
                            retrieval_chunk_id=c.retrieval_chunk_id,
                            original_rank=c.rank,
                            rrf_score=c.raw_score,
                            cross_encoder_score=scores[i] if scores is not None else None,
                            final_rank=final_ranks.get(c.retrieval_chunk_id),
                        )
                        for i, c in enumerate(candidates)
                    ),
                ),
            }
    except (RetrievalServiceError, DatabaseRepositoryError, TimeoutError, ValidationError) as failure:
        detail = (
            failure.detail
            if isinstance(failure, RetrievalServiceError)
            else RetrievalErrorDetail(
                category=ErrorCategory.TIMEOUT
                if isinstance(failure, TimeoutError)
                else (
                    ErrorCategory.DATABASE_FAILURE
                    if isinstance(failure, DatabaseRepositoryError)
                    else ErrorCategory.INCONSISTENT_EVIDENCE
                ),
                code="RERANK_PIPELINE_TIMEOUT" if isinstance(failure, TimeoutError) else "RERANK_VERIFICATION_FAILED",
                stage="reranking",
                message="Reranked retrieval could not complete its consistency checks.",
                retryable=isinstance(failure, TimeoutError),
            )
        )
        payload = {
            **request.model_dump(),
            "request_id": response.request_id if response else new_id(),
            "query_used": request.query.strip(),
            "selected_index_name": "hybrid",
            "index": None,
            "status": "FAILED",
            "error": detail,
            "retrieved_at": utc_now(),
            "fusion": FusionMetadata(config=hybrid_config, branches=response.fusion.branches if response else ()),
            "reranking": RerankingMetadata(
                status="FAILED", config=config, requested_candidates=pool, failure_code=detail.code
            ),
        }
    return RerankedHybridRetrievalResponse.model_validate(payload)
```

### `validate_candidates`

- **Source/class/function/lines:** [src/applications/tillegal/retrieval/reranker.py:14–33](../../src/applications/tillegal/retrieval/reranker.py#L14), class `module-level`.
- **Caller/input:** search_reranked và select_candidates; tuple UnifiedEvidence.
- **Purpose/action/variables:** dùng original rank/UUID/content/hash/method; tạo set IDs, không sửa payload.
- **Callee:** UnifiedEvidence.model_validate, sha256.
- **Output/downstream:** None hoặc integrity exception, quay về search_reranked và select_candidates; exception đi theo failure policy phầnD.
- **Return path:** FROM search_reranked và select_candidates → CALL `validate_candidates` → TO `src/applications/tillegal/retrieval/reranker.py` → ACTION dùng original rank/UUID/content/hash/method; tạo set IDs, không sửa payload → RETURN None hoặc integrity exception → BACK TO search_reranked và select_candidates.

```python
def validate_candidates(candidates: tuple[UnifiedEvidence, ...]) -> None:
    ids = set()
    for rank, candidate in enumerate(candidates, 1):
        item = UnifiedEvidence.model_validate(candidate.model_dump())
        if (
            item.retrieval_chunk_id in ids
            or item.rank != rank
            or item.retrieval_method != "hybrid"
            or item.hash_check != "MATCHED_STORED"
            or hashlib.sha256(item.content.encode("utf-8")).hexdigest() != item.content_sha256
        ):
            raise RetrievalServiceError(
                RetrievalErrorDetail(
                    category=ErrorCategory.INCONSISTENT_EVIDENCE,
                    code="INVALID_RERANK_CANDIDATES",
                    stage="reranking",
                    message="Reranking candidates violate identity or integrity constraints.",
                )
            )
        ids.add(item.retrieval_chunk_id)
```

### `select_candidates`

- **Source/class/function/lines:** [src/applications/tillegal/retrieval/reranker.py:36–55](../../src/applications/tillegal/retrieval/reranker.py#L36), class `module-level`.
- **Caller/input:** search_reranked; candidate tuple/scores optional/top_k.
- **Purpose/action/variables:** sort index theo CE/original rank/UUID; chỉ thay rank; scores None giữ RRF order.
- **Callee:** validate_candidates, UnifiedEvidence.model_validate.
- **Output/downstream:** selected evidence tuple, quay về search_reranked; exception đi theo failure policy phầnD.
- **Return path:** FROM search_reranked → CALL `select_candidates` → TO `src/applications/tillegal/retrieval/reranker.py` → ACTION sort index theo CE/original rank/UUID; chỉ thay rank; scores None giữ RRF order → RETURN selected evidence tuple → BACK TO search_reranked.

```python
def select_candidates(
    candidates: tuple[UnifiedEvidence, ...],
    scores: tuple[float, ...] | None,
    top_k: int,
) -> tuple[UnifiedEvidence, ...]:
    validate_candidates(candidates)
    if type(top_k) is not int or not 1 <= top_k <= 50:
        raise ValueError("Invalid final top-k")
    if scores is not None and (
        len(scores) != len(candidates)
        or any(isinstance(x, bool) or not isinstance(x, (float, int)) or not math.isfinite(x) for x in scores)
    ):
        raise RerankingOperationalError("INVALID_SCORES")
    order = list(range(len(candidates)))
    if scores is not None:
        order.sort(key=lambda i: (-scores[i], candidates[i].rank, str(candidates[i].retrieval_chunk_id)))
    return tuple(
        UnifiedEvidence.model_validate({**candidates[i].model_dump(), "rank": rank})
        for rank, i in enumerate(order[:top_k], 1)
    )
```

### `LocalCrossEncoder.score_pairs`

- **Source/class/function/lines:** [src/integrations/embeddings/cross_encoder_reranker.py:19–20](../../src/integrations/embeddings/cross_encoder_reranker.py#L19), class `LocalCrossEncoder`.
- **Caller/input:** search_reranked; query str/passages tuple[str,...].
- **Purpose/action/variables:** offload inference; cancellation không kill worker.
- **Callee:** asyncio.to_thread(self._score).
- **Output/downstream:** PairScores, quay về search_reranked; exception đi theo failure policy phầnD.
- **Return path:** FROM search_reranked → CALL `LocalCrossEncoder.score_pairs` → TO `src/integrations/embeddings/cross_encoder_reranker.py` → ACTION offload inference; cancellation không kill worker → RETURN PairScores → BACK TO search_reranked.

```python
    async def score_pairs(self, query: str, passages: tuple[str, ...]) -> PairScores:
        return await asyncio.to_thread(self._score, query, passages)
```

### `LocalCrossEncoder._load`

- **Source/class/function/lines:** [src/integrations/embeddings/cross_encoder_reranker.py:22–44](../../src/integrations/embeddings/cross_encoder_reranker.py#L22), class `LocalCrossEncoder`.
- **Caller/input:** _score nếu cold; self._config.model_path.
- **Purpose/action/variables:** local-only CPU,float32,eval; model shape guards; error translated ở _score.
- **Callee:** AutoTokenizer/AutoModelForSequenceClassification.from_pretrained.
- **Output/downstream:** None, cache tokenizer/model, quay về _score nếu cold; exception đi theo failure policy phầnD.
- **Return path:** FROM _score nếu cold → CALL `LocalCrossEncoder._load` → TO `src/integrations/embeddings/cross_encoder_reranker.py` → ACTION local-only CPU,float32,eval; model shape guards; error translated ở _score → RETURN None, cache tokenizer/model → BACK TO _score nếu cold.

```python
    def _load(self) -> None:
        path = self._config.model_path
        if path is None or not path.is_dir():
            raise RerankingOperationalError("MODEL_NOT_PROVISIONED")
        import torch
        from transformers import AutoModelForSequenceClassification, AutoTokenizer

        tokenizer = AutoTokenizer.from_pretrained(str(path), local_files_only=True, trust_remote_code=False)
        model = AutoModelForSequenceClassification.from_pretrained(
            str(path),
            local_files_only=True,
            trust_remote_code=False,
        ).to(device="cpu", dtype=torch.float32)
        if (
            model.config.model_type != "xlm-roberta"
            or model.config.num_labels != 1
            or model.config.hidden_size != 384
            or model.config.num_hidden_layers != 12
            or tokenizer.model_max_length < self._config.max_length
        ):
            raise RerankingOperationalError("MODEL_INCOMPATIBLE")
        model.eval()
        self._tokenizer, self._model = tokenizer, model
```

### `LocalCrossEncoder._score`

- **Source/class/function/lines:** [src/integrations/embeddings/cross_encoder_reranker.py:46–100](../../src/integrations/embeddings/cross_encoder_reranker.py#L46), class `LocalCrossEncoder`.
- **Caller/input:** score_pairs worker; query/passages/config, cached model/tokenizer.
- **Purpose/action/variables:** lock; lengths/truncated; batch only_second; logits shape guard; tuple floats; finally unlock.
- **Callee:** _load, tokenizer, model forward, PairScores.
- **Output/downstream:** PairScores, quay về score_pairs worker; exception đi theo failure policy phầnD.
- **Return path:** FROM score_pairs worker → CALL `LocalCrossEncoder._score` → TO `src/integrations/embeddings/cross_encoder_reranker.py` → ACTION lock; lengths/truncated; batch only_second; logits shape guard; tuple floats; finally unlock → RETURN PairScores → BACK TO score_pairs worker.

```python
    def _score(self, query: str, passages: tuple[str, ...]) -> PairScores:
        if not self._lock.acquire(blocking=False):
            raise RerankingOperationalError("MODEL_BUSY")
        stage = "MODEL_LOAD_FAILED"
        try:
            cold = self._model is None
            started = time.perf_counter()
            if cold:
                self._load()
            load_seconds = time.perf_counter() - started if cold else 0.0
            import torch

            stage = "TOKENIZATION_FAILED"
            tokenizer = self._tokenizer
            query_ids = tokenizer(query, add_special_tokens=False)["input_ids"]
            overhead = tokenizer.num_special_tokens_to_add(pair=True)
            if not query.strip() or len(query_ids) + overhead >= self._config.max_length:
                raise RerankingOperationalError("QUERY_TOO_LONG")
            truncated = tuple(
                len(query_ids) + overhead + len(tokenizer(p, add_special_tokens=False)["input_ids"])
                > self._config.max_length
                for p in passages
            )
            scores = []
            started = time.perf_counter()
            with torch.inference_mode():
                for start in range(0, len(passages), self._config.batch_size):
                    batch = passages[start : start + self._config.batch_size]
                    stage = "TOKENIZATION_FAILED"
                    inputs = tokenizer(
                        [query] * len(batch),
                        list(batch),
                        padding=True,
                        truncation="only_second",
                        max_length=self._config.max_length,
                        return_tensors="pt",
                    )
                    stage = "INFERENCE_FAILED"
                    logits = self._model(**inputs).logits
                    if tuple(logits.shape) != (len(batch), 1):
                        raise RerankingOperationalError("INVALID_SCORES")
                    scores.extend(float(x) for x in logits[:, 0].cpu().tolist())
            return PairScores(
                scores=tuple(scores),
                truncated=truncated,
                cold=cold,
                load_seconds=load_seconds,
                inference_seconds=time.perf_counter() - started,
            )
        except RerankingOperationalError:
            raise
        except Exception as error:
            raise RerankingOperationalError(stage) from error
        finally:
            self._lock.release()
```

### `PairScores.numeric_scores`

- **Source/class/function/lines:** [src/applications/tillegal/retrieval/reranking_models.py:35–40](../../src/applications/tillegal/retrieval/reranking_models.py#L35), class `PairScores`.
- **Caller/input:** Pydantic PairScores construction; raw scores object.
- **Purpose/action/variables:** reject bool/string trước coercion; ContractModel còn chặn nonfinite.
- **Callee:** scalar/type checks.
- **Output/downstream:** numeric values hoặc ValueError, quay về Pydantic PairScores construction; exception đi theo failure policy phầnD.
- **Return path:** FROM Pydantic PairScores construction → CALL `PairScores.numeric_scores` → TO `src/applications/tillegal/retrieval/reranking_models.py` → ACTION reject bool/string trước coercion; ContractModel còn chặn nonfinite → RETURN numeric values hoặc ValueError → BACK TO Pydantic PairScores construction.

```python
    def numeric_scores(cls, values: object) -> object:
        if not isinstance(values, (tuple, list)) or any(
            isinstance(x, bool) or not isinstance(x, (float, int)) for x in values
        ):
            raise ValueError("Scores must be scalar numbers, not booleans or strings")
        return values
```

### `RerankedHybridRetrievalResponse.validate_reranking`

- **Source/class/function/lines:** [src/applications/tillegal/retrieval/reranking_models.py:69–107](../../src/applications/tillegal/retrieval/reranking_models.py#L69), class `RerankedHybridRetrievalResponse`.
- **Caller/input:** Pydantic response model_validate; self metadata/evidence.
- **Purpose/action/variables:** APPLIED/FALLBACK/SKIPPED_EMPTY/FAILED state validation, không thay payload.
- **Callee:** sort/check diagnostics/UUIDs/ranks/RRF scores.
- **Output/downstream:** self hoặc ValueError, quay về Pydantic response model_validate; exception đi theo failure policy phầnD.
- **Return path:** FROM Pydantic response model_validate → CALL `RerankedHybridRetrievalResponse.validate_reranking` → TO `src/applications/tillegal/retrieval/reranking_models.py` → ACTION APPLIED/FALLBACK/SKIPPED_EMPTY/FAILED state validation, không thay payload → RETURN self hoặc ValueError → BACK TO Pydantic response model_validate.

```python
    def validate_reranking(self) -> Self:
        meta = self.reranking
        rows = meta.candidates
        if self.status == "FAILED":
            if meta.status != "FAILED":
                raise ValueError("Failed response requires failed reranking")
            return self
        ids = [r.retrieval_chunk_id for r in rows]
        if len(set(ids)) != len(ids) or [r.original_rank for r in rows] != list(range(1, len(rows) + 1)):
            raise ValueError("Invalid original candidate ranking")
        if len(rows) > meta.requested_candidates:
            raise ValueError("Candidate budget exceeded")
        if meta.status == "SKIPPED_EMPTY":
            if rows or self.status != "NO_MATCH":
                raise ValueError("Empty reranking requires NO_MATCH")
            return self
        if meta.status == "APPLIED":
            if any(r.cross_encoder_score is None for r in rows) or meta.diagnostics is None:
                raise ValueError("Applied ranking requires all scores")
            if tuple(r.cross_encoder_score for r in rows) != meta.diagnostics.scores:
                raise ValueError("Scores do not match diagnostics")
            if len(meta.diagnostics.truncated) != len(rows):
                raise ValueError("Truncation count mismatch")
            ordered = sorted(rows, key=lambda r: (-r.cross_encoder_score, r.original_rank, str(r.retrieval_chunk_id)))
        elif meta.status == "FALLBACK":
            if not meta.failure_code or any(r.cross_encoder_score is not None for r in rows):
                raise ValueError("Fallback must not expose partial scores")
            ordered = list(rows)
        else:
            raise ValueError("Invalid successful reranking state")
        selected = ordered[: self.top_k]
        if [r.retrieval_chunk_id for r in selected] != [e.retrieval_chunk_id for e in self.evidence]:
            raise ValueError("Final evidence order differs from reranking")
        ranks = {r.retrieval_chunk_id: i for i, r in enumerate(selected, 1)}
        if any(r.final_rank != ranks.get(r.retrieval_chunk_id) for r in rows):
            raise ValueError("Invalid final rank mapping")
        if any(e.raw_score != rows[ids.index(e.retrieval_chunk_id)].rrf_score for e in self.evidence):
            raise ValueError("Original RRF score changed")
        return self
```

### `search_hybrid`

- **Source/class/function/lines:** [src/application/services/hybrid_retrieval.py:85–196](../../src/application/services/hybrid_retrieval.py#L85), class `module-level`.
- **Caller/input:** run_hybrid closure; internal request/readers/branch callable/config.
- **Purpose/action/variables:** existing sequential strict branch execution, không sửa thuật toán.
- **Callee:** run_branch, closing checks, reciprocal_rank_fusion.
- **Output/downstream:** HybridRetrievalResponse, quay về run_hybrid closure; exception đi theo failure policy phầnD.
- **Return path:** FROM run_hybrid closure → CALL `search_hybrid` → TO `src/application/services/hybrid_retrieval.py` → ACTION existing sequential strict branch execution, không sửa thuật toán → RETURN HybridRetrievalResponse → BACK TO run_hybrid closure.

### `_check_closing_index`

- **Source/class/function/lines:** [src/application/services/hybrid_retrieval.py:53–82](../../src/application/services/hybrid_retrieval.py#L53), class `module-level`.
- **Caller/input:** existing Hybrid và post-CE coordinator; reader, IndexIdentity.
- **Purpose/action/variables:** observed metadata equality; BEST_EFFORT.
- **Callee:** reader.get_index, IndexIdentity.model_validate.
- **Output/downstream:** None/error, quay về existing Hybrid và post-CE coordinator; exception đi theo failure policy phầnD.
- **Return path:** FROM existing Hybrid và post-CE coordinator → CALL `_check_closing_index` → TO `src/application/services/hybrid_retrieval.py` → ACTION observed metadata equality; BEST_EFFORT → RETURN None/error → BACK TO existing Hybrid và post-CE coordinator.

### `reciprocal_rank_fusion`

- **Source/class/function/lines:** [src/applications/tillegal/retrieval/rank_fusion.py:33–95](../../src/applications/tillegal/retrieval/rank_fusion.py#L33), class `module-level`.
- **Caller/input:** search_hybrid; verified BM25/Dense tuples/k/internal top_k.
- **Purpose/action/variables:** existing RRF formula, UUID dedup, ties; không sửa.
- **Callee:** contract/hash checks, RankContribution/FusedRank.
- **Output/downstream:** FusionResult, quay về search_hybrid; exception đi theo failure policy phầnD.
- **Return path:** FROM search_hybrid → CALL `reciprocal_rank_fusion` → TO `src/applications/tillegal/retrieval/rank_fusion.py` → ACTION existing RRF formula, UUID dedup, ties; không sửa → RETURN FusionResult → BACK TO search_hybrid.

## Phụ lục — Trace giá trị live từ RRF đến final top5

Query/date/policy đúng phầnE; đây là observed UUID/score thật, không phải nhãn relevance.

| UUID | Original RRF rank | RRF score giữ nguyên | CE logit | Final rank |
|---|---:|---:|---:|---:|
| e2740feb-e0e8-44fc-b107-faf2c674a835 | 1 | 0.0325224749 | -3.824454 | 1 |
| ecdd3a4a-cbd7-4af7-ab01-072f917056be | 2 | 0.0163934426 | -5.170841 | loại |
| 91e14d33-71b6-4ee1-b24a-f0cc4b8f3d52 | 3 | 0.0161290323 | -4.574693 | loại |
| b625dfa7-ac82-4133-8292-5c6433c94a47 | 4 | 0.0158730159 | -4.747644 | loại |
| d8369105-7be7-4b39-be3f-52a49f8b6c98 | 5 | 0.0158730159 | -5.547254 | loại |
| 51a5efa9-aa28-4c22-85ad-a78a122161e7 | 6 | 0.0156250000 | -4.713626 | loại |
| ba3df67d-e741-43f0-b97a-b413f7389f78 | 7 | 0.0156250000 | -4.438635 | 4 |
| 0f74d56e-4f53-47df-983a-ab6bf6a8ee1c | 8 | 0.0153846154 | -6.582349 | loại |
| ddefc4d1-ee06-485e-9b47-c56408385bd6 | 9 | 0.0153846154 | -4.523940 | 5 |
| cc71082e-4d86-429c-97c4-832e1a34764c | 10 | 0.0151515152 | -4.752769 | loại |
| f74ace23-d852-4c56-b00b-0116094332f8 | 11 | 0.0151515152 | -4.990658 | loại |
| 23f78953-1949-4cac-a299-db28ed76b58f | 12 | 0.0149253731 | -5.070791 | loại |
| 50d95585-05f1-4387-9607-ba3bb0200967 | 13 | 0.0149253731 | -4.101382 | 3 |
| 55a0dd68-6bc6-48e7-aaed-cf5c6305e07c | 14 | 0.0147058824 | -4.661642 | loại |
| 6bd7ca79-328e-4fb5-a1f3-eec2b2adfa74 | 15 | 0.0147058824 | -5.090713 | loại |
| 550bd48f-cbf7-460e-806a-b2451f255f12 | 16 | 0.0144927536 | -4.720840 | loại |
| c8057a3a-89a6-42e3-8df6-c82c783ed04e | 17 | 0.0144927536 | -5.928151 | loại |
| 9f25715c-4700-45db-8313-05cdb9bfa1b2 | 18 | 0.0142857143 | -5.445208 | loại |
| ad4e9495-7f83-4398-ba7f-8903dde7570e | 19 | 0.0142857143 | -4.756829 | loại |
| 28ece3fc-4723-40cc-acf5-9b55b298047c | 20 | 0.0140845070 | -3.894888 | 2 |

## Phụ lục — Execution trace của evaluation harness

Synthetic unit fixture chỉ kiểm chứng phép tính, không phải kết quả chất lượng corpus thật.

### `metrics` (module-level)

Source [scripts/evaluate_retrieval.py:9–26](../../scripts/evaluate_retrieval.py#L9). FROM evaluate → CALL metrics → TO scripts/evaluate_retrieval.py → ACTION validate inputs/context, tạo metric/exclusion variables theo statements dưới → RETURN dict precision/recall/mrr/ndcg → BACK TO evaluate. Input: ranked UUID list, qrels grades, K. Exception ValueError cho malformed input/context; không tạo relevance labels.

```python
def metrics(ranking: list[str], qrels: dict[str, int], k: int) -> dict[str, float | None]:
    if len(set(ranking)) != len(ranking) or k < 1:
        raise ValueError("Unique ranked IDs and positive K required")
    if any(type(g) is not int or not 0 <= g <= 3 for g in qrels.values()):
        raise ValueError("Human grades must be integers 0-3")
    top = ranking[:k]
    if any(cid not in qrels for cid in top):
        raise ValueError("Unjudged candidates cannot silently become negatives")
    relevant = {cid for cid, grade in qrels.items() if grade > 0}
    hits = sum(cid in relevant for cid in top)
    dcg = sum((2 ** qrels[cid] - 1) / math.log2(i + 2) for i, cid in enumerate(top))
    ideal = sum((2**grade - 1) / math.log2(i + 2) for i, grade in enumerate(sorted(qrels.values(), reverse=True)[:k]))
    return {
        "precision": hits / k,
        "recall": hits / len(relevant) if relevant else None,
        "mrr": next((1 / i for i, cid in enumerate(top, 1) if cid in relevant), 0.0),
        "ndcg": dcg / ideal if ideal else None,
    }
```

### `evaluate` (module-level)

Source [scripts/evaluate_retrieval.py:29–84](../../scripts/evaluate_retrieval.py#L29). FROM CLI main trong scripts/evaluate_retrieval.py → CALL evaluate → TO scripts/evaluate_retrieval.py → ACTION validate inputs/context, tạo metric/exclusion variables theo statements dưới → RETURN result status/metrics/exclusions → BACK TO CLI main trong scripts/evaluate_retrieval.py. Input: dataset JSON + runs JSON + K. Exception ValueError cho malformed input/context; không tạo relevance labels.

```python
def evaluate(dataset: dict, runs: dict, k: int) -> dict:
    if dataset["corpus_manifest"] != runs["corpus_manifest"]:
        raise ValueError("Corpus manifest mismatch")
    rows, excluded = [], []
    modes = ("bm25", "dense", "hybrid", "hybrid_reranked")
    for query in dataset["queries"]:
        qid = query["id"]
        if query.get("judgment_status") != "VERIFIED" or not query.get("qrels"):
            excluded.append({"id": qid, "reason": "UNVERIFIED_JUDGMENTS"})
            continue
        if not dataset["corpus_manifest"] or str(dataset["corpus_manifest"]).startswith("UNPINNED"):
            raise ValueError("Verified judgments require a pinned corpus manifest")
        run = runs["queries"][qid]
        for field in ("text", "as_of_date", "allowed_usage_policies"):
            if query[field] != run[field]:
                raise ValueError("Query/filter context mismatch")
        if not query.get("annotator") or not query.get("judgment_scope"):
            raise ValueError("Human annotation provenance/scope required")
        if run.get("reranking_status") != "APPLIED":
            excluded.append({"id": qid, "reason": "NO_APPLIED_CROSS_ENCODER_RUN"})
            continue
        qrels = query["qrels"]
        pool = run["fixed_hybrid_pool"]
        if len(set(pool)) != len(pool) or not set(run["rankings"]["hybrid_reranked"]).issubset(pool):
            raise ValueError("Reranked output must be a subset of the fixed pool")
        try:
            per_mode = {mode: metrics(run["rankings"][mode], qrels, k) for mode in modes}
            # Fixed-pool comparison uses saved order, not an independently re-retrieved list.
            rrf_fixed = metrics(pool, qrels, k)
        except ValueError as error:
            if "Unjudged" not in str(error):
                raise
            excluded.append({"id": qid, "reason": "INCOMPLETE_JUDGMENTS"})
            continue
        relevant = {cid for cid, g in qrels.items() if g > 0}
        rows.append(
            {
                "id": qid,
                "metrics": per_mode,
                "fixed_pool_rrf": rrf_fixed,
                "candidate_coverage": len(set(pool) & relevant) / len(relevant) if relevant else None,
            }
        )
    aggregate = {}
    for mode in modes:
        aggregate[mode] = {}
        for metric in ("precision", "recall", "mrr", "ndcg"):
            values = [row["metrics"][mode][metric] for row in rows if row["metrics"][mode][metric] is not None]
            aggregate[mode][metric] = {"mean": sum(values) / len(values) if values else None, "count": len(values)}
    return {
        "status": "EVALUATED" if rows else "BLOCKED_NO_VALID_JUDGMENTS",
        "k": k,
        "queries": rows,
        "excluded": excluded,
        "aggregate": aggregate,
    }
```
