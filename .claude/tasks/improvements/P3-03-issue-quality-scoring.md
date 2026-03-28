# Task P3-03: Issue Quality Scoring

## Phase
Phase 3 — Make It Proactive

## Status
pending

## Blocked By
- P2-04-issue-pr-linkage

## Blocks
- P3-04-issue-creator-analytics

## Description
Add quality signals to issues so DevPulse can identify poorly-defined tasks that cause friction for developers. This captures data that is already available in the GitHub API response but never stored, and adds simple analysis of existing issue body content.

## Deliverables

### Database migration
Add columns to `issues`:
- `comment_count` (Integer, default 0) — from `comments` key in GitHub API response (already returned, never stored)
- `body_length` (Integer, default 0) — character count of issue body
- `has_checklist` (Boolean, default False) — True if body contains `- [ ]` or `- [x]` patterns
- `state_reason` (String(30), nullable) — `"completed"`, `"not_planned"`, or `"reopened"` from GitHub API
- `creator_github_username` (String(255), nullable) — from `issue_data.get("user", {}).get("login")`
- `milestone_title` (String(255), nullable) — from `issue_data.get("milestone", {}).get("title")`
- `milestone_due_on` (Date, nullable) — from milestone data
- `reopen_count` (Integer, default 0) — incremented when state transitions from closed to open during sync

### backend/app/services/github_sync.py (extend)
In `upsert_issue()`, extract new fields from the already-fetched API response:
```python
comment_count = issue_data.get("comments", 0)
body = issue_data.get("body") or ""
body_length = len(body)
has_checklist = bool(re.search(r'- \[[ x]\]', body))
state_reason = issue_data.get("state_reason")
creator_github_username = issue_data.get("user", {}).get("login")
milestone = issue_data.get("milestone") or {}
milestone_title = milestone.get("title")
milestone_due_on = milestone.get("due_on")  # parse ISO date
```

For `reopen_count`: compare incoming `state` with stored state. If stored is "closed" and incoming is "open", increment `reopen_count`.

### backend/app/services/stats.py (extend)
New function: `async def get_issue_quality_stats(session, date_from, date_to, team)`

Returns:
- `total_issues_created` — in period
- `avg_body_length` — average issue body length
- `pct_with_checklist` — percentage of issues with acceptance criteria checklists
- `avg_comment_count` — average comments per issue
- `pct_closed_not_planned` — issues closed as "won't fix" / total closed
- `avg_reopen_count` — average reopens per issue
- `issues_without_body` — count of issues with empty or <50 char body
- Label distribution: `{"bug": 12, "feature": 8, "tech-debt": 3, ...}`

### backend/app/api/stats.py (extend)
New routes:
- `GET /api/stats/issues/quality` — returns `IssueQualityStats`
- `GET /api/stats/issues/labels` — returns label distribution

### backend/app/schemas/schemas.py (extend)
```python
class IssueQualityStats(BaseModel):
    total_issues_created: int
    avg_body_length: float
    pct_with_checklist: float
    avg_comment_count: float
    pct_closed_not_planned: float
    avg_reopen_count: float
    issues_without_body: int
    label_distribution: dict[str, int]
```
