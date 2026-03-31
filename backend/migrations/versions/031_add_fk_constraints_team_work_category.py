"""Add FK constraints: developers.team -> teams.name, work_category -> work_categories.

Revision ID: 031
Revises: 030
Create Date: 2026-03-31
"""
from alembic import op
import sqlalchemy as sa

revision = "031"
down_revision = "030"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Widen work_category_source from VARCHAR(20) to VARCHAR(50) to match ORM
    op.alter_column("pull_requests", "work_category_source",
                    type_=sa.String(50), existing_type=sa.String(20))
    op.alter_column("issues", "work_category_source",
                    type_=sa.String(50), existing_type=sa.String(20))

    # Clean up empty string team values before adding FK
    op.execute("UPDATE developers SET team = NULL WHERE team = ''")

    # Auto-create any missing teams from existing developer.team values
    op.execute(
        "INSERT INTO teams (name) "
        "SELECT DISTINCT team FROM developers "
        "WHERE team IS NOT NULL AND team != '' "
        "AND team NOT IN (SELECT name FROM teams) "
        "ON CONFLICT DO NOTHING"
    )

    # Clean up empty string work_category values before adding FKs
    op.execute("UPDATE pull_requests SET work_category = NULL WHERE work_category = ''")
    op.execute("UPDATE issues SET work_category = NULL WHERE work_category = ''")

    # FK: developers.team -> teams.name (CASCADE on rename, SET NULL on delete)
    op.create_foreign_key(
        "fk_developers_team_teams_name",
        "developers", "teams",
        ["team"], ["name"],
        onupdate="CASCADE",
        ondelete="SET NULL",
    )

    # FK: pull_requests.work_category -> work_categories.category_key (SET NULL on delete)
    op.create_foreign_key(
        "fk_pull_requests_work_category",
        "pull_requests", "work_categories",
        ["work_category"], ["category_key"],
        ondelete="SET NULL",
    )

    # FK: issues.work_category -> work_categories.category_key (SET NULL on delete)
    op.create_foreign_key(
        "fk_issues_work_category",
        "issues", "work_categories",
        ["work_category"], ["category_key"],
        ondelete="SET NULL",
    )


def downgrade() -> None:
    op.drop_constraint("fk_issues_work_category", "issues", type_="foreignkey")
    op.drop_constraint("fk_pull_requests_work_category", "pull_requests", type_="foreignkey")
    op.drop_constraint("fk_developers_team_teams_name", "developers", type_="foreignkey")

    op.alter_column("issues", "work_category_source",
                    type_=sa.String(20), existing_type=sa.String(50))
    op.alter_column("pull_requests", "work_category_source",
                    type_=sa.String(20), existing_type=sa.String(50))
