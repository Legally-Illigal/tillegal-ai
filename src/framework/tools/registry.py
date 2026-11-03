"""Thread-safe registry for workflow tool definitions."""

import threading

from src.framework.tools.contracts import ToolSpec


class ToolRegistryError(LookupError):
    """Raised when a tool is missing or a duplicate tool is registered."""


class ToolRegistry:
    """Register tools once and resolve them by stable name."""

    def __init__(self) -> None:
        self._tools: dict[str, ToolSpec] = {}
        self._lock = threading.RLock()

    def register(self, tool: ToolSpec) -> None:
        """Register a tool definition; duplicate names are rejected."""
        with self._lock:
            if tool.name in self._tools:
                raise ToolRegistryError(f"Tool {tool.name!r} is already registered")
            self._tools[tool.name] = tool

    def get(self, name: str) -> ToolSpec:
        """Resolve a registered tool."""
        with self._lock:
            try:
                return self._tools[name]
            except KeyError as error:
                raise ToolRegistryError(f"Tool {name!r} is not registered") from error

    def list_tools(self) -> tuple[ToolSpec, ...]:
        """Return registered tools in deterministic name order."""
        with self._lock:
            return tuple(self._tools[name] for name in sorted(self._tools))
