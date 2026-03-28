import statistics
from datetime import datetime, timedelta, timezone

from sqlalchemy import and_, case, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.models import Developer, Issue, PRReview, PullRequest, Repository
from app.schemas.schemas import (
    BenchmarkMetric,
    BenchmarksResponse,
    DeveloperStatsResponse,
    DeveloperStatsWithPercentilesResponse,
    DeveloperTrendsResponse,
    DeveloperWorkload,
    IssueLinkageStats,
    PercentilePlacement,
    RepoStatsResponse,
    ReviewBreakdown,
    ReviewQualityBreakdown,
    StalePR,
    StalePRsResponse,
    TeamStatsResponse,
    TopContributor,
    TrendDirection,
    TrendPeriod,
    WorkloadAlert,
    WorkloadResponse,
)


def _default_range(
    date_from: datetime | None, date_to: datetime | None
) -> tuple[datetime, datetime]:
    if not date_to:
        date_to = datetime.now(timezone.utc)
    if not date_from:
        date_from = date_to - timedelta(days=30)
    return date_from, date_to


async def get_developer_stats(
    db: AsyncSession,
    developer_id: int,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
) -> DeveloperStatsResponse:
    date_from, date_to = _default_range(date_from, date_to)

    # PRs opened
    prs_opened = await db.scalar(
        select(func.count()).where(
            PullRequest.author_id == developer_id,
            PullRequest.created_at >= date_from,
            PullRequest.created_at <= date_to,
        )
    ) or 0

    # PRs merged
    prs_merged = await db.scalar(
        select(func.count()).where(
            PullRequest.author_id == developer_id,
            PullRequest.is_merged.is_(True),
            PullRequest.merged_at >= date_from,
            PullRequest.merged_at <= date_to,
        )
    ) or 0

    # PRs closed without merge
    prs_closed_no_merge = await db.scalar(
        select(func.count()).where(
            PullRequest.author_id == developer_id,
            PullRequest.state == "closed",
            PullRequest.is_merged.is_(False),
            PullRequest.closed_at >= date_from,
            PullRequest.closed_at <= date_to,
        )
    ) or 0

    # PRs currently open (exclude drafts)
    prs_open = await db.scalar(
        select(func.count()).where(
            PullRequest.author_id == developer_id,
            PullRequest.state == "open",
            PullRequest.is_draft.isnot(True),
        )
    ) or 0

    # Draft PRs currently open
    prs_draft = await db.scalar(
        select(func.count()).where(
            PullRequest.author_id == developer_id,
            PullRequest.state == "open",
            PullRequest.is_draft.is_(True),
        )
    ) or 0

    # Code volume (from PRs in range)
    code_stats = (
        await db.execute(
            select(
                func.coalesce(func.sum(PullRequest.additions), 0),
                func.coalesce(func.sum(PullRequest.deletions), 0),
                func.coalesce(func.sum(PullRequest.changed_files), 0),
            ).where(
                PullRequest.author_id == developer_id,
                PullRequest.created_at >= date_from,
                PullRequest.created_at <= date_to,
            )
        )
    ).one()

    # Reviews given breakdown
    reviews_given_rows = (
        await db.execute(
            select(PRReview.state, func.count()).where(
                PRReview.reviewer_id == developer_id,
                PRReview.submitted_at >= date_from,
                PRReview.submitted_at <= date_to,
            ).group_by(PRReview.state)
        )
    ).all()
    reviews_given = ReviewBreakdown()
    for state, count in reviews_given_rows:
        if state == "APPROVED":
            reviews_given.approved = count
        elif state == "CHANGES_REQUESTED":
            reviews_given.changes_requested = count
        elif state == "COMMENTED":
            reviews_given.commented = count

    # Review quality breakdown
    quality_rows = (
        await db.execute(
            select(PRReview.quality_tier, func.count()).where(
                PRReview.reviewer_id == developer_id,
                PRReview.submitted_at >= date_from,
                PRReview.submitted_at <= date_to,
            ).group_by(PRReview.quality_tier)
        )
    ).all()
    quality_breakdown = ReviewQualityBreakdown()
    for tier, count in quality_rows:
        if tier == "rubber_stamp":
            quality_breakdown.rubber_stamp = count
        elif tier == "minimal":
            quality_breakdown.minimal = count
        elif tier == "standard":
            quality_breakdown.standard = count
        elif tier == "thorough":
            quality_breakdown.thorough = count

    # Review quality score: (rubber_stamp*0 + minimal*1 + standard*3 + thorough*5) / total, normalized 0-10
    total_quality_reviews = (
        quality_breakdown.rubber_stamp
        + quality_breakdown.minimal
        + quality_breakdown.standard
        + quality_breakdown.thorough
    )
    if total_quality_reviews > 0:
        raw_score = (
            quality_breakdown.rubber_stamp * 0
            + quality_breakdown.minimal * 1
            + quality_breakdown.standard * 3
            + quality_breakdown.thorough * 5
        ) / total_quality_reviews
        # Normalize to 0-10 scale (max raw score is 5)
        review_quality_score = round(raw_score * 2, 2)
    else:
        review_quality_score = None

    # Reviews received
    reviews_received = await db.scalar(
        select(func.count())
        .select_from(PRReview)
        .join(PullRequest, PRReview.pr_id == PullRequest.id)
        .where(
            PullRequest.author_id == developer_id,
            PRReview.submitted_at >= date_from,
            PRReview.submitted_at <= date_to,
        )
    ) or 0

    # Avg time to first review
    avg_ttfr = await db.scalar(
        select(func.avg(PullRequest.time_to_first_review_s)).where(
            PullRequest.author_id == developer_id,
            PullRequest.time_to_first_review_s.isnot(None),
            PullRequest.created_at >= date_from,
            PullRequest.created_at <= date_to,
        )
    )

    # Avg time to merge
    avg_ttm = await db.scalar(
        select(func.avg(PullRequest.time_to_merge_s)).where(
            PullRequest.author_id == developer_id,
            PullRequest.is_merged.is_(True),
            PullRequest.time_to_merge_s.isnot(None),
            PullRequest.merged_at >= date_from,
            PullRequest.merged_at <= date_to,
        )
    )

    # Avg time to approve (creation → last approval)
    avg_tta = await db.scalar(
        select(func.avg(PullRequest.time_to_approve_s)).where(
            PullRequest.author_id == developer_id,
            PullRequest.time_to_approve_s.isnot(None),
            PullRequest.created_at >= date_from,
            PullRequest.created_at <= date_to,
        )
    )

    # Avg time after approve (last approval → merge)
    avg_taa = await db.scalar(
        select(func.avg(PullRequest.time_after_approve_s)).where(
            PullRequest.author_id == developer_id,
            PullRequest.is_merged.is_(True),
            PullRequest.time_after_approve_s.isnot(None),
            PullRequest.merged_at >= date_from,
            PullRequest.merged_at <= date_to,
        )
    )

    # PRs merged without approval
    prs_merged_without_approval = await db.scalar(
        select(func.count()).where(
            PullRequest.author_id == developer_id,
            PullRequest.merged_without_approval.is_(True),
            PullRequest.merged_at >= date_from,
            PullRequest.merged_at <= date_to,
        )
    ) or 0

    # Issues assigned
    issues_assigned = await db.scalar(
        select(func.count()).where(
            Issue.assignee_id == developer_id,
            Issue.created_at >= date_from,
            Issue.created_at <= date_to,
        )
    ) or 0

    # Issues closed
    issues_closed = await db.scalar(
        select(func.count()).where(
            Issue.assignee_id == developer_id,
            Issue.closed_at >= date_from,
            Issue.closed_at <= date_to,
        )
    ) or 0

    # Avg time to close issue
    avg_ttc = await db.scalar(
        select(func.avg(Issue.time_to_close_s)).where(
            Issue.assignee_id == developer_id,
            Issue.time_to_close_s.isnot(None),
            Issue.closed_at >= date_from,
            Issue.closed_at <= date_to,
        )
    )

    # Avg review rounds (on merged PRs in period)
    avg_review_rounds = await db.scalar(
        select(func.avg(PullRequest.review_round_count)).where(
            PullRequest.author_id == developer_id,
            PullRequest.is_merged.is_(True),
            PullRequest.merged_at >= date_from,
            PullRequest.merged_at <= date_to,
        )
    )

    # PRs merged on first pass (0 changes_requested reviews)
    prs_merged_first_pass = await db.scalar(
        select(func.count()).where(
            PullRequest.author_id == developer_id,
            PullRequest.is_merged.is_(True),
            PullRequest.review_round_count == 0,
            PullRequest.merged_at >= date_from,
            PullRequest.merged_at <= date_to,
        )
    ) or 0

    first_pass_rate = (
        prs_merged_first_pass / prs_merged if prs_merged > 0 else None
    )

    # PRs self-merged (author merged their own PR)
    prs_self_merged = await db.scalar(
        select(func.count()).where(
            PullRequest.author_id == developer_id,
            PullRequest.is_merged.is_(True),
            PullRequest.is_self_merged.is_(True),
            PullRequest.merged_at >= date_from,
            PullRequest.merged_at <= date_to,
        )
    ) or 0

    self_merge_rate = (
        prs_self_merged / prs_merged if prs_merged > 0 else None
    )

    # PRs authored by this developer that were subsequently reverted
    original_pr = PullRequest.__table__.alias("original_pr")
    prs_reverted = await db.scalar(
        select(func.count())
        .select_from(PullRequest.__table__)
        .join(
            original_pr,
            (PullRequest.__table__.c.reverted_pr_number == original_pr.c.number)
            & (PullRequest.__table__.c.repo_id == original_pr.c.repo_id),
        )
        .where(
            PullRequest.__table__.c.is_revert.is_(True),
            PullRequest.__table__.c.reverted_pr_number.isnot(None),
            PullRequest.__table__.c.created_at >= date_from,
            PullRequest.__table__.c.created_at <= date_to,
            original_pr.c.author_id == developer_id,
        )
    ) or 0

    # Revert PRs this developer authored (fixing problems quickly)
    reverts_authored = await db.scalar(
        select(func.count()).where(
            PullRequest.author_id == developer_id,
            PullRequest.is_revert.is_(True),
            PullRequest.created_at >= date_from,
            PullRequest.created_at <= date_to,
        )
    ) or 0

    return DeveloperStatsResponse(
        prs_opened=prs_opened,
        prs_merged=prs_merged,
        prs_closed_without_merge=prs_closed_no_merge,
        prs_open=prs_open,
        prs_draft=prs_draft,
        total_additions=code_stats[0],
        total_deletions=code_stats[1],
        total_changed_files=code_stats[2],
        reviews_given=reviews_given,
        reviews_received=reviews_received,
        review_quality_breakdown=quality_breakdown,
        review_quality_score=review_quality_score,
        avg_time_to_first_review_hours=avg_ttfr / 3600 if avg_ttfr else None,
        avg_time_to_merge_hours=avg_ttm / 3600 if avg_ttm else None,
        avg_time_to_approve_hours=avg_tta / 3600 if avg_tta else None,
        avg_time_after_approve_hours=avg_taa / 3600 if avg_taa else None,
        prs_merged_without_approval=prs_merged_without_approval,
        issues_assigned=issues_assigned,
        issues_closed=issues_closed,
        avg_time_to_close_issue_hours=avg_ttc / 3600 if avg_ttc else None,
        avg_review_rounds=round(avg_review_rounds, 2) if avg_review_rounds is not None else None,
        prs_merged_first_pass=prs_merged_first_pass,
        first_pass_rate=round(first_pass_rate, 4) if first_pass_rate is not None else None,
        prs_self_merged=prs_self_merged,
        self_merge_rate=round(self_merge_rate, 4) if self_merge_rate is not None else None,
        prs_reverted=prs_reverted,
        reverts_authored=reverts_authored,
    )


