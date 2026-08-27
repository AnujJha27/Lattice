"""Store privacy-safe portrait interaction events."""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0009_portrait_events"
down_revision: Union[str, None] = "0008_review_due_state"
branch_labels: Union[str, Sequence[str], None] = None
depends_on = None


def upgrade() -> None:
    event_enum = postgresql.ENUM(
        "portrait_viewed",
        "portrait_refreshed",
        "portrait_element_opened",
        "portrait_element_hovered",
        "portrait_visual_source_opened",
        "portrait_brain_navigation",
        "portrait_discovery_navigation",
        "portrait_history_opened",
        "portrait_snapshot_selected",
        name="portrait_event_type",
    )
    event_enum.create(op.get_bind(), checkfirst=True)
    op.create_table(
        "portrait_events",
        sa.Column("id", sa.UUID(), primary_key=True),
        sa.Column("user_id", sa.UUID(), sa.ForeignKey("profiles.id", ondelete="CASCADE"), nullable=False),
        sa.Column("snapshot_id", sa.UUID(), sa.ForeignKey("portrait_snapshots.id", ondelete="SET NULL")),
        sa.Column("element_id", sa.Text()),
        sa.Column("event_type", postgresql.ENUM(name="portrait_event_type", create_type=False), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_portrait_events_user_created", "portrait_events", ["user_id", "created_at"])


def downgrade() -> None:
    op.drop_index("ix_portrait_events_user_created", table_name="portrait_events")
    op.drop_table("portrait_events")
    sa.Enum(name="portrait_event_type").drop(op.get_bind(), checkfirst=True)
