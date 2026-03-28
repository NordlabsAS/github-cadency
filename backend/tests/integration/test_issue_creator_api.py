"""Integration tests for GET /api/stats/issues/creators endpoint."""
from datetime import timedelta

import pytest

from app.models.models import Issue, IssueComment, PullRequest
from conftest import NOW, ONE_WEEK_AGO, ONE_DAY_AGO


class TestIssueCreatorStatsEndpoint:
    @pytest.mark.asyncio
    async def test_empty_database(self, client):
        resp = await client.get("/api/stats/issues/creators")
        assert resp.status_code == 200
        data = resp.json()
        assert data["creators"] == []
        assert data["team_averages"]["issues_created"] == 0

    @pytest.mark.asyncio
    async def test_basic_creator_stats(
        self, client, db_session, sample_admin, sample_developer, sample_repo
    ):
        """Two creators with different quality signals produce correct per-creator stats."""
        # Admin creates well-defined issues
        body1 = "Detailed description with acceptance criteria\n- [ ] task 1\n- [x] task 2"
        issue1 = Issue(
            github_id=600,
            repo_id=sample_repo.id,
            number=200,
            title="Feature A",
            body=body1,
            body_length=len(body1),
            has_checklist=True,
            state="closed",
            state_reason="completed",
            comment_count=3,
            creator_github_username="admin",
            created_at=ONE_WEEK_AGO,
            closed_at=ONE_DAY_AGO,
            time_to_close_s=int((ONE_DAY_AGO - ONE_WEEK_AGO).total_seconds()),
            reopen_count=0,
        )
        issue2 = Issue(
            github_id=601,
            repo_id=sample_repo.id,
            number=201,
            title="Feature B",
            body="Another well-described issue with enough detail to be over 100 chars. " * 2,
            body_length=140,
            has_checklist=False,
            state="open",
            comment_count=1,
            creator_github_username="admin",
            created_at=ONE_WEEK_AGO,
            reopen_count=0,
        )
        # Developer creates poorly-defined issues
        issue3 = Issue(
            github_id=602,
            repo_id=sample_repo.id,
            number=202,
            title="Fix bug",
            body="short",
            body_length=5,
            has_checklist=False,
            state="closed",
            state_reason="not_planned",
            comment_count=0,
            creator_github_username="testuser",
            created_at=ONE_WEEK_AGO,
            closed_at=ONE_DAY_AGO,
            time_to_close_s=int((ONE_DAY_AGO - ONE_WEEK_AGO).total_seconds()),
            reopen_count=1,
        )
        db_session.add_all([issue1, issue2, issue3])
        await db_session.commit()

        resp = await client.get("/api/stats/issues/creators")
        assert resp.status_code == 200
        data = resp.json()

        assert len(data["creators"]) == 2

        # Sorted by issues_created desc — admin has 2, testuser has 1
        admin_stats = data["creators"][0]
        dev_stats = data["creators"][1]

        assert admin_stats["github_username"] == "admin"
        assert admin_stats["issues_created"] == 2
        assert admin_stats["display_name"] == "Admin User"
        assert admin_stats["team"] == "platform"
        assert admin_stats["pct_with_checklist"] == 50.0
        assert admin_stats["pct_reopened"] == 0.0
        assert admin_stats["issues_with_body_under_100_chars"] == 1  # body1=73 chars (<100); body2=140 chars (>=100)

        assert dev_stats["github_username"] == "testuser"
        assert dev_stats["issues_created"] == 1
        assert dev_stats["pct_reopened"] == 100.0
        assert dev_stats["pct_closed_not_planned"] == 100.0
        assert dev_stats["issues_with_body_under_100_chars"] == 1

        # Team averages are computed
        avg = data["team_averages"]
        assert avg["issues_created"] == 2  # round(3/2) = 2

    @pytest.mark.asyncio
    async def test_team_filter(
        self, client, db_session, sample_admin, sample_developer, sample_repo
    ):
        """Team filter only includes creators from that team."""
        issue1 = Issue(
            github_id=610,
            repo_id=sample_repo.id,
            number=210,
            title="Platform issue",
            body_length=200,
            has_checklist=True,
            state="open",
            comment_count=0,
            creator_github_username="admin",  # platform team
            created_at=ONE_WEEK_AGO,
            reopen_count=0,
        )
        issue2 = Issue(
            github_id=611,
            repo_id=sample_repo.id,
            number=211,
            title="Backend issue",
            body_length=200,
            has_checklist=False,
            state="open",
            comment_count=0,
            creator_github_username="testuser",  # backend team
            created_at=ONE_WEEK_AGO,
            reopen_count=0,
        )
        db_session.add_all([issue1, issue2])
        await db_session.commit()

        resp = await client.get("/api/stats/issues/creators?team=platform")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["creators"]) == 1
        assert data["creators"][0]["github_username"] == "admin"

        # Non-existent team returns empty
        resp = await client.get("/api/stats/issues/creators?team=nonexistent")
        assert resp.status_code == 200
        assert data["creators"][0]["github_username"] == "admin"

    @pytest.mark.asyncio
    async def test_linkage_metrics(
        self, client, db_session, sample_admin, sample_repo
    ):
        """Issues linked to PRs produce correct avg_prs_per_issue and avg_time_to_first_pr_hours."""
        issue = Issue(
            github_id=620,
            repo_id=sample_repo.id,
            number=220,
            title="Linked issue",
            body_length=200,
            has_checklist=False,
            state="closed",
            state_reason="completed",
            comment_count=2,
            creator_github_username="admin",
            created_at=ONE_WEEK_AGO,
            closed_at=ONE_DAY_AGO,
            time_to_close_s=int((ONE_DAY_AGO - ONE_WEEK_AGO).total_seconds()),
            reopen_count=0,
        )
        db_session.add(issue)
        await db_session.flush()

        # Two PRs close this issue
        pr1 = PullRequest(
            github_id=700,
            repo_id=sample_repo.id,
            number=300,
            title="Fix for #220",
            state="closed",
            is_merged=True,
            additions=10,
            deletions=5,
            changed_files=1,
            created_at=ONE_WEEK_AGO + timedelta(hours=24),
            merged_at=ONE_DAY_AGO,
            closes_issue_numbers=[220],
        )
        pr2 = PullRequest(
            github_id=701,
            repo_id=sample_repo.id,
            number=301,
            title="Another fix for #220",
            state="closed",
            is_merged=True,
            additions=5,
            deletions=2,
            changed_files=1,
            created_at=ONE_WEEK_AGO + timedelta(hours=48),
            merged_at=ONE_DAY_AGO,
            closes_issue_numbers=[220],
        )
        db_session.add_all([pr1, pr2])
        await db_session.commit()

        resp = await client.get("/api/stats/issues/creators")
        assert resp.status_code == 200
        data = resp.json()

        creator = data["creators"][0]
        assert creator["github_username"] == "admin"
        assert creator["avg_prs_per_issue"] == 2.0
        # First PR created 24h after issue → 24.0 hours
        assert creator["avg_time_to_first_pr_hours"] == 24.0

    @pytest.mark.asyncio
    async def test_comment_count_before_pr(
        self, client, db_session, sample_admin, sample_repo
    ):
        """Comments before the first linked PR are counted correctly."""
        issue = Issue(
            github_id=630,
            repo_id=sample_repo.id,
            number=230,
            title="Issue with comments",
            body_length=200,
            has_checklist=False,
            state="closed",
            state_reason="completed",
            comment_count=3,
            creator_github_username="admin",
            created_at=ONE_WEEK_AGO,
            closed_at=ONE_DAY_AGO,
            time_to_close_s=int((ONE_DAY_AGO - ONE_WEEK_AGO).total_seconds()),
            reopen_count=0,
        )
        db_session.add(issue)
        await db_session.flush()

        # PR that closes this issue, created 3 days after the issue
        pr_created = ONE_WEEK_AGO + timedelta(days=3)
        pr = PullRequest(
            github_id=710,
            repo_id=sample_repo.id,
            number=310,
            title="Closes #230",
            state="closed",
            is_merged=True,
            additions=10,
            deletions=5,
            changed_files=1,
            created_at=pr_created,
            merged_at=ONE_DAY_AGO,
            closes_issue_numbers=[230],
        )
        db_session.add(pr)
        await db_session.flush()

        # 2 comments before PR, 1 after
        comment1 = IssueComment(
            github_id=800,
            issue_id=issue.id,
            author_github_username="someone",
            body="What about this approach?",
            created_at=ONE_WEEK_AGO + timedelta(days=1),
        )
        comment2 = IssueComment(
            github_id=801,
            issue_id=issue.id,
            author_github_username="admin",
            body="Let me clarify the requirements",
            created_at=ONE_WEEK_AGO + timedelta(days=2),
        )
        comment3 = IssueComment(
            github_id=802,
            issue_id=issue.id,
            author_github_username="someone",
            body="Looks good in the PR",
            created_at=ONE_WEEK_AGO + timedelta(days=4),  # after PR
        )
        db_session.add_all([comment1, comment2, comment3])
        await db_session.commit()

        resp = await client.get("/api/stats/issues/creators")
        assert resp.status_code == 200
        data = resp.json()

        creator = data["creators"][0]
        assert creator["avg_comment_count_before_pr"] == 2.0

    @pytest.mark.asyncio
    async def test_requires_admin(self, developer_client):
        resp = await developer_client.get("/api/stats/issues/creators")
        assert resp.status_code == 403

    @pytest.mark.asyncio
    async def test_external_creator(
        self, client, db_session, sample_repo
    ):
        """External users (not registered as developers) appear with no team/role."""
        issue = Issue(
            github_id=640,
            repo_id=sample_repo.id,
            number=240,
            title="External issue",
            body_length=200,
            has_checklist=False,
            state="open",
            comment_count=0,
            creator_github_username="external_user",
            created_at=ONE_WEEK_AGO,
            reopen_count=0,
        )
        db_session.add(issue)
        await db_session.commit()

        resp = await client.get("/api/stats/issues/creators")
        assert resp.status_code == 200
        data = resp.json()

        assert len(data["creators"]) == 1
        creator = data["creators"][0]
        assert creator["github_username"] == "external_user"
        assert creator["display_name"] is None
        assert creator["team"] is None
        assert creator["role"] is None
