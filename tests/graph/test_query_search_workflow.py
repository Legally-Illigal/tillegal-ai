"""Unit and in-memory graph tests; no database or model inference."""

import asyncio
import json
from copy import deepcopy
from datetime import UTC, datetime
from unittest.mock import AsyncMock, patch

import pytest
from pydantic import ValidationError

from src.applications.tillegal.agents.query.agent import QueryInputError, understand
from src.applications.tillegal.agents.query.semantic import QueryAnalysisError
from src.applications.tillegal.graphs.legal_qa import QuerySearchNodes, QuerySearchWorkflow
from src.applications.tillegal.retrieval.contracts import RetrievalResponse, RetrievalWarning
from src.applications.tillegal.retrieval.errors import RetrievalErrorDetail
from src.applications.tillegal.state.legal_qa_state import JudgeHandoff
from src.core.config import SupabaseSettings
from src.framework.runtime.cancellation import CancellationToken, ExecutionCancelledError
from src.framework.runtime.execution_context import ExecutionContext, current_execution_context
from src.framework.runtime.lifecycle import ExecutionLifecycle, ExecutionStatus
from src.query_search_bootstrap import QuerySearch, create_query_search
from tests.unit.applications.tillegal.retrieval.test_hybrid_service import hybrid_service
from tests.unit.applications.tillegal.retrieval.test_reranking import configured
from tests.unit.applications.tillegal.test_gemini_query import FAKE_KEY, TARGET, reply
from tests.unit.applications.tillegal.test_query_search_multimode import options
from tests.unit.applications.tillegal.test_query_search_semantic import QUESTION, analysis


class FakeRetrieval:
    def __init__(self, *, fail_at=None):
        self.requests = []
        self.responses = []
        self.fail_at = fail_at

    async def search(self, request):
        self.requests.append(request)
        await asyncio.sleep(0)
        failed = len(self.requests) == self.fail_at
        response = RetrievalResponse(
            **request.model_dump(),
            request_id="00000000-0000-0000-0000-000000000001",
            query_used=request.query.strip(),
            selected_index_name="fixture",
            index=None,
            status="FAILED" if failed else "NO_MATCH",
            retrieved_at=datetime(2026, 11, 21, tzinfo=UTC),
            warnings=(RetrievalWarning(code="FIXTURE_WARNING", message="Fixture only"),),
            error=RetrievalErrorDetail(
                category="DATABASE_FAILURE", code="FIXTURE_READ_FAILED", stage="search", message="Fixture failure"
            )
            if failed
            else None,
        )
        self.responses.append(response)
        return response


def context(run="run-1", request="request-1", token=None):
    return ExecutionContext(run_id=run, request_id=request, **({"cancellation_token": token} if token else {}))


def workflow(service=None, mode="bm25"):
    return QuerySearchWorkflow(QuerySearch(service or FakeRetrieval(), options(mode)))


def test_unit_query_node_and_routes():
    service = FakeRetrieval()
    nodes = QuerySearchNodes(QuerySearch(service, options("bm25")))
    for question, route, status in [
        ("Trích dẫn: thuế", "search", "QUERY_COMPLETED"),
        ("Có được không?", "end", "CLARIFICATION_REQUIRED"),
    ]:
        state = nodes.query({"question": question})
        assert state["plan"] == understand(question)
        assert state["status"] == status and nodes.route_query(state) == route
        assert state["options"] is nodes.pipeline.options
        assert state["search_result"] is state["handoff"] is None
    assert service.requests == []


def test_unit_search_node_keeps_native_result_and_ids():
    service = FakeRetrieval()
    nodes = QuerySearchNodes(QuerySearch(service, options("bm25")))
    initial = {"question": "Trích dẫn: thuế", "run_id": "run", "request_id": "request"}
    state = {**initial, **nodes.query(initial)}
    before = deepcopy(state)
    update = asyncio.run(nodes.search(state))
    handoff = update["handoff"]
    assert state == before and update["status"] == "NO_MATCH"
    assert handoff.responses[0] is service.responses[0]
    assert handoff.run_id == "run" and handoff.request_id == "request"
    assert handoff.warnings == service.responses[0].warnings and handoff.errors == ()


