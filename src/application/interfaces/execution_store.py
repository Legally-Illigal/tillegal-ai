"""Persistence contract for execution submission and outbox dispatch."""

from collections.abc import Mapping
from typing import Protocol
from uuid import UUID

from src.application.dto.execution import OutboxEvent


class ExecutionStore(Protocol):
    """Atomic execution/outbox storage and lease operations."""

    async def submit_execution(self, payload: Mapping[str, object]) -> UUID: ...

    async def claim_outbox_events(
        self,
        owner: str,
        limit: int,
        lease_seconds: int,
    ) -> tuple[OutboxEvent, ...]: ...

    async def mark_outbox_published(self, event_id: UUID, owner: str) -> None: ...

    async def retry_outbox_event(
        self,
        event_id: UUID,
        owner: str,
        error_message: str,
        retry_after_seconds: int,
    ) -> None: ...
