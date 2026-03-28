from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

import jwt

from app.config import settings
from app.schemas.schemas import AppRole, AuthUser

bearer_scheme = HTTPBearer()

JWT_ALGORITHM = "HS256"


def create_jwt(developer_id: int, github_username: str, app_role: str) -> str:
    import datetime

    payload = {
        "developer_id": developer_id,
        "github_username": github_username,
        "app_role": app_role,
        "exp": datetime.datetime.now(datetime.timezone.utc)
        + datetime.timedelta(days=7),
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=JWT_ALGORITHM)


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
) -> AuthUser:
    token = credentials.credentials
    try:
        payload = jwt.decode(
            token, settings.jwt_secret, algorithms=[JWT_ALGORITHM]
        )
        return AuthUser(
            developer_id=payload["developer_id"],
            github_username=payload["github_username"],
            app_role=payload["app_role"],
        )
    except (jwt.InvalidTokenError, KeyError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
        )


async def require_admin(
    user: AuthUser = Depends(get_current_user),
) -> AuthUser:
    if user.app_role != AppRole.admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required",
        )
    return user
