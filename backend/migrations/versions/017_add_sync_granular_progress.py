"""Add granular progress and cancellation columns to sync_events

Adds current_step, current_repo_prs_total/done, current_repo_issues_total/done,
and cancel_requested columns that were missing from migration 015.

Revision ID: 017_add_sync_granular_progress
Revises: 016_add_github_username_columns
Create Date: 2026-03-29
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "017_add_sync_granular_progress"
down_revision: Union[str, None] = "016_add_github_username_columns"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("sync_events", sa.Column("current_step", sa.String(50), nullable=True))
    op.add_column("sync_events", sa.Column("current_repo_prs_total", sa.Integer(), nullable=True))
    op.add_column("sync_events", sa.Column("current_repo_prs_done", sa.Integer(), nullable=True))
    op.add_column("sync_events", sa.Column("current_repo_issues_total", sa.Integer(), nullable=True))
    op.add_column("sync_events", sa.Column("current_repo_issues_done", sa.Integer(), nullable=True))
    op.add_column("sync_events", sa.Column("cancel_requested", sa.Boolean(), server_default="false", nullable=False))


def downgrade() -> None:
    op.drop_column("sync_events", "cancel_requested")
    op.drop_column("sync_events", "current_repo_issues_done")
    op.drop_column("sync_events", "current_repo_issues_total")
    op.drop_column("sync_events", "current_repo_prs_done")
    op.drop_column("sync_events", "current_repo_prs_total")
    op.drop_column("sync_events", "current_step")
