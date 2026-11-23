# Test evidence

CWD D:/DOWNLOAD/tillegal-ai/tillegal-ai-main, Python .venv/Scripts/python.exe 3.12.16. Các lệnh chạy ngoài sandbox được duyệt vì checkout ngoài writable roots và Windows asyncio socketpair.

```powershell
.venv/Scripts/python.exe -B -m pytest -p no:cacheprovider -q tests/unit/applications/tillegal/test_query_hardening.py tests/unit/applications/tillegal/test_query_search.py tests/unit/applications/tillegal/retrieval/test_service.py tests/unit/applications/tillegal/retrieval/test_contracts.py tests/unit/applications/tillegal/retrieval/test_dense_service.py tests/unit/applications/tillegal/retrieval/test_hybrid_service.py tests/unit/applications/tillegal/retrieval/test_reranking.py
```

185 collected/passed, 0 failed/skipped, 2.62s, exit 0. Query hardening được chuyển riêng test không phụ thuộc legacy graph. Tests QuerySearch dùng real RetrievalService với fake ports từ fixtures hiện có; không gọi DB/model. No-match, DB failure, stop-on-failure, metadata/hash/rank, options date/policy mapping, invalid request, clarification, bootstrap delegation, không import ai_core đều có assertion.

Identity test assert response object chính là response fake service trả, plan không bị mutate. Subclass preservation dựa trên không chuyển đổi response; regression Hybrid/reranking của service chạy trong suite, chưa có riêng QuerySearch live Hybrid case.

| Backend | Offline | Live Supabase | Giới hạn |
|---|---|---|---|
| BM25 | VERIFIED service fake ports + QuerySearch | VERIFIED một request OK, 5 evidence | Không benchmark quality/latency |
| Dense | VERIFIED service fake ports | NOT TESTED | Chưa xác minh path model/query inference trong task |
| Hybrid | VERIFIED service regression | NOT TESTED | Không coi unit fusion là live E2E |
| Reranking | VERIFIED service regression | NOT TESTED | Không tự tải hoặc chạy model |

Live script gọi QuerySearch.search('Trích dẫn: hợp đồng dân sự') với BM25/options từ artifact e2e-retrieval.json (date=2026-11-17, top_k=5, policy EXPERIMENTAL_ONLY); tạo settings bằng load_settings(environ=dotenv_values('.env')).supabase; create_query_search timeout_seconds=15; asyncio.wait_for 20s. Credential chỉ dùng trong process, không in/lưu. Không đọc dữ liệu bằng write RPC, không migration.

Kết quả mới: status COMPLETED, 1 request; response mode bm25/status OK/evidence_count 5/error_code null; warning TEMPORAL_METADATA_INCOMPLETE lặp 5 lần. Thử đọc artifact ban đầu bằng utf-8 lỗi UnicodeDecodeError, chạy lại UTF-16 thành công; đây là lỗi harness, không Retrieval.

Quality gates: Ruff check All checks passed và format check 5 files already formatted. Lần đầu check --fix sửa 2 import issues, sau đó format 4 files. Không có test assertion failure trong task. Không chạy full suite hoặc paid inference. Vì target không có .git nên không thể git diff; rà soát giới hạn write-set và stub guard thay cho diff tracked. Target source export được định danh SHA256 ở 01.

## Verification cuối sau chỉnh import fixture

Đổi dynamic import fixture thành import trực tiếp trong test_query_search.py cho dễ đọc; source runtime không đổi. Chạy `.venv/Scripts/python.exe -B -m pytest -p no:cacheprovider -q tests/unit/applications/tillegal/test_query_search.py`: 12 passed trong 1.38s. Ruff check/format --check file này đạt. Kết quả 185 của lượt trước vẫn là bằng chứng regression, không cộng 12 rerun thành số distinct cases mới.
