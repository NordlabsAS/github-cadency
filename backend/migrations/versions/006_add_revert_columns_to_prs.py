"""Add is_revert and reverted_pr_number columns to pull_requests.

Revision ID: 006_add_revert_columns
Revises: 005_add_closes_issue_numbers
Create Date: 2026-03-28
"""
from alembic import op
import sqlalchemy as sa

revision = "006_add_revert_columns"
down_revision = "005_add_closes_issue_numbers"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "pull_requests",
        sa.Column("is_revert", sa.Boolean(), nullable=False, server_default="false"),
    )
    op.add_column(
        "pull_requests",
        sa.Column("reverted_pr_number", sa.Integer(), nullable=True),
    )


def downgrade():
    op.drop_column("pull_requests", "reverted_pr_number")
    op.drop_column("pull_requests", "is_revert")