async def get_team_stats(
    db: AsyncSession,
    team: str | None = None,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
) -> TeamStatsResponse:
    date_from, date_to = _default_range(date_from, date_to)

    # Get team developer IDs
    dev_query = select(Developer.id).where(Developer.is_active.is_(True))
    if team:
        dev_query = dev_query.where(Developer.team == team)
    dev_result = await db.execute(dev_query)
    dev_ids = [row[0] for row in dev_result.all()]
    developer_count = len(dev_ids)

    if not dev_ids:
        return TeamStatsResponse(developer_count=0)

    # Total PRs
    total_prs = await db.scalar(
        select(func.count()).where(
            PullRequest.author_id.in_(dev_ids),
            PullRequest.created_at >= date_from,
            PullRequest.created_at <= date_to,
        )
    ) or 0

    # Total merged
    total_merged = await db.scalar(
        select(func.count()).where(
            PullRequest.author_id.in_(dev_ids),
            PullRequest.is_merged.is_(True),
            PullRequest.merged_at >= date_from,
            PullRequest.merged_at <= date_to,
        )
    ) or 0

    merge_rate = (total_merged / total_prs * 100) if total_prs > 0 else None

    # Avg time to first review
    avg_ttfr = await db.scalar(
        select(func.avg(PullRequest.time_to_first_review_s)).where(
            PullRequest.author_id.in_(dev_ids),
            PullRequest.time_to_first_review_s.isnot(None),
            PullRequest.created_at >= date_from,
            PullRequest.created_at <= date_to,
        )
    )

    # Avg time to merge
    avg_ttm = await db.scalar(
        select(func.avg(PullRequest.time_to_merge_s)).where(
            PullRequest.author_id.in_(dev_ids),
            PullRequest.is_merged.is_(True),
            PullRequest.time_to_merge_s.isnot(None),
            PullRequest.merged_at >= date_from,
            PullRequest.merged_at <= date_to,
        )
    )

    # Total reviews
    total_reviews = await db.scalar(
        select(func.count()).where(
            PRReview.reviewer_id.in_(dev_ids),
            PRReview.submitted_at >= date_from,
            PRReview.submitted_at <= date_to,
        )
    ) or 0

    # Total issues closed
    total_issues_closed = await db.scalar(
        select(func.count()).where(
            Issue.assignee_id.in_(dev_ids),
            Issue.closed_at >= date_from,
            Issue.closed_at <= date_to,
        )
    ) or 0

    # Avg review rounds (team-wide, on merged PRs)
    team_avg_review_rounds = await db.scalar(
        select(func.avg(PullRequest.review_round_count)).where(
            PullRequest.author_id.in_(dev_ids),
            PullRequest.is_merged.is_(True),
            PullRequest.merged_at >= date_from,
            PullRequest.merged_at <= date_to,
        )
    )

    # Team first pass rate (reuse total_merged to avoid redundant query)
    team_first_pass = await db.scalar(
        select(func.count()).where(
            PullRequest.author_id.in_(dev_ids),
            PullRequest.is_merged.is_(True),
            PullRequest.review_round_count == 0,
            PullRequest.merged_at >= date_from,
            PullRequest.merged_at <= date_to,
        )
    ) or 0
    team_first_pass_rate = team_first_pass / total_merged if total_merged > 0 else None

    # Team revert rate: reverted PRs / total merged PRs
    team_reverts = await db.scalar(
        select(func.count()).where(
            PullRequest.author_id.in_(dev_ids),
            PullRequest.is_revert.is_(True),
            PullRequest.created_at >= date_from,
            PullRequest.created_at <= date_to,
        )
    ) or 0
    revert_rate = team_reverts / total_merged if total_merged > 0 else None

    return TeamStatsResponse(
        developer_count=developer_count,
        total_prs=total_prs,
        total_merged=total_merged,
        merge_rate=merge_rate,
        avg_time_to_first_review_hours=avg_ttfr / 3600 if avg_ttfr else None,
        avg_time_to_merge_hours=avg_ttm / 3600 if avg_ttm else None,
        total_reviews=total_reviews,
        total_issues_closed=total_issues_closed,
        avg_review_rounds=round(team_avg_review_rounds, 2) if team_avg_review_rounds is not None else None,
        first_pass_rate=round(team_first_pass_rate, 4) if team_first_pass_rate is not None else None,
        revert_rate=round(revert_rate, 4) if revert_rate is not None else None,
    )


