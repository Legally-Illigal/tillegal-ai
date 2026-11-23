# Source-level Search execution trace

Đây là phần primary walkthrough, không thay bằng diagram hoặc author summary. Mọi snippets dưới đây lấy trực tiếp source hiện tại; ranges được kiểm lại tự động. Signature ở code header là actual source signature, không mô tả third-party internals. Nội dung ACTION là SOURCE-DERIVED; runtime objects thật ở 11.

## SearchOptions: trusted context schema và policy validator

Nguồn [src/applications/tillegal/agents/search/agent.py:13–28](../../../src/applications/tillegal/agents/search/agent.py).

```python
class SearchOptions(BaseModel):
    """Trusted execution context, explicitly supplied by the application."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    mode: RetrievalMode
    top_k: StrictInt = Field(ge=1, le=50)
    as_of_date: date
    allowed_usage_policies: tuple[StrictStr, ...] = Field(min_length=1)

    @field_validator("allowed_usage_policies")
    @classmethod
    def nonblank_policies(cls, values: tuple[str, ...]) -> tuple[str, ...]:
        if any(not value.strip() for value in values):
            raise ValueError("Policies must not be blank")
        return tuple(dict.fromkeys(value.strip() for value in values))
```

- READ: mode/ top_k /date/policy caller cung cấp
- WRITE/TRANSFORM: immutable options; strip/dedup tuple policies
- CONDITION/ACTION/WHY: Các fields required; strict số/policy string; extra forbid; nonblank_policies dùng strip để reject blank rồi stable dedup. Không chọn policy từ question.
- RESULT/NEXT: SearchOptions. model_validate ở receiving Search /bootstrap; ValidationError nếu không hợp lệ.

## Entrypoint và hai validation boundaries

Nguồn [src/applications/tillegal/agents/search/agent.py:38–41](../../../src/applications/tillegal/agents/search/agent.py).

```python
async def search(plan: dict, retrieval: RetrievalService, options: SearchOptions) -> SearchState:
    """Keep native responses intact; stop on a classified retrieval failure."""
    parsed = QueryPlan.model_validate(plan)
    options = SearchOptions.model_validate(options)
```

- READ: raw plan dict, dependency instance, options
- WRITE/TRANSFORM: parsed QueryPlan, validated options
- CONDITION/ACTION/WHY: Validate plan trước options, để constraints rõ ràng trước I/O. Không catch validation error.
- RESULT/NEXT: Đi guard 42 hoặc raise; chưa có request/service call.

## Clarification early return

Nguồn [src/applications/tillegal/agents/search/agent.py:42–43](../../../src/applications/tillegal/agents/search/agent.py).

```python
    if parsed.clarification:
        return {"plan": plan, "requests": (), "responses": (), "status": "CLARIFICATION_REQUIRED"}
```

- READ: parsed.clarification, raw plan
- WRITE/TRANSFORM: SearchState với empty tuples
- CONDITION/ACTION/WHY: Truthy message dừng transport; không tạo packet trong function.
- RESULT/NEXT: Caller nhận CLARIFICATION_REQUIRED; không vào 44.

## Eager requests construction

Nguồn [src/applications/tillegal/agents/search/agent.py:44–45](../../../src/applications/tillegal/agents/search/agent.py).

```python
    requests = tuple(RetrievalRequest(query=subquery.text, **options.model_dump()) for subquery in parsed.subqueries)
    responses = []
```

- READ: parsed.subqueries và options. model_dump
- WRITE/TRANSFORM: tuple requests, list responses mới
- CONDITION/ACTION/WHY: Mỗi subquery.text thành Request; mọi request validate trước loop. Không forward purpose/domain/time.
- RESULT/NEXT: Nếu bất kỳ request fail thì không tới loop; otherwise 46.

## Sequential await và giữ identity

Nguồn [src/applications/tillegal/agents/search/agent.py:46–49](../../../src/applications/tillegal/agents/search/agent.py).

```python
    for request in requests:
        response = await retrieval.search(request)
        responses.append(response)
        if response.status == "FAILED":
```

- READ: requests, service, returned response.status
- WRITE/TRANSFORM: response local, responses append đúng object
- CONDITION/ACTION/WHY: Await từng request; không concurrency fan-out. Append trước failure check nên failed response vẫn được giữ.
- RESULT/NEXT: FAILED đi 50; otherwise request kế tiếp hoặc 56.

## Return failed prefix hoặc completed tuple

Nguồn [src/applications/tillegal/agents/search/agent.py:50–56](../../../src/applications/tillegal/agents/search/agent.py).

```python
            return {
                "plan": plan,
                "requests": requests[: len(responses)],
                "responses": tuple(responses),
                "status": "FAILED",
            }
    return {"plan": plan, "requests": requests, "responses": tuple(responses), "status": "COMPLETED"}
```

- READ: responses length, requests, raw plan
- WRITE/TRANSFORM: SearchState dictionary
- CONDITION/ACTION/WHY: FAILED giữ requests prefix đã có response; COMPLETED giữ toàn bộ. Tuple conversion không serialize nested objects.
- RESULT/NEXT: Return caller; exception trong 47 không đi cả hai return paths.

## RetrievalRequest schema/validators

Nguồn [src/applications/tillegal/retrieval/contracts.py:23–44](../../../src/applications/tillegal/retrieval/contracts.py).

```python
class RetrievalRequest(ContractModel):
    """Explicit search filters; no implicit date or usage-policy defaults."""

    query: StrictStr = Field(min_length=1, max_length=10_000)
    mode: RetrievalMode
    top_k: StrictInt = Field(default=10, ge=1, le=50)
    as_of_date: date
    allowed_usage_policies: tuple[StrictStr, ...] = Field(min_length=1)

    @field_validator("query")
    @classmethod
    def nonblank_query(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("query must not be blank")
        return value

    @field_validator("allowed_usage_policies")
    @classmethod
    def policies(cls, values: tuple[str, ...]) -> tuple[str, ...]:
        if any(not value.strip() for value in values):
            raise ValueError("policies must not be blank")
        return tuple(dict.fromkeys(value.strip() for value in values))
```

- READ: text và options fields
- WRITE/TRANSFORM: typed request; policies trim/dedup
- CONDITION/ACTION/WHY: nonblank_query chỉ check value.strip rồi return nguyên value. top_k default 10 ở schema nhưng Search luôn supply.
- RESULT/NEXT: Request object tới service; blank query/options invalid fail trước I/O.

## QuerySearch.search

