"""Integration tests for P2-03: Approval metrics (approved_at, time_to_approve, time_after_approve, merged_without_approval)."""
import pytest
from datetime import datetime, timedelta, timezone

from app.models.models import Developer, PRReview, PullRequest, Repository
from app.services.github_sync import compute_approval_metrics


NOW = datetime.now(timezone.utc)
ONE_WEEK_AGO = NOW - timedelta(days=7)
THREE_DAYS_AGO = NOW - timedelta(days=3)
ONE_DAY_AGO = NOW - timedelta(days=1)


def _strip_tz(dt: datetime) -> datetime:
    """Strip timezone for comparison — SQLite returns naive datetimes."""
    return dt.replace(tzinfo=None) if dt.tzinfo else dt


class TestComputeApprovalMetrics:
    """Unit-style tests for the compute_approval_metrics sync helper."""

    @pytest.mark.asyncio
    async def test_single_approval(self, db_session, sample_repo, sample_developer, sample_developer_b):
        pr = PullRequest(
            github_id=500, repo_id=sample_repo.id, author_id=sample_developer.id,
            number=50, title="Single approval PR", state="closed",
            is_merged=True, created_at=ONE_WEEK_AGO, merged_at=ONE_DAY_AGO,
        )
        db_session.add(pr)
        await db_session.flush()

        review = PRReview(
            github_id=600, pr_id=pr.id, reviewer_id=sample_developer_b.id,
            state="APPROVED", body="LGTM", body_length=4,
            submitted_at=THREE_DAYS_AGO,
        )
        db_session.add(review)
        await db_session.flush()

        await compute_approval_metrics(db_session, pr)

        assert _strip_tz(pr.approved_at) == _strip_tz(THREE_DAYS_AGO)
        assert pr.approval_count == 1
        assert pr.time_to_approve_s == int((THREE_DAYS_AGO - ONE_WEEK_AGO).total_seconds())
        assert pr.time_after_approve_s == int((ONE_DAY_AGO - THREE_DAYS_AGO).total_seconds())
        assert pr.merged_without_approval is False

    @pytest.mark.asyncio
    async def test_multiple_approvals_re_review(self, db_session, sample_repo, sample_developer, sample_developer_b):
        """PR approved twice (re-review cycle) — approved_at should be the last approval."""
        pr = PullRequest(
            github_id=501, repo_id=sample_repo.id, author_id=sample_developer.id,
            number=51, title="Re-reviewed PR", state="closed",
            is_merged=True, created_at=ONE_WEEK_AGO, merged_at=ONE_DAY_AGO,
        )
        db_session.add(pr)
        await db_session.flush()

        # First approval
        review1 = PRReview(
            github_id=601, pr_id=pr.id, reviewer_id=sample_developer_b.id,
            state="APPROVED", body="LGTM", body_length=4,
            submitted_at=ONE_WEEK_AGO + timedelta(days=1),
        )
        # Second approval (after changes requested cycle)
        review2 = PRReview(
            github_id=602, pr_id=pr.id, reviewer_id=sample_developer_b.id,
            state="APPROVED", body="Good now", body_length=8,
            submitted_at=THREE_DAYS_AGO,
        )
        db_session.add_all([review1, review2])
        await db_session.flush()

        await compute_approval_metrics(db_session, pr)

        assert _strip_tz(pr.approved_at) == _strip_tz(THREE_DAYS_AGO)  # last approval
        assert pr.approval_count == 2  # re-review detected
        assert pr.merged_without_approval is False

    @pytest.mark.asyncio
    async def test_merged_without_approval(self, db_session, sample_repo, sample_developer, sample_developer_b):
        pr = PullRequest(
            github_id=502, repo_id=sample_repo.id, author_id=sample_developer.id,
            number=52, title="No approval PR", state="closed",
            is_merged=True, created_at=ONE_WEEK_AGO, merged_at=ONE_DAY_AGO,
        )
        db_session.add(pr)
        await db_session.flush()

        # Only a COMMENTED review, no APPROVED
        review = PRReview(
            github_id=603, pr_id=pr.id, reviewer_id=sample_developer_b.id,
            state="COMMENTED", body="Just a comment", body_length=14,
            submitted_at=THREE_DAYS_AGO,
        )
        db_session.add(review)
        await db_session.flush()

        await compute_approval_metrics(db_session, pr)

        assert pr.approved_at is None
        assert pr.approval_count == 0
        assert pr.time_to_approve_s is None
        assert pr.time_after_approve_s is None
        assert pr.merged_without_approval is True

    @pytest.mark.asyncio
    async def test_merged_no_reviews(self, db_session, sample_repo, sample_developer):
        """Merged PR with zero reviews — merged_without_approval should be True."""
        pr = PullRequest(
            github_id=503, repo_id=sample_repo.id, author_id=sample_developer.id,
            number=53, title="No review PR", state="closed",
            is_merged=True, created_at=ONE_WEEK_AGO, merged_at=ONE_DAY_AGO,
        )
        db_session.add(pr)
        await db_session.flush()

        await compute_approval_metrics(db_session, pr)

        assert pr.merged_without_approval is True
        assert pr.approval_count == 0

    @pytest.mark.asyncio
    async def test_open_pr_with_approval(self, db_session, sample_repo, sample_developer, sample_developer_b):
        """Open PR with approval — time_after_approve_s should be None, merged_without_approval False."""
        pr = PullRequest(
            github_id=504, repo_id=sample_repo.id, author_id=sample_developer.id,
            number=54, title="Open approved PR", state="open",
            is_merged=False, created_at=ONE_WEEK_AGO,
        )
        db_session.add(pr)
        await db_session.flush()

        review = PRReview(
            github_id=604, pr_id=pr.id, reviewer_id=sample_developer_b.id,
            state="APPROVED", body="LGTM", body_length=4,
            submitted_at=THREE_DAYS_AGO,
        )
        db_session.add(review)
        await db_session.flush()

        await compute_approval_metrics(db_session, pr)

        assert _strip_tz(pr.approved_at) == _strip_tz(THREE_DAYS_AGO)
        assert pr.approval_count == 1
        assert pr.time_to_approve_s is not None
        assert pr.time_after_approve_s is None  # not merged yet
        assert pr.merged_without_approval is False  # not merged


