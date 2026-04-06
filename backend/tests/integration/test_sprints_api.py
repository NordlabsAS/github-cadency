"""Integration tests for sprint and planning API routes."""

from datetime import date, datetime, timedelta, timezone

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.models import (
    ExternalIssue,
    ExternalProject,
    ExternalSprint,
    IntegrationConfig,
    PRExternalIssueLink,
    PullRequest,
    Repository,
)
from app.services.encryption import encrypt_token


# --- Fixtures ---


@pytest_asyncio.fixture
async def linear_setup(db_session: AsyncSession, sample_repo: Repository, sample_pr: PullRequest):
    """Create a full Linear integration with projects, sprints, and issues."""
    # Integration
    config = IntegrationConfig(
        type="linear",
        display_name="Linear",
        api_key=encrypt_token("lin_api_test"),
        status="active",
    )
    db_session.add(config)
    await db_session.flush()

    # Project
    project = ExternalProject(
        integration_id=config.id,
        external_id="proj_1",
        name="Platform Rewrite",
        status="started",
        health="on_track",
        start_date=date(2026, 1, 1),
        target_date=date(2026, 6, 30),
        progress_pct=0.45,
    )
    db_session.add(project)
    await db_session.flush()

    # Sprints (closed cycles)
    sprints = []
    now = datetime.now(timezone.utc)
    for i in range(3):
        sprint = ExternalSprint(
            integration_id=config.id,
            external_id=f"cycle_{i}",
            name=f"Sprint {i+1}",
            number=i + 1,
            team_key="ENG",
            team_name="Engineering",
            state="closed",
            start_date=date(2026, 1 + i, 1),
            end_date=date(2026, 1 + i, 14),
            planned_scope=10 + i,
            completed_scope=8 + i,
            cancelled_scope=2,
            added_scope=3 + i,
        )
        db_session.add(sprint)
        sprints.append(sprint)
    await db_session.flush()

    # Issues
    issues = []
    for j, sprint in enumerate(sprints):
        for k in range(3):
            issue = ExternalIssue(
                integration_id=config.id,
                external_id=f"issue_{j}_{k}",
                identifier=f"ENG-{j*10+k}",
                title=f"Issue {j}-{k}",
                status_category="done" if k < 2 else "in_progress",
                priority=k + 1,
                estimate=float(k + 1),
                sprint_id=sprint.id,
                project_id=project.id,
                triage_duration_s=3600 * (k + 1) if k < 2 else None,
                cycle_time_s=7200 * (k + 1) if k < 2 else None,
                created_at=now - timedelta(days=30),
                started_at=now - timedelta(days=25) if k < 2 else None,
                completed_at=now - timedelta(days=20) if k < 2 else None,
            )
            db_session.add(issue)
            issues.append(issue)
    await db_session.flush()

    # PR-issue link
    link = PRExternalIssueLink(
        pull_request_id=sample_pr.id,
        external_issue_id=issues[0].id,
        link_source="title",
    )
    db_session.add(link)

    await db_session.commit()

    return {
        "config": config,
        "project": project,
        "sprints": sprints,
        "issues": issues,
    }


# --- Sprint tests ---


@pytest.mark.asyncio
async def test_list_sprints(client, linear_setup):
    resp = await client.get("/api/sprints")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 3


@pytest.mark.asyncio
async def test_list_sprints_filter_team(client, linear_setup):
    resp = await client.get("/api/sprints?team_key=ENG")
    assert resp.status_code == 200
    assert len(resp.json()) == 3

    resp = await client.get("/api/sprints?team_key=NONE")
    assert len(resp.json()) == 0


@pytest.mark.asyncio
async def test_sprint_detail(client, linear_setup):
    sprint = linear_setup["sprints"][0]
    resp = await client.get(f"/api/sprints/{sprint.id}")
    assert resp.status_code == 200
    data = resp.json()
    assert data["name"] == "Sprint 1"
    assert len(data["issues"]) == 3
    assert data["completion_rate"] is not None


@pytest.mark.asyncio
async def test_sprint_not_found(client, linear_setup):
    resp = await client.get("/api/sprints/99999")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_velocity_trend(client, linear_setup):
    resp = await client.get("/api/sprints/velocity?team_key=ENG")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["data"]) == 3
    assert data["avg_velocity"] > 0
    assert data["trend_direction"] in ("stable", "increasing", "decreasing")


@pytest.mark.asyncio
async def test_completion_trend(client, linear_setup):
    resp = await client.get("/api/sprints/completion")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["data"]) == 3
    assert data["avg_completion_rate"] > 0
    for point in data["data"]:
        assert 0 <= point["completion_rate"] <= 100


@pytest.mark.asyncio
async def test_scope_creep_trend(client, linear_setup):
    resp = await client.get("/api/sprints/scope-creep")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["data"]) == 3
    assert data["avg_scope_creep_pct"] > 0


# --- Project tests ---


@pytest.mark.asyncio
async def test_list_projects(client, linear_setup):
    resp = await client.get("/api/projects")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 1
    assert data[0]["name"] == "Platform Rewrite"
    assert data[0]["health"] == "on_track"
    assert data[0]["issue_count"] == 9


@pytest.mark.asyncio
async def test_project_detail(client, linear_setup):
    project = linear_setup["project"]
    resp = await client.get(f"/api/projects/{project.id}")
    assert resp.status_code == 200
    data = resp.json()
    assert data["name"] == "Platform Rewrite"
    assert len(data["issues"]) == 9


# --- Planning tests ---


@pytest.mark.asyncio
async def test_triage_metrics(client, linear_setup):
    resp = await client.get("/api/planning/triage")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total_triaged"] > 0
    assert data["avg_triage_duration_s"] > 0


@pytest.mark.asyncio
async def test_work_alignment(client, linear_setup):
    resp = await client.get("/api/planning/alignment")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total_prs"] >= 1
    assert data["linked_prs"] >= 1
    assert data["alignment_pct"] > 0


@pytest.mark.asyncio
async def test_estimation_accuracy(client, linear_setup):
    resp = await client.get("/api/planning/accuracy?team_key=ENG")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["data"]) == 3


@pytest.mark.asyncio
async def test_planning_correlation(client, linear_setup):
    resp = await client.get("/api/planning/correlation?team_key=ENG")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["data"]) == 3


# --- Auth tests ---


@pytest.mark.asyncio
async def test_developer_cannot_access_sprints(developer_client, linear_setup):
    resp = await developer_client.get("/api/sprints")
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_developer_cannot_access_projects(developer_client, linear_setup):
    resp = await developer_client.get("/api/projects")
    assert resp.status_code == 403
