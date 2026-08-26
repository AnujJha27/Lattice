"""Background worker loop over the jobs table.

Runs as an asyncio task inside the FastAPI lifespan — appropriate for a
single-user deployment; extract to a dedicated process when scaling.
"""
import asyncio
import logging
import uuid
from datetime import UTC, datetime, timedelta

from app.core.logging import setup_logging
from app.db import session as db_session
from app.db.models import Job
from app.db.models.job import JobStatus
from app.jobs.handlers import (
    handle_lesson_generation,
    handle_pathway_generation,
    handle_source_ingest,
)
from app.jobs.queue import claim_next_job

logger = logging.getLogger(__name__)

POLL_INTERVAL_SECONDS = 2.0

HANDLERS = {
    "SOURCE_INGEST": handle_source_ingest,
    "PATHWAY_GENERATION": handle_pathway_generation,
    "LESSON_GENERATION": handle_lesson_generation,
}


async def run_job(job) -> None:
    handler = HANDLERS.get(job.type.value)
    if handler is None:
        logger.error("no handler for job type %s", job.type.value)
        job.status = JobStatus.FAILED
        job.last_error = f"no handler registered for {job.type.value}"
        return

    async with db_session.session_factory() as session:
        attached = await session.merge(job)
        # Snapshot before the try: after a rollback these expire and touching
        # them would lazy-load outside the greenlet (MissingGreenlet).
        attempts = attached.attempts
        max_attempts = attached.max_attempts
        try:
            result = await handler(session, attached.payload)
            attached.result = result
            attached.status = JobStatus.SUCCEEDED
            attached.progress = 1.0
            attached.finished_at = datetime.now(UTC)
            await session.commit()
        except Exception as exc:  # noqa: BLE001 — job boundary must contain failures
            error_message = f"{type(exc).__name__}: {exc}"
            await session.rollback()
            # Rate limits need far longer waits than transient errors: free
            # tiers are typically per-minute windows.
            is_rate_limited = "429" in error_message or "Too Many Requests" in error_message
            if attempts >= max_attempts:
                attached.status = JobStatus.FAILED
                attached.last_error = error_message
                attached.finished_at = datetime.now(UTC)
            else:
                backoff = 90 if is_rate_limited else min(2 ** attempts * 5, 300)
                attached.status = JobStatus.PENDING
                attached.attempts = attempts  # keep the claim count
                attached.last_error = error_message
                attached.run_after = datetime.now(UTC) + timedelta(seconds=backoff)
            await session.commit()
            logger.warning(
                "job %s failed (attempt %s/%s): %s",
                attached.id, attempts, max_attempts, error_message,
            )


async def recover_stuck_jobs() -> int:
    """Reset jobs left RUNNING by a previous process (crash/reload) to PENDING,
    and resurrect FAILED pathway jobs whose pathway never completed (e.g. the
    model 404'd and retries were exhausted)."""
    from sqlalchemy import select, update

    async with db_session.session_factory() as session:
        result = await session.execute(
            update(Job)
            .where(Job.status == JobStatus.RUNNING)
            .values(status=JobStatus.PENDING, last_error="recovered after restart")
        )
        recovered = result.rowcount or 0

        # FAILED pathway jobs whose pathway is still GENERATING get a fresh run.
        from app.db.models import Pathway
        from app.db.models.learning import PathwayStatus

        failed = await session.execute(
            select(Job).where(
                Job.type == "PATHWAY_GENERATION", Job.status == JobStatus.FAILED
            )
        )
        for job in failed.scalars().all():
            pathway_id = job.payload.get("pathway_id")
            if not pathway_id:
                continue
            pathway = await session.get(Pathway, uuid.UUID(pathway_id))
            if pathway is None or pathway.status != PathwayStatus.GENERATING:
                continue
            job.status = JobStatus.PENDING
            job.attempts = 0
            job.last_error = None
            job.run_after = None
            recovered += 1

        await session.commit()
        if recovered:
            logger.info("recovered %d stuck/failed job(s)", recovered)
        return recovered


async def worker_loop() -> None:
    """Claim and execute jobs until cancelled."""
    db_session.init_engine()  # safety: works even if started outside the app lifespan
    await recover_stuck_jobs()
    while True:
        try:
            async with db_session.session_factory() as session:
                job = await claim_next_job(session)
                await session.commit()
            if job is None:
                await asyncio.sleep(POLL_INTERVAL_SECONDS)
                continue
            logger.info("running job %s (%s)", job.id, job.type.value)
            await run_job(job)
        except asyncio.CancelledError:
            raise
        except Exception:  # noqa: BLE001 — keep the loop alive no matter what
            logger.exception("worker loop iteration failed")
            await asyncio.sleep(POLL_INTERVAL_SECONDS)


def start_worker() -> asyncio.Task:
    setup_logging()
    return asyncio.create_task(worker_loop(), name="lattice-job-worker")
