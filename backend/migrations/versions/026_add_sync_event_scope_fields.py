"""Add triggered_by and sync_scope columns to sync_events.

Revision ID: 026
Revises: 025
Create Date: 2026-03-30
"""

from alembic import op
import sqlalchemy as sa

revision = "026"
down_revision = "025"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("sync_events", sa.Column("triggered_by", sa.String(50), nullable=True))
    op.add_column("sync_events", sa.Column("sync_scope", sa.String(255), nullable=True))


def downgrade() -> None:
    op.drop_column("sync_events", "sync_scope")
    op.drop_column("sync_events", "triggered_by")
