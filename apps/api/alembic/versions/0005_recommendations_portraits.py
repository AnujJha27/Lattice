"""Recommendation telemetry and versioned portrait state."""
from typing import Sequence, Union
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0005_recommendations_portraits"
down_revision: Union[str, None] = "0004_reviews"
branch_labels: Union[str, Sequence[str], None] = None
depends_on = None


def upgrade() -> None:
    event_enum = postgresql.ENUM("IMPRESSION", "CLICK", name="recommendation_event_type", create_type=False)
    feedback_enum = postgresql.ENUM("BRIDGE", "GAP", "EMERGING_INTEREST", name="portrait_feedback_kind", create_type=False)
    postgresql.ENUM("IMPRESSION", "CLICK", name="recommendation_event_type").create(op.get_bind(), checkfirst=True)
    postgresql.ENUM("BRIDGE", "GAP", "EMERGING_INTEREST", name="portrait_feedback_kind").create(op.get_bind(), checkfirst=True)
    op.create_table(
        "recommendation_events",
        sa.Column("id", sa.UUID(), primary_key=True),
        sa.Column("user_id", sa.UUID(), sa.ForeignKey("profiles.id", ondelete="CASCADE"), nullable=False),
        sa.Column("concept_id", sa.UUID(), sa.ForeignKey("concepts.id", ondelete="CASCADE"), nullable=False),
        sa.Column("event_type", event_enum, nullable=False),
        sa.Column("score", sa.Numeric(8, 2), nullable=False),
        sa.Column("factors", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_recommendation_events_user_created", "recommendation_events", ["user_id", "created_at"])
    op.create_table(
        "portrait_snapshots",
        sa.Column("id", sa.UUID(), primary_key=True),
        sa.Column("user_id", sa.UUID(), sa.ForeignKey("profiles.id", ondelete="CASCADE"), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_portrait_snapshots_user_created", "portrait_snapshots", ["user_id", "created_at"])
    op.create_table(
        "portrait_feedback",
        sa.Column("id", sa.UUID(), primary_key=True),
        sa.Column("user_id", sa.UUID(), sa.ForeignKey("profiles.id", ondelete="CASCADE"), nullable=False),
        sa.Column("kind", feedback_enum, nullable=False),
        sa.Column("subject", sa.Text(), nullable=False),
        sa.Column("accepted", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_portrait_feedback_user_created", "portrait_feedback", ["user_id", "created_at"])


def downgrade() -> None:
    op.drop_index("ix_portrait_feedback_user_created", table_name="portrait_feedback")
    op.drop_table("portrait_feedback")
    op.drop_index("ix_portrait_snapshots_user_created", table_name="portrait_snapshots")
    op.drop_table("portrait_snapshots")
    op.drop_index("ix_recommendation_events_user_created", table_name="recommendation_events")
    op.drop_table("recommendation_events")
    sa.Enum(name="portrait_feedback_kind").drop(op.get_bind(), checkfirst=True)
    sa.Enum(name="recommendation_event_type").drop(op.get_bind(), checkfirst=True)
