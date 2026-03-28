# Task P3-04: Issue Creator Analytics (Management Friction Feedback)

## Phase
Phase 3 — Make It Proactive

## Status
pending

## Blocked By
- P3-03-issue-quality-scoring
- P2-04-issue-pr-linkage

## Blocks
None

## Description
Add per-creator issue quality analytics so team leads and managers can see how well their task definitions serve developers. This is a **unique differentiator** — no competitor helps management see when their own process is causing friction. "Issues you create without checklists take 2.3x longer to close."

## Deliverables

### backend/app/services/stats.py (extend)
New function: `async def get_issue_creator_stats(session, github_username, date_from, date_to)`

Returns per-creator aggregates:
- `issues_created` — total issues created by this person
- `avg_time_to_close_hours` — average close time for their issues
- `avg_comment_count_before_pr` — average comments on their issues before the first linked PR was opened (requires P2-04 issue-PR linkage)
- `pct_with_checklist` — percentage of their issues with acceptance criteria
- `pct_reopened` — percentage of their issues that were reopened at least once
- `pct_closed_not_planned` — percentage closed as "won't fix"
- `avg_prs_per_issue` — average number of PRs linked to each of their issues (>1 suggests scope too large)
- `issues_with_body_under_100_chars` — poorly described issues
- `avg_time_to_first_pr_hours` — average time from issue creation to first linked PR (long = unclear requirements)

### backend/app/api/stats.py (extend)
New route: `GET /api/stats/issues/creator/{github_username}`
- Query params: `date_from`, `date_to`
- Returns `IssueCreatorStats`

### backend/app/schemas/schemas.py (extend)
```python
class IssueCreatorStats(BaseModel):
    github_username: str
    issues_created: int
    avg_time_to_close_hours: float | None
    avg_comment_count_before_pr: float | None
    pct_with_checklist: float
    pct_reopened: float
    pct_closed_not_planned: float
    avg_prs_per_issue: float | None
    issues_with_body_under_100_chars: int
    avg_time_to_first_pr_hours: float | None
```

### AI integration
Extend `POST /api/ai/one-on-one-prep` context:
- If the developer being prepped has created issues (is a team lead), include their issue creator stats
- Claude can then surface patterns like: "Issues you create without checklists take 2.3x longer to close" or "30% of your issues are reopened vs 10% team average"

### Frontend
- Add an "Issue Quality" section to the Insights area
- Show per-creator stats as a table: one row per issue creator with key quality metrics
- Highlight creators whose metrics are significantly worse than average (red badges)
