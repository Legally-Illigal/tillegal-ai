"""Permission-checked, schema-validated asynchronous tool execution."""

import asyncio
import hashlib
import inspect
import json
from collections.abc import Mapping

from pydantic import BaseModel, ValidationError

from src.framework.tools.contracts import ToolIdempotencyStore, ToolSpec
from src.framework.tools.error_handling import (
    ToolExecutionError,
    ToolTimeoutError,
    input_validation_error,
)
from src.framework.tools.permissions import PermissionPolicy, ToolPrincipal
from src.framework.tools.registry import ToolRegistry


class ToolExecutor:
    """Validate, authorize, optionally deduplicate, and execute registered tools."""

    def __init__(
        self,
        registry: ToolRegistry,
        *,
        permission_policy: PermissionPolicy | None = None,
        idempotency_store: ToolIdempotencyStore | None = None,
    ) -> None:
        self._registry = registry
        self._permission_policy = permission_policy or PermissionPolicy()
        self._idempotency_store = idempotency_store

    async def execute(
        self,
        name: str,
        arguments: Mapping[str, object],
        *,
        principal: ToolPrincipal,
        idempotency_key: str | None = None,
    ) -> object:
        """Execute a named tool after input validation and permission checks."""
        tool = self._registry.get(name)
        self._permission_policy.authorize(
            tool.name,
            tool.required_permissions,
            principal,
        )
        validated_arguments = self._validate(tool, arguments)

        async def invoke() -> object:
            return await self._invoke_handler(tool, validated_arguments)

        if idempotency_key is None:
            return await invoke()
        if not idempotency_key.strip():
            raise ValueError("idempotency_key must not be blank")
        if self._idempotency_store is None:
            raise ValueError("An idempotency store is required when idempotency_key is provided")
        scoped_key = json.dumps(
            [tool.name, principal.principal_id, idempotency_key],
            ensure_ascii=False,
            separators=(",", ":"),
        )
        canonical_arguments = json.dumps(
            validated_arguments.model_dump(mode="json"),
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        )
        fingerprint = hashlib.sha256(canonical_arguments.encode("utf-8")).hexdigest()
        return await self._idempotency_store.execute(scoped_key, fingerprint, invoke)

    @staticmethod
    def _validate(tool: ToolSpec, arguments: Mapping[str, object]) -> BaseModel:
        try:
            return tool.args_schema.model_validate(arguments)
        except ValidationError as error:
            raise input_validation_error(error) from error

    @staticmethod
    async def _invoke_handler(tool: ToolSpec, arguments: BaseModel) -> object:
        async def call_handler() -> object:
            if inspect.iscoroutinefunction(tool.handler):
                result = tool.handler(arguments)
            else:
                result = await asyncio.to_thread(tool.handler, arguments)
            if inspect.isawaitable(result):
                return await result
            return result

        task = asyncio.create_task(call_handler())
        try:
            done, _ = await asyncio.wait((task,), timeout=tool.timeout_seconds)
        except asyncio.CancelledError:
            task.cancel()
            task.add_done_callback(_consume_task_exception)
            raise
        if not done:
            task.cancel()
            task.add_done_callback(_consume_task_exception)
            raise ToolTimeoutError(f"Tool {tool.name!r} exceeded its execution timeout")

        try:
            return await task
        except asyncio.CancelledError:
            raise
        except Exception as error:
            raise ToolExecutionError(f"Tool {tool.name!r} failed") from error


def _consume_task_exception(task: asyncio.Task[object]) -> None:
    if not task.cancelled():
        task.exception()
