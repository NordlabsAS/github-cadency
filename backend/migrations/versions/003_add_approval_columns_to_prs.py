"""Add approval tracking columns to pull_requests table.

Revision ID: 003_add_approval_columns
Revises: 002_add_created_by
Create Date: 2026-03-28
"""
from alembic import op
import sqlalchemy as sa

revision = "003_add_approval_columns"
down_revision = "002_add_created_by"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "pull_requests",
        sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "pull_requests",
        sa.Column("approval_count", sa.Integer(), nullable=False, server_default="0"),
    )
    op.add_column(
        "pull_requests",
        sa.Column("time_to_approve_s", sa.Integer(), nullable=True),
    )
    op.add_column(
        "pull_requests",
        sa.Column("time_after_approve_s", sa.Integer(), nullable=True),
    )
    op.add_column(
        "pull_requests",
        sa.Column(
            "merged_without_approval",
            sa.Boolean(),
            nullable=False,
            server_default="false",
        ),
    )


def downgrade() -> None:
    op.drop_column("pull_requests", "merged_without_approval")
    op.drop_column("pull_requests", "time_after_approve_s")
    op.drop_column("pull_requests", "time_to_approve_s")
    op.drop_column("pull_requests", "approval_count")
    op.drop_column("pull_requests", "approved_at")