async def get_repo_stats(
    db: AsyncSession,
    repo_id: int,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
) -> RepoStatsResponse:
    date_from, date_to = _default_range(date_from, date_to)

    total_prs = await db.scalar(
        select(func.count()).where(
            PullRequest.repo_id == repo_id,
            PullRequest.created_at >= date_from,
            PullRequest.created_at <= date_to,
        )
    ) or 0

    total_merged = await db.scalar(
        select(func.count()).where(
            PullRequest.repo_id == repo_id,
            PullRequest.is_merged.is_(True),
            PullRequest.merged_at >= date_from,
            PullRequest.merged_at <= date_to,
        )
    ) or 0

    total_issues = await db.scalar(
        select(func.count()).where(
            Issue.repo_id == repo_id,
            Issue.created_at >= date_from,
            Issue.created_at <= date_to,
        )
    ) or 0

    total_issues_closed = await db.scalar(
        select(func.count()).where(
            Issue.repo_id == repo_id,
            Issue.closed_at >= date_from,
            Issue.closed_at <= date_to,
        )
    ) or 0

    total_reviews = await db.scalar(
        select(func.count())
        .select_from(PRReview)
        .join(PullRequest, PRReview.pr_id == PullRequest.id)
        .where(
            PullRequest.repo_id == repo_id,
            PRReview.submitted_at >= date_from,
            PRReview.submitted_at <= date_to,
        )
    ) or 0

    avg_ttm = await db.scalar(
        select(func.avg(PullRequest.time_to_merge_s)).where(
            PullRequest.repo_id == repo_id,
            PullRequest.is_merged.is_(True),
            PullRequest.time_to_merge_s.isnot(None),
            PullRequest.merged_at >= date_from,
            PullRequest.merged_at <= date_to,
        )
    )

    # Top contributors by PR count
    top_rows = (
        await db.execute(
            select(
                Developer.id,
                Developer.github_username,
                Developer.display_name,
                func.count().label("pr_count"),
            )
            .join(PullRequest, PullRequest.author_id == Developer.id)
            .where(
                PullRequest.repo_id == repo_id,
                PullRequest.created_at >= date_from,
                PullRequest.created_at <= date_to,
            )
            .group_by(Developer.id)
            .order_by(func.count().desc())
            .limit(10)
        )
    ).all()

    top_contributors = [
        TopContributor(
            developer_id=row.id,
            github_username=row.github_username,
            display_name=row.display_name,
            pr_count=row.pr_count,
        )
        for row in top_rows
    ]

    return RepoStatsResponse(
        total_prs=total_prs,
        total_merged=total_merged,
        total_issues=total_issues,
        total_issues_closed=total_issues_closed,
        total_reviews=total_reviews,
        avg_time_to_merge_hours=avg_ttm / 3600 if avg_ttm else None,
        top_contributors=top_contributors,
    )


# --- M2: Team Benchmarks ---


