"""Integration tests for the Teams CRUD API."""

import pytest

pytestmark = pytest.mark.asyncio


async def test_list_teams(client):
    """GET /teams returns seeded teams."""
    resp = await client.get("/api/teams")
    assert resp.status_code == 200
    data = resp.json()
    names = [t["name"] for t in data]
    assert "platform" in names
    assert "backend" in names
    # Ordered by display_order
    assert data[0]["name"] == "platform"
    assert data[1]["name"] == "backend"


async def test_create_team(client):
    """POST /teams creates a new team."""
    resp = await client.post("/api/teams", json={"name": "Frontend"})
    assert resp.status_code == 201
    data = resp.json()
    assert data["name"] == "Frontend"
    assert data["id"] > 0

    # Verify it appears in list
    resp = await client.get("/api/teams")
    names = [t["name"] for t in resp.json()]
    assert "Frontend" in names


async def test_create_team_duplicate(client):
    """POST /teams rejects duplicate names (case-insensitive)."""
    resp = await client.post("/api/teams", json={"name": "Platform"})
    assert resp.status_code == 400
    assert "already exists" in resp.json()["detail"]


async def test_create_team_invalid_name(client):
    """POST /teams rejects invalid names."""
    # Too short
    resp = await client.post("/api/teams", json={"name": "A"})
    assert resp.status_code == 400

    # Special characters
    resp = await client.post("/api/teams", json={"name": "Team@#!"})
    assert resp.status_code == 400


async def test_update_team(client):
    """PATCH /teams/{id} renames a team."""
    # Get platform team id
    resp = await client.get("/api/teams")
    platform = next(t for t in resp.json() if t["name"] == "platform")

    resp = await client.patch(f"/api/teams/{platform['id']}", json={"name": "Platform Core"})
    assert resp.status_code == 200
    assert resp.json()["name"] == "Platform Core"


async def test_delete_team_with_developers_rejected(client, sample_admin):
    """DELETE /teams/{id} rejects if developers are assigned."""
    resp = await client.get("/api/teams")
    platform = next(t for t in resp.json() if t["name"] == "platform")

    resp = await client.delete(f"/api/teams/{platform['id']}")
    assert resp.status_code == 409
    assert "developer(s) still assigned" in resp.json()["detail"]


async def test_delete_team_empty(client):
    """DELETE /teams/{id} succeeds for empty team."""
    # Create a team
    resp = await client.post("/api/teams", json={"name": "Temp Team"})
    team_id = resp.json()["id"]

    resp = await client.delete(f"/api/teams/{team_id}")
    assert resp.status_code == 204


async def test_developer_create_auto_creates_team(client):
    """Creating a developer with a new team name auto-creates the team."""
    resp = await client.post("/api/developers", json={
        "github_username": "newdev",
        "display_name": "New Dev",
        "team": "Mobile",
    })
    assert resp.status_code == 201
    assert resp.json()["team"] == "Mobile"

    # Team should now exist
    resp = await client.get("/api/teams")
    names = [t["name"] for t in resp.json()]
    assert "Mobile" in names


async def test_developer_create_existing_team_case_insensitive(client):
    """Creating a developer with existing team (different case) uses canonical name."""
    resp = await client.post("/api/developers", json={
        "github_username": "casedev",
        "display_name": "Case Dev",
        "team": "BACKEND",
    })
    assert resp.status_code == 201
    # Should use the canonical name from the teams table
    assert resp.json()["team"] == "backend"


async def test_developer_update_team(client, sample_admin):
    """Updating a developer's team resolves via teams table."""
    resp = await client.patch(f"/api/developers/{sample_admin.id}", json={"team": "Infrastructure"})
    assert resp.status_code == 200
    assert resp.json()["team"] == "Infrastructure"


async def test_new_roles_exist(client):
    """New roles (senior_devops, other) are available."""
    resp = await client.get("/api/roles")
    assert resp.status_code == 200
    role_keys = [r["role_key"] for r in resp.json()]
    assert "senior_devops" in role_keys
    assert "other" in role_keys

    # Verify categories
    roles = {r["role_key"]: r for r in resp.json()}
    assert roles["senior_devops"]["contribution_category"] == "code_contributor"
    assert roles["other"]["contribution_category"] == "non_contributor"

    # Verify senior_devops is right after devops
    devops_order = roles["devops"]["display_order"]
    senior_devops_order = roles["senior_devops"]["display_order"]
    assert senior_devops_order == devops_order + 1
