# Source trace

Ranges lấy AST sau format, relative với target root.

| File từ target root | Symbol | Dòng thật |
|---|---|---|
| [src/applications/tillegal/graphs/legal_qa.py](../../../src/applications/tillegal/graphs/legal_qa.py) | `QuerySearchNodes.__init__` | 21–22 |
| [src/applications/tillegal/graphs/legal_qa.py](../../../src/applications/tillegal/graphs/legal_qa.py) | `QuerySearchNodes.query` | 24–33 |
| [src/applications/tillegal/graphs/legal_qa.py](../../../src/applications/tillegal/graphs/legal_qa.py) | `QuerySearchNodes.route_query` | 36–37 |
| [src/applications/tillegal/graphs/legal_qa.py](../../../src/applications/tillegal/graphs/legal_qa.py) | `QuerySearchNodes.search` | 39–54 |
| [src/applications/tillegal/graphs/legal_qa.py](../../../src/applications/tillegal/graphs/legal_qa.py) | `compile_query_search_graph` | 57–66 |
| [src/applications/tillegal/graphs/legal_qa.py](../../../src/applications/tillegal/graphs/legal_qa.py) | `QuerySearchWorkflow.__init__` | 72–74 |
| [src/applications/tillegal/graphs/legal_qa.py](../../../src/applications/tillegal/graphs/legal_qa.py) | `QuerySearchWorkflow.execute` | 76–95 |
| [src/applications/tillegal/state/legal_qa_state.py](../../../src/applications/tillegal/state/legal_qa_state.py) | `JudgeHandoff.warnings` | 35–37 |
| [src/applications/tillegal/state/legal_qa_state.py](../../../src/applications/tillegal/state/legal_qa_state.py) | `JudgeHandoff.errors` | 40–41 |
| [src/applications/tillegal/state/legal_qa_state.py](../../../src/applications/tillegal/state/legal_qa_state.py) | `JudgeHandoff.validate_context` | 44–64 |
| [src/applications/tillegal/state/legal_qa_state.py](../../../src/applications/tillegal/state/legal_qa_state.py) | `JudgeHandoff.from_search` | 67–93 |
| [src/query_search_bootstrap.py](../../../src/query_search_bootstrap.py) | `QuerySearch.search` | 20–21 |
| [src/query_search_bootstrap.py](../../../src/query_search_bootstrap.py) | `create_query_search` | 24–42 |
| [src/applications/tillegal/agents/query/agent.py](../../../src/applications/tillegal/agents/query/agent.py) | `understand` | 29–95 |
| [src/applications/tillegal/agents/search/agent.py](../../../src/applications/tillegal/agents/search/agent.py) | `SearchOptions.nonblank_policies` | 25–28 |
| [src/applications/tillegal/agents/search/agent.py](../../../src/applications/tillegal/agents/search/agent.py) | `search` | 38–56 |
| [src/framework/graphs/factory.py](../../../src/framework/graphs/factory.py) | `create_state_graph` | 8–12 |
| [src/framework/graphs/compiler.py](../../../src/framework/graphs/compiler.py) | `compile_graph` | 10–17 |
| [src/framework/runtime/executor.py](../../../src/framework/runtime/executor.py) | `AsyncGraph.ainvoke` | 18–22 |
| [src/framework/runtime/executor.py](../../../src/framework/runtime/executor.py) | `GraphExecutor.execute` | 28–84 |
| [src/framework/runtime/executor.py](../../../src/framework/runtime/executor.py) | `GraphExecutor._invoke` | 87–94 |
| [src/framework/runtime/executor.py](../../../src/framework/runtime/executor.py) | `GraphExecutor._cancel_invocation` | 97–102 |
| [src/framework/runtime/execution_context.py](../../../src/framework/runtime/execution_context.py) | `ExecutionContext.__post_init__` | 26–37 |
| [src/framework/runtime/execution_context.py](../../../src/framework/runtime/execution_context.py) | `current_execution_context` | 40–42 |
| [src/framework/runtime/execution_context.py](../../../src/framework/runtime/execution_context.py) | `_ExecutionContextBinding.__init__` | 48–50 |
| [src/framework/runtime/execution_context.py](../../../src/framework/runtime/execution_context.py) | `_ExecutionContextBinding.__enter__` | 52–54 |
| [src/framework/runtime/execution_context.py](../../../src/framework/runtime/execution_context.py) | `_ExecutionContextBinding.__exit__` | 56–60 |
| [src/framework/runtime/execution_context.py](../../../src/framework/runtime/execution_context.py) | `_ExecutionContextBinding.__aenter__` | 62–63 |
| [src/framework/runtime/execution_context.py](../../../src/framework/runtime/execution_context.py) | `_ExecutionContextBinding.__aexit__` | 65–66 |
| [src/framework/runtime/execution_context.py](../../../src/framework/runtime/execution_context.py) | `bind_execution_context` | 69–71 |

| Symbol | Caller → callee | Input/processing | Output/error |
|---|---|---|---|
| QuerySearchWorkflow.__init__ | Application → compile_query_search_graph | Inject pipeline, tạo graph/executor một lần | Không retrieval I/O |
| QuerySearchWorkflow.execute | Caller → GraphExecutor.execute | question/context/deadline, fresh initial dict | LegalQAState hoặc exception/cancel |
| compile_query_search_graph | Constructor → create_state_graph/compile_graph | LegalQAState, query/search nodes, conditional edge | Graph không saver/loop/Judge |
| QuerySearchNodes.__init__ | Compiler → giữ pipeline | Application-scoped service/options | Không tạo models mới |
| QuerySearchNodes.query | LangGraph → understand | state.question; delegate validation/NFC/planning | plan/options/clarification/status; reset handoff/search_result; exceptions propagate |
| route_query | Scheduler | Đọc clarification | end hoặc search, không I/O |
| QuerySearchNodes.search | LangGraph → Search Agent → from_search | plan + injected service/options | Native result, handoff, status, error codes; classified failures giữ, unexpected exceptions propagate |
| JudgeHandoff.from_search | Search node → constructor | question/IDs/options/native result, technical status | Packet hoặc ValidationError |
| validate_context | Constructor/JSON parse | Original/count/query/options/response context/first failure checks | Self hoặc validation failure |
| warnings/errors properties | Consumer | Flatten response warnings/errors, giữ canonical per-query data | Typed tuples, không thay nội dung |
| GraphExecutor.execute | Wrapper → graph.ainvoke | Context binding, deadline, token, lifecycle, task cleanup | Output/TimeoutError/ExecutionCancelledError/underlying exception |
| Agent search | Search node → RetrievalService.search | Prebuild requests, tuần tự, stop-on-FAILED | SearchState giữ native response |

Live trace: Trích dẫn: hợp đồng dân sự → quote_lookup/subquery hợp đồng dân sự → QUERY_COMPLETED → Search BM25/top_k5/date2026-11-17/policyEXPERIMENTAL_ONLY → service/RPC → OK/5 evidence → handoff READY → SEARCH_COMPLETED → END. Correlation/run IDs giữ riêng với service request UUID.

Node Search lấy options từ pipeline; state.options chỉ mô tả context. Test cố override state.options không làm đổi backend request. Application dùng execute để bảo đảm fresh state/context/deadline; raw compiled graph chỉ nên invoke với input mới theo schema, không dùng prior output như resumed request. Không triển khai resume/checkpoint trong task.
