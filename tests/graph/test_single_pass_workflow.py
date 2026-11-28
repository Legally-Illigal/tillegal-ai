"""Offline single-pass graph routing, provenance and lifecycle tests."""

import asyncio
import json
import threading
from copy import deepcopy
from unittest.mock import AsyncMock

import pytest
from pydantic import ValidationError

from src.applications.tillegal.agents.judge.schemas import error_result
from src.applications.tillegal.graphs.single_pass import SinglePassOutput
from src.framework.runtime.cancellation import ExecutionCancelledError
from src.framework.runtime.execution_context import ExecutionContext
from src.framework.runtime.lifecycle import ExecutionLifecycle, ExecutionStatus
from src.qa_bootstrap import create_single_pass_workflow
from src.query_search_bootstrap import QuerySearch
from tests.graph.test_query_search_workflow import FakeRetrieval
from tests.unit.applications.tillegal.test_judge_native import state
from tests.unit.applications.tillegal.test_query_search import options


class Planner:
    def __init__(self, plan):
        self.plan = plan

    async def understand(self, question):
        result = deepcopy(self.plan)
        assert result["original"] == question
        return result


class Replay:
    def __init__(self, native):
        self.native = native

    async def search(self, request):
        response = next(r for r in self.native["responses"] if r.query == request.query)
        return response.model_copy(deep=True)


class JudgeFixture:
    mode = "mock"
    model = "offline-contract-fixture"

    def __init__(self, status="SUFFICIENT", started=None, release=None):
        self.status, self.started, self.release = status, started, release
        self.calls = 0

    def generate(self, messages):
        self.calls += 1
        if self.started:
            self.started.set()
            assert self.release.wait(3)
        if self.status == "ERROR":
            return json.dumps(error_result("FIXTURE_ERROR"))
        value = json.loads(messages[-1]["content"])
        ids = [e["evidence_id"] for e in value["evidence"]]
        return json.dumps(
            {
                "status": self.status,
                "issue_checks": [
                    {
                        "issue_id": i["issue_id"],
                        "evidence_ids": ids,
                        "coverage": "full" if self.status == "SUFFICIENT" else "partial",
                    }
                    for i in value["query_plan"]["issues"]
                ],
                "missing_items": [] if self.status == "SUFFICIENT" else ["Fixture missing condition"],
                "next_queries": [],
                "usable_evidence_ids": ids,
                "explanation": "Fixture only, not legal evaluation.",
                "error_code": None,
            }
        )


class SummaryFixture:
    mode = "mock"
    model = "offline-contract-fixture"

    def __init__(self, fail=False, started=None, release=None):
        self.fail, self.calls = fail, 0
        self.started, self.release = started, release

    def generate(self, messages):
        self.calls += 1
        if self.started:
            self.started.set()
            assert self.release.wait(3)
        if self.fail:
            return "invalid json"
        value = json.loads(messages[-1]["content"])
        return json.dumps(
            {
                "units": [
                    {
                        "text": "Synthetic fixture statement.",
                        "issue_ids": [value["query_plan"]["issues"][0]["issue_id"]],
                        "evidence_ids": [value["evidence"][0]["evidence_id"]],
                        "statement_type": "source_statement",
                    }
                ],
                "limitations": [],
                "abstain": False,
            }
        )


def setup(native=None, judge=None, summary=None):
    native = state() if native is None else native
    judge = judge or JudgeFixture()
    summary = summary or SummaryFixture()
    pipeline = QuerySearch(Replay(native), options(), Planner(native["plan"]))
    return create_single_pass_workflow(pipeline, judge_provider=judge, summary_provider=summary), judge, summary


QUESTION = (
    "Tôi ký hợp đồng lao động 2 năm, mới làm được 6 tháng nhưng muốn nghỉ việc. "
    "Tôi có phải báo trước không và có phải bồi thường không?"
)


def run(flow, question=QUESTION, request="request-test"):
    return asyncio.run(flow.execute(question, ExecutionContext(run_id="run", request_id=request)))


@pytest.mark.parametrize("status", ["SUFFICIENT", "INSUFFICIENT"])
def test_success_and_limited_draft(status):
    flow, judge, summary = setup(judge=JudgeFixture(status))
    output = run(flow)
    assert output.workflow_status == "COMPLETED"
    assert output.judge_status == status and output.verification_status == "NOT_RUN"
    assert output.summary_output["status"] == "DRAFT_UNVERIFIED" and output.draft_version == 1
    assert judge.calls == summary.calls == 1
    assert output.trace == ["query", "search", "judge", "summary", "finalize"]
    for citation in output.summary_output["citations"]:
        assert citation["evidence_id"] in output.judge_carrier["adapted"]["evidence_map"]
    assert output.judge_carrier["telemetry"]["provider_calls"] == 1
    assert output.summary_telemetry["provider_calls"] == 1
    if status == "INSUFFICIENT":
        assert "JUDGE_INSUFFICIENT" in output.limitations
        assert output.stop_reason == "single_pass_insufficient"


def test_empty_search_abstains_without_model_calls():
    flow, judge, summary = setup(native=state(True))
    output = run(flow)
    assert output.workflow_status == "COMPLETED" and output.judge_status == "INSUFFICIENT"
    assert output.summary_output["status"] == "ABSTAINED_UNVERIFIED"
    assert judge.calls == summary.calls == 0


