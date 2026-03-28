"""Integration tests for the /api/goals/self endpoints (P1-03)."""
import pytest

from app.models.models import DeveloperGoal


class TestCreateSelfGoal:
    @pytest.mark.asyncio
    async def test_create_self_goal(self, developer_client, sample_developer):
        payload = {
            "title": "Merge more PRs",
            "metric_key": "prs_merged",
            "target_value": 10,
            "target_direction": "above",
        }
        resp = await developer_client.post("/api/goals/self", json=payload)
        assert resp.status_code == 200
        data = resp.json()
        assert data["title"] == "Merge more PRs"
        assert data["developer_id"] == sample_developer.id
        assert data["created_by"] == "self"
        assert data["metric_key"] == "prs_merged"
        assert data["target_value"] == 10
        assert data["status"] == "active"
        assert data["baseline_value"] is not None

    @pytest.mark.asyncio
    async def test_create_self_goal_with_optional_fields(self, developer_client, sample_developer):
        payload = {
            "title": "Reduce merge time",
            "description": "Get faster at shipping",
            "metric_key": "time_to_merge_h",
            "target_value": 24,
            "target_direction": "below",
            "target_date": "2026-06-01",
        }
        resp = await developer_client.post("/api/goals/self", json=payload)
        assert resp.status_code == 200
        data = resp.json()
        assert data["description"] == "Get faster at shipping"
        assert data["target_direction"] == "below"
        assert data["target_date"] == "2026-06-01"

    @pytest.mark.asyncio
    async def test_create_self_goal_unauthenticated(self, raw_client):
        payload = {
            "title": "Test",
            "metric_key": "prs_merged",
            "target_value": 5,
        }
        resp = await raw_client.post("/api/goals/self", json=payload)
        assert resp.status_code == 401


class TestUpdateSelfGoal:
    @pytest.mark.asyncio
    async def test_update_own_self_goal(self, developer_client, sample_developer, db_session):
        # Create a self-created goal directly
        goal = DeveloperGoal(
            developer_id=sample_developer.id,
            title="My goal",
            metric_key="prs_merged",
            target_value=5,
            target_direction="above",
            baseline_value=2,
            created_by="self",
        )
        db_session.add(goal)
        await db_session.commit()
        await db_session.refresh(goal)

        resp = await developer_client.patch(
            f"/api/goals/self/{goal.id}",
            json={"target_value": 8, "notes": "Adjusted target"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["target_value"] == 8
        assert data["notes"] == "Adjusted target"

    @pytest.mark.asyncio
    async def test_cannot_update_admin_created_goal(self, developer_client, sample_developer, db_session):
        goal = DeveloperGoal(
            developer_id=sample_developer.id,
            title="Admin goal",
            metric_key="reviews_given",
            target_value=20,
            target_direction="above",
            baseline_value=10,
            created_by="admin",
        )
        db_session.add(goal)
        await db_session.commit()
        await db_session.refresh(goal)

        resp = await developer_client.patch(
            f"/api/goals/self/{goal.id}",
            json={"status": "abandoned"},
        )
        assert resp.status_code == 403
        assert "admin-created" in resp.json()["detail"]

    @pytest.mark.asyncio
    async def test_cannot_update_other_developers_goal(
        self, developer_client, sample_admin, db_session
    ):
        # Goal belongs to admin, not the developer
        goal = DeveloperGoal(
            developer_id=sample_admin.id,
            title="Admin's own goal",
            metric_key="prs_merged",
            target_value=5,
            target_direction="above",
            baseline_value=1,
            created_by="self",
        )
        db_session.add(goal)
        await db_session.commit()
        await db_session.refresh(goal)

        resp = await developer_client.patch(
            f"/api/goals/self/{goal.id}",
            json={"status": "achieved"},
        )
        assert resp.status_code == 403

    @pytest.mark.asyncio
    async def test_mark_self_goal_achieved(self, developer_client, sample_developer, db_session):
        goal = DeveloperGoal(
            developer_id=sample_developer.id,
            title="Achieve this",
            metric_key="prs_merged",
            target_value=5,
            target_direction="above",
            baseline_value=2,
            created_by="self",
        )
        db_session.add(goal)
        await db_session.commit()
        await db_session.refresh(goal)

        resp = await developer_client.patch(
            f"/api/goals/self/{goal.id}",
            json={"status": "achieved"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "achieved"
        assert data["achieved_at"] is not None

    @pytest.mark.asyncio
    async def test_update_nonexistent_goal(self, developer_client, sample_developer):
        resp = await developer_client.patch(
            "/api/goals/self/99999",
            json={"status": "achieved"},
        )
        assert resp.status_code == 404


class TestExistingGoalEndpointsUnaffected:
    @pytest.mark.asyncio
    async def test_admin_create_goal_has_admin_created_by(self, client, sample_developer):
        payload = {
            "developer_id": sample_developer.id,
            "title": "Admin-set goal",
            "metric_key": "prs_merged",
            "target_value": 15,
        }
        resp = await client.post("/api/goals", json=payload)
        assert resp.status_code == 200
        data = resp.json()
        assert data["created_by"] == "admin"

    @pytest.mark.asyncio
    async def test_list_goals_includes_created_by(self, client, sample_developer, db_session):
        goal = DeveloperGoal(
            developer_id=sample_developer.id,
            title="Test goal",
            metric_key="prs_merged",
            target_value=5,
            target_direction="above",
            baseline_value=2,
            created_by="self",
        )
        db_session.add(goal)
        await db_session.commit()

        resp = await client.get(f"/api/goals?developer_id={sample_developer.id}")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) >= 1
        assert data[0]["created_by"] == "self"
