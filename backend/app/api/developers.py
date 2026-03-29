from datetime import datetime, timezone
from enum import Enum as PyEnum

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.auth import get_current_user, require_admin
from app.models.database import get_db
from app.models.models import Developer
from app.models.models import Issue, PullRequest
from app.schemas.schemas import (
    AppRole,
    AuthUser,
    DeactivationImpactResponse,
    DeveloperCreate,
    DeveloperResponse,
    DeveloperUpdateAdmin,
)

router = APIRouter()


@router.get("/developers", response_model=list[DeveloperResponse])
async def list_developers(
    team: str | None = Query(None),
    is_active: bool = Query(True),
    _: AuthUser = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    stmt = select(Developer).where(Developer.is_active == is_active)
    if team:
        stmt = stmt.where(Developer.team == team)
    stmt = stmt.order_by(Developer.display_name)
    result = await db.execute(stmt)
    return result.scalars().all()


@router.post(
    "/developers",
    response_model=DeveloperResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_developer(
    data: DeveloperCreate,
    _: AuthUser = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    existing = await db.execute(
        select(Developer).where(Developer.github_username == data.github_username)
    )
    existing_dev = existing.scalar_one_or_none()
    if existing_dev:
        if not existing_dev.is_active:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={
                    "code": "inactive_exists",
                    "developer_id": existing_dev.id,
                    "display_name": existing_dev.display_name,
                },
            )
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Developer with github_username '{data.github_username}' already exists",
        )

    now = datetime.now(timezone.utc)
    dev = Developer(**data.model_dump(), created_at=now, updated_at=now)
    db.add(dev)
    await db.commit()
    await db.refresh(dev)
    return dev


@router.get("/developers/{developer_id}", response_model=DeveloperResponse)
async def get_developer(
    developer_id: int,
    user: AuthUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if user.app_role != AppRole.admin and user.developer_id != developer_id:
        raise HTTPException(status_code=403, detail="Access denied")
    dev = await db.get(Developer, developer_id)
    if not dev:
        raise HTTPException(status_code=404, detail="Developer not found")
    return dev


@router.patch("/developers/{developer_id}", response_model=DeveloperResponse)
async def update_developer(
    developer_id: int,
    data: DeveloperUpdateAdmin,
    _: AuthUser = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    dev = await db.get(Developer, developer_id)
    if not dev:
        raise HTTPException(status_code=404, detail="Developer not found")

    updates = data.model_dump(exclude_unset=True)
    for field, value in updates.items():
        setattr(dev, field, value.value if isinstance(value, PyEnum) else value)
    dev.updated_at = datetime.now(timezone.utc)

    await db.commit()
    await db.refresh(dev)
    return dev


@router.get(
    "/developers/{developer_id}/deactivation-impact",
    response_model=DeactivationImpactResponse,
)
async def get_deactivation_impact(
    developer_id: int,
    _: AuthUser = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    dev = await db.get(Developer, developer_id)
    if not dev:
        raise HTTPException(status_code=404, detail="Developer not found")

    from sqlalchemy import func, distinct

    open_prs_result = await db.execute(
        select(func.count()).where(
            PullRequest.author_id == developer_id,
            PullRequest.state == "open",
            PullRequest.is_draft.isnot(True),
        )
    )
    open_prs = open_prs_result.scalar() or 0

    branches_result = await db.execute(
        select(distinct(PullRequest.head_branch)).where(
            PullRequest.author_id == developer_id,
            PullRequest.state == "open",
            PullRequest.is_draft.isnot(True),
            PullRequest.head_branch.isnot(None),
        )
    )
    open_branches = [row[0] for row in branches_result.all()]

    open_issues_result = await db.execute(
        select(func.count()).where(
            Issue.assignee_id == developer_id,
            Issue.state == "open",
        )
    )
    open_issues = open_issues_result.scalar() or 0

    return DeactivationImpactResponse(
        open_prs=open_prs,
        open_issues=open_issues,
        open_branches=open_branches,
    )


@router.delete(
    "/developers/{developer_id}", status_code=status.HTTP_204_NO_CONTENT
)
async def delete_developer(
    developer_id: int,
    _: AuthUser = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    dev = await db.get(Developer, developer_id)
    if not dev:
        raise HTTPException(status_code=404, detail="Developer not found")

    dev.is_active = False
    dev.updated_at = datetime.now(timezone.utc)
    await db.commit()
