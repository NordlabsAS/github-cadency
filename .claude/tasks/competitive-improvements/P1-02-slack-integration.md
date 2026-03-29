# P1-02: Slack Integration for Alerts and PR Nudges

> Priority: 1 (Table Stakes) | Effort: Large | Impact: High
> Competitive gap: All major competitors have Slack integration. DevPulse alerts only visible when someone opens the dashboard.

## Context

DevPulse currently has no notification system. Alerts (stale PRs, workload imbalance, sync failures, high-risk PRs) are only visible when someone actively opens the dashboard. Swarmia's Slack-first workflow is a core differentiator in the market.

The competitive analysis notes this is a key operationalization gap: "DevPulse shows you the data but doesn't help you act on it."

## What to Build

### Phase 1: Slack App + Webhook Notifications

**Slack App setup:**
- DevPulse registers as a Slack App (self-hosted teams create their own Slack App)
- OAuth 2.0 flow to connect Slack workspace
- Store bot token + channel mappings in DB

**Notification types (configurable per-channel):**

| Alert | Trigger | Default Channel |
|-------|---------|----------------|
| Stale PR nudge | PR open > N days (configurable, default 3) | #engineering |
| High-risk PR | Risk score > 0.7 on new PR | #engineering |
| Workload alert | Developer moves to "overloaded" status | #eng-leads |
| Sync failure | Sync completes with errors or fails | #devpulse-admin |
| Sync complete | Successful sync summary | #devpulse-admin |
| Weekly digest | Scheduled summary of key metrics | #engineering |

### Phase 2: Interactive Messages

- Stale PR notifications include "View PR" button (links to GitHub) and "Snooze" button
- Workload alerts include "View Dashboard" link
- Weekly digest includes sparkline-style metric summaries

## Backend Changes

### New Model: `slack_config` table
```
id, workspace_id, team_name, bot_token (encrypted),
default_channel_id, channel_mappings (JSONB),
notification_settings (JSONB), installed_at, installed_by
```

### New Model: `notification_log` table
```
id, type, channel_id, message_ts, payload (JSONB),
sent_at, developer_id (nullable)
```

### New Service: `backend/app/services/slack.py`
- `send_notification(type, payload, channel_override=None)`
- `send_stale_pr_nudge(pr, channel)`
- `send_risk_alert(pr, risk_score, channel)`
- `send_workload_alert(developer, score, channel)`
- `send_sync_summary(sync_event, channel)`
- `send_weekly_digest(channel)`
- Rate limiting: max 1 notification per PR per type per 24h (prevent spam)

### New Router: `backend/app/api/slack.py`
- `POST /api/slack/install` — initiate Slack OAuth
- `GET /api/slack/callback` — OAuth callback, store tokens
- `GET /api/slack/config` — get current config (admin only)
- `PATCH /api/slack/config` — update channel mappings, notification settings
- `POST /api/slack/test` — send test notification
- `DELETE /api/slack/disconnect` — remove integration

### Config (`backend/app/config.py`)
- `SLACK_CLIENT_ID`, `SLACK_CLIENT_SECRET`, `SLACK_SIGNING_SECRET`
- `SLACK_ENCRYPTION_KEY` — for encrypting bot tokens at rest

### Integration Points
- After sync completes: trigger sync summary notification
- Scheduled job (daily): check for stale PRs → send nudges
- Scheduled job (weekly): compute digest → send summary
- On webhook PR event: if risk score > threshold → send alert
- On stats recompute: if workload transitions to overloaded → send alert

## Frontend Changes

### Slack Settings Page (`/admin/settings/slack`)
- Connection status + install/disconnect buttons
- Channel mapping UI (dropdown per notification type)
- Per-notification toggle (enable/disable each type)
- Threshold configuration (stale PR days, risk score threshold)
- Test notification button
- Notification history log

### Nav Update
- Add "Integrations" or "Notifications" to Admin sidebar

## Dependencies
- `slack_sdk` Python package for Slack API
- `cryptography` for token encryption at rest

## Security Considerations
- Bot tokens encrypted at rest using Fernet symmetric encryption
- Slack signing secret verification on all incoming Slack requests
- Admin-only access to Slack configuration
- No sensitive data (code, PR content) in notifications — only metadata and links

## Testing
- Unit test notification formatting for each type
- Unit test rate limiting (no duplicate notifications)
- Unit test channel routing logic
- Mock Slack API for integration tests
- Test OAuth flow with mock Slack endpoints

## Acceptance Criteria
- [ ] Slack App OAuth flow works (install/disconnect)
- [ ] Stale PR nudges sent daily for PRs exceeding threshold
- [ ] High-risk PR alerts on new PRs above risk threshold
- [ ] Workload alerts when developers become overloaded
- [ ] Sync status notifications (success/failure)
- [ ] Weekly digest with key metric summaries
- [ ] Per-notification-type channel routing and enable/disable
- [ ] Rate limiting prevents notification spam
- [ ] Admin-only configuration page
- [ ] Bot tokens encrypted at rest
