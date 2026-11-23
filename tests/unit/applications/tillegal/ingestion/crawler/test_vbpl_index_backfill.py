import asyncio
from uuid import uuid4

import pytest

from src.workers.vbpl_index_backfill import backfill_dense


class Repository:
    def __init__(self):
        self.pending = [{"id": str(uuid4()), "content": "Example"}]
        self.saved = []
        self.refreshed = False

    async def get_index(self, name):
        return {"model_name": "intfloat/multilingual-e5-small", "embedding_dimension": 384}

    async def list_embedding_work(self, name, statuses, limit):
        assert "SKIPPED" in statuses
        return self.pending

    async def upsert_embeddings(self, name, writes):
        self.saved.extend(writes)
        self.pending = []
        return len(writes)

    async def refresh_index_status(self, name):
        self.refreshed = True
        return "READY"


class Embedder:
    def embed_passages(self, texts, batch_size):
        return [tuple([0.1] * 384) for text in texts]


def test_backfill_repairs_pending_and_refreshes():
    repo = Repository()
    assert asyncio.run(backfill_dense(repo, Embedder(), 8)) == {"count": 1, "status": "READY"}
    assert repo.refreshed and len(repo.saved) == 1


def test_resume_with_no_work_does_not_load_model():
    repo = Repository()
    repo.pending = []
    assert asyncio.run(backfill_dense(repo, None, 8))["count"] == 0


def test_bad_vector_count_does_not_write_or_refresh():
    class Broken:
        def embed_passages(self, texts, batch_size):
            return []

    repo = Repository()
    with pytest.raises(ValueError):
        asyncio.run(backfill_dense(repo, Broken(), 8))
    assert not repo.saved and not repo.refreshed


def test_retry_backfill_handles_statement_timeout_but_not_permissions(monkeypatch):
    from postgrest.exceptions import APIError

    from src.integrations.database.repositories.rpc import DatabaseRepositoryError
    from src.workers.vbpl_index_backfill import RetryBackfillRpc

    class Base:
        calls = 0
        code = "57014"

        async def call_rpc(self, name, parameters):
            self.calls += 1
            if self.calls < 3:
                try:
                    raise APIError({"code": self.code, "message": "failure", "details": None, "hint": None})
                except APIError as cause:
                    raise DatabaseRepositoryError("failure") from cause
            return "ok"

    class Repo(RetryBackfillRpc, Base):
        pass

    delays = []

    async def sleep(delay):
        delays.append(delay)

    monkeypatch.setattr("src.workers.vbpl_index_backfill.asyncio.sleep", sleep)
    repo = Repo()
    assert asyncio.run(repo.call_rpc("list_dense_embedding_work", {})) == "ok"
    assert repo.calls == 3 and delays == [2, 4]
    repo = Repo()
    repo.code = "42501"
    with pytest.raises(DatabaseRepositoryError):
        asyncio.run(repo.call_rpc("list_dense_embedding_work", {}))
    assert repo.calls == 1


def test_dense_backfill_read_uses_short_readonly_transaction():
    from src.workers.vbpl_index_backfill import BackfillDenseRepository

    class Cursor:
        def fetchall(self):
            return [{"id": str(uuid4()), "content": "text"}]

    class Connection:
        calls = []

        def execute(self, query, parameters=None):
            self.calls.append((query, parameters))
            return Cursor()

    class Transactions:
        connection = Connection()

        async def run(self, operation):
            return operation(self.connection)

    transactions = Transactions()
    repo = BackfillDenseRepository(None, transactions)
    rows = asyncio.run(repo.list_embedding_work("index", limit=32))
    assert len(rows) == 1
    queries = transactions.connection.calls
    assert queries[0][0] == "SET TRANSACTION READ ONLY"
    assert "statement_timeout = '60s'" in queries[1][0]
    assert queries[3][1] == ("index", ["PENDING", "STALE", "FAILED"], 32)
    assert "e.embedding IS NULL" in queries[3][0]
    assert "vector_dims" in queries[3][0]