async def _compute_per_developer_metrics(
    db: AsyncSession,
    dev_ids: list[int],
    date_from: datetime,
    date_to: datetime,
) -> dict[str, list[float]]:
    """Compute benchmark metrics per developer, returning lists of values for percentile calculation."""
    metrics: dict[str, list[float]] = {
        "time_to_merge_h": [],
        "time_to_first_review_h": [],
        "time_to_approve_h": [],
        "time_after_approve_h": [],
        "prs_merged": [],
        "review_turnaround_h": [],
        "reviews_given": [],
        "additions_per_pr": [],
        "review_rounds": [],
    }

    for dev_id in dev_ids:
        # PRs merged
        prs_merged = await db.scalar(
            select(func.count()).where(
                PullRequest.author_id == dev_id,
                PullRequest.is_merged.is_(True),
                PullRequest.merged_at >= date_from,
                PullRequest.merged_at <= date_to,
            )
        ) or 0
        metrics["prs_merged"].append(float(prs_merged))

        # Avg time to merge (hours)
        avg_ttm = await db.scalar(
            select(func.avg(PullRequest.time_to_merge_s)).where(
                PullRequest.author_id == dev_id,
                PullRequest.is_merged.is_(True),
                PullRequest.time_to_merge_s.isnot(None),
                PullRequest.merged_at >= date_from,
                PullRequest.merged_at <= date_to,
            )
        )
        metrics["time_to_merge_h"].append(avg_ttm / 3600 if avg_ttm else 0.0)

        # Avg time to first review (hours) — for PRs authored by this dev
        avg_ttfr = await db.scalar(
            select(func.avg(PullRequest.time_to_first_review_s)).where(
                PullRequest.author_id == dev_id,
                PullRequest.time_to_first_review_s.isnot(None),
                PullRequest.created_at >= date_from,
                PullRequest.created_at <= date_to,
            )
        )
        metrics["time_to_first_review_h"].append(avg_ttfr / 3600 if avg_ttfr else 0.0)

        # Avg time to approve (hours)
        avg_tta = await db.scalar(
            select(func.avg(PullRequest.time_to_approve_s)).where(
                PullRequest.author_id == dev_id,
                PullRequest.time_to_approve_s.isnot(None),
                PullRequest.created_at >= date_from,
                PullRequest.created_at <= date_to,
            )
        )
        metrics["time_to_approve_h"].append(avg_tta / 3600 if avg_tta else 0.0)

        # Avg time after approve (hours)
        avg_taa = await db.scalar(
            select(func.avg(PullRequest.time_after_approve_s)).where(
                PullRequest.author_id == dev_id,
                PullRequest.is_merged.is_(True),
                PullRequest.time_after_approve_s.isnot(None),
                PullRequest.merged_at >= date_from,
                PullRequest.merged_at <= date_to,
            )
        )
        metrics["time_after_approve_h"].append(avg_taa / 3600 if avg_taa else 0.0)

        # Reviews given count
        reviews_given = await db.scalar(
            select(func.count()).where(
                PRReview.reviewer_id == dev_id,
                PRReview.submitted_at >= date_from,
                PRReview.submitted_at <= date_to,
            )
        ) or 0
        metrics["reviews_given"].append(float(reviews_given))

        # Review turnaround — avg time_to_first_review_s for PRs this dev reviewed
        avg_turnaround = await db.scalar(
            select(func.avg(PullRequest.time_to_first_review_s))
            .select_from(PRReview)
            .join(PullRequest, PRReview.pr_id == PullRequest.id)
            .where(
                PRReview.reviewer_id == dev_id,
                PullRequest.time_to_first_review_s.isnot(None),
                PRReview.submitted_at >= date_from,
                PRReview.submitted_at <= date_to,
            )
        )
        metrics["review_turnaround_h"].append(
            avg_turnaround / 3600 if avg_turnaround else 0.0
        )

        # Additions per PR
        total_additions = await db.scalar(
            select(func.coalesce(func.sum(PullRequest.additions), 0)).where(
                PullRequest.author_id == dev_id,
                PullRequest.is_merged.is_(True),
                PullRequest.merged_at >= date_from,
                PullRequest.merged_at <= date_to,
            )
        ) or 0
        metrics["additions_per_pr"].append(
            total_additions / prs_merged if prs_merged > 0 else 0.0
        )

        # Avg review rounds (on merged PRs)
        avg_rounds = await db.scalar(
            select(func.avg(PullRequest.review_round_count)).where(
                PullRequest.author_id == dev_id,
                PullRequest.is_merged.is_(True),
                PullRequest.merged_at >= date_from,
                PullRequest.merged_at <= date_to,
            )
        )
        metrics["review_rounds"].append(float(avg_rounds) if avg_rounds is not None else 0.0)

    return metrics


def _percentiles(values: list[float]) -> BenchmarkMetric:
    """Compute p25, p50, p75 using linear interpolation."""
    if len(values) < 2:
        v = values[0] if values else 0.0
        return BenchmarkMetric(p25=v, p50=v, p75=v)
    quantiles = statistics.quantiles(values, n=4, method="inclusive")
    return BenchmarkMetric(
        p25=round(quantiles[0], 2),
        p50=round(quantiles[1], 2),
        p75=round(quantiles[2], 2),
    )


# Metrics where lower values are better (latency metrics)
_LOWER_IS_BETTER = {
    "time_to_merge_h", "time_to_first_review_h", "review_turnaround_h",
    "review_rounds", "time_to_approve_h", "time_after_approve_h",
}


def _percentile_band(
    value: float, metric: BenchmarkMetric, metric_name: str = ""
) -> str:
    """Assign percentile band. For lower-is-better metrics, invert so above_p75 = best."""
    if metric_name in _LOWER_IS_BETTER:
        # Invert: low value = good = above_p75
        if value > metric.p75:
            return "below_p25"
        elif value > metric.p50:
            return "p25_to_p50"
        elif value > metric.p25:
            return "p50_to_p75"
        else:
            return "above_p75"
    if value < metric.p25:
        return "below_p25"
    elif value < metric.p50:
        return "p25_to_p50"
    elif value < metric.p75:
        return "p50_to_p75"
    else:
        return "above_p75"


async def get_benchmarks(
    db: AsyncSession,
    team: str | None = None,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
) -> BenchmarksResponse:
    date_from, date_to = _default_range(date_from, date_to)

    dev_query = select(Developer.id).where(Developer.is_active.is_(True))
    if team:
        dev_query = dev_query.where(Developer.team == team)
    dev_result = await db.execute(dev_query)
    dev_ids = [row[0] for row in dev_result.all()]

    if not dev_ids:
        return BenchmarksResponse(
            period_start=date_from,
            period_end=date_to,
            sample_size=0,
            team=team,
            metrics={},
        )

    per_dev = await _compute_per_developer_metrics(db, dev_ids, date_from, date_to)

    return BenchmarksResponse(
        period_start=date_from,
        period_end=date_to,
        sample_size=len(dev_ids),
        team=team,
        metrics={name: _percentiles(values) for name, values in per_dev.items()},
    )


