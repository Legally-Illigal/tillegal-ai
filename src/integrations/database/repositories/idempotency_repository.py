"""PostgreSQL operations for durable tool-call idempotency records."""

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from typing import Any
from uuid import UUID

import psycopg
from psycopg.types.json import Jsonb

from src.integrations.database.repositories.rpc import DatabaseRepositoryError


class IdempotencyKeyConflictError(ValueError):
    """Raised when an existing idempotency key is reused for different input."""


class IdempotencyLeaseLostError(RuntimeError):
    """Raised when a worker no longer owns an in-progress idempotency record."""


class IdempotencyClaimState(StrEnum):
    """Possible outcomes when claiming an idempotency key."""

    OWNED = "owned"
    COMPLETED = "completed"
    IN_PROGRESS = "in_progress"


@dataclass(frozen=True)
class IdempotencyClaim:
    """Result of attempting to claim a persisted idempotency key."""

    state: IdempotencyClaimState
    result: object = None
    lease_expires_at: datetime | None = None


class IdempotencyRepository:
    """Claim, renew, complete, and release records in a caller-owned transaction."""

    def __init__(self, connection: psycopg.Connection[dict[str, Any]]) -> None:
        self._connection = connection

    def claim(
        self,
        key_hash: bytes,
        request_hash: bytes,
        owner: UUID,
        lease_seconds: int,
        retention_seconds: int,
    ) -> IdempotencyClaim:
        """Claim a key, return its stored result, or report another active owner."""
        self._connection.execute(
            """
            WITH expired AS (
                SELECT key_hash
                FROM public.idempotency_records
                WHERE expires_at <= now()
                ORDER BY expires_at
                LIMIT 100
                FOR UPDATE SKIP LOCKED
            )
            DELETE FROM public.idempotency_records AS record
            USING expired
            WHERE record.key_hash = expired.key_hash
            """,
            (),
        )
        self._connection.execute(
            """
            DELETE FROM public.idempotency_records
            WHERE key_hash = %s AND expires_at <= now()
            """,
            (key_hash,),
        )
        inserted = self._connection.execute(
            """
            INSERT INTO public.idempotency_records (
                key_hash, request_hash, status, lease_owner, lease_expires_at, expires_at
            )
            VALUES (
                %s, %s, 'in_progress', %s,
                now() + make_interval(secs => %s),
                now() + make_interval(secs => %s)
            )
            ON CONFLICT (key_hash) DO NOTHING
            RETURNING status
            """,
            (key_hash, request_hash, owner, lease_seconds, lease_seconds + retention_seconds),
        ).fetchone()
        if inserted is not None:
            return IdempotencyClaim(IdempotencyClaimState.OWNED)

        row = self._connection.execute(
            """
            SELECT request_hash, status, result, lease_expires_at,
                   lease_expires_at <= now() AS lease_expired
            FROM public.idempotency_records
            WHERE key_hash = %s
            FOR UPDATE
            """,
            (key_hash,),
        ).fetchone()
        if row is None:
            raise DatabaseRepositoryError("Idempotency record disappeared while being claimed")
        if row["request_hash"] != request_hash:
            raise IdempotencyKeyConflictError("Idempotency key was already used with different tool arguments")
        if row["status"] == "completed":
            return IdempotencyClaim(
                IdempotencyClaimState.COMPLETED,
                result=row["result"],
            )
        if row["lease_expired"]:
            self._connection.execute(
                """
                UPDATE public.idempotency_records
                SET lease_owner = %s,
                    lease_expires_at = now() + make_interval(secs => %s),
                    expires_at = now() + make_interval(secs => %s),
                    updated_at = now()
                WHERE key_hash = %s
                """,
                (owner, lease_seconds, lease_seconds + retention_seconds, key_hash),
            )
            return IdempotencyClaim(IdempotencyClaimState.OWNED)
        return IdempotencyClaim(
            IdempotencyClaimState.IN_PROGRESS,
            lease_expires_at=row["lease_expires_at"],
        )

    def renew(self, key_hash: bytes, owner: UUID, lease_seconds: int, retention_seconds: int) -> bool:
        """Extend the active owner's lease and record retention window."""
        cursor = self._connection.execute(
            """
            UPDATE public.idempotency_records
            SET lease_expires_at = now() + make_interval(secs => %s),
                expires_at = now() + make_interval(secs => %s),
                updated_at = now()
            WHERE key_hash = %s AND lease_owner = %s AND status = 'in_progress'
            """,
            (lease_seconds, lease_seconds + retention_seconds, key_hash, owner),
        )
        return cursor.rowcount == 1

    def complete(
        self,
        key_hash: bytes,
        owner: UUID,
        result: object,
        retention_seconds: int,
    ) -> None:
        """Persist a successful JSON-compatible result for subsequent retries."""
        cursor = self._connection.execute(
            """
            UPDATE public.idempotency_records
            SET status = 'completed',
                result = %s,
                lease_owner = NULL,
                lease_expires_at = NULL,
                expires_at = now() + make_interval(secs => %s),
                updated_at = now()
            WHERE key_hash = %s AND lease_owner = %s AND status = 'in_progress'
            """,
            (Jsonb(result), retention_seconds, key_hash, owner),
        )
        if cursor.rowcount != 1:
            raise IdempotencyLeaseLostError("Cannot complete an idempotency record without its lease")

    def release(self, key_hash: bytes, owner: UUID) -> None:
        """Remove an unfinished record so a later attempt can retry."""
        self._connection.execute(
            """
            DELETE FROM public.idempotency_records
            WHERE key_hash = %s AND lease_owner = %s AND status = 'in_progress'
            """,
            (key_hash, owner),
        )
