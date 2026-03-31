from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.auth import get_current_user, require_admin
from app.models.database import get_db
from app.schemas.schemas import (
    AuthUser,
    RoleCreate,
    RoleDefinitionResponse,
    RoleUpdate,
)
from app.services.roles import (
    create_role,
    delete_role,
    get_all_roles,
    update_role,
)

router = APIRouter()


@router.get("/roles", response_model=list[RoleDefinitionResponse])
async def list_roles(
    _: AuthUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await get_all_roles(db)


@router.post(
    "/roles",
    response_model=RoleDefinitionResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_role_endpoint(
    data: RoleCreate,
    _: AuthUser = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    try:
        return await create_role(db, data)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))


@router.patch("/roles/{role_key}", response_model=RoleDefinitionResponse)
async def update_role_endpoint(
    role_key: str,
    data: RoleUpdate,
    _: AuthUser = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    try:
        return await update_role(db, role_key, data)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.delete("/roles/{role_key}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_role_endpoint(
    role_key: str,
    _: AuthUser = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    try:
        await delete_role(db, role_key)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))
