"""Sources and their provenance — a first-class product requirement.

Sources are knowledge-system records, not lesson attachments: one source can
support many concepts. Discovered sources may be global (owner NULL);
user-uploaded ones are always owned.
"""
import enum
import uuid
from datetime import date, datetime

from pgvector.sqlalchemy import Vector
from sqlalchemy import (
    ARRAY,
    CheckConstraint,
    Date,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from app.db.models.concept import EMBEDDING_DIM


class SourceType(enum.StrEnum):
    OFFICIAL_DOCUMENTATION = "OFFICIAL_DOCUMENTATION"
    TEXTBOOK = "TEXTBOOK"
    ACADEMIC_PAPER = "ACADEMIC_PAPER"
    UNIVERSITY_MATERIAL = "UNIVERSITY_MATERIAL"
    GOVERNMENT = "GOVERNMENT"
    STANDARDS_BODY = "STANDARDS_BODY"
    REFERENCE_WORK = "REFERENCE_WORK"
    PRIMARY_SOURCE = "PRIMARY_SOURCE"
    HIGH_QUALITY_EXPLAINER = "HIGH_QUALITY_EXPLAINER"
    NEWS = "NEWS"
    BLOG = "BLOG"
    FORUM = "FORUM"
    USER_SOURCE = "USER_SOURCE"
    OTHER = "OTHER"


class SourceOrigin(enum.StrEnum):
    DISCOVERED = "DISCOVERED"  # found by the discovery pipeline
    USER_UPLOADED = "USER_UPLOADED"


class IngestStatus(enum.StrEnum):
    PENDING = "PENDING"
    FETCHED = "FETCHED"
    EXTRACTED = "EXTRACTED"
    CHUNKED = "CHUNKED"
    EMBEDDED = "EMBEDDED"
    FAILED = "FAILED"


class Source(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "sources"

    title: Mapped[str] = mapped_column(Text, nullable=False)
    url: Mapped[str | None] = mapped_column(Text)
    canonical_url: Mapped[str | None] = mapped_column(Text)
    storage_path: Mapped[str | None] = mapped_column(Text)  # object-storage key for PDFs etc.
    source_type: Mapped[SourceType] = mapped_column(
        Enum(SourceType, name="source_type"), nullable=False, default=SourceType.OTHER
    )
    origin: Mapped[SourceOrigin] = mapped_column(
        Enum(SourceOrigin, name="source_origin"), nullable=False, default=SourceOrigin.DISCOVERED
    )
    publisher: Mapped[str | None] = mapped_column(Text)
    authors: Mapped[list[str] | None] = mapped_column(ARRAY(Text))
    publication_date: Mapped[date | None] = mapped_column(Date)
    language: Mapped[str | None] = mapped_column(Text)

    authority_score: Mapped[float | None] = mapped_column(Float)
    relevance_score: Mapped[float | None] = mapped_column(Float)
    freshness_score: Mapped[float | None] = mapped_column(Float)

    doi: Mapped[str | None] = mapped_column(Text)
    arxiv_id: Mapped[str | None] = mapped_column(Text)

    retrieved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    content_hash: Mapped[str | None] = mapped_column(Text)
    ingest_status: Mapped[IngestStatus] = mapped_column(
        Enum(IngestStatus, name="ingest_status"), nullable=False, default=IngestStatus.PENDING
    )
    owner_id: Mapped[uuid.UUID | None] = mapped_column(  # NULL → shared discovered source
        UUID(as_uuid=True), ForeignKey("profiles.id", ondelete="CASCADE")
    )
    metadata_: Mapped[dict] = mapped_column("metadata", JSONB, nullable=False, default=dict)

    __table_args__ = (
        CheckConstraint("url IS NOT NULL OR storage_path IS NOT NULL", name="has_locator"),
        UniqueConstraint("canonical_url", name="uq_sources_canonical_url"),
        Index("ix_sources_doi", "doi", unique=True, postgresql_where=Text("doi IS NOT NULL")),
        Index("ix_sources_arxiv", "arxiv_id", unique=True, postgresql_where=Text("arxiv_id IS NOT NULL")),
    )


class SourceChunk(Base, UUIDPrimaryKeyMixin):
    __tablename__ = "source_chunks"

    source_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("sources.id", ondelete="CASCADE"), nullable=False
    )
    position: Mapped[int] = mapped_column(Integer, nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    token_count: Mapped[int | None]
    embedding = mapped_column(Vector(EMBEDDING_DIM), nullable=True)
    chunk_metadata: Mapped[dict] = mapped_column("metadata", JSONB, nullable=False, default=dict)

    __table_args__ = (
        UniqueConstraint("source_id", "position", name="uq_chunk_source_position"),
        Index("ix_chunks_embedding", "embedding", postgresql_using="hnsw",
              postgresql_ops={"embedding": "vector_cosine_ops"}),
    )


class ConceptSource(Base):
    __tablename__ = "concept_sources"

    concept_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("concepts.id", ondelete="CASCADE"), primary_key=True
    )
    source_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("sources.id", ondelete="CASCADE"), primary_key=True
    )
    relevance: Mapped[float] = mapped_column(Numeric(4, 3), nullable=False, default=1.0)
