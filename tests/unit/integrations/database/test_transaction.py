"""Tests for PostgreSQL transaction error reporting."""

import asyncio

import psycopg
import pytest
from pydantic import SecretStr

from src.integrations.database.repositories.rpc import DatabaseRepositoryError
from src.integrations.database.transaction import PostgresTransactionManager


def test_transaction_error_includes_sqlstate_without_connection_details(monkeypatch) -> None:
    async def fail_in_thread(function, *args, **kwargs):
        error = psycopg.errors.lookup("42P01")("relation does not exist")
        raise error

    monkeypatch.setattr(asyncio, "to_thread", fail_in_thread)
    manager = PostgresTransactionManager(SecretStr("postgresql://user:password@host/database"))

    with pytest.raises(DatabaseRepositoryError) as raised:
        asyncio.run(manager.run(lambda connection: None))

    assert "SQLSTATE 42P01" in str(raised.value)
    assert "password" not in str(raised.value)


def test_transaction_error_includes_programming_error_detail(monkeypatch) -> None:
    async def fail_in_thread(function, *args, **kwargs):
        raise psycopg.ProgrammingError("cannot adapt type 'dict'")

    monkeypatch.setattr(asyncio, "to_thread", fail_in_thread)
    manager = PostgresTransactionManager(SecretStr("******host/database"))

    with pytest.raises(DatabaseRepositoryError) as raised:
        asyncio.run(manager.run(lambda connection: None))

    assert "cannot adapt type 'dict'" in str(raised.value)
