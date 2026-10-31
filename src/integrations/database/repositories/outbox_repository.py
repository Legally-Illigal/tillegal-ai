"""Persistence operations for transactional outbox events."""

from typing import Any
from uuid import UUID

import psycopg
from psycopg.types.json import Jsonb

from src.application.dto.execution import OutboxEvent
from src.integrations.database.repositories.rpc import DatabaseRepositoryError


class OutboxLeaseError(DatabaseRepositoryError):
    """Raised when an outbox event is no longer leased by the caller."""


class OutboxRepository:
    """Enqueue and lease outbox events using a caller-owned transaction."""

    def __init__(self, connection: psycopg.Connection[dict[str, Any]]) -> None:
        self._connection = connection

    def enqueue_execution(self, execution_id: UUID) -> UUID:
        """Insert the execution event in the same transaction as its execution."""
        row = self._connection.execute(
            """
            INSERT INTO public.outbox_events (
                aggregate_type, aggregate_id, event_type, payload
            )
            VALUES ('execution', %s, 'execution.queued', %s)
            RETURNING id
            """,
            (execution_id, Jsonb({"execution_id": str(execution_id)})),
        ).fetchone()
        if row is None:
            raise DatabaseRepositoryError("Creating an outbox event returned no identifier")
        return row["id"]

    def claim_pending(
        self,
        owner: str,
        limit: int,
        lease_seconds: int,
    ) -> tuple[OutboxEvent, ...]:
        """Lease available events without blocking competing dispatchers."""
        if not owner.strip():
            raise ValueError("Outbox lease owner must not be blank")
        if limit < 1:
            raise ValueError("Outbox claim limit must be positive")
        if lease_seconds < 1:
            raise ValueError("Outbox lease duration must be positive")

        rows = self._connection.execute(
            """
            WITH candidates AS (
                SELECT id
                FROM public.outbox_events
                WHERE published_at IS NULL
                    AND available_at <= now()
                    AND (locked_until IS NULL OR locked_until < now())
                ORDER BY created_at, id
                FOR UPDATE SKIP LOCKED
                LIMIT %s
            )
            UPDATE public.outbox_events AS event
            SET locked_by = %s,
                locked_until = now() + make_interval(secs => %s),
                attempts = event.attempts + 1
            FROM candidates
            WHERE event.id = candidates.id
            RETURNING event.id, event.event_type, event.payload, event.attempts
            """,
            (limit, owner, lease_seconds),
        ).fetchall()
        return tuple(OutboxEvent.model_validate(row) for row in rows)

    def mark_published(self, event_id: UUID, owner: str) -> None:
        """Acknowledge publication only for the current lease owner."""
        cursor = self._connection.execute(
            """
            UPDATE public.outbox_events
            SET published_at = now(),
                locked_by = NULL,
                locked_until = NULL,
                last_error = NULL
            WHERE id = %s AND locked_by = %s AND published_at IS NULL
            """,
            (event_id, owner),
        )
        if cursor.rowcount != 1:
            raise OutboxLeaseError(f"Outbox event {event_id} is not leased by {owner}")

    def schedule_retry(
        self,
        event_id: UUID,
        owner: str,
        error_message: str,
        retry_after_seconds: int,
    ) -> None:
        """Release a failed event and make it eligible after a bounded delay."""
        if retry_after_seconds < 1:
            raise ValueError("Outbox retry delay must be positive")

        cursor = self._connection.execute(
            """
            UPDATE public.outbox_events
            SET available_at = now() + make_interval(secs => %s),
                locked_by = NULL,
                locked_until = NULL,
                last_error = %s
            WHERE id = %s AND locked_by = %s AND published_at IS NULL
            """,
            (retry_after_seconds, error_message[:2000], event_id, owner),
        )
        if cursor.rowcount != 1:
            raise OutboxLeaseError(f"Outbox event {event_id} is not leased by {owner}")
