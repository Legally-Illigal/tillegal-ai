"""Offline tests of checkpoints, resume, partial failure and ownership."""

import asyncio
from copy import deepcopy
from dataclasses import replace
from datetime import UTC, date, datetime
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from src.api.schemas.crawl import VbplCrawlRequest
from src.application.dto.crawl_job import CrawlJob
from src.applications.tillegal.ingestion.crawler.vbpl_search import SearchPage
from src.bootstrap import create_app
from src.core.config import AppSettings, VbplCrawlSettings
from src.workers.tasks import VbplCrawlWorker


class FakeJobStore:
    def __init__(self, mode="LASTMOD"):
        now = datetime.now(UTC)
        self.job = CrawlJob(
            uuid4(),
            "vbpl",
            date(2024, 1, 1) if mode == "LASTMOD" else None,
            "RUNNING",
            {},
            None,
            1,
            3,
            now,
            now,
            None,
            now,
            mode,
            date(2024, 1, 1) if mode == "ISSUED_RANGE" else None,
            date(2024, 1, 31) if mode == "ISSUED_RANGE" else None,
        )
        self.completed = None
        self.failed = None
        self.checkpoints = []
        self.owned = True

    async def claim(self, owner, lease_seconds):
        return self.job

    async def renew(self, *args):
        return self.owned

    async def checkpoint(self, job_id, owner, result):
        if not self.owned:
            return False
        self.checkpoints.append(deepcopy(result))
        self.job = replace(self.job, result=deepcopy(result))
        return True

    async def succeed(self, job_id, owner, result):
        self.completed = deepcopy(result)

    async def fail(self, job_id, owner, error):
        self.failed = error

    async def get(self, job_id):
        return self.job

    async def create(self, source_id, crawl_date=None, **kwargs):
        self.job = replace(self.job, source_id=source_id, crawl_date=crawl_date, **kwargs)
        return self.job


def worker(store, ingest=None):
    return VbplCrawlWorker(
        store,
        document_ingestor=ingest,
        settings=VbplCrawlSettings(request_pause_seconds=0),
        heartbeat_interval_seconds=0.01,
    )


def setup_sitemap(monkeypatch):
    def fetch(url, settings):
        if url.endswith("sitemap.xml"):
            return b"<sitemapindex><sitemap><loc>https://vbpl.vn/1.xml</loc></sitemap></sitemapindex>"
        return b"""<urlset>
        <url><loc>https://vbpl.vn/van-ban/chi-tiet/a</loc><lastmod>2024-01-01</lastmod></url>
        <url><loc>https://vbpl.vn/van-ban/chi-tiet/b</loc><lastmod>2024-01-01</lastmod></url>
        <url><loc>https://vbpl.vn/van-ban/chi-tiet/c</loc><lastmod>2024-01-02</lastmod></url>
        </urlset>"""

    monkeypatch.setattr("src.workers.tasks.sitemap._fetch_sitemap", fetch)


def test_lastmod_partial_success_and_restart_skip(monkeypatch):
    setup_sitemap(monkeypatch)
    store = FakeJobStore()
    store.job = replace(store.job, result={"existing": {"keep": True}})
    calls = []

    async def ingest(document):
        calls.append(document.url)
        if document.url.endswith("a"):
            raise ValueError("empty Markdown")
        return {"source_document_id": "saved", "markdown_skipped_reason": "antiword_unavailable"}

    asyncio.run(worker(store, ingest).run_once("owner"))
    assert len(calls) == 2
    assert store.failed is None
    assert store.completed["summary"] == {
        "discovered": 2,
        "succeeded": 1,
        "failed": 1,
        "pending": 0,
        "partial_failure": True,
        "stored": 1,
        "stored_unknown": 1,
        "stored_evidence": "confirmed_only; historical missing/false does not prove source absence",
        "document_indexing_complete": 0,
        "document_indexing_unknown": 2,
    }
    assert store.completed["existing"] == {"keep": True}
    assert len(store.checkpoints) == 5
    asyncio.run(worker(store, ingest).run_once("owner"))
    assert len(calls) == 2
    for item in store.job.result["ingestion"]["documents"].values():
        if item["status"] == "FAILED":
            item["status"] = "PENDING"
    asyncio.run(worker(store, ingest).run_once("owner"))
    assert len(calls) == 3 and calls[-1].endswith("a")


