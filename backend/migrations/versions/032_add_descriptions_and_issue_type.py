"""Add description to work_categories/rules, issue_type to issues, issue_type match type.

Revision ID: 032
Revises: 031
Create Date: 2026-03-31
"""
from alembic import op
import sqlalchemy as sa

revision = "032"
down_revision = "031"
branch_labels = None
depends_on = None

# Default descriptions for built-in categories
CATEGORY_DESCRIPTIONS = {
    "feature": "New functionality or enhancements that add user-facing value.",
    "bugfix": "Fixes for defects, regressions, or incorrect behavior.",
    "tech_debt": "Refactoring, dependency updates, code cleanup, and internal improvements.",
    "ops": "Infrastructure, CI/CD, deployment, monitoring, and documentation changes.",
    "unknown": "Items that could not be automatically classified by any rule. Review and recategorize, or add rules to match them.",
}


def upgrade() -> None:
    # Add description to work_categories
    op.add_column("work_categories", sa.Column("description", sa.Text(), nullable=True))

    # Add description to work_category_rules
    op.add_column("work_category_rules", sa.Column("description", sa.Text(), nullable=True))

    # Widen match_type from VARCHAR(20) to VARCHAR(30) to accommodate "issue_type"
    op.alter_column(
        "work_category_rules", "match_type",
        type_=sa.String(30), existing_type=sa.String(20),
    )

    # Add issue_type to issues
    op.add_column("issues", sa.Column("issue_type", sa.String(100), nullable=True))

    # Seed default category descriptions
    for key, desc in CATEGORY_DESCRIPTIONS.items():
        op.execute(
            sa.text(
                "UPDATE work_categories SET description = :desc WHERE category_key = :key"
            ).bindparams(desc=desc, key=key)
        )


def downgrade() -> None:
    op.drop_column("issues", "issue_type")
    op.alter_column(
        "work_category_rules", "match_type",
        type_=sa.String(20), existing_type=sa.String(30),
    )
    op.drop_column("work_category_rules", "description")
    op.drop_column("work_categories", "description")