Nguồn [src/query_search_bootstrap.py:20–21](../../../src/query_search_bootstrap.py).

```python
    async def search(self, question: str) -> SearchState:
        return await search(understand(question), self.retrieval, self.options)
```

- READ: question:str, self.retrieval, self.options
- WRITE/TRANSFORM: Locals/models/updates đúng code block bên trên
- CONDITION/ACTION/WHY: Wrapper không tự tạo handoff; Query errors propagate; return SearchState.
- RESULT/NEXT: Quay lại Application với question → understand → Search; return annotation/raise path thể hiện trong signature và ACTION.

```text
FROM:
Application với question → understand → Search

CALL:
QuerySearch.search — src/query_search_bootstrap.py:20–21

INPUT:
question:str,self.retrieval,self.options

ACTION:
Wrapper không tự tạo handoff;Query errors propagate;return SearchState.

RETURN:
Xem signature/code block: typed output/dict hoặc exception;không thêm fallback ngoài source.

BACK TO:
Application với question → understand → Search;tiếp tục operation trong caller hoặc propagate exception.
```

## create_query_search

Nguồn [src/query_search_bootstrap.py:24–42](../../../src/query_search_bootstrap.py).

```python
def create_query_search(
    settings: SupabaseSettings,
    options: SearchOptions,
    *,
    dense_model_path: Path | None = None,
    hybrid_config: HybridConfig | None = None,
    rerank_config: RerankConfig | None = None,
    timeout_seconds: float = 30,
) -> QuerySearch:
    """Require explicit filters and delegate all retrieval composition."""
    options = SearchOptions.model_validate(options)
    retrieval = create_retrieval_service(
        settings,
        dense_model_path=dense_model_path,
        hybrid_config=hybrid_config,
        rerank_config=rerank_config,
        timeout_seconds=timeout_seconds,
    )
    return QuerySearch(retrieval, options)
```

- READ: Supabase Settings, SearchOptions, optional dense/configs/timeout
- WRITE/TRANSFORM: Locals/models/updates đúng code block bên trên
- CONDITION/ACTION/WHY: Validate options rồi delegate factory; frozen container giữ đúng dependencies; không request-time allocation model.
- RESULT/NEXT: Quay lại Application construction → retrieval bootstrap; return annotation/raise path thể hiện trong signature và ACTION.

```text
FROM:
Application construction → retrieval bootstrap

CALL:
create_query_search — src/query_search_bootstrap.py:24–42

INPUT:
SupabaseSettings,SearchOptions,optional dense/configs/timeout

ACTION:
Validate options rồi delegate factory;frozen container giữ đúng dependencies;không request-time allocation model.

RETURN:
Xem signature/code block: typed output/dict hoặc exception;không thêm fallback ngoài source.

BACK TO:
Application construction → retrieval bootstrap;tiếp tục operation trong caller hoặc propagate exception.
```

## create_retrieval_service

Nguồn [src/retrieval_bootstrap.py:22–70](../../../src/retrieval_bootstrap.py).

```python
def create_retrieval_service(
    settings: SupabaseSettings,
    *,
    dense_model_path: Path | None = None,
    hybrid_config: HybridConfig | None = None,
    rerank_config: RerankConfig | None = None,
    timeout_seconds: float = 30,
) -> RetrievalService:
    """Create read adapters only. Credentials are never rendered or logged here.

    Session persistence/refresh is disabled; search calls only existing read RPCs.
    HTTP timeouts bound worker-thread I/O even after an application deadline expires.
    """
    if settings.url is None or settings.api_key is None:
        raise ValueError("Supabase retrieval configuration is required")
    client = create_client(
        str(settings.url),
        settings.api_key.get_secret_value(),
        options=ClientOptions(persist_session=False, auto_refresh_token=False, postgrest_client_timeout=10),
    )
    dense_retriever: LegalRetriever | None = None
    dense_indexes: IndexReader | None = None
    query_embedder: QueryEmbedder | None = None
    if dense_model_path is not None:
        from src.integrations.embeddings.e5_query_encoder import E5QueryEncoder

        dense_retriever = SupabaseVectorRepository(client)
        dense_indexes = DenseIndexRepository(client)
        query_embedder = E5QueryEncoder(dense_model_path)
    scorer = None
    if rerank_config is not None and rerank_config.enabled:
        from src.integrations.embeddings.cross_encoder_reranker import LocalCrossEncoder

        scorer = LocalCrossEncoder(rerank_config)
    return RetrievalService(
        SparseRetrievalRepository(client),
        ChunkRepository(client),
        SourceDocumentRepository(client),
        SparseIndexRepository(client),
        tokenize_sparse_text,
        sparse_index_name=DEFAULT_SPARSE_INDEX,
        dense_retriever=dense_retriever,
        dense_indexes=dense_indexes,
        query_embedder=query_embedder,
        hybrid_config=hybrid_config,
        rerank_config=rerank_config,
        pair_scorer=scorer,
        timeout_seconds=timeout_seconds,
    )
```

- READ: settings và explicit opt-ins
- WRITE/TRANSFORM: Locals/models/updates đúng code block bên trên
- CONDITION/ACTION/WHY: Reject missing URL/key; create client với read adapter graph, persist/refresh false, HTTP 10 s; E 5/ CrossEncoder wrappers chỉ khi opt-in; trả RetrievalService có dependencies tái sử dụng.
- RESULT/NEXT: Quay lại create_query_search → SDK /adapters/model wrappers/Service; return annotation/raise path thể hiện trong signature và ACTION.

```text
FROM:
create_query_search → SDK/adapters/model wrappers/Service

CALL:
create_retrieval_service — src/retrieval_bootstrap.py:22–70

INPUT:
settings và explicit opt-ins

ACTION:
Reject missing URL/key;create client với read adapter graph,persist/refresh false,HTTP10s;E5/CrossEncoder wrappers chỉ khi opt-in;trả RetrievalService có dependencies tái sử dụng.

RETURN:
Xem signature/code block: typed output/dict hoặc exception;không thêm fallback ngoài source.

BACK TO:
create_query_search → SDK/adapters/model wrappers/Service;tiếp tục operation trong caller hoặc propagate exception.
```

## QuerySearchNodes.__init__

Nguồn [src/applications/tillegal/graphs/legal_qa.py:21–22](../../../src/applications/tillegal/graphs/legal_qa.py).

```python
    def __init__(self, pipeline: QuerySearch) -> None:
        self.pipeline = pipeline
```

