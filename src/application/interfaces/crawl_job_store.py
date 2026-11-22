"""Persistence contract for durable ingestion jobs."""

from datetime import date
from typing import Protocol
from uuid import UUID

from src.application.dto.crawl_job import CrawlJob, CrawlMode


class CrawlJobStore(Protocol):
    """Store and lease durable crawl jobs."""

    async def create(
        self,
        source_id: str,
        crawl_date: date | None = None,
        *,
        crawl_mode: CrawlMode = "LASTMOD",
        issued_from: date | None = None,
        issued_to: date | None = None,
    ) -> CrawlJob: ...

    async def checkpoint(self, job_id: UUID, owner: str, result: dict[str, object]) -> bool: ...

    async def retry_failed(self, job_id: UUID) -> CrawlJob | None: ...

    async def get(self, job_id: UUID) -> CrawlJob | None: ...

    async def get_index_status(self) -> dict[str, object]: ...

    async def claim(self, owner: str, lease_seconds: int) -> CrawlJob | None: ...

    async def renew(self, job_id: UUID, owner: str, lease_seconds: int) -> bool: ...

    async def succeed(self, job_id: UUID, owner: str, result: dict[str, object]) -> None: ...

    async def fail(self, job_id: UUID, owner: str, error_message: str) -> None: ...
