"""Request and workflow correlation context."""

from collections.abc import Generator
from contextlib import contextmanager
from contextvars import ContextVar, Token

_request_id: ContextVar[str | None] = ContextVar("request_id", default=None)
_workflow_run_id: ContextVar[str | None] = ContextVar("workflow_run_id", default=None)


@contextmanager
def bind_request_context(request_id: str) -> Generator[None, None, None]:
    """Bind a request ID for logs emitted within the current async context."""
    request_token = _request_id.set(request_id)
    workflow_token = _workflow_run_id.set(None)
    try:
        yield
    finally:
        _workflow_run_id.reset(workflow_token)
        _request_id.reset(request_token)


@contextmanager
def bind_workflow_run(workflow_run_id: str) -> Generator[None, None, None]:
    """Bind a workflow run ID while preserving the surrounding request context."""
    token: Token[str | None] = _workflow_run_id.set(workflow_run_id)
    try:
        yield
    finally:
        _workflow_run_id.reset(token)


def current_correlation_context() -> dict[str, str]:
    """Return the correlation identifiers currently bound to this context."""
    context: dict[str, str] = {}
    request_id = _request_id.get()
    workflow_run_id = _workflow_run_id.get()
    if request_id is not None:
        context["request_id"] = request_id
    if workflow_run_id is not None:
        context["workflow_run_id"] = workflow_run_id
    return context
