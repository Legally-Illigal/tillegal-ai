"""PostgreSQL-backed idempotency for tool calls across workers and restarts."""

import asyncio
import hashlib
import json
import time
from collections.abc import Awaitable, Callable
from uuid import UUID, uuid4

from pydantic import SecretStr

from src.framework.tools.contracts import ToolIdempotencyStore
from src.integrations.database.repositories.idempotency_repository import (
    IdempotencyClaimState,
    IdempotencyLeaseLostError,
    IdempotencyRepository,
)
from src.integrations.database.transaction import PostgresTransactionManager


class IdempotencyWaitTimeoutError(TimeoutError):
    """Raised when another active owner does not finish before the wait deadline."""


class IdempotencyResultSerializationError(TypeError):
    """Raised when a tool result cannot be persisted as JSON."""


class PostgresIdempotencyStore(ToolIdempotencyStore):
    """Persist successful results and coordinate concurrent requests in PostgreSQL.

    The operation runs outside the database transaction. A lease is renewed while
    it runs, and the result is committed after success. This avoids holding a
    database transaction open over arbitrary tool work, but cannot make external
    side effects and result persistence one atomic operation.
    """

    def __init__(
        self,
        database_url: SecretStr,
        *,
        lease_seconds: int = 60,
        retention_seconds: int = 86_400,
        wait_timeout_seconds: float = 120.0,
        poll_interval_seconds: float = 0.1,
    ) -> None:
        if lease_seconds < 3:
            raise ValueError("lease_seconds must be at least 3")
        if retention_seconds < 1:
            raise ValueError("retention_seconds must be positive")
        if wait_timeout_seconds <= 0:
            raise ValueError("wait_timeout_seconds must be positive")
        if poll_interval_seconds <= 0:
            raise ValueError("poll_interval_seconds must be positive")
        self._transactions = PostgresTransactionManager(database_url)
        self._lease_seconds = lease_seconds
        self._retention_seconds = retention_seconds
        self._wait_timeout_seconds = wait_timeout_seconds
        self._poll_interval_seconds = poll_interval_seconds

    async def execute(
        self,
        key: str,
        request_fingerprint: str,
        operation: Callable[[], Awaitable[object]],
    ) -> object:
        """Return a stored success or run once while holding a renewable DB lease."""
        normalized_key = key.strip()
        if not normalized_key:
            raise ValueError("idempotency key must not be blank")
        if not request_fingerprint.strip():
            raise ValueError("request_fingerprint must not be blank")
        key_hash = hashlib.sha256(normalized_key.encode("utf-8")).digest()
        request_hash = hashlib.sha256(request_fingerprint.encode("utf-8")).digest()
        owner = uuid4()
        deadline = time.monotonic() + self._wait_timeout_seconds

        while True:
            claim = await self._transactions.run(
                lambda connection: IdempotencyRepository(connection).claim(
                    key_hash,
                    request_hash,
                    owner,
                    self._lease_seconds,
                    self._retention_seconds,
                )
            )
            if claim.state is IdempotencyClaimState.COMPLETED:
                return claim.result
            if claim.state is IdempotencyClaimState.OWNED:
                return await self._execute_as_owner(key_hash, owner, operation)

            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise IdempotencyWaitTimeoutError("Timed out waiting for the active idempotent operation")
            await asyncio.sleep(min(self._poll_interval_seconds, remaining))

    async def _execute_as_owner(
        self,
        key_hash: bytes,
        owner: UUID,
        operation: Callable[[], Awaitable[object]],
    ) -> object:
        operation_task = asyncio.create_task(operation())
        heartbeat_task = asyncio.create_task(self._maintain_lease(key_hash, owner))
        try:
            done, _ = await asyncio.wait(
                (operation_task, heartbeat_task),
                return_when=asyncio.FIRST_COMPLETED,
            )
            if operation_task not in done:
                await heartbeat_task
                raise IdempotencyLeaseLostError("Idempotency lease renewal stopped unexpectedly")

            result = await operation_task
            normalized_result = self._normalize_result(result)
            await self._transactions.run(
                lambda connection: IdempotencyRepository(connection).complete(
                    key_hash,
                    owner,
                    normalized_result,
                    self._retention_seconds,
                )
            )
            heartbeat_error = await self._cancel_task(heartbeat_task)
            if heartbeat_error is not None:
                raise heartbeat_error
            return normalized_result
        except BaseException as error:
            cleanup_errors = (
                await self._cancel_task(operation_task),
                await self._cancel_task(heartbeat_task),
            )
            for cleanup_error in cleanup_errors:
                if cleanup_error is not None:
                    error.add_note(f"Idempotency task cleanup failed: {cleanup_error!r}")
            try:
                await self._transactions.run(
                    lambda connection: IdempotencyRepository(connection).release(key_hash, owner)
                )
            except Exception as release_error:
                error.add_note(f"Could not release idempotency lease: {release_error!r}")
            raise

    async def _maintain_lease(self, key_hash: bytes, owner: UUID) -> None:
        interval = self._lease_seconds / 3
        while True:
            await asyncio.sleep(interval)
            renewed = await self._transactions.run(
                lambda connection: IdempotencyRepository(connection).renew(
                    key_hash,
                    owner,
                    self._lease_seconds,
                    self._retention_seconds,
                )
            )
            if not renewed:
                raise IdempotencyLeaseLostError("Idempotency lease was lost before operation completion")

    @staticmethod
    async def _cancel_task(
        task: asyncio.Task[object] | asyncio.Task[None],
    ) -> BaseException | None:
        if not task.done():
            task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            return None
        except Exception as error:
            return error
        return None

    @staticmethod
    def _normalize_result(result: object) -> object:
        try:
            encoded = json.dumps(
                result,
                ensure_ascii=False,
                sort_keys=True,
                separators=(",", ":"),
                allow_nan=False,
            )
            return json.loads(encoded)
        except (TypeError, ValueError, OverflowError) as error:
            raise IdempotencyResultSerializationError(
                "Tool result must be JSON serializable when an idempotency key is used"
            ) from error