class TestApprovalStatsAPI:
    """Integration tests for approval metrics in the stats API."""

    @pytest.mark.asyncio
    async def test_developer_stats_includes_approval_fields(
        self, client, sample_developer, sample_repo, sample_developer_b, db_session
    ):
        """Stats response includes new approval fields with correct values."""
        pr = PullRequest(
            github_id=510, repo_id=sample_repo.id, author_id=sample_developer.id,
            number=60, title="Approved PR", state="closed",
            is_merged=True, created_at=ONE_WEEK_AGO, merged_at=ONE_DAY_AGO,
            time_to_merge_s=int((ONE_DAY_AGO - ONE_WEEK_AGO).total_seconds()),
            approved_at=THREE_DAYS_AGO,
            approval_count=1,
            time_to_approve_s=int((THREE_DAYS_AGO - ONE_WEEK_AGO).total_seconds()),
            time_after_approve_s=int((ONE_DAY_AGO - THREE_DAYS_AGO).total_seconds()),
            merged_without_approval=False,
        )
        db_session.add(pr)
        await db_session.commit()

        resp = await client.get(f"/api/stats/developer/{sample_developer.id}")
        assert resp.status_code == 200
        data = resp.json()

        assert data["avg_time_to_approve_hours"] is not None
        assert data["avg_time_to_approve_hours"] > 0
        assert data["avg_time_after_approve_hours"] is not None
        assert data["avg_time_after_approve_hours"] > 0
        assert data["prs_merged_without_approval"] == 0

    @pytest.mark.asyncio
    async def test_developer_stats_merged_without_approval_count(
        self, client, sample_developer, sample_repo, db_session
    ):
        """prs_merged_without_approval counts correctly."""
        pr = PullRequest(
            github_id=511, repo_id=sample_repo.id, author_id=sample_developer.id,
            number=61, title="No approval merge", state="closed",
            is_merged=True, created_at=ONE_WEEK_AGO, merged_at=ONE_DAY_AGO,
            time_to_merge_s=int((ONE_DAY_AGO - ONE_WEEK_AGO).total_seconds()),
            merged_without_approval=True,
            approval_count=0,
        )
        db_session.add(pr)
        await db_session.commit()

        resp = await client.get(f"/api/stats/developer/{sample_developer.id}")
        assert resp.status_code == 200
        data = resp.json()
        assert data["prs_merged_without_approval"] == 1

    @pytest.mark.asyncio
    async def test_developer_stats_no_approval_data(self, client, sample_developer):
        """When there are no PRs, approval fields should be None/0."""
        resp = await client.get(f"/api/stats/developer/{sample_developer.id}")
        assert resp.status_code == 200
        data = resp.json()
        assert data["avg_time_to_approve_hours"] is None
        assert data["avg_time_after_approve_hours"] is None
        assert data["prs_merged_without_approval"] == 0


