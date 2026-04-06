"""Sprint and planning metrics computed from external (Linear) data."""

import statistics
from datetime import datetime

from sqlalchemy import case, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.logging import get_logger
from app.models.models import (
    ExternalIssue,
    ExternalProject,
    ExternalSprint,
    PRExternalIssueLink,
    PullRequest,
)

logger = get_logger(__name__)


async def get_sprint_velocity(
    db: AsyncSession, team_key: str | None = None, limit: int = 10
) -> dict:
    """Velocity trend: completed scope per cycle over time."""
    query = (
        select(ExternalSprint)
        .where(ExternalSprint.state == "closed")
        .order_by(ExternalSprint.end_date.desc())
        .limit(limit)
    )
    if team_key:
        query = query.where(ExternalSprint.team_key == team_key)

    result = await db.execute(query)
    sprints = list(reversed(result.scalars().all()))

    data = []
    velocities = []
    for s in sprints:
        completed = s.completed_scope or 0
        velocities.append(completed)
        data.append({
            "sprint_id": s.id,
            "sprint_name": s.name,
            "sprint_number": s.number,
            "team_key": s.team_key,
            "completed_scope": completed,
            "planned_scope": s.planned_scope or 0,
            "start_date": s.start_date,
            "end_date": s.end_date,
        })

    avg = statistics.mean(velocities) if velocities else 0.0

    # Trend direction
    trend = "stable"
    if len(velocities) >= 3:
        first_half = statistics.mean(velocities[: len(velocities) // 2])
        second_half = statistics.mean(velocities[len(velocities) // 2 :])
        if first_half > 0:
            change = (second_half - first_half) / first_half
            if change > 0.1:
                trend = "increasing"
            elif change < -0.1:
                trend = "decreasing"

    return {"data": data, "avg_velocity": round(avg, 1), "trend_direction": trend}


async def get_sprint_completion(
    db: AsyncSession, team_key: str | None = None, limit: int = 10
) -> dict:
    """Completion rate trend: committed vs delivered per cycle."""
    query = (
        select(ExternalSprint)
        .where(ExternalSprint.state == "closed")
        .order_by(ExternalSprint.end_date.desc())
        .limit(limit)
    )
    if team_key:
        query = query.where(ExternalSprint.team_key == team_key)

    result = await db.execute(query)
    sprints = list(reversed(result.scalars().all()))

    data = []
    rates = []
    for s in sprints:
        planned = s.planned_scope or 0
        completed = s.completed_scope or 0
        rate = (completed / planned * 100) if planned > 0 else 0.0
        rates.append(rate)
        data.append({
            "sprint_id": s.id,
            "sprint_name": s.name,
            "sprint_number": s.number,
            "planned_scope": planned,
            "completed_scope": completed,
            "completion_rate": round(rate, 1),
        })

    avg = statistics.mean(rates) if rates else 0.0
    return {"data": data, "avg_completion_rate": round(avg, 1)}


async def get_scope_creep(
    db: AsyncSession, team_key: str | None = None, limit: int = 10
) -> dict:
    """Scope creep trend: issues added mid-cycle as % of planned scope."""
    query = (
        select(ExternalSprint)
        .where(ExternalSprint.state == "closed")
        .order_by(ExternalSprint.end_date.desc())
        .limit(limit)
    )
    if team_key:
        query = query.where(ExternalSprint.team_key == team_key)

    result = await db.execute(query)
    sprints = list(reversed(result.scalars().all()))

    data = []
    creep_pcts = []
    for s in sprints:
        planned = s.planned_scope or 0
        added = s.added_scope or 0
        pct = (added / planned * 100) if planned > 0 else 0.0
        creep_pcts.append(pct)
        data.append({
            "sprint_id": s.id,
            "sprint_name": s.name,
            "sprint_number": s.number,
            "planned_scope": planned,
            "added_scope": added,
            "scope_creep_pct": round(pct, 1),
        })

    avg = statistics.mean(creep_pcts) if creep_pcts else 0.0
    return {"data": data, "avg_scope_creep_pct": round(avg, 1)}


async def get_triage_metrics(
    db: AsyncSession, date_from: datetime | None = None, date_to: datetime | None = None
) -> dict:
    """Triage queue metrics: avg/median/p90 triage duration, queue depth."""
    # Issues with triage duration computed
    query = select(ExternalIssue.triage_duration_s).where(
        ExternalIssue.triage_duration_s.isnot(None),
        ExternalIssue.triage_duration_s > 0,
    )
    if date_from:
        query = query.where(ExternalIssue.created_at >= date_from)
    if date_to:
        query = query.where(ExternalIssue.created_at <= date_to)

    result = await db.execute(query)
    durations = [row[0] for row in result.all()]

    # Issues currently in triage
    triage_count_result = await db.execute(
        select(func.count()).where(ExternalIssue.status_category == "triage")
    )
    in_triage = triage_count_result.scalar() or 0

    if not durations:
        return {
            "avg_triage_duration_s": 0.0,
            "median_triage_duration_s": 0.0,
            "p90_triage_duration_s": 0.0,
            "issues_in_triage": in_triage,
            "total_triaged": 0,
        }

    sorted_durations = sorted(durations)
    p90_idx = int(len(sorted_durations) * 0.9)

    return {
        "avg_triage_duration_s": round(statistics.mean(durations), 1),
        "median_triage_duration_s": round(statistics.median(durations), 1),
        "p90_triage_duration_s": round(sorted_durations[min(p90_idx, len(sorted_durations) - 1)], 1),
        "issues_in_triage": in_triage,
        "total_triaged": len(durations),
    }


async def get_estimation_accuracy(
    db: AsyncSession, team_key: str | None = None, limit: int = 10
) -> dict:
    """Per-cycle: estimated points vs completed points."""
    # Get closed sprints
    sprint_query = (
        select(ExternalSprint)
        .where(ExternalSprint.state == "closed")
        .order_by(ExternalSprint.end_date.desc())
        .limit(limit)
    )
    if team_key:
        sprint_query = sprint_query.where(ExternalSprint.team_key == team_key)

    result = await db.execute(sprint_query)
    sprints = list(reversed(result.scalars().all()))

    data = []
    accuracies = []

    for s in sprints:
        # Get issues for this sprint
        issue_result = await db.execute(
            select(
                func.coalesce(func.sum(ExternalIssue.estimate), 0),
                func.coalesce(
                    func.sum(
                        case(
                            (ExternalIssue.status_category == "done", ExternalIssue.estimate),
                            else_=0,
                        )
                    ),
                    0,
                ),
            ).where(ExternalIssue.sprint_id == s.id, ExternalIssue.estimate.isnot(None))
        )
        row = issue_result.first()
        estimated = float(row[0]) if row else 0.0
        completed = float(row[1]) if row else 0.0

        accuracy = (completed / estimated * 100) if estimated > 0 else 0.0
        accuracies.append(accuracy)

        data.append({
            "sprint_id": s.id,
            "sprint_name": s.name,
            "sprint_number": s.number,
            "estimated_points": round(estimated, 1),
            "completed_points": round(completed, 1),
            "accuracy_pct": round(accuracy, 1),
        })

    avg = statistics.mean(accuracies) if accuracies else 0.0
    return {"data": data, "avg_accuracy_pct": round(avg, 1)}


async def get_work_alignment(
    db: AsyncSession, date_from: datetime | None = None, date_to: datetime | None = None
) -> dict:
    """% of PRs linked to external issues vs unlinked (unplanned work)."""
    pr_query = select(func.count()).select_from(PullRequest)
    if date_from:
        pr_query = pr_query.where(PullRequest.created_at >= date_from)
    if date_to:
        pr_query = pr_query.where(PullRequest.created_at <= date_to)

    total_result = await db.execute(pr_query)
    total_prs = total_result.scalar() or 0

    # Count PRs that have at least one external issue link
    linked_query = (
        select(func.count(func.distinct(PRExternalIssueLink.pull_request_id)))
    )
    if date_from or date_to:
        linked_query = linked_query.join(
            PullRequest, PRExternalIssueLink.pull_request_id == PullRequest.id
        )
        if date_from:
            linked_query = linked_query.where(PullRequest.created_at >= date_from)
        if date_to:
            linked_query = linked_query.where(PullRequest.created_at <= date_to)

    linked_result = await db.execute(linked_query)
    linked_prs = linked_result.scalar() or 0

    alignment_pct = (linked_prs / total_prs * 100) if total_prs > 0 else 0.0

    return {
        "total_prs": total_prs,
        "linked_prs": linked_prs,
        "unlinked_prs": total_prs - linked_prs,
        "alignment_pct": round(alignment_pct, 1),
    }


async def get_planning_correlation(
    db: AsyncSession, team_key: str | None = None, limit: int = 10
) -> dict:
    """Correlate sprint completion rate with avg PR merge time per cycle."""
    sprint_query = (
        select(ExternalSprint)
        .where(ExternalSprint.state == "closed")
        .order_by(ExternalSprint.end_date.desc())
        .limit(limit)
    )
    if team_key:
        sprint_query = sprint_query.where(ExternalSprint.team_key == team_key)

    result = await db.execute(sprint_query)
    sprints = list(reversed(result.scalars().all()))

    data = []
    completion_rates = []
    merge_times = []

    for s in sprints:
        planned = s.planned_scope or 0
        completed = s.completed_scope or 0
        rate = (completed / planned * 100) if planned > 0 else 0.0

        # Get avg merge time for PRs linked to issues in this sprint
        avg_merge_result = await db.execute(
            select(func.avg(PullRequest.time_to_merge_s))
            .join(PRExternalIssueLink, PRExternalIssueLink.pull_request_id == PullRequest.id)
            .join(ExternalIssue, PRExternalIssueLink.external_issue_id == ExternalIssue.id)
            .where(
                ExternalIssue.sprint_id == s.id,
                PullRequest.time_to_merge_s.isnot(None),
            )
        )
        avg_merge_s = avg_merge_result.scalar()
        avg_merge_hours = round(avg_merge_s / 3600, 1) if avg_merge_s else None

        completion_rates.append(rate)
        if avg_merge_hours is not None:
            merge_times.append(avg_merge_hours)

        data.append({
            "sprint_id": s.id,
            "sprint_name": s.name,
            "completion_rate": round(rate, 1),
            "avg_pr_merge_time_hours": avg_merge_hours,
        })

    # Simple correlation coefficient (Pearson)
    correlation = None
    if len(data) >= 3:
        paired = [(d["completion_rate"], d["avg_pr_merge_time_hours"]) for d in data if d["avg_pr_merge_time_hours"] is not None]
        if len(paired) >= 3:
            correlation = _pearson_correlation(
                [p[0] for p in paired], [p[1] for p in paired]
            )

    return {"data": data, "correlation_coefficient": correlation}


async def get_projects_list(db: AsyncSession) -> list[dict]:
    """List all external projects with issue counts."""
    result = await db.execute(
        select(
            ExternalProject,
            func.count(ExternalIssue.id).label("issue_count"),
            func.count(
                case((ExternalIssue.status_category == "done", ExternalIssue.id))
            ).label("completed_count"),
        )
        .outerjoin(ExternalIssue, ExternalIssue.project_id == ExternalProject.id)
        .group_by(ExternalProject.id)
        .order_by(ExternalProject.name)
    )
    rows = result.all()

    projects = []
    for project, issue_count, completed_count in rows:
        proj_dict = {
            "id": project.id,
            "external_id": project.external_id,
            "key": project.key,
            "name": project.name,
            "status": project.status,
            "health": project.health,
            "start_date": project.start_date,
            "target_date": project.target_date,
            "progress_pct": project.progress_pct,
            "lead_id": project.lead_id,
            "url": project.url,
            "issue_count": issue_count,
            "completed_issue_count": completed_count,
        }
        projects.append(proj_dict)

    return projects


async def get_project_detail(db: AsyncSession, project_id: int) -> dict | None:
    """Get project with its issues."""
    project = await db.get(ExternalProject, project_id)
    if not project:
        return None

    result = await db.execute(
        select(ExternalIssue)
        .where(ExternalIssue.project_id == project_id)
        .order_by(ExternalIssue.priority, ExternalIssue.created_at.desc())
    )
    issues = result.scalars().all()

    issue_count = len(issues)
    completed_count = sum(1 for i in issues if i.status_category == "done")

    return {
        "project": project,
        "issues": issues,
        "issue_count": issue_count,
        "completed_issue_count": completed_count,
    }


def _pearson_correlation(x: list[float], y: list[float]) -> float | None:
    """Compute Pearson correlation coefficient."""
    n = len(x)
    if n < 3:
        return None

    mean_x = statistics.mean(x)
    mean_y = statistics.mean(y)

    numerator = sum((xi - mean_x) * (yi - mean_y) for xi, yi in zip(x, y))
    denom_x = sum((xi - mean_x) ** 2 for xi in x) ** 0.5
    denom_y = sum((yi - mean_y) ** 2 for yi in y) ** 0.5

    if denom_x == 0 or denom_y == 0:
        return None

    return round(numerator / (denom_x * denom_y), 3)
