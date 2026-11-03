"""Tests for reusable resilience, runtime, state, and tool framework components."""

import asyncio

import pytest
from pydantic import BaseModel, ConfigDict

from src.framework.resilience import (
    AsyncConcurrencyLimiter,
    CircuitBreaker,
    CircuitBreakerPolicy,
    CircuitOpenError,
    CircuitState,
    ConcurrencyLimitError,
    RetryPolicy,
    retry_async,
    retry_sync,
)
from src.framework.runtime import (
    CancellationToken,
    ExecutionCancelledError,
    ExecutionContext,
    ExecutionLifecycle,
    ExecutionStatus,
    GraphExecutor,
    InvalidLifecycleTransitionError,
    bind_execution_context,
    current_execution_context,
)
from src.framework.state import (
    Artifact,
    WorkflowMessage,
    append_unique,
    merge_artifacts,
    merge_messages,
    merge_metadata,
)
from src.framework.tools import (
    ToolExecutionError,
    ToolExecutor,
    ToolInputValidationError,
    ToolPermissionDeniedError,
    ToolPrincipal,
    ToolRegistry,
    ToolRegistryError,
    ToolSpec,
    ToolTimeoutError,
)


@pytest.mark.anyio
async def test_retry_async_and_sync_only_retry_selected_errors() -> None:
    attempts = 0
    delays: list[float] = []

    async def flaky() -> str:
        nonlocal attempts
        attempts += 1
        if attempts < 3:
            raise OSError("transient")
        return "ok"

    async def no_wait(delay: float) -> None:
        delays.append(delay)

    assert (
        await retry_async(
            flaky,
            RetryPolicy(max_attempts=3, initial_delay_seconds=0.25, retry_exceptions=(OSError,)),
            sleep=no_wait,
        )
        == "ok"
    )
    assert attempts == 3
    assert delays == [0.25, 0.5]

    sync_attempts = 0

    def sync_flaky() -> str:
        nonlocal sync_attempts
        sync_attempts += 1
        if sync_attempts == 1:
            raise OSError("temporary")
        return "done"

    assert (
        retry_sync(sync_flaky, RetryPolicy(max_attempts=2, retry_exceptions=(OSError,)), sleep=lambda _: None) == "done"
    )
    with pytest.raises(ValueError):
        retry_sync(lambda: (_ for _ in ()).throw(ValueError("permanent")), RetryPolicy(max_attempts=3))


def test_circuit_breaker_opens_and_recovers() -> None:
    now = 0.0
    breaker = CircuitBreaker(
        CircuitBreakerPolicy(failure_threshold=2, recovery_timeout_seconds=5),
        clock=lambda: now,
    )
    for _ in range(2):
        with pytest.raises(OSError):
            breaker.call(lambda: (_ for _ in ()).throw(OSError("down")))
    assert breaker.state is CircuitState.OPEN
    with pytest.raises(CircuitOpenError):
        breaker.call(lambda: "must not run")

    now = 5.0
    assert breaker.state is CircuitState.HALF_OPEN
    assert breaker.call(lambda: "recovered") == "recovered"
    assert breaker.state is CircuitState.CLOSED


@pytest.mark.anyio
async def test_circuit_breaker_async_failure_and_half_open_probe() -> None:
    now = 0.0
    breaker = CircuitBreaker(
        CircuitBreakerPolicy(failure_threshold=1, recovery_timeout_seconds=1),
        clock=lambda: now,
    )
    with pytest.raises(OSError):
        await breaker.call_async(_raise_async)
    assert breaker.state is CircuitState.OPEN
    now = 1.0
    assert breaker.state is CircuitState.HALF_OPEN
    assert await breaker.call_async(_return_async) == "ok"
    assert breaker.state is CircuitState.CLOSED


async def _raise_async() -> str:
    raise OSError("down")


async def _return_async() -> str:
    return "ok"


@pytest.mark.anyio
async def test_concurrency_limiter_bounds_calls_and_reports_wait_timeout() -> None:
    limiter = AsyncConcurrencyLimiter(1, acquire_timeout_seconds=0.01)
    entered = asyncio.Event()
    release = asyncio.Event()

    async def hold_slot() -> None:
        async with limiter.slot():
            entered.set()
            await release.wait()

    task = asyncio.create_task(hold_slot())
    await entered.wait()
    with pytest.raises(ConcurrencyLimitError):
        async with limiter.slot():
            pytest.fail("the second caller must not acquire the slot")
    release.set()
    await task


