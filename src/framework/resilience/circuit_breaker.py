"""Thread-safe circuit breaker for synchronous and asynchronous operations."""

import asyncio
import threading
import time
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from enum import StrEnum


class CircuitState(StrEnum):
    """Observable circuit-breaker states."""

    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


class CircuitOpenError(RuntimeError):
    """Raised when an operation is rejected by an open circuit."""


@dataclass(frozen=True)
class CircuitBreakerPolicy:
    """Threshold and recovery timeout for a circuit breaker."""

    failure_threshold: int = 5
    recovery_timeout_seconds: float = 30.0
    half_open_max_calls: int = 1

    def __post_init__(self) -> None:
        if self.failure_threshold < 1:
            raise ValueError("failure_threshold must be at least 1")
        if self.recovery_timeout_seconds <= 0:
            raise ValueError("recovery_timeout_seconds must be greater than 0")
        if self.half_open_max_calls < 1:
            raise ValueError("half_open_max_calls must be at least 1")


class CircuitBreaker:
    """Reject calls during outages and probe recovery with a bounded half-open phase."""

    def __init__(
        self,
        policy: CircuitBreakerPolicy | None = None,
        *,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self.policy = policy or CircuitBreakerPolicy()
        self._clock = clock
        self._state = CircuitState.CLOSED
        self._failure_count = 0
        self._opened_at: float | None = None
        self._half_open_calls = 0
        self._lock = threading.Lock()

    @property
    def state(self) -> CircuitState:
        """Return the current state, transitioning to half-open when recovery is due."""
        with self._lock:
            self._refresh_state()
            return self._state

    def call[**P, T](self, operation: Callable[P, T], *args: P.args, **kwargs: P.kwargs) -> T:
        """Execute a synchronous operation through the circuit."""
        self._before_call()
        try:
            result = operation(*args, **kwargs)
        except Exception:
            self._record_failure()
            raise
        self._record_success()
        return result

    async def call_async[T](
        self,
        operation: Callable[[], Awaitable[T]],
    ) -> T:
        """Execute an asynchronous operation through the circuit."""
        self._before_call()
        try:
            result = await operation()
        except asyncio.CancelledError:
            self._release_half_open_probe()
            raise
        except Exception:
            self._record_failure()
            raise
        self._record_success()
        return result

    def _before_call(self) -> None:
        with self._lock:
            self._refresh_state()
            if self._state is CircuitState.OPEN:
                raise CircuitOpenError("Circuit is open; operation was not executed")
            if self._state is CircuitState.HALF_OPEN:
                if self._half_open_calls >= self.policy.half_open_max_calls:
                    raise CircuitOpenError("Circuit is half-open; recovery probe limit reached")
                self._half_open_calls += 1

    def _refresh_state(self) -> None:
        if (
            self._state is CircuitState.OPEN
            and self._opened_at is not None
            and self._clock() - self._opened_at >= self.policy.recovery_timeout_seconds
        ):
            self._state = CircuitState.HALF_OPEN
            self._half_open_calls = 0

    def _record_failure(self) -> None:
        with self._lock:
            if self._state is CircuitState.HALF_OPEN:
                self._open()
                return
            self._failure_count += 1
            if self._failure_count >= self.policy.failure_threshold:
                self._open()

    def _record_success(self) -> None:
        with self._lock:
            if self._state is CircuitState.HALF_OPEN:
                self._state = CircuitState.CLOSED
                self._opened_at = None
            self._failure_count = 0
            self._half_open_calls = 0

    def _release_half_open_probe(self) -> None:
        with self._lock:
            if self._state is CircuitState.HALF_OPEN:
                self._half_open_calls = max(0, self._half_open_calls - 1)

    def _open(self) -> None:
        self._state = CircuitState.OPEN
        self._opened_at = self._clock()
        self._half_open_calls = 0
