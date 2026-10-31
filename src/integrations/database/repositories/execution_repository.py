"""Persistence operations for asynchronous executions."""

from collections.abc import Mapping
from typing import Any
from uuid import UUID

import psycopg
from psycopg.types.json import Jsonb

from src.integrations.database.repositories.rpc import DatabaseRepositoryError


class ExecutionRepository:
    """Read and write execution records using a caller-owned transaction."""

    def __init__(self, connection: psycopg.Connection[dict[str, Any]]) -> None:
        self._connection = connection

    def create_queued(self, execution_id: UUID, payload: Mapping[str, object]) -> UUID:
        """Create a queued execution; the caller controls commit/rollback."""
        row = self._connection.execute(
            """
            INSERT INTO public.executions (id, status, input)
            VALUES (%s, 'queued', %s)
            RETURNING id
            """,
            (execution_id, Jsonb(dict(payload))),
        ).fetchone()
        if row is None:
            raise DatabaseRepositoryError("Creating an execution returned no identifier")
        return row["id"]
