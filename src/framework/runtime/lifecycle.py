"""Validated execution lifecycle state transitions."""

import threading
from dataclasses import dataclass
from datetime import UTC, datetime
from enum import StrEnum


class ExecutionStatus(StrEnum):
    """Supported workflow execution states."""

    CREATED = "created"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    CANCELLED = "cancelled"


class InvalidLifecycleTransitionError(RuntimeError):
    """Raised when an execution attempts an invalid lifecycle transition."""


@dataclass(frozen=True)
class LifecycleSnapshot:
    """Immutable snapshot of execution status and timestamps."""

    status: ExecutionStatus
    created_at: datetime
    started_at: datetime | None
    finished_at: datetime | None
    error: str | None


class ExecutionLifecycle:
    """Track one execution and reject transitions out of terminal states."""

    _TERMINAL_STATUSES = frozenset({ExecutionStatus.SUCCEEDED, ExecutionStatus.FAILED, ExecutionStatus.CANCELLED})

    def __init__(self) -> None:
        now = datetime.now(UTC)
        self._snapshot = LifecycleSnapshot(
            status=ExecutionStatus.CREATED,
            created_at=now,
            started_at=None,
            finished_at=None,
            error=None,
        )
        self._lock = threading.Lock()

    @property
    def snapshot(self) -> LifecycleSnapshot:
        """Return the latest immutable lifecycle state."""
        with self._lock:
            return self._snapshot

    def start(self) -> LifecycleSnapshot:
        """Move a newly created execution to running."""
        with self._lock:
            self._require_status(ExecutionStatus.CREATED)
            self._snapshot = LifecycleSnapshot(
                status=ExecutionStatus.RUNNING,
                created_at=self._snapshot.created_at,
                started_at=datetime.now(UTC),
                finished_at=None,
                error=None,
            )
            return self._snapshot

    def succeed(self) -> LifecycleSnapshot:
        """Mark a running execution successful."""
        return self._finish(ExecutionStatus.SUCCEEDED)

    def fail(self, error: str) -> LifecycleSnapshot:
        """Mark a running execution failed with a non-empty error description."""
        if not error.strip():
            raise ValueError("error must not be blank")
        return self._finish(ExecutionStatus.FAILED, error=error)

    def cancel(self) -> LifecycleSnapshot:
        """Mark a running execution cancelled."""
        return self._finish(ExecutionStatus.CANCELLED)

    def _finish(
        self,
        status: ExecutionStatus,
        *,
        error: str | None = None,
    ) -> LifecycleSnapshot:
        with self._lock:
            self._require_status(ExecutionStatus.RUNNING)
            self._snapshot = LifecycleSnapshot(
                status=status,
                created_at=self._snapshot.created_at,
                started_at=self._snapshot.started_at,
                finished_at=datetime.now(UTC),
                error=error,
            )
            return self._snapshot

    def _require_status(self, expected: ExecutionStatus) -> None:
        if self._snapshot.status is not expected:
            if self._snapshot.status in self._TERMINAL_STATUSES:
                reason = "execution is already terminal"
            else:
                reason = f"expected {expected.value}, got {self._snapshot.status.value}"
            raise InvalidLifecycleTransitionError(reason)
