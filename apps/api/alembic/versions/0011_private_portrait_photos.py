"""Add private, opt-in portrait photo metadata to profiles."""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0011_private_portrait_photos"
down_revision: Union[str, None] = "0010_portrait_refresh_job"
branch_labels: Union[str, Sequence[str], None] = None
depends_on = None


def upgrade() -> None:
    op.add_column("profiles", sa.Column("portrait_photo_key", sa.Text(), nullable=True))
    op.add_column("profiles", sa.Column("portrait_photo_content_type", sa.Text(), nullable=True))
    op.add_column(
        "profiles",
        sa.Column("portrait_photo_enabled", sa.Boolean(), nullable=False, server_default=sa.false()),
    )


def downgrade() -> None:
    op.drop_column("profiles", "portrait_photo_enabled")
    op.drop_column("profiles", "portrait_photo_content_type")
    op.drop_column("profiles", "portrait_photo_key")
