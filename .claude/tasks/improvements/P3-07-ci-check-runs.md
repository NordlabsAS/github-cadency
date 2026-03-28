# Task P3-07: CI/CD Check-Run Integration

## Phase
Phase 3 — Make It Proactive

## Status
pending

## Blocked By
- 04-github-sync-service

## Blocks
- P4-01-dora-metrics

## Description
Track GitHub Actions check runs per PR to surface CI/CD quality signals: PRs merged with failing checks, flaky test detection (multiple retries before green), build duration trends. This is the largest single architectural gap for QA use cases.

## Deliverables

### Database migration
Add column to `pull_requests`:
- `head_sha` (String(40), nullable) — HEAD commit SHA, needed to fetch check runs

New table: `pr_check_runs`
- `id` (Integer, PK)
- `pr_id` (Integer, FK to pull_requests)
- `check_name` (String(255)) — e.g., "tests", "lint", "build"
- `conclusion` (String(30)) — "success", "failure", "neutral", "skipped", "cancelled", "timed_out"
- `started_at` (DateTime, nullable)
- `completed_at` (DateTime, nullable)
- `duration_s` (Integer, nullable)
- `run_attempt` (Integer, default 1) — which attempt this was (for detecting retries)

### backend/app/services/github_sync.py (extend)
In `upsert_pull_request()`:
- Capture `head_sha` from `pr_data.get("head", {}).get("sha")`
- After upserting the PR, fetch check runs: `GET /repos/{full_name}/commits/{head_sha}/check-runs`
- Upsert each check run into `pr_check_runs`

### backend/app/services/stats.py (extend)
New function: `async def get_ci_stats(session, date_from, date_to, repo_id=None)`

Returns:
- `prs_merged_with_failing_checks` — PRs where is_merged=True and any check has conclusion="failure"
- `avg_checks_to_green` — average number of check-run attempts before all pass
- `flaky_checks` — check names with >10% failure rate (likely flaky tests)
- `avg_build_duration_s` — average check run duration
- `slowest_checks` — top 5 slowest check names by average duration

### backend/app/schemas/schemas.py (extend)
```python
class CIStats(BaseModel):
    prs_merged_with_failing_checks: int
    avg_checks_to_green: float | None
    flaky_checks: list[dict]  # [{name, failure_rate, total_runs}]
    avg_build_duration_s: float | None
    slowest_checks: list[dict]  # [{name, avg_duration_s}]
```

### backend/app/api/stats.py (extend)
New route: `GET /api/stats/ci`
- Query params: `date_from`, `date_to`, `repo_id` (optional)
- Returns `CIStats`

## Rate Limit Note
Check runs API call is 1 per PR (for the HEAD SHA). Same rate-limit consideration as P3-06 (code churn). Consider batching or only fetching for recently updated PRs during incremental sync.
