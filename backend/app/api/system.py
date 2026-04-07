from fastapi import APIRouter, Depends

from app.api.auth import require_admin
from app.config import settings
from app.schemas.schemas import AuthUser, VersionResponse

router = APIRouter(prefix="/system", dependencies=[Depends(require_admin)])


@router.get("/version", response_model=VersionResponse)
async def get_version(_: AuthUser = Depends(require_admin)) -> VersionResponse:
    version = settings.devpulse_version
    build = settings.devpulse_build_number
    full_version = f"{version}+build.{build}" if build != "0" else version
    return VersionResponse(
        version=version,
        build=build,
        commit=settings.devpulse_commit_sha,
        deployed_at=settings.devpulse_deploy_time,
        full_version=full_version,
    )
