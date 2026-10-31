"""Tests for execution persistence and transactional outbox behavior."""

import asyncio
from collections.abc import Callable
from typing import Any
from uuid import UUID

import pytest

from src.application.dto.execution import OutboxEvent
from src.application.interfaces.execution_queue import QueuePublishError
from src.application.services.outbox_dispatcher import OutboxDispatcher
from src.integrations.database.execution_store import PostgresExecutionStore
from src.integrations.database.transaction import PostgresTransactionManager


class _FakeCursor:
    def __init__(self, row: dict[str, Any] | None = None, rowcount: int = 1) -> None:
        self._row = row
        self.rowcount = rowcount

    def fetchone(self) -> dict[str, Any] | None:
        return self._row


class _FakeConnection:
    def __init__(self) -> None:
        self.statements: list[tuple[str, tuple[object, ...]]] = []

    def execute(self, query: str, parameters: tuple[object, ...]) -> _FakeCursor:
        self.statements.append((query, parameters))
        if "INSERT INTO public.executions" in query:
            return _FakeCursor({"id": parameters[0]})
        if "INSERT INTO public.outbox_events" in query:
            return _FakeCursor({"id": UUID("00000000-0000-0000-0000-000000000002")})
        raise AssertionError(f"Unexpected SQL: {query}")


def test_execution_and_outbox_are_written_on_one_transaction_connection(monkeypatch) -> None:
    connection = _FakeConnection()

    async def run(
        _manager: PostgresTransactionManager,
        operation: Callable[[_FakeConnection], Any],
    ) -> Any:
        return operation(connection)

    monkeypatch.setattr(PostgresTransactionManager, "run", run)
    store = PostgresExecutionStore("postgresql://test")

    execution_id = asyncio.run(store.submit_execution({"question": "What is the law?"}))

    assert len(connection.statements) == 2
    execution_sql, execution_parameters = connection.statements[0]
    outbox_sql, outbox_parameters = connection.statements[1]
    assert "INSERT INTO public.executions" in execution_sql
    assert "INSERT INTO public.outbox_events" in outbox_sql
    assert execution_parameters[0] == execution_id
    assert outbox_parameters[0] == execution_id


class _FakeStore:
    def __init__(self, events: tuple[OutboxEvent, ...]) -> None:
        self.events = events
        self.published: list[tuple[UUID, str]] = []
        self.retries: list[tuple[UUID, str, str, int]] = []

    async def claim_outbox_events(
        self,
        owner: str,
        limit: int,
        lease_seconds: int,
    ) -> tuple[OutboxEvent, ...]:
        assert owner == "dispatcher-1"
        assert limit == 50
        assert lease_seconds == 60
        return self.events

    async def mark_outbox_published(self, event_id: UUID, owner: str) -> None:
        self.published.append((event_id, owner))

    async def retry_outbox_event(
        self,
        event_id: UUID,
        owner: str,
        error_message: str,
        retry_after_seconds: int,
    ) -> None:
        self.retries.append((event_id, owner, error_message, retry_after_seconds))

    async def submit_execution(self, payload: dict[str, object]) -> UUID:
        raise AssertionError(f"Unexpected submission: {payload}")


class _FakePublisher:
    def __init__(self) -> None:
        self.events: list[OutboxEvent] = []

    async def publish(self, event: OutboxEvent) -> None:
        self.events.append(event)
        if event.attempts == 1:
            raise QueuePublishError("broker unavailable")


def test_dispatcher_retries_failed_publish_and_acknowledges_success() -> None:
    event_id = UUID("00000000-0000-0000-0000-000000000001")
    events = (
        OutboxEvent(
            id=event_id,
            event_type="execution.queued",
            payload={"execution_id": str(event_id)},
            attempts=1,
        ),
        OutboxEvent(
            id=UUID("00000000-0000-0000-0000-000000000002"),
            event_type="execution.queued",
            payload={"execution_id": "00000000-0000-0000-0000-000000000002"},
            attempts=2,
        ),
    )
    store = _FakeStore(events)
    publisher = _FakePublisher()
    dispatcher = OutboxDispatcher(store, publisher, owner="dispatcher-1")

    summary = asyncio.run(dispatcher.dispatch_once())

    assert summary.claimed == 2
    assert summary.published == 1
    assert summary.deferred == 1
    assert store.retries == [(event_id, "dispatcher-1", "broker unavailable", 1)]
    assert store.published == [(events[1].id, "dispatcher-1")]


def test_dispatcher_rejects_nonpositive_batch_size() -> None:
    with pytest.raises(ValueError, match="batch size must be positive"):
        OutboxDispatcher(_FakeStore(()), _FakePublisher(), batch_size=0)
