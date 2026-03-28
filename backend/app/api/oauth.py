from datetime import datetime, timezone
from urllib.parse import urlencode

import httpx
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import RedirectResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.auth import create_jwt, get_current_user
from app.config import settings
from app.models.database import get_db
from app.models.models import Developer
from app.schemas.schemas import AuthMeResponse, AuthUser

router = APIRouter()

GITHUB_AUTHORIZE_URL = "https://github.com/login/oauth/authorize"
GITHUB_TOKEN_URL = "https://github.com/login/oauth/access_token"
GITHUB_USER_URL = "https://api.github.com/user"


@router.get("/auth/login")
async def login():
    params = {
        "client_id": settings.github_client_id,
        "redirect_uri": f"{settings.frontend_url}/auth/callback",
        "scope": "read:user",
    }
    return {"url": f"{GITHUB_AUTHORIZE_URL}?{urlencode(params)}"}


@router.get("/auth/callback")
async def callback(
    code: str = Query(...),
    db: AsyncSession = Depends(get_db),
):
    # Exchange code for GitHub access token
    async with httpx.AsyncClient() as client:
        token_resp = await client.post(
            GITHUB_TOKEN_URL,
            json={
                "client_id": settings.github_client_id,
                "client_secret": settings.github_client_secret,
                "code": code,
            },
            headers={"Accept": "application/json"},
        )
        if token_resp.status_code != 200:
            raise HTTPException(status_code=502, detail="GitHub token exchange failed")

        token_data = token_resp.json()
        access_token = token_data.get("access_token")
        if not access_token:
            error = token_data.get("error_description", "Unknown error")
            raise HTTPException(status_code=400, detail=f"GitHub OAuth error: {error}")

        # Get GitHub user info
        user_resp = await client.get(
            GITHUB_USER_URL,
            headers={
                "Authorization": f"Bearer {access_token}",
                "Accept": "application/vnd.github+json",
            },
        )
        if user_resp.status_code != 200:
            raise HTTPException(status_code=502, detail="Failed to fetch GitHub user")

        gh_user = user_resp.json()

    github_username = gh_user["login"]
    avatar_url = gh_user.get("avatar_url")
    display_name = gh_user.get("name") or github_username

    # Lookup or create developer
    result = await db.execute(
        select(Developer).where(Developer.github_username == github_username)
    )
    dev = result.scalar_one_or_none()

    now = datetime.now(timezone.utc)
    if dev is None:
        # Determine role: initial admin or regular developer
        app_role = "admin" if (
            settings.devpulse_initial_admin
            and github_username.lower() == settings.devpulse_initial_admin.lower()
        ) else "developer"

        dev = Developer(
            github_username=github_username,
            display_name=display_name,
            avatar_url=avatar_url,
            app_role=app_role,
            is_active=True,
            created_at=now,
            updated_at=now,
        )
        db.add(dev)
        await db.commit()
        await db.refresh(dev)
    else:
        if not dev.is_active:
            raise HTTPException(status_code=403, detail="Account is deactivated")
        dev.avatar_url = avatar_url
        dev.updated_at = now
        await db.commit()
        await db.refresh(dev)

    # Issue JWT
    token = create_jwt(dev.id, dev.github_username, dev.app_role)

    # Redirect to frontend with token
    return RedirectResponse(
        url=f"{settings.frontend_url}/auth/callback?token={token}",
        status_code=302,
    )


@router.get("/auth/me", response_model=AuthMeResponse)
async def me(
    user: AuthUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    dev = await db.get(Developer, user.developer_id)
    if not dev:
        raise HTTPException(status_code=404, detail="Developer not found")
    return AuthMeResponse(
        developer_id=dev.id,
        github_username=dev.github_username,
        display_name=dev.display_name,
        app_role=dev.app_role,
        avatar_url=dev.avatar_url,
    )
