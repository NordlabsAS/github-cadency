"""Add missing indexes on issue_comments.issue_id and pr_review_comments.pr_id.

Revision ID: 028
Revises: 027
Create Date: 2026-03-30
"""

from alembic import op

revision = "028"
down_revision = "027"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_index("ix_issue_comment_issue_id", "issue_comments", ["issue_id"])
    op.create_index("ix_pr_review_comment_pr_id", "pr_review_comments", ["pr_id"])


def downgrade() -> None:
    op.drop_index("ix_pr_review_comment_pr_id", table_name="pr_review_comments")
    op.drop_index("ix_issue_comment_issue_id", table_name="issue_comments")
