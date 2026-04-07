"""Add planning notification alert toggles and thresholds to notification_config.

Revision ID: 039
Revises: 038
Create Date: 2026-04-07
"""
from alembic import op
import sqlalchemy as sa

revision = "039"
down_revision = "038"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Enable toggles for 6 new alert types
    op.add_column("notification_config", sa.Column("alert_velocity_declining_enabled", sa.Boolean(), server_default="true"))
    op.add_column("notification_config", sa.Column("alert_scope_creep_high_enabled", sa.Boolean(), server_default="true"))
    op.add_column("notification_config", sa.Column("alert_sprint_at_risk_enabled", sa.Boolean(), server_default="true"))
    op.add_column("notification_config", sa.Column("alert_triage_queue_growing_enabled", sa.Boolean(), server_default="true"))
    op.add_column("notification_config", sa.Column("alert_estimation_accuracy_low_enabled", sa.Boolean(), server_default="true"))
    op.add_column("notification_config", sa.Column("alert_linear_sync_failure_enabled", sa.Boolean(), server_default="true"))
    # Configurable thresholds
    op.add_column("notification_config", sa.Column("velocity_decline_pct", sa.Float(), server_default="20.0"))
    op.add_column("notification_config", sa.Column("scope_creep_threshold_pct", sa.Float(), server_default="25.0"))
    op.add_column("notification_config", sa.Column("sprint_risk_completion_pct", sa.Float(), server_default="50.0"))
    op.add_column("notification_config", sa.Column("triage_queue_max", sa.Integer(), server_default="10"))
    op.add_column("notification_config", sa.Column("triage_duration_hours_max", sa.Integer(), server_default="48"))
    op.add_column("notification_config", sa.Column("estimation_accuracy_min_pct", sa.Float(), server_default="60.0"))


def downgrade() -> None:
    op.drop_column("notification_config", "estimation_accuracy_min_pct")
    op.drop_column("notification_config", "triage_duration_hours_max")
    op.drop_column("notification_config", "triage_queue_max")
    op.drop_column("notification_config", "sprint_risk_completion_pct")
    op.drop_column("notification_config", "scope_creep_threshold_pct")
    op.drop_column("notification_config", "velocity_decline_pct")
    op.drop_column("notification_config", "alert_linear_sync_failure_enabled")
    op.drop_column("notification_config", "alert_estimation_accuracy_low_enabled")
    op.drop_column("notification_config", "alert_triage_queue_growing_enabled")
    op.drop_column("notification_config", "alert_sprint_at_risk_enabled")
    op.drop_column("notification_config", "alert_scope_creep_high_enabled")
    op.drop_column("notification_config", "alert_velocity_declining_enabled")
