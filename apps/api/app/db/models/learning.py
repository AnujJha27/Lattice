"""Per-user learning state: mastery, goals, pathways."""
import enum
import uuid
from datetime import datetime

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    Text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class MasteryState(enum.StrEnum):
    UNSEEN = "UNSEEN"
    AVAILABLE = "AVAILABLE"  # prerequisites satisfied
    LEARNING = "LEARNING"
    FAMILIAR = "FAMILIAR"
    MASTERED = "MASTERED"
    REVIEW_DUE = "REVIEW_DUE"


class GoalStatus(enum.StrEnum):
    ACTIVE = "ACTIVE"
    PAUSED = "PAUSED"
    COMPLETE = "COMPLETE"
    ARCHIVED = "ARCHIVED"


class PathwayStatus(enum.StrEnum):
    GENERATING = "GENERATING"
    READY = "READY"
    FAILED = "FAILED"
    ARCHIVED = "ARCHIVED"


class UserConcept(Base):
    """Learning state for (user, concept). Never duplicate concept content here."""

    __tablename__ = "user_concepts"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("profiles.id", ondelete="CASCADE"), primary_key=True
    )
    concept_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("concepts.id", ondelete="CASCADE"), primary_key=True
    )
    mastery_score: Mapped[float] = mapped_column(Numeric(5, 2), nullable=False, default=0)
    state: Mapped[MasteryState] = mapped_column(
        Enum(MasteryState, name="mastery_state"), nullable=False, default=MasteryState.UNSEEN
    )
    interest_score: Mapped[float] = mapped_column(Numeric(5, 2), nullable=False, default=0)
    confidence: Mapped[float] = mapped_column(Numeric(5, 2), nullable=False, default=0)
    attempt_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    successful_reviews: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    review_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    last_seen_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_tested_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    next_review_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    __table_args__ = (
        CheckConstraint("mastery_score BETWEEN 0 AND 100", name="mastery_range"),
        CheckConstraint("interest_score BETWEEN 0 AND 100", name="interest_range"),
        Index("ix_user_concepts_next_review", "user_id", "next_review_at"),
    )


class Goal(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "goals"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("profiles.id", ondelete="CASCADE"), nullable=False
    )
    title: Mapped[str] = mapped_column(Text, nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    target_depth: Mapped[str | None] = mapped_column(Text)  # beginner|intermediate|advanced
    motivation: Mapped[str | None] = mapped_column(Text)
    time_commitment: Mapped[str | None] = mapped_column(Text)  # e.g. '3h/week'
    status: Mapped[GoalStatus] = mapped_column(
        Enum(GoalStatus, name="goal_status"), nullable=False, default=GoalStatus.ACTIVE
    )

    concepts: Mapped[list["GoalConcept"]] = relationship(back_populates="goal", cascade="all, delete-orphan")

    __table_args__ = (Index("ix_goals_user_status", "user_id", "status"),)


class GoalConcept(Base):
    __tablename__ = "goal_concepts"

    goal_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("goals.id", ondelete="CASCADE"), primary_key=True
    )
    concept_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("concepts.id", ondelete="CASCADE"), primary_key=True
    )
    importance: Mapped[float] = mapped_column(Numeric(4, 3), nullable=False, default=1.0)

    goal: Mapped[Goal] = relationship(back_populates="concepts")


class Pathway(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "pathways"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("profiles.id", ondelete="CASCADE"), nullable=False
    )
    goal_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("goals.id", ondelete="SET NULL")
    )
    concept_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("concepts.id", ondelete="SET NULL")
    )
    title: Mapped[str] = mapped_column(Text, nullable=False)
    topic: Mapped[str | None] = mapped_column(Text)
    description: Mapped[str | None] = mapped_column(Text)
    status: Mapped[PathwayStatus] = mapped_column(
        Enum(PathwayStatus, name="pathway_status"), nullable=False, default=PathwayStatus.GENERATING
    )
    generation_metadata: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)

    sections: Mapped[list["PathwaySection"]] = relationship(
        back_populates="pathway", cascade="all, delete-orphan", order_by="PathwaySection.position"
    )

    __table_args__ = (Index("ix_pathways_user", "user_id", "status"),)


class PathwaySection(Base, UUIDPrimaryKeyMixin):
    __tablename__ = "pathway_sections"

    pathway_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("pathways.id", ondelete="CASCADE"), nullable=False
    )
    position: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    title: Mapped[str] = mapped_column(Text, nullable=False)
    summary: Mapped[str | None] = mapped_column(Text)

    pathway: Mapped[Pathway] = relationship(back_populates="sections")
    concepts: Mapped[list["PathwayConcept"]] = relationship(
        back_populates="section", cascade="all, delete-orphan", order_by="PathwayConcept.position"
    )


class PathwayConcept(Base):
    __tablename__ = "pathway_concepts"

    pathway_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("pathways.id", ondelete="CASCADE"), primary_key=True
    )
    concept_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("concepts.id", ondelete="CASCADE"), primary_key=True
    )
    section_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("pathway_sections.id", ondelete="SET NULL")
    )
    position: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    section: Mapped[PathwaySection | None] = relationship(back_populates="concepts")
