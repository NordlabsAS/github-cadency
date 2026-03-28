# DevPulse API Reference

Base URL: `http://localhost:8000/api`

## Authentication

DevPulse uses GitHub OAuth for authentication. After login, all protected endpoints require a JWT:
```
Authorization: Bearer {jwt_token}
```

**Two roles:**
- `admin` — full access to all endpoints
- `developer` — read-only access to own stats, profile, goals, and repo stats

**Public endpoints** (no auth required): `GET /api/health`, `POST /api/webhooks/github`, `GET /api/auth/login`, `GET /api/auth/callback`

### Access Control Summary

| Endpoint Group | Admin | Developer |
|----------------|-------|-----------|
| **Auth** (`/api/auth/*`) | Public | Public |
| **Developer stats** (`/api/stats/developer/{id}`) | Any ID | Own ID only |
| **Team/benchmarks/workload/collaboration/stale-prs/issue-linkage** | Yes | No (403) |
| **Repo stats** (`/api/stats/repo/{id}`) | Yes | Yes |
| **Developers CRUD** (`/api/developers/*`) | Full access | GET own profile only |
| **Goals** (`/api/goals/*`) | Full access | GET own goals, POST/PATCH self-goals |
| **Sync** (`/api/sync/*`) | Yes | No (403) |
| **AI Analysis** (`/api/ai/*`) | Yes | No (403) |

Date parameters accept ISO 8601 format: `2026-01-01T00:00:00Z`. When `date_from`/`date_to` are omitted, defaults to the last 30 days.

---

## Auth

### GET /api/auth/login

Returns the GitHub OAuth authorization URL. The frontend should redirect the user to this URL.

**Response:** `200 OK`
```json
{
  "url": "https://github.com/login/oauth/authorize?client_id=...&redirect_uri=...&scope=read:user"
}
```

### GET /api/auth/callback?code={code}

OAuth callback. Exchanges the GitHub authorization code for an access token, fetches user profile, creates or updates the developer record, and issues a JWT.

**Behavior:**
- New user → creates developer record (`app_role: "developer"`, or `"admin"` if username matches `DEVPULSE_INITIAL_ADMIN`)
- Existing user → updates `avatar_url`
- Deactivated user → returns `403 Forbidden`

**Response:** `302 Redirect` to `{FRONTEND_URL}/auth/callback?token={jwt}`

### GET /api/auth/me

Returns the currently authenticated user's info.

**Response:** `200 OK`
```json
{
  "developer_id": 1,
  "github_username": "octocat",
  "display_name": "Octo Cat",
  "app_role": "admin",
  "avatar_url": "https://avatars.githubusercontent.com/u/583231"
}
```

---

## Health

### GET /api/health

Returns service status. No authentication required.

**Response:** `200 OK`
```json
{ "status": "ok" }
```

---

## Developers

Team registry CRUD. Developers are the core entity linking GitHub usernames to internal profiles.

**Access:** Admin-only for list, create, update, delete. Developers can GET their own profile.

**DeveloperResponse** includes `app_role` field (`"admin"` or `"developer"`).

### GET /api/developers

List developers. **Admin only.**

| Query Param | Type | Default | Description |
|-------------|------|---------|-------------|
| `team` | string | - | Filter by team name |
| `is_active` | bool | `true` | Filter by active status |

**Response:** `200 OK` — `DeveloperResponse[]` ordered by `display_name`

### POST /api/developers

Create a developer. **Admin only.**

**Request Body:**
```json
{
  "github_username": "octocat",
  "display_name": "Octo Cat",
  "email": "octo@example.com",
  "role": "developer",
  "skills": ["python", "react"],
  "specialty": "backend",
  "location": "San Francisco",
  "timezone": "America/Los_Angeles",
  "team": "Platform",
  "notes": "Started Q1 2026"
}
```

`role` values: `developer`, `senior_developer`, `lead`, `architect`, `devops`, `qa`, `intern`

**Response:** `201 Created` — `DeveloperResponse`
**Errors:** `409 Conflict` if `github_username` already exists

### GET /api/developers/{developer_id}

**Access:** Admin can view any developer. Developers can view their own profile only.

**Response:** `200 OK` — `DeveloperResponse`
**Errors:** `404 Not Found`, `403 Forbidden` (developer accessing another profile)

