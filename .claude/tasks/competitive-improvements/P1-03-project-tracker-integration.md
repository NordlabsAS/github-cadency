# P1-03: Project Tracker Integration (Jira / Linear)

> Priority: 1 (Table Stakes) | Effort: Large | Impact: High
> Competitive gap: LinearB, Jellyfish, Swarmia, DX, Sleuth all integrate with project trackers. DevPulse is GitHub-only.

## Context

Without project tracker integration, DevPulse cannot correlate engineering work to business initiatives, epics, or sprints. Jellyfish's entire value proposition is this alignment. Even basic sprint velocity and epic completion tracking are impossible without this data.

Current issue tracking is limited to GitHub Issues, which many teams don't use as their primary tracker.

## What to Build

### Phase 1: Jira Integration (highest market share)

**Data to sync from Jira:**
- Projects, boards, sprints (active + recent closed)
- Issues/stories/tasks/bugs with status, assignee, story points, epic link
- Sprint membership and completion data
- Issue-PR linkage (via Jira issue keys in PR titles/branches, e.g., `PROJ-123`)

**Metrics unlocked:**
- Sprint velocity (story points completed per sprint)
- Sprint completion rate (% of committed stories delivered)
- Epic cycle time (time from epic start to all stories done)
- Work alignment: % of PRs linked to tracked work vs. unplanned
- Planning accuracy: committed vs. delivered per sprint

### Phase 2: Linear Integration (growing adoption in startups)

Similar data model but via Linear's GraphQL API. Linear's data model maps more cleanly (cycles = sprints, projects = epics).

## Backend Changes

### New Models

**`integration_config` table:**
```
id, type ("jira" | "linear"), config (JSONB, encrypted sensitive fields),
status ("active" | "disabled" | "error"), last_synced_at,
created_at, updated_at
```

**`external_projects` table:**
```
id, integration_id (FK), external_id, key, name,
project_type ("project" | "board"), url
```

**`external_sprints` table:**
```
id, integration_id (FK), project_id (FK), external_id, name,
state ("active" | "closed" | "future"), start_date, end_date,
goal, committed_points, completed_points
```

**`external_issues` table:**
```
id, integration_id (FK), external_id, key, title,
issue_type ("story" | "task" | "bug" | "epic" | "subtask"),
status, status_category ("todo" | "in_progress" | "done"),
assignee_email, assignee_developer_id (FK, nullable),
story_points, epic_id (FK, nullable), sprint_id (FK, nullable),
priority, created_at, resolved_at, url
```

**`pr_external_issue_links` table:**
```
id, pull_request_id (FK), external_issue_id (FK),
link_source ("branch" | "title" | "body" | "commit")
```

### New Service: `backend/app/services/jira_sync.py`
- Jira Cloud REST API v3 client (OAuth 2.0 3LO or API token)
- `sync_jira_projects()` — fetch projects and boards
- `sync_jira_sprints(board_id)` — fetch sprints with velocity
- `sync_jira_issues(project_key)` — paginated issue fetch with changelog
- `link_prs_to_issues()` — regex match Jira keys in PR title/branch/body
- `compute_sprint_metrics()` — velocity, completion rate, carryover

### New Service: `backend/app/services/linear_sync.py`
- Linear GraphQL API client
- Similar structure to Jira sync but adapted for Linear's data model
- Cycles → sprints, Projects → epics mapping

### New Router: `backend/app/api/integrations.py`
- `POST /api/integrations` — configure new integration
- `GET /api/integrations` — list configured integrations
- `PATCH /api/integrations/{id}` — update config
- `DELETE /api/integrations/{id}` — remove integration
- `POST /api/integrations/{id}/sync` — trigger manual sync
- `GET /api/integrations/{id}/status` — sync status
- `POST /api/integrations/{id}/test` — test connection

### New Router: `backend/app/api/sprints.py`
- `GET /api/sprints` — list sprints with metrics
- `GET /api/sprints/{id}` — sprint detail with issues + PRs
- `GET /api/sprints/velocity` — velocity trend over last N sprints
- `GET /api/epics` — epics with progress and cycle time
- `GET /api/planning/accuracy` — committed vs delivered trends

### Config
- `JIRA_CLOUD_URL`, `JIRA_CLIENT_ID`, `JIRA_CLIENT_SECRET`
- `LINEAR_API_KEY`

### Integration with Existing Sync
- After GitHub sync, run `link_prs_to_issues()` to match PRs to external tracker issues
- Scheduled Jira/Linear sync on configurable interval (default: every 2 hours)

## Frontend Changes

### Integration Settings Page (`/admin/settings/integrations`)
- Add/configure/remove Jira or Linear integration
- Connection test + sync trigger
- Field mapping configuration
- Sync status and history

### Sprint Dashboard Page (`/insights/sprints`)
- Sprint selector (current + recent)
- Velocity chart (bar chart, points per sprint, trend line)
- Sprint completion card (committed vs. delivered)
- Sprint burndown/burnup chart
- Stories by status breakdown
- PR linkage rate (% of sprint work with associated PRs)

### Epic Tracking Page (`/insights/epics`)
- Epic list with progress bars (stories done / total)
- Epic cycle time metrics
- Epic → PR mapping

### Work Alignment Card (Dashboard + Executive Dashboard)
- % of PRs linked to tracked work
- Unplanned work ratio

### Types
- New interfaces for Sprint, ExternalIssue, EpicProgress, SprintVelocity, PlanningAccuracy

## Dependencies
- `jira` or `atlassian-python-api` for Jira REST client (or raw httpx)
- Linear GraphQL client (httpx + gql queries)

## Security Considerations
- Jira/Linear API tokens encrypted at rest
- Scoped permissions: read-only access to project data
- No writes back to Jira/Linear (read-only, consistent with DevPulse philosophy)

## Testing
- Unit test Jira key extraction regex (`PROJ-123` patterns)
- Unit test sprint metric computation (velocity, completion rate)
- Unit test PR-to-issue linking logic
- Mock Jira/Linear API responses for integration tests
- Test OAuth flow for Jira Cloud

## Acceptance Criteria
- [ ] Jira Cloud OAuth connection flow works
- [ ] Projects, sprints, and issues sync from Jira
- [ ] PRs auto-linked to Jira issues via key matching
- [ ] Sprint velocity chart with trend
- [ ] Sprint completion rate (committed vs. delivered)
- [ ] Epic progress tracking
- [ ] Work alignment metric (linked vs. unlinked PRs)
- [ ] Integration settings page (admin only)
- [ ] Read-only — never writes to Jira/Linear