- READ: pipeline QuerySearch
- WRITE/TRANSFORM: Locals/models/updates đúng code block bên trên
- CONDITION/ACTION/WHY: Lưu shared pipeline; không copy result state vào object.
- RESULT/NEXT: Quay lại Graph compiler → nodes; return annotation/raise path thể hiện trong signature và ACTION.

```text
FROM:
Graph compiler → nodes

CALL:
QuerySearchNodes.__init__ — src/applications/tillegal/graphs/legal_qa.py:21–22

INPUT:
pipeline QuerySearch

ACTION:
Lưu shared pipeline;không copy result state vào object.

RETURN:
Xem signature/code block: typed output/dict hoặc exception;không thêm fallback ngoài source.

BACK TO:
Graph compiler → nodes;tiếp tục operation trong caller hoặc propagate exception.
```

## QuerySearchNodes.query

Nguồn [src/applications/tillegal/graphs/legal_qa.py:24–33](../../../src/applications/tillegal/graphs/legal_qa.py).

```python
    def query(self, state: LegalQAState) -> LegalQAState:
        plan = understand(state["question"])
        return {
            "plan": plan,
            "options": self.pipeline.options,
            "clarification": plan["clarification"],
            "status": "CLARIFICATION_REQUIRED" if plan["clarification"] else "QUERY_COMPLETED",
            "search_result": None,
            "handoff": None,
        }
```

- READ: state.question và self.pipeline.options
- WRITE/TRANSFORM: Locals/models/updates đúng code block bên trên
- CONDITION/ACTION/WHY: Return plan/options/clarification/status/reset fields; không gọi QuerySearch.search.
- RESULT/NEXT: Quay lại LangGraph → understand; return annotation/raise path thể hiện trong signature và ACTION.

```text
FROM:
LangGraph → understand

CALL:
QuerySearchNodes.query — src/applications/tillegal/graphs/legal_qa.py:24–33

INPUT:
state.question và self.pipeline.options

ACTION:
Return plan/options/clarification/status/reset fields;không gọi QuerySearch.search.

RETURN:
Xem signature/code block: typed output/dict hoặc exception;không thêm fallback ngoài source.

BACK TO:
LangGraph → understand;tiếp tục operation trong caller hoặc propagate exception.
```

## QuerySearchNodes.route_query

Nguồn [src/applications/tillegal/graphs/legal_qa.py:36–37](../../../src/applications/tillegal/graphs/legal_qa.py).

```python
    def route_query(state: LegalQAState) -> Literal["search", "end"]:
        return "end" if state["clarification"] else "search"
```

- READ: state.clarification
- WRITE/TRANSFORM: Locals/models/updates đúng code block bên trên
- CONDITION/ACTION/WHY: Truthy→end, else search; missing key KeyError; không fall back đến Search nếu clarification.
- RESULT/NEXT: Quay lại LangGraph conditional edge; return annotation/raise path thể hiện trong signature và ACTION.

```text
FROM:
LangGraph conditional edge

CALL:
QuerySearchNodes.route_query — src/applications/tillegal/graphs/legal_qa.py:36–37

INPUT:
state.clarification

ACTION:
Truthy→end,else search;missing key KeyError;không fall back đến Search nếu clarification.

RETURN:
Xem signature/code block: typed output/dict hoặc exception;không thêm fallback ngoài source.

BACK TO:
LangGraph conditional edge;tiếp tục operation trong caller hoặc propagate exception.
```

## QuerySearchNodes.search

Nguồn [src/applications/tillegal/graphs/legal_qa.py:39–54](../../../src/applications/tillegal/graphs/legal_qa.py).

```python
    async def search(self, state: LegalQAState) -> LegalQAState:
        result = await search(state["plan"], self.pipeline.retrieval, self.pipeline.options)
        handoff = JudgeHandoff.from_search(
            question=state["question"],
            request_id=state.get("request_id"),
            run_id=state["run_id"],
            options=self.pipeline.options,
            result=result,
        )
        status = "SEARCH_COMPLETED" if handoff.status == "READY" else handoff.status
        return {
            "search_result": result,
            "handoff": handoff,
            "status": status,
            "errors": [error.code for error in handoff.errors],
        }
```

- READ: state.plan/question/run IDs; pipeline dependencies
- WRITE/TRANSFORM: Locals/models/updates đúng code block bên trên
- CONDITION/ACTION/WHY: Await Search; packet validation; READY map SEARCH_COMPLETED; return state update và typed error codes. Exception trước return không tạo packet giả.
- RESULT/NEXT: Quay lại LangGraph → Search → JudgeHandoff; return annotation/raise path thể hiện trong signature và ACTION.

```text
FROM:
LangGraph → Search → JudgeHandoff

CALL:
QuerySearchNodes.search — src/applications/tillegal/graphs/legal_qa.py:39–54

INPUT:
state.plan/question/run IDs;pipeline dependencies

ACTION:
Await Search;packet validation;READY map SEARCH_COMPLETED;return state update và typed error codes. Exception trước return không tạo packet giả.

RETURN:
Xem signature/code block: typed output/dict hoặc exception;không thêm fallback ngoài source.

BACK TO:
LangGraph → Search → JudgeHandoff;tiếp tục operation trong caller hoặc propagate exception.
```

## compile_query_search_graph

Nguồn [src/applications/tillegal/graphs/legal_qa.py:57–66](../../../src/applications/tillegal/graphs/legal_qa.py).

```python
def compile_query_search_graph(pipeline: QuerySearch):
    """Compile the existing framework's StateGraph with no persistent request state."""
    nodes = QuerySearchNodes(pipeline)
    builder = create_state_graph(LegalQAState)
    builder.add_node("query", nodes.query)
    builder.add_node("search", nodes.search)
    builder.add_edge(START, "query")
    builder.add_conditional_edges("query", nodes.route_query, {"search": "search", "end": END})
    builder.add_edge("search", END)
    return compile_graph(builder, name="query-search")
```

- READ: pipeline
- WRITE/TRANSFORM: Locals/models/updates đúng code block bên trên
- CONDITION/ACTION/WHY: Tạo 2 nodes, edges và no saver; Search →END; không Judge hoặc retryloop.
- RESULT/NEXT: Quay lại Workflow constructor → framework factory/compiler; return annotation/raise path thể hiện trong signature và ACTION.

