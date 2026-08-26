"""Versioned portrait snapshots and learner corrections."""
import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, Index, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column
import enum

from app.db.base import Base, UUIDPrimaryKeyMixin


class PortraitFeedbackKind(enum.StrEnum):
    BRIDGE = "BRIDGE"
    GAP = "GAP"
    EMERGING_INTEREST = "EMERGING_INTEREST"


class PortraitSnapshot(Base, UUIDPrimaryKeyMixin):
    __tablename__ = "portrait_snapshots"

    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("profiles.id", ondelete="CASCADE"), nullable=False)
    payload: Mapped[dict] = mapped_column(JSONB, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    __table_args__ = (Index("ix_portrait_snapshots_user_created", "user_id", "created_at"),)


class PortraitFeedback(Base, UUIDPrimaryKeyMixin):
    __tablename__ = "portrait_feedback"

    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("profiles.id", ondelete="CASCADE"), nullable=False)
    kind: Mapped[PortraitFeedbackKind] = mapped_column(Enum(PortraitFeedbackKind, name="portrait_feedback_kind"), nullable=False)
    subject: Mapped[str] = mapped_column(Text, nullable=False)
    accepted: Mapped[bool] = mapped_column(Boolean, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    __table_args__ = (Index("ix_portrait_feedback_user_created", "user_id", "created_at"),)
