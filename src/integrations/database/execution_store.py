"""PostgreSQL implementation of execution and outbox persistence."""

from collections.abc import Mapping
from typing import Any
from uuid import UUID, uuid4

import psycopg
from pydantic import SecretStr

from src.application.dto.execution import OutboxEvent
from src.application.interfaces.execution_store import ExecutionStore
from src.integrations.database.repositories.execution_repository import ExecutionRepository
from src.integrations.database.repositories.outbox_repository import OutboxRepository
from src.integrations.database.transaction import PostgresTransactionManager


class PostgresExecutionStore(ExecutionStore):
    """Keep execution state and its queued event in a shared PostgreSQL transaction."""

    def __init__(self, database_url: SecretStr) -> None:
        self._transactions = PostgresTransactionManager(database_url)

    async def submit_execution(self, payload: Mapping[str, object]) -> UUID:
        execution_id = uuid4()

        def persist(connection: psycopg.Connection[dict[str, Any]]) -> UUID:
            ExecutionRepository(connection).create_queued(execution_id, payload)
            OutboxRepository(connection).enqueue_execution(execution_id)
            return execution_id

        return await self._transactions.run(persist)

    async def claim_outbox_events(
        self,
        owner: str,
        limit: int,
        lease_seconds: int,
    ) -> tuple[OutboxEvent, ...]:
        return await self._transactions.run(
            lambda connection: OutboxRepository(connection).claim_pending(owner, limit, lease_seconds)
        )

    async def mark_outbox_published(self, event_id: UUID, owner: str) -> None:
        await self._transactions.run(
            lambda connection: OutboxRepository(connection).mark_published(event_id, owner)
        )

    async def retry_outbox_event(
        self,
        event_id: UUID,
        owner: str,
        error_message: str,
        retry_after_seconds: int,
    ) -> None:
        await self._transactions.run(
            lambda connection: OutboxRepository(connection).schedule_retry(
                event_id,
                owner,
                error_message,
                retry_after_seconds,
            )
        )