### PATCH /api/developers/{developer_id}

Partial update. Only provided fields are changed. **Admin only.**

**Request Body:** Any subset of `DeveloperCreate` fields (except `github_username`), plus:
- `app_role`: `"admin"` or `"developer"` — promotes or demotes a user

**Response:** `200 OK` — `DeveloperResponse`

### DELETE /api/developers/{developer_id}

Soft-delete: sets `is_active = false`. **Admin only.** Deactivated developers cannot log in via OAuth.

**Response:** `204 No Content`

---

## Stats

All stats endpoints accept optional `date_from` and `date_to` query parameters.

### GET /api/stats/developer/{developer_id}

Developer metrics for a date range. **Developers can only access their own stats.**

| Query Param | Type | Default | Description |
|-------------|------|---------|-------------|
| `date_from` | datetime | 30 days ago | Period start |
| `date_to` | datetime | now | Period end |
| `include_percentiles` | bool | `false` | Include team-relative percentile placement |

**Response:** `200 OK`
```json
{
  "prs_opened": 12,
  "prs_merged": 10,
  "prs_closed_without_merge": 1,
  "prs_open": 3,
  "prs_draft": 1,
  "total_additions": 2450,
  "total_deletions": 890,
  "total_changed_files": 45,
  "reviews_given": {
    "approved": 8,
    "changes_requested": 3,
    "commented": 5
  },
  "reviews_received": 15,
  "review_quality_breakdown": {
    "rubber_stamp": 2,
    "minimal": 3,
    "standard": 6,
    "thorough": 5
  },
  "review_quality_score": 6.25,
  "avg_time_to_first_review_hours": 4.2,
  "avg_time_to_merge_hours": 18.5,
  "issues_assigned": 5,
  "issues_closed": 3,
  "avg_time_to_close_issue_hours": 48.0
}
```

When `include_percentiles=true`, adds:
```json
{
  "percentiles": {
    "time_to_merge_h": {
      "value": 18.5,
      "percentile_band": "p50_to_p75",
      "team_median": 22.0
    },
    "prs_merged": {
      "value": 10.0,
      "percentile_band": "above_p75",
      "team_median": 7.0
    }
  }
}
```

Percentile bands: `below_p25`, `p25_to_p50`, `p50_to_p75`, `above_p75`. For lower-is-better metrics (time_to_merge_h, time_to_first_review_h, review_turnaround_h), bands are inverted so `above_p75` always means "best performer."

### GET /api/stats/team

Team-wide aggregate metrics. **Admin only.**

| Query Param | Type | Default | Description |
|-------------|------|---------|-------------|
| `team` | string | - | Filter by team name (all active devs if omitted) |

**Response:** `200 OK`
```json
{
  "developer_count": 12,
  "total_prs": 85,
  "total_merged": 72,
  "merge_rate": 84.7,
  "avg_time_to_first_review_hours": 3.8,
  "avg_time_to_merge_hours": 16.2,
  "total_reviews": 210,
  "total_issues_closed": 34
}
```

### GET /api/stats/repo/{repo_id}

Repository-scoped metrics with top contributors.

**Response:** `200 OK`
```json
{
  "total_prs": 45,
  "total_merged": 38,
  "total_issues": 22,
  "total_issues_closed": 18,
  "total_reviews": 95,
  "avg_time_to_merge_hours": 14.3,
  "top_contributors": [
    { "developer_id": 1, "github_username": "octocat", "display_name": "Octo Cat", "pr_count": 12 }
  ]
}
```

### GET /api/stats/benchmarks

Team percentile bands (p25/p50/p75) across all active developers. **Admin only.**

| Query Param | Type | Default | Description |
|-------------|------|---------|-------------|
| `team` | string | - | Filter by team |

**Response:** `200 OK`
```json
{
  "period_start": "2026-02-26T00:00:00Z",
  "period_end": "2026-03-28T00:00:00Z",
  "sample_size": 15,
  "team": null,
  "metrics": {
    "time_to_merge_h": { "p25": 8.5, "p50": 16.2, "p75": 28.0 },
    "time_to_first_review_h": { "p25": 1.2, "p50": 3.8, "p75": 8.5 },
    "prs_merged": { "p25": 3.0, "p50": 7.0, "p75": 12.0 },
    "review_turnaround_h": { "p25": 2.0, "p50": 5.5, "p75": 12.0 },
    "reviews_given": { "p25": 4.0, "p50": 10.0, "p75": 18.0 },
    "additions_per_pr": { "p25": 50.0, "p50": 150.0, "p75": 400.0 }
  }
}
```