@pytest.mark.parametrize("question", ["Có được không?", "31/02/2024"])
def test_graph_clarification_skips_search_node(question):
    service = FakeRetrieval()
    flow = workflow(service)

    async def run():
        updates = [
            item
            async for item in flow.graph.astream(
                {"question": question, "run_id": "run", "request_id": "r"}, stream_mode="updates"
            )
        ]
        assert [next(iter(update)) for update in updates] == ["query"]
        result = await flow.execute(question, context(), timeout_seconds=1)
        assert result["status"] == "CLARIFICATION_REQUIRED"
        assert result["handoff"] is result["search_result"] is None
        assert result["clarification"] == understand(question)["clarification"]

    asyncio.run(run())
    assert service.requests == []


def test_graph_exact_order_and_no_match_handoff():
    service = FakeRetrieval()
    flow = workflow(service)

    async def run():
        initial = {"question": "Trích dẫn: thuế", "run_id": "run", "request_id": "r"}
        updates = [item async for item in flow.graph.astream(initial, stream_mode="updates")]
        assert [next(iter(update)) for update in updates] == ["query", "search"]
        assert updates[0]["query"]["status"] == "QUERY_COMPLETED"
        assert updates[1]["search"]["status"] == "NO_MATCH"

    asyncio.run(run())
    assert len(service.requests) == 1
    assert set(flow.graph.nodes) == {"__start__", "query", "search"}


@pytest.mark.parametrize("mode", ["bm25", "dense", "hybrid", "rerank"])
def test_real_service_fake_ports_preserve_subtypes_and_json(mode):
    service, *_ = configured() if mode == "rerank" else hybrid_service()
    flow = workflow(service, mode)
    lifecycle = ExecutionLifecycle()
    state = asyncio.run(flow.execute("Trích dẫn: thuế", context(), timeout_seconds=2, lifecycle=lifecycle))
    assert lifecycle.snapshot.status is ExecutionStatus.SUCCEEDED
    assert state["status"] == "SEARCH_COMPLETED" and state["clarification"] is None
    packet = state["handoff"]
    assert packet.status == "READY" and packet.search_status == "COMPLETED"
    assert packet.responses[0] is state["search_result"]["responses"][0]
    restored = JudgeHandoff.model_validate_json(packet.model_dump_json())
    assert restored == packet and type(restored.responses[0]) is type(packet.responses[0])
    assert restored.responses[0].evidence == packet.responses[0].evidence
    assert restored.options == options(mode)
    assert restored.warnings == packet.warnings and restored.errors == ()
    if mode == "hybrid":
        assert restored.responses[0].fusion == packet.responses[0].fusion
    if mode == "rerank":
        assert restored.responses[0].reranking == packet.responses[0].reranking
    direct = asyncio.run(QuerySearch(service, options(mode)).search("Trích dẫn: thuế"))
    assert packet.responses[0].model_dump(exclude={"request_id", "retrieved_at"}) == direct["responses"][0].model_dump(
        exclude={"request_id", "retrieved_at"}
    )


def test_multiple_queries_failure_keeps_prior_response_and_error():
    service = FakeRetrieval(fail_at=2)
    state = asyncio.run(workflow(service).execute("thuế; nghỉ phép", context(), timeout_seconds=1))
    packet = state["handoff"]
    assert state["status"] == packet.status == "RETRIEVAL_FAILED"
    assert state["search_result"]["status"] == "FAILED"
    assert len(service.requests) == len(packet.responses) == 2
    assert packet.responses[0].status == "NO_MATCH" and packet.responses[1].status == "FAILED"
    assert packet.errors[0] is packet.responses[1].error
    assert state["errors"] == ["FIXTURE_READ_FAILED"]
    assert JudgeHandoff.model_validate_json(packet.model_dump_json()) == packet


@pytest.mark.parametrize("question", [None, "", "abc\0def"])
def test_invalid_input_preserves_query_error(question):
    service = FakeRetrieval()
    lifecycle = ExecutionLifecycle()
    with pytest.raises(QueryInputError):
        asyncio.run(workflow(service).execute(question, context(), timeout_seconds=1, lifecycle=lifecycle))
    assert lifecycle.snapshot.status is ExecutionStatus.FAILED
    assert service.requests == []


