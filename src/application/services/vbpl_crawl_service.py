"""Application use case for requesting VBPL sitemap discovery."""

from copy import deepcopy
from dataclasses import replace
from datetime import date
from uuid import UUID

from src.application.dto.crawl_job import CrawlJob, CrawlMode, normalize_indexing_report, validate_crawl_dates
from src.application.interfaces.crawl_job_store import CrawlJobStore
from src.applications.tillegal.ingestion.crawler.vbpl_sitemap import current_vietnam_date


class VbplCrawlService:
    """Create and retrieve durable VBPL crawl jobs."""

    def __init__(self, jobs: CrawlJobStore) -> None:
        self._jobs = jobs

    async def request_crawl(
        self,
        target_date: date | None = None,
        *,
        crawl_mode: CrawlMode = "LASTMOD",
        issued_from: date | None = None,
        issued_to: date | None = None,
    ) -> CrawlJob:
        """Queue discovery for the supplied date, defaulting to Vietnam today."""
        if crawl_mode == "LASTMOD":
            target_date = target_date or current_vietnam_date()
        validate_crawl_dates(crawl_mode, target_date, issued_from, issued_to)
        if crawl_mode == "LASTMOD":
            return await self._jobs.create("vbpl", target_date)
        return await self._jobs.create(
            "vbpl",
            None,
            crawl_mode=crawl_mode,
            issued_from=issued_from,
            issued_to=issued_to,
        )

    async def retry_failed(self, job_id: UUID) -> CrawlJob | None:
        return await self._jobs.retry_failed(job_id)

    async def get_job(self, job_id: UUID) -> CrawlJob | None:
        """Return a crawl job by ID."""
        job = await self._jobs.get(job_id)
        if job is None or job.source_id != "vbpl":
            return None
        result = normalize_indexing_report(deepcopy(job.result))
        if hasattr(self._jobs, "get_index_status"):
            result["index_status"] = await self._jobs.get_index_status()
        return replace(job, result=result)
