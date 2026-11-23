# Task 4 — Kết luận kiểm chứng đa mode

Audit và execution ngày 21/11/2026, timezone Asia/Saigon. Checkout authoritative duy nhất là `D:/DOWNLOAD/tillegal-ai/tillegal-ai-main`. Không có `.git`; đã dùng manifest checksum trước/sau cho 322 file source/test/config/dependency. Runtime source không đổi, không có file bị xóa. Thêm đúng một test file; tài liệu/probe/evidence nằm trong thư mục Task 4.

## Kết quả

- VERIFIED OFFLINE — 25 unit tests riêng đạt; tổng focused regression 275 passed trong 2.15s, không failed/skipped. Những tập này có giao nhau, không cộng số tests.
- VERIFIED REAL SUPABASE — BM25, Dense (repeat), Hybrid RRF và Hybrid+rerank APPLIED đều có execution thành công cho một câu hỏi kiểm soát.
- PARTIAL về độ ổn định startup — Dense lần đầu timeout encoding đúng deadline 30s; kết quả thất bại được giữ, lần repeat không tăng timeout. Chưa phân rã nguyên nhân import/load/cache/CPU để kết luận tại sao nhanh hơn.
- NOT TESTED — throughput, p95/p99, tập câu hỏi đa dạng, legal correctness, production resource lifecycle, LangGraph/HTTP/Judge/Answer integration.

| Probe | Search elapsed (s) | State / response | Evidence | Chi tiết |
|---|---|---|---|---|
| bm25 | 3.833384 | COMPLETED / OK | 5 | Không lỗi |
| dense | 30.001632 | FAILED / FAILED | 0 | RETRIEVAL_TIMEOUT |
| dense-repeat | 16.217589 | COMPLETED / OK | 5 | Không lỗi |
| hybrid | 20.964112 | COMPLETED / OK | 5 | Không lỗi |
| rerank | 24.154172 | COMPLETED / OK | 5 | APPLIED |

BM25 Search-mediated và direct call có cùng request; bằng nhau toàn response khi bỏ request_id/retrieved_at. Cùng index identity quan sát được. Đây là BEST_EFFORT, không phải hai lần đọc trong một transaction snapshot.

Không tái thiết kế Query/Search/Service; chưa có defect integration tái hiện cần sửa source. Rerank là stage bật trong Hybrid, không phải mode thứ tư trong RetrievalRequest. Fallback khi model rerank lỗi là behavior có warning của service, đã kiểm offline; probe live rerank lần này là APPLIED.

Các JSON trong evidence lưu identity/hash/status/diagnostic, không lưu credential hoặc toàn text/source metadata. Model local đã tồn tại; không download, migration, ingest, rebuild hoặc gọi LLM trả phí. Không Git write.
