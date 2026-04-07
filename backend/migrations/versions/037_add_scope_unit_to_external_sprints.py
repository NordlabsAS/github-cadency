"""Add scope_unit column to external_sprints for tracking whether scope
metrics use points or issue counts.

Revision ID: 037
Revises: 036
Create Date: 2026-04-07
"""
from alembic import op
import sqlalchemy as sa

revision = "037"
down_revision = "036"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "external_sprints",
        sa.Column("scope_unit", sa.String(20), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("external_sprints", "scope_unit")
