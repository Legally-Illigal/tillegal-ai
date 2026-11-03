"""Tests for the PostgreSQL LangGraph checkpointer lifecycle."""

import pytest
from pydantic import SecretStr

from src.integrations.langgraph.postgres_checkpointer import PostgresCheckpointer


@pytest.mark.anyio
async def test_checkpointer_opens_pool_and_sets_up_saver(monkeypatch) -> None:
    calls: list[object] = []
    pool_instance = None

    class FakePool:
        def __init__(self, **kwargs) -> None:
            nonlocal pool_instance
            calls.append(kwargs)
            pool_instance = self

        async def open(self, *, wait: bool) -> None:
            calls.append(("open", wait))

        async def close(self) -> None:
            calls.append("close")

    class FakeSaver:
        def __init__(self, pool) -> None:
            assert pool is pool_instance
            calls.append("saver")

        async def setup(self) -> None:
            calls.append("setup")

    monkeypatch.setattr(
        "src.integrations.langgraph.postgres_checkpointer.AsyncConnectionPool",
        FakePool,
    )
    monkeypatch.setattr(
        "src.integrations.langgraph.postgres_checkpointer.AsyncPostgresSaver",
        FakeSaver,
    )
    checkpointer = PostgresCheckpointer(SecretStr("postgresql://example/db"))

    saver = await checkpointer.open()

    assert saver is checkpointer.saver
    assert calls == [
        {
            "conninfo": "postgresql://example/db",
            "kwargs": {"autocommit": True, "prepare_threshold": 0},
            "min_size": 1,
            "max_size": 10,
            "open": False,
        },
        ("open", True),
        "saver",
        "setup",
    ]

    await checkpointer.close()

    assert calls[-1] == "close"


@pytest.mark.anyio
async def test_checkpointer_closes_pool_when_setup_fails(monkeypatch) -> None:
    calls: list[str] = []

    class FakePool:
        def __init__(self, **kwargs) -> None:
            assert kwargs["max_size"] == 10

        async def open(self, *, wait: bool) -> None:
            calls.append(("open", wait))

        async def close(self) -> None:
            calls.append("close")

    class FakeSaver:
        def __init__(self, pool) -> None:
            assert pool is not None

        async def setup(self) -> None:
            raise RuntimeError("setup failed")

    monkeypatch.setattr(
        "src.integrations.langgraph.postgres_checkpointer.AsyncConnectionPool",
        FakePool,
    )
    monkeypatch.setattr(
        "src.integrations.langgraph.postgres_checkpointer.AsyncPostgresSaver",
        FakeSaver,
    )
    checkpointer = PostgresCheckpointer(SecretStr("postgresql://example/db"))

    with pytest.raises(RuntimeError, match="setup failed"):
        await checkpointer.open()

    assert calls == [("open", True), "close"]
