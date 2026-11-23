# Input contract: query-derived và trusted application options

Entrypoint OBSERVED: `search(plan: dict, retrieval: RetrievalService, options: SearchOptions) -> SearchState`. Python annotations không tự enforce dependency protocol. Runtime code validate plan/options, không isinstance-check retrieval. Source [Search38–47](../../../src/applications/tillegal/agents/search/agent.py).

| Parameter | Type/required | Origin/default | Validation/consumer | Failure/example |
|---|---|---|---|---|
|plan |dict; bắt buộc | Query understand output hoặc direct caller; không default | QueryPlan. model_validate 40 | ValidationError trước service; sáu fields bên dưới |
|retrieval | RetrievalService annotation; bắt buộc | QuerySearch.retrieval injected |await retrieval.search 47; không runtime interface adapter |Thiếu search có thể AttributeError; tests dùng fakes duck typing |
|options | SearchOptions annotation; bắt buộc |Application cung cấp; không default | SearchOptions. model_validate 41 | ValidationError trước clarification/calls; raw dict cũng validate được trong diagnostic |

 QueryPlan internal schema [query/agent.py15–26](../../../src/applications/tillegal/agents/query/agent.py):

| Field | Exact type/required/default | Origin và consumer |
|---|---|---|
|original |str length 1..10000; required/no default |Raw question; Search giữ trong raw plan, handoff so với question |
|intent |Literal quote_lookup/legal_question; required | Query rules; Search validate nhưng không quyết định mode |
|domain |Literal labour/unknown; required |Keyword label; không map corpus filter |
| temporal_scope |list[str]; required |Mention strings; không override as_of_date |
|subqueries |list[Subquery], 1..4; required |Mỗi text thành request; purpose validate nhưng không forward |
|clarification |str hoặc None; required/no default |Truthy string làm early return; empty string falsy |

Nullable khác optional key: `clarification=None` được chấp nhận; bỏ field không có default thì ValidationError. QueryPlan default extra handling là ignore, trong khi raw SearchState.plan giữ extras. Những field chứa str không đồng nghĩa toàn bộ model strict. Search không validate lại raw question bằng understand khi nhận direct plan.

## Trusted SearchOptions đầy đủ

Source [SearchOptions13–28](../../../src/applications/tillegal/agents/search/agent.py); model frozen, extra forbid. Tất cả bốn fields required, không project default trong SearchOptions.

| Field | Type/constraints | Origin / example | Processing/failure | Downstream |
|---|---|---|---|---|
|mode |RetrievalMode: bm25, dense, hybrid |Application, ví dụ hybrid |String enum conversion; rerank bị reject |Service dispatch, không query classification |
| top_k | StrictInt, 1..50 |Application, ví dụ 2 |bool, string số, 0, 51 bị reject |Mỗi request tối đa k evidence, không global budget |
| as_of_date |datetime.date |Application, ví dụ date(2026, 11, 10) | Pydantic có thể parse ISO string hợp lệ; ngày invalid/ None bị reject |Trusted filter của retrieval |
| allowed_usage_policies |tuple[StrictStr,...], ít nhất 1 |Application, ví dụ(EXPERIMENTAL_ONLY,) |Reject blank/non-string; strip từng policy rồi dedup giữ thứ tự |Service/repository governance filter |

Ví dụ OBSERVED normalized_options: input date string 2026-11-10 và policies list[" A ", "A", "B"] tạo date object cùng tuple("A", "B"). SearchOptions frozen ngăn assignment thông thường, không chứng minh authorization của caller; “trusted” là boundary responsibility của application. Không tự kiểm user có quyền dùng policy nào trong Search.

 RetrievalRequest có top_k default 10 nhưng SearchOptions bắt buộc top_k và Search luôn truyền field này; default 10 không được ngầm áp ở Search path. Reranking là cấu hình service cho hybrid, không RetrievalMode thứ tư.

## Identity, runtime và dependencies không nằm trong Search input schema

- Search function không nhận request_id / run_id /timeout/token riêng. RetrievalRequest cũng không có identity field; service sinh response. request_id riêng.
- Graph lấy IDs từ ExecutionContext qua state rồi đưa vào JudgeHandoff. ContextVar binding cho downstream được GraphExecutor quản lý, không do Search thêm IDs vào request.
- Query original/time/domain/purpose không thể điều khiển trusted mode/date/policies bằng text. Test test_untrusted_state_options_do_not_override_injection còn cho thấy graph dùng pipeline.options, không tin state.options bị caller thay.
- Không có pending field, legacy EvidenceBundle hoặc HTTP body contract trong input này.

Kiểm chứng: [multimode tests55–139](../../../tests/unit/applications/tillegal/test_query_search_multimode.py), [graph tests299–307](../../../tests/graph/test_query_search_workflow.py); diagnostics options và schemas ở [search-traces.json](evidence/search-traces.json). Exact errors/zero calls xem 03/12.
