"""Durable crawl-job value returned by the persistence layer."""

from dataclasses import dataclass
from datetime import date, datetime
from typing import Literal
from uuid import UUID

CrawlJobStatus = Literal["PENDING", "RUNNING", "SUCCEEDED", "FAILED", "CANCELLED"]
CrawlMode = Literal["LASTMOD", "ISSUED_RANGE"]


@dataclass(frozen=True)
class CrawlJob:
    """Persisted lifecycle and checkpoints for one complete crawl run."""

    id: UUID
    source_id: str
    crawl_date: date | None
    status: CrawlJobStatus
    result: dict[str, object]
    error_message: str | None
    attempts: int
    max_attempts: int
    created_at: datetime
    started_at: datetime | None
    completed_at: datetime | None
    updated_at: datetime
    crawl_mode: CrawlMode = "LASTMOD"
    issued_from: date | None = None
    issued_to: date | None = None


def validate_crawl_dates(mode: str, crawl_date: date | None, start: date | None, end: date | None) -> None:
    if mode == "LASTMOD":
        valid = crawl_date is not None and start is None and end is None
    elif mode == "ISSUED_RANGE":
        valid = crawl_date is None and start is not None and end is not None and start <= end
    else:
        valid = False
    if not valid:
        raise ValueError("Use a lastmod date OR an inclusive issued-date range")


def normalize_indexing_report(result: dict[str, object]) -> dict[str, object]:
    """Normalize checkpoints without inferring missing historical indexing evidence."""
    documents = result.get("ingestion", {}).get("documents", {})
    for item in documents.values():
        item.pop("retrieval_ready", None)
        counts = [item.get(key) for key in ("chunk_count", "embedding_count", "sparse_chunk_count")]
        known = all(type(value) is int and value >= 0 for value in counts)
        item["document_indexing_complete"] = counts[0] > 0 and counts[0] == counts[1] == counts[2] if known else None
    summary = result.setdefault("summary", {})
    summary.pop("retrieval_ready", None)
    summary["document_indexing_complete"] = sum(
        item["document_indexing_complete"] is True for item in documents.values()
    )
    summary["document_indexing_unknown"] = sum(
        item["document_indexing_complete"] is None for item in documents.values()
    )
    return result
