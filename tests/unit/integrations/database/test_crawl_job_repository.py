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
