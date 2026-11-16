# Task8 — Stage2 implementation và verification

Ngày16/11/2026. Baseline: [Stage1 đã được user duyệt](task8-reranking-audit-design.md). Phạm vi main repo; không đổi crawler/SQL/schema/indexes/Agents. Không cài dependencies hoặc download models.

## Kết quả theo mức bằng chứng

| Status | Kết quả / scope |
|---|---|
| IMPLEMENTED | Optional post-Hybrid local pair scoring, pool expansion enabled-only, CE scores riêng, immutable evidence selection, explicit fallback, closing checks, DI/CLI |
| UNIT TESTED | Full unit suite **386 passed**, có tests mới và existing regression |
| INTEGRATION TESTED | Real RetrievalService→existing Hybrid→fake scorer→final subclass; metadata/hash/ID/RRF preservation, context/filter/index/error guards; tests nằm trong unit suite theo cấu trúc repo |
| LIVE VERIFIED | Hai successful actual Supabase+local model service runs:20 candidates→5 evidence, OK/APPLIED, actual scores và source identities. Read-only GET RPC instrumentation; chưa chạy extended CLI với real DB |
| EVALUATED | **Chưa đạt quality evaluation**: không có verified human qrels; harness chạy và trả BLOCKED_NO_VALID_JUDGMENTS, không fabricated metrics |
| BLOCKED / limitations | Quality labels, corpus E5 revision provenance lịch sử, mypy thiếu package, cold-start budget10s không đủ bảo đảm |

## Thay đổi source chính xác

### Modified

- `src/application/services/retrieval_service.py`: thêm optional config/scorer, reuse run_hybrid closure; chỉ enabled Hybrid đi coordinator mới.
- `src/applications/tillegal/retrieval/ports.py`: PairScorer Protocol. Output typed PairScores thay bare tuple trong proposal để mang cold/load/inference/truncation diagnostics; cùng contract1 scalar/candidate, không thay kiến trúc.
- `src/applications/tillegal/retrieval/reranker.py`: thay placeholder bằng pure integrity validation/score validation/selection và safe operational error.
- `src/retrieval_bootstrap.py`: conditional lazy scorer composition, không load khi disabled.
- `scripts/search_legal_chunks.py`: opt-in flags, reject missing path/non-Hybrid, giữ existing defaults10/bm25 và existing JSON disabled.
- `docs/retrieval-learning/README.md`: link chương04 và ghi snapshot lịch sử.

### Created

- `src/applications/tillegal/retrieval/reranking_models.py`: config, PairScores, candidate diagnostics và opt-in Hybrid response subclass/validators.
- `src/integrations/embeddings/cross_encoder_reranker.py`: local AutoTokenizer/sequence-classifier CPU float32, only_second truncation, batch inference/logits, cache/lock/cancellation policy.
- `src/application/services/reranking.py`: expansion, deadline, classified CE fallback, post-inference index checks, metadata/response assembly.
- `scripts/evaluate_retrieval.py`: offline saved-ranking metrics harness, human-qrels/context/pool validation, excludes unverified/unjudged cases.
- `tests/unit/applications/tillegal/retrieval/test_reranking.py`: pure/service integration/adapter/CLI/timeout/integrity/consumer-order tests.
- `tests/unit/applications/tillegal/retrieval/test_reranking_evaluation.py`: hand-calculated metric checks, no-label/unjudged handling, duplicate IDs.
- `docs/retrieval-learning/04_RERANKING_TECHNICAL_WALKTHROUGH.md`: Vietnamese learning chapter,16 actual function traces/code statements, actual live20-row ranking table,15 oral questions.
- `.docs/development/task8-verify.py`: standalone verification launcher; Windows standard-library memory counters; local model + explicitly --live read-only real service.
- `.docs/development/task8-execution-evidence.json`: actual local/live observations, model hash, versions, score/rank/provenance/timing/resource records.
- `.docs/development/task8-evaluation-queries.json`:3 sample queries **UNVERIFIED**, qrels=null, not labeled dataset.
- `.docs/development/task8-evaluation-runs-template.json`: empty ranking input template, not fake experiment results.
- `.docs/development/task8-evaluation-result.json`: actual harness outcome; metrics null,3 queries excluded.
- `.docs/development/task8-reranking-verification.md`: bản báo cáo này.

