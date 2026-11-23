# LangGraph Search node: state, lifecycle và END

Nguồn [legal_qa.py18–95](../../../src/applications/tillegal/graphs/legal_qa.py),[LegalQAState96–103](../../../src/applications/tillegal/state/legal_qa_state.py),[WorkflowState10–18](../../../src/framework/state/base.py),[GraphExecutor28–102](../../../src/framework/runtime/executor.py).

## Registration và callable

compile_query_search_graph 57–66 tạo QuerySearchNodes (pipeline), StateGraph(LegalQAState), đăng ký query/search, START→query, conditional clarification→END hoặc search, search→END. Không retry/loop/ Judge node. compile_graph không được truyền saver, defaultcheckpointer= None; không claim persistence/resume.

`QuerySearchNodes.search(self, state: LegalQAState) -> LegalQAState` là async node 39–54. Input sau query update có plan/question/ run_id và optional request_id. Node lấy state["plan"] nhưng dùng self.pipeline.retrieval/options, không state.options. Điều này bảo vệ injected execution configuration khỏi state tampering trong tests 299–307, không thay tenant ACL /auth policy layer chưa có.

## Statement-level summary và ownership

1. Dòng 40 await existing Search function với plan dict + pipeline dependencies.
2. Dòng 41–47 gọi JudgeHandoff.from_search: question=state.question, request_id =get optional, run_id required, options injected, result SearchState.
3. Dòng 48 chuyển packet READY thành graph SEARCH_COMPLETED; packet NO_MATCH / RETRIEVAL_FAILED giữ nguyên.
4. Dòng 49–54 trả partial update search_result, handoff, status, errors chỉ safe typed error.code.
5. Graph merge update rồi search→END. Handoff validation exception trước 49 đồng nghĩa không có completed Search node update.

| Layer | Thành công có evidence | Không match |Classified failure |Execution exception |
|---|---|---|---|---|
|Native response |OK | NO_MATCH | FAILED |Không response cho call ném |
| SearchState | COMPLETED | COMPLETED | FAILED, giữ prior responses |Không state return |
| JudgeHandoff | READY | NO_MATCH | RETRIEVAL_FAILED |Không packet thành công |
|Graph final status | SEARCH_COMPLETED | NO_MATCH | RETRIEVAL_FAILED |Không final state thay exception |
|Executor lifecycle | SUCCEEDED | SUCCEEDED | SUCCEEDED | FAILED hoặc CANCELLED theo loại |

 SUCCEEDED lifecycle nghĩa graph computation hoàn thành và trả output, kể cả typed retrieval failure. Không nhầm lifecycle failure với business retrieval failure hoặc evidence sufficiency.

## State channels và reducer

LegalQAState inherits WorkflowState, total= False:keys optional về typing, không tự runtime validate missing plan/question/ run_id. Graph Search node dùng indexing có thể KeyError nếu bypass public wrapper. request_id dùng state.get nên missing→ None. Handoff có validators riêng.

plan/options/question/IDs/search_result/handoff/status không có custom reducer nên dùng last-value channel semantics trong graph này. errors kế thừa Annotated[list[str], append_unique]; reducer giữ thứ tự và dedup codes. Nó không merge evidence hoặc remove duplicate warnings. Query reset search_result/handoff thành None, workflow.execute 84–88 tạo fresh initial state; không nhập packet từ run cũ.

```mermaid
sequenceDiagram
 participant A as Caller
 participant W as Workflow.execute
 participant E as Executor/context binding
 participant G as LangGraph
 participant N as Search node
 participant S as Search function
 participant R as RetrievalService
 participant H as JudgeHandoff
 A->>W: question,ExecutionContext,timeout
 W->>E: fresh initial state
 E->>G: ainvoke
 G->>G: Query update + route
 alt clarification
 G-->>E: END,CLARIFICATION_REQUIRED,no handoff
 else search
 G->>N: merged plan/question/IDs
 N->>S: await search(plan,pipeline.retrieval,pipeline.options)
 loop each processed subquery
 S->>R: await search(request)
 R-->>S: native response
 end
 S-->>N: SearchState
 N->>H: from_search;context validation
 H-->>N: typed technical packet
 N-->>G: result/handoff/status/errors update
 G-->>E: END
 end
 E-->>A: state hoặc propagated exception
```

## IDs, cancellation và isolation

 ExecutionContext kiểm IDs nonblank, bind bằng ContextVar trong executor._invoke 93–94. Search không truyền IDs vào RetrievalRequest; packet dùng run-level IDs, response UUID riêng. Wrapper tạo fresh state mỗi execution; compiled graph, service/options shared. Tests repeated/concurrent invocations kiểm không rò state/IDs/errors giữa requests, không chứng minh production SDK /model throughput/tenant isolation.

Executor timeout/cancel/error không bị node chuyển thành packet: TimeoutError outer, lifecycle FAILED; CancellationToken → ExecutionCancelledError, lifecycle CANCELLED; caller task.cancel→asyncio. CancelledError. Service timeout đã classified lại là response FAILED với packet và graph trả bình thường. Chi tiết 12/13; đúng code blocks ở 10.

Historical Task 5 state table ghi Required cho total= False là discrepancy đã ghi Task 6a và giữ nguyên old report. Current source/runtime optional-key evidence là authority. Task 6B không sửa graph hoặc thêm Judge.
