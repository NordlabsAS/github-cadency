"""Add issue quality scoring columns to issues table.

Revision ID: 008_add_issue_quality_columns
Revises: 007_merge_006_heads
Create Date: 2026-03-28
"""
from alembic import op
import sqlalchemy as sa

revision = "008_add_issue_quality_columns"
down_revision = "007_merge_006_heads"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "issues",
        sa.Column("comment_count", sa.Integer(), nullable=False, server_default="0"),
    )
    op.add_column(
        "issues",
        sa.Column("body_length", sa.Integer(), nullable=False, server_default="0"),
    )
    op.add_column(
        "issues",
        sa.Column(
            "has_checklist", sa.Boolean(), nullable=False, server_default="false"
        ),
    )
    op.add_column(
        "issues",
        sa.Column("state_reason", sa.String(30), nullable=True),
    )
    op.add_column(
        "issues",
        sa.Column("creator_github_username", sa.String(255), nullable=True),
    )
    op.add_column(
        "issues",
        sa.Column("milestone_title", sa.String(255), nullable=True),
    )
    op.add_column(
        "issues",
        sa.Column("milestone_due_on", sa.Date(), nullable=True),
    )
    op.add_column(
        "issues",
        sa.Column("reopen_count", sa.Integer(), nullable=False, server_default="0"),
    )


def downgrade():
    op.drop_column("issues", "reopen_count")
    op.drop_column("issues", "milestone_due_on")
    op.drop_column("issues", "milestone_title")
    op.drop_column("issues", "creator_github_username")
    op.drop_column("issues", "state_reason")
    op.drop_column("issues", "has_checklist")
    op.drop_column("issues", "body_length")
    op.drop_column("issues", "comment_count")
