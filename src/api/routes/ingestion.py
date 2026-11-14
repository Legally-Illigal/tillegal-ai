"""Durable legal-source ingestion routes."""

from uuid import UUID

from fastapi import APIRouter, HTTPException, Request, status

from src.api.schemas.crawl import CrawlJobResponse, VbplCrawlRequest
from src.application.services.vbpl_crawl_service import VbplCrawlService

router = APIRouter(prefix="/ingestion/vbpl", tags=["ingestion"])


def _service(request: Request) -> VbplCrawlService:
    jobs = getattr(request.app.state, "crawl_job_store", None)
    if jobs is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="VBPL ingestion requires DATABASE_URL",
        )
    return VbplCrawlService(jobs)


@router.post(
    "/crawl",
    response_model=CrawlJobResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Request VBPL sitemap discovery for a date",
)
async def request_vbpl_crawl(
    request: Request,
    body: VbplCrawlRequest | None = None,
) -> CrawlJobResponse:
    """Queue a durable sitemap scan for the requested or current Vietnam date."""
    job = await _service(request).request_crawl(body.crawl_date if body is not None else None)
    return CrawlJobResponse.from_job(job)


@router.get(
    "/jobs/{job_id}",
    response_model=CrawlJobResponse,
    summary="Get VBPL crawl job status",
)
async def get_vbpl_crawl_job(job_id: UUID, request: Request) -> CrawlJobResponse:
    """Return the lifecycle and result of a previously requested crawl."""
    job = await _service(request).get_job(job_id)
    if job is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Crawl job not found")
    return CrawlJobResponse.from_job(job)
