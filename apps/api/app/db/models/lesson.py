"""Lessons with source provenance, and AI generation accounting.

Lesson content is JSONB validated against a Pydantic schema at the API layer;
provenance is first-class: lesson_sources records which sources grounded a
lesson, and paragraphs may carry validated source_ids inside content JSON.
"""
import uuid
from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, Float, ForeignKey, Index, Integer, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class Lesson(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "lessons"

    concept_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("concepts.id", ondelete="CASCADE"), nullable=False
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("profiles.id", ondelete="CASCADE"), nullable=False
    )
    title: Mapped[str] = mapped_column(Text, nullable=False)
    content: Mapped[dict] = mapped_column(JSONB, nullable=False)  # schema-validated structure
    status: Mapped[str] = mapped_column(
        Text, nullable=False, default="READY"
    )  # READY | STALE | FAILED
    grounding: Mapped[str] = mapped_column(Text, nullable=False, default="GROUNDED")
    # GROUNDED | GENERATED | MIXED
    generated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    generation_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("ai_generations.id", ondelete="SET NULL")
    )

    __table_args__ = (
        Index("ix_lessons_concept_user", "concept_id", "user_id", "created_at"),
    )


class LessonSource(Base):
    __tablename__ = "lesson_sources"

    lesson_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("lessons.id", ondelete="CASCADE"), primary_key=True
    )
    source_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("sources.id", ondelete="CASCADE"), primary_key=True
    )
    relevance: Mapped[float] = mapped_column(Float, nullable=False, default=1.0)


class PromptVersion(Base, UUIDPrimaryKeyMixin):
    """Prompts are production code: versioned and traceable."""

    __tablename__ = "prompt_versions"

    key: Mapped[str] = mapped_column(Text, nullable=False)  # e.g. 'lesson_generation'
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    template: Mapped[str] = mapped_column(Text, nullable=False)
    provider: Mapped[str | None]
    model: Mapped[str | None]
    parameters: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    schema_version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)

    __table_args__ = (
        Index("ix_prompt_versions_key_version", "key", "version", unique=True),
    )


class AIGeneration(Base, UUIDPrimaryKeyMixin):
    """One row per AI call. Cost/latency observability lives here."""

    __tablename__ = "ai_generations"

    user_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    feature: Mapped[str] = mapped_column(Text, nullable=False)  # pathway_gen, lesson_gen, tutor...
    prompt_key: Mapped[str | None]
    prompt_version: Mapped[int | None]
    provider: Mapped[str] = mapped_column(Text, nullable=False)
    model: Mapped[str] = mapped_column(Text, nullable=False)
    input_tokens: Mapped[int | None] = mapped_column(Integer)
    output_tokens: Mapped[int | None] = mapped_column(Integer)
    cost_estimate_usd: Mapped[float | None]
    latency_ms: Mapped[int | None] = mapped_column(Integer)
    success: Mapped[bool] = mapped_column(Integer, nullable=False, default=1)  # boolean-ish for checks
    error: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    __table_args__ = (
        CheckConstraint("success IN (0, 1)", name="success_bool"),
        Index("ix_ai_generations_feature_time", "feature", "created_at"),
    )