async def get_developer_stats_with_percentiles(
    db: AsyncSession,
    developer_id: int,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
) -> DeveloperStatsWithPercentilesResponse:
    date_from, date_to = _default_range(date_from, date_to)
    base = await get_developer_stats(db, developer_id, date_from, date_to)

    # Get the developer's team for team-relative benchmarks
    dev = await db.get(Developer, developer_id)
    dev_query = select(Developer.id).where(Developer.is_active.is_(True))
    if dev and dev.team:
        dev_query = dev_query.where(Developer.team == dev.team)
    dev_result = await db.execute(dev_query)
    dev_ids = [row[0] for row in dev_result.all()]

    if len(dev_ids) < 2:
        return DeveloperStatsWithPercentilesResponse(**base.model_dump())

    per_dev = await _compute_per_developer_metrics(db, dev_ids, date_from, date_to)
    benchmarks = {name: _percentiles(values) for name, values in per_dev.items()}

    # Map developer stats fields to benchmark metric names
    dev_values = {
        "time_to_merge_h": base.avg_time_to_merge_hours or 0.0,
        "time_to_first_review_h": base.avg_time_to_first_review_hours or 0.0,
        "prs_merged": float(base.prs_merged),
        "reviews_given": float(
            base.reviews_given.approved
            + base.reviews_given.changes_requested
            + base.reviews_given.commented
        ),
        "additions_per_pr": (
            base.total_additions / base.prs_merged
            if base.prs_merged > 0
            else 0.0
        ),
        "review_rounds": base.avg_review_rounds or 0.0,
        "time_to_approve_h": base.avg_time_to_approve_hours or 0.0,
        "time_after_approve_h": base.avg_time_after_approve_hours or 0.0,
    }

    # Compute review turnaround for this specific developer
    avg_turnaround = await db.scalar(
        select(func.avg(PullRequest.time_to_first_review_s))
        .select_from(PRReview)
        .join(PullRequest, PRReview.pr_id == PullRequest.id)
        .where(
            PRReview.reviewer_id == developer_id,
            PullRequest.time_to_first_review_s.isnot(None),
            PRReview.submitted_at >= date_from,
            PRReview.submitted_at <= date_to,
        )
    )
    dev_values["review_turnaround_h"] = avg_turnaround / 3600 if avg_turnaround else 0.0

    percentiles = {}
    for metric_name, bm in benchmarks.items():
        val = dev_values.get(metric_name, 0.0)
        percentiles[metric_name] = PercentilePlacement(
            value=round(val, 2),
            percentile_band=_percentile_band(val, bm, metric_name),
            team_median=bm.p50,
        )

    return DeveloperStatsWithPercentilesResponse(
        **base.model_dump(), percentiles=percentiles
    )


# --- M3: Trend Lines ---


# Polarity: True = higher is better, False = lower is better, None = neutral
_METRIC_POLARITY: dict[str, bool | None] = {
    "prs_merged": True,
    "avg_time_to_merge_h": False,
    "reviews_given": True,
    "additions": None,
    "deletions": None,
    "issues_closed": True,
}


def _linear_regression(values: list[float]) -> tuple[float, float]:
    """Simple OLS: y = slope*x + intercept. Returns (slope, intercept)."""
    n = len(values)
    if n < 2:
        return 0.0, values[0] if values else 0.0
    x_mean = (n - 1) / 2.0
    y_mean = sum(values) / n
    numerator = sum((i - x_mean) * (v - y_mean) for i, v in enumerate(values))
    denominator = sum((i - x_mean) ** 2 for i in range(n))
    if denominator == 0:
        return 0.0, y_mean
    slope = numerator / denominator
    intercept = y_mean - slope * x_mean
    return slope, intercept


def _trend_direction(
    slope: float, n_periods: int, first_val: float, polarity: bool | None
) -> TrendDirection:
    """Classify trend direction using regression slope, respecting metric polarity."""
    # Total change predicted by the regression over all periods
    predicted_change = slope * (n_periods - 1)
    baseline = max(abs(first_val), 1.0)
    change_pct = round(predicted_change / baseline * 100, 1)

    if abs(change_pct) < 5.0:
        direction = "stable"
    elif polarity is None:
        direction = "stable"
    elif polarity:
        direction = "improving" if slope > 0 else "worsening"
    else:
        direction = "improving" if slope < 0 else "worsening"

    return TrendDirection(direction=direction, change_pct=change_pct)


async def get_developer_trends(
    db: AsyncSession,
    developer_id: int,
    periods: int = 8,
    period_type: str = "week",
    sprint_length_days: int = 14,
) -> DeveloperTrendsResponse:
    if period_type == "month":
        period_days = 30
    elif period_type == "sprint":
        period_days = sprint_length_days
    else:
        period_days = 7

    now = datetime.now(timezone.utc)
    period_list: list[TrendPeriod] = []

    for i in range(periods - 1, -1, -1):
        end = now - timedelta(days=i * period_days)
        start = end - timedelta(days=period_days)

        prs_merged = await db.scalar(
            select(func.count()).where(
                PullRequest.author_id == developer_id,
                PullRequest.is_merged.is_(True),
                PullRequest.merged_at >= start,
                PullRequest.merged_at < end,
            )
        ) or 0

        avg_ttm = await db.scalar(
            select(func.avg(PullRequest.time_to_merge_s)).where(
                PullRequest.author_id == developer_id,
                PullRequest.is_merged.is_(True),
                PullRequest.time_to_merge_s.isnot(None),
                PullRequest.merged_at >= start,
                PullRequest.merged_at < end,
            )
        )

        reviews_given = await db.scalar(
            select(func.count()).where(
                PRReview.reviewer_id == developer_id,
                PRReview.submitted_at >= start,
                PRReview.submitted_at < end,
            )
        ) or 0

        code_stats = (
            await db.execute(
                select(
                    func.coalesce(func.sum(PullRequest.additions), 0),
                    func.coalesce(func.sum(PullRequest.deletions), 0),
                ).where(
                    PullRequest.author_id == developer_id,
                    PullRequest.created_at >= start,
                    PullRequest.created_at < end,
                )
            )
        ).one()

        issues_closed = await db.scalar(
            select(func.count()).where(
                Issue.assignee_id == developer_id,
                Issue.closed_at >= start,
                Issue.closed_at < end,
            )
        ) or 0

        period_list.append(
            TrendPeriod(
                start=start,
                end=end,
                prs_merged=prs_merged,
                avg_time_to_merge_h=round(avg_ttm / 3600, 2) if avg_ttm else None,
                reviews_given=reviews_given,
                additions=code_stats[0],
                deletions=code_stats[1],
                issues_closed=issues_closed,
            )
        )

    # Compute trends via linear regression
    trends: dict[str, TrendDirection] = {}
    for metric_name, polarity in _METRIC_POLARITY.items():
        values = []
        for p in period_list:
            val = getattr(p, metric_name, None)
            # Skip None values for optional metrics (e.g., avg_time_to_merge_h)
            values.append(float(val) if val is not None else 0.0)
        non_zero_count = sum(1 for v in values if v != 0.0)
        if non_zero_count < 2:
            trends[metric_name] = TrendDirection(direction="stable", change_pct=0.0)
            continue
        slope, _ = _linear_regression(values)
        trends[metric_name] = _trend_direction(
            slope, len(values), values[0], polarity
        )

    return DeveloperTrendsResponse(
        developer_id=developer_id,
        period_type=period_type,
        periods=period_list,
        trends=trends,
    )


