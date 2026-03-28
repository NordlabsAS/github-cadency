# Task P3-10: Developer "Invisible Work" Notes

## Phase
Phase 3 — Make It Proactive

## Status
pending

## Blocked By
- P1-01-developer-self-access

## Blocks
None

## Description
Allow developers to annotate time periods with notes explaining non-code work: on-call rotation, mentoring, architecture reviews, conference attendance, vacation. This prevents the "underutilized" alert from firing unfairly and gives managers context for low-activity periods. Currently, a developer on vacation for a week shows zero PRs with no explanation.

## Deliverables

### Database migration
New table: `developer_notes`
- `id` (Integer, PK)
- `developer_id` (Integer, FK to developers, not null)
- `date_from` (Date, not null)
- `date_to` (Date, not null)
- `note_type` (String(50)) — "vacation", "on_call", "mentoring", "architecture", "conference", "other"
- `note_text` (Text, not null)
- `created_at` (DateTime)

### backend/app/models/models.py (extend)
Add `DeveloperNote` model.

### backend/app/api/notes.py (new)
- `POST /api/developers/{id}/notes` — create a note (admin or developer's own token via P1-01)
- `GET /api/developers/{id}/notes` — list notes for a developer (filterable by date range)
- `DELETE /api/developers/{id}/notes/{note_id}` — delete a note

### backend/app/schemas/schemas.py (extend)
```python
class DeveloperNoteCreate(BaseModel):
    date_from: date
    date_to: date
    note_type: str  # "vacation" | "on_call" | "mentoring" | "architecture" | "conference" | "other"
    note_text: str

class DeveloperNoteResponse(BaseModel):
    id: int
    developer_id: int
    date_from: date
    date_to: date
    note_type: str
    note_text: str
    created_at: datetime
```

### Integration with existing features

**Workload alerts:** In `get_workload()`, before generating an `underutilized` alert for a developer, check if they have an active note overlapping the current period. If so, suppress the alert or change it to an `info` severity with the note context.

**1:1 prep brief:** Include active developer notes in the context sent to Claude for the 1:1 prep. The AI can then account for non-code work in its assessment.

**Developer Detail page:** Show notes as a timeline/banner on the developer detail page, providing context for any metric dips.

### Frontend
- Add "Add Note" button on Developer Detail page
- Simple form: date range, type dropdown, free text
- Notes displayed as colored banners on the trends chart (e.g., gray band for vacation periods)
- Developers can add notes for themselves using their personal token
