# Contracts và quyền sở hữu

`understand(question: str) -> dict` giữ sáu trường: original str nguyên đối số, intent quote_lookup/legal_question, domain labour/unknown, temporal_scope list[str], subqueries list[Subquery] 1–4, clarification str|None. QueryInputError(ValueError) có mã cố định; NFC nội bộ, calendar validation và taxonomy Task 1 được giữ.

`SearchOptions` immutable extra-forbid gồm mode RetrievalMode, top_k StrictInt 1–50, as_of_date date và allowed_usage_policies tuple[StrictStr,...] không rỗng. Tất cả required, không default date/policy. Policies strip và dedup. Options là trusted context: application phải xác thực quyền trước cấp options; schema validation tự nó không cấp quyền.

`search(plan: dict, retrieval: RetrievalService, options: SearchOptions) -> SearchState`: validate plan/options; clarification → zero calls; prebuild mọi RetrievalRequest trước I/O; tuần tự gọi search. Request.query từ subquery.text; mode/top_k/as_of_date/policies từ options. Không lấy quyền từ domain hoặc câu hỏi. Query temporal_scope được giữ trong plan nhưng không ghi đè ngày runtime; caller chịu trách nhiệm reconciliation ngày theo contract nghiệp vụ.

SearchState TypedDict gồm plan dict gốc, requests tuple[RetrievalRequest,...] thực sự đã gọi, responses tuple[RetrievalResponse,...], status CLARIFICATION_REQUIRED/COMPLETED/FAILED. Subclass Hybrid/Reranked response được giữ nguyên object, không serialize qua base model nên không rơi fusion/reranking. Search không gom/dedup evidence xuyên query vì việc đó có thể làm mất per-query ranking/index/date semantics. Unknown fields theo contract service vẫn giữ nguyên trong metadata.

Nếu FAILED ở query thứ N, state giữ N requests/responses và dừng; các OK trước đó không bị coi là final successful answer. ValidationError hoặc exception ngoài classified service contract propagate, không đổi thành NO_MATCH. Không có retry/fallback ở Search.

Ví dụ chạy live: question Trích dẫn: hợp đồng dân sự → query hợp đồng dân sự, intent quote_lookup, domain unknown, temporal_scope rỗng. Options dùng BM25, top_k=5, as_of_date=2026-11-17, policy EXPERIMENTAL_ONLY từ artifact e2e-retrieval.json của target. Đây là ngày explicit tái sử dụng, không phải ngày tự lấy từ đồng hồ. Response OK với 5 evidence. Original có prefix, query chỉ topic theo rule cũ.

Request và response chính xác ở src/applications/tillegal/retrieval/contracts.py. RetrievalResponse gồm schema_version, request_id UUID do service tạo, query/query_used, mode/top_k/date/policy, selected_index_name, index optional, status OK/NO_MATCH/FAILED, evidence tuple, warnings tuple, error optional, retrieved_at timezone-aware, consistency BEST_EFFORT. Search không thay request_id bằng correlation ID legacy.
