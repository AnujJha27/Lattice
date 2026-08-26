"""Append-only review attempts used for mastery history and discovery."""
import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, Integer, Numeric, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, UUIDPrimaryKeyMixin


class Review(Base, UUIDPrimaryKeyMixin):
    __tablename__ = "reviews"

    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("profiles.id", ondelete="CASCADE"), nullable=False)
    concept_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("concepts.id", ondelete="CASCADE"), nullable=False)
    quiz_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("quizzes.id", ondelete="SET NULL"))
    correct: Mapped[bool] = mapped_column(Boolean, nullable=False)
    confidence: Mapped[int] = mapped_column(Integer, nullable=False)
    previous_mastery: Mapped[float] = mapped_column(Numeric(5, 2), nullable=False)
    mastery_after: Mapped[float] = mapped_column(Numeric(5, 2), nullable=False)
    response_ms: Mapped[int | None] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    __table_args__ = (Index("ix_reviews_user_created", "user_id", "created_at"),)
