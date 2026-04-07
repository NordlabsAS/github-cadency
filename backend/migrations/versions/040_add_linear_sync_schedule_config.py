"""Add linear_sync_enabled and linear_sync_interval_minutes to sync_schedule_config.

Revision ID: 040
Revises: 039
Create Date: 2026-04-07
"""
from alembic import op
import sqlalchemy as sa

revision = "040"
down_revision = "039"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("sync_schedule_config", sa.Column("linear_sync_enabled", sa.Boolean(), server_default="true"))
    op.add_column("sync_schedule_config", sa.Column("linear_sync_interval_minutes", sa.Integer(), server_default="120"))


def downgrade() -> None:
    op.drop_column("sync_schedule_config", "linear_sync_interval_minutes")
    op.drop_column("sync_schedule_config", "linear_sync_enabled")