### GET /api/stats/developer/{developer_id}/trends

Period-bucketed stats with linear regression trend analysis. **Developers can only access their own trends.**

| Query Param | Type | Default | Description |
|-------------|------|---------|-------------|
| `periods` | int (2-52) | `8` | Number of time buckets |
| `period_type` | string | `week` | `week`, `sprint`, or `month` |
| `sprint_length_days` | int (7-28) | `14` | Only used when `period_type=sprint` |

**Response:** `200 OK`
```json
{
  "developer_id": 1,
  "period_type": "week",
  "periods": [
    {
      "start": "2026-02-05T00:00:00Z",
      "end": "2026-02-12T00:00:00Z",
      "prs_merged": 3,
      "avg_time_to_merge_h": 12.5,
      "reviews_given": 5,
      "additions": 450,
      "deletions": 120,
      "issues_closed": 1
    }
  ],
  "trends": {
    "prs_merged": { "direction": "improving", "change_pct": 15.2 },
    "avg_time_to_merge_h": { "direction": "stable", "change_pct": -2.1 },
    "reviews_given": { "direction": "worsening", "change_pct": -22.0 }
  }
}
```

Direction respects metric polarity: decreasing `avg_time_to_merge_h` = "improving". Change < 5% = "stable". Neutral metrics (additions, deletions) always show "stable."

### GET /api/stats/collaboration

Reviewer-author collaboration matrix with team insights. **Admin only.**

| Query Param | Type | Default | Description |
|-------------|------|---------|-------------|
| `team` | string | - | Filter by team |

**Response:** `200 OK`
```json
{
  "matrix": [
    {
      "reviewer_id": 1, "reviewer_name": "Alice", "reviewer_team": "Platform",
      "author_id": 2, "author_name": "Bob", "author_team": "Platform",
      "reviews_count": 12, "approvals": 8, "changes_requested": 4
    }
  ],
  "insights": {
    "silos": [
      { "team_a": "Platform", "team_b": "Mobile", "note": "Zero cross-team reviews" }
    ],
    "bus_factors": [
      { "repo_name": "org/core-api", "sole_reviewer_id": 1, "sole_reviewer_name": "Alice", "review_share_pct": 78.5 }
    ],
    "isolated_developers": [
      { "developer_id": 5, "display_name": "Charlie" }
    ],
    "strongest_pairs": []
  }
}
```

Insights:
- **Silos:** Team pairs with zero cross-team reviews (excludes devs with no team set)
- **Bus factors:** Reviewers with >70% of all reviews on a repo in the date range
- **Isolated:** Developers with 0 reviews given AND reviews received from <= 1 unique reviewer
- **Strongest pairs:** Top 10 mutual review pairs by combined review count

### GET /api/stats/workload

Per-developer workload indicators and automated alerts. **Admin only.**

| Query Param | Type | Default | Description |
|-------------|------|---------|-------------|
| `team` | string | - | Filter by team |

**Response:** `200 OK`
```json
{
  "developers": [
    {
      "developer_id": 1,
      "github_username": "octocat",
      "display_name": "Octo Cat",
      "open_prs_authored": 3,
      "drafts_open": 1,
      "open_prs_reviewing": 2,
      "open_issues_assigned": 1,
      "reviews_given_this_period": 8,
      "reviews_received_this_period": 5,
      "prs_waiting_for_review": 1,
      "avg_review_wait_h": 6.5,
      "workload_score": "balanced"
    }
  ],
  "alerts": [
    { "type": "review_bottleneck", "developer_id": 3, "message": "Alice gave 25 reviews (team median: 10)" },
    { "type": "stale_prs", "developer_id": 2, "message": "PR #42 (Fix auth) waiting for review > 48h" },
    { "type": "uneven_assignment", "developer_id": null, "message": "Top 2 dev(s) hold 15/20 open issues" },
    { "type": "underutilized", "developer_id": 5, "message": "Charlie has 0 PRs and 0 reviews in the period" }
  ]
}
```

