"""Enqueue + claim helpers for the Postgres-backed jobs table."""
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Job
from app.db.models.job import JobStatus, JobType


async def enqueue_job(
    session: AsyncSession,
    job_type: str,
    payload: dict[str, Any],
    *,
    dedupe_key: str | None = None,
    run_after: datetime | None = None,
) -> Job:
    """Insert a PENDING job. A dedupe key with existing non-terminal work is idempotent."""
    if dedupe_key:
        existing = await session.execute(select(Job).where(Job.dedupe_key == dedupe_key))
        found = existing.scalar_one_or_none()
        if found is not None and found.status not in (JobStatus.FAILED, JobStatus.CANCELLED):
            return found

    job = Job(
        type=JobType(job_type),
        status=JobStatus.PENDING,
        payload=payload,
        dedupe_key=dedupe_key,
        run_after=run_after or datetime.now(UTC),
    )
    session.add(job)
    await session.flush()
    return job


async def claim_next_job(session: AsyncSession) -> Job | None:
    """Atomically claim the oldest runnable job (SKIP LOCKED → safe under concurrency)."""
    result = await session.execute(
        select(Job)
        .where(
            Job.status == JobStatus.PENDING,
            text("(run_after IS NULL OR run_after <= :now)"),
        )
        .order_by(Job.created_at)
        .limit(1)
        .with_for_update(skip_locked=True),
        {"now": datetime.now(UTC)},
    )
    job = result.scalar_one_or_none()
    if job is None:
        return None
    job.status = JobStatus.RUNNING
    job.started_at = datetime.now(UTC)
    job.attempts += 1
    await session.flush()
    return job
