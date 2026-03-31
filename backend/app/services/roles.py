import re

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.models import Developer, RoleDefinition
from app.schemas.schemas import ContributionCategory, RoleCreate, RoleUpdate


async def get_all_roles(db: AsyncSession) -> list[RoleDefinition]:
    """Return all role definitions ordered by display_order."""
    result = await db.execute(
        select(RoleDefinition).order_by(RoleDefinition.display_order)
    )
    return list(result.scalars().all())


async def get_role_category_map(db: AsyncSession) -> dict[str, str]:
    """Return a mapping of role_key -> contribution_category for all roles."""
    result = await db.execute(
        select(RoleDefinition.role_key, RoleDefinition.contribution_category)
    )
    return {row.role_key: row.contribution_category for row in result.all()}


async def get_roles_by_category(
    db: AsyncSession, category: ContributionCategory,
) -> list[str]:
    """Return role_keys belonging to a given contribution category."""
    result = await db.execute(
        select(RoleDefinition.role_key).where(
            RoleDefinition.contribution_category == category.value,
        )
    )
    return [row[0] for row in result.all()]


async def validate_role_key(db: AsyncSession, role_key: str) -> bool:
    """Check if a role_key exists in role_definitions."""
    result = await db.scalar(
        select(func.count()).select_from(RoleDefinition).where(
            RoleDefinition.role_key == role_key,
        )
    )
    return (result or 0) > 0


async def create_role(db: AsyncSession, data: RoleCreate) -> RoleDefinition:
    """Create a new custom role definition."""
    if not re.match(r"^[a-z][a-z0-9_]{1,48}$", data.role_key):
        raise ValueError(
            "role_key must be lowercase alphanumeric with underscores, 2-49 chars, starting with a letter"
        )

    existing = await db.get(RoleDefinition, data.role_key)
    if existing:
        raise ValueError(f"Role '{data.role_key}' already exists")

    max_order = await db.scalar(
        select(func.max(RoleDefinition.display_order))
    )

    role = RoleDefinition(
        role_key=data.role_key,
        display_name=data.display_name,
        contribution_category=data.contribution_category.value,
        display_order=(max_order or 0) + 1,
        is_default=False,
    )
    db.add(role)
    await db.commit()
    await db.refresh(role)
    return role


async def update_role(
    db: AsyncSession, role_key: str, data: RoleUpdate,
) -> RoleDefinition:
    """Update an existing role definition."""
    role = await db.get(RoleDefinition, role_key)
    if not role:
        raise ValueError(f"Role '{role_key}' not found")

    if data.display_name is not None:
        role.display_name = data.display_name
    if data.contribution_category is not None:
        role.contribution_category = data.contribution_category.value
    if data.display_order is not None:
        role.display_order = data.display_order

    await db.commit()
    await db.refresh(role)
    return role


async def delete_role(db: AsyncSession, role_key: str) -> None:
    """Delete a custom role. Rejects deletion of default roles or roles in use."""
    role = await db.get(RoleDefinition, role_key)
    if not role:
        raise ValueError(f"Role '{role_key}' not found")
    if role.is_default:
        raise ValueError(f"Cannot delete default role '{role_key}'")

    in_use = await db.scalar(
        select(func.count()).select_from(Developer).where(
            Developer.role == role_key,
        )
    )
    if in_use:
        raise ValueError(
            f"Cannot delete role '{role_key}': {in_use} developer(s) still assigned"
        )

    await db.execute(
        delete(RoleDefinition).where(RoleDefinition.role_key == role_key)
    )
    await db.commit()
