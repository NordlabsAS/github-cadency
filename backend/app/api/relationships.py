"""API routes for developer relationships, org tree, and enhanced collaboration."""

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.auth import get_current_user, require_admin
from app.models.database import get_db
from app.models.models import Developer
from app.schemas.schemas import (
    AppRole,
    AuthUser,
    CommunicationScoresResponse,
    DeveloperRelationshipCreate,
    DeveloperRelationshipDelete,
    DeveloperRelationshipResponse,
    DeveloperRelationshipsResponse,
    OrgTreeResponse,
    OverTaggedResponse,
    WorksWithResponse,
)
from app.services.enhanced_collaboration import (
    get_communication_scores,
    get_over_tagged,
    get_works_with,
)
from app.services.relationships import (
    get_developer_relationships,
    get_org_tree,
    remove_relationship,
    set_relationship,
)

router = APIRouter()


# --- Relationships ---


@router.get(
    "/developers/{developer_id}/relationships",
    response_model=DeveloperRelationshipsResponse,
)
async def developer_relationships(
    developer_id: int,
    user: AuthUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if user.app_role != AppRole.admin and user.developer_id != developer_id:
        raise HTTPException(status_code=403, detail="Access denied")
    dev = await db.get(Developer, developer_id)
    if not dev:
        raise HTTPException(status_code=404, detail="Developer not found")
    return await get_developer_relationships(db, developer_id)


@router.post(
    "/developers/{developer_id}/relationships",
    response_model=DeveloperRelationshipResponse,
)
async def create_relationship(
    developer_id: int,
    body: DeveloperRelationshipCreate,
    user: AuthUser = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    source = await db.get(Developer, developer_id)
    if not source:
        raise HTTPException(status_code=404, detail="Source developer not found")
    target = await db.get(Developer, body.target_id)
    if not target:
        raise HTTPException(status_code=404, detail="Target developer not found")
    if developer_id == body.target_id:
        raise HTTPException(status_code=400, detail="Cannot create self-relationship")

    rel = await set_relationship(
        db,
        developer_id,
        body.target_id,
        body.relationship_type.value,
        user.github_username,
    )
    await db.commit()
    await db.refresh(rel, ["source", "target"])

    return DeveloperRelationshipResponse(
        id=rel.id,
        source_id=rel.source_id,
        target_id=rel.target_id,
        relationship_type=rel.relationship_type,
        source_name=rel.source.display_name,
        target_name=rel.target.display_name,
        source_avatar_url=rel.source.avatar_url,
        target_avatar_url=rel.target.avatar_url,
        created_at=rel.created_at,
    )


@router.delete("/developers/{developer_id}/relationships", status_code=204)
async def delete_relationship(
    developer_id: int,
    body: DeveloperRelationshipDelete,
    _: AuthUser = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    removed = await remove_relationship(
        db, developer_id, body.target_id, body.relationship_type.value
    )
    if not removed:
        raise HTTPException(status_code=404, detail="Relationship not found")
    await db.commit()


# --- Org Tree ---


@router.get("/org-tree", response_model=OrgTreeResponse)
async def org_tree(
    team: str | None = Query(None),
    _: AuthUser = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    return await get_org_tree(db, team)


# --- Works With ---


@router.get(
    "/developers/{developer_id}/works-with", response_model=WorksWithResponse
)
async def works_with(
    developer_id: int,
    date_from: datetime | None = Query(None),
    date_to: datetime | None = Query(None),
    limit: int = Query(10, ge=1, le=50),
    user: AuthUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if user.app_role != AppRole.admin and user.developer_id != developer_id:
        raise HTTPException(status_code=403, detail="Access denied")
    dev = await db.get(Developer, developer_id)
    if not dev:
        raise HTTPException(status_code=404, detail="Developer not found")
    return await get_works_with(db, developer_id, date_from, date_to, limit)


# --- Over-tagged & Communication ---


@router.get("/stats/over-tagged", response_model=OverTaggedResponse)
async def over_tagged(
    team: str | None = Query(None),
    date_from: datetime | None = Query(None),
    date_to: datetime | None = Query(None),
    _: AuthUser = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    return await get_over_tagged(db, team, date_from, date_to)


@router.get(
    "/stats/communication-scores", response_model=CommunicationScoresResponse
)
async def communication_scores(
    team: str | None = Query(None),
    date_from: datetime | None = Query(None),
    date_to: datetime | None = Query(None),
    _: AuthUser = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    return await get_communication_scores(db, team, date_from, date_to)
