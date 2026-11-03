"""Bounded synchronous and asynchronous retry helpers."""

import asyncio
import random
import time
from collections.abc import Awaitable, Callable
from dataclasses import dataclass


@dataclass(frozen=True)
class RetryPolicy:
    """Exponential backoff policy with a bounded delay and optional jitter."""

    max_attempts: int = 3
    initial_delay_seconds: float = 0.1
    max_delay_seconds: float = 2.0
    multiplier: float = 2.0
    jitter_ratio: float = 0.0
    retry_exceptions: tuple[type[Exception], ...] = (Exception,)

    def __post_init__(self) -> None:
        if self.max_attempts < 1:
            raise ValueError("max_attempts must be at least 1")
        if self.initial_delay_seconds < 0 or self.max_delay_seconds < 0:
            raise ValueError("retry delays must not be negative")
        if self.multiplier < 1:
            raise ValueError("multiplier must be at least 1")
        if not 0 <= self.jitter_ratio <= 1:
            raise ValueError("jitter_ratio must be between 0 and 1")
        if not self.retry_exceptions or any(
            not isinstance(error_type, type) or not issubclass(error_type, Exception)
            for error_type in self.retry_exceptions
        ):
            raise ValueError("retry_exceptions must contain Exception types")

    def delay_for(self, failed_attempt: int) -> float:
        """Return the delay after a failed attempt (1-based)."""
        if failed_attempt < 1:
            raise ValueError("failed_attempt must be at least 1")
        delay = min(
            self.initial_delay_seconds * self.multiplier ** (failed_attempt - 1),
            self.max_delay_seconds,
        )
        if self.jitter_ratio:
            delay *= random.uniform(1 - self.jitter_ratio, 1 + self.jitter_ratio)
        return min(delay, self.max_delay_seconds)


def retry_sync[T](
    operation: Callable[[], T],
    policy: RetryPolicy,
    *,
    sleep: Callable[[float], None] = time.sleep,
) -> T:
    """Run a synchronous operation, retrying only configured exception types."""
    for attempt in range(1, policy.max_attempts + 1):
        try:
            return operation()
        except policy.retry_exceptions:
            if attempt == policy.max_attempts:
                raise
            sleep(policy.delay_for(attempt))
    raise RuntimeError("unreachable retry state")


async def retry_async[T](
    operation: Callable[[], Awaitable[T]],
    policy: RetryPolicy,
    *,
    sleep: Callable[[float], Awaitable[None]] = asyncio.sleep,
) -> T:
    """Run an asynchronous operation, retrying only configured exception types."""
    for attempt in range(1, policy.max_attempts + 1):
        try:
            return await operation()
        except policy.retry_exceptions:
            if attempt == policy.max_attempts:
                raise
            await sleep(policy.delay_for(attempt))
    raise RuntimeError("unreachable retry state")