def test_query_execution_failure_propagates_without_handoff():
    service = FakeRetrieval()
    lifecycle = ExecutionLifecycle()
    with patch("src.applications.tillegal.graphs.legal_qa.understand", side_effect=RuntimeError("fixture error")):
        with pytest.raises(RuntimeError, match="fixture error"):
            asyncio.run(workflow(service).execute("Trích dẫn: thuế", context(), timeout_seconds=1, lifecycle=lifecycle))
    assert lifecycle.snapshot.status is ExecutionStatus.FAILED and service.requests == []


def test_unexpected_search_exception_is_execution_failure():
    class Broken(FakeRetrieval):
        async def search(self, request):
            raise RuntimeError("fixture execution error")

    lifecycle = ExecutionLifecycle()
    with pytest.raises(RuntimeError, match="fixture execution error"):
        asyncio.run(workflow(Broken()).execute("Trích dẫn: thuế", context(), timeout_seconds=1, lifecycle=lifecycle))
    assert lifecycle.snapshot.status is ExecutionStatus.FAILED


def test_typed_retrieval_timeout_becomes_failed_handoff():
    class Deadline(FakeRetrieval):
        async def search(self, request):
            response = await super().search(request)
            return response.model_copy(
                update={
                    "status": "FAILED",
                    "error": RetrievalErrorDetail(
                        category="TIMEOUT", code="RETRIEVAL_TIMEOUT", stage="search", message="Fixture deadline"
                    ),
                }
            )

    state = asyncio.run(workflow(Deadline()).execute("Trích dẫn: thuế", context(), timeout_seconds=1))
    assert state["status"] == "RETRIEVAL_FAILED"
    assert state["handoff"].errors[0].category == "TIMEOUT"


def test_outer_timeout_and_cancellation_propagate():
    class Waiting(FakeRetrieval):
        def __init__(self):
            super().__init__()
            self.started = asyncio.Event()
            self.cancelled = False

        async def search(self, request):
            self.started.set()
            try:
                await asyncio.Event().wait()
            finally:
                self.cancelled = True

    async def run():
        service = Waiting()
        lifecycle = ExecutionLifecycle()
        with pytest.raises(TimeoutError):
            await workflow(service).execute("Trích dẫn: thuế", context(), timeout_seconds=0.05, lifecycle=lifecycle)
        assert lifecycle.snapshot.status is ExecutionStatus.FAILED and service.cancelled
        service = Waiting()
        lifecycle = ExecutionLifecycle()
        token = CancellationToken()
        task = asyncio.create_task(
            workflow(service).execute("Trích dẫn: thuế", context(token=token), timeout_seconds=2, lifecycle=lifecycle)
        )
        await asyncio.wait_for(service.started.wait(), timeout=1)
        token.cancel("fixture cancellation")
        with pytest.raises(ExecutionCancelledError):
            await task
        assert lifecycle.snapshot.status is ExecutionStatus.CANCELLED and service.cancelled
        assert current_execution_context() is None

    asyncio.run(run())


def test_caller_task_cancellation_propagates():
    async def run():
        started = asyncio.Event()

        class Waiting(FakeRetrieval):
            async def search(self, request):
                started.set()
                await asyncio.Event().wait()

        lifecycle = ExecutionLifecycle()
        task = asyncio.create_task(
            workflow(Waiting()).execute("Trích dẫn: thuế", context(), timeout_seconds=2, lifecycle=lifecycle)
        )
        await asyncio.wait_for(started.wait(), timeout=1)
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task
        assert lifecycle.snapshot.status is ExecutionStatus.CANCELLED

    asyncio.run(run())


