# Retrieval known issues — 2026-11-14

Phạm vi cập nhật: Task 6. P0 là correctness/security/contract/integrity nghiêm trọng; P1 chặn integration hoặc task phụ thuộc; P2 là cải thiện không chặn implementation hiện tại. Không dùng danh sách này để khẳng định lỗi runtime đã xảy ra khi chưa có bằng chứng.

| Priority | Vấn đề / bằng chứng | Tác động và điều kiện đóng |
|---|---|---|
| P1 | Task 4.6, Dense và Hybrid chưa có live Supabase verification; unit tests dùng fake ports/RPC responses | BLOCKED / RUNTIME_UNVERIFIED. Xác nhận deployed RPCs, read permissions, corpus, sparse/dense readiness rồi chạy read-only cases có expected IDs |
| P1 | Chưa xác minh stored embeddings cùng checkpoint revision với local E5 | Dimension384/norm đúng chưa đủ. Cần provenance về model revision, passage/query prefixes và preprocessing; không tự re-index |
| P1 | Index observations không phải transaction snapshot | Source cho thấy nhiều read calls tách rời; đây là consistency limitation, chưa có bằng chứng race xảy ra. Concurrent re-ingest có thể vượt khoảng kiểm tra; cần concurrency verification trước cam kết snapshot consistency |
| P1 | Consumer tương lai phải hiểu Hybrid response extension | Hybrid adds fusion, score_kind RRF và per-branch indexes. Trước nối API/Agents, thống nhất DTO/serialization; base DTO không parse extra fusion. Chưa có bằng chứng consumer hiện tại bị phá |
| P1 | Request chưa có document-ID filter riêng | Giữ nguyên source/effective-date/governance filters. Chốt yêu cầu document scoping trước task cần nó, không hứa filter chưa được triển khai |
| P2 | Sequential orchestration có thể cộng latency và hydrate chunk lặp ở hai branch | Chưa có runtime baseline; chỉ cân nhắc parallel/dedup reads khi đã đo và kiểm tra client/model concurrency safety |
| P2 | k60 và budgets20/20 chưa được đánh giá trên corpus Tillegal | Không khẳng định Hybrid tốt hơn. Chuẩn bị labels và so BM25/Dense/Hybrid trước tuning |
| P2 | UUID chunk có thể thay đổi sau re-ingest | Canonical dedup đúng trong một attempt; không dùng UUID hiện tại như durable cross-ingestion identity nếu chưa có thiết kế |
| P2 | Same-UUID metadata comparison cố ý nghiêm ngặt | Metadata thay đổi hợp lệ giữa hai reads cũng có thể fail; cần debug consistency thay vì silent merge. Không nới integrity policy chỉ để tránh lỗi |
| P2 | Synchronous RPC/model work trong thread không bị cưỡng bức dừng bởi async timeout | Response không lộ partial evidence nhưng công việc nền có thể hoàn tất muộn. Giữ client timeouts/encoder lock hiện có; đo tài nguyên khi stabilization |

Không phát hiện P0 còn mở qua unit verification hiện tại; không suy ra hệ thống production không có lỗi. Strict failure và không degraded mode là quyết định MVP đã công khai, không phải backend failures được che giấu.

Chi tiết implementation, tests và prerequisites: [Task 6](task6-hybrid-retrieval.md).