SHA-256 comparison against Stage1 snapshot351 files confirms only6 existing files above changed;7 new files in source/scripts/tests/learning areas. Ba chương học01–03, existing Hybrid/RRF implementation, SQL migrations, repositories, crawler, Agents và dependencies không bị chỉnh. Không có Git metadata nhận diện được ở snapshot; đây là hash comparison, không giả lập git diff.

## Kiến trúc và contract thực tế

Enabled only: original request top_k5→internal Hybrid top_k20→BM25/Dense đầy đủ và RRF→verified pool→PairScorer→sort CE desc/original RRF rank/UUID→select original Top-K→closing index checks→opt-in subclass. Branch budgets20/20 vẫn tách biệt pool20 và final5; có thể actual pool nhỏ hơn. Không refill hoặc bỏ mandatory filter để kiếm đủ candidates.

Giữ raw_score/score_kind=RRF, metadata/provenance/content/hash. CE score riêng ở reranking.candidates; final evidence.rank/list order có thể khác RRF raw_score sort. fusion.ranking reorder theo final IDs nhưng contributions/score giữ nguyên. Response validates original RRF và CE diagnostics/selection alignment. Disabled không có extra reranking field. Consumer opt-in phải parse RerankedHybridRetrievalResponse.

Audit `rg -n 'sort|raw_score|\.evidence' src -g '*.py'` không thấy downstream response consumer tự sort final evidence theo RRF score. CLI model_dump_json giữ list order; test CLI dùng scores gây đảo thứ tự RRF xác nhận behavior. Không khẳng định external clients ngoài repo đã được kiểm tra.

Operational adapter failures là RerankingOperationalError safe code và CE invalid score/timeout → FALLBACK+warning, original RRF selection. Retrieval branch errors, policy/source/hash/identity conflicts hoặc final index read/change → FAILED, không partial evidence. External cancellation không bị che. Lock tồn tại qua cancelled worker; no unbounded queue/retry. Thiếu model path CLI là boundary invalid arguments; path được chỉ định nhưng nonexistent → operational fallback.

## Commands và outcomes thực thi

Working directory: `tillegal-ai-main/`. Không có live calls trong unit tests.

```powershell
.venv/Scripts/python.exe -m pytest tests/unit/applications/tillegal/retrieval/test_reranking.py -q
# checkpoint đầu:19 passed in1.07s; sau đó bổ sung3 cases adapter/CLI

.venv/Scripts/python.exe -m pytest tests/unit/applications/tillegal/retrieval tests/unit/integrations/database/test_repositories.py -q
# retrieval/repository checkpoint:225 passed in5.36s; additional evaluation fixture covered by final full unit run

.venv/Scripts/python.exe -m pytest tests/unit -q
# final:386 passed in7.43s
```

Test coverage mới: empty/single/multiple, positional mapping/order/ties/Top-K, NaN/Inf/count/bool/missing text/duplicate rejection, load/tokenizer/inference/busy/fallback behavior, full metadata/RRF preservation, disabled/non-Hybrid compatibility, policy/hash/index fail không bị fallback, inference/total deadlines, response tampering, CLI không re-sort, only_second truncation, cancellation vẫn giữ worker lock. Existing tests tiếp tục kiểm tra date/index/identity/schema/strict branch behavior.

Ban đầu tests trong sandbox treo tại Windows socket._fallback_socketpair→accept khi asyncio tạo loop; faulthandler xác nhận vị trí. Đã terminate các attempts chưa hoàn thành và rerun cùng tests ngoài sandbox thành công. Không chỉnh asyncio behavior trong product để né môi trường. Smoke đầu còn thiếu psutil; đã dùng standard-library Windows counters, không cài psutil. Các attempts lỗi không được tính pass.

Lint/format trên **11 changed/new product/test Python files** (5 modified source gồm reranker/ports/service/bootstrap/CLI +3 new modules +eval script +2 tests):

