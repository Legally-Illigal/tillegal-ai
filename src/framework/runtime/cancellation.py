"""Cooperative cancellation token for asynchronous workflow tasks."""

import asyncio


class ExecutionCancelledError(asyncio.CancelledError):
    """Raised when a workflow is cancelled through its execution context."""


class CancellationToken:
    """Share a cooperative cancellation signal across workflow components."""

    def __init__(self) -> None:
        self._event = asyncio.Event()
        self._reason: str | None = None

    @property
    def is_cancelled(self) -> bool:
        """Return whether cancellation has been requested."""
        return self._event.is_set()

    @property
    def reason(self) -> str | None:
        """Return the optional cancellation reason."""
        return self._reason

    def cancel(self, reason: str | None = None) -> None:
        """Request cancellation; the first request determines the reason."""
        if not self._event.is_set():
            self._reason = reason
            self._event.set()

    async def wait_cancelled(self) -> None:
        """Wait until cancellation has been requested."""
        await self._event.wait()

    def raise_if_cancelled(self) -> None:
        """Raise the cancellation exception when cancellation was requested."""
        if self.is_cancelled:
            message = "Execution cancelled"
            if self._reason:
                message = f"{message}: {self._reason}"
            raise ExecutionCancelledError(message)
