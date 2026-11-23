"""Synthetic offline Search handoff observations; no application changes or external I/O."""

import asyncio
import hashlib
import inspect
import json
import sys
from copy import deepcopy
from datetime import UTC, date, datetime
from pathlib import Path
from uuid import UUID

from langsmith import tracing_context
from pydantic import BaseModel, ValidationError

from src.applications.tillegal.agents.query.agent import QueryPlan, understand
from src.applications.tillegal.agents.search.agent import SearchOptions, search
from src.applications.tillegal.graphs.legal_qa import QuerySearchNodes, QuerySearchWorkflow
from src.applications.tillegal.retrieval.contracts import RetrievalResponse, RetrievalWarning
from src.applications.tillegal.retrieval.errors import RetrievalErrorDetail
from src.applications.tillegal.state.legal_qa_state import JudgeHandoff
from src.framework.runtime.execution_context import ExecutionContext
from src.framework.runtime.lifecycle import ExecutionLifecycle
from src.query_search_bootstrap import QuerySearch
from tests.unit.applications.tillegal.retrieval.test_hybrid_service import hybrid_service
from tests.unit.applications.tillegal.retrieval.test_reranking import configured
from tests.unit.applications.tillegal.test_query_search_multimode import options

OUT = Path(".docs/agent-development/task-06b-search-knowledge-handoff/evidence")


def dump(value):
    if isinstance(value, BaseModel):
        return value.model_dump(mode="json")
    if isinstance(value, dict):
        return {key: dump(item) for key, item in value.items()}
    if isinstance(value, (tuple, list)):
        return [dump(item) for item in value]
    if isinstance(value, (date, datetime, UUID)):
        return str(value)
    return value


def plan_for(*texts, clarification=None):
    return QueryPlan(
        original="; ".join(texts),
        intent="legal_question",
        domain="unknown",
        temporal_scope=[],
        subqueries=[{"text": text, "purpose": "question_part"} for text in texts],
        clarification=clarification,
    ).model_dump()


def no_match(request, number, failed=False):
    return RetrievalResponse(
        **request.model_dump(),
        request_id=UUID(int=number),
        query_used=request.query.strip(),
        selected_index_name="synthetic-fixture",
        index=None,
        status="FAILED" if failed else "NO_MATCH",
        retrieved_at=datetime(2026, 11, 21, tzinfo=UTC),
        warnings=(RetrievalWarning(code="FIXTURE_WARNING", message="Synthetic observation"),),
        error=RetrievalErrorDetail(
            category="DATABASE_FAILURE", code="FIXTURE_FAILURE", stage="search", message="Synthetic failure"
        )
        if failed
        else None,
    )


class Recorder:
    def __init__(self, backend=None, *, fail_at=None, exception_at=None, mismatch=False):
        self.backend = backend
        self.fail_at = fail_at
        self.exception_at = exception_at
        self.mismatch = mismatch
        self.requests = []
        self.responses = []
        self.events = []
        self.active = 0
        self.max_active = 0

    async def search(self, request):
        number = len(self.requests) + 1
        self.requests.append(request)
        self.events.append({"event": "start", "number": number, "query": request.query})
        self.active += 1
        self.max_active = max(self.max_active, self.active)
        try:
            await asyncio.sleep(0)
            if self.exception_at == number:
                raise RuntimeError("Synthetic dependency exception")
            if self.fail_at == number or self.backend is None:
                response = no_match(request, number, self.fail_at == number)
            else:
                response = await self.backend.search(request)
            if self.mismatch:
                response = response.model_copy(update={"query": "different synthetic query"})
            self.responses.append(response)
            self.events.append({"event": "return", "number": number, "status": response.status})
            return response
        finally:
            self.active -= 1


def error_data(error):
    result = {"type": type(error).__name__}
    if isinstance(error, ValidationError):
        result["details"] = [{"type": row["type"], "loc": list(row["loc"])} for row in error.errors()]
    else:
        result["message"] = str(error)
    return result


