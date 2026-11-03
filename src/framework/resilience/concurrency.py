"""Asynchronous concurrency limiting."""

import asyncio
from collections.abc import AsyncIterator, Awaitable, Callable
from contextlib import asynccontextmanager


class ConcurrencyLimitError(TimeoutError):
    """Raised when a concurrency slot is not available before its wait timeout."""


class AsyncConcurrencyLimiter:
    """Bound concurrent operations while allowing callers to configure queue wait."""

    def __init__(self, max_concurrency: int, *, acquire_timeout_seconds: float | None = None) -> None:
        if max_concurrency < 1:
            raise ValueError("max_concurrency must be at least 1")
        if acquire_timeout_seconds is not None and acquire_timeout_seconds <= 0:
            raise ValueError("acquire_timeout_seconds must be greater than 0")
        self.max_concurrency = max_concurrency
        self.acquire_timeout_seconds = acquire_timeout_seconds
        self._semaphore = asyncio.Semaphore(max_concurrency)

    @asynccontextmanager
    async def slot(self) -> AsyncIterator[None]:
        """Acquire and reliably release one concurrency slot."""
        try:
            if self.acquire_timeout_seconds is None:
                await self._semaphore.acquire()
            else:
                await asyncio.wait_for(
                    self._semaphore.acquire(),
                    timeout=self.acquire_timeout_seconds,
                )
        except TimeoutError as error:
            raise ConcurrencyLimitError("Timed out waiting for a concurrency slot") from error
        try:
            yield
        finally:
            self._semaphore.release()

    async def run[T](self, operation: Callable[[], Awaitable[T]]) -> T:
        """Run an asynchronous operation while holding a concurrency slot."""
        async with self.slot():
            return await operation()
