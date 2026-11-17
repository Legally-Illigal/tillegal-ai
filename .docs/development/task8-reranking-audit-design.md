# Task 8 — Stage 1: audit và thiết kế reranking

Ngày audit: **16/11/2026**. Trạng thái: **AUDITED / PROPOSED — chờ review**.

Phạm vi phiên này chỉ Phase A và B theo Execution Control của Task 8. Chưa triển khai reranking, chưa chạy inference, tests mới, live query hoặc đánh giá chất lượng. Không cài package, tải model, đọc `.env`, thay đổi database hay source. Báo cáo này đặt tại `.docs/development/` theo Task 5/6; chương học chỉ được tạo ở Stage 2 trong `docs/retrieval-learning/`.

## A1 — Kết luận audit hiện trạng

Reranker hiện chưa có implementation: `src/applications/tillegal/retrieval/reranker.py:1` chỉ chứa docstring. Search `rerank|CrossEncoder|ForSequenceClassification` trong source/scripts/configs không tìm thấy pipeline reranking khác. Không tái tạo BM25/Dense/RRF.

```text
scripts/search_legal_chunks.py::main
 → RetrievalRequest validation → _configured_service
 → retrieval_bootstrap.create_retrieval_service
 → RetrievalService.search(mode=hybrid)
 → search_hybrid
   → self.search(mode=bm25, top_k=bm25_candidates)
      → tokenize/dedup → sparse preflight → sparse RPC
      → chunk/source hydration → hash/policy/date validation → postflight
   → self.search(mode=dense, top_k=dense_candidates)
      → dense preflight → E5 query encoding → vector RPC
      → stored chunk integrity checks/source payload eligibility → postflight
   → closing index checks → reciprocal_rank_fusion
   → HybridRetrievalResponse → service → CLI JSON
```

Hai nhánh **tuần tự**, hydration nằm **trước fusion**. Không có hydration sau RRF, không fallback khi retrieval branch lỗi. RRF dedup theo canonical UUID, cùng UUID khác payload gây lỗi; khác UUID cùng text vẫn là hai chunks. Branch budgets mặc định 20/20, final request top_k mặc định 10, giới hạn 50. RRF hiện cắt theo **request.top_k**, nên xin 5 hiện chỉ nhận 5 fused candidates dù branches đã lấy 20/20.

Điểm chèn an toàn: **sau Hybrid thành công và có evidence đã hydrate/validate, trước trả kết quả cuối**. Service cần yêu cầu Hybrid trả pool lớn hơn final top_k, rồi mới rerank/select. Không chèn vào SQL, sparse/dense adapters hoặc trước integrity gates.

### Candidate và các ràng buộc phải tái sử dụng

`UnifiedEvidence` chứa retrieval_chunk_id/source_document_id/document_structure_id (UUID), chunk_key/content/content_sha256/hash_check, locators/offsets, chunk/source metadata, title/URL/source provenance, effective dates/policy, rank/raw_score/score_kind/retrieval_method. Object immutable và extra-forbid. Không tạo một chunk DTO thứ hai làm mất provenance.

Filters áp dụng tại sparse/vector SQL bằng explicit as_of_date và usage-policy allowlist; Python `_check_eligibility` kiểm tra lại inclusive dates/policy và reject inverted date range. NULL dates được cho qua với warning, không chứng minh hiệu lực. BM25 đọc source reader riêng; Dense dùng source JOIN trong RPC và đọc lại chunks để kiểm tra. Hash chỉ chứng minh content khớp stored digest, không chứng minh legal validity hay embedding freshness.

Index pre/post/closing observations là BEST_EFFORT, không transaction snapshot. Reranking thêm thời gian xử lý nên cần closing recheck sau inference, không được nâng consistency thành snapshot. SQL read infrastructure và source metadata không cần thay đổi.

### Các phát hiện ảnh hưởng thiết kế

1. `UnifiedEvidence.score_kind` hiện chỉ BM25/COSINE_SIMILARITY/RRF; method hybrid bắt buộc RRF. Không thể ghi CE logits vào raw_score rồi vẫn ghi score_kind=RRF.
2. `HybridRetrievalResponse.validate_fusion` kiểm tra IDs explanations theo evidence và tổng contributions bằng raw_score. Nó không yêu cầu final evidence sort giảm theo RRF score. Có thể giữ nguyên RRF scores, reorder explanations theo UUID và thêm CE score metadata riêng qua subclass opt-in.
3. Response model extra-forbid: consumer dùng base DTO không tự nhận field mới. Tắt reranking phải trả chính model/JSON cũ; consumer opt-in phải parse extension mới.
4. CLI có defaults bm25/top_k10; **giữ nguyên defaults cũ**. Hybrid/top5 là recipe thí nghiệm opt-in, không đổi defaults toàn ứng dụng.
5. File legal_retrieval tool chỉ docstring: chưa có bằng chứng product HTTP/agent route đã nối service. Scope Stage 2 là existing service/bootstrap/CLI.
6. CPU worker không bị kill khi async timeout; giữ lock tới khi thread hoàn tất, tránh inference chồng nhau. Không tạo queue vô hạn.

## A2 — Audit tài liệu và bằng chứng cũ

Đã đối chiếu README và ba chương 01/02/03 trong `docs/retrieval-learning/`: tiếng Việt, H1 tên chủ đề, phần A–F/G, giải thích mục đích/cơ chế/dữ liệu/implementation/liên kết; source relative path + exact line range; FROM → CALL → TO → ACTION → RETURN → BACK TO; ví dụ ILLUSTRATIVE, failure semantics, phụ lục code và 15 câu vấn đáp.

