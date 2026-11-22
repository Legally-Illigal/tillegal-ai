"""PostgreSQL persistence for durable crawl jobs."""

from datetime import date
from typing import Any, cast
from uuid import UUID

import psycopg
from psycopg.types.json import Jsonb

from src.application.dto.crawl_job import CrawlJob, CrawlJobStatus, CrawlMode, validate_crawl_dates
from src.core.identifiers import new_id
from src.integrations.database.repositories.rpc import DatabaseRepositoryError
from src.integrations.database.transaction import PostgresTransactionManager

ACTIVE_STATUSES = ("PENDING", "RUNNING")


class CrawlJobRepository:
    """Create, lease, and complete rows in public.crawl_jobs."""

    def __init__(self, transactions: PostgresTransactionManager) -> None:
        self._transactions = transactions

    async def create(
        self,
        source_id: str,
        crawl_date: date | None = None,
        *,
        crawl_mode: CrawlMode = "LASTMOD",
        issued_from: date | None = None,
        issued_to: date | None = None,
    ) -> CrawlJob:
        """Create a job unless one for the same source/date is already active."""
        job_id = new_id()
        validate_crawl_dates(crawl_mode, crawl_date, issued_from, issued_to)
        lock_key = str(crawl_date) if crawl_mode == "LASTMOD" else f"ISSUED_RANGE:{issued_from}:{issued_to}"

        def persist(connection: psycopg.Connection[dict[str, Any]]) -> CrawlJob:
            connection.execute(
                "SELECT pg_advisory_xact_lock(hashtext(%s), hashtext(%s))",
                (source_id, lock_key),
            )
            existing = connection.execute(
                """
                SELECT * FROM public.crawl_jobs
                WHERE source_id = %s AND crawl_mode = %s
                  AND crawl_date IS NOT DISTINCT FROM %s
                  AND issued_from IS NOT DISTINCT FROM %s AND issued_to IS NOT DISTINCT FROM %s
                  AND status = ANY(%s)
                ORDER BY created_at DESC
                LIMIT 1
                """,
                (source_id, crawl_mode, crawl_date, issued_from, issued_to, list(ACTIVE_STATUSES)),
            ).fetchone()
            if existing is not None:
                return _to_crawl_job(existing)

            row = connection.execute(
                """
                INSERT INTO public.crawl_jobs (id, source_id, crawl_date, crawl_mode, issued_from, issued_to)
                VALUES (%s, %s, %s, %s, %s, %s)
                RETURNING *
                """,
                (job_id, source_id, crawl_date, crawl_mode, issued_from, issued_to),
            ).fetchone()
            if row is None:
                raise DatabaseRepositoryError("Failed to create crawl job")
            return _to_crawl_job(row)

        return await self._transactions.run(persist)

    async def get(self, job_id: UUID) -> CrawlJob | None:
        """Load a job by ID."""

        def load(connection: psycopg.Connection[dict[str, Any]]) -> CrawlJob | None:
            row = connection.execute(
                "SELECT * FROM public.crawl_jobs WHERE id = %s",
                (job_id,),
            ).fetchone()
            return _to_crawl_job(row) if row is not None else None

        return await self._transactions.run(load)

    async def get_index_status(self) -> dict[str, object]:
        """Read global statuses only; never refresh or force READY here."""
        from src.application.services.vbpl_markdown_indexing_service import DENSE_INDEX_NAME, SPARSE_INDEX_NAME

        def read(connection):
            row = connection.execute(
                """SELECT
                (SELECT status FROM public.dense_indexes WHERE index_name=%s) AS dense,
                (SELECT status FROM public.sparse_indexes WHERE index_name=%s) AS sparse,
                statement_timestamp() AS checked_at""",
                (DENSE_INDEX_NAME, SPARSE_INDEX_NAME),
            ).fetchone()
            return {
                "dense": row["dense"],
                "sparse": row["sparse"],
                "checked_at": row["checked_at"].isoformat(),
                "scope": "global",
            }

        return await self._transactions.run(read)

    async def claim(self, owner: str, lease_seconds: int) -> CrawlJob | None:
        """Claim the oldest pending or expired job, respecting its retry limit."""

        def claim_one(connection: psycopg.Connection[dict[str, Any]]) -> CrawlJob | None:
            row = connection.execute(
                """
                WITH candidate AS (
                    SELECT id
                    FROM public.crawl_jobs
                    WHERE source_id = 'vbpl' AND attempts < max_attempts
                      AND (
                          status = 'PENDING'
                          OR (status = 'RUNNING' AND lease_until < now())
                      )
                    ORDER BY created_at
                      LIMIT 1
                      FOR UPDATE SKIP LOCKED
                )
                UPDATE public.crawl_jobs AS job
                SET status = 'RUNNING',
                    owner = %s,
                    lease_until = now() + (%s * interval '1 second'),
                    attempts = job.attempts + 1,
                    started_at = COALESCE(job.started_at, now()),
                    error_message = NULL,
                    updated_at = now()
                FROM candidate
                WHERE job.id = candidate.id
                RETURNING job.*
                """,
                (owner, lease_seconds),
            ).fetchone()
            connection.execute(
                """
                UPDATE public.crawl_jobs
                SET status = 'FAILED',
                    error_message = COALESCE(error_message, 'Maximum crawl attempts exceeded'),
                    owner = NULL,
                    lease_until = NULL,
                    completed_at = now(),
                    updated_at = now()
                WHERE source_id = 'vbpl' AND status = 'RUNNING'
                  AND lease_until < now()
                  AND attempts >= max_attempts
                """
            )
            return _to_crawl_job(row) if row is not None else None

        return await self._transactions.run(claim_one)

    async def renew(self, job_id: UUID, owner: str, lease_seconds: int) -> bool:
        """Extend a job lease if it is still owned by this worker."""

        def renew_lease(connection: psycopg.Connection[dict[str, Any]]) -> bool:
            cursor = connection.execute(
                """
                UPDATE public.crawl_jobs
                SET lease_until = now() + (%s * interval '1 second'),
                    updated_at = now()
                WHERE id = %s AND status = 'RUNNING' AND owner = %s AND lease_until > now()
                """,
                (lease_seconds, job_id, owner),
            )
            return cursor.rowcount == 1

        return await self._transactions.run(renew_lease)

    async def succeed(self, job_id: UUID, owner: str, result: dict[str, object]) -> None:
        """Persist the result and mark the owned job successful."""
        await self._finish(job_id, owner, "SUCCEEDED", result, None)

    async def checkpoint(self, job_id: UUID, owner: str, result: dict[str, object]) -> bool:
        def save(connection):
            return (
                connection.execute(
                    """UPDATE public.crawl_jobs SET result = result || %s, updated_at = now()
                WHERE id = %s AND owner = %s AND status = 'RUNNING' AND lease_until > now()""",
                    (Jsonb(result), job_id, owner),
                ).rowcount
                == 1
            )

        return await self._transactions.run(save)

    async def retry_failed(self, job_id: UUID) -> CrawlJob | None:
        """Requeue only failed documents, preserving successful checkpoints atomically."""

        def retry(connection):
            # Same lock order as create, then row lock; competing active jobs stay unique.
            row = connection.execute("SELECT * FROM public.crawl_jobs WHERE id = %s", (job_id,)).fetchone()
            if row is None or row["source_id"] != "vbpl":
                return None
            key = (
                str(row["crawl_date"])
                if row["crawl_mode"] == "LASTMOD"
                else f"ISSUED_RANGE:{row['issued_from']}:{row['issued_to']}"
            )
            connection.execute("SELECT pg_advisory_xact_lock(hashtext(%s), hashtext(%s))", (row["source_id"], key))
            row = connection.execute(
                "SELECT * FROM public.crawl_jobs WHERE id = %s FOR UPDATE",
                (job_id,),
            ).fetchone()
            if row["status"] not in ("SUCCEEDED", "FAILED"):
                raise ValueError("Retry requires a completed job")
            result = dict(row["result"])
            ingestion = dict(result.get("ingestion", {}))
            documents = {key: dict(value) for key, value in ingestion.get("documents", {}).items()}
            failed = [item for item in documents.values() if item.get("status") == "FAILED"]
            if not failed:
                raise ValueError("Job has no failed documents")
            for item in failed:
                item.update(status="PENDING")
            ingestion["documents"] = documents
            result.update(phase="ingestion", ingestion=ingestion, summary={"retry_pending": len(failed)})
            try:
                saved = connection.execute(
                    """UPDATE public.crawl_jobs SET status='PENDING', result=%s, attempts=0,
                    owner=NULL, lease_until=NULL, completed_at=NULL, error_message=NULL, updated_at=now()
                    WHERE id=%s RETURNING *""",
                    (Jsonb(result), job_id),
                ).fetchone()
            except psycopg.errors.UniqueViolation as error:
                raise ValueError("Another job for these dates is active") from error
            return _to_crawl_job(saved)

        return await self._transactions.run(retry)

    async def fail(self, job_id: UUID, owner: str, error_message: str) -> None:
        """Record a failure and retry until the job's attempt limit is reached."""
        await self._finish(job_id, owner, "FAILED", None, error_message[:2000])

    async def _finish(
        self,
        job_id: UUID,
        owner: str,
        status: str,
        result: dict[str, object] | None,
        error_message: str | None,
    ) -> None:
        def finish(connection: psycopg.Connection[dict[str, Any]]) -> None:
            row = connection.execute(
                """
                UPDATE public.crawl_jobs
                SET status = CASE
                        WHEN %s = 'FAILED' AND attempts < max_attempts THEN 'PENDING'
                        ELSE %s
                    END,
                    result = result || COALESCE(%s, '{}'::jsonb),
                    error_message = %s,
                    owner = NULL,
                    lease_until = NULL,
                    completed_at = CASE
                        WHEN %s = 'SUCCEEDED' OR attempts >= max_attempts THEN now()
                        ELSE NULL
                    END,
                    updated_at = now()
                WHERE id = %s AND status = 'RUNNING' AND owner = %s AND lease_until > now()
                RETURNING id
                """,
                (
                    status,
                    status,
                    Jsonb(result) if result is not None else None,
                    error_message,
                    status,
                    job_id,
                    owner,
                ),
            ).fetchone()
            if row is None:
                raise DatabaseRepositoryError(f"Crawl job lease is no longer owned: {job_id}")

        await self._transactions.run(finish)


def _to_crawl_job(row: dict[str, Any]) -> CrawlJob:
    """Convert a PostgreSQL row into the application job value."""
    return CrawlJob(
        id=cast(UUID, row["id"]),
        source_id=str(row["source_id"]),
        crawl_date=cast(date | None, row["crawl_date"]),
        status=cast(CrawlJobStatus, row["status"]),
        result=cast(dict[str, object], row["result"]),
        error_message=cast(str | None, row["error_message"]),
        attempts=int(row["attempts"]),
        max_attempts=int(row["max_attempts"]),
        created_at=row["created_at"],
        started_at=row["started_at"],
        completed_at=row["completed_at"],
        updated_at=row["updated_at"],
        crawl_mode=cast(CrawlMode, row.get("crawl_mode", "LASTMOD")),
        issued_from=row.get("issued_from"),
        issued_to=row.get("issued_to"),
    )
