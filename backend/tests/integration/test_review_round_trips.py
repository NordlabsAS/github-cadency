"""Integration tests for P2-02: Review Round-Trip Count feature."""
import pytest
from datetime import timedelta

from app.models.models import Developer, PRReview, PullRequest, Repository

# Import shared fixtures and time constants
from conftest import NOW, ONE_DAY_AGO, ONE_WEEK_AGO


class TestReviewRoundTripsInDeveloperStats:
    @pytest.mark.asyncio
    async def test_first_pass_pr_stats(
        self, client, sample_developer, sample_pr, sample_review
    ):
        """A merged PR with 0 CHANGES_REQUESTED reviews = first pass."""
        resp = await client.get(f"/api/stats/developer/{sample_developer.id}")
        assert resp.status_code == 200
        data = resp.json()
        assert data["avg_review_rounds"] == 0.0
        assert data["prs_merged_first_pass"] == 1
        assert data["first_pass_rate"] == 1.0

    @pytest.mark.asyncio
    async def test_pr_with_changes_requested(
        self, db_session, client, sample_developer, sample_developer_b, sample_repo
    ):
        """A PR with CHANGES_REQUESTED reviews should increase review rounds."""
        pr = PullRequest(
            github_id=500,
            repo_id=sample_repo.id,
            author_id=sample_developer.id,
            number=50,
            title="Feature PR",
            state="closed",
            is_merged=True,
            review_round_count=2,
            created_at=ONE_WEEK_AGO,
            merged_at=ONE_DAY_AGO,
            time_to_merge_s=int((ONE_DAY_AGO - ONE_WEEK_AGO).total_seconds()),
        )
        db_session.add(pr)
        await db_session.commit()

        resp = await client.get(f"/api/stats/developer/{sample_developer.id}")
        assert resp.status_code == 200
        data = resp.json()
        # Only this one PR with 2 rounds
        assert data["avg_review_rounds"] == 2.0
        assert data["prs_merged_first_pass"] == 0
        assert data["first_pass_rate"] == 0.0

    @pytest.mark.asyncio
    async def test_mixed_prs_stats(
        self, db_session, client, sample_developer, sample_repo
    ):
        """Mixed PRs: one first-pass, one with rounds."""
        pr1 = PullRequest(
            github_id=601,
            repo_id=sample_repo.id,
            author_id=sample_developer.id,
            number=61,
            title="Clean PR",
            state="closed",
            is_merged=True,
            review_round_count=0,
            created_at=ONE_WEEK_AGO,
            merged_at=ONE_DAY_AGO,
            time_to_merge_s=3600,
        )
        pr2 = PullRequest(
            github_id=602,
            repo_id=sample_repo.id,
            author_id=sample_developer.id,
            number=62,
            title="Iterated PR",
            state="closed",
            is_merged=True,
            review_round_count=3,
            created_at=ONE_WEEK_AGO,
            merged_at=ONE_DAY_AGO,
            time_to_merge_s=7200,
        )
        db_session.add_all([pr1, pr2])
        await db_session.commit()

        resp = await client.get(f"/api/stats/developer/{sample_developer.id}")
        assert resp.status_code == 200
        data = resp.json()
        assert data["avg_review_rounds"] == 1.5  # (0 + 3) / 2
        assert data["prs_merged_first_pass"] == 1
        assert data["first_pass_rate"] == 0.5

    @pytest.mark.asyncio
    async def test_no_merged_prs_returns_none(self, client, sample_developer):
        """No merged PRs means avg_review_rounds and first_pass_rate are None."""
        resp = await client.get(f"/api/stats/developer/{sample_developer.id}")
        assert resp.status_code == 200
        data = resp.json()
        assert data["avg_review_rounds"] is None
        assert data["prs_merged_first_pass"] == 0
        assert data["first_pass_rate"] is None


class TestReviewRoundTripsInTeamStats:
    @pytest.mark.asyncio
    async def test_team_stats_include_review_rounds(
        self, db_session, client, sample_developer, sample_repo
    ):
        pr = PullRequest(
            github_id=700,
            repo_id=sample_repo.id,
            author_id=sample_developer.id,
            number=70,
            title="Team PR",
            state="closed",
            is_merged=True,
            review_round_count=1,
            created_at=ONE_WEEK_AGO,
            merged_at=ONE_DAY_AGO,
            time_to_merge_s=3600,
        )
        db_session.add(pr)
        await db_session.commit()

        resp = await client.get("/api/stats/team")
        assert resp.status_code == 200
        data = resp.json()
        assert data["avg_review_rounds"] == 1.0
        assert data["first_pass_rate"] == 0.0


class TestReviewRoundsInBenchmarks:
    @pytest.fixture(autouse=True)
    async def seed_groups(self, db_session):
        from app.models.models import BenchmarkGroupConfig
        group = BenchmarkGroupConfig(
            group_key="ics", display_name="IC Engineers", display_order=1,
            roles=["developer", "senior_developer", "lead", "architect", "intern"],
            metrics=["prs_merged", "time_to_merge_h", "review_rounds", "reviews_given"],
            min_team_size=3, is_default=True,
        )
        db_session.add(group)
        await db_session.commit()

    @pytest.mark.asyncio
    async def test_benchmarks_include_review_rounds(
        self, db_session, client, sample_developer, sample_developer_b, sample_repo
    ):
        """Benchmarks should include review_rounds metric."""
        for i, dev in enumerate([sample_developer, sample_developer_b]):
            pr = PullRequest(
                github_id=800 + i,
                repo_id=sample_repo.id,
                author_id=dev.id,
                number=80 + i,
                title=f"PR {i}",
                state="closed",
                is_merged=True,
                review_round_count=i,
                created_at=ONE_WEEK_AGO,
                merged_at=ONE_DAY_AGO,
                time_to_merge_s=3600,
            )
            db_session.add(pr)
        await db_session.commit()

        resp = await client.get("/api/stats/benchmarks")
        assert resp.status_code == 200
        data = resp.json()
        assert "review_rounds" in data["metrics"]
        metric = data["metrics"]["review_rounds"]
        assert "p25" in metric
        assert "p50" in metric
        assert "p75" in metric