def test_issued_pages_and_resume_after_discovery_failure(monkeypatch):
    store = FakeJobStore("ISSUED_RANGE")
    pages, processed = [], []
    broken = True

    def fetch(start, end, page, settings):
        assert (start, end) == (date(2024, 1, 1), date(2024, 1, 31))
        pages.append(page)
        if page == 2 and broken:
            raise TimeoutError()
        ids = range(10) if page == 1 else range(10, 11)
        return SearchPage(
            11, page, [{"id": str(i), "document_url": f"https://vbpl.vn/van-ban/chi-tiet/{i}"} for i in ids]
        )

    async def ingest(document):
        processed.append(document.url)
        return {"markdown_indexing": {"dense_index_status": "READY", "sparse_index_status": "READY"}}

    monkeypatch.setattr("src.workers.tasks.fetch_search_page", fetch)
    asyncio.run(worker(store, ingest).run_once("owner"))
    assert len(processed) == 10 and store.completed is None
    assert store.job.result["discovery"]["next_page"] == 2
    broken = False
    asyncio.run(worker(store, ingest).run_once("owner"))
    assert pages == [1, 2, 2, 2, 2]
    assert len(processed) == len(set(processed)) == 11
    assert store.completed["summary"]["succeeded"] == 11


def test_lease_loss_cancels_ingestion_and_never_finishes(monkeypatch):
    setup_sitemap(monkeypatch)
    store = FakeJobStore()
    cancelled = []

    async def ingest(document):
        store.owned = False
        try:
            await asyncio.sleep(1)
        finally:
            cancelled.append(True)

    asyncio.run(worker(store, ingest).run_once("owner"))
    assert cancelled == [True]
    assert store.completed is None and store.failed is None
    assert all(item["status"] == "PENDING" for item in store.job.result["ingestion"]["documents"].values())


def test_missing_ingestor_is_job_failure(monkeypatch):
    setup_sitemap(monkeypatch)
    store = FakeJobStore()
    asyncio.run(worker(store).run_once("owner"))
    assert store.failed and store.completed is None


@pytest.mark.parametrize(
    "body",
    [
        {"crawl_mode": "LASTMOD", "issued_from": "2024-01-01"},
        {"crawl_mode": "ISSUED_RANGE", "issued_from": "2024-01-31", "issued_to": "2024-01-01"},
        {"crawl_mode": "ISSUED_RANGE", "issued_from": "2024-01-01"},
        {
            "crawl_mode": "ISSUED_RANGE",
            "crawl_date": "2024-01-01",
            "issued_from": "2024-01-01",
            "issued_to": "2024-01-31",
        },
    ],
)
def test_invalid_modes_and_dates(body):
    with pytest.raises(ValueError):
        VbplCrawlRequest(**body)


def test_api_old_lastmod_and_issued_alias():
    app = create_app(AppSettings())
    store = FakeJobStore()
    app.state.crawl_job_store = store
    with TestClient(app) as client:
        response = client.post("/ingestion/vbpl/crawl", json={"crawl_date": "2024-01-01"})
        assert response.json()["crawl_mode"] == "LASTMOD"
        response = client.post(
            "/ingestion/vbpl/search",
            json={
                "issued_from": "2024-01-01",
                "issued_to": "2024-01-31",
            },
        )
        assert response.status_code == 202
        assert response.json()["crawl_date"] is None
        assert response.json()["crawl_mode"] == "ISSUED_RANGE"
        assert client.get(f"/ingestion/vbpl/jobs/{store.job.id}").status_code == 200


def test_api_retry_returns_conflict_and_progress():
    app = create_app(AppSettings())
    store = FakeJobStore()
    app.state.crawl_job_store = store

    async def retry(job_id):
        if store.job.status == "RUNNING":
            raise ValueError("Retry requires a completed job")
        store.job = replace(store.job, status="PENDING")
        return store.job

    store.retry_failed = retry
    with TestClient(app) as client:
        url = f"/ingestion/vbpl/jobs/{store.job.id}/retry-failed"
        assert client.post(url).status_code == 409
        store.job = replace(store.job, status="SUCCEEDED", result={"summary": {"failed": 1}})
        response = client.post(url)
        assert response.status_code == 202
        assert response.json()["status"] == "PENDING"
        assert response.json()["result"]["summary"]["failed"] == 1


