"""Integration tests for GET /api/stats/repos/summary endpoint."""
import pytest
from datetime import timedelta

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.models import Developer, Issue, PRReview, PullRequest, Repository

# Re-use conftest timestamps
from conftest import NOW, ONE_DAY_AGO, ONE_WEEK_AGO


class TestReposSummary:
    @pytest.mark.asyncio
    async def test_empty_no_tracked_repos(self, client):
        """Returns empty list when no tracked repos exist."""
        resp = await client.get("/api/stats/repos/summary")
        assert resp.status_code == 200
        assert resp.json() == []

    @pytest.mark.asyncio
    async def test_basic_metrics(
        self, client, sample_repo, sample_pr, sample_review, sample_issue
    ):
        """Returns correct per-repo counts for a tracked repo."""
        resp = await client.get("/api/stats/repos/summary")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1

        item = data[0]
        assert item["repo_id"] == sample_repo.id
        assert item["total_prs"] >= 1
        assert item["total_merged"] >= 1
        assert item["total_issues"] >= 1
        assert item["total_reviews"] >= 1
        assert item["avg_time_to_merge_hours"] is not None
        assert item["last_pr_date"] is not None

    @pytest.mark.asyncio
    async def test_untracked_excluded(
        self, client, sample_repo, sample_pr, db_session: AsyncSession
    ):
        """Untracked repos are not included in the summary."""
        sample_repo.is_tracked = False
        db_session.add(sample_repo)
        await db_session.commit()

        resp = await client.get("/api/stats/repos/summary")
        assert resp.status_code == 200
        assert resp.json() == []

    @pytest.mark.asyncio
    async def test_date_range_filtering(
        self, client, sample_repo, sample_pr
    ):
        """Only includes data within the specified date range."""
        # Use a date range that excludes the sample PR (created ONE_WEEK_AGO)
        future = NOW + timedelta(days=10)
        future_end = future + timedelta(days=5)
        date_from_str = future.strftime("%Y-%m-%dT%H:%M:%S")
        date_to_str = future_end.strftime("%Y-%m-%dT%H:%M:%S")
        resp = await client.get(
            f"/api/stats/repos/summary?date_from={date_from_str}&date_to={date_to_str}"
        )
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1
        assert data[0]["total_prs"] == 0
        assert data[0]["total_merged"] == 0

    @pytest.mark.asyncio
    async def test_previous_period_trends(
        self, client, sample_repo, sample_developer, db_session: AsyncSession
    ):
        """Previous period fields populated when historical data exists."""
        # Create a PR in the "previous" 30-day window (31-60 days ago)
        old_pr = PullRequest(
            github_id=999,
            repo_id=sample_repo.id,
            author_id=sample_developer.id,
            number=99,
            title="Old PR",
            state="closed",
            is_merged=True,
            additions=10,
            deletions=5,
            changed_files=1,
            created_at=NOW - timedelta(days=45),
            merged_at=NOW - timedelta(days=40),
            time_to_merge_s=int(timedelta(days=5).total_seconds()),
            head_branch="old-feature",
            base_branch="main",
        )
        db_session.add(old_pr)
        await db_session.commit()

        resp = await client.get("/api/stats/repos/summary")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1
        item = data[0]
        assert item["prev_total_prs"] >= 1
        assert item["prev_total_merged"] >= 1
        assert item["prev_avg_time_to_merge_hours"] is not None

    @pytest.mark.asyncio
    async def test_auth_required(self, raw_client):
        """Returns 401 without authentication."""
        resp = await raw_client.get("/api/stats/repos/summary")
        assert resp.status_code == 401

    @pytest.mark.asyncio
    async def test_multiple_repos(
        self, client, sample_repo, sample_pr, db_session: AsyncSession, sample_developer
    ):
        """Returns entries for each tracked repo."""
        repo2 = Repository(
            github_id=99999,
            name="second-repo",
            full_name="org/second-repo",
            language="TypeScript",
            is_tracked=True,
            created_at=NOW,
        )
        db_session.add(repo2)
        await db_session.commit()
        await db_session.refresh(repo2)

        # Add a PR to repo2
        pr2 = PullRequest(
            github_id=888,
            repo_id=repo2.id,
            author_id=sample_developer.id,
            number=50,
            title="Feature",
            state="closed",
            is_merged=True,
            additions=20,
            deletions=3,
            changed_files=2,
            created_at=ONE_WEEK_AGO,
            merged_at=ONE_DAY_AGO,
            time_to_merge_s=int((ONE_DAY_AGO - ONE_WEEK_AGO).total_seconds()),
            head_branch="feature",
            base_branch="main",
        )
        db_session.add(pr2)
        await db_session.commit()

        resp = await client.get("/api/stats/repos/summary")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 2
        repo_ids = {item["repo_id"] for item in data}
        assert sample_repo.id in repo_ids
        assert repo2.id in repo_ids

    @pytest.mark.asyncio
    async def test_developer_client_can_access(
        self, developer_client, sample_repo, sample_pr
    ):
        """Non-admin authenticated users can also access the summary."""
        resp = await developer_client.get("/api/stats/repos/summary")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1
