"""Request and response schemas for ingestion crawl jobs."""

from datetime import date, datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from src.application.dto.crawl_job import CrawlJob


class VbplCrawlRequest(BaseModel):
    """Request sitemap discovery for a date; omitted date means Vietnam today."""

    model_config = ConfigDict(extra="forbid")

    crawl_date: date | None = None


class CrawlJobResponse(BaseModel):
    """Public crawl-job status and result."""

    id: UUID
    source_id: str
    crawl_date: date
    status: Literal["PENDING", "RUNNING", "SUCCEEDED", "FAILED", "CANCELLED"]
    result: dict[str, object]
    error_message: str | None
    attempts: int
    max_attempts: int
    created_at: datetime
    started_at: datetime | None
    completed_at: datetime | None
    updated_at: datetime

    @classmethod
    def from_job(cls, job: CrawlJob) -> "CrawlJobResponse":
        """Build an API response from the application value."""
        return cls(**job.__dict__)
