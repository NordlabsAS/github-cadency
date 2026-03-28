"""Merge 006 branch heads.

Revision ID: 007_merge_006_heads
Revises: 006_add_pr_metadata, 006_add_revert_columns
Create Date: 2026-03-28
"""

revision = "007_merge_006_heads"
down_revision = ("006_add_pr_metadata", "006_add_revert_columns")
branch_labels = None
depends_on = None


def upgrade():
    pass


def downgrade():
    pass
