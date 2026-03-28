"""Add closes_issue_numbers JSONB column to pull_requests.

Revision ID: 005_add_closes_issue_numbers
Revises: 004_merge_003_heads
Create Date: 2026-03-28
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "005_add_closes_issue_numbers"
down_revision = "004_merge_003_heads"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "pull_requests",
        sa.Column("closes_issue_numbers", postgresql.JSONB(), nullable=True),
    )


def downgrade():
    op.drop_column("pull_requests", "closes_issue_numbers")