def test_repeated_and_concurrent_requests_are_isolated():
    service = FakeRetrieval(fail_at=1)
    flow = workflow(service)

    async def run():
        failed = await flow.execute("Trích dẫn: thuế", context("failed", "f"), timeout_seconds=1)
        first, second = await asyncio.gather(
            flow.execute("Trích dẫn: hợp đồng", context("one", "r1"), timeout_seconds=1),
            flow.execute("Trích dẫn: nghỉ phép", context("two", "r2"), timeout_seconds=1),
        )
        assert failed["status"] == "RETRIEVAL_FAILED"
        assert first["errors"] == second["errors"] == []
        assert first["run_id"] == first["handoff"].run_id == "one"
        assert second["request_id"] == second["handoff"].request_id == "r2"
        assert first["handoff"].responses[0].query == "hợp đồng"
        assert second["handoff"].responses[0].query == "nghỉ phép"
        first["plan"]["original"] = "caller mutation"
        assert second["plan"]["original"] == "Trích dẫn: nghỉ phép"
        clarified = await flow.execute("Có được không?", context("three", "r3"), timeout_seconds=1)
        assert clarified["handoff"] is clarified["search_result"] is None
        assert clarified["errors"] == []

    asyncio.run(run())


def test_untrusted_state_options_do_not_override_injection():
    service = FakeRetrieval()
    nodes = QuerySearchNodes(QuerySearch(service, options("bm25")))
    initial = {"question": "Trích dẫn: thuế", "run_id": "run", "options": options("dense")}
    state = {**initial, **nodes.query(initial)}
    state["options"] = options("hybrid")
    update = asyncio.run(nodes.search(state))
    assert service.requests[0].mode == "bm25"
    assert update["handoff"].options == options("bm25")


@pytest.mark.parametrize(
    "change",
    [{"status": "READY"}, {"question": "different"}, {"responses": ()}, {"requests": ()}, {"extra": "invalid"}],
)
def test_handoff_rejects_inconsistent_or_extra_fields(change):
    state = asyncio.run(workflow().execute("Trích dẫn: thuế", context(), timeout_seconds=1))
    data = state["handoff"].model_dump()
    with pytest.raises(ValidationError):
        JudgeHandoff.model_validate({**data, **change})


def test_graph_context_and_no_judge_dependency():
    import inspect

    import src.applications.tillegal.graphs.legal_qa as module

    class Bound(FakeRetrieval):
        async def search(self, request):
            assert current_execution_context().run_id == "run-1"
            return await super().search(request)

    asyncio.run(workflow(Bound()).execute("Trích dẫn: thuế", context(), timeout_seconds=1))
    source = inspect.getsource(module)
    assert "ai_core" not in source
    assert "agents.judge" not in source
    assert 'add_node("judge"' not in source


@pytest.mark.parametrize("boundary", ["request", "options", "response"])
def test_handoff_context_mismatch_is_rejected(boundary):
    state = asyncio.run(workflow().execute("Trích dẫn: thuế", context(), timeout_seconds=1))
    data = state["handoff"].model_dump()
    if boundary == "request":
        data["requests"][0]["query"] = "different query"
    elif boundary == "options":
        data["options"]["allowed_usage_policies"] = ("OTHER_POLICY",)
    else:
        data["responses"][0]["query"] = "different query"
    with pytest.raises(ValidationError):
        JudgeHandoff.model_validate(data)


def test_unicode_original_survives_graph_and_handoff():
    import unicodedata

    question = unicodedata.normalize("NFD", "  Trích dẫn: nghỉ phép  ")
    service = FakeRetrieval()
    state = asyncio.run(workflow(service).execute(question, context(), timeout_seconds=1))
    assert state["question"] == state["plan"]["original"] == state["handoff"].question == question
    assert service.requests[0].query == "nghỉ phép"
    assert JudgeHandoff.model_validate_json(state["handoff"].model_dump_json()).plan.original == question


# Phase A: exercise the actual compiled graph with the existing Gemini factory/adapter.
def semantic_runner(monkeypatch, service=None, mode="bm25"):
    monkeypatch.setenv("GOOGLE_API_KEY", FAKE_KEY)
    with patch("src.query_search_bootstrap.create_retrieval_service", return_value=service or FakeRetrieval()):
        return create_query_search(SupabaseSettings(), options(mode), semantic_mode="gemini")


def test_phase_a_default_compiled_graph_does_not_call_gemini():
    service = FakeRetrieval()
    with patch(TARGET, AsyncMock(side_effect=AssertionError("unexpected provider"))) as provider:
        state = asyncio.run(workflow(service).execute(QUESTION, context(), timeout_seconds=2))
    provider.assert_not_called()
    assert state["plan"] == understand(QUESTION)
    assert state["plan"]["analysis_method"] == "deterministic"
    assert [request.query for request in service.requests] == [s["text"] for s in state["plan"]["subqueries"]]


