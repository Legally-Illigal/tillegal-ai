"""PostgreSQL-backed LangGraph checkpoint storage."""

from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from psycopg_pool import AsyncConnectionPool
from pydantic import SecretStr


class PostgresCheckpointer:
    """Manage a pooled async PostgreSQL connection for LangGraph checkpoints."""

    def __init__(self, database_url: SecretStr) -> None:
        self._pool = AsyncConnectionPool(
            conninfo=database_url.get_secret_value(),
            kwargs={"autocommit": True, "prepare_threshold": 0},
            min_size=1,
            max_size=10,
            open=False,
        )
        self._saver: AsyncPostgresSaver | None = None

    @property
    def saver(self) -> AsyncPostgresSaver:
        """Return the initialized saver for compiling LangGraph workflows."""
        if self._saver is None:
            raise RuntimeError("PostgreSQL checkpointer has not been opened")
        return self._saver

    async def open(self) -> AsyncPostgresSaver:
        """Open the connection pool and initialize LangGraph checkpoint tables."""
        if self._saver is not None:
            raise RuntimeError("PostgreSQL checkpointer is already open")

        try:
            await self._pool.open(wait=True)
            saver = AsyncPostgresSaver(self._pool)
            await saver.setup()
        except Exception:
            await self._pool.close()
            raise

        self._saver = saver
        return saver

    async def close(self) -> None:
        """Close the connection pool."""
        await self._pool.close()
        self._saver = None
