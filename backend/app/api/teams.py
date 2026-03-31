from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.auth import get_current_user, require_admin
from app.models.database import get_db
from app.schemas.schemas import AuthUser, TeamCreate, TeamResponse, TeamUpdate
from app.services.teams import create_team, delete_team, get_all_teams, update_team

router = APIRouter()


@router.get("/teams", response_model=list[TeamResponse])
async def list_teams(
    _: AuthUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await get_all_teams(db)


@router.post("/teams", response_model=TeamResponse, status_code=status.HTTP_201_CREATED)
async def create_team_endpoint(
    data: TeamCreate,
    _: AuthUser = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    try:
        return await create_team(db, data)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.patch("/teams/{team_id}", response_model=TeamResponse)
async def update_team_endpoint(
    team_id: int,
    data: TeamUpdate,
    _: AuthUser = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    try:
        return await update_team(db, team_id, data)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.delete("/teams/{team_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_team_endpoint(
    team_id: int,
    _: AuthUser = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    try:
        return await delete_team(db, team_id)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))
