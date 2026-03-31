"""Add role_definitions table and issues.creator_id FK.

Revision ID: 027
Revises: 026
Create Date: 2026-03-30
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

revision = "027"
down_revision = "026"
branch_labels = None
depends_on = None

DEFAULT_ROLES = [
    {"role_key": "developer", "display_name": "Developer", "contribution_category": "code_contributor", "display_order": 1, "is_default": True},
    {"role_key": "senior_developer", "display_name": "Senior Developer", "contribution_category": "code_contributor", "display_order": 2, "is_default": True},
    {"role_key": "lead", "display_name": "Engineering Lead", "contribution_category": "code_contributor", "display_order": 3, "is_default": True},
    {"role_key": "architect", "display_name": "Architect", "contribution_category": "code_contributor", "display_order": 4, "is_default": True},
    {"role_key": "devops", "display_name": "DevOps Engineer", "contribution_category": "code_contributor", "display_order": 5, "is_default": True},
    {"role_key": "qa", "display_name": "QA Engineer", "contribution_category": "code_contributor", "display_order": 6, "is_default": True},
    {"role_key": "intern", "display_name": "Intern", "contribution_category": "code_contributor", "display_order": 7, "is_default": True},
    {"role_key": "product_manager", "display_name": "Product Manager", "contribution_category": "issue_contributor", "display_order": 8, "is_default": True},
    {"role_key": "product_owner", "display_name": "Product Owner", "contribution_category": "issue_contributor", "display_order": 9, "is_default": True},
    {"role_key": "engineering_manager", "display_name": "Engineering Manager", "contribution_category": "issue_contributor", "display_order": 10, "is_default": True},
    {"role_key": "scrum_master", "display_name": "Scrum Master", "contribution_category": "issue_contributor", "display_order": 11, "is_default": True},
    {"role_key": "designer", "display_name": "Designer", "contribution_category": "non_contributor", "display_order": 12, "is_default": True},
    {"role_key": "system_account", "display_name": "System Account", "contribution_category": "system", "display_order": 13, "is_default": True},
]


def upgrade() -> None:
    table = op.create_table(
        "role_definitions",
        sa.Column("role_key", sa.String(50), primary_key=True),
        sa.Column("display_name", sa.String(100), nullable=False),
        sa.Column("contribution_category", sa.String(30), nullable=False),
        sa.Column("display_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("is_default", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.bulk_insert(table, DEFAULT_ROLES)

    op.add_column("issues", sa.Column("creator_id", sa.Integer(), sa.ForeignKey("developers.id"), nullable=True))
    op.create_index("ix_issue_creator_id", "issues", ["creator_id"])


def downgrade() -> None:
    op.drop_index("ix_issue_creator_id", table_name="issues")
    op.drop_column("issues", "creator_id")
    op.drop_table("role_definitions")
