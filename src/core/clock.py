"""Clock abstractions for consistent, testable time handling."""

from datetime import UTC, datetime
from typing import Protocol


class Clock(Protocol):
    """Source of timezone-aware UTC timestamps."""

    def now(self) -> datetime:
        """Return the current time in UTC."""


class SystemClock:
    """Clock backed by the system wall clock."""

    def now(self) -> datetime:
        return datetime.now(UTC)


def utc_now() -> datetime:
    """Return the current timezone-aware UTC time."""
    return SystemClock().now()
