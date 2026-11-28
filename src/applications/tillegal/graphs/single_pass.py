"""Single-pass QA graph; agent semantics and legacy Query/Search stay unchanged."""

import asyncio
from copy import deepcopy
from dataclasses import asdict
from datetime import date
from typing import Any, Literal
from uuid import uuid4

from langgraph.graph import END, START
from pydantic import BaseModel, ConfigDict, Field, model_validator

from src.applications.tillegal.agents.judge.adapter import (
    AdaptedJudgeInput,
    JudgeAdapterError,
    NativeJudgeResult,
    evaluate_search,
)
from src.applications.tillegal.agents.judge.agent import JudgeAgent
from src.applications.tillegal.agents.query.agent import QueryInputError
from src.applications.tillegal.agents.query.semantic import QueryAnalysisError
from src.applications.tillegal.agents.response.adapter import adapt_judge
from src.applications.tillegal.agents.response.agent import SummaryAgent
from src.applications.tillegal.agents.response.schemas import SummaryError, validate_public_output
from src.applications.tillegal.graphs.legal_qa import QuerySearchNodes
from src.applications.tillegal.state.legal_qa_state import LegalQAState
from src.framework.graphs.compiler import compile_graph
from src.framework.graphs.factory import create_state_graph
from src.framework.runtime.execution_context import ExecutionContext
from src.framework.runtime.executor import GraphExecutor
from src.framework.runtime.lifecycle import ExecutionLifecycle
from src.query_search_bootstrap import QuerySearch


class SinglePassOutput(BaseModel):
    """Public envelope: execution completion never implies legal verification."""

    model_config = ConfigDict(extra="forbid")
    schema_version: Literal["1"] = "1"
    request_id: str = Field(min_length=1)
    run_id: str = Field(min_length=1)
    workflow_status: Literal["COMPLETED", "CLARIFICATION_REQUIRED", "ERROR"]
    clarification: str | None = None
    judge_status: Literal["SUFFICIENT", "INSUFFICIENT", "ERROR"] | None = None
    summary_output: dict[str, Any] | None = None
    draft_version: int | None = None
    verification_status: Literal["NOT_RUN"] = "NOT_RUN"
    limitations: list[str]
    as_of_date: date
    stop_reason: str = Field(min_length=1)
    errors: list[str]
    judge_carrier: dict[str, Any] | None = None
    summary_telemetry: dict[str, Any]
    trace: list[str]

    @model_validator(mode="after")
    def validate_links(self) -> "SinglePassOutput":
        summary = self.summary_output
        if self.judge_carrier is not None:
            carrier = self.judge_carrier
            try:
                adapt_judge(
                    NativeJudgeResult(
                        AdaptedJudgeInput(**carrier["adapted"]), carrier["judge_result"], carrier["telemetry"]
                    )
                )
            except (KeyError, TypeError, ValueError, SummaryError) as exc:
                raise ValueError("Invalid native Judge carrier") from exc
            if carrier["judge_result"]["status"] != self.judge_status:
                raise ValueError("Judge status mismatch")
            context = carrier["adapted"]["judge_input"]
            if context["request_id"] != self.request_id or context["as_of_date"] != self.as_of_date.isoformat():
                raise ValueError("Judge context mismatch")
        if summary is not None:
            validate_public_output(summary)
            if (summary["request_id"], summary["as_of_date"], summary["draft_version"]) != (
                self.request_id,
                self.as_of_date.isoformat(),
                self.draft_version,
            ):
                raise ValueError("Summary context mismatch")
            if summary["status"] == "ERROR" and self.workflow_status != "ERROR":
                raise ValueError("Summary error must fail workflow")
            if self.judge_carrier is None:
                raise ValueError("Summary requires carrier")
            evidence = self.judge_carrier["adapted"]["evidence_map"]
            if any(c["evidence_id"] not in evidence for c in summary["citations"]):
                raise ValueError("Citation evidence missing")
        elif self.draft_version is not None:
            raise ValueError("No summary version without summary")
        if self.workflow_status == "COMPLETED" and (summary is None or self.judge_status == "ERROR"):
            raise ValueError("Completed workflow requires successful Summary")
        return self


class SinglePassState(LegalQAState, total=False):
    judge_carrier: NativeJudgeResult
    summary_result: dict[str, Any]
    summary_telemetry: dict[str, Any]
    stop_reason: str
    node_trace: list[str]
    output: SinglePassOutput


