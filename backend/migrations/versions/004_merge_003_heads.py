"""Merge 003 branch heads.

Revision ID: 004_merge_003_heads
Revises: 003_add_approval_columns, 003_add_review_round_count
Create Date: 2026-03-28
"""

revision = "004_merge_003_heads"
down_revision = ("003_add_approval_columns", "003_add_review_round_count")
branch_labels = None
depends_on = None


def upgrade():
    pass


def downgrade():
    pass
