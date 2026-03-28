"""Integration tests for revert PR detection stats."""
import pytest
from datetime import timedelta
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.models import Developer, PullRequest, Repository

from conftest import NOW, ONE_DAY_AGO, ONE_WEEK_AGO


class TestRevertDeveloperStats:
    @pytest.mark.asyncio
    async def test_prs_reverted_counts_original_author(
        self, client, sample_developer, sample_developer_b, sample_pr, sample_repo, db_session: AsyncSession
    ):
        """A revert PR by dev_b referencing dev_a's PR should increment dev_a's prs_reverted."""
        # sample_pr is PR #1 authored by sample_developer
        # Create a revert PR by sample_developer_b referencing PR #1
        revert_pr = PullRequest(
            github_id=999,
            repo_id=sample_repo.id,
            author_id=sample_developer_b.id,
            number=2,
            title='Revert "Fix bug"',
            body="Reverts #1",
            state="closed",
            is_merged=True,
            is_revert=True,
            reverted_pr_number=1,
            created_at=ONE_DAY_AGO,
            merged_at=NOW,
        )
        db_session.add(revert_pr)
        await db_session.commit()

        resp = await client.get(f"/api/stats/developer/{sample_developer.id}")
        assert resp.status_code == 200
        data = resp.json()
        assert data["prs_reverted"] == 1
        assert data["reverts_authored"] == 0

    @pytest.mark.asyncio
    async def test_reverts_authored_counts_revert_author(
        self, client, sample_developer, sample_developer_b, sample_pr, sample_repo, db_session: AsyncSession
    ):
        """The developer who authored the revert PR gets reverts_authored incremented."""
        revert_pr = PullRequest(
            github_id=999,
            repo_id=sample_repo.id,
            author_id=sample_developer_b.id,
            number=2,
            title='Revert "Fix bug"',
            body="Reverts #1",
            state="closed",
            is_merged=True,
            is_revert=True,
            reverted_pr_number=1,
            created_at=ONE_DAY_AGO,
            merged_at=NOW,
        )
        db_session.add(revert_pr)
        await db_session.commit()

        resp = await client.get(f"/api/stats/developer/{sample_developer_b.id}")
        assert resp.status_code == 200
        data = resp.json()
        assert data["reverts_authored"] == 1
        assert data["prs_reverted"] == 0

    @pytest.mark.asyncio
    async def test_no_reverts(self, client, sample_developer, sample_pr):
        resp = await client.get(f"/api/stats/developer/{sample_developer.id}")
        assert resp.status_code == 200
        data = resp.json()
        assert data["prs_reverted"] == 0
        assert data["reverts_authored"] == 0


class TestRevertTeamStats:
    @pytest.mark.asyncio
    async def test_team_revert_rate(
        self, client, sample_developer, sample_pr, sample_repo, db_session: AsyncSession
    ):
        revert_pr = PullRequest(
            github_id=999,
            repo_id=sample_repo.id,
            author_id=sample_developer.id,
            number=2,
            title='Revert "Fix bug"',
            body="Reverts #1",
            state="closed",
            is_merged=True,
            is_revert=True,
            reverted_pr_number=1,
            created_at=ONE_DAY_AGO,
            merged_at=NOW,
        )
        db_session.add(revert_pr)
        await db_session.commit()

        resp = await client.get("/api/stats/team")
        assert resp.status_code == 200
        data = resp.json()
        # 1 revert out of 2 merged PRs = 0.5
        assert data["revert_rate"] == 0.5

    @pytest.mark.asyncio
    async def test_team_revert_rate_zero(
        self, client, sample_developer, sample_pr
    ):
        resp = await client.get("/api/stats/team")
        assert resp.status_code == 200
        data = resp.json()
        assert data["revert_rate"] == 0.0

    @pytest.mark.asyncio
    async def test_team_revert_rate_none_no_merges(self, client, sample_developer):
        resp = await client.get("/api/stats/team")
        assert resp.status_code == 200
        data = resp.json()
        assert data["revert_rate"] is None
