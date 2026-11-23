"""Tests for crawl-job JSONB persistence."""

import asyncio
from uuid import uuid4

from psycopg.types.json import Jsonb

from src.integrations.database.repositories.crawl_job_repository import CrawlJobRepository


def test_finish_wraps_results_for_jsonb_adaptation() -> None:
    class Cursor:
        def fetchone(self):
            return {"id": job_id}

    class Connection:
        parameters = None

        def execute(self, query, parameters):
            self.parameters = parameters
            return Cursor()

    class TransactionManager:
        connection = Connection()

        async def run(self, operation):
            return operation(self.connection)

    job_id = uuid4()
    transactions = TransactionManager()
    repository = CrawlJobRepository(transactions)
    result = {"selected_count": 1, "selected": [{"url": "https://vbpl.vn/"}]}

    asyncio.run(repository.succeed(job_id, "worker-1", result))

    saved_result = transactions.connection.parameters[2]
    assert isinstance(saved_result, Jsonb)
    assert saved_result.obj == result


class MemoryTransactions:
    """Exercise repository calls concurrently without connecting to any database."""

    def __init__(self):
        import threading

        self.lock = threading.Lock()
        self.rows = {}
        self.queries = []

    async def run(self, operation):
        def transaction():
            # Models transaction-scoped advisory locking; SQL guards are asserted below.
            with self.lock:
                return operation(self)

        return await asyncio.to_thread(transaction)

    def execute(self, query, parameters=None):
        from datetime import UTC, datetime
        from types import SimpleNamespace

        self.queries.append((query, parameters))
        row = None
        if "INSERT INTO public.crawl_jobs" in query:
            job_id, source, target, mode, start, end = parameters
            now = datetime.now(UTC)
            row = dict(
                id=job_id,
                source_id=source,
                crawl_date=target,
                crawl_mode=mode,
                issued_from=start,
                issued_to=end,
                status="PENDING",
                result={},
                error_message=None,
                attempts=0,
                max_attempts=3,
                created_at=now,
                updated_at=now,
                started_at=None,
                completed_at=None,
            )
            self.rows[job_id] = row
        elif "SELECT *" in query and "source_id = %s" in query:
            source, mode, target, start, end, statuses = parameters
            row = next(
                (
                    r
                    for r in self.rows.values()
                    if (r["source_id"], r["crawl_mode"], r["crawl_date"], r["issued_from"], r["issued_to"])
                    == (source, mode, target, start, end)
                    and r["status"] in statuses
                ),
                None,
            )
        elif "SELECT *" in query:
            row = self.rows.get(parameters[0])
        elif "SET status='PENDING'" in query:
            result, job_id = parameters
            row = self.rows[job_id]
            row.update(status="PENDING", result=result.obj, attempts=0)
        return SimpleNamespace(fetchone=lambda: row, rowcount=1)


def test_concurrent_create_reuses_only_active_jobs_in_both_modes():
    from datetime import date

    transactions = MemoryTransactions()
    repository = CrawlJobRepository(transactions)

    async def run():
        for mode in ("LASTMOD", "ISSUED_RANGE"):
            kwargs = (
                {"crawl_date": date(2024, 1, 1)}
                if mode == "LASTMOD"
                else {"crawl_mode": mode, "issued_from": date(2024, 1, 1), "issued_to": date(2024, 1, 31)}
            )
            jobs = await asyncio.gather(*(repository.create("vbpl", **kwargs) for _ in range(12)))
            assert len({job.id for job in jobs}) == 1
            transactions.rows[jobs[0].id]["status"] = "SUCCEEDED"
            assert (await repository.create("vbpl", **kwargs)).id != jobs[0].id

    asyncio.run(run())
    locks = [q for q, _ in transactions.queries if "pg_advisory_xact_lock" in q]
    assert len(locks) == 26
    selects = [q for q, _ in transactions.queries if "status = ANY" in q]
    assert all("crawl_mode = %s" in q and "issued_to IS NOT DISTINCT FROM %s" in q for q in selects)


def test_retry_failed_preserves_success_and_metadata():
    from datetime import date

    transactions = MemoryTransactions()
    repository = CrawlJobRepository(transactions)

    async def run():
        job = await repository.create("vbpl", date(2024, 1, 1))
        transactions.rows[job.id].update(
            status="SUCCEEDED",
            result={
                "discovery": {"complete": True},
                "existing": {"keep": True},
                "ingestion": {
                    "documents": {
                        "a": {"status": "SUCCEEDED", "source_document_id": "saved"},
                        "b": {"status": "FAILED", "error": "EmptyMarkdownError", "attempts": 1},
                    }
                },
            },
        )
        retried = await repository.retry_failed(job.id)
        assert retried.status == "PENDING" and retried.attempts == 0
        assert retried.result["ingestion"]["documents"]["a"] == {
            "status": "SUCCEEDED",
            "source_document_id": "saved",
        }
        assert retried.result["ingestion"]["documents"]["b"]["status"] == "PENDING"
        assert retried.result["existing"] == {"keep": True}
        assert retried.result["discovery"]["complete"] is True

    asyncio.run(run())


def test_checkpoint_is_fenced_by_unexpired_lease_and_merges_json():
    transactions = MemoryTransactions()
    repository = CrawlJobRepository(transactions)
    assert asyncio.run(repository.checkpoint(uuid4(), "owner", {"phase": "discovery"}))
    sql, parameters = transactions.queries[-1]
    assert "owner = %s" in sql and "lease_until > now()" in sql and "status = 'RUNNING'" in sql
    assert "result = result || %s" in sql
    assert isinstance(parameters[0], Jsonb)


def test_invalid_dates_rejected_before_database_transaction():
    from datetime import date

    import pytest

    transactions = MemoryTransactions()
    repository = CrawlJobRepository(transactions)
    with pytest.raises(ValueError):
        asyncio.run(
            repository.create(
                "vbpl", crawl_mode="ISSUED_RANGE", issued_from=date(2024, 2, 1), issued_to=date(2024, 1, 1)
            )
        )
    assert not transactions.queries
