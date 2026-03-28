# Task P3-02: Sprint Model with Planned-vs-Actual Tracking

## Phase
Phase 3 — Make It Proactive

## Status
pending

## Blocked By
- 07-stats-service

## Blocks
None

## Description
Add a first-class Sprint entity so team leads can define named iterations with start/end dates and track planned-vs-actual delivery. Currently, the trends endpoint supports `period_type="sprint"` with configurable length, but there is no named sprint, no sprint-vs-sprint comparison, and no carry-over detection.

## Deliverables

### Database migration
New table: `sprints`
- `id` (Integer, PK)
- `name` (String, not null) — e.g., "Sprint 42"
- `team` (String, nullable) — team scope
- `start_date` (Date, not null)
- `end_date` (Date, not null)
- `created_at` (DateTime)

### backend/app/models/models.py (extend)
Add `Sprint` model to ORM.

### backend/app/schemas/schemas.py (extend)
```python
class SprintCreate(BaseModel):
    name: str
    team: str | None = None
    start_date: date
    end_date: date

class SprintStatsResponse(BaseModel):
    sprint: SprintCreate
    prs_opened: int
    prs_merged: int
    prs_carried_over: int  # opened before sprint, merged during
    prs_carried_forward: int  # opened during sprint, not yet merged
    issues_closed: int
    reviews_given: int
    avg_time_to_merge_hours: float | None
    avg_review_rounds: float | None
    developers_active: int
    velocity_vs_previous: float | None  # % change in prs_merged vs prior sprint
```

### backend/app/services/sprints.py (new)
- `create_sprint(session, sprint_data)` — create a sprint
- `get_sprints(session, team)` — list sprints
- `get_sprint_stats(session, sprint_id)` — compute stats for a sprint window
  - PRs opened: `created_at` within sprint window
  - PRs merged: `merged_at` within sprint window
  - Carried over: `created_at` before sprint start, `merged_at` within sprint
  - Carried forward: `created_at` within sprint, not yet merged or `merged_at` after sprint end
  - Auto-fetch previous sprint stats for velocity comparison

### backend/app/api/sprints.py (new)
- `POST /api/sprints` — create sprint
- `GET /api/sprints` — list sprints (optional `?team=` filter)
- `GET /api/sprints/{id}/stats` — sprint stats with comparison to previous sprint
- `DELETE /api/sprints/{id}` — delete sprint

### Frontend: Sprint view
- Add sprint management to the Insights section or as a sub-page
- Sprint list with stats summary per sprint
- Sprint detail: stat cards + comparison to previous sprint with delta indicators
- Sprint creation form: name, team, start date, end date
