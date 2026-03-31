"""Tests for the role definitions API."""
import pytest


class TestRolesAPI:

    @pytest.mark.asyncio
    async def test_list_roles(self, client):
        resp = await client.get("/api/roles")
        assert resp.status_code == 200
        roles = resp.json()
        assert len(roles) == 15
        # Check ordering
        assert roles[0]["role_key"] == "developer"
        assert roles[-1]["role_key"] == "system_account"
        # Check structure
        r = roles[0]
        assert r["display_name"] == "Developer"
        assert r["contribution_category"] == "code_contributor"
        assert r["is_default"] is True

    @pytest.mark.asyncio
    async def test_list_roles_contribution_categories(self, client):
        resp = await client.get("/api/roles")
        roles = resp.json()
        categories = {r["contribution_category"] for r in roles}
        assert categories == {"code_contributor", "issue_contributor", "non_contributor", "system"}
        # Verify PM roles are issue_contributor
        pm = next(r for r in roles if r["role_key"] == "product_manager")
        assert pm["contribution_category"] == "issue_contributor"

    @pytest.mark.asyncio
    async def test_create_custom_role(self, client):
        resp = await client.post("/api/roles", json={
            "role_key": "data_scientist",
            "display_name": "Data Scientist",
            "contribution_category": "code_contributor",
        })
        assert resp.status_code == 201
        data = resp.json()
        assert data["role_key"] == "data_scientist"
        assert data["display_name"] == "Data Scientist"
        assert data["is_default"] is False

    @pytest.mark.asyncio
    async def test_create_duplicate_role_fails(self, client):
        resp = await client.post("/api/roles", json={
            "role_key": "developer",
            "display_name": "Developer Duplicate",
            "contribution_category": "code_contributor",
        })
        assert resp.status_code == 409

    @pytest.mark.asyncio
    async def test_create_role_invalid_key(self, client):
        resp = await client.post("/api/roles", json={
            "role_key": "Bad Role!",
            "display_name": "Bad",
            "contribution_category": "code_contributor",
        })
        assert resp.status_code == 409

    @pytest.mark.asyncio
    async def test_update_role(self, client):
        # Create a custom role first
        await client.post("/api/roles", json={
            "role_key": "tech_writer",
            "display_name": "Tech Writer",
            "contribution_category": "non_contributor",
        })
        # Update it
        resp = await client.patch("/api/roles/tech_writer", json={
            "display_name": "Technical Writer",
            "contribution_category": "issue_contributor",
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["display_name"] == "Technical Writer"
        assert data["contribution_category"] == "issue_contributor"

    @pytest.mark.asyncio
    async def test_update_default_role_category(self, client):
        """Admins can change the contribution category of default roles."""
        resp = await client.patch("/api/roles/designer", json={
            "contribution_category": "issue_contributor",
        })
        assert resp.status_code == 200
        assert resp.json()["contribution_category"] == "issue_contributor"

    @pytest.mark.asyncio
    async def test_delete_custom_role(self, client):
        await client.post("/api/roles", json={
            "role_key": "temp_role",
            "display_name": "Temporary",
            "contribution_category": "non_contributor",
        })
        resp = await client.delete("/api/roles/temp_role")
        assert resp.status_code == 204

    @pytest.mark.asyncio
    async def test_delete_default_role_fails(self, client):
        resp = await client.delete("/api/roles/developer")
        assert resp.status_code == 409

    @pytest.mark.asyncio
    async def test_delete_role_in_use_fails(self, client):
        """Can't delete a role assigned to a developer."""
        # 'lead' is used by sample_admin
        resp = await client.delete("/api/roles/lead")
        assert resp.status_code == 409

    @pytest.mark.asyncio
    async def test_developer_role_validation(self, client):
        """Creating a developer with an invalid role should fail."""
        resp = await client.post("/api/developers", json={
            "github_username": "newdev",
            "display_name": "New Dev",
            "role": "nonexistent_role",
        })
        assert resp.status_code == 400

    @pytest.mark.asyncio
    async def test_developer_with_pm_role(self, client):
        """Can create a developer with a PM role."""
        resp = await client.post("/api/developers", json={
            "github_username": "pm_user",
            "display_name": "PM User",
            "role": "product_manager",
        })
        assert resp.status_code == 201
        assert resp.json()["role"] == "product_manager"

    @pytest.mark.asyncio
    async def test_developer_client_can_list_roles(self, developer_client):
        """Non-admin users can list roles (for dropdowns)."""
        resp = await developer_client.get("/api/roles")
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_developer_client_cannot_create_role(self, developer_client):
        """Non-admin users cannot create roles."""
        resp = await developer_client.post("/api/roles", json={
            "role_key": "hacker",
            "display_name": "Hacker",
            "contribution_category": "code_contributor",
        })
        assert resp.status_code == 403
