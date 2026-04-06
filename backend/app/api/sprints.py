"""Sprint, planning, and project API routes."""

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.auth import require_admin
from app.models.database import get_db
from app.models.models import ExternalIssue, ExternalSprint
from app.schemas.schemas import (
    EstimationAccuracyResponse,
    ExternalIssueResponse,
    ExternalProjectDetailResponse,
    ExternalProjectResponse,
    PlanningCorrelationResponse,
    ScopeCreepResponse,
    SprintCompletionResponse,
    SprintDetailResponse,
    SprintResponse,
    SprintVelocityResponse,
    TriageMetricsResponse,
    WorkAlignmentResponse,
)
from app.services.sprint_stats import (
    get_estimation_accuracy,
    get_planning_correlation,
    get_project_detail,
    get_projects_list,
    get_scope_creep,
    get_sprint_completion,
    get_sprint_velocity,
    get_triage_metrics,
    get_work_alignment,
)

router = APIRouter()


# --- Sprints ---


@router.get(
    "/sprints",
    response_model=list[SprintResponse],
    dependencies=[Depends(require_admin)],
)
async def list_sprints(
    db: AsyncSession = Depends(get_db),
    team_key: str | None = Query(None),
    state: str | None = Query(None),
    limit: int = Query(20, ge=1, le=100),
):
    """List cycles/sprints with optional filters."""
    query = select(ExternalSprint).order_by(ExternalSprint.end_date.desc()).limit(limit)
    if team_key:
        query = query.where(ExternalSprint.team_key == team_key)
    if state:
        query = query.where(ExternalSprint.state == state)
    result = await db.execute(query)
    return [SprintResponse.model_validate(s) for s in result.scalars().all()]


@router.get(
    "/sprints/velocity",
    response_model=SprintVelocityResponse,
    dependencies=[Depends(require_admin)],
)
async def velocity_trend(
    db: AsyncSession = Depends(get_db),
    team_key: str | None = Query(None),
    limit: int = Query(10, ge=1, le=50),
):
    """Sprint velocity trend chart data."""
    data = await get_sprint_velocity(db, team_key=team_key, limit=limit)
    return SprintVelocityResponse(**data)


@router.get(
    "/sprints/completion",
    response_model=SprintCompletionResponse,
    dependencies=[Depends(require_admin)],
)
async def completion_trend(
    db: AsyncSession = Depends(get_db),
    team_key: str | None = Query(None),
    limit: int = Query(10, ge=1, le=50),
):
    """Sprint completion rate trend."""
    data = await get_sprint_completion(db, team_key=team_key, limit=limit)
    return SprintCompletionResponse(**data)


@router.get(
    "/sprints/scope-creep",
    response_model=ScopeCreepResponse,
    dependencies=[Depends(require_admin)],
)
async def scope_creep_trend(
    db: AsyncSession = Depends(get_db),
    team_key: str | None = Query(None),
    limit: int = Query(10, ge=1, le=50),
):
    """Scope creep trend across sprints."""
    data = await get_scope_creep(db, team_key=team_key, limit=limit)
    return ScopeCreepResponse(**data)


@router.get(
    "/sprints/{sprint_id}",
    response_model=SprintDetailResponse,
    dependencies=[Depends(require_admin)],
)
async def get_sprint_detail(
    sprint_id: int,
    db: AsyncSession = Depends(get_db),
):
    """Get sprint/cycle detail with issues and metrics."""
    sprint = await db.get(ExternalSprint, sprint_id)
    if not sprint:
        raise HTTPException(status_code=404, detail="Sprint not found")

    result = await db.execute(
        select(ExternalIssue)
        .where(ExternalIssue.sprint_id == sprint_id)
        .order_by(ExternalIssue.priority, ExternalIssue.created_at)
    )
    issues = result.scalars().all()

    planned = sprint.planned_scope or 0
    completed = sprint.completed_scope or 0
    added = sprint.added_scope or 0
    completion_rate = (completed / planned * 100) if planned > 0 else None
    scope_creep_pct = (added / planned * 100) if planned > 0 else None

    return SprintDetailResponse(
        **{c.name: getattr(sprint, c.name) for c in sprint.__table__.columns},
        issues=[ExternalIssueResponse.model_validate(i) for i in issues],
        completion_rate=round(completion_rate, 1) if completion_rate is not None else None,
        scope_creep_pct=round(scope_creep_pct, 1) if scope_creep_pct is not None else None,
    )


# --- Projects ---


@router.get(
    "/projects",
    response_model=list[ExternalProjectResponse],
    dependencies=[Depends(require_admin)],
)
async def list_projects(db: AsyncSession = Depends(get_db)):
    """List all external projects with health and progress."""
    projects = await get_projects_list(db)
    return [ExternalProjectResponse(**p) for p in projects]


@router.get(
    "/projects/{project_id}",
    response_model=ExternalProjectDetailResponse,
    dependencies=[Depends(require_admin)],
)
async def get_project(
    project_id: int,
    db: AsyncSession = Depends(get_db),
):
    """Get project detail with issues."""
    data = await get_project_detail(db, project_id)
    if not data:
        raise HTTPException(status_code=404, detail="Project not found")

    project = data["project"]
    return ExternalProjectDetailResponse(
        **{c.name: getattr(project, c.name) for c in project.__table__.columns},
        issue_count=data["issue_count"],
        completed_issue_count=data["completed_issue_count"],
        issues=[ExternalIssueResponse.model_validate(i) for i in data["issues"]],
    )


# --- Planning Insights ---


@router.get(
    "/planning/triage",
    response_model=TriageMetricsResponse,
    dependencies=[Depends(require_admin)],
)
async def triage_metrics(
    db: AsyncSession = Depends(get_db),
    date_from: datetime | None = Query(None),
    date_to: datetime | None = Query(None),
):
    """Triage queue metrics."""
    data = await get_triage_metrics(db, date_from=date_from, date_to=date_to)
    return TriageMetricsResponse(**data)


@router.get(
    "/planning/alignment",
    response_model=WorkAlignmentResponse,
    dependencies=[Depends(require_admin)],
)
async def work_alignment(
    db: AsyncSession = Depends(get_db),
    date_from: datetime | None = Query(None),
    date_to: datetime | None = Query(None),
):
    """Work alignment: linked vs unlinked PRs."""
    data = await get_work_alignment(db, date_from=date_from, date_to=date_to)
    return WorkAlignmentResponse(**data)


@router.get(
    "/planning/accuracy",
    response_model=EstimationAccuracyResponse,
    dependencies=[Depends(require_admin)],
)
async def estimation_accuracy(
    db: AsyncSession = Depends(get_db),
    team_key: str | None = Query(None),
    limit: int = Query(10, ge=1, le=50),
):
    """Estimation accuracy trend."""
    data = await get_estimation_accuracy(db, team_key=team_key, limit=limit)
    return EstimationAccuracyResponse(**data)


@router.get(
    "/planning/correlation",
    response_model=PlanningCorrelationResponse,
    dependencies=[Depends(require_admin)],
)
async def planning_correlation(
    db: AsyncSession = Depends(get_db),
    team_key: str | None = Query(None),
    limit: int = Query(10, ge=1, le=50),
):
    """Planning vs delivery correlation."""
    data = await get_planning_correlation(db, team_key=team_key, limit=limit)
    return PlanningCorrelationResponse(**data)
