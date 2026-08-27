"""Add a durable job type for asynchronous portrait recomputation."""
from typing import Sequence, Union

from alembic import op

revision: str = "0010_portrait_refresh_job"
down_revision: Union[str, None] = "0009_portrait_events"
branch_labels: Union[str, Sequence[str], None] = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TYPE job_type ADD VALUE IF NOT EXISTS 'PORTRAIT_REFRESH'")


def downgrade() -> None:
    # PostgreSQL enum values cannot be removed safely in-place.
    pass
