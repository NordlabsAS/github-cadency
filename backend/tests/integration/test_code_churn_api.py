"""Integration tests for GET /api/stats/repo/{id}/churn endpoint."""

import pytest

from app.models.models import PRFile, PullRequest, RepoTreeFile
from conftest import NOW, ONE_WEEK_AGO


class TestCodeChurnEndpoint:
    @pytest.mark.asyncio
    async def test_repo_not_found(self, client):
        resp = await client.get("/api/stats/repo/99999/churn")
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_empty_repo(self, client, sample_repo):
        resp = await client.get(f"/api/stats/repo/{sample_repo.id}/churn")
        assert resp.status_code == 200
        data = resp.json()
        assert data["repo_id"] == sample_repo.id
        assert data["repo_name"] == "test-repo"
        assert data["hotspot_files"] == []
        assert data["stale_directories"] == []
        assert data["total_files_in_repo"] == 0
        assert data["total_files_changed"] == 0

    @pytest.mark.asyncio
    async def test_with_pr_files(self, client, db_session, sample_pr, sample_repo):
        # Add files to the existing sample PR
        f1 = PRFile(
            pr_id=sample_pr.id,
            filename="src/main.py",
            additions=30,
            deletions=10,
            status="modified",
        )
        f2 = PRFile(
            pr_id=sample_pr.id,
            filename="src/utils.py",
            additions=5,
            deletions=2,
            status="added",
        )
        db_session.add_all([f1, f2])
        await db_session.commit()

        resp = await client.get(f"/api/stats/repo/{sample_repo.id}/churn")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total_files_changed"] == 2
        assert len(data["hotspot_files"]) == 2

        top = data["hotspot_files"][0]
        assert "path" in top
        assert "change_frequency" in top
        assert "total_churn" in top
        assert "contributor_count" in top

    @pytest.mark.asyncio
    async def test_stale_directories(self, client, db_session, sample_pr, sample_repo):
        # Add a file to sample PR (which is recent)
        f1 = PRFile(
            pr_id=sample_pr.id,
            filename="src/main.py",
            additions=10,
            deletions=5,
            status="modified",
        )
        db_session.add(f1)

        # Add repo tree with src/ (active) and legacy/ (stale)
        tree_entries = [
            RepoTreeFile(repo_id=sample_repo.id, path="src", type="tree", last_synced_at=NOW),
            RepoTreeFile(repo_id=sample_repo.id, path="legacy", type="tree", last_synced_at=NOW),
            RepoTreeFile(repo_id=sample_repo.id, path="src/main.py", type="blob", last_synced_at=NOW),
            RepoTreeFile(repo_id=sample_repo.id, path="legacy/old.py", type="blob", last_synced_at=NOW),
        ]
        db_session.add_all(tree_entries)
        await db_session.commit()

        resp = await client.get(f"/api/stats/repo/{sample_repo.id}/churn")
        assert resp.status_code == 200
        data = resp.json()

        stale_paths = [d["path"] for d in data["stale_directories"]]
        assert "legacy" in stale_paths
        assert "src" not in stale_paths

    @pytest.mark.asyncio
    async def test_limit_parameter(self, client, db_session, sample_pr, sample_repo):
        # Add multiple files
        for i in range(5):
            db_session.add(
                PRFile(
                    pr_id=sample_pr.id,
                    filename=f"file_{i}.py",
                    additions=10 * (5 - i),
                    deletions=0,
                    status="modified",
                )
            )
        await db_session.commit()

        resp = await client.get(f"/api/stats/repo/{sample_repo.id}/churn?limit=2")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["hotspot_files"]) == 2

    @pytest.mark.asyncio
    async def test_response_shape(self, client, sample_repo):
        resp = await client.get(f"/api/stats/repo/{sample_repo.id}/churn")
        assert resp.status_code == 200
        data = resp.json()

        # Verify all expected keys are present
        assert "repo_id" in data
        assert "repo_name" in data
        assert "hotspot_files" in data
        assert "stale_directories" in data
        assert "total_files_in_repo" in data
        assert "total_files_changed" in data
        assert "tree_truncated" in data
