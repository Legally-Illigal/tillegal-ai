"""Outbox event dispatch use case."""

from dataclasses import dataclass
from uuid import uuid4

from src.application.interfaces.execution_queue import ExecutionQueuePublisher, QueuePublishError
from src.application.interfaces.execution_store import ExecutionStore


@dataclass(frozen=True)
class DispatchSummary:
    """Counts for one dispatcher polling cycle."""

    claimed: int
    published: int
    deferred: int


class OutboxDispatcher:
    """Publish leased events and record acknowledgements or retry schedules."""

    def __init__(
        self,
        store: ExecutionStore,
        publisher: ExecutionQueuePublisher,
        *,
        owner: str | None = None,
        batch_size: int = 50,
        lease_seconds: int = 60,
    ) -> None:
        if batch_size < 1:
            raise ValueError("Outbox batch size must be positive")
        if lease_seconds < 1:
            raise ValueError("Outbox lease duration must be positive")
        self._store = store
        self._publisher = publisher
        self._owner = owner or str(uuid4())
        self._batch_size = batch_size
        self._lease_seconds = lease_seconds

    async def dispatch_once(self) -> DispatchSummary:
        """Publish one batch; failed publishes are persisted for later retry."""
        events = await self._store.claim_outbox_events(
            self._owner,
            self._batch_size,
            self._lease_seconds,
        )
        published = 0
        deferred = 0
        for event in events:
            try:
                await self._publisher.publish(event)
            except QueuePublishError as error:
                retry_after = min(2 ** min(event.attempts - 1, 8), 300)
                await self._store.retry_outbox_event(
                    event.id,
                    self._owner,
                    str(error),
                    retry_after,
                )
                deferred += 1
            else:
                await self._store.mark_outbox_published(event.id, self._owner)
                published += 1
        return DispatchSummary(claimed=len(events), published=published, deferred=deferred)
