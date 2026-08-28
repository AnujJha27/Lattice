"""Track explicit portrait photo preference changes."""
from typing import Sequence, Union

from alembic import op

revision: str = "0012_portrait_photo_events"
down_revision: Union[str, None] = "0011_private_portrait_photos"
branch_labels: Union[str, Sequence[str], None] = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TYPE portrait_event_type ADD VALUE IF NOT EXISTS 'portrait_photo_enabled'")
    op.execute("ALTER TYPE portrait_event_type ADD VALUE IF NOT EXISTS 'portrait_photo_disabled'")


def downgrade() -> None:
    # PostgreSQL enum values cannot be removed safely in-place.
    pass