def test_checkpoint_rejection_does_not_continue_to_next_document(monkeypatch):
    setup_sitemap(monkeypatch)
    store = FakeJobStore()
    calls = []

    async def ingest(document):
        calls.append(document.url)
        store.owned = False
        return {}

    asyncio.run(worker(store, ingest).run_once("owner"))
    assert len(calls) == 1
    assert store.completed is None and store.failed is None


def test_http_diagnostics_never_include_secret_urls():
    import httpx

    from src.workers.tasks import _error_details

    response = httpx.Response(429, request=httpx.Request("GET", "https://example.com/?token=SECRET"))
    error = httpx.HTTPStatusError("SECRET", request=response.request, response=response)
    details = _error_details(error)
    assert details == {
        "type": "HTTPStatusError",
        "http_status": 429,
        "retryable": True,
        "stage": "ingestion",
        "reason": "ingestion_failed",
        "message": "Operation failed at ingestion.",
    }
    assert "SECRET" not in str(details)


def test_transient_document_http_error_retried_without_repeating_success(monkeypatch):
    from src.applications.tillegal.ingestion.crawler.vbpl_document import VbplDocumentFetchError

    setup_sitemap(monkeypatch)
    store = FakeJobStore()
    calls = []
    sleeps = []
    original_sleep = asyncio.sleep

    async def sleep(delay):
        sleeps.append(delay)
        await original_sleep(0)

    async def ingest(document):
        calls.append(document.url)
        if len(calls) == 1:
            raise VbplDocumentFetchError("private URL must not be saved", status_code=429, retry_after="3")
        return {}

    monkeypatch.setattr("src.workers.tasks.asyncio.sleep", sleep)
    asyncio.run(worker(store, ingest).run_once("owner"))
    assert len(calls) == 3
    assert calls[0] == calls[1] and calls[1] != calls[2]
    assert 3 in sleeps
    assert store.completed["summary"]["succeeded"] == 2
    assert "private URL" not in str(store.checkpoints)


def test_search_http_failure_preserves_page_and_status(monkeypatch):
    import httpx

    store = FakeJobStore("ISSUED_RANGE")

    def fetch(*args):
        response = httpx.Response(403, request=httpx.Request("POST", "https://example.com/?secret=SECRET"))
        raise httpx.HTTPStatusError("SECRET", request=response.request, response=response)

    monkeypatch.setattr("src.workers.tasks.fetch_search_page", fetch)
    asyncio.run(worker(store).run_once("owner"))
    assert store.failed == "Crawl failed: HTTPStatusError HTTP 403"
    assert store.job.result["last_error"]["http_status"] == 403
    assert "SECRET" not in str(store.job.result)


def test_database_permission_failure_stops_before_remaining_documents(monkeypatch):
    from postgrest.exceptions import APIError

    from src.integrations.database.repositories.rpc import DatabaseRepositoryError

    setup_sitemap(monkeypatch)
    store = FakeJobStore()
    calls = []

    async def ingest(document):
        calls.append(document.url)
        try:
            raise APIError({"code": "42501", "message": "SECRET", "details": None, "hint": None})
        except APIError as cause:
            raise DatabaseRepositoryError("lookup failed") from cause

    asyncio.run(worker(store, ingest).run_once("owner"))
    assert len(calls) == 1
    assert store.completed is None
    assert "42501" in store.failed
    assert store.job.result["summary"]["pending"] == 1
    assert store.job.result["last_error"]["database_code"] == "42501"
    assert "SECRET" not in str(store.checkpoints)


def test_document_completion_is_independent_of_global_index_status(monkeypatch):
    setup_sitemap(monkeypatch)
    store = FakeJobStore()

    async def ingest(document):
        return {
            "markdown_indexing": {
                "chunk_count": 3,
                "embedding_count": 3,
                "sparse_chunk_count": 3,
                "dense_index_status": "STALE",
                "sparse_index_status": "STALE",
            }
        }

    async def statuses():
        return {"dense": "STALE", "sparse": "STALE", "checked_at": "2026-11-22T00:00:00Z", "scope": "global"}

    store.get_index_status = statuses
    asyncio.run(worker(store, ingest).run_once("owner"))
    assert store.completed["summary"]["document_indexing_complete"] == 2
    assert store.completed["index_status"]["dense"] == "STALE"
    assert "retrieval_ready" not in str(store.completed)


