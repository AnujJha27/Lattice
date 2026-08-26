"""quiz questions for Phase F"""
from typing import Sequence, Union
import sqlalchemy as sa
from alembic import op

revision: str = "0003_quizzes"
down_revision: Union[str, None] = "0002_job_timestamps"
branch_labels: Union[str, Sequence[str], None] = None
depends_on = None

def upgrade() -> None:
    op.create_table(
        "quizzes",
        sa.Column("id", sa.UUID(), primary_key=True),
        sa.Column("user_id", sa.UUID(), sa.ForeignKey("profiles.id", ondelete="CASCADE"), nullable=False),
        sa.Column("concept_id", sa.UUID(), sa.ForeignKey("concepts.id", ondelete="CASCADE"), nullable=False),
        sa.Column("question", sa.Text(), nullable=False),
        sa.Column("options", sa.JSON(), nullable=False),
        sa.Column("answer", sa.Integer(), nullable=False),
        sa.Column("rationale", sa.Text(), nullable=False, server_default=""),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_quizzes_user_concept", "quizzes", ["user_id", "concept_id"])

def downgrade() -> None:
    op.drop_index("ix_quizzes_user_concept", table_name="quizzes")
    op.drop_table("quizzes")