```text
FROM:
Workflow constructor → framework factory/compiler

CALL:
compile_query_search_graph — src/applications/tillegal/graphs/legal_qa.py:57–66

INPUT:
pipeline

ACTION:
Tạo2nodes,edges và no saver;Search→END;không Judge hoặc retryloop.

RETURN:
Xem signature/code block: typed output/dict hoặc exception;không thêm fallback ngoài source.

BACK TO:
Workflow constructor → framework factory/compiler;tiếp tục operation trong caller hoặc propagate exception.
```

## QuerySearchWorkflow.__init__

Nguồn [src/applications/tillegal/graphs/legal_qa.py:72–74](../../../src/applications/tillegal/graphs/legal_qa.py).

```python
    def __init__(self, pipeline: QuerySearch) -> None:
        self.graph = compile_query_search_graph(pipeline)
        self.executor = GraphExecutor()
```

- READ: pipeline
- WRITE/TRANSFORM: Locals/models/updates đúng code block bên trên
- CONDITION/ACTION/WHY: Compile một lần, executor object được reuse; không validate mọi future input ở constructor.
- RESULT/NEXT: Quay lại Application → graph compiler/ GraphExecutor; return annotation/raise path thể hiện trong signature và ACTION.

```text
FROM:
Application → graph compiler/GraphExecutor

CALL:
QuerySearchWorkflow.__init__ — src/applications/tillegal/graphs/legal_qa.py:72–74

INPUT:
pipeline

ACTION:
Compile một lần,executor object được reuse;không validate mọi future input ở constructor.

RETURN:
Xem signature/code block: typed output/dict hoặc exception;không thêm fallback ngoài source.

BACK TO:
Application → graph compiler/GraphExecutor;tiếp tục operation trong caller hoặc propagate exception.
```

## QuerySearchWorkflow.execute

Nguồn [src/applications/tillegal/graphs/legal_qa.py:76–95](../../../src/applications/tillegal/graphs/legal_qa.py).

```python
    async def execute(
        self,
        question: str,
        context: ExecutionContext,
        *,
        timeout_seconds: float,
        lifecycle: ExecutionLifecycle | None = None,
    ) -> LegalQAState:
        initial: LegalQAState = {
            "question": question,
            "run_id": context.run_id,
            "request_id": context.request_id,
        }
        return await self.executor.execute(
            self.graph,
            initial,
            context,
            timeout_seconds=timeout_seconds,
            lifecycle=lifecycle,
        )
```

- READ: question, ExecutionContext, positive timeout, lifecycle optional
- WRITE/TRANSFORM: Locals/models/updates đúng code block bên trên
- CONDITION/ACTION/WHY: Tạo fresh initial dict cho invocation; đưa context IDs vào state; await executor và trả LegalQAState hoặc propagate error.
- RESULT/NEXT: Quay lại Application → GraphExecutor.execute; return annotation/raise path thể hiện trong signature và ACTION.

```text
FROM:
Application → GraphExecutor.execute

CALL:
QuerySearchWorkflow.execute — src/applications/tillegal/graphs/legal_qa.py:76–95

INPUT:
question,ExecutionContext,positive timeout,lifecycle optional

ACTION:
Tạo fresh initial dict cho invocation;đưa context IDs vào state;await executor và trả LegalQAState hoặc propagate error.

RETURN:
Xem signature/code block: typed output/dict hoặc exception;không thêm fallback ngoài source.

BACK TO:
Application → GraphExecutor.execute;tiếp tục operation trong caller hoặc propagate exception.
```

## JudgeHandoff.warnings

Nguồn [src/applications/tillegal/state/legal_qa_state.py:35–37](../../../src/applications/tillegal/state/legal_qa_state.py).

```python
    def warnings(self) -> tuple[RetrievalWarning, ...]:
        """Derive warnings without duplicating or discarding per-query response data."""
        return tuple(warning for response in self.responses for warning in response.warnings)
```

- READ: self.responses
- WRITE/TRANSFORM: Locals/models/updates đúng code block bên trên
- CONDITION/ACTION/WHY: Flatten tuple, giữ order/duplicates; @property không tự serialize top-level.
- RESULT/NEXT: Quay lại Packet consumer → per-response warnings; return annotation/raise path thể hiện trong signature và ACTION.

```text
FROM:
Packet consumer → per-response warnings

CALL:
JudgeHandoff.warnings — src/applications/tillegal/state/legal_qa_state.py:35–37

INPUT:
self.responses

ACTION:
Flatten tuple,giữ order/duplicates;@property không tự serialize top-level.

RETURN:
Xem signature/code block: typed output/dict hoặc exception;không thêm fallback ngoài source.

BACK TO:
Packet consumer → per-response warnings;tiếp tục operation trong caller hoặc propagate exception.
```

## JudgeHandoff.errors

Nguồn [src/applications/tillegal/state/legal_qa_state.py:40–41](../../../src/applications/tillegal/state/legal_qa_state.py).

```python
    def errors(self) -> tuple[RetrievalErrorDetail, ...]:
        return tuple(response.error for response in self.responses if response.error is not None)
```

- READ: self.responses
- WRITE/TRANSFORM: Locals/models/updates đúng code block bên trên
- CONDITION/ACTION/WHY: Chỉ lấy error khác None; không chuyển unexpected exception thành detail.
- RESULT/NEXT: Quay lại Graph node/consumer → per-response error; return annotation/raise path thể hiện trong signature và ACTION.

```text
FROM:
Graph node/consumer → per-response error

CALL:
JudgeHandoff.errors — src/applications/tillegal/state/legal_qa_state.py:40–41

INPUT:
self.responses

ACTION:
Chỉ lấy error khácNone;không chuyển unexpected exception thành detail.

RETURN:
Xem signature/code block: typed output/dict hoặc exception;không thêm fallback ngoài source.

BACK TO:
Graph node/consumer → per-response error;tiếp tục operation trong caller hoặc propagate exception.
```

## JudgeHandoff.validate_context

Nguồn [src/applications/tillegal/state/legal_qa_state.py:44–64](../../../src/applications/tillegal/state/legal_qa_state.py).

