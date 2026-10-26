# Component Design

## 1. Component map

| Component / module | Trách nhiệm | Không chịu trách nhiệm |
|---|---|---|
| API boundary | Nhận request nội bộ, kiểm tra payload/schema, tạo correlation context và trả response có cấu trúc | Xác thực nghiệp vụ người dùng |
| Workflow Orchestrator | Khởi tạo state/budget; điều phối node; quản lý nhánh, vòng lặp, retry và điều kiện dừng | Tự đánh giá tính đúng pháp lý bằng logic ngầm |
| Workflow State / Contracts | Định nghĩa schema request, state, evidence, claim, citation, verification report và kết quả cuối | Dựa hoàn toàn vào prompt để bảo đảm cấu trúc |
| Query Agent | Phân tích câu hỏi/intent, tách vấn đề pháp lý, tạo query plan và câu hỏi làm rõ nếu cần | Tự khẳng định căn cứ pháp luật khi chưa truy xuất |
| Search Agent / Retrieval interface | Thực hiện truy xuất theo query plan; trả evidence cùng source/version/metadata và lỗi truy xuất | Xem điểm retrieval là xác suất kết luận đúng |
| Judge Agent | Đánh giá evidence sufficiency, khoảng trống, mâu thuẫn và nhu cầu tìm bổ sung | Coi `SUFFICIENT` là bằng chứng câu trả lời cuối đã được verify |
| Summary / Answer Agent | Tạo bản nháp tiếng Việt, giải thích áp dụng quy định, liên kết claim với citation/evidence và nêu giới hạn | Tự thêm căn cứ không có trong evidence |
| Verify Agent | Kiểm tra claim–citation, định danh/vị trí citation, mức độ hỗ trợ, metadata hiệu lực khi có dữ liệu | Chỉ dựa vào nhận xét ngôn ngữ của LLM để quyết định trạng thái |
| Faith-Search | Tìm evidence/nguồn thay thế có mục tiêu khi lỗi verify có thể sửa; giữ nguyên nguồn gốc citation | Tự đổi citation chưa xác minh thành verified |
| LLM Gateway | Cung cấp giao diện gọi model dùng chung, chuẩn hóa cấu hình/usage/error và áp dụng policy | Để application code phụ thuộc trực tiếp vào SDK của một provider |
| Prompt / Context module | Quản lý prompt template, context assembly, phiên bản prompt và quy tắc truyền ngữ cảnh | Lưu secret hoặc thay thế schema validation |
| Evaluation | Chạy evaluator theo dataset/config/version; tổng hợp kết quả và phân loại lỗi | Đánh đồng điểm đánh giá tổng quát với tính đúng pháp lý |
| Observability | Log có cấu trúc, tracing, timing, token/cost usage, lỗi và lý do dừng | Ghi API key, token xác thực hoặc dữ liệu nhạy cảm không cần thiết |
| Persistence / Checkpoint adapter | Cung cấp abstraction cho checkpoint/state persistence nếu workflow cần | Buộc framework dùng một backend chưa được quyết định |
| Provider/retrieval integrations | Adapter tới LLM provider và Supabase Postgres + pgvector cho RAG | Để lỗi/provider-specific type rò rỉ xuyên suốt domain/application |

## 2. Framework versus Tillegal modules

### Framework (generic)
- Workflow execution abstractions and shared graph utilities.
- Common state/contract patterns where genuinely reusable.
- LLM gateway and provider adapter interface.
- Prompt/context management primitives.
- Generic telemetry and evaluation interfaces.
- Retry/timeout/budget utilities.
- Persistence/checkpoint interfaces.
- Common errors and result envelopes.

### Tillegal application (domain-specific)
- Legal Q&A/advice/citation-verification graph configuration.
- Query/Judge/Answer/Verify/Faith-Search implementations for legal tasks.
- Legal evidence and citation schemas.
- Legal source metadata interpretation and temporal-validity checks.
- Legal-specific evaluators and golden datasets.
- Legal answer policies and Vietnamese response formatting.

## 3. Data contracts that must be explicit

The architecture expects typed/schema-validated contracts for at least:
- Request context: `request_id`, processing `mode`, `as_of_date` where applicable, input and permitted conversation context.
- Query plan: legal issues, search queries and query history.
- Evidence: `evidence_id`, source/document/version identifiers, content/location metadata and retrieval diagnostics.
- Judge result: status, missing items, usable evidence IDs and suggested next queries.
- Draft: version, claims and citations.
- Verification: per-claim/per-citation status, evidence used, reason and limitations.
- Control: search rounds, retry count and remaining budget.
- Termination: status, `stop_reason` and limitations.

Stable identifiers should be used consistently: `request_id`, `claim_id`, `citation_id`, `evidence_id`, `document_id`, and `version_id`.

## 4. Error boundaries

Each component should return either a validated result or a typed/structured failure. Examples include provider timeout, retrieval unavailable, invalid model output, unknown evidence ID, verification failure and budget exhaustion. Do not silently convert a technical failure into a successful legal conclusion.

A partial failure affecting one claim/citation must remain visible in the final verification result; it must not be hidden by an overall success flag.

## 5. MVP implementation note

This document defines logical responsibilities, not a mandatory one-file-per-component mapping. Keep the initial implementation small: modules may share a package or graph until there is a concrete reason to split them. Do not create separate network services for each Agent.
