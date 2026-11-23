"""Background tasks for durable legal-source ingestion."""

import asyncio
import logging
import re
from collections.abc import Awaitable, Callable
from copy import deepcopy
from datetime import date
from uuid import UUID

import httpx
import psycopg
from postgrest.exceptions import APIError
from storage3.exceptions import StorageApiError

from src.application.dto.crawl_job import normalize_indexing_report
from src.application.interfaces.crawl_job_store import CrawlJobStore
from src.application.services.vbpl_document_ingestion_service import SearchDocumentUrl
from src.applications.tillegal.ingestion.crawler import vbpl_sitemap as sitemap
from src.applications.tillegal.ingestion.crawler.vbpl_document import DIAGNOSTIC_STAGES
from src.applications.tillegal.ingestion.crawler.vbpl_search import fetch_search_page
from src.applications.tillegal.ingestion.crawler.vbpl_sitemap import VbplDocumentUrl
from src.core.config import VbplCrawlSettings
from src.integrations.database.repositories.rpc import DatabaseRepositoryError

logger = logging.getLogger("tillegal.ingestion")


class CrawlLeaseLostError(RuntimeError):
    """Ownership was lost; stop without checkpointing document failure."""


def _error_details(error: Exception) -> dict[str, object]:
    """Extract allowlisted diagnostics; never persist exception messages or URLs."""
    stage = getattr(error, "ingestion_stage", None)
    stage = stage if stage in DIAGNOSTIC_STAGES else "ingestion"
    reason = getattr(error, "ingestion_reason", None)
    reason = reason if reason in {f"{item}_failed" for item in DIAGNOSTIC_STAGES} else f"{stage}_failed"
    details: dict[str, object] = {
        "type": type(error).__name__,
        "stage": stage,
        "reason": reason,
        "message": f"Operation failed at {stage}.",
    }
    current = error
    seen = set()
    while id(current) not in seen:
        seen.add(id(current))
        if isinstance(current, (APIError, psycopg.Error)):
            code = current.code if isinstance(current, APIError) else current.sqlstate
            if isinstance(code, str) and re.fullmatch(r"[A-Z0-9]{5,12}", code):
                details["database_code"] = code
            details["retryable"] = False
            break
        status = getattr(current, "status_code", None)
        if isinstance(current, StorageApiError):
            status = current.status
            if isinstance(status, str) and re.fullmatch(r"[1-5][0-9]{2}", status):
                status = int(status)
        if isinstance(current, httpx.HTTPStatusError):
            status = current.response.status_code
        if type(status) is int and 100 <= status <= 599:
            details["http_status"] = status
            details["retryable"] = status in (408, 429, 500, 502, 503, 504)
            break
        if isinstance(current, (httpx.TransportError, TimeoutError)):
            details["retryable"] = True
        cause = current.__cause__
        if cause is None:
            break
        current = cause
    return details


