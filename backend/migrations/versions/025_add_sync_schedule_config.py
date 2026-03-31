"""Add sync_schedule_config singleton table.

Revision ID: 025
Revises: 024
Create Date: 2026-03-30
"""

from alembic import op
import sqlalchemy as sa

revision = "025"
down_revision = "024"
branch_labels = None
depends_on = None


def upgrade() -> None:
    table = op.create_table(
        "sync_schedule_config",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("auto_sync_enabled", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("incremental_interval_minutes", sa.Integer(), nullable=False, server_default="15"),
        sa.Column("full_sync_cron_hour", sa.Integer(), nullable=False, server_default="2"),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    # Seed singleton row
    op.bulk_insert(table, [{"id": 1}])


def downgrade() -> None:
    op.drop_table("sync_schedule_config")
