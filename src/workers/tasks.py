"""Background tasks for durable legal-source ingestion."""

import asyncio
import logging
from uuid import UUID

from src.application.interfaces.crawl_job_store import CrawlJobStore
from src.applications.tillegal.ingestion.crawler.vbpl_sitemap import scan_vbpl_sitemaps

logger = logging.getLogger("tillegal.ingestion")


class VbplCrawlWorker:
    """Claim durable VBPL jobs and persist sitemap discovery results."""

    def __init__(
        self,
        jobs: CrawlJobStore,
        *,
        poll_interval_seconds: float = 5,
        lease_seconds: int = 180,
        heartbeat_interval_seconds: float = 45,
    ) -> None:
        if poll_interval_seconds <= 0 or lease_seconds <= 0 or heartbeat_interval_seconds <= 0:
            raise ValueError("Worker polling and lease intervals must be positive")
        if heartbeat_interval_seconds >= lease_seconds:
            raise ValueError("Heartbeat interval must be shorter than the job lease")
        self._jobs = jobs
        self._poll_interval_seconds = poll_interval_seconds
        self._lease_seconds = lease_seconds
        self._heartbeat_interval_seconds = heartbeat_interval_seconds

    async def run_once(self, owner: str) -> bool:
        """Claim and execute at most one job; return whether a job was claimed."""
        job = await self._jobs.claim(owner, self._lease_seconds)
        if job is None:
            return False

        heartbeat = asyncio.create_task(self._keep_lease(job.id, owner))
        try:
            result = await asyncio.to_thread(scan_vbpl_sitemaps, job.crawl_date)
            await self._jobs.succeed(
                job.id,
                owner,
                {
                    "target_date": result.target_date.isoformat(),
                    "sitemap_count": result.sitemap_count,
                    "document_url_count": result.document_url_count,
                    "selected_count": len(result.selected),
                    "shards": [
                        {
                            "url": shard.url,
                            "document_url_count": shard.document_url_count,
                            "selected_count": shard.selected_count,
                        }
                        for shard in result.shards
                    ],
                    "selected": [
                        {
                            "url": document.url,
                            "sitemap_lastmod": document.lastmod.isoformat(),
                            "sitemap_url": document.sitemap_url,
                        }
                        for document in result.selected
                    ],
                },
            )
        except Exception as error:
            logger.exception(
                "VBPL crawl attempt failed",
                extra={
                    "crawl_job_id": str(job.id),
                    "crawl_date": job.crawl_date.isoformat(),
                    "error_category": type(error).__name__,
                    "error_message": str(error),
                },
            )
            await self._jobs.fail(job.id, owner, f"{type(error).__name__}: {error}")
        finally:
            heartbeat.cancel()
            try:
                await heartbeat
            except asyncio.CancelledError:
                pass

        return True

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
                raise RuntimeError(f"Lost lease for crawl job {job_id}")
