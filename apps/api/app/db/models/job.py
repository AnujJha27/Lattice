"""Durable background jobs backed by PostgreSQL (no Redis/queue service needed yet).

Workers poll this table. Supports retries with backoff, progress, and failure
records. Idempotency: callers pass a unique dedupe_key where applicable.
"""
import enum
from datetime import datetime

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    Enum,
    Index,
    Integer,
    Numeric,
    Text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class JobStatus(enum.StrEnum):
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    SUCCEEDED = "SUCCEEDED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


class JobType(enum.StrEnum):
    SOURCE_DISCOVERY = "SOURCE_DISCOVERY"
    SOURCE_INGEST = "SOURCE_INGEST"
    EMBEDDING = "EMBEDDING"
    PATHWAY_GENERATION = "PATHWAY_GENERATION"
    LESSON_GENERATION = "LESSON_GENERATION"
    PORTRAIT_REFRESH = "PORTRAIT_REFRESH"
    PORTRAIT_VISUAL_REFRESH = "PORTRAIT_VISUAL_REFRESH"
    GRAPH_METRICS = "GRAPH_METRICS"


class Job(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "jobs"

    type: Mapped[JobType] = mapped_column(Enum(JobType, name="job_type"), nullable=False)
    status: Mapped[JobStatus] = mapped_column(
        Enum(JobStatus, name="job_status"), nullable=False, default=JobStatus.PENDING
    )
    payload: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    result: Mapped[dict | None] = mapped_column(JSONB)
    progress: Mapped[float] = mapped_column(Numeric(3, 2), nullable=False, default=0)
    dedupe_key: Mapped[str | None] = mapped_column(Text)

    attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    max_attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=3)

    last_error: Mapped[str | None] = mapped_column(Text)
    run_after: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    __table_args__ = (
        CheckConstraint("progress BETWEEN 0 AND 1", name="progress_range"),
        CheckConstraint("attempts >= 0 AND max_attempts > 0", name="attempts_sane"),
        Index("ix_jobs_poll", "status", "run_after"),
        Index("ix_jobs_dedupe", "dedupe_key", unique=True, postgresql_where=Text("dedupe_key IS NOT NULL")),
    )
