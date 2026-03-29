# P3-06: Historical Metric Snapshots

> Priority: 3 (Nice-to-Have) | Effort: Medium | Impact: Medium
> Competitive gap: Metrics recomputed on-demand; no point-in-time snapshots for "how were we doing 6 months ago?"

## Context

DevPulse recomputes all metrics on-demand from raw data. This means historical views depend on having historical data, but some derived metrics (workload balance, team composition, collaboration patterns) change as the team changes. There's no way to answer "what did our dashboard look like last quarter?"

## What to Build

### Periodic Metric Snapshots

Scheduled job captures a snapshot of all key metrics at regular intervals (daily, weekly).

### Snapshot Data

| Snapshot Category | Metrics Captured |
|-------------------|-----------------|
| Team Stats | PR throughput, avg cycle time, avg review time, merge rate, revert rate |
| DORA | Deploy frequency, lead time, CFR, MTTR, overall band |
| Workload | Per-developer workload scores, overloaded count, distribution |
| Review Quality | % per tier (thorough/standard/rubber_stamp/minimal) |
| Collaboration | Silo count, bus factor risks, isolated developers |
| Investment | % feature/bugfix/tech_debt/ops/unknown |
| Goals | Team compliance rate, goals on-track count |
| Headcount | Active developer count, team sizes |

### Features

- **Time machine:** View any metric as of a specific past date
- **Period comparison:** Compare current quarter vs. last quarter
- **Trend charts with historical context:** Richer trend data beyond the 30-day window
- **Executive reporting:** "Here's how we improved since last quarter" backed by snapshots

## Backend Changes

### New Model: `metric_snapshots` table
```
id, snapshot_date (date, indexed),
snapshot_type ("daily" | "weekly" | "monthly"),
scope_type ("org" | "team"), scope_value (str, nullable),
category (str — "team_stats" | "dora" | "workload" | etc.),
metrics (JSONB — the captured metric values),
created_at
```
Unique constraint on (snapshot_date, snapshot_type, scope_type, scope_value, category).

### New Service: `backend/app/services/snapshots.py`
- `capture_snapshot(scope, categories)` — compute and store current metrics
- `capture_all_snapshots()` — scheduled job, captures org + per-team snapshots
- `get_snapshot(date, scope, category)` — retrieve a point-in-time snapshot
- `get_snapshot_series(start, end, scope, category)` — time series for trend charts
- `compare_periods(period1, period2, scope)` — side-by-side comparison
- Data sourced from existing stats/DORA/workload/collaboration services

### Scheduler Integration
- Daily snapshot at configurable time (default 2 AM)
- Weekly snapshot on Monday
- Monthly snapshot on 1st of month
- Backfill: on first run, attempt to generate historical snapshots from existing data

### New Router: `backend/app/api/snapshots.py`
- `GET /api/snapshots?date={date}&scope={scope}&category={category}` — get snapshot
- `GET /api/snapshots/series?start={start}&end={end}&category={category}` — time series
- `GET /api/snapshots/compare?period1_start&period1_end&period2_start&period2_end` — period comparison
- `POST /api/snapshots/capture` — trigger manual snapshot (admin)
- `GET /api/snapshots/dates` — list available snapshot dates

### Retention Policy
- Daily snapshots: keep 90 days, then aggregate to weekly
- Weekly snapshots: keep 1 year, then aggregate to monthly
- Monthly snapshots: keep indefinitely
- Configurable via settings

## Frontend Changes

### Time Machine Mode
- Date picker that loads snapshot data instead of live data
- Visual indicator: "Viewing snapshot from March 1, 2026"
- Available on Dashboard, Executive Dashboard, Insights pages

### Period Comparison View (`/insights/compare`)
- Side-by-side metric cards: Period A vs Period B
- Delta indicators (improved/declined/stable)
- Mini trend charts spanning both periods

### Enhanced Trend Charts
- Trend charts can now span months/quarters (not just 30 days)
- Monthly data points from snapshots fill in historical gaps
- Smooth transition between snapshot data and live computed data

### Executive Dashboard Enhancement
- Quarter-over-quarter comparison cards
- "Since last snapshot" deltas on key metrics

## Testing
- Unit test snapshot capture for each category
- Unit test time series assembly (fill gaps, handle missing snapshots)
- Unit test period comparison with different time ranges
- Unit test retention policy (daily → weekly aggregation)
- Test backfill logic with existing data

## Acceptance Criteria
- [ ] Daily metric snapshots captured automatically
- [ ] Weekly and monthly snapshots captured on schedule
- [ ] Point-in-time snapshot retrieval via API
- [ ] Time series of snapshots for trend visualization
- [ ] Period comparison (quarter vs. quarter)
- [ ] Retention policy with aggregation
- [ ] Time machine mode on Dashboard and Executive Dashboard
- [ ] Enhanced trend charts spanning months/quarters
