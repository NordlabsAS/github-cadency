# P2-02: Working Agreements with Automated Notifications

> Priority: 2 (Differentiate) | Effort: Medium | Impact: Medium-High
> Competitive gap: Swarmia's "working agreements" and LinearB's "gitStream" turn passive dashboards into active improvement tools.

## Context

Working agreements are team-set targets (e.g., "PRs should be reviewed within 4 hours", "No PR should be open more than 5 days") with automated monitoring and notifications when agreements are violated. Swarmia has made this a core differentiator.

DevPulse already computes all the underlying metrics. This feature layers goal-like targets with automated monitoring on top of existing data, transforming DevPulse from "observe-only" to an "active improvement tool."

## What to Build

### Working Agreement Types

| Agreement | Metric Source | Example Target |
|-----------|--------------|----------------|
| PR review time | `time_to_first_review_s` | First review within 4 hours |
| PR cycle time | `total_cycle_time_s` | Merged within 3 days |
| PR size limit | `additions + deletions` | Max 400 lines changed |
| Stale PR limit | Open PR age | No PRs open > 5 days |
| Review quality | `review_quality_tier` | <10% rubber stamp reviews |
| Workload balance | Workload score | No developer overloaded (>12) |
| DORA deploy frequency | Deploy frequency | At least 1 deploy/day |
| DORA lead time | Lead time | Under 24 hours |

### Agreement Lifecycle

1. **Create:** Admin or tech lead defines agreement for a team (or org-wide)
2. **Monitor:** Scheduled job checks agreements against current metrics
3. **Alert:** When violated, notify via dashboard banner + Slack (if integrated)
4. **Track:** Historical compliance rate over time
5. **Review:** Weekly/monthly compliance summary

## Backend Changes

### New Model: `working_agreements` table
```
id, name, description, metric_type (enum matching above),
operator ("lt" | "gt" | "lte" | "gte" | "eq"),
threshold_value (float), threshold_unit ("hours" | "days" | "lines" | "percent" | "count"),
scope_type ("org" | "team"), scope_value (str, nullable — team name),
status ("active" | "paused" | "archived"),
notification_channels (JSONB — slack channel IDs),
created_by (FK), created_at, updated_at
```

### New Model: `agreement_violations` table
```
id, agreement_id (FK), violated_at, resolved_at,
entity_type ("pull_request" | "developer" | "team"),
entity_id (int), details (JSONB — metric value, threshold, context),
notification_sent (bool), notification_sent_at
```

### New Model: `agreement_compliance` table
```
id, agreement_id (FK), period_start, period_end,
total_measured (int), total_compliant (int),
compliance_rate (float), computed_at
```

### New Service: `backend/app/services/agreements.py`
- `check_agreements()` — scheduled job, evaluates all active agreements
- `evaluate_agreement(agreement)` — compute current metric vs threshold
- `record_violation(agreement, entity_type, entity_id, details)`
- `resolve_violations(agreement)` — auto-resolve when metric returns to compliance
- `compute_compliance_history(agreement_id, periods)` — weekly/monthly compliance rates
- `get_team_compliance_summary(team)` — all agreements for a team with current status

### New Router: `backend/app/api/agreements.py`
- `POST /api/agreements` — create agreement (admin/lead)
- `GET /api/agreements` — list agreements with current compliance
- `GET /api/agreements/{id}` — detail with violation history
- `PATCH /api/agreements/{id}` — update threshold/config
- `DELETE /api/agreements/{id}` — archive agreement
- `GET /api/agreements/compliance` — compliance trends over time
- `GET /api/agreements/violations` — active violations (filterable)

### Scheduler Integration (`backend/app/main.py`)
- Add `check_agreements` job — runs every 15 minutes (configurable)
- On each run: evaluate all active agreements → create/resolve violations → send notifications

### Slack Integration (if P1-02 implemented)
- New notification type: `agreement_violation`
- Format: "Working agreement '{name}' violated: {details}. [View Dashboard]"
- Daily digest of active violations (if any)

## Frontend Changes

### Working Agreements Page (`/admin/agreements`)
- Agreement list with compliance badges (green/amber/red)
- Create/edit agreement dialog with metric picker, threshold config
- Per-agreement detail: compliance trend chart, active violations, history

### Agreements Dashboard Widget
- Top-level compliance summary card on Dashboard
- "3 of 5 agreements met" style indicator
- Active violations list with severity

### Team Detail Integration
- Show team's agreement compliance on team pages
- Highlight specific violations (e.g., "2 PRs exceed cycle time agreement")

### Insights Integration (`/insights/agreements`)
- Compliance trend charts over time
- Cross-team comparison of agreement adherence
- Most frequently violated agreements

## Testing
- Unit test each agreement type evaluation logic
- Unit test violation creation and resolution
- Unit test compliance rate computation
- Unit test scheduler integration (check_agreements runs correctly)
- Test edge cases: no data for metric, team with zero PRs, etc.

## Acceptance Criteria
- [ ] Admins can create working agreements with metric thresholds
- [ ] Agreements automatically evaluated on schedule (every 15 min)
- [ ] Violations created when metrics exceed thresholds
- [ ] Violations auto-resolved when metrics return to compliance
- [ ] Compliance rate tracked over time (weekly/monthly)
- [ ] Dashboard widget showing current compliance status
- [ ] Slack notifications for violations (if Slack integrated)
- [ ] Agreement compliance trends visible in insights
