"""Short-lived PostgreSQL transactions for application repositories."""

import asyncio
from collections.abc import Callable
from typing import Any, TypeVar

import psycopg
from psycopg.rows import dict_row
from pydantic import SecretStr

from src.integrations.database.repositories.rpc import DatabaseRepositoryError

T = TypeVar("T")
TransactionOperation = Callable[[psycopg.Connection[dict[str, Any]]], T]


class PostgresTransactionManager:
    """Run a synchronous database operation in an isolated worker thread."""

    def __init__(self, database_url: SecretStr) -> None:
        self._database_url = database_url

    async def run(self, operation: TransactionOperation[T]) -> T:
        """Run an operation atomically without blocking the async event loop."""
        try:
            return await asyncio.to_thread(self._run, operation)
        except psycopg.Error as error:
            raise DatabaseRepositoryError("PostgreSQL transaction failed") from error

    def _run(self, operation: TransactionOperation[T]) -> T:
        with psycopg.connect(
            self._database_url.get_secret_value(),
            row_factory=dict_row,
        ) as connection:
            with connection.transaction():
                return operation(connection)