@pytest.mark.parametrize("fail_at", [None, 2])
def test_phase_a_compiled_gemini_matches_facade_payload_and_entire_search_state(monkeypatch, fail_at):
    service = FakeRetrieval(fail_at=fail_at)
    data = analysis()
    data["issues"].append({"issue": "Điều kiện nghỉ việc", "search_query": "người lao động điều kiện nghỉ việc"})
    with patch(TARGET, AsyncMock(return_value=reply(json.dumps(data)))) as provider:
        runner = semantic_runner(monkeypatch, service)
        direct = asyncio.run(runner.search(QUESTION))
        arguments = provider.call_args
        assert provider.await_count == 1
        service.requests.clear()
        service.responses.clear()
        provider.reset_mock()
        with patch.object(QuerySearch, "search", side_effect=AssertionError("graph must not call facade.search")):
            state = asyncio.run(QuerySearchWorkflow(runner).execute(QUESTION, context(), timeout_seconds=2))
        assert provider.await_count == 1 and provider.call_args == arguments
    assert state["plan"] == direct["plan"]
    assert state["plan"]["analysis_method"] == "llm"
    assert state["search_result"] == direct  # Includes all warnings/errors/occurrences/options/scores.
    assert service.requests == list(direct["requests"])
    assert len(service.requests) == (2 if fail_at else 3)
    assert state["handoff"].responses == direct["responses"]
    if fail_at:
        assert state["search_result"]["completeness"] == "PARTIAL"
        assert state["search_result"]["skipped_subqueries"] == (2,)
        assert state["errors"] == ["FIXTURE_READ_FAILED"]
    else:
        assert state["errors"] == []


def test_phase_a_compiled_stream_orders_semantic_query_before_search(monkeypatch):
    with patch(TARGET, AsyncMock(return_value=reply())) as provider:
        runner = semantic_runner(monkeypatch)

        async def run():
            return [
                item
                async for item in QuerySearchWorkflow(runner).graph.astream(
                    {"question": QUESTION, "run_id": "stream", "request_id": "stream-request"}, stream_mode="updates"
                )
            ]

        updates = asyncio.run(run())
    assert [next(iter(update)) for update in updates] == ["query", "search"]
    assert updates[0]["query"]["plan"]["analysis_method"] == "llm"
    assert updates[0]["query"]["search_result"] is None
    assert updates[1]["search"]["search_result"]["plan"] == updates[0]["query"]["plan"]
    assert provider.await_count == 1


@pytest.mark.parametrize("question", ["Trích dẫn: thuế", "Có được không?", "31/02/2024"])
def test_phase_a_existing_deterministic_guards_make_zero_model_calls(monkeypatch, question):
    service = FakeRetrieval()
    with patch(TARGET, AsyncMock(side_effect=AssertionError("guard must bypass model"))) as provider:
        state = asyncio.run(
            QuerySearchWorkflow(semantic_runner(monkeypatch, service)).execute(question, context(), timeout_seconds=2)
        )
    provider.assert_not_called()
    assert state["plan"] == understand(question)
    if state["clarification"]:
        assert state["status"] == "CLARIFICATION_REQUIRED"
        assert state["handoff"] is state["search_result"] is None and service.requests == []
    else:
        assert len(service.requests) == 1 and state["handoff"].plan.intent == "quote_lookup"