class VbplCrawlWorker:
    """Claim durable VBPL jobs, discover candidates, and ingest selected documents."""

    def __init__(
        self,
        jobs: CrawlJobStore,
        *,
        document_ingestor: Callable[[VbplDocumentUrl | SearchDocumentUrl], Awaitable[dict[str, object]]] | None = None,
        poll_interval_seconds: float | None = None,
        lease_seconds: int | None = None,
        heartbeat_interval_seconds: float | None = None,
        settings: VbplCrawlSettings | None = None,
    ) -> None:
        if poll_interval_seconds is None:
            poll_interval_seconds = settings.worker_poll_interval_seconds if settings else 5
        if lease_seconds is None:
            lease_seconds = settings.worker_lease_seconds if settings else 180
        if heartbeat_interval_seconds is None:
            heartbeat_interval_seconds = settings.worker_heartbeat_interval_seconds if settings else 45
        if poll_interval_seconds <= 0 or lease_seconds <= 0 or heartbeat_interval_seconds <= 0:
            raise ValueError("Worker polling and lease intervals must be positive")
        if heartbeat_interval_seconds >= lease_seconds:
            raise ValueError("Heartbeat interval must be shorter than the job lease")
        self._jobs = jobs
        self._document_ingestor = document_ingestor
        self._settings = settings
        self._poll_interval_seconds = poll_interval_seconds
        self._lease_seconds = lease_seconds
        self._heartbeat_interval_seconds = heartbeat_interval_seconds

    async def run_once(self, owner: str) -> bool:
        """Claim and execute at most one job; return whether a job was claimed."""
        job = await self._jobs.claim(owner, self._lease_seconds)
        if job is None:
            return False

        logger.info("Starting crawl job %s mode=%s", job.id, job.crawl_mode)
        heartbeat = asyncio.create_task(self._keep_lease(job.id, owner))
        work = asyncio.create_task(self._process(job, owner))
        try:
            done, _ = await asyncio.wait((heartbeat, work), return_when=asyncio.FIRST_COMPLETED)
            if heartbeat in done:
                await heartbeat
            await work
        except Exception as error:
            work.cancel()
            await asyncio.gather(work, return_exceptions=True)
            details = _error_details(error)
            logger.error("Crawl job %s stopped: %s", job.id, details)
            # Never mutate lifecycle after ownership has expired or changed.
            if await self._jobs.renew(job.id, owner, self._lease_seconds):
                latest = await self._jobs.get(job.id)
                result = deepcopy(latest.result if latest else job.result)
                result["last_error"] = {**details, "phase": result.get("phase", "discovery")}
                if await self._jobs.checkpoint(job.id, owner, result):
                    suffix = f" HTTP {details['http_status']}" if "http_status" in details else ""
                    if "database_code" in details:
                        suffix += f" database {details['database_code']}"
                    await self._jobs.fail(job.id, owner, f"Crawl failed: {type(error).__name__}{suffix}")
        finally:
            work.cancel()
            heartbeat.cancel()
            await asyncio.gather(work, heartbeat, return_exceptions=True)
        return True

    async def _process(self, job, owner):
        result = deepcopy(job.result)
        discovery = result.setdefault("discovery", {})
        ingestion = result.setdefault("ingestion", {})
        documents = ingestion.setdefault("documents", {})
        pause = self._settings.request_pause_seconds if self._settings else 0.25
        consecutive_system_errors = 0

        async def with_retry(operation, stage, document_item=None):
            for attempt in range(3):
                if not await self._jobs.renew(job.id, owner, self._lease_seconds):
                    raise CrawlLeaseLostError("Lost crawl lease")
                try:
                    return await operation()
                except Exception as error:
                    details = _error_details(error)
                    saved_id = getattr(error, "stored_source_document_id", None)
                    if document_item is not None and saved_id:
                        document_item.update(stored=True, source_document_id=str(saved_id))
                    if not details.get("retryable") or attempt == 2:
                        raise
                    delay = max(pause, 2 ** (attempt + 1))
                    header = (
                        error.response.headers.get("Retry-After")
                        if isinstance(error, httpx.HTTPStatusError)
                        else getattr(error, "retry_after", None)
                    )
                    if isinstance(header, str) and header.isdecimal():
                        delay = min(120, max(delay, int(header)))
                    result["last_error"] = {**details, "stage": stage, "retry_in_seconds": delay}
                    await checkpoint(stage)
                    logger.warning("Retry job=%s stage=%s delay=%s error=%s", job.id, stage, delay, details)
                    await asyncio.sleep(delay)

        async def checkpoint(phase):
            result["phase"] = phase
            values = list(documents.values())
            successes = sum(item.get("status") == "SUCCEEDED" for item in values)
            failures = sum(item.get("status") == "FAILED" for item in values)
            result["summary"] = {
                **result.get("summary", {}),
                "discovered": len(values),
                "succeeded": successes,
                "failed": failures,
                "pending": len(values) - successes - failures,
                "partial_failure": failures > 0,
                "stored": sum(item.get("stored") is True for item in values),
                "stored_unknown": sum(item.get("stored") is not True for item in values),
                "stored_evidence": "confirmed_only; historical missing/false does not prove source absence",
            }
            normalized = normalize_indexing_report(result)
            result.update(normalized)
            if not await self._jobs.checkpoint(job.id, owner, result):
                raise CrawlLeaseLostError("Lost crawl lease")
            logger.info("Checkpoint job %s phase=%s summary=%s", job.id, phase, result["summary"])

        async def ingest_pending():
            nonlocal consecutive_system_errors
            pending = [item for item in documents.values() if item.get("status") not in ("SUCCEEDED", "FAILED")]
            if pending and self._document_ingestor is None:
                raise RuntimeError("VBPL document ingestion requires configured Storage")
            for item in pending:
                if not await self._jobs.renew(job.id, owner, self._lease_seconds):
                    raise CrawlLeaseLostError("Lost crawl lease")
                logger.info("Processing job %s document %s", job.id, item["url"])
                item["attempts"] = item.get("attempts", 0) + 1
                try:
                    document = (
                        VbplDocumentUrl(item["url"], date.fromisoformat(item["lastmod"]), item["sitemap_url"])
                        if job.crawl_mode == "LASTMOD"
                        else SearchDocumentUrl(item["url"], str(job.id))
                    )
                    outcome = await with_retry(lambda: self._document_ingestor(document), "ingestion", item)
                    consecutive_system_errors = 0
                    indexing = _mapping(outcome.get("markdown_indexing"))
                    # Store only resume/observability metadata, never document text or vectors.
                    item.update(
                        status="SUCCEEDED",
                        stored=True,
                        error=None,
                        error_details=None,
                        source_document_id=str(outcome.get("source_document_id", "")),
                        markdown_skipped_reason=outcome.get("markdown_skipped_reason"),
                        chunk_count=indexing.get("chunk_count", 0),
                        embedding_count=indexing.get("embedding_count", 0),
                        sparse_chunk_count=indexing.get("sparse_chunk_count"),
                    )
                except CrawlLeaseLostError:
                    raise
                except Exception as error:
                    details = _error_details(error)
                    item.update(status="FAILED", error=type(error).__name__, error_details=details)
                    saved_id = getattr(error, "stored_source_document_id", None)
                    if saved_id:
                        item.update(stored=True, source_document_id=str(saved_id))
                    logger.warning("Document failed job=%s error=%s", job.id, details)
                    systemic = isinstance(error, DatabaseRepositoryError) or details.get("http_status") in (
                        401,
                        403,
                        429,
                        500,
                        502,
                        503,
                        504,
                    )
                    consecutive_system_errors = consecutive_system_errors + 1 if systemic else 0
                    if details.get("database_code") in ("42501", "42P01", "42883", "PGRST202", "PGRST205"):
                        result["last_error"] = {**details, "stage": "ingestion", "reason": "database_configuration"}
                        await checkpoint("ingestion")
                        raise
                    if consecutive_system_errors >= 3:
                        result["last_error"] = {**details, "stage": "ingestion", "reason": "repeated_system_failure"}
                        await checkpoint("ingestion")
                        raise
                await checkpoint("ingestion")
                await asyncio.sleep(pause)

        # Process a page saved before a crash before fetching another one.
        await ingest_pending()
        if job.crawl_mode == "LASTMOD":
            if job.crawl_date is None:
                raise ValueError("LASTMOD requires crawl_date")
            if not discovery.get("complete"):
                if "sitemaps" not in discovery:
                    xml = await asyncio.to_thread(sitemap._fetch_sitemap, sitemap.SITEMAP_INDEX_URL, self._settings)
                    discovery["sitemaps"] = list(
                        sitemap.parse_sitemap_index(
                            xml,
                            self._settings.max_sitemap_count if self._settings else None,
                        )
                    )
                    discovery["next_shard"] = 0
                    await checkpoint("discovery")
                urls = discovery["sitemaps"]
                for index in range(discovery["next_shard"], len(urls)):
                    await asyncio.sleep(pause)
                    logger.info("Reading job %s sitemap %s", job.id, urls[index])
                    xml = await asyncio.to_thread(sitemap._fetch_sitemap, urls[index], self._settings)
                    count, selected = sitemap.parse_document_sitemap(xml, urls[index], job.crawl_date)
                    for document in selected:
                        documents.setdefault(
                            document.url,
                            {
                                "url": document.url,
                                "status": "PENDING",
                                "lastmod": document.lastmod.isoformat(),
                                "sitemap_url": document.sitemap_url,
                            },
                        )
                    discovery.update(
                        next_shard=index + 1,
                        complete=index + 1 == len(urls),
                        document_url_count=discovery.get("document_url_count", 0) + count,
                    )
                    await checkpoint("discovery")
                    await ingest_pending()
        elif job.crawl_mode == "ISSUED_RANGE":
            if job.issued_from is None or job.issued_to is None:
                raise ValueError("ISSUED_RANGE requires dates")
            while not discovery.get("complete"):
                page_number = discovery.get("next_page", 1)
                await asyncio.sleep(pause)
                logger.info("Reading job %s search page %s", job.id, page_number)
                result["phase"] = "discovery"
                discovery["fetching_page"] = page_number
                await checkpoint("discovery")
                page = await with_retry(
                    lambda: asyncio.to_thread(
                        fetch_search_page,
                        job.issued_from,
                        job.issued_to,
                        page_number,
                        self._settings or VbplCrawlSettings(),
                    ),
                    "discovery",
                )
                if "total" in discovery and discovery["total"] != page.total:
                    raise ValueError("Search total changed during pagination; reconcile discovery")
                new_count = 0
                for item in page.items:
                    url = item["document_url"]
                    if url not in documents:
                        new_count += 1
                        documents[url] = {"url": url, "record_id": item["id"], "status": "PENDING"}
                if new_count != len(page.items):
                    raise ValueError("Search pages overlap; reconcile discovery")
                discovery.update(next_page=page_number + 1, total=page.total, complete=page_number * 10 >= page.total)
                await checkpoint("discovery")
                await ingest_pending()
        else:
            raise ValueError("Unknown crawl mode")
        if hasattr(self._jobs, "get_index_status"):
            result["index_status"] = await self._jobs.get_index_status()
        await checkpoint("complete")
        await self._jobs.succeed(job.id, owner, result)
        logger.info("Completed crawl job %s: %s", job.id, result["summary"])

    async def run_forever(self, owner: str) -> None:
        """Poll continuously; persisted jobs survive application restarts."""
        while True:
            try:
                claimed = await self.run_once(owner)
            except Exception:
                logger.exception("VBPL crawl worker iteration failed")
                claimed = False
            if not claimed:
                await asyncio.sleep(self._poll_interval_seconds)

    async def _keep_lease(self, job_id: UUID, owner: str) -> None:
        while True:
            await asyncio.sleep(self._heartbeat_interval_seconds)
            if not await self._jobs.renew(job_id, owner, self._lease_seconds):
                raise CrawlLeaseLostError("Lost crawl lease")


def _mapping(value: object) -> dict[str, object]:
    return value if isinstance(value, dict) else {}
