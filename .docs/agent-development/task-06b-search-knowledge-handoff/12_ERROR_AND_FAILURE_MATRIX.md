# Error/failure matrix: owning layer và output thực tế

Nguồn [Search38–56](../../../src/applications/tillegal/agents/search/agent.py),[Request23–44](../../../src/applications/tillegal/retrieval/contracts.py),[service192–305](../../../src/application/services/retrieval_service.py),[node39–54](../../../src/applications/tillegal/graphs/legal_qa.py),[handoff44–93](../../../src/applications/tillegal/state/legal_qa_state.py),[executor28–84](../../../src/framework/runtime/executor.py). Test symbol/range/assertion ở 14/18. Không tự gán project error codes cho Pydantic exceptions.

| Trigger | Owner / type | Propagation và state | Subsequent queries / handoff | Evidence |
|---|---|---|---|---|
|Missing/ None /empty QueryPlan | Search 40, ValidationError |Không SearchState; graph exception |0 calls, no packet |missing_plan/none_plan; test_options_and_plan_fail_before_reads |
|Unsupported intent/domain/purpose | QueryPlan Literal schema |Reject trước options/clarification |0 calls, no packet |unsupported_intent; invalid-plan tests |
|0 hoặc>4 subqueries | QueryPlan list bounds | ValidationError |0 calls dù clarification có message |empty_subqueries/five_subqueries/clarification_invalid_plan |
|Empty subquery text |Subquery min_length | ValidationError |0 calls |empty_text; test_invalid_plan_no_calls |
|Tab/whitespace-only query |Request nonblank 34–37 | ValidationError trong eager construction |0 calls cho cả batch |tab_second; QueryPlan vẫn hợp lệ |
|Valid clarification | Search 42–43; graph router 36–37 |Direct empty tuples/ CLARIFICATION_REQUIRED; graph skip Search |0 calls, no handoff |clarification; test_graph_clarification_skips_search_node |
|Invalid options dù clarification | Search 41 trước guard | ValidationError |0 calls, no packet |clarification_invalid_options |
|Missing mode | SearchOptions required |Missing field ValidationError SOURCE-DERIVED; mode= None diagnostic enum reject |0 calls, no packet |missing_mode(case thực dùng None); schema 18 |
|mode=rerank |RetrievalMode Literal/enum | ValidationError; không fallbackhybrid |0 calls, no packet |rerank_mode; test_unit_invalid_options |
| top_k 0, 51, bool, string | StrictInt /constraints | ValidationError |0 calls, no packet |zero/bool/string probes; existing 0/51/bool cases |
|Invalid/missing as_of_date |Options date parser | ValidationError |0 calls, no packet |invalid_date/missing_date; ISO calendar sai |
|Empty/blank/non-string policy |Options tuple/ StrictStr /validator | ValidationError |0 calls, no packet |empty_policy/blank_policy/number_policy |
|Extra option |Options extra forbid | ValidationError |0 calls, no packet |extra_option |
|No searchable BM25 tokens |Service preprocessing 307–318 |Classified EMPTY_TERMS/INVALID_REQUEST, FAILED response | Search stop; graph RETRIEVAL_FAILED packet |Service tests contract/invalid request; khác blank request schema |
|Native NO_MATCH |Service outcome | Search COMPLETED nếu mọi call nonfailed |Tiếp các queries; packet NO_MATCH nếu tất cả empty |no_match; all-mode no-match tests |
|Native FAILED |Service classified detail | Search append rồi FAILED; graph RETRIEVAL_FAILED |Dừng và giữ prefix; packet được tạo nếu contexts hợp lệ |failed_first/partial_failure; graph 155–165 |
|Unexpected retrieval exception |Dependency, vd RuntimeError | Search không catch; executor FAILED /raise |Dừng, không return partial state/packet |exception_second; test_unexpected_search_exception_is_execution_failure |
|Service deadline |Service catches TimeoutError →detail TIMEOUT | FAILED response; không outer execution error nếu graph còn deadline |Dừng; RETRIEVAL_FAILED packet |test_offline_total_deadline; test_typed_retrieval_timeout_becomes_failed_handoff |
|Workflow outer deadline | GraphExecutor 52–55, TimeoutError |Lifecycle FAILED, cancel invocation, raise |Dừng coroutine, no packet output |test_outer_timeout_and_cancellation_propagate |
| CancellationToken |Executor 56–63, ExecutionCancelledError |Lifecycle CANCELLED, raise |Dừng coroutine, no packet output |same test; ContextVar restored |
|Caller task.cancel |Executor 68–73, CancelledError |Lifecycle CANCELLED, propagate |Dừng coroutine, no packet output |test_caller_task_cancellation_propagates |
|Missing raw node state.plan |Node 40, KeyError |Không automatic TypedDict validation |0 calls, no packet |supplemental missing_state_plan |
|Request/response context mismatch | Search không check; handoff 54–55 |Direct Search có thể COMPLETED; packet ValidationError; graph FAILED exception |Direct call đã xảy ra; no valid graphpacket |context_mismatch/graph_context_mismatch; handoff_context_mismatch tests |
|Inconsistent packet status/counts/extra | JudgeHandoff validators | ValidationError; node không emit completed update |Không packet; không retry |test_handoff_rejects_inconsistent_or_extra_fields |
|Metadata not JSON serializable | Pydantic serializer, không Search | model_dump_json ném PydanticSerializationError |Packet object có thể tồn tại trước serialization; graph không tự serialize trong node |supplemental object() copy |

## Failure không đồng nghĩa exception

Classified FAILED được coi là một return object hợp lệ. GraphExecutor có thể SUCCEEDED dù graph.status= RETRIEVAL_FAILED vì computation kết thúc đúng contract. Unexpected exception/outer timeout/cancel không trở thành RetrievalResponse. Không có catch-all chuyển mọi lỗi thành safe public detail. GraphExecutor.fail còn ghi type/error string trong lifecycle; không claim arbitrary upstream exceptions đã được sanitize giống database classified detail.

## Partial history và no automatic recovery

 FAILED ở queryj:responses[0..j] và requests prefix được trả; queryj+1...không chạy. Exception ởj:recorder có thể quan sát prior calls nhưng caller không nhận SearchState từ function. Không retry/backoff/cross-mode fallback hoặc resume/subquery cursor trong Search. Reranker operational fallback là quyết định downstream có warning, không phải Search đổi strategy.

Cancellation của async task không đảm bảo worker thread stopped; locks model và HTTP timeouts xử lý tài nguyên ở layer khác. Không đưa task đã bị cancel vào một responseOK để làm kết quả đẹp hơn.
