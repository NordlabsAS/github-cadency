"""Integration tests for draft PR filtering in stats and workload."""
import pytest
import pytest_asyncio
from datetime import timedelta

from conftest import NOW, ONE_WEEK_AGO
from app.models.models import Developer, PullRequest, Repository


@pytest_asyncio.fixture
async def sample_draft_pr(
    db_session, sample_developer, sample_repo
) -> PullRequest:
    """An open draft PR — should be excluded from prs_open and workload counts."""
    pr = PullRequest(
        github_id=901,
        repo_id=sample_repo.id,
        author_id=sample_developer.id,
        number=901,
        title="WIP: new feature",
        state="open",
        is_merged=False,
        is_draft=True,
        additions=10,
        deletions=2,
        changed_files=1,
        created_at=ONE_WEEK_AGO,
    )
    db_session.add(pr)
    await db_session.commit()
    await db_session.refresh(pr)
    return pr


@pytest_asyncio.fixture
async def sample_open_pr(
    db_session, sample_developer, sample_repo
) -> PullRequest:
    """A regular open PR (not draft) — should be included in prs_open."""
    pr = PullRequest(
        github_id=902,
        repo_id=sample_repo.id,
        author_id=sample_developer.id,
        number=902,
        title="Ready for review",
        state="open",
        is_merged=False,
        is_draft=False,
        additions=20,
        deletions=5,
        changed_files=2,
        created_at=ONE_WEEK_AGO,
    )
    db_session.add(pr)
    await db_session.commit()
    await db_session.refresh(pr)
    return pr


@pytest_asyncio.fixture
async def stale_draft_pr(
    db_session, sample_developer, sample_repo
) -> PullRequest:
    """A draft PR open for >48h with no reviews — should NOT trigger stale alert."""
    pr = PullRequest(
        github_id=903,
        repo_id=sample_repo.id,
        author_id=sample_developer.id,
        number=903,
        title="WIP: long running draft",
        state="open",
        is_merged=False,
        is_draft=True,
        additions=5,
        deletions=1,
        changed_files=1,
        created_at=NOW - timedelta(days=5),
        first_review_at=None,
    )
    db_session.add(pr)
    await db_session.commit()
    await db_session.refresh(pr)
    return pr


@pytest_asyncio.fixture
async def stale_regular_pr(
    db_session, sample_developer, sample_repo
) -> PullRequest:
    """A regular PR open for >48h with no reviews — SHOULD trigger stale alert."""
    pr = PullRequest(
        github_id=904,
        repo_id=sample_repo.id,
        author_id=sample_developer.id,
        number=904,
        title="Needs review urgently",
        state="open",
        is_merged=False,
        is_draft=False,
        additions=30,
        deletions=10,
        changed_files=3,
        created_at=NOW - timedelta(days=5),
        first_review_at=None,
    )
    db_session.add(pr)
    await db_session.commit()
    await db_session.refresh(pr)
    return pr


class TestDeveloperStatsDraftFiltering:
    @pytest.mark.asyncio
    async def test_prs_open_excludes_drafts(
        self, client, sample_developer, sample_draft_pr, sample_open_pr
    ):
        resp = await client.get(f"/api/stats/developer/{sample_developer.id}")
        assert resp.status_code == 200
        data = resp.json()
        assert data["prs_open"] == 1  # only the non-draft open PR
        assert data["prs_draft"] == 1  # the draft PR counted separately

    @pytest.mark.asyncio
    async def test_prs_draft_zero_when_no_drafts(
        self, client, sample_developer, sample_open_pr
    ):
        resp = await client.get(f"/api/stats/developer/{sample_developer.id}")
        assert resp.status_code == 200
        data = resp.json()
        assert data["prs_open"] == 1
        assert data["prs_draft"] == 0

    @pytest.mark.asyncio
    async def test_only_draft_prs(
        self, client, sample_developer, sample_draft_pr
    ):
        resp = await client.get(f"/api/stats/developer/{sample_developer.id}")
        assert resp.status_code == 200
        data = resp.json()
        assert data["prs_open"] == 0
        assert data["prs_draft"] == 1


class TestWorkloadDraftFiltering:
    @pytest.mark.asyncio
    async def test_workload_excludes_drafts_from_open_authored(
        self, client, sample_developer, sample_draft_pr, sample_open_pr
    ):
        resp = await client.get("/api/stats/workload")
        assert resp.status_code == 200
        data = resp.json()
        dev_workload = next(
            d for d in data["developers"]
            if d["developer_id"] == sample_developer.id
        )
        assert dev_workload["open_prs_authored"] == 1  # excludes draft
        assert dev_workload["drafts_open"] == 1

    @pytest.mark.asyncio
    async def test_workload_excludes_drafts_from_waiting_for_review(
        self, client, sample_developer, sample_draft_pr, sample_open_pr
    ):
        resp = await client.get("/api/stats/workload")
        assert resp.status_code == 200
        data = resp.json()
        dev_workload = next(
            d for d in data["developers"]
            if d["developer_id"] == sample_developer.id
        )
        # Both PRs have no first_review_at, but draft should be excluded
        assert dev_workload["prs_waiting_for_review"] == 1

    @pytest.mark.asyncio
    async def test_workload_score_excludes_reviews_given(
        self, client, sample_developer
    ):
        """Workload score should only count pending work, not completed reviews."""
        resp = await client.get("/api/stats/workload")
        assert resp.status_code == 200
        data = resp.json()
        dev_workload = next(
            d for d in data["developers"]
            if d["developer_id"] == sample_developer.id
        )
        # With 0 open items, score should be "low" regardless of reviews_given
        assert dev_workload["workload_score"] == "low"


class TestStaleAlertsDraftFiltering:
    @pytest.mark.asyncio
    async def test_stale_alert_excludes_draft_prs(
        self, client, sample_developer, stale_draft_pr
    ):
        resp = await client.get("/api/stats/workload")
        assert resp.status_code == 200
        data = resp.json()
        stale_alerts = [a for a in data["alerts"] if a["type"] == "stale_prs"]
        # Draft PR open >48h should NOT generate a stale alert
        draft_alerts = [a for a in stale_alerts if "903" in a["message"]]
        assert len(draft_alerts) == 0

    @pytest.mark.asyncio
    async def test_stale_alert_includes_regular_prs(
        self, client, sample_developer, stale_regular_pr
    ):
        resp = await client.get("/api/stats/workload")
        assert resp.status_code == 200
        data = resp.json()
        stale_alerts = [a for a in data["alerts"] if a["type"] == "stale_prs"]
        regular_alerts = [a for a in stale_alerts if "904" in a["message"]]
        assert len(regular_alerts) == 1

    @pytest.mark.asyncio
    async def test_stale_alert_only_for_regular_not_draft(
        self, client, sample_developer, stale_draft_pr, stale_regular_pr
    ):
        resp = await client.get("/api/stats/workload")
        assert resp.status_code == 200
        data = resp.json()
        stale_alerts = [a for a in data["alerts"] if a["type"] == "stale_prs"]
        # Only the regular stale PR should generate an alert
        assert len(stale_alerts) == 1
        assert "904" in stale_alerts[0]["message"]
