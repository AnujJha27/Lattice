"""jobs.created_at / updated_at for FIFO polling

Revision ID: 0002_job_timestamps
Revises: 0001_baseline
Create Date: 2026-08-25
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0002_job_timestamps"
down_revision: Union[str, None] = "0001_baseline"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "jobs",
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.func.now()),
    )
    op.add_column(
        "jobs",
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.func.now()),
    )
    op.create_index("ix_jobs_created_at", "jobs", ["created_at"])


def downgrade() -> None:
    op.drop_index("ix_jobs_created_at", table_name="jobs")
    op.drop_column("jobs", "updated_at")
    op.drop_column("jobs", "created_at")
