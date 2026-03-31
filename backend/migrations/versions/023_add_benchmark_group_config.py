"""Add benchmark_group_config table with default peer groups.

Revision ID: 023
Revises: 022
Create Date: 2026-03-30
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

revision = "023"
down_revision = "022"
branch_labels = None
depends_on = None

DEFAULT_GROUPS = [
    {
        "group_key": "ics",
        "display_name": "IC Engineers",
        "display_order": 1,
        "roles": ["developer", "senior_developer", "architect", "intern"],
        "metrics": [
            "prs_merged", "time_to_merge_h", "time_to_first_review_h",
            "time_to_approve_h", "time_after_approve_h",
            "additions_per_pr", "review_rounds",
        ],
        "min_team_size": 3,
        "is_default": True,
    },
    {
        "group_key": "leads",
        "display_name": "Engineering Leads",
        "display_order": 2,
        "roles": ["lead"],
        "metrics": [
            "time_to_first_review_h", "reviews_given",
            "review_turnaround_h", "review_quality_score",
        ],
        "min_team_size": 3,
        "is_default": True,
    },
    {
        "group_key": "devops",
        "display_name": "DevOps",
        "display_order": 3,
        "roles": ["devops"],
        "metrics": [
            "prs_merged", "time_to_merge_h",
        ],
        "min_team_size": 3,
        "is_default": True,
    },
    {
        "group_key": "qa",
        "display_name": "QA Engineers",
        "display_order": 4,
        "roles": ["qa"],
        "metrics": [
            "reviews_given", "review_turnaround_h", "review_quality_score",
            "changes_requested_rate", "blocker_catch_rate",
            "issues_closed", "prs_merged_bugfix",
        ],
        "min_team_size": 3,
        "is_default": True,
    },
]


def upgrade() -> None:
    table = op.create_table(
        "benchmark_group_config",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("group_key", sa.String(50), unique=True, nullable=False),
        sa.Column("display_name", sa.String(100), nullable=False),
        sa.Column("display_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("roles", JSONB(), nullable=False),
        sa.Column("metrics", JSONB(), nullable=False),
        sa.Column("min_team_size", sa.Integer(), nullable=False, server_default="3"),
        sa.Column("is_default", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.bulk_insert(table, DEFAULT_GROUPS)


def downgrade() -> None:
    op.drop_table("benchmark_group_config")
