"""Integration tests for the integrations API (Linear config CRUD, sync status, user mapping)."""

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.models import IntegrationConfig, ExternalSprint, ExternalIssue, ExternalProject
from app.services.encryption import encrypt_token


# --- Fixtures ---


@pytest_asyncio.fixture
async def linear_integration(db_session: AsyncSession) -> IntegrationConfig:
    """Create an active Linear integration for testing."""
    config = IntegrationConfig(
        type="linear",
        display_name="Linear",
        api_key=encrypt_token("lin_api_test_key"),
        workspace_id="ws_123",
        workspace_name="Test Workspace",
        status="active",
    )
    db_session.add(config)
    await db_session.commit()
    await db_session.refresh(config)
    return config


# --- Tests ---


@pytest.mark.asyncio
async def test_create_integration(client):
    """Admin can create a new integration."""
    resp = await client.post("/api/integrations", json={
        "type": "linear",
        "display_name": "My Linear",
        "api_key": "lin_api_test",
    })
    assert resp.status_code == 201
    data = resp.json()
    assert data["type"] == "linear"
    assert data["display_name"] == "My Linear"
    assert data["api_key_configured"] is True
    assert data["status"] == "active"
    assert data["is_primary_issue_source"] is False


@pytest.mark.asyncio
async def test_list_integrations(client, linear_integration):
    """Admin can list all integrations."""
    resp = await client.get("/api/integrations")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 1
    assert data[0]["type"] == "linear"
    assert data[0]["workspace_name"] == "Test Workspace"


@pytest.mark.asyncio
async def test_update_integration(client, linear_integration):
    """Admin can update integration config."""
    resp = await client.patch(f"/api/integrations/{linear_integration.id}", json={
        "display_name": "Updated Linear",
    })
    assert resp.status_code == 200
    assert resp.json()["display_name"] == "Updated Linear"


@pytest.mark.asyncio
async def test_delete_integration(client, linear_integration):
    """Admin can delete an integration."""
    resp = await client.delete(f"/api/integrations/{linear_integration.id}")
    assert resp.status_code == 204

    # Verify it's gone
    resp = await client.get("/api/integrations")
    assert len(resp.json()) == 0


@pytest.mark.asyncio
async def test_integration_not_found(client):
    """404 for non-existent integration."""
    resp = await client.patch("/api/integrations/999", json={"display_name": "x"})
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_get_sync_status(client, linear_integration):
    """Admin can get sync status for an integration."""
    resp = await client.get(f"/api/integrations/{linear_integration.id}/status")
    assert resp.status_code == 200
    data = resp.json()
    assert data["is_syncing"] is False
    assert data["issues_synced"] == 0
    assert data["sprints_synced"] == 0
    assert data["projects_synced"] == 0


@pytest.mark.asyncio
async def test_get_issue_source_default(client):
    """Default issue source is github when no integration is primary."""
    resp = await client.get("/api/integrations/issue-source")
    assert resp.status_code == 200
    data = resp.json()
    assert data["source"] == "github"
    assert data["integration_id"] is None


@pytest.mark.asyncio
async def test_set_primary_issue_source(client, linear_integration):
    """Admin can set an integration as primary issue source."""
    resp = await client.patch(f"/api/integrations/{linear_integration.id}/primary")
    assert resp.status_code == 200
    assert resp.json()["is_primary_issue_source"] is True

    # Verify issue source endpoint
    resp = await client.get("/api/integrations/issue-source")
    data = resp.json()
    assert data["source"] == "linear"
    assert data["integration_id"] == linear_integration.id


@pytest.mark.asyncio
async def test_developer_client_cannot_access(developer_client):
    """Non-admin users cannot access integration endpoints."""
    resp = await developer_client.get("/api/integrations")
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_map_user(client, linear_integration, sample_developer):
    """Admin can map a Linear user to a DevPulse developer."""
    resp = await client.post(f"/api/integrations/{linear_integration.id}/map-user", json={
        "external_user_id": "linear_user_abc",
        "developer_id": sample_developer.id,
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data["developer_id"] == sample_developer.id
    assert data["external_user_id"] == "linear_user_abc"
    assert data["mapped_by"] == "admin"
    assert data["integration_type"] == "linear"
