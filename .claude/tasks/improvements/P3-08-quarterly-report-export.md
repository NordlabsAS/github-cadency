# Task P3-08: Quarterly Performance Report Export

## Phase
Phase 3 — Make It Proactive

## Status
pending

## Blocked By
- M3-trend-lines
- M2-team-benchmarks
- M6-developer-goals

## Blocks
None

## Description
Add a structured quarterly report endpoint that returns a developer's performance summary over a 3-month period, suitable for performance reviews and manager-to-director reporting. Currently, a team lead preparing for a performance review must manually query multiple endpoints and mentally aggregate the data.

## Deliverables

### backend/app/services/reports.py (new)
New function: `async def generate_quarterly_report(session, developer_id, quarter_start, quarter_end)`

Gathers:
1. Developer stats for the quarter (from `get_developer_stats`)
2. Developer stats for the previous quarter (for comparison)
3. Percentile placement (from `get_developer_stats` with `include_percentiles=True`)
4. Trend data across the quarter (from `get_developer_trends`)
5. Goal status: active, achieved, abandoned counts
6. Review quality breakdown
7. Collaboration summary: top review partners, repos contributed to
8. Notable PRs: largest merged PRs by additions, most-reviewed PRs

Returns a `QuarterlyReport` schema with all sections pre-computed.

### backend/app/schemas/schemas.py (extend)
```python
class QuarterlyReport(BaseModel):
    developer_id: int
    developer_name: str
    period: str  # "Q1 2026"
    quarter_start: date
    quarter_end: date

    # Current quarter stats
    stats: DeveloperStatsResponse
    # Previous quarter stats for comparison
    previous_stats: DeveloperStatsResponse | None
    # Delta percentages for key metrics
    deltas: dict[str, float]  # {"prs_merged": 15.0, "time_to_merge": -8.5, ...}

    # Percentile placement
    percentiles: dict[str, str]  # {"prs_merged": "above_p75", ...}

    # Trend summary
    trend_directions: dict[str, str]  # {"prs_merged": "improving", ...}

    # Goals
    goals_achieved: int
    goals_active: int
    goals_abandoned: int

    # Review quality
    review_quality: dict  # quality breakdown

    # Notable work
    notable_prs: list[dict]  # [{number, title, html_url, additions, reviews_count}]

    # Collaboration
    top_review_partners: list[dict]  # [{name, reviews_exchanged}]
    repos_contributed_to: list[str]
```

### backend/app/api/reports.py (new)
- `GET /api/reports/developer/{id}/quarterly` — returns JSON report
  - Query params: `quarter_start`, `quarter_end` (or `quarter` like "2026-Q1")
- `GET /api/reports/developer/{id}/quarterly/markdown` — returns Markdown-formatted report
  - Same params, returns `text/markdown` content type

### Markdown format
The Markdown export should be copy-pasteable into Notion, Confluence, or email:
```markdown
# Quarterly Review: {developer_name} — {period}

## Summary
- PRs Merged: {N} ({delta}% vs previous quarter)
- Avg Time to Merge: {N}h ({delta}% vs previous quarter)
...

## Team Context
- Percentile placement: above p75 on review quality, p50-p75 on velocity

## Trends
- Improving: review quality, time to first review
- Stable: PRs merged
- Worsening: none

## Goals
- Achieved: {N} | Active: {N} | Abandoned: {N}

## Notable Work
- PR #123: "Add auth middleware" (450 additions, 3 reviews)
...
```
