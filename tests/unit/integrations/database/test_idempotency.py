"""Tests for PostgreSQL idempotency repository and adapter behavior."""

import asyncio
from typing import Any
from uuid import UUID

import pytest
from pydantic import SecretStr

from src.integrations.database.idempotency_store import (
    IdempotencyResultSerializationError,
    PostgresIdempotencyStore,
)
from src.integrations.database.repositories.idempotency_repository import (
    IdempotencyClaimState,
    IdempotencyKeyConflictError,
    IdempotencyRepository,
)
from src.integrations.database.transaction import PostgresTransactionManager


class _Cursor:
    def __init__(self, row: dict[str, Any] | None = None, rowcount: int = 1) -> None:
        self._row = row
        self.rowcount = rowcount

    def fetchone(self) -> dict[str, Any] | None:
        return self._row


class _ClaimConnection:
    def __init__(self, *, inserted: bool, selected: dict[str, Any] | None = None) -> None:
        self.inserted = inserted
        self.selected = selected
        self.statements: list[str] = []

    def execute(self, query: str, parameters: tuple[object, ...]) -> _Cursor:
        del parameters
        self.statements.append(query)
        if "INSERT INTO public.idempotency_records" in query:
            return _Cursor({"status": "in_progress"} if self.inserted else None)
        if "SELECT request_hash, status, result" in query:
            return _Cursor(self.selected)
        if "UPDATE public.idempotency_records" in query:
            return _Cursor(rowcount=1)
        if "DELETE FROM public.idempotency_records" in query:
            return _Cursor(rowcount=1)
        raise AssertionError(f"Unexpected SQL: {query}")


def test_repository_claim_creates_record_and_recovers_expired_lease() -> None:
    owner = UUID("00000000-0000-0000-0000-000000000001")
    connection = _ClaimConnection(inserted=True)
    claim = IdempotencyRepository(connection).claim(b"k" * 32, b"r" * 32, owner, 30, 600)
    assert claim.state is IdempotencyClaimState.OWNED
    assert len(connection.statements) == 3

    expired_connection = _ClaimConnection(
        inserted=False,
        selected={
            "request_hash": b"r" * 32,
            "status": "in_progress",
            "result": None,
            "lease_expires_at": None,
            "lease_expired": True,
        },
    )
    recovered = IdempotencyRepository(expired_connection).claim(
        b"k" * 32,
        b"r" * 32,
        owner,
        30,
        600,
    )
    assert recovered.state is IdempotencyClaimState.OWNED
    assert any("lease_owner = %s" in sql for sql in expired_connection.statements)


@pytest.mark.parametrize(
    ("status", "result", "expected"),
    [
        ("completed", {"answer": "cached"}, IdempotencyClaimState.COMPLETED),
        ("in_progress", None, IdempotencyClaimState.IN_PROGRESS),
    ],
)
def test_repository_claim_returns_completed_or_active_claim(
    status: str,
    result: object,
    expected: IdempotencyClaimState,
) -> None:
    connection = _ClaimConnection(
        inserted=False,
        selected={
            "request_hash": b"r" * 32,
            "status": status,
            "result": result,
            "lease_expires_at": "later",
            "lease_expired": False,
        },
    )
    claim = IdempotencyRepository(connection).claim(
        b"k" * 32,
        b"r" * 32,
        UUID("00000000-0000-0000-0000-000000000001"),
        30,
        600,
    )
    assert claim.state is expected
    assert claim.result == result


def test_repository_rejects_reusing_a_key_with_different_input() -> None:
    connection = _ClaimConnection(
        inserted=False,
        selected={
            "request_hash": b"other" + b"r" * 27,
            "status": "completed",
            "result": {},
            "lease_expires_at": None,
            "lease_expired": False,
        },
    )
    with pytest.raises(IdempotencyKeyConflictError, match="different tool arguments"):
        IdempotencyRepository(connection).claim(
            b"k" * 32,
            b"r" * 32,
            UUID("00000000-0000-0000-0000-000000000001"),
            30,
            600,
        )


class _InMemoryDatabaseForTest:
    records: dict[bytes, dict[str, object]] = {}