Workload scores: `low` (no activity), `balanced` (<= 5 total load), `high` (<= 12), `overloaded` (> 12). Total load = open PRs authored + reviewing + open issues + reviews given.

### GET /api/stats/stale-prs

Open PRs that need attention, sorted by staleness (most stale first). **Admin only.**

| Query Param | Type | Default | Description |
|-------------|------|---------|-------------|
| `team` | string | - | Filter by team (PRs authored by team members) |
| `threshold_hours` | int (1-720) | `24` | Minimum age in hours before a PR is considered stale |

**Three staleness categories:**
1. **`no_review`** — open, non-draft, no first review received, older than threshold
2. **`changes_requested_no_response`** — most recent review is `CHANGES_REQUESTED`, author hasn't updated the PR since (within 1h tolerance), review older than threshold
3. **`approved_not_merged`** — has at least one `APPROVED` review, last approval older than threshold, still not merged

PRs are deduplicated across categories (priority: no_review > changes_requested > approved_not_merged).

**Response:** `200 OK`
```json
{
  "stale_prs": [
    {
      "pr_id": 42,
      "number": 123,
      "title": "Fix authentication middleware",
      "html_url": "https://github.com/org/repo/pull/123",
      "repo_name": "org/repo",
      "author_name": "Alice",
      "author_id": 1,
      "age_hours": 72.5,
      "is_draft": false,
      "review_count": 0,
      "has_approved": false,
      "has_changes_requested": false,
      "last_activity_at": "2026-03-25T10:00:00Z",
      "stale_reason": "no_review"
    },
    {
      "pr_id": 55,
      "number": 145,
      "title": "Update caching layer",
      "html_url": "https://github.com/org/repo/pull/145",
      "repo_name": "org/repo",
      "author_name": "Bob",
      "author_id": 2,
      "age_hours": 48.2,
      "is_draft": false,
      "review_count": 1,
      "has_approved": true,
      "has_changes_requested": false,
      "last_activity_at": "2026-03-26T08:30:00Z",
      "stale_reason": "approved_not_merged"
    }
  ],
  "total_count": 2
}
```

---

### GET /api/stats/issue-linkage

Issue-to-PR linkage statistics via closing keywords parsed from PR bodies. Shows how well issues are connected to the PRs that resolved them. **Admin only.**

| Query Param | Type | Default | Description |
|-------------|------|---------|-------------|
| `date_from` | datetime | 30 days ago | Start of date range (ISO 8601) |
| `date_to` | datetime | now | End of date range (ISO 8601) |
| `team` | string | - | Filter by team (PRs by author team, issues by assignee team) |

**Closing keywords recognized:** `close`, `closes`, `closed`, `fix`, `fixes`, `fixed`, `resolve`, `resolves`, `resolved` — case-insensitive, followed by `#N` where N is an issue number in the same repo.

**Response:** `200 OK`
```json
{
  "issues_with_linked_prs": 15,
  "issues_without_linked_prs": 3,
  "avg_prs_per_issue": 1.2,
  "issues_with_multiple_prs": 2,
  "prs_without_linked_issues": 8
}
```

| Field | Description |
|-------|-------------|
| `issues_with_linked_prs` | Closed issues referenced by at least one PR's closing keywords |
| `issues_without_linked_prs` | Closed issues with no PR referencing them (work outside PR process) |
| `avg_prs_per_issue` | Average PRs per linked issue (`null` if no linked issues) |
| `issues_with_multiple_prs` | Issues linked to 2+ PRs (may indicate scope was too large) |
| `prs_without_linked_issues` | PRs in the date range that don't reference any issue (undocumented work) |

---

## Developer Goals

**Access:** Admin has full CRUD. Developers can view their own goals, create self-goals via `/goals/self`, and update their own self-created goals.

### POST /api/goals

Create a goal for a developer. Baseline value is auto-computed from the current 30-day window. **Admin only.**

**Request Body:**
```json
{
  "developer_id": 1,
  "title": "Reduce avg PR size",
  "description": "Target smaller, more focused PRs",
  "metric_key": "avg_pr_additions",
  "target_value": 200,
  "target_direction": "below",
  "target_date": "2026-06-01"
}
```

