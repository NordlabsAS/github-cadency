# Task P4-01: DORA Metrics (Deploy Frequency + Change Lead Time)

## Phase
Phase 4 — Make It Best-in-Class

## Status
pending

## Blocked By
- P3-07-ci-check-runs

## Blocks
None

## Description
Implement the two most accessible DORA metrics using GitHub Actions as the deployment signal. DORA (Deployment Frequency, Lead Time for Changes, Change Failure Rate, Mean Time to Recovery) is the industry standard framework for measuring software delivery. Without DORA metrics, DevPulse is difficult to justify to leadership who think in DORA terms.

This task focuses on the two metrics achievable with GitHub data alone: Deploy Frequency and Change Lead Time. Change Failure Rate and MTTR require incident management integration (out of scope).

## Deliverables

### Database migration
New table: `deployments`
- `id` (Integer, PK)
- `repo_id` (Integer, FK to repositories)
- `environment` (String(100)) — "production", "staging", etc.
- `sha` (String(40)) — deployed commit SHA
- `deployed_at` (DateTime)
- `workflow_name` (String(255)) — GitHub Actions workflow name
- `workflow_run_id` (BigInteger) — GitHub Actions run ID
- `status` (String(30)) — "success", "failure"
- `lead_time_s` (Integer, nullable) — time from first commit to deploy

### backend/app/services/github_sync.py (extend)
New sync step: fetch GitHub Actions deployment events
- Use GitHub Deployments API: `GET /repos/{owner}/{repo}/deployments`
- Or detect from workflow runs: `GET /repos/{owner}/{repo}/actions/runs?event=push&branch=main&status=success`
- Configurable: `DEPLOY_WORKFLOW_NAME` env var to identify the deployment workflow
- For each deployment, compute `lead_time_s`: time from the oldest undeployed merged PR's `merged_at` to `deployed_at`

### backend/app/services/stats.py (extend)
New function: `async def get_dora_metrics(session, date_from, date_to, repo_id=None)`

Returns:
- `deploy_frequency` — deployments per day in the period
- `deploy_frequency_band` — "elite" (multiple/day), "high" (daily-weekly), "medium" (weekly-monthly), "low" (monthly+) per DORA benchmarks
- `avg_lead_time_hours` — average time from merge to deploy
- `lead_time_band` — "elite" (<1h), "high" (<1 day), "medium" (<1 week), "low" (>1 week)
- `deployments` — list of recent deployments with details

### backend/app/schemas/schemas.py (extend)
```python
class DORAMetrics(BaseModel):
    deploy_frequency: float  # deploys per day
    deploy_frequency_band: str
    avg_lead_time_hours: float | None
    lead_time_band: str
    total_deployments: int
    period_days: int
```

### backend/app/api/stats.py (extend)
New route: `GET /api/stats/dora`
- Query params: `date_from`, `date_to`, `repo_id` (optional)
- Returns `DORAMetrics`

### backend/app/config.py (extend)
- `DEPLOY_WORKFLOW_NAME` (String, default "") — GitHub Actions workflow name that represents a production deployment
- `DEPLOY_ENVIRONMENT` (String, default "production") — environment name to track
