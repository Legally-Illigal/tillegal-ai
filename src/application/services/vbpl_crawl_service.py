"""Application use case for requesting VBPL sitemap discovery."""

from datetime import date
from uuid import UUID

from src.application.dto.crawl_job import CrawlJob
from src.application.interfaces.crawl_job_store import CrawlJobStore
from src.applications.tillegal.ingestion.crawler.vbpl_sitemap import current_vietnam_date


class VbplCrawlService:
    """Create and retrieve durable VBPL crawl jobs."""

    def __init__(self, jobs: CrawlJobStore) -> None:
        self._jobs = jobs

    async def request_crawl(self, target_date: date | None = None) -> CrawlJob:
        """Queue discovery for the supplied date, defaulting to Vietnam today."""
        return await self._jobs.create("vbpl", target_date or current_vietnam_date())

    async def get_job(self, job_id: UUID) -> CrawlJob | None:
        """Return a crawl job by ID."""
        return await self._jobs.get(job_id)
