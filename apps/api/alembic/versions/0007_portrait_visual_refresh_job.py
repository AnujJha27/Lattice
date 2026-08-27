"""Add a durable job type for asynchronous portrait visual refreshes."""
from typing import Sequence, Union

from alembic import op

revision: str = "0007_portrait_visual_refresh_job"
down_revision: Union[str, None] = "0006_visual_assets"
branch_labels: Union[str, Sequence[str], None] = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TYPE job_type ADD VALUE IF NOT EXISTS 'PORTRAIT_VISUAL_REFRESH'")


def downgrade() -> None:
    # PostgreSQL enum values cannot be removed safely in-place. The value is
    # harmless for older code and is retained on downgrade.
    pass