def test_execution_context_binds_and_restores_context() -> None:
    context = ExecutionContext(run_id="run-1", metadata={"tenant": "demo"})
    assert current_execution_context() is None
    with bind_execution_context(context):
        assert current_execution_context() is context
        with pytest.raises(TypeError):
            context.metadata["tenant"] = "changed"
    assert current_execution_context() is None


class _FakeGraph:
    def __init__(self, *, delay: float = 0, failure: Exception | None = None) -> None:
        self.delay = delay
        self.failure = failure
        self.context_seen: ExecutionContext | None = None

    async def ainvoke(self, input: str, config: object = None) -> str:
        self.context_seen = current_execution_context()
        await asyncio.sleep(self.delay)
        if self.failure:
            raise self.failure
        return input.upper()


@pytest.mark.anyio
async def test_graph_executor_updates_lifecycle_and_propagates_context() -> None:
    executor = GraphExecutor()
    graph = _FakeGraph()
    context = ExecutionContext(run_id="run-2")
    lifecycle = ExecutionLifecycle()

    assert await executor.execute(graph, "hello", context, lifecycle=lifecycle) == "HELLO"
    assert graph.context_seen is context
    assert lifecycle.snapshot.status is ExecutionStatus.SUCCEEDED

    failed_lifecycle = ExecutionLifecycle()
    with pytest.raises(RuntimeError, match="graph error"):
        await executor.execute(
            _FakeGraph(failure=RuntimeError("graph error")),
            "hello",
            context,
            lifecycle=failed_lifecycle,
        )
    assert failed_lifecycle.snapshot.status is ExecutionStatus.FAILED


@pytest.mark.anyio
async def test_graph_executor_enforces_timeout_and_cooperative_cancellation() -> None:
    context = ExecutionContext(run_id="slow")
    lifecycle = ExecutionLifecycle()
    with pytest.raises(TimeoutError, match="exceeded"):
        await GraphExecutor().execute(
            _FakeGraph(delay=1),
            "hello",
            context,
            timeout_seconds=0.001,
            lifecycle=lifecycle,
        )
    assert lifecycle.snapshot.status is ExecutionStatus.FAILED

    token = CancellationToken()
    context = ExecutionContext(run_id="cancelled", cancellation_token=token)
    lifecycle = ExecutionLifecycle()
    task = asyncio.create_task(
        GraphExecutor().execute(
            _FakeGraph(delay=1),
            "hello",
            context,
            lifecycle=lifecycle,
        )
    )
    await asyncio.sleep(0)
    token.cancel("user request")
    with pytest.raises(ExecutionCancelledError, match="user request"):
        await task
    assert lifecycle.snapshot.status is ExecutionStatus.CANCELLED


def test_lifecycle_rejects_invalid_and_terminal_transitions() -> None:
    lifecycle = ExecutionLifecycle()
    with pytest.raises(InvalidLifecycleTransitionError):
        lifecycle.succeed()
    lifecycle.start()
    lifecycle.succeed()
    with pytest.raises(InvalidLifecycleTransitionError, match="terminal"):
        lifecycle.fail("too late")


def test_state_reducers_merge_by_identity_and_metadata() -> None:
    original = WorkflowMessage(role="assistant", content="draft", message_id="msg-1")
    revised = WorkflowMessage(role="assistant", content="final", message_id="msg-1")
    other = WorkflowMessage(role="user", content="question", message_id="msg-2")
    assert merge_messages([original], [revised, other]) == [revised, other]
    assert append_unique([1, 2], [2, 3]) == [1, 2, 3]
    first_artifact = Artifact(name="answer", content="draft", artifact_id="art-1")
    revised_artifact = Artifact(name="answer", content="final", artifact_id="art-1")
    assert merge_artifacts([first_artifact], [revised_artifact]) == [revised_artifact]
    assert merge_metadata({"a": 1}, {"a": 2, "b": 3}) == {"a": 2, "b": 3}


class _LookupArguments(BaseModel):
    model_config = ConfigDict(extra="forbid")

    query: str


