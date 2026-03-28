"""Add pr_files and repo_tree_files tables, default_branch to repositories.

Revision ID: 009_add_pr_files_and_repo_tree
Revises: 008_add_issue_quality_columns
Create Date: 2026-03-28
"""

from alembic import op
import sqlalchemy as sa

revision = "009_add_pr_files_and_repo_tree"
down_revision = "008_add_issue_quality_columns"
branch_labels = None
depends_on = None


def upgrade():
    # Add default_branch and tree_truncated to repositories
    op.add_column(
        "repositories", sa.Column("default_branch", sa.String(255), nullable=True)
    )
    op.add_column(
        "repositories",
        sa.Column(
            "tree_truncated", sa.Boolean(), server_default="false", nullable=False
        ),
    )

    # Create pr_files table
    op.create_table(
        "pr_files",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "pr_id",
            sa.Integer(),
            sa.ForeignKey("pull_requests.id"),
            nullable=False,
        ),
        sa.Column("filename", sa.Text(), nullable=False),
        sa.Column("additions", sa.Integer(), server_default="0"),
        sa.Column("deletions", sa.Integer(), server_default="0"),
        sa.Column("status", sa.String(20), nullable=True),
        sa.Column("previous_filename", sa.Text(), nullable=True),
        sa.UniqueConstraint("pr_id", "filename", name="uq_pr_file_pr_filename"),
    )
    op.create_index("ix_pr_file_pr_id", "pr_files", ["pr_id"])
    op.create_index("ix_pr_file_filename", "pr_files", ["filename"])

    # Create repo_tree_files table
    op.create_table(
        "repo_tree_files",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "repo_id",
            sa.Integer(),
            sa.ForeignKey("repositories.id"),
            nullable=False,
        ),
        sa.Column("path", sa.Text(), nullable=False),
        sa.Column("type", sa.String(10), nullable=False),
        sa.Column(
            "last_synced_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
        sa.UniqueConstraint("repo_id", "path", name="uq_repo_tree_file_repo_path"),
    )
    op.create_index("ix_repo_tree_file_repo_id", "repo_tree_files", ["repo_id"])


def downgrade():
    op.drop_index("ix_repo_tree_file_repo_id", table_name="repo_tree_files")
    op.drop_table("repo_tree_files")
    op.drop_index("ix_pr_file_filename", table_name="pr_files")
    op.drop_index("ix_pr_file_pr_id", table_name="pr_files")
    op.drop_table("pr_files")
    op.drop_column("repositories", "tree_truncated")
    op.drop_column("repositories", "default_branch")
