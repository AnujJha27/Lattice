"""Canonical knowledge graph: concepts and their relationships.

Design notes:
- `concepts` are canonical/shared; per-user state lives in `user_concepts`.
- Scope GLOBAL vs USER prevents accidental private concepts leaking.
- Prerequisite edges must form a DAG — validated by the API before insert,
  plus a DB-level self-loop guard here.
"""
import enum
import uuid

from pgvector.sqlalchemy import Vector
from sqlalchemy import (
    CheckConstraint,
    Computed,
    Enum,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import ARRAY, TSVECTOR, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

EMBEDDING_DIM = 768  # Gemini text-embedding-004


class ConceptScope(enum.StrEnum):
    GLOBAL = "GLOBAL"
    USER = "USER"


class EdgeType(enum.StrEnum):
    PREREQUISITE = "PREREQUISITE"
    RELATED_TO = "RELATED_TO"
    PART_OF = "PART_OF"


class Concept(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "concepts"

    canonical_name: Mapped[str] = mapped_column(Text, nullable=False, unique=True)
    description: Mapped[str | None] = mapped_column(Text)
    domain: Mapped[str | None] = mapped_column(Text)
    difficulty: Mapped[int | None] = mapped_column(Integer, CheckConstraint("difficulty BETWEEN 1 AND 5"))
    aliases: Mapped[list[str]] = mapped_column(ARRAY(Text), nullable=False, default=list)
    scope: Mapped[ConceptScope] = mapped_column(
        Enum(ConceptScope, name="concept_scope"), nullable=False, default=ConceptScope.GLOBAL
    )
    owner_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("profiles.id", ondelete="CASCADE")
    )
    summary_embedding = mapped_column(Vector(EMBEDDING_DIM), nullable=True)
    # Generated column (computed from canonical_name) — never written by the ORM.
    name_tsv: Mapped[object | None] = mapped_column(
        TSVECTOR,
        Computed("to_tsvector('english', coalesce(canonical_name,''))", persisted=True),
    )

    __table_args__ = (
        UniqueConstraint("canonical_name", name="uq_concepts_canonical_name"),
        Index("ix_concepts_domain", "domain"),
        Index("ix_concepts_aliases", "aliases", postgresql_using="gin"),
        Index("ix_concepts_name_fts", name_tsv, postgresql_using="gin"),
        Index("ix_concepts_summary_embedding", "summary_embedding", postgresql_using="hnsw",
              postgresql_ops={"summary_embedding": "vector_cosine_ops"}),
        CheckConstraint("scope != 'USER' OR owner_id IS NOT NULL", name="user_scope_has_owner"),
    )


class ConceptEdge(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "concept_edges"

    source_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("concepts.id", ondelete="CASCADE"), nullable=False
    )
    target_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("concepts.id", ondelete="CASCADE"), nullable=False
    )
    type: Mapped[EdgeType] = mapped_column(
        Enum(EdgeType, name="edge_type"), nullable=False, default=EdgeType.PREREQUISITE
    )
    confidence: Mapped[float | None]
    created_by: Mapped[str | None] = mapped_column(String(64))  # 'ai:<prompt_key>:<version>' or 'user'

    __table_args__ = (
        UniqueConstraint("source_id", "target_id", "type", name="uq_edge_triple"),
        CheckConstraint("source_id <> target_id", name="no_self_edge"),
        Index("ix_edges_target_prereq", "target_id", postgresql_where=Text("type = 'PREREQUISITE'")),
        Index("ix_edges_source_prereq", "source_id", postgresql_where=Text("type = 'PREREQUISITE'")),
    )
