"""Execution submission use case."""

from collections.abc import Mapping
from uuid import UUID

from src.application.interfaces.execution_store import ExecutionStore


class ExecutionService:
    """Submit work for asynchronous execution."""

    def __init__(self, store: ExecutionStore) -> None:
        self._store = store

    async def submit(self, payload: Mapping[str, object]) -> UUID:
        """Persist the execution and its outbox event atomically."""
        return await self._store.submit_execution(payload)