class SinglePassNodes:
    def __init__(self, pipeline: QuerySearch, judge: JudgeAgent, summary: SummaryAgent):
        self.base = QuerySearchNodes(pipeline)
        self.pipeline, self.judge_agent, self.summary_agent = pipeline, judge, summary

    @staticmethod
    def update(state, node, **values):
        return {"node_trace": [*state.get("node_trace", []), node], **values}

    async def query(self, state):
        try:
            if self.pipeline.query_agent is not None:
                result = await self.base.query_semantic(state)
            else:
                result = self.base.query(state)
            return self.update(state, "query", **result)
        except (QueryInputError, QueryAnalysisError):
            return self.update(state, "query", status="ERROR", errors=["QUERY_FAILED"], stop_reason="query_error")

    @staticmethod
    def route_query(state):
        return "finalize" if state.get("clarification") or state.get("status") == "ERROR" else "search"

    async def search(self, state):
        result = await self.base.search(state)
        return self.update(state, "search", **result)

    @staticmethod
    def route_search(state):
        result = state["search_result"]
        return "judge" if result["status"] == "COMPLETED" and result["completeness"] == "COMPLETE" else "finalize"

    async def judge(self, state):
        search = deepcopy(state["search_result"])
        try:
            carrier = await asyncio.to_thread(
                evaluate_search,
                search,
                judge=self.judge_agent,
                request_id=state["request_id"],
                options=self.pipeline.options,
                search_rounds_completed=1,
                query_history=[str(r.request_id) for r in search["responses"]],
                query_text_history=list(dict.fromkeys(r.query for r in search["requests"])),
            )
        except JudgeAdapterError as exc:
            return self.update(state, "judge", status="ERROR", errors=[exc.code], stop_reason="judge_adapter_error")
        failed = carrier.judge_result["status"] == "ERROR"
        reason = (
            "judge_error"
            if failed
            else (
                "single_pass_insufficient"
                if carrier.judge_result["status"] == "INSUFFICIENT"
                else "single_pass_completed"
            )
        )
        return self.update(
            state,
            "judge",
            judge_carrier=carrier,
            stop_reason=reason,
            status="ERROR" if failed else "JUDGE_COMPLETED",
            errors=[carrier.judge_result["error_code"]] if failed else [],
        )

    @staticmethod
    def route_judge(state):
        return "finalize" if state.get("status") == "ERROR" else "summary"

    async def summary(self, state):
        # The worker receives a detached carrier; cancelled work cannot mutate graph state.
        carrier = deepcopy(state["judge_carrier"])
        reason = state["stop_reason"]

        def generate():
            telemetry = {}
            value = adapt_judge(carrier, stop_reason=reason, draft_version=1)
            return self.summary_agent.summarize(value, telemetry=telemetry), telemetry

        try:
            result, telemetry = await asyncio.to_thread(generate)
        except SummaryError as exc:
            return self.update(state, "summary", status="ERROR", errors=[exc.code], stop_reason="summary_adapter_error")
        failed = result["status"] == "ERROR"
        return self.update(
            state,
            "summary",
            summary_result=result,
            summary_telemetry=telemetry,
            status="ERROR" if failed else "SUMMARY_COMPLETED",
            stop_reason="summary_error" if failed else reason,
            errors=[result["error"]["code"]] if failed else [],
        )

    def finalize(self, state):
        summary = state.get("summary_result")
        carrier = state.get("judge_carrier")
        clarification = state.get("clarification")
        reason = state.get("stop_reason")
        failed = state.get("status") == "ERROR"
        if clarification:
            reason = "clarification_required"
        elif not reason:
            failed, reason = True, "search_incomplete"
        limitations = ["VERIFY_NOT_RUN"]
        if state.get("search_result") is not None:
            limitations += list(state["search_result"]["warnings"])
        if carrier is not None:
            limitations += carrier.adapted.judge_input["context"]["limitations"]
            limitations += carrier.judge_result["missing_items"]
            if carrier.judge_result["status"] == "INSUFFICIENT":
                limitations += ["JUDGE_INSUFFICIENT", "SINGLE_PASS_NO_REFINEMENT"]
        if summary is not None:
            limitations += summary["limitations"]
        trace = [*state.get("node_trace", []), "finalize"]
        errors = list(state.get("errors", []))
        if reason == "search_incomplete" and not errors:
            errors = ["SEARCH_NOT_COMPLETE"]
        output = SinglePassOutput(
            request_id=state["request_id"],
            run_id=state["run_id"],
            workflow_status="CLARIFICATION_REQUIRED" if clarification else "ERROR" if failed else "COMPLETED",
            clarification=clarification,
            judge_status=carrier.judge_result["status"] if carrier else None,
            summary_output=deepcopy(summary),
            draft_version=summary["draft_version"] if summary else None,
            limitations=list(dict.fromkeys(limitations)),
            as_of_date=self.pipeline.options.as_of_date,
            stop_reason=reason,
            errors=errors,
            judge_carrier=asdict(carrier) if carrier else None,
            summary_telemetry=deepcopy(state.get("summary_telemetry", {})),
            trace=trace,
        )
        return {"output": output, "node_trace": trace, "status": output.workflow_status}


def compile_single_pass_graph(pipeline, judge, summary):
    nodes = SinglePassNodes(pipeline, judge, summary)
    builder = create_state_graph(SinglePassState)
    for name in ("query", "search", "judge", "summary", "finalize"):
        builder.add_node(name, getattr(nodes, name))
    builder.add_edge(START, "query")
    builder.add_conditional_edges("query", nodes.route_query, {"search": "search", "finalize": "finalize"})
    builder.add_conditional_edges("search", nodes.route_search, {"judge": "judge", "finalize": "finalize"})
    builder.add_conditional_edges("judge", nodes.route_judge, {"summary": "summary", "finalize": "finalize"})
    builder.add_edge("summary", "finalize")
    builder.add_edge("finalize", END)
    return compile_graph(builder, name="qa-single-pass")


class SinglePassWorkflow:
    """Compile once; each execution owns fresh state. Services must support concurrent use."""

    def __init__(self, pipeline: QuerySearch, judge: JudgeAgent, summary: SummaryAgent) -> None:
        self.graph = compile_single_pass_graph(pipeline, judge, summary)
        self.executor = GraphExecutor()

    async def execute(
        self,
        question: str,
        context: ExecutionContext,
        *,
        timeout_seconds: float = 60,
        lifecycle: ExecutionLifecycle | None = None,
    ) -> SinglePassOutput:
        if context.request_id is None:
            context = ExecutionContext(
                run_id=context.run_id,
                request_id=str(uuid4()),
                parent_run_id=context.parent_run_id,
                metadata=context.metadata,
                cancellation_token=context.cancellation_token,
            )
        initial = {"question": question, "request_id": context.request_id, "run_id": context.run_id}
        state = await self.executor.execute(
            self.graph,
            initial,
            context,
            timeout_seconds=timeout_seconds,
            lifecycle=lifecycle,
        )
        return state["output"]