class _RecordingIdempotencyStore:
    def __init__(self) -> None:
        self.calls: list[tuple[str, str]] = []

    async def execute(self, key: str, request_fingerprint: str, operation):
        self.calls.append((key, request_fingerprint))
        return await operation()


@pytest.mark.anyio
async def test_tool_executor_validates_authorizes_and_delegates_idempotency() -> None:
    calls = 0

    async def lookup(arguments: _LookupArguments) -> dict[str, str]:
        nonlocal calls
        calls += 1
        return {"query": arguments.query}

    registry = ToolRegistry()
    tool = ToolSpec(
        name="legal_lookup",
        description="Find legal documents",
        args_schema=_LookupArguments,
        handler=lookup,
        required_permissions=frozenset({"legal:read"}),
    )
    registry.register(tool)
    with pytest.raises(ToolRegistryError, match="already registered"):
        registry.register(tool)

    idempotency_store = _RecordingIdempotencyStore()
    executor = ToolExecutor(registry, idempotency_store=idempotency_store)
    with pytest.raises(ToolPermissionDeniedError, match="legal:read"):
        await executor.execute(
            "legal_lookup",
            {"query": "labor"},
            principal=ToolPrincipal("user-1"),
        )
    with pytest.raises(ToolInputValidationError, match="arguments are invalid"):
        await executor.execute(
            "legal_lookup",
            {"query": "labor", "unexpected": True},
            principal=ToolPrincipal("user-1", frozenset({"legal:read"})),
        )

    principal = ToolPrincipal("user-1", frozenset({"legal:read"}))
    assert await executor.execute(
        "legal_lookup",
        {"query": "labor"},
        principal=principal,
        idempotency_key="request-1",
    ) == {"query": "labor"}
    assert calls == 1
    assert idempotency_store.calls[0][0] == '["legal_lookup","user-1","request-1"]'
    assert len(idempotency_store.calls[0][1]) == 64


@pytest.mark.anyio
async def test_tool_executor_surfaces_handler_errors_and_timeouts() -> None:
    registry = ToolRegistry()

    async def failure(_: _LookupArguments) -> str:
        raise RuntimeError("private internal detail")

    async def slow(_: _LookupArguments) -> str:
        await asyncio.sleep(1)
        return "late"

    registry.register(
        ToolSpec(
            name="failing_tool",
            description="Fails",
            args_schema=_LookupArguments,
            handler=failure,
        )
    )
    registry.register(
        ToolSpec(
            name="slow_tool",
            description="Slow",
            args_schema=_LookupArguments,
            handler=slow,
            timeout_seconds=0.001,
        )
    )
    executor = ToolExecutor(registry)
    principal = ToolPrincipal("user-1")
    with pytest.raises(ToolExecutionError, match="failing_tool") as caught:
        await executor.execute("failing_tool", {"query": "x"}, principal=principal)
    assert "private internal detail" not in str(caught.value)
    assert isinstance(caught.value.__cause__, RuntimeError)
    with pytest.raises(ToolTimeoutError, match="slow_tool"):
        await executor.execute("slow_tool", {"query": "x"}, principal=principal)


@pytest.mark.anyio
async def test_tool_executor_runs_sync_handlers_and_wraps_handler_timeouts() -> None:
    registry = ToolRegistry()

    def lookup(arguments: _LookupArguments) -> str:
        return arguments.query.upper()

    def raises_timeout(_: _LookupArguments) -> str:
        raise TimeoutError("handler-specific timeout")

    registry.register(
        ToolSpec(
            name="sync_lookup",
            description="Synchronous lookup",
            args_schema=_LookupArguments,
            handler=lookup,
        )
    )
    registry.register(
        ToolSpec(
            name="handler_timeout",
            description="Raises its own timeout",
            args_schema=_LookupArguments,
            handler=raises_timeout,
        )
    )
    executor = ToolExecutor(registry)
    principal = ToolPrincipal("user-1")

    assert await executor.execute("sync_lookup", {"query": "law"}, principal=principal) == "LAW"
    with pytest.raises(ToolExecutionError, match="handler_timeout") as caught:
        await executor.execute("handler_timeout", {"query": "law"}, principal=principal)
    assert isinstance(caught.value.__cause__, TimeoutError)
