"""Add teams table and new role definitions (senior_devops, other).

Revision ID: 029
Revises: 028
Create Date: 2026-03-31
"""

from alembic import op
import sqlalchemy as sa

revision = "029"
down_revision = "028"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # --- Teams table ---
    op.create_table(
        "teams",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("name", sa.String(100), nullable=False, unique=True),
        sa.Column("display_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # Seed teams from existing developer.team values
    conn = op.get_bind()
    rows = conn.execute(
        sa.text("SELECT DISTINCT team FROM developers WHERE team IS NOT NULL AND team != ''")
    ).fetchall()
    for i, row in enumerate(rows):
        conn.execute(
            sa.text("INSERT INTO teams (name, display_order) VALUES (:name, :ord)"),
            {"name": row[0], "ord": i + 1},
        )

    # --- New roles: shift display_order for existing roles >= 6, then insert ---
    # Shift QA (6→7), Intern (7→8), PM (8→9), PO (9→10), EM (10→11),
    # Scrum (11→12), Designer (12→13), System (13→14)
    conn.execute(
        sa.text(
            "UPDATE role_definitions SET display_order = display_order + 1 "
            "WHERE display_order >= 6"
        )
    )
    # Insert Senior DevOps Engineer at order 6
    conn.execute(
        sa.text(
            "INSERT INTO role_definitions (role_key, display_name, contribution_category, display_order, is_default) "
            "VALUES ('senior_devops', 'Senior DevOps Engineer', 'code_contributor', 6, true)"
        )
    )
    # Insert Other at the end (order 15 = old 14 shifted + 1)
    conn.execute(
        sa.text(
            "INSERT INTO role_definitions (role_key, display_name, contribution_category, display_order, is_default) "
            "VALUES ('other', 'Other', 'non_contributor', 15, true)"
        )
    )


def downgrade() -> None:
    conn = op.get_bind()
    conn.execute(sa.text("DELETE FROM role_definitions WHERE role_key IN ('senior_devops', 'other')"))
    conn.execute(
        sa.text(
            "UPDATE role_definitions SET display_order = display_order - 1 "
            "WHERE display_order >= 7"
        )
    )
    op.drop_table("teams")
