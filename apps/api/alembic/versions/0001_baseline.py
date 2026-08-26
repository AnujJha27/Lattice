"""Lattice baseline schema

Revision ID: 0001_baseline
Revises:
Create Date: 2026-08-24

Baseline mirroring app.db.models. Extensions and auth-schema FKs are handled
here; RLS is enabled as defense-in-depth even though the API scopes every query.
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from pgvector.sqlalchemy import Vector
from sqlalchemy.dialects import postgresql as pg

revision: str = "0001_baseline"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── Extensions ────────────────────────────────────────────────
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")
    op.execute("CREATE EXTENSION IF NOT EXISTS pgcrypto")

    # ── Enums ─────────────────────────────────────────────────────
    for name, values in {
        "concept_scope": ["GLOBAL", "USER"],
        "edge_type": ["PREREQUISITE", "RELATED_TO", "PART_OF"],
        "mastery_state": ["UNSEEN", "AVAILABLE", "LEARNING", "FAMILIAR", "MASTERED"],
        "goal_status": ["ACTIVE", "PAUSED", "COMPLETE", "ARCHIVED"],
        "pathway_status": ["GENERATING", "READY", "FAILED", "ARCHIVED"],
        "source_type": [
            "OFFICIAL_DOCUMENTATION", "TEXTBOOK", "ACADEMIC_PAPER",
            "UNIVERSITY_MATERIAL", "GOVERNMENT", "STANDARDS_BODY",
            "REFERENCE_WORK", "PRIMARY_SOURCE", "HIGH_QUALITY_EXPLAINER",
            "NEWS", "BLOG", "FORUM", "USER_SOURCE", "OTHER",
        ],
        "source_origin": ["DISCOVERED", "USER_UPLOADED"],
        "ingest_status": ["PENDING", "FETCHED", "EXTRACTED", "CHUNKED", "EMBEDDED", "FAILED"],
        "job_type": [
            "SOURCE_DISCOVERY", "SOURCE_INGEST", "EMBEDDING",
            "PATHWAY_GENERATION", "LESSON_GENERATION", "GRAPH_METRICS",
        ],
        "job_status": ["PENDING", "RUNNING", "SUCCEEDED", "FAILED", "CANCELLED"],
    }.items():
        enum = pg.ENUM(*values, name=name)
        enum.create(op.get_bind())

    bind = op.get_bind()

    # ── profiles ──────────────────────────────────────────────────
    op.create_table(
        "profiles",
        sa.Column("id", pg.UUID(as_uuid=True), primary_key=True),
        sa.Column("display_name", sa.Text()),
        sa.Column("onboarded_at", sa.DateTime(timezone=True)),
        sa.Column("settings", pg.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.execute(
        """
        ALTER TABLE profiles ADD CONSTRAINT fk_profiles_id_auth_users
        FOREIGN KEY (id) REFERENCES auth.users(id) ON DELETE CASCADE
        """
    )

    # ── concepts ──────────────────────────────────────────────────
    op.create_table(
        "concepts",
        sa.Column("id", pg.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("canonical_name", sa.Text(), nullable=False),
        sa.Column("description", sa.Text()),
        sa.Column("domain", sa.Text()),
        sa.Column("difficulty", sa.Integer()),
        sa.Column("aliases", sa.ARRAY(sa.Text()), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("scope", pg.ENUM(name="concept_scope", create_type=False), nullable=False,
                  server_default="GLOBAL"),
        sa.Column("owner_id", pg.UUID(as_uuid=True), sa.ForeignKey("profiles.id", ondelete="CASCADE")),
        sa.Column("summary_embedding", Vector(768)),
        sa.Column(
            "name_tsv",
            pg.TSVECTOR(),
            sa.Computed("to_tsvector('english', coalesce(canonical_name,''))", persisted=True),
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("canonical_name", name="uq_concepts_canonical_name"),
        sa.CheckConstraint("difficulty IS NULL OR difficulty BETWEEN 1 AND 5"),
        sa.CheckConstraint("scope != 'USER' OR owner_id IS NOT NULL", name="user_scope_has_owner"),
    )
    op.create_index("ix_concepts_domain", "concepts", ["domain"])
    op.execute("CREATE INDEX ix_concepts_aliases ON concepts USING gin (aliases)")
    op.execute("CREATE INDEX ix_concepts_name_fts ON concepts USING gin (name_tsv)")
    op.execute(
        "CREATE INDEX ix_concepts_summary_embedding ON concepts "
        "USING hnsw (summary_embedding vector_cosine_ops)"
    )

    # ── concept_edges ─────────────────────────────────────────────
    op.create_table(
        "concept_edges",
        sa.Column("id", pg.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("source_id", pg.UUID(as_uuid=True), sa.ForeignKey("concepts.id", ondelete="CASCADE"), nullable=False),
        sa.Column("target_id", pg.UUID(as_uuid=True), sa.ForeignKey("concepts.id", ondelete="CASCADE"), nullable=False),
        sa.Column("type", pg.ENUM(name="edge_type", create_type=False), nullable=False, server_default="PREREQUISITE"),
        sa.Column("confidence", sa.Float()),
        sa.Column("created_by", sa.String(64)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("source_id", "target_id", "type", name="uq_edge_triple"),
        sa.CheckConstraint("source_id <> target_id", name="no_self_edge"),
    )
    op.create_index(
        "ix_edges_target_prereq", "concept_edges", ["target_id"],
        postgresql_where=sa.text("type = 'PREREQUISITE'"),
    )
    op.create_index(
        "ix_edges_source_prereq", "concept_edges", ["source_id"],
        postgresql_where=sa.text("type = 'PREREQUISITE'"),
    )

    # ── user_concepts ─────────────────────────────────────────────
    op.create_table(
        "user_concepts",
        sa.Column("user_id", pg.UUID(as_uuid=True), sa.ForeignKey("profiles.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("concept_id", pg.UUID(as_uuid=True), sa.ForeignKey("concepts.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("mastery_score", sa.Numeric(5, 2), nullable=False, server_default="0"),
        sa.Column("state", pg.ENUM(name="mastery_state", create_type=False), nullable=False, server_default="UNSEEN"),
        sa.Column("interest_score", sa.Numeric(5, 2), nullable=False, server_default="0"),
        sa.Column("confidence", sa.Numeric(5, 2), nullable=False, server_default="0"),
        sa.Column("attempt_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("successful_reviews", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("review_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("last_seen_at", sa.DateTime(timezone=True)),
        sa.Column("last_tested_at", sa.DateTime(timezone=True)),
        sa.Column("next_review_at", sa.DateTime(timezone=True)),
        sa.CheckConstraint("mastery_score BETWEEN 0 AND 100", name="mastery_range"),
        sa.CheckConstraint("interest_score BETWEEN 0 AND 100", name="interest_range"),
    )
    op.create_index("ix_user_concepts_next_review", "user_concepts", ["user_id", "next_review_at"])

    # ── goals ─────────────────────────────────────────────────────
    op.create_table(
        "goals",
        sa.Column("id", pg.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("user_id", pg.UUID(as_uuid=True), sa.ForeignKey("profiles.id", ondelete="CASCADE"), nullable=False),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("description", sa.Text()),
        sa.Column("target_depth", sa.Text()),
        sa.Column("motivation", sa.Text()),
        sa.Column("time_commitment", sa.Text()),
        sa.Column("status", pg.ENUM(name="goal_status", create_type=False), nullable=False, server_default="ACTIVE"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_goals_user_status", "goals", ["user_id", "status"])

    op.create_table(
        "goal_concepts",
        sa.Column("goal_id", pg.UUID(as_uuid=True), sa.ForeignKey("goals.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("concept_id", pg.UUID(as_uuid=True), sa.ForeignKey("concepts.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("importance", sa.Numeric(4, 3), nullable=False, server_default="1"),
    )

    # ── pathways ──────────────────────────────────────────────────
    op.create_table(
        "pathways",
        sa.Column("id", pg.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("user_id", pg.UUID(as_uuid=True), sa.ForeignKey("profiles.id", ondelete="CASCADE"), nullable=False),
        sa.Column("goal_id", pg.UUID(as_uuid=True), sa.ForeignKey("goals.id", ondelete="SET NULL")),
        sa.Column("concept_id", pg.UUID(as_uuid=True), sa.ForeignKey("concepts.id", ondelete="SET NULL")),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("topic", sa.Text()),
        sa.Column("description", sa.Text()),
        sa.Column("status", pg.ENUM(name="pathway_status", create_type=False), nullable=False,
                  server_default="GENERATING"),
        sa.Column("generation_metadata", pg.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_pathways_user", "pathways", ["user_id", "status"])

    op.create_table(
        "pathway_sections",
        sa.Column("id", pg.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("pathway_id", pg.UUID(as_uuid=True), sa.ForeignKey("pathways.id", ondelete="CASCADE"), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("summary", sa.Text()),
    )

    op.create_table(
        "pathway_concepts",
        sa.Column("pathway_id", pg.UUID(as_uuid=True), sa.ForeignKey("pathways.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("concept_id", pg.UUID(as_uuid=True), sa.ForeignKey("concepts.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("section_id", pg.UUID(as_uuid=True), sa.ForeignKey("pathway_sections.id", ondelete="SET NULL")),
        sa.Column("position", sa.Integer(), nullable=False, server_default="0"),
    )

    # ── sources ───────────────────────────────────────────────────
    op.create_table(
        "sources",
        sa.Column("id", pg.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("url", sa.Text()),
        sa.Column("canonical_url", sa.Text()),
        sa.Column("storage_path", sa.Text()),
        sa.Column("source_type", pg.ENUM(name="source_type", create_type=False), nullable=False,
                  server_default="OTHER"),
        sa.Column("origin", pg.ENUM(name="source_origin", create_type=False), nullable=False,
                  server_default="DISCOVERED"),
        sa.Column("publisher", sa.Text()),
        sa.Column("authors", sa.ARRAY(sa.Text())),
        sa.Column("publication_date", sa.Date()),
        sa.Column("language", sa.Text()),
        sa.Column("authority_score", sa.Float()),
        sa.Column("relevance_score", sa.Float()),
        sa.Column("freshness_score", sa.Float()),
        sa.Column("doi", sa.Text()),
        sa.Column("arxiv_id", sa.Text()),
        sa.Column("retrieved_at", sa.DateTime(timezone=True)),
        sa.Column("content_hash", sa.Text()),
        sa.Column("ingest_status", pg.ENUM(name="ingest_status", create_type=False), nullable=False,
                  server_default="PENDING"),
        sa.Column("owner_id", pg.UUID(as_uuid=True), sa.ForeignKey("profiles.id", ondelete="CASCADE")),
        sa.Column("metadata", pg.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id"),
        sa.CheckConstraint("url IS NOT NULL OR storage_path IS NOT NULL", name="has_locator"),
        sa.UniqueConstraint("canonical_url", name="uq_sources_canonical_url"),
    )
    op.create_index("ix_sources_doi", "sources", ["doi"], unique=True,
                    postgresql_where=sa.text("doi IS NOT NULL"))
    op.create_index("ix_sources_arxiv", "sources", ["arxiv_id"], unique=True,
                    postgresql_where=sa.text("arxiv_id IS NOT NULL"))

    op.create_table(
        "source_chunks",
        sa.Column("id", pg.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("source_id", pg.UUID(as_uuid=True), sa.ForeignKey("sources.id", ondelete="CASCADE"), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("token_count", sa.Integer()),
        sa.Column("embedding", Vector(768)),
        sa.Column("metadata", pg.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("source_id", "position", name="uq_chunk_source_position"),
    )
    op.execute(
        "CREATE INDEX ix_chunks_embedding ON source_chunks USING hnsw (embedding vector_cosine_ops)"
    )

    op.create_table(
        "concept_sources",
        sa.Column("concept_id", pg.UUID(as_uuid=True), sa.ForeignKey("concepts.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("source_id", pg.UUID(as_uuid=True), sa.ForeignKey("sources.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("relevance", sa.Numeric(4, 3), nullable=False, server_default="1"),
    )

    # ── lessons & provenance ──────────────────────────────────────
    op.create_table(
        "prompt_versions",
        sa.Column("id", pg.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("key", sa.Text(), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("template", sa.Text(), nullable=False),
        sa.Column("provider", sa.Text()),
        sa.Column("model", sa.Text()),
        sa.Column("parameters", pg.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("schema_version", sa.Integer(), nullable=False, server_default="1"),
    )
    op.create_index("ix_prompt_versions_key_version", "prompt_versions", ["key", "version"], unique=True)

    op.create_table(
        "ai_generations",
        sa.Column("id", pg.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("user_id", pg.UUID(as_uuid=True)),
        sa.Column("feature", sa.Text(), nullable=False),
        sa.Column("prompt_key", sa.Text()),
        sa.Column("prompt_version", sa.Integer()),
        sa.Column("provider", sa.Text(), nullable=False),
        sa.Column("model", sa.Text(), nullable=False),
        sa.Column("input_tokens", sa.Integer()),
        sa.Column("output_tokens", sa.Integer()),
        sa.Column("cost_estimate_usd", sa.Float()),
        sa.Column("latency_ms", sa.Integer()),
        sa.Column("success", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("error", sa.Text()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint("success IN (0, 1)", name="success_bool"),
    )
    op.create_index("ix_ai_generations_feature_time", "ai_generations", ["feature", "created_at"])

    op.create_table(
        "lessons",
        sa.Column("id", pg.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("concept_id", pg.UUID(as_uuid=True), sa.ForeignKey("concepts.id", ondelete="CASCADE"), nullable=False),
        sa.Column("user_id", pg.UUID(as_uuid=True), sa.ForeignKey("profiles.id", ondelete="CASCADE"), nullable=False),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("content", pg.JSONB(), nullable=False),
        sa.Column("status", sa.Text(), nullable=False, server_default="READY"),
        sa.Column("grounding", sa.Text(), nullable=False, server_default="GROUNDED"),
        sa.Column("generated_at", sa.DateTime(timezone=True)),
        sa.Column("generation_id", pg.UUID(as_uuid=True), sa.ForeignKey("ai_generations.id", ondelete="SET NULL")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_lessons_concept_user", "lessons", ["concept_id", "user_id", "created_at"])

    op.create_table(
        "lesson_sources",
        sa.Column("lesson_id", pg.UUID(as_uuid=True), sa.ForeignKey("lessons.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("source_id", pg.UUID(as_uuid=True), sa.ForeignKey("sources.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("relevance", sa.Float(), nullable=False, server_default="1"),
    )

    # ── jobs ──────────────────────────────────────────────────────
    op.create_table(
        "jobs",
        sa.Column("id", pg.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("type", pg.ENUM(name="job_type", create_type=False), nullable=False),
        sa.Column("status", pg.ENUM(name="job_status", create_type=False), nullable=False,
                  server_default="PENDING"),
        sa.Column("payload", pg.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("result", pg.JSONB()),
        sa.Column("progress", sa.Numeric(3, 2), nullable=False, server_default="0"),
        sa.Column("dedupe_key", sa.Text()),
        sa.Column("attempts", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("max_attempts", sa.Integer(), nullable=False, server_default="3"),
        sa.Column("last_error", sa.Text()),
        sa.Column("run_after", sa.DateTime(timezone=True)),
        sa.Column("started_at", sa.DateTime(timezone=True)),
        sa.Column("finished_at", sa.DateTime(timezone=True)),
        sa.CheckConstraint("progress BETWEEN 0 AND 1", name="progress_range"),
        sa.CheckConstraint("attempts >= 0 AND max_attempts > 0", name="attempts_sane"),
    )
    op.create_index("ix_jobs_poll", "jobs", ["status", "run_after"])
    op.create_index("ix_jobs_dedupe", "jobs", ["dedupe_key"], unique=True,
                    postgresql_where=sa.text("dedupe_key IS NOT NULL"))

    # ── Defense-in-depth RLS (API also scopes queries explicitly) ──
    op.execute("ALTER TABLE user_concepts ENABLE ROW LEVEL SECURITY")
    op.execute("""
        CREATE POLICY own_user_concepts ON user_concepts FOR ALL
        USING (auth.uid() = user_id) WITH CHECK (auth.uid() = user_id)
    """)


def downgrade() -> None:
    bind = op.get_bind()
    tables = [
        "jobs", "lesson_sources", "lessons", "ai_generations", "prompt_versions",
        "concept_sources", "source_chunks", "sources",
        "pathway_concepts", "pathway_sections", "pathways",
        "goal_concepts", "goals", "user_concepts", "concept_edges", "concepts", "profiles",
    ]
    for t in tables:
        op.drop_table(t)
    for name in [
        "job_status", "job_type", "ingest_status", "source_origin", "source_type",
        "pathway_status", "goal_status", "mastery_state", "edge_type", "concept_scope",
    ]:
        pg.ENUM(name=name).drop(bind, checkfirst=True)
