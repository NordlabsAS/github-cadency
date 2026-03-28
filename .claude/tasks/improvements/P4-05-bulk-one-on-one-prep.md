# Task P4-05: Bulk 1:1 Prep Generation

## Phase
Phase 4 — Make It Best-in-Class

## Status
pending

## Blocked By
- M7-one-on-one-prep-brief
- P1-04-structured-ai-rendering

## Blocks
None

## Description
Allow team leads to generate 1:1 prep briefs for all their reports in a single operation, sorted by concern level. Currently, running a 1:1 brief requires selecting one developer at a time — a team lead with 10 reports must trigger 10 separate analyses and manually compare them.

## Deliverables

### backend/app/api/ai_analysis.py (extend)
New endpoint: `POST /api/ai/bulk-one-on-one-prep`

Request body:
```python
class BulkOneOnOnePrepRequest(BaseModel):
    developer_ids: list[int]  # or team: str to prep all developers on a team
    date_from: date | None = None
    date_to: date | None = None
```

Response: list of 1:1 prep results sorted by concern level (highest first)

Implementation:
- Run all developer briefs concurrently using `asyncio.gather`
- Each brief reuses the existing `generate_one_on_one_prep()` service function
- After all complete, sort by a derived concern score:
  - Count of "concern" or "warning" level items in `metrics_highlights`
  - Presence of declining trends
  - Off-track goals
- Return sorted list with concern_score as a new field

### backend/app/schemas/schemas.py (extend)
```python
class BulkOneOnOnePrepResponse(BaseModel):
    briefs: list[OneOnOnePrepBrief]  # sorted by concern_score desc

class OneOnOnePrepBrief(BaseModel):
    developer_id: int
    developer_name: str
    concern_score: float  # 0.0 = all good, 1.0 = needs attention
    result: dict  # same structure as single 1:1 prep result
```

### Frontend
- Add "Prep All 1:1s" button to the AI Analysis page or a dedicated "1:1 Prep" section
- Shows a team selector, then generates briefs for all developers on that team
- Results displayed as a list of cards sorted by concern level
  - Red border: high concern
  - Amber border: moderate
  - Green border: all good
- Each card expandable to show full structured brief (using P1-04 renderer)
- Loading state: show progress as each brief completes

### Rate Limit Consideration
- 10 developers = 10 Claude API calls
- Add a simple rate limiter: max 5 concurrent Claude calls
- Show estimated wait time in the UI
- Consider caching: if a brief for this developer+date range already exists in `ai_analyses`, reuse it