Chọn **03_HYBRID_RRF_TECHNICAL_WALKTHROUGH.md** làm khung chính vì reranking nối trực tiếp output của Hybrid. Dùng độ sâu tensor/inference của chương Dense cho đoạn Cross-Encoder. Stage 2 tạo `04_RERANKING_TECHNICAL_WALKTHROUGH.md`, cập nhật learning README bằng link mới; không viết chương mang tên implementation khi mới có proposal. Không ghi log tests thô vào chương học.

Các nguồn engineering: Task 5/6, dependency rules, documentation/project/architecture rules, known_issues, legacy-data-live-verification và retrieval-live-integration-verification. Không sửa các bản lịch sử. Có các khác biệt cần ghi nhận:

- Các chương học nói chưa kiểm tra live trong **phiên viết chương**, không phải bằng chứng repo chưa từng live. Addendum 14/11 ở [legacy-data-live-verification](legacy-data-live-verification.md) ghi technical E2E BM25/Dense/Hybrid pass; phiên Stage 1 này **không chạy lại**. Không dùng kết quả đó làm bằng chứng reranker.
- Task 6/known_issues và báo cáo live đầu tiên ghi runtime blocked; addendum mới hơn ghi technical E2E pass nhưng corpus E5 revision provenance và semantic quality còn thiếu. Phân biệt bằng chứng lịch sử và quan sát mới.
- Call chain Task 6 ghi sparse preflight trước tokenizer; source hiện tại `RetrievalService.search` thực hiện tokenization trước preflight. Các chương học hiện tại mô tả đúng thứ tự source.
- Local CE checkpoint hiện đã có; không được báo missing checkpoint chỉ từ giả định laptop chưa cài model.

## B1 — Chọn baseline model

Chọn **`cross-encoder/mmarco-mMiniLMv2-L12-H384-v1`**, revision local **`1427fd652930e4ba29e8149678df786c240d8825`**. Có sẵn config/tokenizer/safetensors trong cache chuẩn Hugging Face; chưa load weights vào model. Chỉ đọc JSON và header safetensors (không deserialize weights). Header có 117,641,603 tensor elements, file model 470,592,698 bytes, xấp xỉ 449 MiB trên đĩa. Không gọi số này là peak RAM hay count trainable parameters chính xác.

Local config xác nhận XLMRobertaForSequenceClassification, 12 layers, hidden384, 12 heads, 1 label, float32, tokenizer XLMRobertaTokenizer; tokenizer max length512 (max_position_embeddings514 không có nghĩa cho phép pair514). Default CE activation ghi Identity: ưu tiên raw single-logit scoring, không mặc định sigmoid/probability.