```powershell
.venv/Scripts/ruff.exe check src/application/services/reranking.py src/application/services/retrieval_service.py src/applications/tillegal/retrieval/reranking_models.py src/applications/tillegal/retrieval/reranker.py src/applications/tillegal/retrieval/ports.py src/integrations/embeddings/cross_encoder_reranker.py scripts/search_legal_chunks.py scripts/evaluate_retrieval.py src/retrieval_bootstrap.py tests/unit/applications/tillegal/retrieval/test_reranking.py tests/unit/applications/tillegal/retrieval/test_reranking_evaluation.py
# All checks passed!
.venv/Scripts/ruff.exe format --check src/application/services/reranking.py src/application/services/retrieval_service.py src/applications/tillegal/retrieval/reranking_models.py src/applications/tillegal/retrieval/reranker.py src/applications/tillegal/retrieval/ports.py src/integrations/embeddings/cross_encoder_reranker.py scripts/search_legal_chunks.py scripts/evaluate_retrieval.py src/retrieval_bootstrap.py tests/unit/applications/tillegal/retrieval/test_reranking.py tests/unit/applications/tillegal/retrieval/test_reranking_evaluation.py
#11 files already formatted
.venv/Scripts/python.exe -m mypy src/applications/tillegal/retrieval/reranker.py src/applications/tillegal/retrieval/reranking_models.py src/application/services/reranking.py src/integrations/embeddings/cross_encoder_reranker.py --follow-imports=silent
# BLOCKED: No module named mypy; không cài thêm
```

Learning chapter20 local links/function anchors được kiểm tra; AST ranges chính xác và balanced code fences. Đã independently recompute final live IDs bằng CE logits desc/original rank/UUID và so retained raw RRF score, cả hai runs PASS.

## Model runtime và live E2E

```powershell
.venv/Scripts/python.exe -X utf8 .docs/development/task8-verify.py --live
# artifact task8-execution-evidence.json,4 runs, blocker=null
```

Checkpoint local mMARCO multilingual MiniLMv2 revision1427fd652930e4ba29e8149678df786c240d8825. Hash weights `5daeca2481a76b5976a2bdc32f0a78532b6716da4f8cd3ff59460ef8d2f359b4`. Runtime torch2.15.0/transformers5.22.2/sentence-transformers5.7.0; torch CPU threads4 observed. Auto classes load successfully, outputs finite[B,1], no download. Config guards không attestation weights tuyệt đối, file hash quan sát trong manifest mới là bằng chứng bản được chạy.

Live query: “Điều kiện để hợp đồng dân sự có hiệu lực là gì?”, explicit date2026-11-16, policyEXPERIMENTAL_ONLY. Existing configured project, persisted chunks/indexes.6 allowlisted retrieval/read RPCs only qua GET; guard chặn other methods/RPCs. Production SDK POST transport chưa được chạy trong live scope. No startup server/workers/migration/crawler/index write.

| Run | Candidates/final | Model load s | Batch inference s | Full measured call s | RSS observation bytes |
|---|---|---:|---:|---:|---:|
| First-process local cold smoke (2 illustrative pairs) |2/2 scores|19.251668|0.100173|19.366165|1,170,370,560 after |
| Local warm smoke (same2 pairs) |2/2 scores|0|0.029713|0.030682|1,170,542,592 after |
| Live new CE adapter, imports/cache already warm |20/5|3.769584|1.969958|11.924187|See JSON live run |
| Live warm CE adapter |20/5|0|1.815912|5.454981|See JSON live run |

Before local smoke working set36,564,992 bytes. RSS/working set sampled per-process, không peak-memory measurement hoặc memory requirement guarantee. E5 warmup8.023764s được đo riêng trước live calls, không giấu vào CE load hoặc full live latency. Cold new adapter khác **cold process**: cold live đã hưởng imports/OS cache từ smoke. inference timer bao batch tokenize/forward/float conversion nhưng không pre-pass length tokenization; elapsed bao toàn scorer wait/workload. Không p95 hay throughput claims từ2 samples.

Hai live responses OK/APPLIED, pool20/final5,0 truncated,0 fallback, same logits/order. Source title/UUID/URL/dates/policy/hash được record subset; full legal content không persisted vào artifact. Chương04 có real20-row mapping; đây là technical verification chứ không human relevance judgment. Hash match không chứng minh nguyên văn raw source hoặc embedding freshness.

### Timeout practical assessment

Default enabled CE10s/total40s được giữ theo approved proposal; measured warm20-pool~1.82s phù hợp sample này, nhưng process-cold load19.25s **vượt10s**. Để tránh initial fallback khi đánh giá cold process, dùng explicit CE30s/total70s hoặc controlled warmup trước traffic; chưa tự warm model khi disabled hoặc tăng default latency toàn hệ thống. Cold inference timeout có thể return fallback trước khi thread load xong; worker vẫn giữ lock và tài nguyên cho đến finally. Không coi model timeout là worker termination.

