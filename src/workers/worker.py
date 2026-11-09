"""Background worker entry points."""

import asyncio

from src.core.config import load_settings
from src.core.identifiers import new_id
from src.integrations.database.repositories.crawl_job_repository import CrawlJobRepository
from src.integrations.database.transaction import PostgresTransactionManager
from src.workers.tasks import VbplCrawlWorker


async def run_worker() -> None:
    """Run the ingestion worker as a standalone process."""
    database_url = load_settings().supabase.database_url
    if database_url is None:
        raise ValueError("DATABASE_URL must be set before running the ingestion worker")
    repository = CrawlJobRepository(PostgresTransactionManager(database_url))
    await VbplCrawlWorker(repository).run_forever(str(new_id()))


def main() -> None:
    """Start the worker event loop."""
    asyncio.run(run_worker())


if __name__ == "__main__":
    main()