async def observe(name, plan, opts, service):
    row = {
        "id": name,
        "label": "OBSERVED",
        "backend": "synthetic service"
        if service.backend is None
        else "real RetrievalService with fake read/model ports",
        "input_plan": dump(plan),
        "options": dump(opts),
    }
    before = deepcopy(plan)
    snapshots = []

    def tracer(frame, event, arg):
        if frame.f_code is search.__code__ and event == "line":
            snapshots.append(
                {
                    "line": frame.f_lineno,
                    "locals": {
                        key: dump(frame.f_locals[key])
                        for key in ("parsed", "options", "requests", "responses", "response")
                        if key in frame.f_locals
                    },
                }
            )
        return tracer

    previous = sys.gettrace()
    sys.settrace(tracer)
    try:
        state = await search(plan, service, opts)
        row["search_state"] = dump(state)
        row["response_types"] = [type(response).__name__ for response in state["responses"]]
        row["plan_identity_preserved"] = state["plan"] is plan
        row["response_identity_preserved"] = all(
            actual is expected for actual, expected in zip(state["responses"], service.responses, strict=True)
        )
        row["evidence_payload_hashes_match"] = all(
            hashlib.sha256(item.content.encode("utf-8")).hexdigest() == item.content_sha256
            for response in state["responses"]
            for item in response.evidence
        )
        if state["status"] != "CLARIFICATION_REQUIRED":
            try:
                handoff = JudgeHandoff.from_search(
                    question=plan["original"],
                    request_id="fixture-request",
                    run_id="fixture-run",
                    options=opts,
                    result=state,
                )
                encoded = handoff.model_dump_json()
                restored = JudgeHandoff.model_validate_json(encoded)
                row["handoff"] = dump(handoff)
                row["handoff_warning_codes"] = [warning.code for warning in handoff.warnings]
                row["handoff_error_codes"] = [error.code for error in handoff.errors]
                row["handoff_roundtrip_equal"] = restored == handoff
                row["handoff_roundtrip_types"] = [type(response).__name__ for response in restored.responses]
            except Exception as error:
                row["handoff_exception"] = error_data(error)
    except Exception as error:
        row["exception"] = error_data(error)
    finally:
        sys.settrace(previous)
    row.update(
        requests_observed=dump(service.requests),
        responses_observed=dump(service.responses),
        call_events=service.events,
        max_active_calls=service.max_active,
        plan_unchanged=plan == before,
        source_line_snapshots=snapshots,
    )
    return row


async def graph_observe(name, question, mode, service):
    lifecycle = ExecutionLifecycle()
    row = {
        "id": name,
        "label": "OBSERVED",
        "backend": "real service/fake ports" if service.backend else "synthetic service",
        "question": question,
        "options": dump(options(mode)),
    }
    flow = QuerySearchWorkflow(QuerySearch(service, options(mode)))
    try:
        state = await flow.execute(
            question,
            ExecutionContext(run_id=name, request_id="request-" + name),
            timeout_seconds=2,
            lifecycle=lifecycle,
        )
        row["state"] = dump(state)
        if state.get("handoff"):
            packet = state["handoff"]
            row["handoff_roundtrip_equal"] = JudgeHandoff.model_validate_json(packet.model_dump_json()) == packet
            row["response_types"] = [type(response).__name__ for response in packet.responses]
    except Exception as error:
        row["exception"] = error_data(error)
    row.update(
        lifecycle=lifecycle.snapshot.status.value,
        requests=dump(service.requests),
        responses=dump(service.responses),
        call_events=service.events,
    )
    return row


