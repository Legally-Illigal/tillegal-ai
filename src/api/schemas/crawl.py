"""Request and response schemas for ingestion crawl jobs."""

from datetime import date, datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, model_validator

from src.application.dto.crawl_job import CrawlJob


class VbplIssuedSearchRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    issued_from: date
    issued_to: date

    @model_validator(mode="after")
    def validate_range(self):
        if self.issued_from > self.issued_to:
            raise ValueError("issued_from must be <= issued_to")
        return self


class VbplCrawlRequest(BaseModel):
    """Request sitemap discovery for a date; omitted date means Vietnam today."""

    model_config = ConfigDict(extra="forbid")

    crawl_date: date | None = None
    crawl_mode: Literal["LASTMOD", "ISSUED_RANGE"] = "LASTMOD"
    issued_from: date | None = None
    issued_to: date | None = None

    @model_validator(mode="after")
    def validate_dates(self):
        from src.application.dto.crawl_job import validate_crawl_dates
        from src.applications.tillegal.ingestion.crawler.vbpl_sitemap import current_vietnam_date

        target = self.crawl_date
        if self.crawl_mode == "LASTMOD" and target is None:
            target = current_vietnam_date()
        validate_crawl_dates(self.crawl_mode, target, self.issued_from, self.issued_to)
        return self


class CrawlJobResponse(BaseModel):
    """Public crawl-job status and result."""

    id: UUID
    source_id: str
    crawl_date: date | None
    crawl_mode: Literal["LASTMOD", "ISSUED_RANGE"] = "LASTMOD"
    issued_from: date | None = None
    issued_to: date | None = None
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
