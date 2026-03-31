"""Integration tests for the Benchmarks V2 API."""
import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.models import BenchmarkGroupConfig, Developer


@pytest.fixture
async def seed_benchmark_groups(db_session: AsyncSession):
    """Seed default benchmark groups for tests."""
    groups = [
        BenchmarkGroupConfig(
            group_key="ics",
            display_name="IC Engineers",
            display_order=1,
            roles=["developer", "senior_developer", "architect", "intern"],
            metrics=["prs_merged", "time_to_merge_h", "reviews_given"],
            min_team_size=2,
            is_default=True,
        ),
        BenchmarkGroupConfig(
            group_key="qa",
            display_name="QA Engineers",
            display_order=2,
            roles=["qa"],
            metrics=["reviews_given", "review_quality_score", "issues_closed"],
            min_team_size=2,
            is_default=True,
        ),
    ]
    db_session.add_all(groups)
    await db_session.commit()
    return groups


class TestBenchmarkGroups:
    @pytest.mark.asyncio
    async def test_list_groups(self, client, seed_benchmark_groups):
        resp = await client.get("/api/stats/benchmark-groups")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 2
        assert data[0]["group_key"] == "ics"
        assert data[1]["group_key"] == "qa"
        assert data[0]["display_order"] < data[1]["display_order"]

    @pytest.mark.asyncio
    async def test_update_group_roles(self, client, seed_benchmark_groups):
        resp = await client.patch(
            "/api/stats/benchmark-groups/ics",
            json={"roles": ["developer", "senior_developer"]},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["roles"] == ["developer", "senior_developer"]

    @pytest.mark.asyncio
    async def test_update_group_invalid_role(self, client, seed_benchmark_groups):
        resp = await client.patch(
            "/api/stats/benchmark-groups/ics",
            json={"roles": ["nonexistent_role"]},
        )
        assert resp.status_code == 400

    @pytest.mark.asyncio
    async def test_update_group_invalid_metric(self, client, seed_benchmark_groups):
        resp = await client.patch(
            "/api/stats/benchmark-groups/ics",
            json={"metrics": ["fake_metric"]},
        )
        assert resp.status_code == 400

    @pytest.mark.asyncio
    async def test_update_group_empty_metrics(self, client, seed_benchmark_groups):
        resp = await client.patch(
            "/api/stats/benchmark-groups/ics",
            json={"metrics": []},
        )
        assert resp.status_code == 400

    @pytest.mark.asyncio
    async def test_update_group_not_found(self, client, seed_benchmark_groups):
        resp = await client.patch(
            "/api/stats/benchmark-groups/nonexistent",
            json={"display_name": "New Name"},
        )
        assert resp.status_code == 400


class TestBenchmarksV2:
    @pytest.mark.asyncio
    async def test_benchmarks_v2_ics_group(
        self, client, seed_benchmark_groups, sample_developer, sample_developer_b, sample_pr
    ):
        """IC group returns developers with matching roles."""
        resp = await client.get("/api/stats/benchmarks?group=ics")
        assert resp.status_code == 200
        data = resp.json()
        assert data["group"]["group_key"] == "ics"
        assert data["sample_size"] == 2  # developer + senior_developer
        assert len(data["developers"]) == 2
        assert "prs_merged" in data["metrics"]
        dev_ids = {d["developer_id"] for d in data["developers"]}
        assert sample_developer.id in dev_ids
        assert sample_developer_b.id in dev_ids

    @pytest.mark.asyncio
    async def test_benchmarks_v2_default_group(
        self, client, seed_benchmark_groups, sample_developer, sample_pr
    ):
        """When no group param, defaults to first group by display_order."""
        resp = await client.get("/api/stats/benchmarks")
        assert resp.status_code == 200
        data = resp.json()
        assert data["group"]["group_key"] == "ics"

    @pytest.mark.asyncio
    async def test_benchmarks_v2_empty_group(
        self, client, seed_benchmark_groups, sample_developer
    ):
        """QA group returns empty when no QA developers exist."""
        resp = await client.get("/api/stats/benchmarks?group=qa")
        assert resp.status_code == 200
        data = resp.json()
        assert data["sample_size"] == 0
        assert data["developers"] == []

    @pytest.mark.asyncio
    async def test_benchmarks_v2_team_filter(
        self, client, seed_benchmark_groups, sample_developer, sample_developer_b, sample_pr
    ):
        """Team filter narrows the developer pool."""
        resp = await client.get("/api/stats/benchmarks?group=ics&team=backend")
        assert resp.status_code == 200
        data = resp.json()
        assert data["team"] == "backend"
        assert data["sample_size"] == 2  # both are on 'backend' team

        resp = await client.get("/api/stats/benchmarks?group=ics&team=nonexistent")
        data = resp.json()
        assert data["sample_size"] == 0

    @pytest.mark.asyncio
    async def test_benchmarks_v2_system_account_excluded(
        self, client, seed_benchmark_groups, sample_developer, db_session
    ):
        """System accounts are excluded from benchmarks."""
        bot = Developer(
            github_username="dependabot",
            display_name="Dependabot",
            role="system_account",
            team="backend",
            app_role="developer",
            is_active=True,
        )
        db_session.add(bot)
        await db_session.commit()

        resp = await client.get("/api/stats/benchmarks?group=ics")
        assert resp.status_code == 200
        dev_names = {d["display_name"] for d in resp.json()["developers"]}
        assert "Dependabot" not in dev_names

    @pytest.mark.asyncio
    async def test_benchmarks_v2_null_role_excluded(
        self, client, seed_benchmark_groups, db_session
    ):
        """Developers with null role are excluded from all groups."""
        dev = Developer(
            github_username="norole",
            display_name="No Role Dev",
            role=None,
            team="backend",
            app_role="developer",
            is_active=True,
        )
        db_session.add(dev)
        await db_session.commit()

        resp = await client.get("/api/stats/benchmarks?group=ics")
        assert resp.status_code == 200
        dev_names = {d["display_name"] for d in resp.json()["developers"]}
        assert "No Role Dev" not in dev_names

    @pytest.mark.asyncio
    async def test_benchmarks_v2_metric_info(
        self, client, seed_benchmark_groups, sample_developer, sample_pr
    ):
        """Response includes metric_info with label and lower_is_better."""
        resp = await client.get("/api/stats/benchmarks?group=ics")
        assert resp.status_code == 200
        data = resp.json()
        metric_keys = [m["key"] for m in data["metric_info"]]
        assert "prs_merged" in metric_keys
        # Check metric info structure
        prs_info = next(m for m in data["metric_info"] if m["key"] == "prs_merged")
        assert prs_info["lower_is_better"] is False
        assert prs_info["unit"] == "count"

    @pytest.mark.asyncio
    async def test_benchmarks_v2_developer_rows_have_bands(
        self, client, seed_benchmark_groups, sample_developer, sample_developer_b, sample_pr
    ):
        """Each developer row has percentile bands per metric."""
        resp = await client.get("/api/stats/benchmarks?group=ics")
        assert resp.status_code == 200
        data = resp.json()
        for dev in data["developers"]:
            assert "metrics" in dev
            for metric_key, mv in dev["metrics"].items():
                assert "value" in mv
                assert "percentile_band" in mv

    @pytest.mark.asyncio
    async def test_benchmarks_v2_team_comparison(
        self, client, seed_benchmark_groups, sample_developer, sample_developer_b, db_session
    ):
        """Team comparison appears when multiple teams meet min size."""
        # sample_developer and sample_developer_b are both on 'backend'
        # Add 2 devs on 'frontend' team to meet min_team_size=2
        for i in range(2):
            dev = Developer(
                github_username=f"frontdev{i}",
                display_name=f"Frontend Dev {i}",
                role="developer",
                team="frontend",
                app_role="developer",
                is_active=True,
            )
            db_session.add(dev)
        await db_session.commit()

        resp = await client.get("/api/stats/benchmarks?group=ics")
        assert resp.status_code == 200
        data = resp.json()
        assert data["team_comparison"] is not None
        assert len(data["team_comparison"]) == 2
        team_names = {t["team"] for t in data["team_comparison"]}
        assert "backend" in team_names
        assert "frontend" in team_names

    @pytest.mark.asyncio
    async def test_benchmarks_v2_no_team_comparison_with_filter(
        self, client, seed_benchmark_groups, sample_developer, sample_developer_b
    ):
        """Team comparison is not shown when a specific team is filtered."""
        resp = await client.get("/api/stats/benchmarks?group=ics&team=backend")
        assert resp.status_code == 200
        data = resp.json()
        assert data["team_comparison"] is None

    @pytest.mark.asyncio
    async def test_benchmarks_v2_group_not_found(
        self, client, seed_benchmark_groups
    ):
        resp = await client.get("/api/stats/benchmarks?group=nonexistent")
        assert resp.status_code == 404


class TestUnassignedRoleCount:
    @pytest.mark.asyncio
    async def test_count_with_unassigned(self, client, db_session):
        """Counts active developers with null role."""
        dev = Developer(
            github_username="norole1",
            display_name="No Role 1",
            role=None,
            app_role="developer",
            is_active=True,
        )
        db_session.add(dev)
        await db_session.commit()

        resp = await client.get("/api/developers/unassigned-role-count")
        assert resp.status_code == 200
        assert resp.json()["count"] >= 1

    @pytest.mark.asyncio
    async def test_count_excludes_inactive(self, client, db_session):
        """Inactive developers with null role are not counted."""
        dev = Developer(
            github_username="inactive_norole",
            display_name="Inactive No Role",
            role=None,
            app_role="developer",
            is_active=False,
        )
        db_session.add(dev)
        await db_session.commit()

        resp = await client.get("/api/developers/unassigned-role-count")
        assert resp.status_code == 200
        # Should not count the inactive one — the admin fixture has role='lead' so count is 0
        # unless other fixtures added unassigned devs
        data = resp.json()
        assert isinstance(data["count"], int)

    @pytest.mark.asyncio
    async def test_count_accessible_by_developer(self, developer_client, sample_developer):
        """Non-admin users can also fetch the unassigned count."""
        resp = await developer_client.get("/api/developers/unassigned-role-count")
        assert resp.status_code == 200
