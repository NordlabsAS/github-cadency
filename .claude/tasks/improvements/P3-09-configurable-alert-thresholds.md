# Task P3-09: Configurable Alert Thresholds

## Phase
Phase 3 — Make It Proactive

## Status
pending

## Blocked By
- M4-workload-balance
- P3-01-slack-webhook-notifications

## Blocks
None

## Description
Make all hardcoded alert thresholds configurable per team. Currently, the workload score buckets, bus factor threshold (>70%), stale PR threshold (48h), and underutilized definition are all hardcoded constants. Different teams have different cadences — a distributed async team needs a longer stale PR threshold than a co-located team.

## Deliverables

### Database migration
New table: `alert_configs`
- `id` (Integer, PK)
- `team` (String, nullable) — null = global default
- `stale_pr_threshold_hours` (Integer, default 24)
- `overloaded_score_threshold` (Integer, default 12)
- `bus_factor_threshold_pct` (Integer, default 70)
- `underutilized_min_weeks` (Integer, default 2) — require N consecutive zero-activity weeks before alerting
- `review_bottleneck_pending_count` (Integer, default 5) — flag reviewer as bottleneck when pending > N
- `created_at` (DateTime)
- `updated_at` (DateTime)

### backend/app/services/stats.py (extend)
- Load alert config at the start of `get_workload()` — query `alert_configs` for the team, fall back to global default, fall back to hardcoded values
- Replace all hardcoded thresholds with config values
- For `underutilized`: only fire if the developer has had zero activity for `underutilized_min_weeks` consecutive weeks, not just the current period

### backend/app/services/collaboration.py (extend)
- Load bus factor threshold from config instead of hardcoded 70%

### backend/app/api/config.py (new)
- `GET /api/config/alerts?team=` — get alert configuration
- `PATCH /api/config/alerts` — update alert configuration
  - Body: partial update of any threshold fields
  - If team is specified, creates/updates team-specific config; otherwise updates global

### backend/app/schemas/schemas.py (extend)
```python
class AlertConfig(BaseModel):
    team: str | None
    stale_pr_threshold_hours: int
    overloaded_score_threshold: int
    bus_factor_threshold_pct: int
    underutilized_min_weeks: int
    review_bottleneck_pending_count: int

class AlertConfigUpdate(BaseModel):
    team: str | None = None
    stale_pr_threshold_hours: int | None = None
    overloaded_score_threshold: int | None = None
    bus_factor_threshold_pct: int | None = None
    underutilized_min_weeks: int | None = None
    review_bottleneck_pending_count: int | None = None
```

### Frontend
- Add a Settings/Config page accessible to admins
- Form for adjusting alert thresholds per team
- Explain each threshold with a description of what it controls