class _FakeIdempotencyRepository:
    def __init__(self, _connection: object) -> None:
        self._records = _InMemoryDatabaseForTest.records

    def claim(self, key_hash, request_hash, owner, lease_seconds, retention_seconds):
        del retention_seconds
        record = self._records.get(key_hash)
        if record is None:
            self._records[key_hash] = {
                "request_hash": request_hash,
                "status": "in_progress",
                "owner": owner,
                "lease_until": asyncio.get_running_loop().time() + lease_seconds,
            }
            return _Claim(IdempotencyClaimState.OWNED)
        if record["request_hash"] != request_hash:
            raise IdempotencyKeyConflictError("Idempotency key was already used with different tool arguments")
        if record["status"] == "completed":
            return _Claim(IdempotencyClaimState.COMPLETED, record["result"])
        if record["lease_until"] <= asyncio.get_running_loop().time():
            record["owner"] = owner
            record["lease_until"] = asyncio.get_running_loop().time() + lease_seconds
            return _Claim(IdempotencyClaimState.OWNED)
        return _Claim(IdempotencyClaimState.IN_PROGRESS)

    def renew(self, key_hash, owner, lease_seconds, retention_seconds):
        del retention_seconds
        record = self._records.get(key_hash)
        if record is None or record["owner"] != owner or record["status"] != "in_progress":
            return False
        record["lease_until"] = asyncio.get_running_loop().time() + lease_seconds
        return True

    def complete(self, key_hash, owner, result, retention_seconds):
        del retention_seconds
        record = self._records[key_hash]
        if record["owner"] != owner:
            raise RuntimeError("lease lost")
        record["status"] = "completed"
        record["result"] = result
        record["owner"] = None

    def release(self, key_hash, owner):
        record = self._records.get(key_hash)
        if record is not None and record["owner"] == owner and record["status"] == "in_progress":
            del self._records[key_hash]


class _Claim:
    def __init__(self, state: IdempotencyClaimState, result: object = None) -> None:
        self.state = state
        self.result = result


@pytest.fixture(autouse=True)
def _clear_fake_database() -> None:
    _InMemoryDatabaseForTest.records.clear()


def _install_fake_database(monkeypatch) -> None:
    async def run(_manager: PostgresTransactionManager, operation):
        return operation(object())

    monkeypatch.setattr(PostgresTransactionManager, "run", run)
    monkeypatch.setattr(
        "src.integrations.database.idempotency_store.IdempotencyRepository",
        _FakeIdempotencyRepository,
    )


@pytest.mark.anyio
async def test_postgres_store_persists_result_and_rejects_fingerprint_mismatch(monkeypatch) -> None:
    _install_fake_database(monkeypatch)
    store = PostgresIdempotencyStore(SecretStr("postgresql://test"))
    calls = 0

    async def operation() -> dict[str, str]:
        nonlocal calls
        calls += 1
        return {"answer": "persisted"}

    result = await store.execute("tool:user:key", "request-hash", operation)
    replay = await store.execute("tool:user:key", "request-hash", operation)

    assert result == replay == {"answer": "persisted"}
    assert calls == 1
    with pytest.raises(IdempotencyKeyConflictError):
        await store.execute("tool:user:key", "different-request", operation)


@pytest.mark.anyio
async def test_postgres_store_coalesces_concurrent_calls_across_store_instances(monkeypatch) -> None:
    _install_fake_database(monkeypatch)
    first_store = PostgresIdempotencyStore(SecretStr("postgresql://test"))
    second_store = PostgresIdempotencyStore(
        SecretStr("postgresql://test"),
        poll_interval_seconds=0.005,
    )
    entered = asyncio.Event()
    release = asyncio.Event()
    calls = 0

    async def operation() -> list[str]:
        nonlocal calls
        calls += 1
        entered.set()
        await release.wait()
        return ["one", "two"]

    first = asyncio.create_task(first_store.execute("same-key", "same-request", operation))
    await entered.wait()
    second = asyncio.create_task(second_store.execute("same-key", "same-request", operation))
    await asyncio.sleep(0.02)
    release.set()

    assert await asyncio.gather(first, second) == [["one", "two"], ["one", "two"]]
    assert calls == 1


@pytest.mark.anyio
async def test_postgres_store_releases_failed_and_non_json_operations(monkeypatch) -> None:
    _install_fake_database(monkeypatch)
    store = PostgresIdempotencyStore(SecretStr("postgresql://test"))

    async def failure() -> object:
        raise RuntimeError("try again")

    with pytest.raises(RuntimeError, match="try again"):
        await store.execute("retry-key", "same-request", failure)

    async def non_json() -> object:
        return object()

    with pytest.raises(IdempotencyResultSerializationError, match="JSON serializable"):
        await store.execute("retry-key", "same-request", non_json)

    async def success() -> str:
        return "ok"

    assert await store.execute("retry-key", "same-request", success) == "ok"
