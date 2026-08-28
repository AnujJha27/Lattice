"""Versioned portrait snapshots and learner corrections."""
import enum
import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, Index, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, UUIDPrimaryKeyMixin


class PortraitFeedbackKind(enum.StrEnum):
    BRIDGE = "BRIDGE"
    GAP = "GAP"
    EMERGING_INTEREST = "EMERGING_INTEREST"


class PortraitEventType(enum.StrEnum):
    VIEWED = "portrait_viewed"
    REFRESHED = "portrait_refreshed"
    ELEMENT_OPENED = "portrait_element_opened"
    ELEMENT_HOVERED = "portrait_element_hovered"
    VISUAL_SOURCE_OPENED = "portrait_visual_source_opened"
    BRAIN_NAVIGATION = "portrait_brain_navigation"
    DISCOVERY_NAVIGATION = "portrait_discovery_navigation"
    HISTORY_OPENED = "portrait_history_opened"
    SNAPSHOT_SELECTED = "portrait_snapshot_selected"
    PHOTO_ENABLED = "portrait_photo_enabled"
    PHOTO_DISABLED = "portrait_photo_disabled"


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


class PortraitEvent(Base, UUIDPrimaryKeyMixin):
    """Privacy-safe portrait telemetry; identifiers only, never concept text."""

    __tablename__ = "portrait_events"

    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("profiles.id", ondelete="CASCADE"), nullable=False)
    snapshot_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("portrait_snapshots.id", ondelete="SET NULL")
    )
    element_id: Mapped[str | None] = mapped_column(Text)
    event_type: Mapped[PortraitEventType] = mapped_column(
        Enum(
            PortraitEventType,
            name="portrait_event_type",
            values_callable=lambda enum_type: [member.value for member in enum_type],
        ),
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    __table_args__ = (Index("ix_portrait_events_user_created", "user_id", "created_at"),)
