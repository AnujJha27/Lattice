"""Recommendation telemetry for ranking evaluation."""
import enum
import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, Index, Numeric, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, UUIDPrimaryKeyMixin


class RecommendationEventType(enum.StrEnum):
    IMPRESSION = "IMPRESSION"
    CLICK = "CLICK"


class RecommendationEvent(Base, UUIDPrimaryKeyMixin):
    __tablename__ = "recommendation_events"

    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("profiles.id", ondelete="CASCADE"), nullable=False)
    concept_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("concepts.id", ondelete="CASCADE"), nullable=False)
    event_type: Mapped[RecommendationEventType] = mapped_column(Enum(RecommendationEventType, name="recommendation_event_type"), nullable=False)
    score: Mapped[float] = mapped_column(Numeric(8, 2), nullable=False)
    factors: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    __table_args__ = (Index("ix_recommendation_events_user_created", "user_id", "created_at"),)
