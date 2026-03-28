# Task P3-01: Slack Webhook Notifications for Alerts and PR Nudges

## Phase
Phase 3 — Make It Proactive

## Status
pending

## Blocked By
- P2-01-stale-pr-endpoint
- M4-workload-balance

## Blocks
None

## Description
Add a webhook dispatch system that pushes alerts to Slack (or any webhook-compatible service) after each sync. Currently, all insights are pull-only — a team lead never sees alerts unless they open the dashboard. Swarmia's Slack nudges are their #1 competitive differentiator; this closes that gap with zero Slack-specific code.

## Deliverables

### backend/app/config.py (extend)
New env vars:
- `ALERT_WEBHOOK_URL` (String, default "") — webhook URL for alert dispatch (Slack incoming webhook format)
- `ALERT_WEBHOOK_ENABLED` (Boolean, default False)
- `ALERT_MIN_SEVERITY` (String, default "warning") — minimum severity to dispatch ("info", "warning", "critical")

### backend/app/services/notifications.py (new)
Async service for webhook dispatch:

```python
async def dispatch_alerts(alerts: list[WorkloadAlert], stale_prs: list[StalePR]) -> None:
```

Format alerts as Slack Block Kit messages:
- **Stale PR nudge**: "PR #{number} *{title}* has been waiting for review for {age}h — author: @{author}"
- **Workload alert**: "{developer} is {alert_type}: {message}"
- **Goal expiry**: "{developer}'s goal '{metric}' expires in {days} days and is off-track"

Use `httpx.AsyncClient` (already a project dependency) to POST to the webhook URL.

### backend/app/services/notifications.py — alert persistence
New table: `alert_events`
- `id` (Integer, PK)
- `alert_type` (String) — matches WorkloadAlert types
- `severity` (String) — info/warning/critical
- `developer_id` (Integer, FK, nullable)
- `message` (Text)
- `fired_at` (DateTime)
- `acknowledged_at` (DateTime, nullable)
- `acknowledged_by` (String, nullable)

Persist alerts on each sync. Only dispatch NEW alerts (not already in `alert_events` with same type+developer in the last 24h) to avoid spam.

### backend/app/main.py (extend)
In the APScheduler job that runs after each sync:
1. Compute workload alerts via `get_workload()`
2. Compute stale PRs via `get_stale_prs()`
3. Check for expiring goals
4. Call `dispatch_alerts()` with new alerts
5. Persist all alerts to `alert_events`

### backend/app/api/alerts.py (new)
- `GET /api/alerts` — list recent alert events with pagination
- `PATCH /api/alerts/{id}/acknowledge` — mark alert as acknowledged

### Frontend: Alert history
- Add alert history view accessible from Dashboard "Needs Attention" zone
- Show acknowledged vs unacknowledged alerts
- "Acknowledge" button per alert
