# Commands, counts và evidence

## Môi trường

Target `D:/DOWNLOAD/tillegal-ai/tillegal-ai-main`, .venv Python3.12.16. Package metadata ghi torch2.15.0, transformers5.22.2, sentence-transformers5.7.0, supabase2.33.0, pytest8.4.2. [Manifest](evidence/model-and-index.json) lưu phiên bản/checkpoint/metadata. Không cài dependency.

## Level 1 — controlled fakes

```powershell
.venv/Scripts/python.exe -B -m pytest -p no:cacheprovider -q tests/unit/applications/tillegal/test_query_search_multimode.py -k 'test_unit or test_clarification or test_invalid_plan'
```

25 passed,16 deselected,0 failed/skipped,1.05s. Fake service kiểm request mapping/identity và bootstrap config; không gọi backend. Lượt đầu với selector `-k 'unit or clarification or invalid_plan'` đã chạy cả41 tests vì path chứa unit,41 passed trong2.04s; không gọi nhầm đó là25 unit riêng. Tests trong file chạy unit đầu rồi offline service fixtures.

## Level 2 — focused regression, real components với fake read ports

```powershell
.venv/Scripts/python.exe -B -m pytest -p no:cacheprovider -q tests/unit/applications/tillegal/test_query_hardening.py tests/unit/applications/tillegal/test_query_search.py tests/unit/applications/tillegal/test_query_search_multimode.py tests/unit/applications/tillegal/retrieval/test_service.py tests/unit/applications/tillegal/retrieval/test_contracts.py tests/unit/applications/tillegal/retrieval/test_dense_service.py tests/unit/applications/tillegal/retrieval/test_query_encoder.py tests/unit/applications/tillegal/retrieval/test_hybrid_service.py tests/unit/applications/tillegal/retrieval/test_rank_fusion.py tests/unit/applications/tillegal/retrieval/test_reranking.py tests/unit/applications/tillegal/retrieval/test_supabase_vector_repository.py --junitxml=.docs/agent-development/task-04-multimode-verification/evidence/offline-junit.xml
```

275 collected/passed,0 failed/skipped,2.15s. [JUnit](evidence/offline-junit.xml) là evidence máy.25/41 là subsets/reruns trong275, không cộng thành số distinct tests mới. Suite không chạy real model hoặc Supabase; tokenizer/model adapters có controlled fakes/fixtures. New file thêm41 cases, runtime source không sửa.

## Level 3 — live read-only

Các lệnh chạy cwd target, mode riêng biệt. Script không đọc .env vào os.environ; dùng dotenv_values → load_settings(environ=mapping). Date/policy/top_k lấy từ artifact e2e-retrieval.json; không in credentials. Model path trong script là snapshot đã có, local_files_only ở adapters.

```powershell
.venv/Scripts/python.exe -B -X utf8 -c "import runpy,sys; sys.argv=['live_probe','bm25']; runpy.run_path('.docs/agent-development/task-04-multimode-verification/evidence/live_probe.py',run_name='__main__')"
```

Dense/Hybrid/rerank lần lượt dùng cùng command với argv mode dense/hybrid/rerank, bọc `subprocess.run([...],timeout=90)` để tránh indefinite process; service deadline vẫn30s, outer async45s, rerank total40s. Script BM25 gọi direct service thêm đúng1 lần với request đã phát; còn mode khác một lần mỗi probe.

Dense repeat dùng `runpy.run_path` lấy `probe`, `asyncio.run(probe('dense'))`, ghi riêng live-dense-repeat.json; initial timeout được giữ trong live-dense.json. Lý do repeat: hai Dense branches Hybrid/rerank đã thành công nên kiểm standalone repeatability với cấu hình không đổi. Mỗi probe là process mới; không claim model đã warm trong cùng instance.

| Probe | Search elapsed (s) | State / response | Evidence | Chi tiết |
|---|---|---|---|---|
| bm25 | 3.833384 | COMPLETED / OK | 5 | Không lỗi |
| dense | 30.001632 | FAILED / FAILED | 0 | RETRIEVAL_TIMEOUT |
| dense-repeat | 16.217589 | COMPLETED / OK | 5 | Không lỗi |
| hybrid | 20.964112 | COMPLETED / OK | 5 | Không lỗi |
| rerank | 24.154172 | COMPLETED / OK | 5 | APPLIED |

BM25 direct riêng0.937097s; equality excluding request_id/retrieved_at=true, same_observed_index=true. Measured elapsed là QuerySearch await, không toàn interpreter/cleanup. Samples quá ít để tính p95, speedup hay đánh giá chất lượng. Dense đầu timeout không có vector retrieval success trong attempt đó; không giấu failure bằng kết quả repeat.

Các successful live responses đều có TEMPORAL_METADATA_INCOMPLETE warnings; warning codes/IDs nguyên ở JSON. Rerank APPLIED,diagnostics cold=true,load3.964188s,inference1.584810s. Có FutureWarning về API get_sentence_embedding_dimension được đổi tên thành get_embedding_dimension khi probe đọc dimension; không ảnh hưởng response. Runtime adapter đã có compatibility reader; Task4 không sửa source vì warning của helper kiểm chứng.

## Failure/edge-case coverage

| Case | Evidence / outcome |
|---|---|
| Invalid QueryPlan / empty subquery | New invalid-plan cases raise ValidationError,zero service calls |
| Clarification | 2 cases ×4 profiles,zero calls |
| Invalid mode/top_k | mode rerank/top_k0,51,bool reject trước I/O |
| Missing E5 | Real adapter với nonexistent dir → MODEL_NOT_PROVISIONED,zero vector calls |
| Missing reranker | Real adapter missing path → explicit FALLBACK/RERANKING_FALLBACK,không APPLIED |
| Dense index missing/stale/incompatible | New missing case + existing dense preflight matrix,zero encode/vector calls |
| Connection/backend failure | Fake repository errors → typed DATABASE_FAILURE; không cố làm hỏng live connection |
| Retrieval deadline | New dense/Hybrid timeout; actual Dense first attempt encoding timeout |
| Hybrid branch failure | New2 cases,bằng chứng failed state/empty final evidence/no fallback |
| No-match | New4 profiles,NO_MATCH empty; rerank SKIPPED_EMPTY |
| Temporal metadata missing | Fake fixture warnings + mọi successful live response |
| Invalid vectors/model scores/cancellation | Existing query encoder/rerank/fusion/RPC suites trong275 |

## Lint và source verification

```powershell
.venv/Scripts/ruff.exe check tests/unit/applications/tillegal/test_query_search_multimode.py .docs/agent-development/task-04-multimode-verification/evidence/live_probe.py
.venv/Scripts/ruff.exe format --check tests/unit/applications/tillegal/test_query_search_multimode.py .docs/agent-development/task-04-multimode-verification/evidence/live_probe.py
```

Final All checks passed;2 files already formatted. Probe ban đầu có4 E501, format giải quyết; không che failed lint đầu. Source export không có Git nên không claim git diff. Manifest trước322 files; sau thêm một test,changed=[],deleted=[]. Không secrets trong output/evidence; không ghi .env. Pooling source path đoán theo phiên bản cũ không tồn tại, đã định vị lại bằng find_spec và đọc đúng path module lowercase; đây là inspection correction, không test failure.
