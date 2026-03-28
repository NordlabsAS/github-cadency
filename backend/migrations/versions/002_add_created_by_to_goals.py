"""Add created_by column to developer_goals table.

Revision ID: 002_add_created_by
Revises: 001_add_app_role
Create Date: 2026-03-28
"""
from alembic import op
import sqlalchemy as sa

revision = "002_add_created_by"
down_revision = "001_add_app_role"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "developer_goals",
        sa.Column("created_by", sa.String(10), nullable=True, server_default="admin"),
    )


def downgrade() -> None:
    op.drop_column("developer_goals", "created_by")