Lý do chọn: model nhỏ, pair scoring đúng vai trò, checkpoint local đã tồn tại, dùng thư viện đã có, phù hợp làm baseline CPU. Không khẳng định tốt nhất hoặc cải thiện chất lượng luật Việt Nam. [Model card](https://huggingface.co/cross-encoder/mmarco-mMiniLMv2-L12-H384-v1) mô tả training mMARCO và CrossEncoder/Transformers usage; [dataset card](https://huggingface.co/datasets/unicamp-dl/mmarco) liệt kê Vietnamese. Đây là cơ sở hỗ trợ tiếng Việt, không phải legal benchmark.

### So sánh các lựa chọn

| Tiêu chí | mMARCO MiniLMv2 — baseline | BGE reranker v2 m3 | Jina reranker v2 base multilingual |
|---|---|---|---|
| Checkpoint | cross-encoder/mmarco-mMiniLMv2-L12-H384-v1 | BAAI/bge-reranker-v2-m3 | jinaai/jina-reranker-v2-base-multilingual |
| Architecture | XLM-R sequence classifier, local12×384 | XLM-R classifier24×1024 | Custom XLM-R classifier12×768 |
| Ngôn ngữ | Multilingual, mMARCO có Vietnamese | Multilingual; cần đo Vietnamese legal | Multilingual; cần đo Vietnamese legal |
| Input/output | Query+passage pair → scalar logit | Pair → scalar score | Pair → score; custom long-text handling |
| Sequence | Local tokenizer512, đề xuất max512 tổng pair | Config8194 positional slots; context dài tốn CPU; cap512 cho trial nếu thử | Card1024, có sliding window |
| Size/resource | Local~470.6 MB weights; dự trù 1–3 GiB runtime, chưa đo | Repo model file~2.27 GB; CPU/RAM nặng hơn baseline, chưa đo | Ước tính~0.28B theo kiến trúc, FP32~1.1 GB weights; không đo peak RAM |
| CPU feasibility | Có thể thử batch4 trên16GB; chưa có latency | Có thể chạy CPU nhưng chi phí lớn hơn; chưa có latency | Có CPU path; custom code/deps cần thử riêng |
| Dependencies | torch/transformers qua sentence-transformers đã có | transformers/torch hoặc FlagEmbedding (không cần cài cho baseline) | transformers, custom code, einops theo card |
| License | Apache-2.0 | Apache-2.0 | CC-BY-NC-4.0 |
| Hạn chế | Training web/machine translations; 512 tokens có thể mất ngoại lệ cuối chunk | Context dài không đồng nghĩa hiểu luật; memory/latency | Custom code và license khác, thêm độ phức tạp tích hợp |

BGE architecture được xác nhận từ [config](https://huggingface.co/BAAI/bge-reranker-v2-m3/raw/main/config.json), size từ [files](https://huggingface.co/BAAI/bge-reranker-v2-m3/tree/main), scope/license từ [card](https://huggingface.co/BAAI/bge-reranker-v2-m3). Jina từ [config](https://huggingface.co/jinaai/jina-reranker-v2-base-multilingual/raw/main/config.json) và [card](https://huggingface.co/jinaai/jina-reranker-v2-base-multilingual). Resource estimates là dự trù kỹ thuật, không measured results. Với memory budget chung còn E5/Python/OS, chỉ phép đo Stage 2 mới xác nhận phù hợp.

Generative reranker cần sinh token, parse output và kiểm tra missing/duplicate IDs, thường thêm memory/latency; không cần thiết cho pair→scalar baseline trên CPU U-series. Không dùng API cloud. Giữ mô hình generative là hướng nghiên cứu sau, không thêm dependency/runtime riêng bây giờ.

Venv có sẵn (đọc package metadata, không import/load model): sentence-transformers5.7.0, transformers5.22.2, torch2.15.0, supabase2.33.0, pydantic2.14.1. `pyproject.toml` cho sentence-transformers>=3.3,<6. API tương thích cụ thể phải kiểm tra bằng smoke test local-only ở Stage 2; không tuyên bố config cũ chắc load được trên version mới.

## B2 — Kiến trúc đề xuất, chưa triển khai

Giữ một RetrievalService. Thêm pure ranking function ở placeholder reranker.py; concrete local inference adapter ở integrations, small Protocol ở ports. Application không import torch/transformers trực tiếp.

```text
service.search(original request: hybrid, top_k=5)
 → [enabled only] internal request top_k=max(5,pool20)
 → existing search_hybrid(internal request), branches budgets20/20 unchanged
 → validated Hybrid response with <=20 fused evidence
 → pair scorer(query.strip(), tuple(content))
 → validated finite CE scores, fixed positional mapping back to UUID
 → sort (-ce_score, original_rrf_rank, canonical_uuid), select original top_k
 → recheck observed index identities; integrity checks still mandatory
 → RerankedHybridRetrievalResponse with original request fields
```

`max(final top_k, configured pool)` <=50 bảo đảm không tự hạ request khi người dùng xin trên20. Branch budgets vẫn là cấu hình độc lập: pool40 nhưng branches chỉ20/20 có thể thiếu ứng viên do overlap; ghi actual count, không tự vượt budgets/filter hoặc refill. Không rerank BM25/Dense khi config enabled: trả kết quả mode cũ, ghi rõ scope HYBRID_ONLY trong help/docs; CLI explicit --rerank với non-hybrid bị reject trước DB để không gây nhầm.

### Contract đề xuất

Protocol `PairScorer.score_pairs(query: str, passages: tuple[str,...]) -> tuple[float,...]` async; kết quả vị trí i ứng với passage i. Adapter không trả evidence/ID mới và không có quyền sửa source metadata. Domain pure function nhận original tuple UnifiedEvidence, scores, final_k → selection + explanation. Scores phải đúng count, scalar numeric non-bool, finite; reject shape[N,2] hoặc labels!=1, không tự chọn class.

Model `RerankConfig` immutable/extra-forbid. Metadata chứa enabled/status (`APPLIED`, `FALLBACK`, `SKIPPED_EMPTY`), model name/revision, pool requested/actual, timings/load-cold flag, max_length/batch, per-candidate UUID/original RRF rank/RRF score/CE score nullable/final rank nullable, safe failure code và truncation counts. Chỉ giữ scores/IDs trong run artifact, không log full legal text hoặc query tùy tiện.

**Không cần đổi base UnifiedEvidence:** final `rank` là vị trí CE, `raw_score` và `score_kind=RRF` vẫn giữ điểm retrieval, method=hybrid. CE score chỉ nằm ở `reranking` metadata; consumer không sort lại theo raw_score khi enabled. Đặt tên `cross_encoder_score` rõ ràng. Score RRF có thể không giảm dần trong final list: đây là thay đổi semantics của **opt-in extension**, phải test/document.

Tạo subclass **`RerankedHybridRetrievalResponse(HybridRetrievalResponse)`**, thêm required reranking metadata; base class validation RRF vẫn chạy. Reorder/filter `fusion.ranking` theo final evidence IDs, không mất contributions. Lưu original RRF ranks cho **toàn pool** trong reranking metadata; fusion.ranking vẫn giải thích điểm RRF từng final UUID. Validator mới so UUID set/subset, final ranks/order/CE scores và payload preservation. Build bằng `model_validate` từ payload đầy đủ, không dùng model_copy để bỏ qua validators.

Disabled trả đúng class/schema cũ, không thêm reranking=null. Enabled client phải chọn DTO subclass; base extra-forbid không parse được extension. Không sửa schema_version1 của response cũ; extension document riêng bằng metadata version1 và CLI flag opt-in. Nếu consumer đòi raw_score là final rank score, đó là contract v2 riêng cần review, không âm thầm thay nghĩa RRF.

### Load, tokenization và inference

Đề xuất concrete adapter dùng `AutoTokenizer` + `AutoModelForSequenceClassification` từ dependencies đã có. Đây vẫn là Cross-Encoder, không bắt buộc class tên CrossEncoder. Lý do chọn Auto classes: điều khiển `truncation='only_second'` và logits rõ ràng, không phụ thuộc default truncation/activation của CrossEncoder.predict giữa các phiên bản.

Loader nhận explicit local path, local_files_only=True và trust_remote_code=False cho tokenizer/model; validate architecture/num_labels1 và tokenizer max length. CPU float32, eval + torch.inference_mode, lazy load/cache một model/adapter; record revision và file hash trong manifest Stage 2. Không encode E5 prefix ở đây; pair gồm query nguyên nghĩa và content chunk, không chèn title/source metadata thêm lần nữa. Text evidence không bị sửa dù model input bị truncate.

Tạo pairs theo đúng RRF order; với mỗi batch, tokenizer(query_list, passage_list,padding=True,truncation='only_second',max_length=512,return_tensors='pt'). Query quá dài đến mức không còn chỗ cho passage thì classified QUERY_TOO_LONG và fallback, không âm thầm cắt câu hỏi. Đếm query/passage pair lengths để record truncation flags. Cắt **đuôi passage** sau khi tính cả special tokens, không theo số từ tiếng Việt. Query có thể <=10.000 ký tự mà vẫn vượt pair budget.

Input IDs/mask [B,L] → sequence classifier contextual states [B,L,384] → classification head → logits [B,1] → squeeze đúng label axis → [B] → tuple floats theo original order. Không dùng E5 sentence mean pooling hoặc cosine trong reranker. Không sigmoid mặc định; logit không calibrated probability. Batch padding chỉ tới longest pair của batch, tổng pair<=512; batch4 khởi đầu để giới hạn activation memory. CPU latency phải đo cold/warm riêng.

Async offload qua worker + nonblocking threading lock giống pattern E5: lock bao cả load/score, giữ đến khi worker thực sự xong. Busy thì fallback có warning, không enqueue vô hạn. Synchronous worker vẫn có thể chạy sau deadline; không hứa timeout kill inference. Không hỗ trợ GPU trong baseline; device literal cpu, không thêm lựa chọn chưa test.

### Config đề xuất (tất cả là mới, chưa có trong CLI hiện tại)

| Field/flag đề xuất | Default / validation | Ý nghĩa |
|---|---|---|
| enabled / --rerank | false | Disabled giữ behavior/schema cũ |
| model_path / --rerank-model-path | None, cần path nếu enabled | Explicit provisioned folder; path không tồn tại lúc chạy → warning fallback |
| candidate_pool / --rerank-candidates |20, strict int1–50| Internal Hybrid top_k=max(pool,request.top_k) |
| batch_size / --rerank-batch-size |4, strict int1–16| CPU microbatch |
| max_length / --rerank-max-length |512, strict int32–512| Tổng pair gồm special tokens |
| inference_timeout_seconds |10, finite>0| Budget chờ reranker gồm cold load |
| total_timeout_seconds |40, finite>0| Enabled pipeline tổng; deadline còn lại ràng buộc từng wait |
| final evidence | request.top_k | Recipe explicit --mode hybrid --top-k5; không đổi default10 cũ |

Truyền optional config/scorer qua constructor/bootstrap keyword-only như HybridConfig; không thêm global env/config app nếu CLI/DI đủ. `core/config.py` chỉ tiếp tục cấp Supabase settings. Config sai kiểu/range bị reject trước DB. Thiếu model_path khi enabled là lỗi cấu hình CLI; đường dẫn được chỉ định nhưng chưa provision/load lỗi là operational failure có fallback để test case phân biệt rõ.

### Fallback và integrity policy

| Trường hợp | Hành vi đề xuất |
|---|---|
| Disabled | Bỏ qua stage hoàn toàn, không expand pool, không load model |
| Hybrid FAILED | Truyền đúng error hiện có, không gọi scorer, không biến thành success |
| Empty/NO_MATCH | Không load model, trả NO_MATCH + SKIPPED_EMPTY extension nếu enabled |
| Một candidate | Vẫn score nếu enabled để có evidence inference, selection giữ UUID |
| N<final_k | Trả tối đa N, rank liên tục, không padding/retrieve lại |
| Missing/load/tokenization/inference/busy/timeout failure | Giữ RRF original order của pool, cắt final_k; warning RERANKING_FALLBACK + safe code, metadata FALLBACK; không exception text/path dump |
| Wrong score count, NaN/Inf/bool/non-scalar scores | Reject **toàn score batch**, fallback RRF; không trộn partial CE và RRF |
| Long passage | Truncate only passage + metadata và warning RERANKING_TRUNCATED; không sửa content evidence |
| Duplicate UUID, thiếu/blank text, bad hash, payload/identity conflict | Fail INCONSISTENT_EVIDENCE; **không fallback để che lỗi integrity** |
| Final closing index read fail/change | FAILED theo taxonomy hiện có; không fallback dùng corpus observation đã thay đổi |
| External cancellation | Propagate cancellation; không bắt BaseException để giả thành fallback |

Fallback chỉ là CE operational error sau Hybrid đã valid, không nới STRICT policy của BM25/Dense/RRF. Với fallback cũng cắt/re-rank số thứ tự 1..K, filter fusion explanations/warnings theo final IDs; giữ global warnings. CE không quyết định policy, hiệu lực, source attribution. Pure function không bao giờ sửa content/title/source/hash/metadata. Final validator so payload toàn bộ trừ rank với candidate gốc.

Budget: disabled vẫn30s hiện có. Enabled total40s mới chỉ áp dụng opt-in, Hybrid giữ<=30s và remaining deadline; CE wait<=min(10s,remaining), sau đó closing checks trong remaining budget. Nếu CE hết budget nhưng còn thời gian closing check thì fallback; total deadline/closing check không đủ → FAILED TIMEOUT, không hứa fallback thành công vượt deadline. Cần tests riêng ở cả ranh giới này.

## B3 — Kế hoạch thay đổi Stage 2, chưa thực hiện

| File dự kiến | Thay đổi nhỏ nhất |
|---|---|
| src/applications/tillegal/retrieval/reranker.py | Pure ranking/selection, deterministic tie, integrity guards; không import model SDK |
| src/applications/tillegal/retrieval/reranking_models.py (mới) | Config, diagnostics và opt-in response subclass |
| src/applications/tillegal/retrieval/ports.py | PairScorer protocol |
| src/integrations/embeddings/cross_encoder_reranker.py (mới) | Local CPU scoring/load/lock/tokenization/logits |
| src/application/services/reranking.py (mới) | Post-Hybrid coordination/fallback, response assembly; không service thứ hai |
| src/application/services/retrieval_service.py | Optional injection và HYBRID opt-in dispatch; reuse search_hybrid, không rewrite branches |
| src/retrieval_bootstrap.py | Compose scorer khi enabled |
| scripts/search_legal_chunks.py | Explicit flags/validation và help score semantics |
| tests/unit/applications/tillegal/retrieval/ | Deterministic scorer/ranking/service/CLI/contracts tests |
| .docs/development/task8-reranking-verification.md (mới sau implementation) | Exact commands, actual test/live results và blockers |
| docs/retrieval-learning/04_RERANKING_TECHNICAL_WALKTHROUGH.md | Chapter sau implementation: source AST ranges, data transforms, real/illustrative distinction,15 câu vấn đáp |
| docs/retrieval-learning/README.md | Link chương04 ở Stage 2; giữ nguyên ba chương cũ |

Không đổi migrations/SQL/Supabase/crawler/ingestion/Agents/answer generation. Chưa có file mới trong danh sách này được triển khai tại Stage 1.

## B4 — Verification và evaluation dự kiến

Unit cases: empty,1/many, score-position mapping, descending/ties, final_k, finite/count/type/shape, missing text, duplicate IDs, hash/metadata preservation, load/tokenizer/inference failures, fallback warning/order, disabled no-load/no-expansion, non-Hybrid unchanged, model busy/cancellation/thread lifetime, request validation và extended response roundtrip/tampering. Dùng fake scorer; model loader tests monkeypatch Auto classes, không download.

Integration boundary dùng real RetrievalService + existing fake repositories từ test_hybrid_service.py, đổi candidate budgets độc lập final_k, assert exact UUID→content/source/hash mapping trước/sau rerank, filters/index failures không bị CE che; total/branch/CE timeout tách biệt. Existing regression command dự kiến từ repo root: `.venv/Scripts/python.exe -m pytest tests/unit/applications/tillegal/retrieval tests/unit/integrations/database/test_repositories.py -q`. **Chưa chạy trong Stage 1**; mở rộng suite/lint sau thay đổi theo failures và scope, không ghi lại counts lịch sử như kết quả mới.

Live Stage 2: reuse read-only verifier patterns đã có, xác nhận explicit local E5/CE revisions và existing Supabase target/read permissions, không chạy startup workers/migration. Đo real Vietnamese query với same date/policy, RRF pool20 → CPU scores → final5, lưu UUID/source metadata subset/original/new ranks/actual scores/counts/cold-warm timings/warnings trong artifact riêng. Không dùng fake scores thay live evidence. `.env` tồn tại không có nghĩa process đã configured; Stage 1 chưa kiểm tra kết nối nên không kết luận DB hiện usable hay blocked.

Evaluation: chưa tìm thấy labeled legal retrieval dataset trong learning materials/evaluation skeleton được khảo sát; Stage 2 phải kiểm tra thêm dữ liệu trước khi kết luận hoàn toàn không có. Format đề xuất mỗi query có id/text/as_of_date/policies, corpus manifest/index observations, qrels [{chunk_uuid,content_sha256,grade0..3,annotator,reason}], judgment_status và split. Grade>0 là relevant; chưa annotate phải null/unverified, không gán0. Seed câu hỏi dân sự/lao động/đất đai/hiệu lực chỉ là unverified samples.

So bốn cấu hình BM25/Dense/Hybrid/Hybrid+CE cùng query/date/policy/K và corpus manifest; riêng RRF-vs-CE dùng **cùng frozen pool20**, không gọi candidate generation hai lần rồi nói cùng pool. Recall@K=found relevant/total relevant; Precision@K=relevant/K (quy ước denominator K kể cả trả ít); MRR@K=1/rank first relevant,0 nếu không có; nDCG dùng gain2^grade−1/log2(rank+1), ideal từ qrels; IDCG0 ghi undefined/exclude có báo count. Candidate coverage= relevant trong pool/total relevant. Unjudged không tự coi irrelevant; báo judgment coverage, dùng tập fully judged để so chính thức. Report macro means/eligible query counts, actual returned count, p50/p95 khi đủ samples, cold/warm latency riêng.

Error analysis theo query: relevant absent pool → candidate generation issue; present nhưng CE hạ → reranking issue; pháp luật gần chủ đề khác điều kiện/hiệu lực, truncation mất ngoại lệ, BM25-Dense disagreement và fallback. Không fabricate cải thiện/metrics. Giữ optional default=false đến khi labels+chất lượng+CPU latency chứng minh lợi ích.

## B5 — Kết quả và điểm review

Kiểm tra cuối Stage1: SHA-256 trước/sau của **351 files** trong source/scripts/tests/learning docs/agent rules không thay đổi; không thêm file ở các vùng đó. Báo cáo này là file duy nhất được tạo. Đã kiểm tra **46 local Markdown links**, các line anchors và37 inventory ranges bằng Python AST, không phát hiện lỗi. Kiểm tra này không phải unit/integration test của reranker. Không có test count mới hoặc kết quả inference/live/quality trong phiên này.

| Status | Stage 1 |
|---|---|
| AUDITED | Source/documents/model config/local cache đã kiểm tra |
| DESIGNED | PROPOSED: điểm chèn, model, contract, config, fallback, tests/evaluation |
| IMPLEMENTED / UNIT TESTED / INTEGRATION TESTED | Chưa thực hiện Task8 |
| LIVE VERIFIED / EVALUATED | Chưa thực hiện Task8; prior retrieval E2E không thay bằng chứng reranker |
| BLOCKED | Stage2 chưa được ủy quyền; còn runtime compatibility/latency/labels/E5 provenance cần xác minh |

Đề xuất review bốn quyết định: local MiniLMv2 revision đã nêu; post-Hybrid pool20→final request.top_k; giữ RRF raw_score và thêm CE score qua opt-in extension; fallback chỉ lỗi operational CE, integrity/index/retrieval lỗi vẫn fail. Theo Execution Control, **dừng sau Phase B**; không coi proposal này là kiến trúc đã phê duyệt.

## Phụ lục A — Inventory source đã xác minh

Path relative với repo; range1-based lấy từ AST hiện tại. Mỗi output quay về caller trước khi chuyển downstream như call graph A1. Class/function ghi chính xác; module-level ghi rõ. Đây là source hiện tại, không phải tên function đề xuất Stage2.

| File / class.function / lines | Trách nhiệm và dependencies | Input → output | Caller → callee |
|---|---|---|---|
| [scripts/search_legal_chunks.py:58–132](../../scripts/search_legal_chunks.py#L58), `main` | validate/dispatch/serialize; argparse/Pydantic/asyncio | CLI argv → Request→JSON/exit status | Process → _configured_service; service.search |
| [scripts/search_legal_chunks.py:28–42](../../scripts/search_legal_chunks.py#L28), `_configured_service` | load process configuration; existing SupabaseSettings | path/config → RetrievalService | main → load_settings; create_retrieval_service |
| [src/retrieval_bootstrap.py:21–59](../../src/retrieval_bootstrap.py#L21), `create_retrieval_service` | DI; supabase SDK/local adapters | settings/path/HybridConfig → service | _configured_service → repositories/E5QueryEncoder/RetrievalService |
| [src/applications/tillegal/retrieval/contracts.py:23–44](../../src/applications/tillegal/retrieval/contracts.py#L23), `RetrievalRequest` | request validation; Pydantic | query/mode/top_k/date/policies → validated request | CLI/main, service.search → nonblank_query; policies |
| [src/applications/tillegal/retrieval/contracts.py:65–110](../../src/applications/tillegal/retrieval/contracts.py#L65), `UnifiedEvidence` | identity/provenance/score contract; Pydantic | chunk/source/rank/score fields → validated immutable evidence | service hydration; RRF → validate_semantics |
| [src/applications/tillegal/retrieval/contracts.py:113–149](../../src/applications/tillegal/retrieval/contracts.py#L113), `RetrievalResponse` | status/unique IDs/consecutive rank; Pydantic | request context/evidence/error → response | service.search → validate_outcome |
| [src/application/services/retrieval_service.py:185–284](../../src/application/services/retrieval_service.py#L185), `RetrievalService.search` | dispatch/error/deadline; asyncio/Pydantic | RetrievalRequest → RetrievalResponse/HybridResponse | CLI or search_hybrid run_branch → search_hybrid; branch helpers; repositories |
| [src/application/services/retrieval_service.py:286–296](../../src/application/services/retrieval_service.py#L286), `RetrievalService._prepare_sparse_terms` | dedup/empty check; tokenizer | query str → tuple terms | search bm25 → injected tokenize_sparse_text |
| [src/application/services/vbpl_markdown_indexing_service.py:39–41](../../src/application/services/vbpl_markdown_indexing_service.py#L39), `tokenize_sparse_text` | NFC/lower/regex Unicode | str → tuple tokens | _prepare_sparse_terms; upstream → unicodedata.normalize; re.findall |
| [src/application/services/retrieval_service.py:471–512](../../src/application/services/retrieval_service.py#L471), `RetrievalService._read_and_validate_index` | readiness/tokenizer/statistics; Pydantic | configured index name → _SparseIndex | search bm25 → SparseIndexRepository.get_index |
| [src/application/services/retrieval_service.py:298–322](../../src/application/services/retrieval_service.py#L298), `RetrievalService._search_sparse` | hit validation/count/order; TypeAdapter | request+terms → tuple SparseSearchHit | search bm25 → SparseRetrievalRepository.search |
| [src/integrations/database/repositories/sparse_retrieval_repository.py:25–40](../../src/integrations/database/repositories/sparse_retrieval_repository.py#L25), `SparseRetrievalRepository.search` | payload+RPC+parse; Supabase/Pydantic | SparseSearchRequest → tuple SparseSearchHit | _search_sparse → call_rpc(search_sparse_legal_chunks) |
| [src/applications/tillegal/retrieval/document_models.py:88–115](../../src/applications/tillegal/retrieval/document_models.py#L88), `SparseSearchRequest` | dedup explicit filters; Pydantic | terms/index/filters → validated request | _search_sparse → field validators |
| [src/applications/tillegal/retrieval/document_models.py:118–124](../../src/applications/tillegal/retrieval/document_models.py#L118), `SparseSearchHit` | finite score/UUID contract | UUID+score → typed hit | sparse adapter/service → Pydantic validation |
| [src/application/services/retrieval_service.py:324–388](../../src/application/services/retrieval_service.py#L324), `RetrievalService._hydrate_sparse_hits` | batch/memoize/map original rank; UUID/Pydantic | hits/request → tuple UnifiedEvidence | search bm25 → get_by_ids; sources.get; _check_eligibility; _make_evidence |
| [src/application/services/retrieval_service.py:391–414](../../src/application/services/retrieval_service.py#L391), `RetrievalService._check_eligibility` | date/policy/inverted range; datetime | source/request → None or error | sparse/dense hydration → _failure |
| [src/application/services/retrieval_service.py:417–446](../../src/application/services/retrieval_service.py#L417), `RetrievalService._make_evidence` | stored content hash and payload map; hashlib | chunk/source/hit/rank → UnifiedEvidence | _hydrate_sparse_hits → sha256; UnifiedEvidence |
| [src/application/services/retrieval_service.py:534–577](../../src/application/services/retrieval_service.py#L534), `RetrievalService._read_dense_index` | E5 contract/readiness; Pydantic | configured index name → _DenseIndex | search dense → DenseIndexRepository.get_index |
| [src/integrations/embeddings/e5_query_encoder.py:40–44](../../src/integrations/embeddings/e5_query_encoder.py#L40), `E5QueryEncoder.encode_query` | local CPU query embedding; SentenceTransformer | query → tuple float384 | search dense → to_thread(_encode) |
| [src/applications/tillegal/retrieval/document_models.py:12–53](../../src/applications/tillegal/retrieval/document_models.py#L12), `VectorSearchRequest` | dimension/finite/nonzero/filter; Pydantic | vector/index/filters → typed request | search dense → field validators |
| [src/applications/tillegal/retrieval/document_models.py:56–85](../../src/applications/tillegal/retrieval/document_models.py#L56), `RetrievedEvidence` | UUID/source/content/similarity contract | joined RPC fields → typed evidence hit | vector repository → Pydantic validation |
| [src/integrations/database/repositories/supabase_vector_repository.py:25–65](../../src/integrations/database/repositories/supabase_vector_repository.py#L25), `SupabaseVectorRepository.search` | HTTP errors/log/parse; supabase/httpx | VectorSearchRequest → tuple RetrievedEvidence | search dense → to_thread(_execute_search); TypeAdapter |
| [src/integrations/database/repositories/supabase_vector_repository.py:67–78](../../src/integrations/database/repositories/supabase_vector_repository.py#L67), `SupabaseVectorRepository._execute_search` | pgvector payload+RPC; supabase | VectorSearchRequest → response.data | vector.search worker → _format_vector; rpc(search_legal_chunks) |
| [src/application/services/retrieval_service.py:598–703](../../src/application/services/retrieval_service.py#L598), `RetrievalService._map_dense_evidence` | verify payload/hash/rank/index; hashlib/Pydantic | hits/request/index → tuple UnifiedEvidence | search dense → chunks.get_by_ids; _check_eligibility; UnifiedEvidence |
| [src/application/services/retrieval_service.py:514–532](../../src/application/services/retrieval_service.py#L514), `RetrievalService._check_index_unchanged` | metadata equality; _SparseIndex | before _SparseIndex → None or error | search bm25 → indexes.get_index |
| [src/application/services/retrieval_service.py:579–596](../../src/application/services/retrieval_service.py#L579), `RetrievalService._check_dense_index_unchanged` | metadata equality; _DenseIndex | before _DenseIndex → None or error | search dense → dense_indexes.get_index |
| [src/application/services/hybrid_retrieval.py:85–196](../../src/application/services/hybrid_retrieval.py#L85), `search_hybrid` | sequential strict coordinator; asyncio | request/run_branch/readers/config/timeout → HybridRetrievalResponse | RetrievalService.search → run_branch; _validate_context; closing check; RRF |
| [src/application/services/hybrid_retrieval.py:40–50](../../src/application/services/hybrid_retrieval.py#L40), `_validate_context` | prevent cross-query/filter context merge | branch response/expected request/index → None or error | search_hybrid → _invalid_context |
| [src/application/services/hybrid_retrieval.py:53–82](../../src/application/services/hybrid_retrieval.py#L53), `_check_closing_index` | extend observations across both branches; no snapshot | reader/observed IndexIdentity → None or error | search_hybrid → reader.get_index; IndexIdentity |
| [src/applications/tillegal/retrieval/rank_fusion.py:33–95](../../src/applications/tillegal/retrieval/rank_fusion.py#L33), `reciprocal_rank_fusion` | RRF/UUID dedup/tie/conflicts; hashlib | two evidence tuples/k/top_k → FusionResult | search_hybrid → UnifiedEvidence; sha256; RankContribution; FusedRank |
| [src/applications/tillegal/retrieval/hybrid_models.py:13–18](../../src/applications/tillegal/retrieval/hybrid_models.py#L13), `HybridConfig` | independent candidate budgets | k/branch budgets → validated config | CLI/bootstrap/service → Pydantic fields |
| [src/applications/tillegal/retrieval/hybrid_models.py:92–118](../../src/applications/tillegal/retrieval/hybrid_models.py#L92), `HybridRetrievalResponse.validate_fusion` | RRF explanations vs evidence/budgets | self → self or ValidationError | Pydantic response construction → math.isclose |
| [src/integrations/database/repositories/chunk_repository.py:19–30](../../src/integrations/database/repositories/chunk_repository.py#L19), `ChunkRepository.get_by_ids` | batch canonical read; typed adapter | UUID tuple → tuple chunk dicts | both hydrations → call_rpc(get_retrieval_chunks) |
| [src/integrations/database/repositories/source_document_repository.py:30–40](../../src/integrations/database/repositories/source_document_repository.py#L30), `SourceDocumentRepository.get` | source metadata read; base RPC | source UUID → dict/None | sparse hydration → call_rpc(get_source_document) |
| [src/integrations/database/repositories/sparse_index_repository.py:71–77](../../src/integrations/database/repositories/sparse_index_repository.py#L71), `SparseIndexRepository.get_index` | sparse metadata read | index name → dict/None | service/closing check → call_rpc(get_sparse_index) |
| [src/integrations/database/repositories/dense_index_repository.py:68–74](../../src/integrations/database/repositories/dense_index_repository.py#L68), `DenseIndexRepository.get_index` | dense metadata read | index name → dict/None | service/closing check → call_rpc(get_dense_index) |
| [src/integrations/database/repositories/rpc.py:21–27](../../src/integrations/database/repositories/rpc.py#L21), `SupabaseRpcRepository.call_rpc` | SDK async boundary/errors; supabase/httpx | function name/payload → response.data | read repositories → to_thread(client.rpc.execute) |

### Existing test inventory (source inspected, không chạy lại ở Stage1)

- [test_cli.py](../../tests/unit/applications/tillegal/retrieval/test_cli.py): `test_invalid_arguments_before_dependencies` (43–47), `test_cli_fake_service_json_and_request` (50–56), `test_dense_without_configuration` (59–61), `test_configuration_error_never_echoes_exception` (64–70), `test_help_does_not_construct_dependencies` (73–75), `test_bootstrap_real_read_adapters_fake_rpc_without_model_or_worker` (78–117), `test_default_configuration_does_not_read_dotenv` (120–131), `test_service_failure_exit_codes` (143–151), `test_cold_bootstrap_import_never_imports_models_or_starts_network` (154–175), `test_dense_cli_bootstrap_existing_vector_adapter_fake_rpc` (178–210), `test_bm25_cli_ignores_dense_path_and_does_not_enable_encoder` (213–225), `test_invalid_hybrid_config_before_dependencies` (229–231), `test_hybrid_requires_local_model_path` (234–236), `test_hybrid_cli_configuration_and_existing_read_adapters` (239–309).
- [test_contracts.py](../../tests/unit/applications/tillegal/retrieval/test_contracts.py): `test_invalid_request` (99–101), `test_required_date_and_policies` (104–109), `test_query_preserved_policies_deduplicated_and_serialization` (112–118), `test_old_sparse_imports_are_same_classes` (121–128), `test_response_invariants` (146–148), `test_success_and_failure_roundtrip` (151–160), `test_score_kinds_cannot_be_mixed` (163–166).
- [test_dense_service.py](../../tests/unit/applications/tillegal/retrieval/test_dense_service.py): `test_dense_mapping_integrity_ranking_and_filters` (106–120), `test_dense_no_match_does_not_fetch_chunks` (123–126), `test_dense_preflight_failure_before_encoder` (141–145), `test_dense_missing_index` (148–151), `test_bad_vector_blocks_rpc` (155–158), `test_model_failure_is_classified_without_raw_message` (161–172), `test_invalid_dense_hits` (185–189), `test_dense_source_filters_and_metadata` (196–198), `test_dense_stored_integrity` (210–212), `test_dense_postflight_change_and_network_error` (215–221).
- [test_hybrid_service.py](../../tests/unit/applications/tillegal/retrieval/test_hybrid_service.py): `test_real_service_branches_fuse_with_metadata_and_independent_candidate_limits` (76–93), `test_empty_is_valid_not_a_backend_failure` (99–106), `test_backend_failure_never_becomes_degraded_success` (110–121), `test_bad_embedding_stops_hybrid_before_vector_rpc` (124–128), `test_missing_local_checkpoint_is_not_no_match` (131–137), `test_integrity_failure_never_reaches_fusion` (140–145), `test_same_chunk_conflicting_source_metadata_blocks_fusion` (148–153), `test_closing_index_check_covers_interval_between_branches` (156–167), `test_hybrid_index_unavailable_stops_dense` (170–173), `test_outer_timeout_does_not_return_first_branch_hits` (176–184), `test_single_backend_payloads_keep_original_shape` (187–192), `test_closing_read_failure_is_not_no_match` (195–205), `test_branch_context_mismatch_is_an_integrity_failure` (208–231), `test_source_filter_failure_is_not_hidden_by_other_backend` (234–239), `test_hybrid_explanation_contract_rejects_tampering` (243–257).
- [test_query_encoder.py](../../tests/unit/applications/tillegal/retrieval/test_query_encoder.py): `test_query_prefix_local_only_lazy_load_and_normalization` (49–65), `test_token_limit_and_empty_input` (68–76), `test_malformed_embedding` (80–85), `test_load_failure_redacted` (88–96), `test_missing_model_does_not_import` (99–106), `test_busy_encoder_does_not_start_parallel_work` (109–117), `test_new_dimension_method_and_exact_token_limit` (120–126), `test_incompatible_model_config` (130–137), `test_cancelled_awaiter_keeps_worker_exclusive` (140–169).
- [test_rank_fusion.py](../../tests/unit/applications/tillegal/retrieval/test_rank_fusion.py): `test_hand_calculated_rrf_and_original_scores` (27–41), `test_tie_breaking_uuid_not_input_order_or_raw_score` (44–52), `test_different_ids_same_text_are_not_merged` (55–57), `test_one_branch_empty_is_valid` (61–65), `test_both_empty` (68–69), `test_invalid_branch_candidates_fail` (73–89), `test_same_uuid_cross_backend_conflicts_fail` (102–105), `test_config_validation` (112–114), `test_pure_function_validates_limits` (118–120).
- [test_service.py](../../tests/unit/applications/tillegal/retrieval/test_service.py): `test_index_failures` (90–95), `test_dense_not_configured_without_reads` (98–102), `test_invalid_request_makes_no_calls` (105–109), `test_real_indexing_tokenizer_and_parameter_mapping` (120–131), `test_empty_terms_without_db_reads` (134–139), `test_sparse_hits_keep_original_order_and_scores` (142–149), `test_sparse_failure_is_not_no_match` (152–156), `test_hydration_preserves_ranking_hash_and_reads_source_once` (218–229), `test_bad_chunks_fail_without_partial_evidence` (244–249), `test_bad_sources_fail` (264–268), `test_missing_source` (271–274), `test_duplicate_hits_block_hydration` (277–281), `test_dates_are_inclusive_and_nullable` (284–290), `test_postflight_change_discards_hydrated_results` (293–297), `test_timeout_is_not_no_match` (300–308), `test_invalid_repository_schema_cause_is_classified` (311–319).
- [test_supabase_vector_repository.py](../../tests/unit/applications/tillegal/retrieval/test_supabase_vector_repository.py): `test_search_calls_rpc_with_embedding_and_explicit_allowlists` (86–99), `test_search_logs_correlated_result_metadata` (102–114), `test_search_request_rejects_invalid_values` (126–128), `test_search_maps_supabase_transport_failures` (131–137), `test_search_rejects_invalid_rpc_response_contract` (140–145).
