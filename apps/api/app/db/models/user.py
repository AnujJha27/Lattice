"""User identity. Auth lives in Supabase (auth.users); we mirror a profile row.

The FK profiles.id → auth.users.id is declared only in the Alembic baseline
(auth schema tables are not part of our SQLAlchemy metadata).
"""
import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin


class Profile(Base, TimestampMixin):
    __tablename__ = "profiles"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    display_name: Mapped[str | None] = mapped_column(Text)
    onboarded_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    settings: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    portrait_photo_key: Mapped[str | None] = mapped_column(Text)
    portrait_photo_content_type: Mapped[str | None] = mapped_column(Text)
    portrait_photo_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
