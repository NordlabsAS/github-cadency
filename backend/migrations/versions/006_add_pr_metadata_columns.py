"""Add labels, merged_by_username, head/base branch, is_self_merged to pull_requests.

Revision ID: 006_add_pr_metadata
Revises: 005_add_closes_issue_numbers
Create Date: 2026-03-28
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "006_add_pr_metadata"
down_revision = "005_add_closes_issue_numbers"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "pull_requests",
        sa.Column("labels", postgresql.JSONB(), nullable=True),
    )
    op.add_column(
        "pull_requests",
        sa.Column("merged_by_username", sa.String(255), nullable=True),
    )
    op.add_column(
        "pull_requests",
        sa.Column("head_branch", sa.String(255), nullable=True),
    )
    op.add_column(
        "pull_requests",
        sa.Column("base_branch", sa.String(255), nullable=True),
    )
    op.add_column(
        "pull_requests",
        sa.Column(
            "is_self_merged",
            sa.Boolean(),
            nullable=False,
            server_default="false",
        ),
    )


def downgrade():
    op.drop_column("pull_requests", "is_self_merged")
    op.drop_column("pull_requests", "base_branch")
    op.drop_column("pull_requests", "head_branch")
    op.drop_column("pull_requests", "merged_by_username")
    op.drop_column("pull_requests", "labels")
