"""Durable crawl-job value returned by the persistence layer."""

from dataclasses import dataclass
from datetime import date, datetime
from typing import Literal
from uuid import UUID

CrawlJobStatus = Literal["PENDING", "RUNNING", "SUCCEEDED", "FAILED", "CANCELLED"]


@dataclass(frozen=True)
class CrawlJob:
    """Persisted lifecycle and result data for one source/date crawl."""

    id: UUID
    source_id: str
    crawl_date: date
    status: CrawlJobStatus
    result: dict[str, object]
    error_message: str | None
    attempts: int
    max_attempts: int
    created_at: datetime
    started_at: datetime | None
    completed_at: datetime | None
    updated_at: datetime