class TestApprovalBenchmarks:
    @pytest.fixture(autouse=True)
    async def seed_groups(self, db_session):
        from app.models.models import BenchmarkGroupConfig
        group = BenchmarkGroupConfig(
            group_key="ics", display_name="IC Engineers", display_order=1,
            roles=["developer", "senior_developer", "lead", "architect", "intern"],
            metrics=["prs_merged", "time_to_merge_h", "time_to_approve_h", "time_after_approve_h", "reviews_given"],
            min_team_size=3, is_default=True,
        )
        db_session.add(group)
        await db_session.commit()

    @pytest.mark.asyncio
    async def test_benchmarks_include_approval_metrics(
        self, client, sample_developer, sample_developer_b, sample_repo, db_session
    ):
        """Benchmarks response includes time_to_approve_h and time_after_approve_h."""
        pr = PullRequest(
            github_id=520, repo_id=sample_repo.id, author_id=sample_developer.id,
            number=70, title="Benchmark PR", state="closed",
            is_merged=True, created_at=ONE_WEEK_AGO, merged_at=ONE_DAY_AGO,
            time_to_approve_s=int((THREE_DAYS_AGO - ONE_WEEK_AGO).total_seconds()),
            time_after_approve_s=int((ONE_DAY_AGO - THREE_DAYS_AGO).total_seconds()),
        )
        db_session.add(pr)
        await db_session.commit()

        resp = await client.get("/api/stats/benchmarks")
        assert resp.status_code == 200
        data = resp.json()
        assert "time_to_approve_h" in data["metrics"]
        assert "time_after_approve_h" in data["metrics"]
        assert "p25" in data["metrics"]["time_to_approve_h"]
        assert "p50" in data["metrics"]["time_to_approve_h"]
        assert "p75" in data["metrics"]["time_to_approve_h"]


class TestMergedWithoutApprovalAlerts:
    @pytest.mark.asyncio
    async def test_workload_alerts_merged_without_approval(
        self, client, sample_developer, sample_repo, db_session
    ):
        """Workload endpoint fires both per-dev and team alerts for merged-without-approval."""
        pr = PullRequest(
            github_id=530, repo_id=sample_repo.id, author_id=sample_developer.id,
            number=80, title="Unapproved merge", state="closed",
            is_merged=True, created_at=ONE_WEEK_AGO, merged_at=ONE_DAY_AGO,
            merged_without_approval=True, approval_count=0,
        )
        db_session.add(pr)
        await db_session.commit()

        resp = await client.get("/api/stats/workload")
        assert resp.status_code == 200
        data = resp.json()

        alert_types = [a["type"] for a in data["alerts"]]
        assert "merged_without_approval" in alert_types

        # Should have both per-developer and team-level alerts
        mwa_alerts = [a for a in data["alerts"] if a["type"] == "merged_without_approval"]
        per_dev = [a for a in mwa_alerts if a.get("developer_id") is not None]
        team_level = [a for a in mwa_alerts if a.get("developer_id") is None]
        assert len(per_dev) >= 1
        assert len(team_level) >= 1
