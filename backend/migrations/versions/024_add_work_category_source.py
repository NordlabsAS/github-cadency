"""Add work_category_source column to pull_requests and issues.

Tracks provenance of work category: label, title, ai, manual, cross_ref.
Manual overrides are authoritative and never overwritten by re-classification.

Revision ID: 024
Revises: 023
Create Date: 2026-03-30
"""

from alembic import op
import sqlalchemy as sa

revision = "024"
down_revision = "023"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("pull_requests", sa.Column("work_category_source", sa.String(20), nullable=True))
    op.add_column("issues", sa.Column("work_category_source", sa.String(20), nullable=True))


def downgrade() -> None:
    op.drop_column("issues", "work_category_source")
    op.drop_column("pull_requests", "work_category_source")
