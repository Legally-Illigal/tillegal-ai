"""Execution metadata propagated through async workflow tasks."""

from collections.abc import Mapping
from contextvars import ContextVar, Token
from dataclasses import dataclass, field
from types import MappingProxyType

from src.framework.runtime.cancellation import CancellationToken

_current_context: ContextVar["ExecutionContext | None"] = ContextVar(
    "framework_execution_context",
    default=None,
)


@dataclass(frozen=True)
class ExecutionContext:
    """Immutable identifiers and controls associated with one workflow run."""

    run_id: str
    request_id: str | None = None
    parent_run_id: str | None = None
    metadata: Mapping[str, str] = field(default_factory=dict)
    cancellation_token: CancellationToken = field(default_factory=CancellationToken, compare=False)

    def __post_init__(self) -> None:
        if not self.run_id.strip():
            raise ValueError("run_id must not be blank")
        if self.request_id is not None and not self.request_id.strip():
            raise ValueError("request_id must not be blank when provided")
        if self.parent_run_id is not None and not self.parent_run_id.strip():
            raise ValueError("parent_run_id must not be blank when provided")
        if any(not isinstance(key, str) or not key for key in self.metadata):
            raise ValueError("metadata keys must be non-empty strings")
        if any(not isinstance(value, str) for value in self.metadata.values()):
            raise ValueError("metadata values must be strings")
        object.__setattr__(self, "metadata", MappingProxyType(dict(self.metadata)))


def current_execution_context() -> ExecutionContext | None:
    """Return the execution context bound to the current async context."""
    return _current_context.get()


class _ExecutionContextBinding:
    """Context manager that binds an execution context and restores the prior value."""

    def __init__(self, context: ExecutionContext) -> None:
        self._context = context
        self._token: Token[ExecutionContext | None] | None = None

    def __enter__(self) -> ExecutionContext:
        self._token = _current_context.set(self._context)
        return self._context

    def __exit__(self, *_: object) -> None:
        if self._token is None:
            raise RuntimeError("Execution context manager was not entered")
        _current_context.reset(self._token)
        self._token = None

    async def __aenter__(self) -> ExecutionContext:
        return self.__enter__()

    async def __aexit__(self, *_: object) -> None:
        self.__exit__()


def bind_execution_context(context: ExecutionContext) -> _ExecutionContextBinding:
    """Bind an execution context for the duration of a with or async-with block."""
    return _ExecutionContextBinding(context)
