import re

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.models import Developer, Team
from app.schemas.schemas import TeamCreate, TeamUpdate

TEAM_NAME_PATTERN = re.compile(r"^[a-zA-Z0-9][a-zA-Z0-9 ]{0,98}[a-zA-Z0-9]$")


def _validate_team_name(name: str) -> None:
    """Validate team name: letters, numbers, spaces; 2-100 chars; no leading/trailing spaces."""
    name = name.strip()
    if len(name) < 2:
        raise ValueError("Team name must be at least 2 characters")
    if not TEAM_NAME_PATTERN.match(name):
        raise ValueError(
            "Team name must contain only letters, numbers, and spaces, "
            "and cannot start or end with a space"
        )


async def get_all_teams(db: AsyncSession) -> list[Team]:
    """Return all teams ordered by display_order."""
    result = await db.execute(
        select(Team).order_by(Team.display_order, Team.name)
    )
    return list(result.scalars().all())


async def create_team(db: AsyncSession, data: TeamCreate) -> Team:
    """Create a new team."""
    name = data.name.strip()
    _validate_team_name(name)

    existing = await db.execute(
        select(Team).where(func.lower(Team.name) == name.lower())
    )
    if existing.scalar_one_or_none():
        raise ValueError(f"Team '{name}' already exists")

    max_order = await db.scalar(select(func.max(Team.display_order)))
    team = Team(name=name, display_order=(max_order or 0) + 1)
    db.add(team)
    await db.commit()
    await db.refresh(team)
    return team


async def update_team(db: AsyncSession, team_id: int, data: TeamUpdate) -> Team:
    """Update a team's name or display_order."""
    team = await db.get(Team, team_id)
    if not team:
        raise ValueError(f"Team with id {team_id} not found")

    if data.name is not None:
        name = data.name.strip()
        _validate_team_name(name)

        # Check uniqueness (excluding self)
        existing = await db.execute(
            select(Team).where(
                func.lower(Team.name) == name.lower(),
                Team.id != team_id,
            )
        )
        if existing.scalar_one_or_none():
            raise ValueError(f"Team '{name}' already exists")

        old_name = team.name
        team.name = name

        # Update all developers with the old team name
        if old_name != name:
            result = await db.execute(
                select(Developer).where(Developer.team == old_name)
            )
            for dev in result.scalars().all():
                dev.team = name

    if data.display_order is not None:
        team.display_order = data.display_order

    await db.commit()
    await db.refresh(team)
    return team


async def delete_team(db: AsyncSession, team_id: int) -> None:
    """Delete a team. Rejects if developers are still assigned."""
    team = await db.get(Team, team_id)
    if not team:
        raise ValueError(f"Team with id {team_id} not found")

    in_use = await db.scalar(
        select(func.count()).select_from(Developer).where(
            Developer.team == team.name,
        )
    )
    if in_use:
        raise ValueError(
            f"Cannot delete team '{team.name}': {in_use} developer(s) still assigned"
        )

    await db.execute(delete(Team).where(Team.id == team_id))
    await db.commit()


async def resolve_team(db: AsyncSession, team_name: str | None) -> str | None:
    """Resolve a team name: find existing (case-insensitive) or create new.

    Returns the canonical team name (from the teams table) or None.
    """
    if not team_name or not team_name.strip():
        return None

    name = team_name.strip()

    # Try to find existing team (case-insensitive)
    result = await db.execute(
        select(Team).where(func.lower(Team.name) == name.lower())
    )
    existing = result.scalar_one_or_none()
    if existing:
        return existing.name

    # Auto-create the team
    _validate_team_name(name)
    max_order = await db.scalar(select(func.max(Team.display_order)))
    team = Team(name=name, display_order=(max_order or 0) + 1)
    db.add(team)
    await db.flush()
    return team.name
