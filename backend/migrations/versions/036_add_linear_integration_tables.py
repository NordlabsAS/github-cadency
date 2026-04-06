"""Add Linear integration tables: integration_config, external_projects, external_sprints,
external_issues, developer_identity_map, pr_external_issue_links.

Revision ID: 036
Revises: 035
Create Date: 2026-04-06
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

revision = "036"
down_revision = "035"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # --- integration_config ---
    op.create_table(
        "integration_config",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("type", sa.String(30), nullable=False),
        sa.Column("display_name", sa.String(255), nullable=True),
        sa.Column("api_key", sa.Text(), nullable=True),
        sa.Column("workspace_id", sa.String(255), nullable=True),
        sa.Column("workspace_name", sa.String(255), nullable=True),
        sa.Column("config", JSONB(), nullable=True),
        sa.Column("status", sa.String(30), nullable=False, server_default="active"),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("is_primary_issue_source", sa.Boolean(), server_default="false"),
        sa.Column("last_synced_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_integration_config_type", "integration_config", ["type"])

    # --- external_projects ---
    op.create_table(
        "external_projects",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("integration_id", sa.Integer(), sa.ForeignKey("integration_config.id", ondelete="CASCADE"), nullable=False),
        sa.Column("external_id", sa.String(255), nullable=False),
        sa.Column("key", sa.String(50), nullable=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("status", sa.String(30), nullable=True),
        sa.Column("health", sa.String(30), nullable=True),
        sa.Column("start_date", sa.Date(), nullable=True),
        sa.Column("target_date", sa.Date(), nullable=True),
        sa.Column("progress_pct", sa.Float(), nullable=True),
        sa.Column("lead_id", sa.Integer(), sa.ForeignKey("developers.id", ondelete="SET NULL"), nullable=True),
        sa.Column("url", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_external_projects_integration", "external_projects", ["integration_id"])
    op.create_unique_constraint("uq_external_projects_ext_id", "external_projects", ["external_id"])

    # --- external_sprints ---
    op.create_table(
        "external_sprints",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("integration_id", sa.Integer(), sa.ForeignKey("integration_config.id", ondelete="CASCADE"), nullable=False),
        sa.Column("external_id", sa.String(255), nullable=False),
        sa.Column("name", sa.String(255), nullable=True),
        sa.Column("number", sa.Integer(), nullable=True),
        sa.Column("team_key", sa.String(100), nullable=True),
        sa.Column("team_name", sa.String(255), nullable=True),
        sa.Column("state", sa.String(30), nullable=False),
        sa.Column("start_date", sa.Date(), nullable=True),
        sa.Column("end_date", sa.Date(), nullable=True),
        sa.Column("planned_scope", sa.Integer(), nullable=True),
        sa.Column("completed_scope", sa.Integer(), nullable=True),
        sa.Column("cancelled_scope", sa.Integer(), nullable=True),
        sa.Column("added_scope", sa.Integer(), nullable=True),
        sa.Column("url", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_external_sprints_integration", "external_sprints", ["integration_id"])
    op.create_index("ix_external_sprints_state", "external_sprints", ["state"])
    op.create_unique_constraint("uq_external_sprints_ext_id", "external_sprints", ["external_id"])

    # --- external_issues ---
    op.create_table(
        "external_issues",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("integration_id", sa.Integer(), sa.ForeignKey("integration_config.id", ondelete="CASCADE"), nullable=False),
        sa.Column("external_id", sa.String(255), nullable=False),
        sa.Column("identifier", sa.String(50), nullable=False),
        sa.Column("title", sa.String(500), nullable=False),
        sa.Column("description_length", sa.Integer(), nullable=True),
        sa.Column("issue_type", sa.String(30), nullable=True),
        sa.Column("status", sa.String(100), nullable=True),
        sa.Column("status_category", sa.String(30), nullable=True),
        sa.Column("priority", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("priority_label", sa.String(30), nullable=True),
        sa.Column("estimate", sa.Float(), nullable=True),
        sa.Column("assignee_email", sa.String(320), nullable=True),
        sa.Column("assignee_developer_id", sa.Integer(), sa.ForeignKey("developers.id", ondelete="SET NULL"), nullable=True),
        sa.Column("project_id", sa.Integer(), sa.ForeignKey("external_projects.id", ondelete="SET NULL"), nullable=True),
        sa.Column("sprint_id", sa.Integer(), sa.ForeignKey("external_sprints.id", ondelete="SET NULL"), nullable=True),
        sa.Column("parent_issue_id", sa.Integer(), sa.ForeignKey("external_issues.id", ondelete="SET NULL"), nullable=True),
        sa.Column("labels", JSONB(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("cancelled_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("triage_duration_s", sa.Integer(), nullable=True),
        sa.Column("cycle_time_s", sa.Integer(), nullable=True),
        sa.Column("url", sa.Text(), nullable=True),
    )
    op.create_index("ix_external_issues_integration", "external_issues", ["integration_id"])
    op.create_index("ix_external_issues_identifier", "external_issues", ["identifier"])
    op.create_index("ix_external_issues_sprint", "external_issues", ["sprint_id"])
    op.create_index("ix_external_issues_project", "external_issues", ["project_id"])
    op.create_index("ix_external_issues_assignee", "external_issues", ["assignee_developer_id"])
    op.create_index("ix_external_issues_status_category", "external_issues", ["status_category"])
    op.create_unique_constraint("uq_external_issues_ext_id", "external_issues", ["external_id"])

    # --- developer_identity_map ---
    op.create_table(
        "developer_identity_map",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("developer_id", sa.Integer(), sa.ForeignKey("developers.id", ondelete="CASCADE"), nullable=False),
        sa.Column("integration_type", sa.String(30), nullable=False),
        sa.Column("external_user_id", sa.String(255), nullable=False),
        sa.Column("external_email", sa.String(320), nullable=True),
        sa.Column("external_display_name", sa.String(255), nullable=True),
        sa.Column("mapped_by", sa.String(20), nullable=False, server_default="auto"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_unique_constraint("uq_dev_identity_map", "developer_identity_map", ["developer_id", "integration_type"])
    op.create_index("ix_dev_identity_map_ext_email", "developer_identity_map", ["external_email"])

    # --- pr_external_issue_links ---
    op.create_table(
        "pr_external_issue_links",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("pull_request_id", sa.Integer(), sa.ForeignKey("pull_requests.id", ondelete="CASCADE"), nullable=False),
        sa.Column("external_issue_id", sa.Integer(), sa.ForeignKey("external_issues.id", ondelete="CASCADE"), nullable=False),
        sa.Column("link_source", sa.String(30), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_unique_constraint("uq_pr_ext_issue_link", "pr_external_issue_links", ["pull_request_id", "external_issue_id"])
    op.create_index("ix_pr_ext_issue_links_pr", "pr_external_issue_links", ["pull_request_id"])
    op.create_index("ix_pr_ext_issue_links_issue", "pr_external_issue_links", ["external_issue_id"])


def downgrade() -> None:
    op.drop_table("pr_external_issue_links")
    op.drop_table("developer_identity_map")
    op.drop_table("external_issues")
    op.drop_table("external_sprints")
    op.drop_table("external_projects")
    op.drop_table("integration_config")