```python
    def validate_context(self) -> Self:
        if self.question != self.plan.original or self.plan.clarification:
            raise ValueError("Handoff requires the original non-clarifying query context")
        if len(self.requests) != len(self.responses) or len(self.requests) > len(self.plan.subqueries):
            raise ValueError("Handoff request/response counts differ")
        for subquery, request, response in zip(self.plan.subqueries, self.requests, self.responses):
            if request.query != subquery.text:
                raise ValueError("Handoff query differs from its plan")
            if any(getattr(request, key) != value for key, value in self.options.model_dump().items()):
                raise ValueError("Handoff execution options differ")
            if any(getattr(response, key) != getattr(request, key) for key in RetrievalRequest.model_fields):
                raise ValueError("Handoff response context differs")
        failed = self.responses[-1].status == "FAILED"
        if any(response.status == "FAILED" for response in self.responses[:-1]):
            raise ValueError("Search must stop at its first failure")
        expected = "RETRIEVAL_FAILED" if failed else "READY" if any(r.evidence for r in self.responses) else "NO_MATCH"
        if self.status != expected or self.search_status != ("FAILED" if failed else "COMPLETED"):
            raise ValueError("Handoff status differs from retrieval outcomes")
        if not failed and len(self.requests) != len(self.plan.subqueries):
            raise ValueError("Completed handoff requires all subqueries")
        return self
```

- READ: question/plan/options/requests/responses/statuses
- WRITE/TRANSFORM: Locals/models/updates đúng code block bên trên
- CONDITION/ACTION/WHY: Kiểm raw original, clarification, counts, per-query/options/response context, stop-at-first-failure và derived status; ValueError thành ValidationError ở constructor.
- RESULT/NEXT: Quay lại Pydantic after model fields → consistency checks; return annotation/raise path thể hiện trong signature và ACTION.

```text
FROM:
Pydantic after model fields → consistency checks

CALL:
JudgeHandoff.validate_context — src/applications/tillegal/state/legal_qa_state.py:44–64

INPUT:
question/plan/options/requests/responses/statuses

ACTION:
Kiểm raw original,clarification,counts,per-query/options/response context,stop-at-first-failure và derived status;ValueError thành ValidationError ở constructor.

RETURN:
Xem signature/code block: typed output/dict hoặc exception;không thêm fallback ngoài source.

BACK TO:
Pydantic after model fields → consistency checks;tiếp tục operation trong caller hoặc propagate exception.
```

## JudgeHandoff.from_search

Nguồn [src/applications/tillegal/state/legal_qa_state.py:67–93](../../../src/applications/tillegal/state/legal_qa_state.py).

```python
    def from_search(
        cls,
        *,
        question: str,
        request_id: str | None,
        run_id: str,
        options: SearchOptions,
        result: SearchState,
    ) -> Self:
        status = (
            "RETRIEVAL_FAILED"
            if result["status"] == "FAILED"
            else "READY"
            if any(response.evidence for response in result["responses"])
            else "NO_MATCH"
        )
        return cls(
            question=question,
            request_id=request_id,
            run_id=run_id,
            plan=result["plan"],
            options=options,
            requests=result["requests"],
            responses=result["responses"],
            search_status=result["status"],
            status=status,
        )
```

- READ: question, request_id, run_id, options, result
- WRITE/TRANSFORM: Locals/models/updates đúng code block bên trên
- CONDITION/ACTION/WHY: FAILED ưu tiên RETRIEVAL_FAILED, else evidence→ READY, else NO_MATCH; constructor chạy schema/context validators.
- RESULT/NEXT: Quay lại Graph Search node → JudgeHandoff constructor; return annotation/raise path thể hiện trong signature và ACTION.

```text
FROM:
Graph Search node → JudgeHandoff constructor

CALL:
JudgeHandoff.from_search — src/applications/tillegal/state/legal_qa_state.py:67–93

INPUT:
question,request_id,run_id,options,result

ACTION:
FAILED ưu tiên RETRIEVAL_FAILED,else evidence→READY,else NO_MATCH;constructor chạy schema/context validators.

RETURN:
Xem signature/code block: typed output/dict hoặc exception;không thêm fallback ngoài source.

BACK TO:
Graph Search node → JudgeHandoff constructor;tiếp tục operation trong caller hoặc propagate exception.
```

## GraphExecutor.execute

Nguồn [src/framework/runtime/executor.py:28–84](../../../src/framework/runtime/executor.py).

```python
    async def execute[InputT, OutputT](
        self,
        graph: AsyncGraph[InputT, OutputT],
        graph_input: InputT,
        context: ExecutionContext,
        *,
        config: Mapping[str, object] | None = None,
        timeout_seconds: float | None = None,
        lifecycle: ExecutionLifecycle | None = None,
    ) -> OutputT:
        """Invoke a graph and update lifecycle on success, failure, or cancellation."""
        if timeout_seconds is not None and timeout_seconds <= 0:
            raise ValueError("timeout_seconds must be greater than 0")
        context.cancellation_token.raise_if_cancelled()
        execution_lifecycle = lifecycle or ExecutionLifecycle()
        execution_lifecycle.start()
        invocation = asyncio.create_task(self._invoke(graph, graph_input, context, config))
        cancellation = asyncio.create_task(context.cancellation_token.wait_cancelled())
        try:
            done, _ = await asyncio.wait(
                (invocation, cancellation),
                timeout=timeout_seconds,
                return_when=asyncio.FIRST_COMPLETED,
            )
            if not done:
                await self._cancel_invocation(invocation)
                execution_lifecycle.fail(f"Graph execution exceeded {timeout_seconds} seconds")
                raise TimeoutError(f"Graph execution exceeded {timeout_seconds} seconds")
            if cancellation in done and invocation not in done:
                await self._cancel_invocation(invocation)
                execution_lifecycle.cancel()
                reason = context.cancellation_token.reason
                message = "Execution cancelled"
                if reason:
                    message = f"{message}: {reason}"
                raise ExecutionCancelledError(message)

            output = await invocation
            execution_lifecycle.succeed()
            return output
        except asyncio.CancelledError:
            if execution_lifecycle.snapshot.status is ExecutionStatus.RUNNING:
                execution_lifecycle.cancel()
            if not invocation.done():
                await self._cancel_invocation(invocation)
            raise
        except Exception as error:
            if execution_lifecycle.snapshot.status is ExecutionStatus.RUNNING:
                execution_lifecycle.fail(f"{type(error).__name__}: {error}")
            raise
        finally:
            if not cancellation.done():
                cancellation.cancel()
            try:
                await cancellation
            except asyncio.CancelledError:
                pass
```

- READ: graph, input, context, config, timeout, lifecycle
- WRITE/TRANSFORM: Locals/models/updates đúng code block bên trên
- CONDITION/ACTION/WHY: Guard deadline/token, start lifecycle, create tasks, wait FIRST_ COMPLETED; timeout/cancel/error cập nhật lifecycle rồi propagate; finally cancel watcher. Typed retrieval failure vẫn ordinary output/lifecycle success.
- RESULT/NEXT: Quay lại Workflow.execute → _invoke/cancellation tasks; return annotation/raise path thể hiện trong signature và ACTION.

