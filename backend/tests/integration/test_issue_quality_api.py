"""Integration tests for /api/stats/issues/quality and /api/stats/issues/labels endpoints."""
from datetime import timedelta

import pytest

from app.models.models import Issue
from conftest import NOW, ONE_WEEK_AGO, ONE_DAY_AGO


class TestIssueQualityEndpoint:
    @pytest.mark.asyncio
    async def test_empty_database(self, client):
        resp = await client.get("/api/stats/issues/quality")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total_issues_created"] == 0
        assert data["avg_body_length"] == 0.0
        assert data["pct_with_checklist"] == 0.0
        assert data["label_distribution"] == {}

    @pytest.mark.asyncio
    async def test_quality_stats(
        self, client, db_session, sample_developer, sample_repo
    ):
        """Issues with varying quality signals produce correct stats."""
        # Well-defined issue with checklist
        body1 = "Description\n- [ ] task 1\n- [x] task 2"
        issue1 = Issue(
            github_id=500,
            repo_id=sample_repo.id,
            assignee_id=sample_developer.id,
            number=100,
            title="Add feature X",
            body=body1,
            body_length=len(body1),
            has_checklist=True,
            state="open",
            comment_count=5,
            labels=["feature", "frontend"],
            creator_github_username="alice",
            created_at=ONE_WEEK_AGO,
            updated_at=ONE_DAY_AGO,
            reopen_count=0,
        )
        # Poorly-defined issue with no body
        issue2 = Issue(
            github_id=501,
            repo_id=sample_repo.id,
            assignee_id=sample_developer.id,
            number=101,
            title="Fix bug",
            body="",
            body_length=0,
            has_checklist=False,
            state="closed",
            state_reason="not_planned",
            comment_count=1,
            labels=["bug"],
            creator_github_username="bob",
            created_at=ONE_WEEK_AGO,
            closed_at=ONE_DAY_AGO,
            reopen_count=1,
        )
        # Issue with short body
        issue3 = Issue(
            github_id=502,
            repo_id=sample_repo.id,
            assignee_id=sample_developer.id,
            number=102,
            title="Quick fix",
            body="A short description here",
            body_length=len("A short description here"),
            has_checklist=False,
            state="closed",
            state_reason="completed",
            comment_count=2,
            labels=["bug"],
            creator_github_username="alice",
            created_at=ONE_WEEK_AGO,
            closed_at=ONE_DAY_AGO,
            reopen_count=0,
        )
        db_session.add_all([issue1, issue2, issue3])
        await db_session.commit()

        resp = await client.get("/api/stats/issues/quality")
        assert resp.status_code == 200
        data = resp.json()

        assert data["total_issues_created"] == 3
        assert data["pct_with_checklist"] == pytest.approx(33.3, abs=0.1)
        assert data["avg_comment_count"] == pytest.approx(2.7, abs=0.1)
        assert data["pct_closed_not_planned"] == 50.0  # 1 not_planned out of 2 closed
        assert data["avg_reopen_count"] == pytest.approx(0.33, abs=0.01)
        # body_length 37, 0, and 24 are all < 50
        assert data["issues_without_body"] == 3
        assert data["label_distribution"]["bug"] == 2
        assert data["label_distribution"]["feature"] == 1
        assert data["label_distribution"]["frontend"] == 1

    @pytest.mark.asyncio
    async def test_team_filter(
        self, client, db_session, sample_developer, sample_repo
    ):
        issue = Issue(
            github_id=510,
            repo_id=sample_repo.id,
            assignee_id=sample_developer.id,
            number=110,
            title="Team issue",
            state="open",
            body_length=100,
            has_checklist=False,
            comment_count=0,
            created_at=ONE_WEEK_AGO,
            reopen_count=0,
        )
        db_session.add(issue)
        await db_session.commit()

        # sample_developer is on "backend" team
        resp = await client.get("/api/stats/issues/quality?team=backend")
        assert resp.status_code == 200
        assert resp.json()["total_issues_created"] == 1

        # Non-existent team returns zeros
        resp = await client.get("/api/stats/issues/quality?team=nonexistent")
        assert resp.status_code == 200
        assert resp.json()["total_issues_created"] == 0

    @pytest.mark.asyncio
    async def test_requires_admin(self, developer_client):
        resp = await developer_client.get("/api/stats/issues/quality")
        assert resp.status_code == 403

    @pytest.mark.asyncio
    async def test_date_range_filter(
        self, client, db_session, sample_developer, sample_repo
    ):
        """Issues outside date range are excluded."""
        old_issue = Issue(
            github_id=520,
            repo_id=sample_repo.id,
            assignee_id=sample_developer.id,
            number=120,
            title="Old issue",
            state="open",
            body_length=100,
            has_checklist=False,
            comment_count=0,
            created_at=NOW - timedelta(days=60),
            reopen_count=0,
        )
        recent_issue = Issue(
            github_id=521,
            repo_id=sample_repo.id,
            assignee_id=sample_developer.id,
            number=121,
            title="Recent issue",
            state="open",
            body_length=200,
            has_checklist=True,
            comment_count=3,
            created_at=ONE_DAY_AGO,
            reopen_count=0,
        )
        db_session.add_all([old_issue, recent_issue])
        await db_session.commit()

        date_from = (NOW - timedelta(days=7)).strftime("%Y-%m-%dT%H:%M:%S")
        date_to = NOW.strftime("%Y-%m-%dT%H:%M:%S")
        resp = await client.get(
            f"/api/stats/issues/quality?date_from={date_from}&date_to={date_to}"
        )
        assert resp.status_code == 200
        assert resp.json()["total_issues_created"] == 1


class TestIssueLabelEndpoint:
    @pytest.mark.asyncio
    async def test_empty_database(self, client):
        resp = await client.get("/api/stats/issues/labels")
        assert resp.status_code == 200
        assert resp.json() == {}

    @pytest.mark.asyncio
    async def test_label_distribution(
        self, client, db_session, sample_developer, sample_repo
    ):
        issue1 = Issue(
            github_id=530,
            repo_id=sample_repo.id,
            assignee_id=sample_developer.id,
            number=130,
            title="Bug 1",
            state="open",
            labels=["bug", "critical"],
            created_at=ONE_WEEK_AGO,
            body_length=0,
            has_checklist=False,
            comment_count=0,
            reopen_count=0,
        )
        issue2 = Issue(
            github_id=531,
            repo_id=sample_repo.id,
            assignee_id=sample_developer.id,
            number=131,
            title="Bug 2",
            state="open",
            labels=["bug"],
            created_at=ONE_WEEK_AGO,
            body_length=0,
            has_checklist=False,
            comment_count=0,
            reopen_count=0,
        )
        db_session.add_all([issue1, issue2])
        await db_session.commit()

        resp = await client.get("/api/stats/issues/labels")
        assert resp.status_code == 200
        data = resp.json()
        assert data["bug"] == 2
        assert data["critical"] == 1

    @pytest.mark.asyncio
    async def test_requires_admin(self, developer_client):
        resp = await developer_client.get("/api/stats/issues/labels")
        assert resp.status_code == 403
