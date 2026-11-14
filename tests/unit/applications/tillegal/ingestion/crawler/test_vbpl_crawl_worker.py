"""Tests for durable VBPL crawl-job execution."""

import asyncio
from datetime import UTC, date, datetime
from uuid import uuid4

from src.application.dto.crawl_job import CrawlJob
from src.applications.tillegal.ingestion.crawler.vbpl_sitemap import (
    SitemapScanResult,
    SitemapShardResult,
    VbplDocumentUrl,
)
from src.workers.tasks import VbplCrawlWorker


class FakeJobStore:
    def __init__(self) -> None:
        now = datetime.now(UTC)
        self.job = CrawlJob(
            id=uuid4(),
            source_id="vbpl",
            crawl_date=date(2026, 11, 9),
            status="RUNNING",
            result={},
            error_message=None,
            attempts=1,
            max_attempts=3,
            created_at=now,
            started_at=now,
            completed_at=None,
            updated_at=now,
        )
        self.completed: tuple[object, str, dict[str, object]] | None = None
        self.failed: tuple[object, str, str] | None = None

    async def claim(self, owner: str, lease_seconds: int) -> CrawlJob:
        return self.job

    async def renew(self, job_id, owner: str, lease_seconds: int) -> bool:
        return True

    async def succeed(self, job_id, owner: str, result: dict[str, object]) -> None:
        self.completed = (job_id, owner, result)

    async def fail(self, job_id, owner: str, error_message: str) -> None:
        self.failed = (job_id, owner, error_message)


async def fake_document_ingestor(document: VbplDocumentUrl) -> dict[str, object]:
    return {
        "source_record_id": "doc-a",
        "action": "created",
        "attachment_count": 3,
        "downloaded_attachment_count": 3,
    }


def test_worker_persists_sitemap_scan_result(monkeypatch) -> None:
    document = VbplDocumentUrl(
        "https://vbpl.vn/van-ban/chi-tiet/doc-a",
        date(2026, 11, 9),
        "https://vbpl.vn/sitemap/1.xml",
    )
    result = SitemapScanResult(
        target_date=date(2026, 11, 9),
        sitemap_count=1,
        document_url_count=1,
        selected=(document,),
        shards=(SitemapShardResult("https://vbpl.vn/sitemap/1.xml", 1, 1),),
    )
    monkeypatch.setattr("src.workers.tasks.scan_vbpl_sitemaps", lambda target_date: result)
    jobs = FakeJobStore()

    claimed = asyncio.run(
        VbplCrawlWorker(
            jobs,
            document_ingestor=fake_document_ingestor,
            heartbeat_interval_seconds=0.01,
        ).run_once("worker-1")
    )

    assert claimed
    assert jobs.failed is None
    assert jobs.completed is not None
    assert jobs.completed[0] == jobs.job.id
    assert jobs.completed[2]["selected_count"] == 1
    assert jobs.completed[2]["selected"][0]["url"] == document.url
    ingestion = jobs.completed[2]["document_ingestion"]
    assert isinstance(ingestion, dict)
    assert ingestion["created_count"] == 1
    assert ingestion["downloaded_attachment_count"] == 3
    assert ingestion["chunk_count"] == 0
    assert ingestion["embedding_count"] == 0


def test_worker_fails_when_files_need_ingestion_but_storage_is_not_configured(monkeypatch) -> None:
    document = VbplDocumentUrl(
        "https://vbpl.vn/van-ban/chi-tiet/doc-a--1",
        date(2026, 11, 9),
        "https://vbpl.vn/sitemap/1.xml",
    )
    result = SitemapScanResult(
        target_date=date(2026, 11, 9),
        sitemap_count=1,
        document_url_count=1,
        selected=(document,),
        shards=(SitemapShardResult("https://vbpl.vn/sitemap/1.xml", 1, 1),),
    )
    monkeypatch.setattr("src.workers.tasks.scan_vbpl_sitemaps", lambda target_date: result)
    jobs = FakeJobStore()

    claimed = asyncio.run(VbplCrawlWorker(jobs, heartbeat_interval_seconds=0.01).run_once("worker-1"))

    assert claimed
    assert jobs.completed is None
    assert jobs.failed is not None
    assert "SUPABASE_URL" in jobs.failed[2]


def test_worker_persists_crawl_failure(monkeypatch) -> None:
    def fail_scan(target_date):
        raise RuntimeError("sitemap unavailable")

    monkeypatch.setattr("src.workers.tasks.scan_vbpl_sitemaps", fail_scan)
    jobs = FakeJobStore()

    claimed = asyncio.run(VbplCrawlWorker(jobs, heartbeat_interval_seconds=0.01).run_once("worker-1"))

    assert claimed
    assert jobs.completed is None
    assert jobs.failed is not None
    assert jobs.failed[2] == "RuntimeError: sitemap unavailable"
