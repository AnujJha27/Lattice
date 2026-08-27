"""Reusable visual assets and immutable portrait associations."""
import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum, Float, ForeignKey, Integer, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, UUIDPrimaryKeyMixin
from app.modules.visual_sources.rights import RightsClass


class VisualAsset(Base, UUIDPrimaryKeyMixin):
    __tablename__ = "visual_assets"

    title: Mapped[str] = mapped_column(Text, nullable=False)
    source_url: Mapped[str] = mapped_column(Text, nullable=False)
    canonical_url: Mapped[str] = mapped_column(Text, nullable=False, unique=True)
    creator: Mapped[str | None] = mapped_column(Text)
    institution: Mapped[str | None] = mapped_column(Text)
    source_date: Mapped[str | None] = mapped_column(Text)
    license: Mapped[str | None] = mapped_column(Text)
    rights_class: Mapped[RightsClass] = mapped_column(Enum(RightsClass, name="visual_rights_class"), nullable=False)
    attribution_text: Mapped[str | None] = mapped_column(Text)
    image_url: Mapped[str] = mapped_column(Text, nullable=False)
    thumbnail_url: Mapped[str | None] = mapped_column(Text)
    width: Mapped[int | None] = mapped_column(Integer)
    height: Mapped[int | None] = mapped_column(Integer)
    provider: Mapped[str] = mapped_column(Text, nullable=False)
    relevance_score: Mapped[float] = mapped_column(Float, nullable=False, default=0)
    aesthetic_score: Mapped[float] = mapped_column(Float, nullable=False, default=0)
    rights_score: Mapped[float] = mapped_column(Float, nullable=False, default=0)
    quality_score: Mapped[float] = mapped_column(Float, nullable=False, default=0)
    cached_image_key: Mapped[str | None] = mapped_column(Text)
    content_hash: Mapped[str | None] = mapped_column(Text)
    retrieved_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    metadata_: Mapped[dict] = mapped_column("metadata", JSONB, nullable=False, default=dict)


class PortraitVisual(Base, UUIDPrimaryKeyMixin):
    __tablename__ = "portrait_visuals"

    snapshot_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("portrait_snapshots.id", ondelete="CASCADE"), nullable=False
    )
    visual_asset_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("visual_assets.id", ondelete="CASCADE"), nullable=False
    )
    represents: Mapped[str] = mapped_column(Text, nullable=False)
    concept_ids: Mapped[list[str]] = mapped_column(JSONB, nullable=False, default=list)
    portrait_role: Mapped[str] = mapped_column(Text, nullable=False)
    relevance_score: Mapped[float] = mapped_column(Float, nullable=False, default=0)

    __table_args__ = (UniqueConstraint("snapshot_id", "visual_asset_id", name="uq_portrait_visual_snapshot_asset"),)