# --- M4: Workload Balance ---


async def get_workload(
    db: AsyncSession,
    team: str | None = None,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
) -> WorkloadResponse:
    date_from, date_to = _default_range(date_from, date_to)

    dev_query = select(Developer).where(Developer.is_active.is_(True))
    if team:
        dev_query = dev_query.where(Developer.team == team)
    dev_result = await db.execute(dev_query)
    developers = list(dev_result.scalars().all())

    if not developers:
        return WorkloadResponse(developers=[], alerts=[])

    workloads: list[DeveloperWorkload] = []
    reviews_given_values: list[tuple[int, int]] = []  # (dev_id, count)
    open_issues_per_dev: list[tuple[int, int]] = []  # (dev_id, count)

    for dev in developers:
        # Open PRs authored (exclude drafts)
        open_authored = await db.scalar(
            select(func.count()).where(
                PullRequest.author_id == dev.id,
                PullRequest.state == "open",
                PullRequest.is_draft.isnot(True),
            )
        ) or 0

        # Draft PRs authored
        drafts_open = await db.scalar(
            select(func.count()).where(
                PullRequest.author_id == dev.id,
                PullRequest.state == "open",
                PullRequest.is_draft.is_(True),
            )
        ) or 0

        # Open PRs reviewing (has a review on an open PR)
        open_reviewing = await db.scalar(
            select(func.count(func.distinct(PullRequest.id)))
            .select_from(PRReview)
            .join(PullRequest, PRReview.pr_id == PullRequest.id)
            .where(
                PRReview.reviewer_id == dev.id,
                PullRequest.state == "open",
            )
        ) or 0

        # Open issues assigned
        open_issues = await db.scalar(
            select(func.count()).where(
                Issue.assignee_id == dev.id,
                Issue.state == "open",
            )
        ) or 0
        open_issues_per_dev.append((dev.id, open_issues))

        # Reviews given this period
        reviews_given = await db.scalar(
            select(func.count()).where(
                PRReview.reviewer_id == dev.id,
                PRReview.submitted_at >= date_from,
                PRReview.submitted_at <= date_to,
            )
        ) or 0
        reviews_given_values.append((dev.id, reviews_given))

        # Reviews received this period
        reviews_received = await db.scalar(
            select(func.count())
            .select_from(PRReview)
            .join(PullRequest, PRReview.pr_id == PullRequest.id)
            .where(
                PullRequest.author_id == dev.id,
                PRReview.submitted_at >= date_from,
                PRReview.submitted_at <= date_to,
            )
        ) or 0

        # PRs waiting for review (open, authored by dev, no reviews yet, exclude drafts)
        prs_waiting = await db.scalar(
            select(func.count()).where(
                PullRequest.author_id == dev.id,
                PullRequest.state == "open",
                PullRequest.first_review_at.is_(None),
                PullRequest.is_draft.isnot(True),
            )
        ) or 0

        # Avg review wait — avg time_to_first_review for dev's reviewed PRs in period
        avg_wait = await db.scalar(
            select(func.avg(PullRequest.time_to_first_review_s)).where(
                PullRequest.author_id == dev.id,
                PullRequest.time_to_first_review_s.isnot(None),
                PullRequest.created_at >= date_from,
                PullRequest.created_at <= date_to,
            )
        )

        # Workload score heuristic (pending work only — completed reviews are output, not load)
        total_load = open_authored + open_reviewing + open_issues
        if total_load == 0:
            score = "low"
        elif total_load <= 5:
            score = "balanced"
        elif total_load <= 12:
            score = "high"
        else:
            score = "overloaded"

        workloads.append(
            DeveloperWorkload(
                developer_id=dev.id,
                github_username=dev.github_username,
                display_name=dev.display_name,
                open_prs_authored=open_authored,
                drafts_open=drafts_open,
                open_prs_reviewing=open_reviewing,
                open_issues_assigned=open_issues,
                reviews_given_this_period=reviews_given,
                reviews_received_this_period=reviews_received,
                prs_waiting_for_review=prs_waiting,
                avg_review_wait_h=round(avg_wait / 3600, 2) if avg_wait else None,
                workload_score=score,
            )
        )

    # Generate alerts
    alerts: list[WorkloadAlert] = []

    # Review bottleneck: reviews_given > 2x team median
    review_counts = [c for _, c in reviews_given_values]
    if review_counts:
        team_median_reviews = statistics.median(review_counts)
        for dev_id, count in reviews_given_values:
            if team_median_reviews > 0 and count > 2 * team_median_reviews:
                dev = next(d for d in developers if d.id == dev_id)
                alerts.append(
                    WorkloadAlert(
                        type="review_bottleneck",
                        developer_id=dev_id,
                        message=f"{dev.display_name} gave {count} reviews "
                        f"(team median: {team_median_reviews:.0f})",
                    )
                )

    # Stale PRs: any PR waiting for first review > 48h
    now = datetime.now(timezone.utc)
    stale_cutoff = now - timedelta(hours=48)
    stale_prs_result = await db.execute(
        select(PullRequest.number, PullRequest.title, PullRequest.author_id).where(
            PullRequest.state == "open",
            PullRequest.first_review_at.is_(None),
            PullRequest.created_at <= stale_cutoff,
            PullRequest.is_draft.isnot(True),
        )
    )
    for row in stale_prs_result.all():
        alerts.append(
            WorkloadAlert(
                type="stale_prs",
                developer_id=row.author_id,
                message=f"PR #{row.number} ({row.title}) waiting for review > 48h",
            )
        )

    # Uneven assignment: top 20% hold > 50% of open issues
    if open_issues_per_dev:
        sorted_issues = sorted(open_issues_per_dev, key=lambda x: x[1], reverse=True)
        total_open_issues = sum(c for _, c in sorted_issues)
        if total_open_issues > 0:
            top_20_count = max(1, len(sorted_issues) // 5)
            top_20_issues = sum(c for _, c in sorted_issues[:top_20_count])
            if top_20_issues > total_open_issues * 0.5:
                top_names = []
                for dev_id, _ in sorted_issues[:top_20_count]:
                    dev = next(d for d in developers if d.id == dev_id)
                    top_names.append(dev.display_name)
                alerts.append(
                    WorkloadAlert(
                        type="uneven_assignment",
                        message=f"Top {top_20_count} dev(s) ({', '.join(top_names)}) "
                        f"hold {top_20_issues}/{total_open_issues} open issues",
                    )
                )

    # Underutilized: 0 PRs and 0 reviews in period
    for dev in developers:
        dev_prs = await db.scalar(
            select(func.count()).where(
                PullRequest.author_id == dev.id,
                PullRequest.created_at >= date_from,
                PullRequest.created_at <= date_to,
            )
        ) or 0
        dev_reviews = next(
            (c for did, c in reviews_given_values if did == dev.id), 0
        )
        if dev_prs == 0 and dev_reviews == 0:
            alerts.append(
                WorkloadAlert(
                    type="underutilized",
                    developer_id=dev.id,
                    message=f"{dev.display_name} has 0 PRs and 0 reviews in the period",
                )
            )

    # Merged without approval: per-developer and team-level alerts
    total_merged_no_approval = 0
    for dev in developers:
        dev_no_approval = await db.scalar(
            select(func.count()).where(
                PullRequest.author_id == dev.id,
                PullRequest.merged_without_approval.is_(True),
                PullRequest.merged_at >= date_from,
                PullRequest.merged_at <= date_to,
            )
        ) or 0
        total_merged_no_approval += dev_no_approval
        if dev_no_approval > 0:
            alerts.append(
                WorkloadAlert(
                    type="merged_without_approval",
                    developer_id=dev.id,
                    message=f"{dev.display_name} has {dev_no_approval} PR(s) "
                    f"merged without approval this period",
                )
            )
    if total_merged_no_approval > 0:
        alerts.append(
            WorkloadAlert(
                type="merged_without_approval",
                message=f"{total_merged_no_approval} PR(s) merged without "
                f"any approval this period",
            )
        )

    # Revert spike: revert rate exceeds 5%
    dev_ids = [d.id for d in developers]
    total_merged_team = await db.scalar(
        select(func.count()).where(
            PullRequest.author_id.in_(dev_ids),
            PullRequest.is_merged.is_(True),
            PullRequest.merged_at >= date_from,
            PullRequest.merged_at <= date_to,
        )
    ) or 0
    total_reverts = await db.scalar(
        select(func.count()).where(
            PullRequest.author_id.in_(dev_ids),
            PullRequest.is_revert.is_(True),
            PullRequest.created_at >= date_from,
            PullRequest.created_at <= date_to,
        )
    ) or 0
    if total_merged_team > 0:
        revert_pct = total_reverts / total_merged_team * 100
        if revert_pct > 5:
            alerts.append(
                WorkloadAlert(
                    type="revert_spike",
                    message=f"Revert rate is {revert_pct:.1f}% "
                    f"({total_reverts} reverts out of {total_merged_team} merged PRs)",
                )
            )

    return WorkloadResponse(developers=workloads, alerts=alerts)


async def get_stale_prs(
    db: AsyncSession,
    team: str | None = None,
    threshold_hours: int = 24,
) -> StalePRsResponse:
    now = datetime.now(timezone.utc)
    cutoff = now - timedelta(hours=threshold_hours)

    # Build base filter for open, non-draft PRs
    base_filters = [
        PullRequest.state == "open",
        PullRequest.is_draft.isnot(True),
    ]

    # Team filter: restrict to PRs authored by team members
    if team:
        dev_query = select(Developer.id).where(
            Developer.is_active.is_(True),
            Developer.team == team,
        )
        dev_result = await db.execute(dev_query)
        dev_ids = [row[0] for row in dev_result.all()]
        if not dev_ids:
            return StalePRsResponse(stale_prs=[], total_count=0)
        base_filters.append(PullRequest.author_id.in_(dev_ids))

    # --- Category 1: No review (open, not draft, no first review, age > threshold) ---
    no_review_query = (
        select(PullRequest)
        .where(
            *base_filters,
            PullRequest.first_review_at.is_(None),
            PullRequest.created_at <= cutoff,
        )
    )
    no_review_result = await db.execute(no_review_query)
    no_review_prs = no_review_result.scalars().all()

    # --- Category 2: Changes requested, no response ---
    # Find PRs where the most recent review is CHANGES_REQUESTED
    # and the PR hasn't been updated significantly since that review.
    # We fetch candidates in SQL, then filter the "no response" heuristic in Python
    # (timedelta arithmetic on columns isn't portable across SQLite/PostgreSQL).
    latest_review_subq = (
        select(
            PRReview.pr_id,
            func.max(PRReview.submitted_at).label("latest_submitted_at"),
        )
        .group_by(PRReview.pr_id)
        .subquery()
    )

    changes_requested_query = (
        select(PullRequest, PRReview.submitted_at.label("review_submitted_at"))
        .join(PRReview, PRReview.pr_id == PullRequest.id)
        .join(
            latest_review_subq,
            and_(
                latest_review_subq.c.pr_id == PullRequest.id,
                latest_review_subq.c.latest_submitted_at == PRReview.submitted_at,
            ),
        )
        .where(
            *base_filters,
            PRReview.state == "CHANGES_REQUESTED",
            PRReview.submitted_at <= cutoff,
        )
    )
    changes_requested_result = await db.execute(changes_requested_query)
    changes_requested_prs = []
    for row in changes_requested_result.all():
        pr = row[0]
        review_at = row.review_submitted_at
        pr_updated = pr.updated_at
        # Normalize tz for comparison
        if review_at and review_at.tzinfo is None:
            review_at = review_at.replace(tzinfo=timezone.utc)
        if pr_updated and pr_updated.tzinfo is None:
            pr_updated = pr_updated.replace(tzinfo=timezone.utc)
        # No author response: PR updated_at within 1h of the review
        if pr_updated and review_at and pr_updated <= review_at + timedelta(hours=1):
            changes_requested_prs.append(pr)

    # --- Category 3: Approved but not merged ---
    # Has at least one APPROVED review, last approval > threshold ago
    latest_approval_subq = (
        select(
            PRReview.pr_id,
            func.max(PRReview.submitted_at).label("latest_approval_at"),
        )
        .where(PRReview.state == "APPROVED")
        .group_by(PRReview.pr_id)
        .subquery()
    )

    approved_not_merged_query = (
        select(PullRequest)
        .join(
            latest_approval_subq,
            latest_approval_subq.c.pr_id == PullRequest.id,
        )
        .where(
            *base_filters,
            PullRequest.is_merged.isnot(True),
            latest_approval_subq.c.latest_approval_at <= cutoff,
        )
    )
    approved_result = await db.execute(approved_not_merged_query)
    approved_not_merged_prs = approved_result.scalars().all()

    # Deduplicate (a PR could match multiple categories; keep highest priority reason)
    seen_ids: dict[int, str] = {}
    pr_map: dict[int, PullRequest] = {}

    for pr in no_review_prs:
        if pr.id not in seen_ids:
            seen_ids[pr.id] = "no_review"
            pr_map[pr.id] = pr

    for pr in changes_requested_prs:
        if pr.id not in seen_ids:
            seen_ids[pr.id] = "changes_requested_no_response"
            pr_map[pr.id] = pr

    for pr in approved_not_merged_prs:
        if pr.id not in seen_ids:
            seen_ids[pr.id] = "approved_not_merged"
            pr_map[pr.id] = pr

    # Build response objects with review counts and author/repo info
    stale_list: list[StalePR] = []
    for pr_id, reason in seen_ids.items():
        pr = pr_map[pr_id]

        # Get review stats for this PR
        review_count = await db.scalar(
            select(func.count()).select_from(PRReview).where(PRReview.pr_id == pr.id)
        ) or 0
        has_approved = (
            await db.scalar(
                select(func.count())
                .select_from(PRReview)
                .where(PRReview.pr_id == pr.id, PRReview.state == "APPROVED")
            )
            or 0
        ) > 0
        has_changes_requested = (
            await db.scalar(
                select(func.count())
                .select_from(PRReview)
                .where(
                    PRReview.pr_id == pr.id, PRReview.state == "CHANGES_REQUESTED"
                )
            )
            or 0
        ) > 0

        # Get repo name
        repo = await db.get(Repository, pr.repo_id)
        repo_name = repo.full_name or repo.name or "unknown" if repo else "unknown"

        # Get author name
        author_name = None
        if pr.author_id:
            author = await db.get(Developer, pr.author_id)
            if author:
                author_name = author.display_name

        created = pr.created_at
        if created and created.tzinfo is None:
            created = created.replace(tzinfo=timezone.utc)
        age_hours = (now - created).total_seconds() / 3600 if created else 0

        last_activity = pr.updated_at or pr.created_at or now
        if last_activity.tzinfo is None:
            last_activity = last_activity.replace(tzinfo=timezone.utc)

        stale_list.append(
            StalePR(
                pr_id=pr.id,
                number=pr.number,
                title=pr.title or "",
                html_url=pr.html_url or "",
                repo_name=repo_name,
                author_name=author_name,
                author_id=pr.author_id,
                age_hours=round(age_hours, 1),
                is_draft=bool(pr.is_draft),
                review_count=review_count,
                has_approved=has_approved,
                has_changes_requested=has_changes_requested,
                last_activity_at=last_activity,
                stale_reason=reason,
            )
        )

    # Sort by age descending (most stale first)
    stale_list.sort(key=lambda x: x.age_hours, reverse=True)

    return StalePRsResponse(stale_prs=stale_list, total_count=len(stale_list))


# --- P2-04: Issue-PR Linkage ---


async def get_issue_linkage_stats(
    db: AsyncSession,
    team: str | None = None,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
) -> IssueLinkageStats:
    date_from, date_to = _default_range(date_from, date_to)

    # Team filter: get developer IDs if team is specified
    team_dev_ids: list[int] | None = None
    if team:
        dev_result = await db.execute(
            select(Developer.id).where(
                Developer.is_active.is_(True),
                Developer.team == team,
            )
        )
        team_dev_ids = [row[0] for row in dev_result.all()]
        if not team_dev_ids:
            return IssueLinkageStats(
                issues_with_linked_prs=0,
                issues_without_linked_prs=0,
                avg_prs_per_issue=None,
                issues_with_multiple_prs=0,
                prs_without_linked_issues=0,
            )

    # Get all PRs in date range that have closing keywords
    pr_filters = [
        PullRequest.created_at >= date_from,
        PullRequest.created_at <= date_to,
        PullRequest.closes_issue_numbers.isnot(None),
    ]
    if team_dev_ids is not None:
        pr_filters.append(PullRequest.author_id.in_(team_dev_ids))

    pr_result = await db.execute(
        select(PullRequest.repo_id, PullRequest.closes_issue_numbers).where(*pr_filters)
    )
    pr_rows = pr_result.all()

    # Build map: (repo_id, issue_number) → count of PRs referencing it
    issue_ref_counts: dict[tuple[int, int], int] = {}
    prs_with_refs = 0
    prs_without_refs = 0

    for repo_id, issue_nums in pr_rows:
        if issue_nums:
            prs_with_refs += 1
            for num in issue_nums:
                key = (repo_id, num)
                issue_ref_counts[key] = issue_ref_counts.get(key, 0) + 1
        else:
            prs_without_refs += 1

    # Also count PRs with no closing keywords at all
    all_pr_filters = [
        PullRequest.created_at >= date_from,
        PullRequest.created_at <= date_to,
    ]
    if team_dev_ids is not None:
        all_pr_filters.append(PullRequest.author_id.in_(team_dev_ids))

    total_prs = await db.scalar(
        select(func.count()).where(*all_pr_filters)
    ) or 0
    prs_without_linked_issues = total_prs - prs_with_refs

    # Get all closed issues in date range
    issue_filters = [
        Issue.state == "closed",
        Issue.closed_at >= date_from,
        Issue.closed_at <= date_to,
    ]
    if team_dev_ids is not None:
        issue_filters.append(Issue.assignee_id.in_(team_dev_ids))

    issue_result = await db.execute(
        select(Issue.repo_id, Issue.number).where(*issue_filters)
    )
    closed_issues = issue_result.all()

    # Cross-reference closed issues with PR linkage
    issues_with_linked_prs = 0
    issues_without_linked_prs = 0
    issues_with_multiple_prs = 0
    pr_counts_per_issue: list[int] = []

    for repo_id, issue_number in closed_issues:
        key = (repo_id, issue_number)
        ref_count = issue_ref_counts.get(key, 0)
        if ref_count > 0:
            issues_with_linked_prs += 1
            pr_counts_per_issue.append(ref_count)
            if ref_count >= 2:
                issues_with_multiple_prs += 1
        else:
            issues_without_linked_prs += 1

    avg_prs_per_issue = (
        round(sum(pr_counts_per_issue) / len(pr_counts_per_issue), 2)
        if pr_counts_per_issue
        else None
    )

    return IssueLinkageStats(
        issues_with_linked_prs=issues_with_linked_prs,
        issues_without_linked_prs=issues_without_linked_prs,
        avg_prs_per_issue=avg_prs_per_issue,
        issues_with_multiple_prs=issues_with_multiple_prs,
        prs_without_linked_issues=prs_without_linked_issues,
    )
