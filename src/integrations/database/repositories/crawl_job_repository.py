"""PostgreSQL persistence for durable crawl jobs."""

from datetime import date
from typing import Any, cast
from uuid import UUID

import psycopg
from psycopg.types.json import Jsonb

from src.application.dto.crawl_job import CrawlJob, CrawlJobStatus
from src.core.identifiers import new_id
from src.integrations.database.repositories.rpc import DatabaseRepositoryError
from src.integrations.database.transaction import PostgresTransactionManager

ACTIVE_STATUSES = ("PENDING", "RUNNING")


class CrawlJobRepository:
    """Create, lease, and complete rows in public.crawl_jobs."""

    def __init__(self, transactions: PostgresTransactionManager) -> None:
        self._transactions = transactions

    async def create(self, source_id: str, crawl_date: date) -> CrawlJob:
        """Create a job unless one for the same source/date is already active."""
        job_id = new_id()

        def persist(connection: psycopg.Connection[dict[str, Any]]) -> CrawlJob:
            connection.execute(
                "SELECT pg_advisory_xact_lock(hashtext(%s), hashtext(%s))",
                (source_id, crawl_date.isoformat()),
            )
            existing = connection.execute(
                """
                SELECT * FROM public.crawl_jobs
                WHERE source_id = %s AND crawl_date = %s AND status = ANY(%s)
                ORDER BY created_at DESC
                LIMIT 1
                """,
                (source_id, crawl_date, list(ACTIVE_STATUSES)),
            ).fetchone()
            if existing is not None:
                return _to_crawl_job(existing)

            row = connection.execute(
                """
                INSERT INTO public.crawl_jobs (id, source_id, crawl_date)
                VALUES (%s, %s, %s)
                RETURNING *
                """,
                (job_id, source_id, crawl_date),
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

    async def claim(self, owner: str, lease_seconds: int) -> CrawlJob | None:
        """Claim the oldest pending or expired job, respecting its retry limit."""

        def claim_one(connection: psycopg.Connection[dict[str, Any]]) -> CrawlJob | None:
            row = connection.execute(
                """
                WITH candidate AS (
                    SELECT id
                    FROM public.crawl_jobs
                    WHERE attempts < max_attempts
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
                WHERE status = 'RUNNING'
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
                WHERE id = %s AND status = 'RUNNING' AND owner = %s
                """,
                (lease_seconds, job_id, owner),
            )
            return cursor.rowcount == 1

        return await self._transactions.run(renew_lease)

    async def succeed(self, job_id: UUID, owner: str, result: dict[str, object]) -> None:
        """Persist the result and mark the owned job successful."""
        await self._finish(job_id, owner, "SUCCEEDED", result, None)

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
                    result = COALESCE(%s, result),
                    error_message = %s,
                    owner = NULL,
                    lease_until = NULL,
                    completed_at = CASE
                        WHEN %s = 'SUCCEEDED' OR attempts >= max_attempts THEN now()
                        ELSE NULL
                    END,
                    updated_at = now()
                WHERE id = %s AND status = 'RUNNING' AND owner = %s
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
        crawl_date=cast(date, row["crawl_date"]),
        status=cast(CrawlJobStatus, row["status"]),
        result=cast(dict[str, object], row["result"]),
        error_message=cast(str | None, row["error_message"]),
        attempts=int(row["attempts"]),
        max_attempts=int(row["max_attempts"]),
        created_at=row["created_at"],
        started_at=row["started_at"],
        completed_at=row["completed_at"],
        updated_at=row["updated_at"],
    )
