# Task 5 — Kết quả triển khai

Ngày21/11/2026, timezone Asia/Saigon. Authoritative checkout D:/DOWNLOAD/tillegal-ai/tillegal-ai-main. Source export không có .git; version bằng checksum, không claim Git diff.

- IMPLEMENTED: graph hai node node Query/Search dùng framework hiện có, dừng clarification hoặc technical handoff.
- VERIFIED OFFLINE:30 graph/node/handoff tests đạt2.08s; regression 320 passed trong3.82s, 0 failed/skipped.30 nằm trong 320.
- VERIFIED REAL SUPABASE:1 BM25 graph smoke, 1 retrieval call, OK/5 evidence, SEARCH_COMPLETED, handoff READY. Await execution3.062241s; IDs/hash/round-trip đạt.
- PARTIAL: prototype handoff readiness; chưa production lifecycle/ACL/checkpoint/load.
- NOT TESTED trong Task 5: live Dense/Hybrid/rerank qua graph, durable checkpoint/resume, legal quality. Live Task 4 thuộc pipeline trước graph.

Hoàn thiện2 stub graph/state và thêm 1 graph test. Không đổi Query/Search/QuerySearch/RetrievalService/bootstrap/config/dependencies. Không có Judge node hoặc decision pháp lý. Expected service failure giữ native response; execution exception/cancellation propagate theo GraphExecutor, không tạo packet thành công giả.

Task dùng injected QuerySearch làm container service/options; nodes gọi underlying understand/search để không chạy Query hai lần. Ngày/policy/mode không suy từ input. Không retry/search loop/model download/migration/Git write.
