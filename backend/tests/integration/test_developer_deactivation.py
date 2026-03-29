"""Integration tests for developer deactivation/reactivation feature."""
import pytest

from app.models.models import Developer, Issue, PullRequest
from conftest import NOW, ONE_WEEK_AGO


class TestToggleActiveViaPatch:
    @pytest.mark.asyncio
    async def test_deactivate_via_patch(self, client, sample_developer):
        resp = await client.patch(
            f"/api/developers/{sample_developer.id}",
            json={"is_active": False},
        )
        assert resp.status_code == 200
        assert resp.json()["is_active"] is False

        # No longer in active list
        resp = await client.get("/api/developers")
        usernames = [d["github_username"] for d in resp.json()]
        assert "testuser" not in usernames

        # Appears in inactive list
        resp = await client.get("/api/developers?is_active=false")
        usernames = [d["github_username"] for d in resp.json()]
        assert "testuser" in usernames

    @pytest.mark.asyncio
    async def test_reactivate_via_patch(self, client, sample_developer):
        # Deactivate first
        await client.patch(
            f"/api/developers/{sample_developer.id}",
            json={"is_active": False},
        )
        # Reactivate
        resp = await client.patch(
            f"/api/developers/{sample_developer.id}",
            json={"is_active": True},
        )
        assert resp.status_code == 200
        assert resp.json()["is_active"] is True

        # Back in active list
        resp = await client.get("/api/developers")
        usernames = [d["github_username"] for d in resp.json()]
        assert "testuser" in usernames

    @pytest.mark.asyncio
    async def test_patch_is_active_preserves_other_fields(self, client, sample_developer):
        resp = await client.patch(
            f"/api/developers/{sample_developer.id}",
            json={"is_active": False},
        )
        data = resp.json()
        assert data["is_active"] is False
        assert data["display_name"] == "Test User"
        assert data["team"] == "backend"


class TestDeactivationImpact:
    @pytest.mark.asyncio
    async def test_no_open_work(self, client, sample_developer):
        resp = await client.get(
            f"/api/developers/{sample_developer.id}/deactivation-impact"
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["open_prs"] == 0
        assert data["open_issues"] == 0
        assert data["open_branches"] == []

    @pytest.mark.asyncio
    async def test_with_open_prs_and_issues(
        self, client, sample_developer, sample_repo, db_session
    ):
        # Create open PR
        pr = PullRequest(
            github_id=900,
            repo_id=sample_repo.id,
            author_id=sample_developer.id,
            number=90,
            title="WIP feature",
            state="open",
            is_merged=False,
            additions=10,
            deletions=0,
            changed_files=1,
            created_at=NOW,
            head_branch="feature/wip",
            base_branch="main",
        )
        # Create open issue assigned to dev
        issue = Issue(
            github_id=901,
            repo_id=sample_repo.id,
            assignee_id=sample_developer.id,
            number=91,
            title="Open bug",
            state="open",
            created_at=NOW,
        )
        db_session.add_all([pr, issue])
        await db_session.commit()

        resp = await client.get(
            f"/api/developers/{sample_developer.id}/deactivation-impact"
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["open_prs"] == 1
        assert data["open_issues"] == 1
        assert "feature/wip" in data["open_branches"]

    @pytest.mark.asyncio
    async def test_draft_prs_excluded(
        self, client, sample_developer, sample_repo, db_session
    ):
        pr = PullRequest(
            github_id=902,
            repo_id=sample_repo.id,
            author_id=sample_developer.id,
            number=92,
            title="Draft PR",
            state="open",
            is_draft=True,
            is_merged=False,
            additions=5,
            deletions=0,
            changed_files=1,
            created_at=NOW,
            head_branch="draft/experiment",
            base_branch="main",
        )
        db_session.add(pr)
        await db_session.commit()

        resp = await client.get(
            f"/api/developers/{sample_developer.id}/deactivation-impact"
        )
        data = resp.json()
        assert data["open_prs"] == 0
        assert data["open_branches"] == []

    @pytest.mark.asyncio
    async def test_not_found(self, client):
        resp = await client.get("/api/developers/999/deactivation-impact")
        assert resp.status_code == 404


class TestCreateInactiveConflict:
    @pytest.mark.asyncio
    async def test_create_with_inactive_username_returns_structured_409(
        self, client, sample_developer
    ):
        # Deactivate the developer
        await client.patch(
            f"/api/developers/{sample_developer.id}",
            json={"is_active": False},
        )

        # Try to create with same username
        resp = await client.post(
            "/api/developers",
            json={
                "github_username": "testuser",
                "display_name": "New User",
            },
        )
        assert resp.status_code == 409
        detail = resp.json()["detail"]
        assert detail["code"] == "inactive_exists"
        assert detail["developer_id"] == sample_developer.id
        assert detail["display_name"] == "Test User"

    @pytest.mark.asyncio
    async def test_create_with_active_username_returns_plain_409(
        self, client, sample_developer
    ):
        resp = await client.post(
            "/api/developers",
            json={
                "github_username": "testuser",
                "display_name": "Duplicate",
            },
        )
        assert resp.status_code == 409
        assert isinstance(resp.json()["detail"], str)