async def main():
    rows = []
    for mode in ("bm25", "dense", "hybrid", "rerank"):
        service, *_ = configured() if mode == "rerank" else hybrid_service()
        rows.append(await observe("one_" + mode, understand("Trích dẫn: thuế"), options(mode), Recorder(service)))
    service, *_ = hybrid_service()
    rows.append(
        await observe("multi_success", plan_for("thuế", "hợp đồng", "bảo hiểm"), options("bm25"), Recorder(service))
    )
    rows.append(await observe("duplicate_calls", plan_for("thuế", "thuế"), options("bm25"), Recorder()))
    rows.append(await observe("clarification", understand("Có được không?"), options("bm25"), Recorder()))
    rows.append(await observe("no_match", plan_for("thuế"), options("bm25"), Recorder()))
    rows.append(
        await observe("failed_first", plan_for("thuế", "hợp đồng", "bảo hiểm"), options("bm25"), Recorder(fail_at=1))
    )
    service, *_ = hybrid_service()
    rows.append(
        await observe(
            "partial_failure", plan_for("thuế", "hợp đồng", "bảo hiểm"), options("bm25"), Recorder(service, fail_at=2)
        )
    )
    service, *_ = hybrid_service()
    rows.append(
        await observe(
            "exception_second",
            plan_for("thuế", "hợp đồng", "bảo hiểm"),
            options("bm25"),
            Recorder(service, exception_at=2),
        )
    )
    rows.append(await observe("missing_plan", {}, options("bm25"), Recorder()))
    rows.append(await observe("none_plan", None, options("bm25"), Recorder()))
    for name, change in [
        ("empty_subqueries", {"subqueries": []}),
        ("empty_text", {"subqueries": [{"text": "", "purpose": "lookup"}]}),
        ("unsupported_intent", {"intent": "unknown"}),
        ("five_subqueries", {"subqueries": [{"text": "thuế", "purpose": "topic"}] * 5}),
        ("clarification_invalid_plan", {"clarification": "Hỏi lại", "subqueries": []}),
    ]:
        rows.append(await observe(name, {**plan_for("thuế"), **change}, options("bm25"), Recorder()))
    rows.append(await observe("tab_second", plan_for("thuế", "\t", "hợp đồng"), options("bm25"), Recorder()))
    rows.append(await observe("spaces_retained", plan_for("  thuế  "), options("bm25"), Recorder()))
    rows.append(
        await observe("extra_plan_field", {**plan_for("thuế"), "confidence": 0.99}, options("bm25"), Recorder())
    )
    rows.append(await observe("context_mismatch", plan_for("thuế"), options("bm25"), Recorder(mismatch=True)))
    for name, change in [
        ("top_k_zero", {"top_k": 0}),
        ("top_k_bool", {"top_k": True}),
        ("top_k_string", {"top_k": "2"}),
        ("missing_mode", {"mode": None}),
        ("rerank_mode", {"mode": "rerank"}),
        ("invalid_date", {"as_of_date": "2024-02-31"}),
        ("missing_date", {"as_of_date": None}),
        ("empty_policy", {"allowed_usage_policies": ()}),
        ("blank_policy", {"allowed_usage_policies": (" ",)}),
        ("number_policy", {"allowed_usage_policies": (1,)}),
        ("extra_option", {"extra": True}),
    ]:
        rows.append(await observe(name, plan_for("thuế"), {**options("bm25").model_dump(), **change}, Recorder()))
    normalized = SearchOptions.model_validate(
        {**options("bm25").model_dump(), "as_of_date": "2026-11-10", "allowed_usage_policies": [" A ", "A", "B"]}
    )
    rows.append(await observe("normalized_options", plan_for("thuế"), normalized, Recorder()))
    rows.append(
        await observe(
            "clarification_invalid_options",
            understand("Có được không?"),
            {**options("bm25").model_dump(), "top_k": 0},
            Recorder(),
        )
    )
    graphs = []
    for mode in ("bm25", "dense", "hybrid", "rerank"):
        service, *_ = configured() if mode == "rerank" else hybrid_service()
        graphs.append(await graph_observe("graph_" + mode, "Trích dẫn: thuế", mode, Recorder(service)))
    for name, question, recorder in [
        ("graph_no_match", "Trích dẫn: thuế", Recorder()),
        ("graph_clarification", "Có được không?", Recorder()),
        ("graph_failure", "thuế; hợp đồng; bảo hiểm", Recorder(fail_at=2)),
        ("graph_exception", "thuế; hợp đồng", Recorder(exception_at=2)),
        ("graph_context_mismatch", "Trích dẫn: thuế", Recorder(mismatch=True)),
    ]:
        graphs.append(await graph_observe(name, question, "bm25", recorder))
    signatures = {
        label: str(inspect.signature(obj))
        for label, obj in {
            "search": search,
            "SearchOptions": SearchOptions,
            "QuerySearch.search": QuerySearch.search,
            "QuerySearchNodes.search": QuerySearchNodes.search,
            "JudgeHandoff.from_search": JudgeHandoff.from_search,
            "JudgeHandoff.validate_context": JudgeHandoff.validate_context,
        }.items()
    }
    payload = {
        "label": "OBSERVED",
        "scope": "Offline only, synthetic content and fake backend/model ports",
        "search_case_count": len(rows),
        "graph_case_count": len(graphs),
        "search_traces": rows,
        "graph_traces": graphs,
        "signatures": signatures,
    }
    (OUT / "search-traces.json").write_text(json.dumps(payload, ensure_ascii=True, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "search_cases": len(rows),
                "graph_cases": len(graphs),
                "results": [
                    {
                        "id": row["id"],
                        "calls": len(row["requests_observed"]),
                        "status": row.get("search_state", {}).get("status"),
                        "exception": row.get("exception", {}).get("type"),
                        "handoff": row.get("handoff", {}).get("status"),
                    }
                    for row in rows
                ],
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    with tracing_context(enabled=False):
        asyncio.run(main())
