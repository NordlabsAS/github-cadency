"""Integration tests for the /api/stats/stale-prs endpoint."""
from datetime import timedelta

import pytest

from app.models.models import Developer, PRReview, PullRequest, Repository
from conftest import NOW


class TestStalePRsEndpoint:
    @pytest.mark.asyncio
    async def test_stale_prs_empty(self, client):
        """No open PRs means empty response."""
        resp = await client.get("/api/stats/stale-prs")
        assert resp.status_code == 200
        data = resp.json()
        assert data["stale_prs"] == []
        assert data["total_count"] == 0

    @pytest.mark.asyncio
    async def test_stale_prs_no_review(
        self, client, db_session, sample_developer, sample_repo
    ):
        """Open PR with no review older than threshold is stale."""
        pr = PullRequest(
            github_id=500,
            repo_id=sample_repo.id,
            author_id=sample_developer.id,
            number=50,
            title="Waiting for review",
            state="open",
            is_draft=False,
            is_merged=False,
            html_url="https://github.com/org/test-repo/pull/50",
            created_at=NOW - timedelta(hours=48),
            updated_at=NOW - timedelta(hours=48),
            first_review_at=None,
        )
        db_session.add(pr)
        await db_session.commit()

        resp = await client.get("/api/stats/stale-prs?threshold_hours=24")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total_count"] == 1
        stale = data["stale_prs"][0]
        assert stale["number"] == 50
        assert stale["stale_reason"] == "no_review"
        assert stale["author_name"] == "Test User"
        assert stale["repo_name"] == "org/test-repo"
        assert stale["age_hours"] >= 47  # ~48h

    @pytest.mark.asyncio
    async def test_stale_prs_draft_excluded(
        self, client, db_session, sample_developer, sample_repo
    ):
        """Draft PRs should not appear in stale list."""
        pr = PullRequest(
            github_id=501,
            repo_id=sample_repo.id,
            author_id=sample_developer.id,
            number=51,
            title="Draft PR",
            state="open",
            is_draft=True,
            is_merged=False,
            created_at=NOW - timedelta(hours=72),
            updated_at=NOW - timedelta(hours=72),
            first_review_at=None,
        )
        db_session.add(pr)
        await db_session.commit()

        resp = await client.get("/api/stats/stale-prs?threshold_hours=24")
        assert resp.status_code == 200
        assert resp.json()["total_count"] == 0

    @pytest.mark.asyncio
    async def test_stale_prs_below_threshold_excluded(
        self, client, db_session, sample_developer, sample_repo
    ):
        """PR younger than threshold should not be stale."""
        pr = PullRequest(
            github_id=502,
            repo_id=sample_repo.id,
            author_id=sample_developer.id,
            number=52,
            title="Fresh PR",
            state="open",
            is_draft=False,
            is_merged=False,
            created_at=NOW - timedelta(hours=2),
            updated_at=NOW - timedelta(hours=2),
            first_review_at=None,
        )
        db_session.add(pr)
        await db_session.commit()

        resp = await client.get("/api/stats/stale-prs?threshold_hours=24")
        assert resp.status_code == 200
        assert resp.json()["total_count"] == 0

    @pytest.mark.asyncio
    async def test_stale_prs_changes_requested_no_response(
        self, client, db_session, sample_developer, sample_developer_b, sample_repo
    ):
        """PR with CHANGES_REQUESTED and no author response is stale."""
        review_time = NOW - timedelta(hours=36)
        pr = PullRequest(
            github_id=503,
            repo_id=sample_repo.id,
            author_id=sample_developer.id,
            number=53,
            title="Needs changes",
            state="open",
            is_draft=False,
            is_merged=False,
            html_url="https://github.com/org/test-repo/pull/53",
            created_at=NOW - timedelta(hours=72),
            updated_at=review_time,  # same as review time = no response
            first_review_at=review_time,
        )
        db_session.add(pr)
        await db_session.flush()

        review = PRReview(
            github_id=600,
            pr_id=pr.id,
            reviewer_id=sample_developer_b.id,
            state="CHANGES_REQUESTED",
            body="Please fix the null check",
            body_length=26,
            quality_tier="standard",
            submitted_at=review_time,
        )
        db_session.add(review)
        await db_session.commit()

        resp = await client.get("/api/stats/stale-prs?threshold_hours=24")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total_count"] == 1
        stale = data["stale_prs"][0]
        assert stale["number"] == 53
        assert stale["stale_reason"] == "changes_requested_no_response"
        assert stale["has_changes_requested"] is True

    @pytest.mark.asyncio
    async def test_stale_prs_approved_not_merged(
        self, client, db_session, sample_developer, sample_developer_b, sample_repo
    ):
        """PR that is approved but not merged past threshold is stale."""
        approval_time = NOW - timedelta(hours=36)
        pr = PullRequest(
            github_id=504,
            repo_id=sample_repo.id,
            author_id=sample_developer.id,
            number=54,
            title="Ready to merge",
            state="open",
            is_draft=False,
            is_merged=False,
            html_url="https://github.com/org/test-repo/pull/54",
            created_at=NOW - timedelta(hours=72),
            updated_at=approval_time,
            first_review_at=approval_time,
        )
        db_session.add(pr)
        await db_session.flush()

        review = PRReview(
            github_id=601,
            pr_id=pr.id,
            reviewer_id=sample_developer_b.id,
            state="APPROVED",
            body="LGTM",
            body_length=4,
            quality_tier="rubber_stamp",
            submitted_at=approval_time,
        )
        db_session.add(review)
        await db_session.commit()

        resp = await client.get("/api/stats/stale-prs?threshold_hours=24")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total_count"] == 1
        stale = data["stale_prs"][0]
        assert stale["number"] == 54
        assert stale["stale_reason"] == "approved_not_merged"
        assert stale["has_approved"] is True

    @pytest.mark.asyncio
    async def test_stale_prs_team_filter(
        self, client, db_session, sample_developer, sample_repo
    ):
        """Team filter restricts results to PRs by team members."""
        pr = PullRequest(
            github_id=505,
            repo_id=sample_repo.id,
            author_id=sample_developer.id,  # team=backend
            number=55,
            title="Backend PR",
            state="open",
            is_draft=False,
            is_merged=False,
            created_at=NOW - timedelta(hours=48),
            updated_at=NOW - timedelta(hours=48),
            first_review_at=None,
        )
        db_session.add(pr)
        await db_session.commit()

        # Backend team should find it
        resp = await client.get("/api/stats/stale-prs?team=backend&threshold_hours=24")
        assert resp.status_code == 200
        assert resp.json()["total_count"] == 1

        # Nonexistent team should find nothing
        resp = await client.get(
            "/api/stats/stale-prs?team=nonexistent&threshold_hours=24"
        )
        assert resp.status_code == 200
        assert resp.json()["total_count"] == 0

    @pytest.mark.asyncio
    async def test_stale_prs_sorted_by_age_desc(
        self, client, db_session, sample_developer, sample_repo
    ):
        """Results should be sorted most stale first."""
        for i, hours_ago in enumerate([30, 72, 48]):
            pr = PullRequest(
                github_id=510 + i,
                repo_id=sample_repo.id,
                author_id=sample_developer.id,
                number=60 + i,
                title=f"PR {hours_ago}h old",
                state="open",
                is_draft=False,
                is_merged=False,
                created_at=NOW - timedelta(hours=hours_ago),
                updated_at=NOW - timedelta(hours=hours_ago),
                first_review_at=None,
            )
            db_session.add(pr)
        await db_session.commit()

        resp = await client.get("/api/stats/stale-prs?threshold_hours=24")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total_count"] == 3
        ages = [pr["age_hours"] for pr in data["stale_prs"]]
        assert ages == sorted(ages, reverse=True)

    @pytest.mark.asyncio
    async def test_stale_prs_requires_admin(self, developer_client):
        """Developer role should get 403."""
        resp = await developer_client.get("/api/stats/stale-prs")
        assert resp.status_code == 403

    @pytest.mark.asyncio
    async def test_stale_prs_requires_auth(self, raw_client):
        """No auth should get 401."""
        resp = await raw_client.get("/api/stats/stale-prs")
        assert resp.status_code == 401
