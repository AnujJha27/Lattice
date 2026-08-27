"""Rights-aware visual assets for portrait snapshots."""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0006_visual_assets"
down_revision: Union[str, None] = "0005_recommendations_portraits"
branch_labels: Union[str, Sequence[str], None] = None
depends_on = None


def upgrade() -> None:
    rights_enum = postgresql.ENUM(
        "PUBLIC_DOMAIN", "CC0", "CC_BY", "CC_BY_SA", "RESTRICTED", "UNKNOWN",
        name="visual_rights_class",
    )
    rights_enum.create(op.get_bind(), checkfirst=True)
    op.create_table(
        "visual_assets",
        sa.Column("id", sa.UUID(), primary_key=True),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("source_url", sa.Text(), nullable=False),
        sa.Column("canonical_url", sa.Text(), nullable=False),
        sa.Column("creator", sa.Text()),
        sa.Column("institution", sa.Text()),
        sa.Column("source_date", sa.Text()),
        sa.Column("license", sa.Text()),
        sa.Column("rights_class", postgresql.ENUM(name="visual_rights_class", create_type=False), nullable=False),
        sa.Column("attribution_text", sa.Text()),
        sa.Column("image_url", sa.Text(), nullable=False),
        sa.Column("thumbnail_url", sa.Text()),
        sa.Column("width", sa.Integer()),
        sa.Column("height", sa.Integer()),
        sa.Column("provider", sa.Text(), nullable=False),
        sa.Column("relevance_score", sa.Float(), nullable=False, server_default="0"),
        sa.Column("aesthetic_score", sa.Float(), nullable=False, server_default="0"),
        sa.Column("rights_score", sa.Float(), nullable=False, server_default="0"),
        sa.Column("quality_score", sa.Float(), nullable=False, server_default="0"),
        sa.Column("cached_image_key", sa.Text()),
        sa.Column("content_hash", sa.Text()),
        sa.Column("retrieved_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("metadata", postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.UniqueConstraint("canonical_url", name="uq_visual_assets_canonical_url"),
    )
    op.create_table(
        "portrait_visuals",
        sa.Column("id", sa.UUID(), primary_key=True),
        sa.Column("snapshot_id", sa.UUID(), sa.ForeignKey("portrait_snapshots.id", ondelete="CASCADE"), nullable=False),
        sa.Column("visual_asset_id", sa.UUID(), sa.ForeignKey("visual_assets.id", ondelete="CASCADE"), nullable=False),
        sa.Column("represents", sa.Text(), nullable=False),
        sa.Column("concept_ids", postgresql.JSONB(), nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("portrait_role", sa.Text(), nullable=False),
        sa.Column("relevance_score", sa.Float(), nullable=False, server_default="0"),
        sa.UniqueConstraint("snapshot_id", "visual_asset_id", name="uq_portrait_visual_snapshot_asset"),
    )


def downgrade() -> None:
    op.drop_table("portrait_visuals")
    op.drop_table("visual_assets")
    sa.Enum(name="visual_rights_class").drop(op.get_bind(), checkfirst=True)
