"""Add creator_email, creator_developer_id, work_category, work_category_source
to external_issues for primary issue source branching.

Revision ID: 038
Revises: 037
Create Date: 2026-04-07
"""
from alembic import op
import sqlalchemy as sa

revision = "038"
down_revision = "037"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("external_issues", sa.Column("creator_email", sa.String(320), nullable=True))
    op.add_column(
        "external_issues",
        sa.Column(
            "creator_developer_id",
            sa.Integer(),
            sa.ForeignKey("developers.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )
    op.add_column("external_issues", sa.Column("work_category", sa.String(50), nullable=True))
    op.add_column("external_issues", sa.Column("work_category_source", sa.String(20), nullable=True))
    op.create_index("ix_external_issues_creator", "external_issues", ["creator_developer_id"])


def downgrade() -> None:
    op.drop_index("ix_external_issues_creator", table_name="external_issues")
    op.drop_column("external_issues", "work_category_source")
    op.drop_column("external_issues", "work_category")
    op.drop_column("external_issues", "creator_developer_id")
    op.drop_column("external_issues", "creator_email")
