"""append-only review attempts"""
from typing import Sequence, Union
import sqlalchemy as sa
from alembic import op

revision: str = "0004_reviews"
down_revision: Union[str, None] = "0003_quizzes"
branch_labels: Union[str, Sequence[str], None] = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "reviews",
        sa.Column("id", sa.UUID(), primary_key=True),
        sa.Column("user_id", sa.UUID(), sa.ForeignKey("profiles.id", ondelete="CASCADE"), nullable=False),
        sa.Column("concept_id", sa.UUID(), sa.ForeignKey("concepts.id", ondelete="CASCADE"), nullable=False),
        sa.Column("quiz_id", sa.UUID(), sa.ForeignKey("quizzes.id", ondelete="SET NULL")),
        sa.Column("correct", sa.Boolean(), nullable=False),
        sa.Column("confidence", sa.Integer(), nullable=False),
        sa.Column("previous_mastery", sa.Numeric(5, 2), nullable=False),
        sa.Column("mastery_after", sa.Numeric(5, 2), nullable=False),
        sa.Column("response_ms", sa.Integer()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_reviews_user_created", "reviews", ["user_id", "created_at"])


def downgrade() -> None:
    op.drop_index("ix_reviews_user_created", table_name="reviews")
    op.drop_table("reviews")