def test_legacy_checkpoint_without_sparse_evidence_is_unknown():
    from src.application.dto.crawl_job import normalize_indexing_report

    result = {
        "summary": {"succeeded": 1, "retrieval_ready": 1},
        "ingestion": {
            "documents": {
                "a": {"status": "SUCCEEDED", "chunk_count": 2, "embedding_count": 2, "retrieval_ready": True},
                "b": {"chunk_count": 2, "embedding_count": 1, "sparse_chunk_count": 2},
                "c": {"chunk_count": 0, "embedding_count": 0, "sparse_chunk_count": 0},
            }
        },
    }
    report = normalize_indexing_report(result)
    assert report["summary"]["document_indexing_unknown"] == 1
    assert report["summary"]["document_indexing_complete"] == 0
    assert report["ingestion"]["documents"]["a"]["document_indexing_complete"] is None
    assert report["ingestion"]["documents"]["b"]["document_indexing_complete"] is False
    assert report["ingestion"]["documents"]["c"]["document_indexing_complete"] is False
    assert "retrieval_ready" not in str(report)


def test_stored_failure_then_retry_clears_diagnostics(monkeypatch):
    from src.applications.tillegal.ingestion.crawler.vbpl_document import diagnostic_stage

    setup_sitemap(monkeypatch)
    store = FakeJobStore()
    broken = True
    calls = []

    async def ingest(document):
        calls.append(document.url)
        if document.url.endswith("a") and broken:
            with diagnostic_stage("dense_index") as progress:
                progress["source_document_id"] = str(uuid4())
                raise ValueError("Authorization: SECRET cookie=SECRET https://host/?signed=SECRET full text")
        return {"source_document_id": str(uuid4())}

    asyncio.run(worker(store, ingest).run_once("owner"))
    failed = next(item for item in store.completed["ingestion"]["documents"].values() if item["status"] == "FAILED")
    assert failed["stored"] is True and failed["source_document_id"]
    assert failed["error_details"]["stage"] == "dense_index"
    assert failed["error_details"]["reason"] == "dense_index_failed"
    assert "SECRET" not in str(store.completed)
    assert store.completed["summary"]["stored"] == 2
    assert store.completed["summary"]["failed"] == 1
    for item in store.job.result["ingestion"]["documents"].values():
        if item["status"] == "FAILED":
            item["status"] = "PENDING"
            item["unrelated"] = "keep"
    broken = False
    asyncio.run(worker(store, ingest).run_once("owner"))
    retried = next(item for item in store.completed["ingestion"]["documents"].values() if "unrelated" in item)
    assert retried["status"] == "SUCCEEDED"
    assert retried["error"] is None and retried["error_details"] is None
    assert retried["unrelated"] == "keep"
    assert len(calls) == 3


@pytest.mark.parametrize(
    "stage",
    [
        "fetch_page",
        "metadata",
        "file_list",
        "attachment",
        "convert_html",
        "convert_word",
        "save_source",
        "parse_chunk",
        "dense_index",
        "sparse_index",
    ],
)
def test_controlled_stage_diagnostics_preserve_exception(stage):
    from src.applications.tillegal.ingestion.crawler.vbpl_document import diagnostic_stage
    from src.workers.tasks import _error_details

    original = ValueError("Authorization cookie signed URL response body SECRET")
    with pytest.raises(ValueError) as caught:
        with diagnostic_stage(stage):
            raise original
    assert caught.value is original
    details = _error_details(original)
    assert details["stage"] == stage and details["reason"] == stage + "_failed"
    assert "SECRET" not in str(details)


def test_storage_and_postgres_diagnostics_are_sanitized():
    import psycopg
    from storage3.exceptions import StorageApiError

    from src.workers.tasks import _error_details

    assert _error_details(StorageApiError("SECRET", "forbidden", 403))["http_status"] == 403
    details = _error_details(psycopg.errors.InsufficientPrivilege("SECRET"))
    assert details["database_code"] == "42501"
    assert "SECRET" not in str(details)
