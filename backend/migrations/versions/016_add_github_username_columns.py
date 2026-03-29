"""Add github username columns for author/reviewer/assignee backfill

Stores raw GitHub usernames on PRs, reviews, and issues so that
author/reviewer/assignee links can be efficiently backfilled when
new developers are synced from GitHub.

Revision ID: 016_add_github_username_columns
Revises: 015_add_sync_resumability
Create Date: 2026-03-29
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "016_add_github_username_columns"
down_revision: Union[str, None] = "015_add_sync_resumability"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "pull_requests",
        sa.Column("author_github_username", sa.String(255), nullable=True),
    )
    op.add_column(
        "pr_reviews",
        sa.Column("reviewer_github_username", sa.String(255), nullable=True),
    )
    op.add_column(
        "issues",
        sa.Column("assignee_github_username", sa.String(255), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("issues", "assignee_github_username")
    op.drop_column("pr_reviews", "reviewer_github_username")
    op.drop_column("pull_requests", "author_github_username")
