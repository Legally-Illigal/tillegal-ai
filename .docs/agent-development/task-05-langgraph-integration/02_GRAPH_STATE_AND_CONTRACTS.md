# State và contracts

Public API: QuerySearchWorkflow(pipeline); await execute(question, ExecutionContext, timeout_seconds=..., lifecycle=...). Initial state chỉ question/run_id/request_id. Caller chịu authorization và ID uniqueness. ExecutionContext validate nonblank IDs; request_id optional. Không lấy credentials/backend clients vào state.

Question validation thuộc understand, giữ QueryInputError và original. QueryPlan trong state vẫn dict sáu fields; trong handoff là typed model để validate/JSON. Native SearchState giữ plan, requests tuple, responses tuple và COMPLETED/FAILED.

### JudgeHandoff

| Field | Python type | Default/constraint |
|---|---|---|
| schema_version | `Literal['1']` | `'1'` |
| request_id | `str \| None` | `Required` |
| run_id | `str` | `Field(min_length=1)` |
| question | `str` | `Field(min_length=1, max_length=10000)` |
| plan | `QueryPlan` | `Required` |
| options | `SearchOptions` | `Required` |
| requests | `tuple[RetrievalRequest, ...]` | `Field(min_length=1)` |
| responses | `tuple[RetrievalOutcome, ...]` | `Field(min_length=1)` |
| search_status | `Literal['COMPLETED', 'FAILED']` | `Required` |
| status | `Literal['READY', 'NO_MATCH', 'RETRIEVAL_FAILED']` | `Required` |

### LegalQAState

| Field | Python type | Default/constraint |
|---|---|---|
| request_id | `str \| None` | `Required` |
| question | `str` | `Required` |
| plan | `dict` | `Required` |
| options | `SearchOptions` | `Required` |
| search_result | `SearchState \| None` | `Required` |
| clarification | `str \| None` | `Required` |
| handoff | `JudgeHandoff \| None` | `Required` |

LegalQAState kế thừa WorkflowState: run_id/status/errors và optional messages/artifacts/metadata. errors là list[str] safe service codes với append_unique reducer hiện hữu. Các channel mới dùng last-value. question/plan/options/clarification/search_result/handoff được cập nhật theo node, không append responses run trước.

| State status | Ý nghĩa |
|---|---|
| QUERY_COMPLETED | Intermediate sau Query, trước Search |
| CLARIFICATION_REQUIRED | Không Search, END, handoff None |
| SEARCH_COMPLETED | Search xong, ít nhất một response có evidence, không FAILED |
| NO_MATCH | Mọi subquery hoàn tất không evidence, không phải exception |
| RETRIEVAL_FAILED | Dừng tại native FAILED, giữ prior responses nếu có |

Execution failure không tạo final state/handoff mới; exception propagate và lifecycle FAILED. Cancellation lifecycle CANCELLED. Không claim state.status EXECUTION_FAILED được emit. Các trạng thái execution nằm out-of-band theo executor convention.

RetrievalOutcome union gồm RerankedHybridRetrievalResponse, HybridRetrievalResponse, RetrievalResponse theo thứ tự subtype cụ thể trước. Tests JSON round-trip giữ đúng subtype/UUID/date/nulls/metadata/fusion/reranking. Graph in-memory không cần serialize mỗi edge; chưa attach saver hoặc kiểm durable checkpoint end-to-end.

Frozen model không deep-freeze nested metadata/list. Caller tránh mutate packet/evidence. handoff.warnings/errors là properties derive từ responses; JSON canonical giữ tại responses[i].warnings/error, không có keys property riêng.
