"""Integration tests for GitHub OAuth flow."""
import os
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


class TestOAuthLogin:
    @pytest.mark.asyncio
    async def test_login_returns_github_url(self, raw_client):
        resp = await raw_client.get("/api/auth/login")
        assert resp.status_code == 200
        data = resp.json()
        assert "url" in data
        assert "github.com/login/oauth/authorize" in data["url"]
        assert "client_id=" in data["url"]


def _make_github_mocks(login: str, name: str, avatar_url: str):
    """Create mock httpx responses for GitHub token + user endpoints."""
    mock_token_resp = MagicMock()
    mock_token_resp.status_code = 200
    mock_token_resp.json.return_value = {"access_token": "gh_fake_token"}

    mock_user_resp = MagicMock()
    mock_user_resp.status_code = 200
    mock_user_resp.json.return_value = {
        "login": login,
        "name": name,
        "avatar_url": avatar_url,
    }

    mock_client = AsyncMock()
    mock_client.post.return_value = mock_token_resp
    mock_client.get.return_value = mock_user_resp
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)
    return mock_client


class TestOAuthCallback:
    @pytest.mark.asyncio
    async def test_callback_creates_new_developer(self, raw_client):
        mock_client = _make_github_mocks("newghuser", "New User", "https://example.com/avatar.jpg")

        with patch("app.api.oauth.httpx.AsyncClient", return_value=mock_client):
            resp = await raw_client.get(
                "/api/auth/callback?code=test_code",
                follow_redirects=False,
            )

        assert resp.status_code == 302
        location = resp.headers["location"]
        assert "token=" in location

    @pytest.mark.asyncio
    async def test_callback_initial_admin_gets_admin_role(self, raw_client):
        os.environ["DEVPULSE_INITIAL_ADMIN"] = "initialadmin"
        # Force settings reload
        from app.config import settings
        settings.__dict__["devpulse_initial_admin"] = "initialadmin"

        mock_client = _make_github_mocks("initialadmin", "Initial Admin", "https://example.com/avatar.jpg")

        with patch("app.api.oauth.httpx.AsyncClient", return_value=mock_client):
            resp = await raw_client.get(
                "/api/auth/callback?code=test_code",
                follow_redirects=False,
            )

        assert resp.status_code == 302
        location = resp.headers["location"]
        assert "token=" in location

        # Decode the JWT to verify admin role
        import jwt
        token = location.split("token=")[1]
        payload = jwt.decode(token, os.environ.get("JWT_SECRET", "test-jwt-secret-for-testing"), algorithms=["HS256"])
        assert payload["app_role"] == "admin"
        assert payload["github_username"] == "initialadmin"

        # Cleanup
        settings.__dict__["devpulse_initial_admin"] = ""
        os.environ.pop("DEVPULSE_INITIAL_ADMIN", None)

    @pytest.mark.asyncio
    async def test_callback_existing_user_updates_avatar(self, raw_client, sample_developer):
        mock_client = _make_github_mocks("testuser", "Test User", "https://new-avatar.com/img.jpg")

        with patch("app.api.oauth.httpx.AsyncClient", return_value=mock_client):
            resp = await raw_client.get(
                "/api/auth/callback?code=test_code",
                follow_redirects=False,
            )

        assert resp.status_code == 302
        location = resp.headers["location"]
        assert "token=" in location
