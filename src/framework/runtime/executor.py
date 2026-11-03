"""Execute asynchronous graph workflows with cancellation and timeout handling."""

import asyncio
from collections.abc import Mapping
from typing import Protocol, TypeVar

from src.framework.runtime.cancellation import ExecutionCancelledError
from src.framework.runtime.execution_context import ExecutionContext, bind_execution_context
from src.framework.runtime.lifecycle import ExecutionLifecycle, ExecutionStatus

InputT = TypeVar("InputT")
OutputT = TypeVar("OutputT")


class AsyncGraph(Protocol[InputT, OutputT]):
    """Minimal protocol implemented by compiled asynchronous graph workflows."""

    async def ainvoke(
        self,
        input: InputT,
        config: Mapping[str, object] | None = None,
    ) -> OutputT: ...


class GraphExecutor:
    """Run a graph while propagating context and enforcing cancellation/deadlines."""

    async def execute[InputT, OutputT](
        self,
        graph: AsyncGraph[InputT, OutputT],
        graph_input: InputT,
        context: ExecutionContext,
        *,
        config: Mapping[str, object] | None = None,
        timeout_seconds: float | None = None,
        lifecycle: ExecutionLifecycle | None = None,
    ) -> OutputT:
        """Invoke a graph and update lifecycle on success, failure, or cancellation."""
        if timeout_seconds is not None and timeout_seconds <= 0:
            raise ValueError("timeout_seconds must be greater than 0")
        context.cancellation_token.raise_if_cancelled()
        execution_lifecycle = lifecycle or ExecutionLifecycle()
        execution_lifecycle.start()
        invocation = asyncio.create_task(self._invoke(graph, graph_input, context, config))
        cancellation = asyncio.create_task(context.cancellation_token.wait_cancelled())
        try:
            done, _ = await asyncio.wait(
                (invocation, cancellation),
                timeout=timeout_seconds,
                return_when=asyncio.FIRST_COMPLETED,
            )
            if not done:
                await self._cancel_invocation(invocation)
                execution_lifecycle.fail(f"Graph execution exceeded {timeout_seconds} seconds")
                raise TimeoutError(f"Graph execution exceeded {timeout_seconds} seconds")
            if cancellation in done and invocation not in done:
                await self._cancel_invocation(invocation)
                execution_lifecycle.cancel()
                reason = context.cancellation_token.reason
                message = "Execution cancelled"
                if reason:
                    message = f"{message}: {reason}"
                raise ExecutionCancelledError(message)

            output = await invocation
            execution_lifecycle.succeed()
            return output
        except asyncio.CancelledError:
            if execution_lifecycle.snapshot.status is ExecutionStatus.RUNNING:
                execution_lifecycle.cancel()
            if not invocation.done():
                await self._cancel_invocation(invocation)
            raise
        except Exception as error:
            if execution_lifecycle.snapshot.status is ExecutionStatus.RUNNING:
                execution_lifecycle.fail(f"{type(error).__name__}: {error}")
            raise
        finally:
            if not cancellation.done():
                cancellation.cancel()
            try:
                await cancellation
            except asyncio.CancelledError:
                pass

    @staticmethod
    async def _invoke[InputT, OutputT](
        graph: AsyncGraph[InputT, OutputT],
        graph_input: InputT,
        context: ExecutionContext,
        config: Mapping[str, object] | None,
    ) -> OutputT:
        with bind_execution_context(context):
            return await graph.ainvoke(graph_input, config=config)

    @staticmethod
    async def _cancel_invocation[T](invocation: asyncio.Task[T]) -> None:
        invocation.cancel()
        try:
            await invocation
        except asyncio.CancelledError:
            pass
