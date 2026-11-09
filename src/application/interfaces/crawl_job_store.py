"""Persistence contract for durable ingestion jobs."""

from datetime import date
from typing import Protocol
from uuid import UUID

from src.application.dto.crawl_job import CrawlJob


class CrawlJobStore(Protocol):
    """Store and lease durable crawl jobs."""

    async def create(self, source_id: str, crawl_date: date) -> CrawlJob: ...

    async def get(self, job_id: UUID) -> CrawlJob | None: ...

    async def claim(self, owner: str, lease_seconds: int) -> CrawlJob | None: ...

    async def renew(self, job_id: UUID, owner: str, lease_seconds: int) -> bool: ...

    async def succeed(self, job_id: UUID, owner: str, result: dict[str, object]) -> None: ...

    async def fail(self, job_id: UUID, owner: str, error_message: str) -> None: ...