@pytest.mark.parametrize("failure", ["timeout", "provider", "invalid_json", "invalid_schema", "grounding"])
def test_phase_a_query_errors_never_fallback_or_execute_search(monkeypatch, failure):
    data = analysis(facts=[{"text": "hợp đồng lao động 3 năm", "source_quote": "hợp đồng lao động 3 năm"}])
    provider = AsyncMock(return_value=reply(json.dumps(data)))
    code = "QUERY_ANALYSIS_INVALID_RESPONSE"
    if failure in {"timeout", "provider"}:
        provider.side_effect = TimeoutError() if failure == "timeout" else RuntimeError(FAKE_KEY)
        code = "QUERY_ANALYSIS_TIMEOUT" if failure == "timeout" else "QUERY_ANALYSIS_PROVIDER_ERROR"
    elif failure == "invalid_json":
        provider.return_value = reply("not JSON")
        code = "QUERY_ANALYSIS_PROVIDER_ERROR"  # Existing adapter rejects non-JSON before semantic validation.
    elif failure == "invalid_schema":
        provider.return_value = reply("{}")
    service = FakeRetrieval()
    lifecycle = ExecutionLifecycle()
    with (
        patch(TARGET, provider),
        patch("src.applications.tillegal.graphs.legal_qa.understand", side_effect=AssertionError("no fallback")),
        patch("src.applications.tillegal.graphs.legal_qa.search", new_callable=AsyncMock) as search_node,
    ):
        with pytest.raises(QueryAnalysisError) as error:
            asyncio.run(
                QuerySearchWorkflow(semantic_runner(monkeypatch, service)).execute(
                    QUESTION, context(), timeout_seconds=2, lifecycle=lifecycle
                )
            )
        search_node.assert_not_called()
    assert provider.await_count == 1 and service.requests == []
    assert error.value.args == (code,) and str(error.value) == code
    assert FAKE_KEY not in str(error.value) and QUESTION not in str(error.value)
    assert lifecycle.snapshot.status is ExecutionStatus.FAILED


def test_phase_a_semantic_clarification_skips_search(monkeypatch):
    service = FakeRetrieval()
    clarification = "Bạn dự định nghỉ việc vào thời điểm nào?"
    with patch(TARGET, AsyncMock(return_value=reply(json.dumps(analysis(clarification=clarification))))) as provider:
        state = asyncio.run(
            QuerySearchWorkflow(semantic_runner(monkeypatch, service)).execute(QUESTION, context(), timeout_seconds=2)
        )
    assert provider.await_count == 1
    assert state["plan"]["analysis_method"] == "llm"
    assert state["clarification"] == clarification and state["status"] == "CLARIFICATION_REQUIRED"
    assert state["handoff"] is state["search_result"] is None and service.requests == []


@pytest.mark.parametrize("kind", ["caller", "token", "deadline"])
def test_phase_a_semantic_cancellation_and_deadline_propagate(monkeypatch, kind):
    async def run():
        started, finished = asyncio.Event(), asyncio.Event()

        async def wait(**kwargs):
            started.set()
            try:
                await asyncio.Event().wait()
            finally:
                finished.set()

        service = FakeRetrieval()
        lifecycle = ExecutionLifecycle()
        token = CancellationToken()
        with patch(TARGET, AsyncMock(side_effect=wait)) as provider:
            flow = QuerySearchWorkflow(semantic_runner(monkeypatch, service))
            task = asyncio.create_task(
                flow.execute(
                    QUESTION,
                    context(token=token),
                    timeout_seconds=0.1 if kind == "deadline" else 2,
                    lifecycle=lifecycle,
                )
            )
            await asyncio.wait_for(started.wait(), timeout=1)
            if kind == "caller":
                task.cancel()
                expected = asyncio.CancelledError
            elif kind == "token":
                token.cancel("fixture cancellation")
                expected = ExecutionCancelledError
            else:
                expected = TimeoutError
            with pytest.raises(expected):
                await task
            assert provider.await_count == 1 and finished.is_set()
        assert service.requests == [] and current_execution_context() is None
        assert lifecycle.snapshot.status is (
            ExecutionStatus.FAILED if kind == "deadline" else ExecutionStatus.CANCELLED
        )

    asyncio.run(run())


