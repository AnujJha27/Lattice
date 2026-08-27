"""Add REVIEW_DUE to the deterministic mastery state enum."""
from typing import Sequence, Union

from alembic import op

revision: str = "0008_review_due_state"
down_revision: Union[str, None] = "0007_portrait_visual_refresh_job"
branch_labels: Union[str, Sequence[str], None] = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TYPE mastery_state ADD VALUE IF NOT EXISTS 'REVIEW_DUE'")


def downgrade() -> None:
    # PostgreSQL enum values cannot be removed safely in-place.
    pass
