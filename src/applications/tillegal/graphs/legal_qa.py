"""LangGraph Query/Search boundary ending before legal sufficiency assessment."""

from typing import Literal

from langgraph.graph import END, START

from src.applications.tillegal.agents.query.agent import understand
from src.applications.tillegal.agents.search.agent import search
from src.applications.tillegal.state.legal_qa_state import JudgeHandoff, LegalQAState
from src.framework.graphs.compiler import compile_graph
from src.framework.graphs.factory import create_state_graph
from src.framework.runtime.execution_context import ExecutionContext
from src.framework.runtime.executor import GraphExecutor
from src.framework.runtime.lifecycle import ExecutionLifecycle
from src.query_search_bootstrap import QuerySearch


class QuerySearchNodes:
    """Reuse agent entrypoints with application-scoped dependencies."""

    def __init__(self, pipeline: QuerySearch) -> None:
        self.pipeline = pipeline

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

    @staticmethod
    def route_query(state: LegalQAState) -> Literal["search", "end"]:
        return "end" if state["clarification"] else "search"

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


class QuerySearchWorkflow:
    """Compile once; execute fresh state per request using the shared executor."""

    def __init__(self, pipeline: QuerySearch) -> None:
        self.graph = compile_query_search_graph(pipeline)
        self.executor = GraphExecutor()

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