`metric_key` values: `avg_pr_additions`, `time_to_merge_h`, `reviews_given`, `review_quality_score`, `prs_merged`, `time_to_first_review_h`, `issues_closed`, `prs_opened`

`target_direction`: `"above"` (metric should be >= target) or `"below"` (metric should be <= target)

**Response:** `201 Created` — `GoalResponse`

### GET /api/goals?developer_id={id}

List all goals for a developer, ordered by creation date (newest first). **Developers can only list their own goals.**

**Response:** `200 OK` — `GoalResponse[]`
**Errors:** `403 Forbidden` (developer accessing another developer's goals)

### PATCH /api/goals/{goal_id}

Update goal status or notes. **Admin only.**

**Request Body:**
```json
{
  "status": "achieved",
  "notes": "Consistently under 200 additions since Feb"
}
```

`status` values: `active`, `achieved`, `abandoned`

**Response:** `200 OK` — `GoalResponse`

### POST /api/goals/self

Create a goal for the authenticated developer. `developer_id` is derived from the JWT token. Baseline value is auto-computed from the current 30-day window. The goal is marked `created_by: "self"`. **Any authenticated user.**

**Request Body:**
```json
{
  "title": "Ship more PRs",
  "description": "Focus on smaller, frequent merges",
  "metric_key": "prs_merged",
  "target_value": 12,
  "target_direction": "above",
  "target_date": "2026-06-01"
}
```

Only `title`, `metric_key`, and `target_value` are required. No `developer_id` field — it is set from the token.

**Response:** `200 OK` — `GoalResponse` (with `created_by: "self"`)

### PATCH /api/goals/self/{goal_id}

Update a self-created goal. Developers can only update goals they created themselves (`created_by: "self"`). Admin-created goals return `403`. **Any authenticated user (own goals only).**

**Request Body:**
```json
{
  "target_value": 15,
  "target_date": "2026-07-01",
  "status": "achieved",
  "notes": "Consistently hitting target"
}
```

All fields are optional. `status` values: `active`, `achieved`, `abandoned`.

**Response:** `200 OK` — `GoalResponse`
**Errors:** `403 Forbidden` (goal belongs to another developer, or goal was admin-created), `404 Not Found`

### GET /api/goals/{goal_id}/progress

Get goal progress with 8-week history. Triggers auto-achievement check: if the metric crosses the target for 2 consecutive weekly periods, the goal is automatically marked as achieved. **Developers can only view their own goals' progress.**

**Response:** `200 OK`
```json
{
  "goal_id": 1,
  "title": "Reduce avg PR size",
  "target_value": 200,
  "target_direction": "below",
  "baseline_value": 350.0,
  "current_value": 180.5,
  "status": "achieved",
  "history": [
    { "period_end": "2026-02-07T00:00:00Z", "value": 320.0 },
    { "period_end": "2026-02-14T00:00:00Z", "value": 280.0 },
    { "period_end": "2026-03-28T00:00:00Z", "value": 180.5 }
  ]
}
```

---

## Sync

**All sync endpoints are admin only.**

### POST /api/sync/full

Trigger a full sync (all tracked repos, all data). Runs as a background task.

**Response:** `202 Accepted`
```json
{ "status": "accepted", "sync_type": "full" }
```

### POST /api/sync/incremental

Trigger an incremental sync (changes since last sync per repo).

**Response:** `202 Accepted`

### GET /api/sync/repos

List all repositories discovered from the GitHub organization.

**Response:** `200 OK` — `RepoResponse[]`

### PATCH /api/sync/repos/{repo_id}/track

Enable or disable tracking for a repository.

**Request Body:**
```json
{ "is_tracked": true }
```

**Response:** `200 OK` — `RepoResponse`

### GET /api/sync/events

List recent sync events.

| Query Param | Type | Default | Description |
|-------------|------|---------|-------------|
| `limit` | int (1-200) | `50` | Max events to return |

**Response:** `200 OK` — `SyncEventResponse[]` ordered by `started_at` desc

---

## Webhooks

### POST /api/webhooks/github

GitHub webhook receiver. No Bearer auth — uses HMAC signature verification.

**Required Headers:**
- `X-Hub-Signature-256`: HMAC-SHA256 signature of body
- `X-GitHub-Event`: Event type (`pull_request`, `pull_request_review`, `pull_request_review_comment`, `issues`, `issue_comment`)

**Response:** `200 OK` — `{ "status": "ok" }`
**Errors:** `401 Unauthorized` on invalid signature

---

## AI Analysis

**All AI endpoints are admin only.** AI features require `ANTHROPIC_API_KEY` to be set. All analysis calls are synchronous (wait for Claude response). Results are persisted in `ai_analyses` table.

### POST /api/ai/analyze

Run a standard AI analysis (communication, conflict, or sentiment).

**Request Body:**
```json
{
  "analysis_type": "communication",
  "scope_type": "developer",
  "scope_id": "1",
  "date_from": "2026-02-01T00:00:00Z",
  "date_to": "2026-03-01T00:00:00Z"
}
```

`analysis_type`: `communication`, `conflict`, `sentiment`
`scope_type`: `developer`, `team`, `repo`
`scope_id`: developer ID (string), team name, or repo ID (string)

**Response:** `201 Created` — `AIAnalysisResponse` with structured JSON in `result` field

### POST /api/ai/one-on-one-prep

Generate a structured 1:1 meeting prep brief for a developer.

**Request Body:**
```json
{
  "developer_id": 1,
  "date_from": "2026-02-01T00:00:00Z",
  "date_to": "2026-03-01T00:00:00Z"
}
```

**Context gathered:** developer stats, 4-period trends, team benchmarks, PR list, review quality tiers, active goals with progress, previous 1:1 brief (for continuity).

**Response:** `201 Created` — `AIAnalysisResponse` where `result` contains:
```json
{
  "period_summary": "...",
  "metrics_highlights": [
    { "metric": "prs_merged", "value": "10", "context": "Above team median of 7", "concern_level": "none" }
  ],
  "notable_work": ["Led the auth middleware rewrite"],
  "suggested_talking_points": [
    {
      "topic": "Review volume",
      "framing": "I've noticed you've been doing a lot of reviews lately. How are you feeling about the review load?",
      "evidence": "25 reviews given, 2.5x team median"
    }
  ],
  "goal_progress": [
    { "title": "Reduce avg PR size", "status": "active", "current_value": "185" }
  ]
}
```

### POST /api/ai/team-health

Generate a comprehensive team health assessment.

**Request Body:**
```json
{
  "team": "Platform",
  "date_from": "2026-02-01T00:00:00Z",
  "date_to": "2026-03-01T00:00:00Z"
}
```

`team` is optional — omit for all active developers.

**Context gathered:** team stats + benchmarks, workload balance + alerts, collaboration matrix + insights, CHANGES_REQUESTED reviews with body text + metadata (up to 60), heated issue threads with full chronological dialogue (3+ comments between 2 tracked devs), active team goals with current values.

**Response:** `201 Created` — `AIAnalysisResponse` where `result` contains:
```json
{
  "overall_health_score": 7,
  "velocity_assessment": "Team is shipping at a sustainable pace...",
  "workload_concerns": [
    { "concern": "Alice is reviewing 2.5x the team median", "suggestion": "Rotate review assignments" }
  ],
  "collaboration_patterns": "Strong intra-team reviews but zero cross-team with Mobile...",
  "communication_flags": [
    { "severity": "medium", "observation": "Recurring terse CHANGES_REQUESTED reviews between Bob and Charlie" }
  ],
  "process_recommendations": ["Implement round-robin review assignment"],
  "strengths": ["Fast time-to-first-review (median 3.8h)", "High merge rate (85%)"],
  "action_items": [
    { "priority": "high", "action": "Address review bottleneck on core-api repo", "owner": "lead" }
  ]
}
```

### GET /api/ai/history

List past analysis results.

| Query Param | Type | Description |
|-------------|------|-------------|
| `analysis_type` | string | Filter: `communication`, `conflict`, `sentiment`, `one_on_one_prep`, `team_health` |
| `scope_type` | string | Filter: `developer`, `team`, `repo` |

**Response:** `200 OK` — `AIAnalysisResponse[]` (last 50, newest first)

### GET /api/ai/history/{analysis_id}

Get a specific analysis result.

**Response:** `200 OK` — `AIAnalysisResponse`