```text
FROM:
Workflow.execute → _invoke/cancellation tasks

CALL:
GraphExecutor.execute — src/framework/runtime/executor.py:28–84

INPUT:
graph,input,context,config,timeout,lifecycle

ACTION:
Guard deadline/token,start lifecycle,create tasks,wait FIRST_COMPLETED;timeout/cancel/error cập nhật lifecycle rồi propagate;finally cancel watcher. Typed retrieval failure vẫn ordinary output/lifecycle success.

RETURN:
Xem signature/code block: typed output/dict hoặc exception;không thêm fallback ngoài source.

BACK TO:
Workflow.execute → _invoke/cancellation tasks;tiếp tục operation trong caller hoặc propagate exception.
```

## GraphExecutor._invoke

Nguồn [src/framework/runtime/executor.py:87–94](../../../src/framework/runtime/executor.py).

```python
    async def _invoke[InputT, OutputT](
        graph: AsyncGraph[InputT, OutputT],
        graph_input: InputT,
        context: ExecutionContext,
        config: Mapping[str, object] | None,
    ) -> OutputT:
        with bind_execution_context(context):
            return await graph.ainvoke(graph_input, config=config)
```

- READ: graph_input, context, config
- WRITE/TRANSFORM: Locals/models/updates đúng code block bên trên
- CONDITION/ACTION/WHY: Bind ExecutionContext bằng context manager rồi await compiled graph; binding được restore khi thoát.
- RESULT/NEXT: Quay lại Executor task → graph.ainvoke; return annotation/raise path thể hiện trong signature và ACTION.

```text
FROM:
Executor task → graph.ainvoke

CALL:
GraphExecutor._invoke — src/framework/runtime/executor.py:87–94

INPUT:
graph_input,context,config

ACTION:
Bind ExecutionContext bằng context manager rồi await compiled graph;binding được restore khi thoát.

RETURN:
Xem signature/code block: typed output/dict hoặc exception;không thêm fallback ngoài source.

BACK TO:
Executor task → graph.ainvoke;tiếp tục operation trong caller hoặc propagate exception.
```

## GraphExecutor._cancel_invocation

Nguồn [src/framework/runtime/executor.py:97–102](../../../src/framework/runtime/executor.py).

```python
    async def _cancel_invocation[T](invocation: asyncio.Task[T]) -> None:
        invocation.cancel()
        try:
            await invocation
        except asyncio.CancelledError:
            pass
```

- READ: invocation asyncio.Task
- WRITE/TRANSFORM: Locals/models/updates đúng code block bên trên
- CONDITION/ACTION/WHY: Cancel awaited graph task và await cleanup; chỉ suppress CancelledError. Không đảm bảo synchronous worker thread dừng ngay.
- RESULT/NEXT: Quay lại Timeout/cancel path → task.cancel; return annotation/raise path thể hiện trong signature và ACTION.

```text
FROM:
Timeout/cancel path → task.cancel

CALL:
GraphExecutor._cancel_invocation — src/framework/runtime/executor.py:97–102

INPUT:
invocation asyncio.Task

ACTION:
Cancel awaited graph task và await cleanup;chỉ suppress CancelledError. Không đảm bảo synchronous worker thread dừng ngay.

RETURN:
Xem signature/code block: typed output/dict hoặc exception;không thêm fallback ngoài source.

BACK TO:
Timeout/cancel path → task.cancel;tiếp tục operation trong caller hoặc propagate exception.
```

## RetrievalService.__init__: giữ dependencies và config

Nguồn [src/application/services/retrieval_service.py:157–190](../../../src/application/services/retrieval_service.py).

```python
    def __init__(
        self,
        sparse_retriever: SparseRetriever,
        chunks: ChunkReader,
        sources: SourceReader,
        indexes: IndexReader,
        tokenizer: Callable[[str], tuple[str, ...]],
        *,
        sparse_index_name: str = DEFAULT_SPARSE_INDEX,
        timeout_seconds: float = 30,
        dense_retriever: LegalRetriever | None = None,
        query_embedder: QueryEmbedder | None = None,
        dense_indexes: IndexReader | None = None,
        dense_index_name: str = DEFAULT_DENSE_INDEX,
        hybrid_config: HybridConfig | None = None,
        rerank_config: RerankConfig | None = None,
        pair_scorer: PairScorer | None = None,
    ) -> None:
        if not sparse_index_name.strip() or not 0 < timeout_seconds < float("inf"):
            raise ValueError("index name and finite positive timeout are required")
        self._sparse = sparse_retriever
        self._chunks = chunks
        self._sources = sources
        self._indexes = indexes
        self._tokenizer = tokenizer
        self._index_name = sparse_index_name.strip()
        self._timeout = timeout_seconds
        self._dense = dense_retriever
        self._query_embedder = query_embedder
        self._dense_indexes = dense_indexes
        self._dense_index_name = dense_index_name
        self._hybrid_config = hybrid_config or HybridConfig()
        self._rerank_config = rerank_config or RerankConfig()
        self._pair_scorer = pair_scorer
```

- READ: read ports/tokenizer/configs
- WRITE/TRANSFORM: self._sparse/_chunks/_sources/_indexes/_dense/_query_embedder/_timeout/...
- CONDITION/ACTION/WHY: Validate index name và finite positive timeout; dùng default configs khi không supplied. Không I/O/model inference ở constructor service.
- RESULT/NEXT: search sử dụng fields được inject; service object shared theo pipeline.

## RetrievalService.search: validation và Hybrid /rerank delegation

Nguồn [src/application/services/retrieval_service.py:192–220](../../../src/application/services/retrieval_service.py).

```python
    async def search(self, request: RetrievalRequest) -> RetrievalResponse | HybridRetrievalResponse:
        """Return a classified outcome; malformed requests never invoke dependencies."""
        request = RetrievalRequest.model_validate(request)
        if request.mode == RetrievalMode.HYBRID:

            async def run_hybrid(branch_request: RetrievalRequest) -> HybridRetrievalResponse:
                return await search_hybrid(
                    branch_request,
                    run_branch=self.search,
                    sparse_indexes=self._indexes,
                    dense_indexes=self._dense_indexes,
                    sparse_index_name=self._index_name,
                    dense_index_name=self._dense_index_name,
                    dense_configured=self._dense is not None and self._query_embedder is not None,
                    config=self._hybrid_config,
                    timeout_seconds=self._timeout,
                )

            if self._rerank_config.enabled:
                return await search_reranked(
                    request,
                    run_hybrid=run_hybrid,
                    scorer=self._pair_scorer,
                    config=self._rerank_config,
                    sparse_indexes=self._indexes,
                    dense_indexes=self._dense_indexes,
                    hybrid_config=self._hybrid_config,
                )
            return await run_hybrid(request)
```