## Usage và cấu hình

Recipe **minh họa cú pháp, không phải command live đã chạy**; thay đường dẫn placeholders bằng provisioned local snapshots. Supabase configuration tiếp tục do existing loader/process cấp; không paste credentials.

```powershell
.venv/Scripts/python.exe scripts/search_legal_chunks.py --query "Điều kiện để hợp đồng dân sự có hiệu lực là gì?" --mode hybrid --top-k 5 --as-of-date 2026-11-16 --allowed-policy EXPERIMENTAL_ONLY --dense-model-path "<LOCAL_E5_SNAPSHOT>" --rerank --rerank-model-path "<LOCAL_MMARCO_SNAPSHOT>" --rerank-candidates 20 --rerank-batch-size 4 --rerank-max-length 512 --rerank-timeout 30 --rerank-total-timeout 70
```

Không --rerank → old behavior/schema, không expand/load. Enabled only Hybrid; candidate pool1–50, batch1–16, pair length32–512, finite positive timeouts. CPU-only adapter. Final evidence luôn theo request.top_k, defaults CLI cũ không bị thay. Metadata config hiện có model_path do user provision, không chứa credentials.

## Evaluation: phương pháp đã chạy, quality bị chặn

```powershell
.venv/Scripts/python.exe scripts/evaluate_retrieval.py --dataset .docs/development/task8-evaluation-queries.json --runs .docs/development/task8-evaluation-runs-template.json --output .docs/development/task8-evaluation-result.json
# BLOCKED_NO_VALID_JUDGMENTS;3 samples UNVERIFIED, aggregate means=null/count0
```

Harness nhận hai JSON cùng corpus_manifest. Dataset queries có id/text/as_of_date/allowed_usage_policies/judgment_status/annotator/judgment_scope và qrels map `chunk_uuid → grade0..3`. Chỉ VERIFIED có provenance mới được evaluate. Corpus manifest cần pin index observations/content hashes để labels không trôi theo re-ingest; template UNPINNED là chưa đủ cho quality study.

Saved runs: queries map theo id, cùng text/date/policies, reranking_status=APPLIED (FALLBACK bị exclude), rankings map4 keys bm25/dense/hybrid/hybrid_reranked (lists UUID theo output order), fixed_hybrid_pool là full RRF order của **chính pool được CE score**. Re-ranked list phải là subset pool; không dùng hai lần retrieve độc lập rồi nói fixed-pool. Template runs rỗng vì chưa có verified qrels; không fabricated4-system ranking experiment.

Recall@K tính relevant found/tổng relevant grades>0; Precision@K denominatorK kể cả trả ít; MRR@K first relevant reciprocal rank hoặc0; nDCG dùng2^grade−1 và log2(rank+1), IDCG0 → None; candidate coverage là relevant trong pool/tổng relevant. Macro means có counts riêng cho undefined metrics. Unjudged output bị loại khỏi comparison, không tự thành negative; incomplete qrels không đại diện recall toàn corpus, report judgment scope. Relevance labels không được lấy từ top retrieval scores.

Chưa có valid labels nên không có số Recall/MRR/nDCG/Precision cải thiện. Tiếp theo cần human annotate legal evidence trên union candidates của4 configs và thêm known relevant ngoài pool, kiểm tra thời điểm/điều kiện/ngoại lệ; phân biệt generation miss và reranking demotion. Chưa có cơ sở enable default hoặc đổi model/pool vì quality. Giữ optional.

## Remaining limitations

- Technical live verification chỉ1 query với2 runs; không throughput/concurrency SLA hoặc legal quality claim.
- E5 historical corpus revision compatibility vẫn chưa chứng minh dù technical retrieval hoạt động; Task8 không tự re-embed để che uncertainty.
- BEST_EFFORT metadata observations không transaction snapshot; CE không re-evaluate legal validity.
- Long passage có thể bị truncate mất ngoại lệ; warning/diagnostics có nhưng chưa đánh giá chất lượng trên long legal chunks.
- External clients phải opt-in DTO/order semantics; chưa kiểm tra code ngoài repo.
- Mypy chưa chạy được vì chưa cài; package installation không cần thiết để hoàn thành behavioral checks hiện có.