def test_clarification_and_generated_request_id():
    retrieval = AsyncMock()
    flow = create_single_pass_workflow(
        QuerySearch(retrieval, options()), judge_provider=JudgeFixture(), summary_provider=SummaryFixture()
    )
    output = run(flow, "Có được không?", request=None)
    assert output.workflow_status == "CLARIFICATION_REQUIRED" and output.request_id
    assert output.judge_carrier is None and output.summary_output is None
    retrieval.search.assert_not_called()


@pytest.mark.parametrize("fail_at", [1, 2])
def test_failed_and_partial_search_skip_judge(fail_at):
    native = state()
    judge, summary = JudgeFixture(), SummaryFixture()
    flow = create_single_pass_workflow(
        QuerySearch(FakeRetrieval(fail_at=fail_at), options(), Planner(native["plan"])),
        judge_provider=judge,
        summary_provider=summary,
    )
    output = run(flow)
    assert output.workflow_status == "ERROR" and output.stop_reason == "search_incomplete"
    assert judge.calls == summary.calls == 0 and output.errors


def test_judge_error_skips_summary():
    flow, _, summary = setup(judge=JudgeFixture("ERROR"))
    output = run(flow)
    assert output.judge_status == "ERROR" and output.workflow_status == "ERROR"
    assert output.stop_reason == "judge_error" and summary.calls == 0


def test_summary_error_preserved():
    flow, _, _ = setup(summary=SummaryFixture(fail=True))
    output = run(flow)
    assert output.workflow_status == "ERROR" and output.stop_reason == "summary_error"
    assert output.summary_output["status"] == "ERROR" and output.errors


def test_two_requests_keep_distinct_ids_and_state():
    flow, _, _ = setup()

    async def execute():
        return await asyncio.gather(
            *[flow.execute(QUESTION, ExecutionContext(run_id=f"run-{i}", request_id=f"req-{i}")) for i in range(2)]
        )

    a, b = asyncio.run(execute())
    assert a.workflow_status == b.workflow_status == "COMPLETED"
    assert a.request_id != b.request_id
    assert set(a.judge_carrier["adapted"]["evidence_map"]).isdisjoint(b.judge_carrier["adapted"]["evidence_map"])
    assert a.summary_output["request_id"] == "req-0" and b.summary_output["request_id"] == "req-1"
    a.summary_output["limitations"].append("local change")
    assert "local change" not in b.summary_output["limitations"]


@pytest.mark.parametrize("cancel", [False, True])
@pytest.mark.parametrize("stage", ["judge", "summary"])
def test_timeout_and_cancellation_while_sync_provider_runs(cancel, stage):
    started, release = threading.Event(), threading.Event()
    flow, _, summary = setup(
        judge=JudgeFixture(started=started, release=release) if stage == "judge" else JudgeFixture(),
        summary=SummaryFixture(started=started, release=release) if stage == "summary" else SummaryFixture(),
    )

    async def execute():
        context = ExecutionContext(run_id="slow", request_id="slow")
        lifecycle = ExecutionLifecycle()
        task = asyncio.create_task(
            flow.execute(QUESTION, context, timeout_seconds=2 if cancel else 0.15, lifecycle=lifecycle)
        )
        try:
            for _ in range(100):
                if started.is_set():
                    break
                await asyncio.sleep(0.005)
            assert started.is_set(), "Provider did not start; event loop may be blocked"
            if cancel:
                context.cancellation_token.cancel("test")
            with pytest.raises(ExecutionCancelledError if cancel else TimeoutError):
                await task
            assert not release.is_set()
            assert summary.calls == (0 if stage == "judge" else 1)
            assert lifecycle.snapshot.status == (ExecutionStatus.CANCELLED if cancel else ExecutionStatus.FAILED)
        finally:
            release.set()
            if not task.done():
                task.cancel()
                await asyncio.gather(task, return_exceptions=True)

    asyncio.run(execute())


def test_live_opt_in_and_public_validation():
    native = state()
    pipeline = QuerySearch(Replay(native), options(), Planner(native["plan"]))
    judge = JudgeFixture()
    judge.mode = "live"
    with pytest.raises(ValueError, match="OPT_IN"):
        create_single_pass_workflow(pipeline, judge_provider=judge, summary_provider=SummaryFixture())
    flow = create_single_pass_workflow(
        pipeline, judge_provider=judge, summary_provider=SummaryFixture(), allow_live=True
    )
    output = run(flow).model_dump(mode="json")
    output["verification_status"] = "VERIFIED"
    with pytest.raises(ValidationError):
        SinglePassOutput.model_validate(output)


def test_public_output_rejects_tampered_provenance():
    flow, _, _ = setup()
    output = run(flow).model_dump(mode="json")
    output["judge_carrier"]["adapted"]["evidence_map"].clear()
    with pytest.raises(ValidationError):
        SinglePassOutput.model_validate(output)


def test_invalid_question_returns_error_without_retrieval():
    retrieval = AsyncMock()
    flow = create_single_pass_workflow(
        QuerySearch(retrieval, options()), judge_provider=JudgeFixture(), summary_provider=SummaryFixture()
    )
    output = run(flow, "")
    assert output.workflow_status == "ERROR" and output.stop_reason == "query_error"
    retrieval.search.assert_not_called()


def test_offline_example_uses_production_entrypoint():
    from examples.orchestrator.offline import main

    output = asyncio.run(main())
    assert output.workflow_status == "COMPLETED"
    assert output.verification_status == "NOT_RUN"
    assert output.trace == ["query", "search", "judge", "summary", "finalize"]
