"""Queue publisher contract for execution outbox events."""

from typing import Protocol

from src.application.dto.execution import OutboxEvent


class QueuePublishError(RuntimeError):
    """Raised when an event cannot be accepted by the execution queue."""


class ExecutionQueuePublisher(Protocol):
    """Publish an outbox event to a durable execution queue."""

    async def publish(self, event: OutboxEvent) -> None: ...
