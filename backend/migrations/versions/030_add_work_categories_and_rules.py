"""Add configurable work categories and classification rules.

Revision ID: 030
Revises: 029
Create Date: 2026-03-31
"""
from alembic import op
import sqlalchemy as sa

revision = "030"
down_revision = "029"
branch_labels = None
depends_on = None

# Seed data: default categories (matching current hardcoded set)
DEFAULT_CATEGORIES = [
    ("feature", "Feature", "#3b82f6", False, 1),
    ("bugfix", "Bug Fix", "#ef4444", False, 2),
    ("tech_debt", "Tech Debt", "#f59e0b", False, 3),
    ("ops", "Ops", "#22c55e", False, 4),
    ("unknown", "Unknown", "#94a3b8", False, 5),
]

# Seed data: label rules (from LABEL_CATEGORY_MAP)
LABEL_RULES = [
    # Feature labels
    ("feature", "feature", 1),
    ("enhancement", "feature", 2),
    ("feat", "feature", 3),
    ("new feature", "feature", 4),
    ("story", "feature", 5),
    # Bugfix labels
    ("bug", "bugfix", 10),
    ("bugfix", "bugfix", 11),
    ("fix", "bugfix", 12),
    ("defect", "bugfix", 13),
    ("hotfix", "bugfix", 14),
    ("regression", "bugfix", 15),
    # Tech debt labels
    ("tech-debt", "tech_debt", 20),
    ("tech debt", "tech_debt", 21),
    ("refactor", "tech_debt", 22),
    ("refactoring", "tech_debt", 23),
    ("cleanup", "tech_debt", 24),
    ("chore", "tech_debt", 25),
    ("dependencies", "tech_debt", 26),
    ("dependency", "tech_debt", 27),
    ("deps", "tech_debt", 28),
    # Ops labels
    ("ops", "ops", 30),
    ("infrastructure", "ops", 31),
    ("infra", "ops", 32),
    ("ci", "ops", 33),
    ("ci/cd", "ops", 34),
    ("deploy", "ops", 35),
    ("deployment", "ops", 36),
    ("devops", "ops", 37),
    ("monitoring", "ops", 38),
    ("config", "ops", 39),
    ("documentation", "ops", 40),
    ("docs", "ops", 41),
]

# Seed data: title regex rules (from TITLE_PATTERNS)
TITLE_REGEX_RULES = [
    (r"\bfix(?:es|ed)?\b|\bbug\b|\bhotfix\b|\bregression\b", "bugfix", 100),
    (r"\bfeat(?:ure)?\b|\badd(?:s|ed)?\s", "feature", 101),
    (r"\brefactor\b|\bcleanup\b|\btech.?debt\b|\bchore\b|\bdeps?\b|\bbump\b", "tech_debt", 102),
    (r"\bci\b|\bcd\b|\bdeploy\b|\binfra\b|\bconfig\b|\bdocs?\b|\bmonitoring\b", "ops", 103),
]


def upgrade() -> None:
    # Create work_categories table
    op.create_table(
        "work_categories",
        sa.Column("category_key", sa.String(50), primary_key=True),
        sa.Column("display_name", sa.String(100), nullable=False),
        sa.Column("color", sa.String(7), nullable=False),
        sa.Column("exclude_from_stats", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("display_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("is_default", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # Create work_category_rules table
    op.create_table(
        "work_category_rules",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("match_type", sa.String(20), nullable=False),
        sa.Column("match_value", sa.String(255), nullable=False),
        sa.Column("case_sensitive", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("category_key", sa.String(50), sa.ForeignKey("work_categories.category_key"), nullable=False),
        sa.Column("priority", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_work_category_rules_priority", "work_category_rules", ["priority"])

    # Seed default categories
    categories_table = sa.table(
        "work_categories",
        sa.column("category_key", sa.String),
        sa.column("display_name", sa.String),
        sa.column("color", sa.String),
        sa.column("exclude_from_stats", sa.Boolean),
        sa.column("display_order", sa.Integer),
        sa.column("is_default", sa.Boolean),
    )
    op.bulk_insert(categories_table, [
        {
            "category_key": key,
            "display_name": name,
            "color": color,
            "exclude_from_stats": excluded,
            "display_order": order,
            "is_default": True,
        }
        for key, name, color, excluded, order in DEFAULT_CATEGORIES
    ])

    # Seed label rules
    rules_table = sa.table(
        "work_category_rules",
        sa.column("match_type", sa.String),
        sa.column("match_value", sa.String),
        sa.column("case_sensitive", sa.Boolean),
        sa.column("category_key", sa.String),
        sa.column("priority", sa.Integer),
    )
    op.bulk_insert(rules_table, [
        {
            "match_type": "label",
            "match_value": value,
            "case_sensitive": False,
            "category_key": cat,
            "priority": priority,
        }
        for value, cat, priority in LABEL_RULES
    ])

    # Seed title regex rules
    op.bulk_insert(rules_table, [
        {
            "match_type": "title_regex",
            "match_value": pattern,
            "case_sensitive": False,
            "category_key": cat,
            "priority": priority,
        }
        for pattern, cat, priority in TITLE_REGEX_RULES
    ])

    # Widen work_category columns from String(20) to String(50)
    with op.batch_alter_table("pull_requests") as batch_op:
        batch_op.alter_column("work_category", type_=sa.String(50), existing_type=sa.String(20))
    with op.batch_alter_table("issues") as batch_op:
        batch_op.alter_column("work_category", type_=sa.String(50), existing_type=sa.String(20))


def downgrade() -> None:
    with op.batch_alter_table("issues") as batch_op:
        batch_op.alter_column("work_category", type_=sa.String(20), existing_type=sa.String(50))
    with op.batch_alter_table("pull_requests") as batch_op:
        batch_op.alter_column("work_category", type_=sa.String(20), existing_type=sa.String(50))
    op.drop_table("work_category_rules")
    op.drop_table("work_categories")