def test_phase_a_concurrent_semantic_graph_requests_are_isolated(monkeypatch):
    async def run():
        entered, both = [], asyncio.Event()

        async def respond(**kwargs):
            question = json.loads(kwargs["messages"][1]["content"])["question"]
            entered.append((question, current_execution_context().run_id))
            if len(entered) == 2:
                both.set()
            await asyncio.wait_for(both.wait(), timeout=1)
            data = analysis()
            if "3 năm" in question:
                data = json.loads(json.dumps(data, ensure_ascii=False).replace("2 năm", "3 năm"))
            return reply(json.dumps(data))

        service = FakeRetrieval()
        with patch(TARGET, AsyncMock(side_effect=respond)) as provider:
            flow = QuerySearchWorkflow(semantic_runner(monkeypatch, service))
            one, two = await asyncio.gather(
                flow.execute(QUESTION, context("one", "r1"), timeout_seconds=2),
                flow.execute(QUESTION.replace("2 năm", "3 năm"), context("two", "r2"), timeout_seconds=2),
            )
            assert provider.await_count == 2
        assert set(entered) == {(QUESTION, "one"), (QUESTION.replace("2 năm", "3 năm"), "two")}
        assert one["handoff"].request_id == "r1" and two["handoff"].request_id == "r2"
        assert one["plan"]["original"] == QUESTION and two["plan"]["original"] != QUESTION
        assert "2 năm" in one["plan"]["facts"][0]["text"] and "3 năm" in two["plan"]["facts"][0]["text"]
        assert len(service.requests) == 4
        one["plan"]["issues"].append("caller mutation")
        assert "caller mutation" not in two["plan"]["issues"]
        assert one["errors"] == two["errors"] == [] and current_execution_context() is None

    asyncio.run(run())


@pytest.mark.parametrize("mode", ["bm25", "dense", "hybrid", "rerank"])
def test_phase_a_semantic_native_subtypes_scores_and_dedup_stay_intact(monkeypatch, mode):
    service, *_ = configured() if mode == "rerank" else hybrid_service()
    data = analysis(
        domain="unknown",
        facts=[],
        missing_information=[],
        issues=[
            {"issue": "Nội dung về thuế", "search_query": "thuế"},
            {"issue": "Căn cứ liên quan thuế", "search_query": "thuế"},
        ],
    )
    question = "Quy định về thuế là gì?"
    with (
        patch(TARGET, AsyncMock(return_value=reply(json.dumps(data)))) as provider,
        patch.object(service, "search", wraps=service.search) as retrieval,
    ):
        runner = semantic_runner(monkeypatch, service, mode)
        state = asyncio.run(QuerySearchWorkflow(runner).execute(question, context(), timeout_seconds=2))
        # Hybrid recursively dispatches its two native branches through the same service.
        native_calls = 3 if mode in {"hybrid", "rerank"} else 1
        assert provider.await_count == 1 and retrieval.await_count == native_calls
        assert sum(call.args[0].mode == options(mode).mode for call in retrieval.await_args_list) == 1
        assert len(state["plan"]["issues"]) == 2 and len(state["plan"]["subqueries"]) == 1
        assert state["plan"]["search_objectives"][0]["issue_indices"] == [0, 1]
        assert state["search_result"]["executed_searches"] == 1
        assert all(o.issue_indices == (0, 1) for g in state["search_result"]["evidence"] for o in g.occurrences)
        response = state["search_result"]["responses"][0]
        assert state["handoff"].responses[0] is response and response.evidence
        restored = JudgeHandoff.model_validate_json(state["handoff"].model_dump_json())
        assert type(restored.responses[0]) is type(response)
        assert restored == state["handoff"]
        arguments = provider.call_args
        direct = asyncio.run(runner.search(question))
        assert provider.await_count == 2 and provider.call_args == arguments
        assert retrieval.await_count == 2 * native_calls
    assert response.model_dump(exclude={"request_id", "retrieved_at"}) == direct["responses"][0].model_dump(
        exclude={"request_id", "retrieved_at"}
    )
    assert state["search_result"]["warnings"] == direct["warnings"]
    assert state["search_result"]["errors"] == direct["errors"]


def test_phase_a_semantic_sync_invoke_is_explicitly_unsupported(monkeypatch):
    service = FakeRetrieval()
    with patch(TARGET, AsyncMock(return_value=reply())) as provider:
        flow = QuerySearchWorkflow(semantic_runner(monkeypatch, service))
        with pytest.raises(TypeError, match="No synchronous function provided"):
            flow.graph.invoke({"question": QUESTION, "run_id": "sync", "request_id": "sync-r"})
    provider.assert_not_called()
    assert service.requests == []
