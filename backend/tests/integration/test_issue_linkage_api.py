"""Integration tests for the /api/stats/issue-linkage endpoint."""
from datetime import timedelta

import pytest

from app.models.models import Issue, PullRequest
from conftest import NOW, ONE_WEEK_AGO, ONE_DAY_AGO


class TestIssueLinkageEndpoint:
    @pytest.mark.asyncio
    async def test_empty_database(self, client):
        resp = await client.get("/api/stats/issue-linkage")
        assert resp.status_code == 200
        data = resp.json()
        assert data["issues_with_linked_prs"] == 0
        assert data["issues_without_linked_prs"] == 0
        assert data["avg_prs_per_issue"] is None
        assert data["issues_with_multiple_prs"] == 0
        assert data["prs_without_linked_issues"] == 0

    @pytest.mark.asyncio
    async def test_linked_issue(
        self, client, db_session, sample_developer, sample_repo
    ):
        """PR with closing keyword linked to a closed issue."""
        # Create a closed issue #10
        issue = Issue(
            github_id=400,
            repo_id=sample_repo.id,
            assignee_id=sample_developer.id,
            number=10,
            title="Bug report",
            state="closed",
            created_at=ONE_WEEK_AGO,
            closed_at=ONE_DAY_AGO,
        )
        # Create a PR that closes #10
        pr = PullRequest(
            github_id=401,
            repo_id=sample_repo.id,
            author_id=sample_developer.id,
            number=20,
            title="Fix the bug",
            body="Fixes #10",
            state="closed",
            is_merged=True,
            closes_issue_numbers=[10],
            created_at=ONE_WEEK_AGO,
            merged_at=ONE_DAY_AGO,
        )
        db_session.add_all([issue, pr])
        await db_session.commit()

        resp = await client.get("/api/stats/issue-linkage")
        assert resp.status_code == 200
        data = resp.json()
        assert data["issues_with_linked_prs"] == 1
        assert data["issues_without_linked_prs"] == 0
        assert data["avg_prs_per_issue"] == 1.0
        assert data["issues_with_multiple_prs"] == 0
        assert data["prs_without_linked_issues"] == 0

    @pytest.mark.asyncio
    async def test_unlinked_issue_and_pr(
        self, client, db_session, sample_developer, sample_repo
    ):
        """Closed issue with no PR referencing it + PR with no closing keywords."""
        issue = Issue(
            github_id=402,
            repo_id=sample_repo.id,
            assignee_id=sample_developer.id,
            number=11,
            title="Unlinked issue",
            state="closed",
            created_at=ONE_WEEK_AGO,
            closed_at=ONE_DAY_AGO,
        )
        pr = PullRequest(
            github_id=403,
            repo_id=sample_repo.id,
            author_id=sample_developer.id,
            number=21,
            title="Random fix",
            body="Just some cleanup",
            state="closed",
            is_merged=True,
            closes_issue_numbers=[],
            created_at=ONE_WEEK_AGO,
            merged_at=ONE_DAY_AGO,
        )
        db_session.add_all([issue, pr])
        await db_session.commit()

        resp = await client.get("/api/stats/issue-linkage")
        assert resp.status_code == 200
        data = resp.json()
        assert data["issues_with_linked_prs"] == 0
        assert data["issues_without_linked_prs"] == 1
        assert data["prs_without_linked_issues"] == 1

    @pytest.mark.asyncio
    async def test_multiple_prs_per_issue(
        self, client, db_session, sample_developer, sample_repo
    ):
        """Issue referenced by 2 PRs."""
        issue = Issue(
            github_id=404,
            repo_id=sample_repo.id,
            assignee_id=sample_developer.id,
            number=12,
            title="Complex bug",
            state="closed",
            created_at=ONE_WEEK_AGO,
            closed_at=ONE_DAY_AGO,
        )
        pr1 = PullRequest(
            github_id=405,
            repo_id=sample_repo.id,
            author_id=sample_developer.id,
            number=22,
            title="Partial fix",
            body="Fixes #12",
            state="closed",
            is_merged=True,
            closes_issue_numbers=[12],
            created_at=ONE_WEEK_AGO,
            merged_at=ONE_DAY_AGO,
        )
        pr2 = PullRequest(
            github_id=406,
            repo_id=sample_repo.id,
            author_id=sample_developer.id,
            number=23,
            title="Complete fix",
            body="Closes #12",
            state="closed",
            is_merged=True,
            closes_issue_numbers=[12],
            created_at=ONE_WEEK_AGO,
            merged_at=ONE_DAY_AGO,
        )
        db_session.add_all([issue, pr1, pr2])
        await db_session.commit()

        resp = await client.get("/api/stats/issue-linkage")
        assert resp.status_code == 200
        data = resp.json()
        assert data["issues_with_linked_prs"] == 1
        assert data["issues_with_multiple_prs"] == 1
        assert data["avg_prs_per_issue"] == 2.0
        assert data["prs_without_linked_issues"] == 0

    @pytest.mark.asyncio
    async def test_requires_admin(self, developer_client):
        resp = await developer_client.get("/api/stats/issue-linkage")
        assert resp.status_code == 403

    @pytest.mark.asyncio
    async def test_team_filter(
        self, client, db_session, sample_developer, sample_repo
    ):
        """Team filter excludes issues/PRs from other teams."""
        issue = Issue(
            github_id=407,
            repo_id=sample_repo.id,
            assignee_id=sample_developer.id,
            number=13,
            title="Team bug",
            state="closed",
            created_at=ONE_WEEK_AGO,
            closed_at=ONE_DAY_AGO,
        )
        pr = PullRequest(
            github_id=408,
            repo_id=sample_repo.id,
            author_id=sample_developer.id,
            number=24,
            title="Team fix",
            body="Fixes #13",
            state="closed",
            is_merged=True,
            closes_issue_numbers=[13],
            created_at=ONE_WEEK_AGO,
            merged_at=ONE_DAY_AGO,
        )
        db_session.add_all([issue, pr])
        await db_session.commit()

        # sample_developer is on "backend" team
        resp = await client.get("/api/stats/issue-linkage?team=backend")
        assert resp.status_code == 200
        data = resp.json()
        assert data["issues_with_linked_prs"] == 1

        # Non-existent team returns zeros
        resp = await client.get("/api/stats/issue-linkage?team=nonexistent")
        assert resp.status_code == 200
        data = resp.json()
        assert data["issues_with_linked_prs"] == 0