- READ: typed request, self configs
- WRITE/TRANSFORM: validated request, closure run_hybrid
- CONDITION/ACTION/WHY: Request mode HYBRID dispatch helper; rerank enabled dùng search_reranked. Helper nhận self.search để chạy branches, không Search Agent làm RRF.
- RESULT/NEXT: Return native subtype hoặc tiếp 221 cho bm25/dense.

## Single backend: ID, try, readiness, deadline, BM25

Nguồn [src/application/services/retrieval_service.py:221–247](../../../src/application/services/retrieval_service.py).

```python
        request_id = new_id()
        index: _SparseIndex | _DenseIndex | None = None
        evidence: tuple[UnifiedEvidence, ...] = ()
        error: RetrievalErrorDetail | None = None
        stage = "validation"
        try:
            if request.mode == RetrievalMode.DENSE and (
                self._dense is None or self._query_embedder is None or self._dense_indexes is None
            ):
                raise _failure(
                    ErrorCategory.CONFIGURATION_ERROR,
                    "MODE_NOT_CONFIGURED",
                    stage,
                    "Dense retrieval requires a local query encoder and read adapters.",
                )
            async with asyncio.timeout(self._timeout):
                if request.mode == RetrievalMode.BM25:
                    stage = "preprocessing"
                    terms = self._prepare_sparse_terms(request.query.strip())
                    stage = "index_preflight"
                    index = await self._read_and_validate_index()
                    stage = "search"
                    hits = await self._search_sparse(request, terms)
                    stage = "hydration"
                    evidence = await self._hydrate_sparse_hits(hits, request)
                    stage = "index_postflight"
                    await self._check_index_unchanged(index)
```

- READ: request và self dependencies
- WRITE/TRANSFORM: response UUID, index/evidence/error locals, stage
- CONDITION/ACTION/WHY: Config Dense guard; asyncio.timeout; BM25 preprocess/index/search/hydrate/postcheck. Đây là service boundary, không mở rộng thành toàn algorithm tutorial.
- RESULT/NEXT: Dense branch 248–275 hoặc exception handling 276.

## Single backend: Dense boundary

Nguồn [src/application/services/retrieval_service.py:248–275](../../../src/application/services/retrieval_service.py).

```python
                else:
                    stage = "index_preflight"
                    index = await self._read_dense_index()
                    stage = "encoding"
                    vector = await self._query_embedder.encode_query(request.query.strip())
                    try:
                        vector = validate_query_vector(vector)
                    except (TypeError, ValueError) as failure:
                        raise _failure(
                            ErrorCategory.MODEL_UNAVAILABLE,
                            "INVALID_EMBEDDING",
                            stage,
                            "Query encoder returned an invalid normalized vector.",
                        ) from failure
                    stage = "search"
                    dense_hits = await self._dense.search(
                        VectorSearchRequest(
                            dense_index_name=self._dense_index_name,
                            query_embedding=vector,
                            top_k=request.top_k,
                            as_of_date=request.as_of_date,
                            allowed_usage_policies=request.allowed_usage_policies,
                        )
                    )
                    stage = "hydration"
                    evidence = await self._map_dense_evidence(dense_hits, request, index)
                    stage = "index_postflight"
                    await self._check_dense_index_unchanged(index)
```

- READ: request.query/date/policy/ top_k; encoder/vector ports
- WRITE/TRANSFORM: vector, dense_hits, evidence, index observations
- CONDITION/ACTION/WHY: Read index trước encoding; strip query ở encoder boundary; validate vector; vector request; map evidence; closing index check.
- RESULT/NEXT: Typed failure catch hoặc response return.

## Service classified failure và native response

Nguồn [src/application/services/retrieval_service.py:276–305](../../../src/application/services/retrieval_service.py).

```python
        except RetrievalServiceError as failure:
            error = failure.detail
        except TimeoutError:
            error = RetrievalErrorDetail(
                category=ErrorCategory.TIMEOUT,
                code="RETRIEVAL_TIMEOUT",
                stage=stage,
                message="Retrieval exceeded its deadline.",
                retryable=True,
            )
        except (DatabaseRepositoryError, RetrievalError) as failure:
            invalid_response = isinstance(failure.__cause__, ValidationError)
            error = RetrievalErrorDetail(
                category=ErrorCategory.INCONSISTENT_EVIDENCE if invalid_response else ErrorCategory.DATABASE_FAILURE,
                code="INVALID_REPOSITORY_RESPONSE" if invalid_response else "DATABASE_READ_FAILED",
                stage=stage,
                message="Repository returned invalid data." if invalid_response else "Database read failed.",
            )
        return RetrievalResponse(
            **request.model_dump(),
            request_id=request_id,
            query_used=request.query.strip(),
            selected_index_name=self._index_name if request.mode == RetrievalMode.BM25 else self._dense_index_name,
            index=index.identity() if index is not None else None,
            status="FAILED" if error else "OK" if evidence else "NO_MATCH",
            evidence=() if error else evidence,
            warnings=() if error else self._evidence_warnings(evidence),
            error=error,
            retrieved_at=utc_now(),
        )
```

- READ: known exceptions, stage, index/evidence
- WRITE/TRANSFORM: safe RetrievalErrorDetail và RetrievalResponse
- CONDITION/ACTION/WHY: Catches được liệt kê rõ, không catch arbitrary RuntimeError; FAILED bỏ evidence; OK/ NO_MATCH theo evidence. query raw echo, query_used strip; warnings do service derive.
- RESULT/NEXT: Search 47 nhận đúng object, append 48. Unexpected exception propagate ra Search.

## Call boundary Search chính

```text
FROM:
QuerySearch.search (src/query_search_bootstrap.py20–21) hoặc QuerySearchNodes.search (graphs/legal_qa.py39–54)

CALL:
await search(plan, retrieval, options) — Search agent38–56

INPUT:
plan dict sáu fields; injected RetrievalService; trusted SearchOptions

ACTION:
Validate plan/options;clarification guard;eager requests;sequential await;append native responses;stop on FAILED

RETURN:
SearchState dict với raw plan/typed tuples/status;hoặc validation/dependency exception

BACK TO:
Standalone return SearchState;graph tạo JudgeHandoff.from_search rồi state update/END
```

