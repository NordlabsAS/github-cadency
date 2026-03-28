"""Add review_round_count column to pull_requests table.

Revision ID: 003_add_review_round_count
Revises: 002_add_created_by
Create Date: 2026-03-28
"""
from alembic import op
import sqlalchemy as sa

revision = "003_add_review_round_count"
down_revision = "002_add_created_by"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "pull_requests",
        sa.Column("review_round_count", sa.Integer(), nullable=False, server_default="0"),
    )


def downgrade() -> None:
    op.drop_column("pull_requests", "review_round_count")
