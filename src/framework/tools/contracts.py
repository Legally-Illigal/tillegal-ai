"""Validated contracts for permissioned workflow tools."""

import re
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Protocol

from pydantic import BaseModel

type ToolHandler = Callable[[BaseModel], object]


class ToolIdempotencyStore(Protocol):
    """Persistence port for deduplicating tool calls across workers."""

    async def execute(
        self,
        key: str,
        request_fingerprint: str,
        operation: Callable[[], Awaitable[object]],
    ) -> object: ...


_TOOL_NAME_PATTERN = re.compile(r"[a-z][a-z0-9_]{1,63}\Z")


@dataclass(frozen=True)
class ToolSpec:
    """Tool definition with an input schema and explicit permission requirements."""

    name: str
    description: str
    args_schema: type[BaseModel]
    handler: ToolHandler
    required_permissions: frozenset[str] = frozenset()
    timeout_seconds: float = 30.0

    def __post_init__(self) -> None:
        if not _TOOL_NAME_PATTERN.fullmatch(self.name):
            raise ValueError("tool name must be 2-64 lowercase letters, digits, or underscores")
        if not self.description.strip():
            raise ValueError("tool description must not be blank")
        if not isinstance(self.args_schema, type) or not issubclass(self.args_schema, BaseModel):
            raise TypeError("args_schema must be a Pydantic BaseModel class")
        if not callable(self.handler):
            raise TypeError("tool handler must be callable")
        if self.timeout_seconds <= 0:
            raise ValueError("timeout_seconds must be greater than 0")
        if not isinstance(self.required_permissions, (set, frozenset)):
            raise TypeError("required_permissions must be a set of permission names")
        if any(not isinstance(permission, str) or not permission.strip() for permission in self.required_permissions):
            raise ValueError("required permissions must not be blank")
        object.__setattr__(self, "required_permissions", frozenset(self.required_permissions))