## Các inherited/generated operations

 QueryPlan. model_validate, SearchOptions. model_validate, RetrievalRequest constructor và model_dump / model_dump_json do Pydantic cung cấp; không có project function body riêng để invent line range. Model schemas/validators được chỉ ra ở 02/03/05/07/09. TypedDict không tự có Pydantic runtime validation. asyncio/ SDK internals chỉ được mô tả theo call boundary mà source cho thấy.

 Search module không có helper hidden search_many/fuse_responses/select_mode. Toàn bộ orchestration chỉ 38–56. Downstream helper signatures/ranges ở 18; algorithms sâu tham khảo guides retrieval-learning liên kết ở 06.

## Bảng vi mô cho những functions nhiều nhánh

Các rows dưới đây tham chiếu snippets nguyên văn cùng source/range ở trên. Đây là diễn giải theo thứ tự thực thi, không phải giả intermediate values đã observe.

| Function/block | Read → write | Condition/transformation/next |
|---|---|---|
| SearchOptions.nonblank_policies 26 |values → generator bool |Bất kỳ policy.strip falsy thì raiseValueError 27; Pydantic wrap thành ValidationError |
| SearchOptions 28 |values → ordered dict keys →tuple |Strip mỗi policy, dedup stable order; return normalized tuple |
|Request.nonblank_query 35–37 |value → strip check |Blank raise 36, else return raw value 37; không trim payload |
|Request.policies 42–44 |values → same guard/dedup |Guard trước; strip/dedup sau; không lowercase |
| QuerySearch.search 21 |question → understand return → Search args |Synchronous Query phải thành công trước await Search; exception Query chặn Search |
|create_query_search 34–42 |options/settings/configs → service →container |Validate options trước construction; factory error propagate; container chỉ tạo saufactorysuccess |
| QuerySearchNodes.search 40 |state.plan, pipeline →result |Await hết Search trước khi packet constructor chạy |
|Graphnode 41–47 |state question/IDs, options, result →handoff | request_id dùngget nullable; question/ run_id indexing có thể KeyError nếu rawstate thiếu |
|Graphnode 48 |handoff.status →status | READY đổi SEARCH_COMPLETED; khác giữ nguyên |
|Graphnode 49–54 |result, packet, error details →update |Errors list chỉ codes; return không mutate inputstate trực tiếp |
|from_search 76–82 |result.status, response.evidence →status | FAILED ưu tiên; elseany nonempty→ READY; else NO_MATCH |
|from_search 83–93 |result fields/context →cls instance | Pydantic schemas rồi aftervalidator; throw nếu không nhất quán |
|validate_context 45–48 |question/original, clarification, counts |Mismatch/clarifying→raise 46; count mismatch/too many→raise 48 |
|validate_context 49–55 |zip plan.subqueries/requests/responses |Check requesttext 50; optionsequality 52; responseecho 54; raise riêng 51/53/55 |
|validate_context 56–61 |last/earlier statuses, evidence →failed/expected |Earlierfailure→raise 58; deriveexpected 59; status mismatch→raise 61 |
|validate_context 62–64 |failed flag, totalcounts |Nonfailedphải xử lýđủ; elsereturnself không sửa fields |
|Executor 39–43 |timeout/context/lifecycle →running lifecycle |Nonpositive timeout raise 40; pre-cancel token raise 41 trướcstart; start 43 |
|Executor 44–51 |graph input/context/token →two tasks, done set |Schedule invocation và watcher; waitFIRST_ COMPLETED với timeout |
|Executor 52–55 |done empty →cancel invocation, lifecyclefailed |Deadline hết:await cleanup rồi TimeoutError; không graph state return |
|Executor 56–63 |cancellation done và invocation notdone |Cancelinvocation, lifecyclecancel, derive reason, ExecutionCancelledError |
|Executor 65–67 |invocation task result →output |Nếu task raise thì tới catches; else succeed lifecycle rồi return |
|Executor 68–77 | CancelledError /Exception và current lifecycle |Chỉ transition nếu cònRUNNING; cancel chưadoneinvocation; raisegiữexception |
|Executor 78–84 |cancellation watcher task |Finallycancelwatcher nếu cònpending, await vàsuppress CancelledError; không suppress arbitrary failures |
|_invoke 93–94 |context/input/config →bound invocation |Context manager bind/restores quanh graph.ainvoke; async tasks inherit context đúngbinding |
|_cancel_invocation 98–102 |invocation task |cancel rồi await; only CancelledError suppressed, không kill thread |
|retrievalbootstrap 35–41 |settings.url/key → SDK client |Missing reject trướcallocation; secret get chỉ trong process; clienttimeouts/sessionflags explicit |
|retrievalbootstrap 42–55 |densepath/rerankenabled →optional wrappers |No Dense paththì None; rerankenabledthìmớitạo scorer; wrapperkhácweightload |
|retrievalbootstrap 56–70 |adapters/tokenizer/wrappers/config →service |Constructor receives shared ports; no RPC/inference ở Search construction |

### Validator call-boundary dossiers

```text
FROM:
Search.search40 / QuerySearch bootstrap34
CALL:
QueryPlan.model_validate / SearchOptions.model_validate
INPUT:
Raw plan dict / trusted options object hoặc dictionary
ACTION:
Pydantic fields + project validators;không gọi retrieval
RETURN:
Typed model hoặc ValidationError
BACK TO:
Search guard42 hoặc bootstrap factory35
```

```text
FROM:
Search.search44 tuple comprehension
CALL:
RetrievalRequest constructor →nonblank_query34–37 vàpolicies41–44
INPUT:
Subquery.text vàoptions.model_dump Python values
ACTION:
Typed constraints,blank check;policy strip/dedup;query giữ raw
RETURN:
Request object hoặc ValidationError trước mọi service calls
BACK TO:
Comprehension tiếp theo;chỉ khi toàn tuple thành công mới Search46
```

```text
FROM:
Graph Search node41 →JudgeHandoff.from_search83
CALL:
JudgeHandoff constructor →validate_context44–64
INPUT:
Context,typed requests/responses,derived status
ACTION:
Schema validation và consistency guards theo order
RETURN:
Packet hợp lệ hoặc ValidationError
BACK TO:
Graph node48 map status,return update49–54;exception thìpropagate
```
