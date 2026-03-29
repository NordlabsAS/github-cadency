# P2-01: Developer Experience Surveys

> Priority: 2 (Differentiate) | Effort: Medium | Impact: High
> Competitive gap: DX and Swarmia have surveys as core differentiators. No competitor offers self-hosted surveys.

## Context

Quantitative metrics alone miss developer satisfaction, friction points, and burnout signals. DX has built an entire platform around developer experience surveys (SPACE framework). Swarmia uses 32-question surveys. The industry is moving toward combining system metrics with qualitative survey data.

DevPulse has a unique opportunity: **the only self-hosted survey option** in the market. Teams in regulated industries who can't send satisfaction data to third-party SaaS would find this extremely valuable.

## What to Build

### Survey System

**Built-in survey templates:**

1. **Quick Pulse (5 questions, weekly/biweekly):**
   - How productive did you feel this week? (1-5)
   - How would you rate your developer experience today? (1-5)
   - Is anything blocking your work? (yes/no + optional text)
   - How sustainable is your current pace? (1-5)
   - One thing we could improve? (open text)

2. **Comprehensive DX Survey (15-20 questions, quarterly):**
   - Based on SPACE framework dimensions:
     - **Satisfaction:** Overall satisfaction, tool satisfaction, process satisfaction
     - **Performance:** Self-assessed productivity, code quality confidence
     - **Activity:** Meeting load, focus time availability, context switching frequency
     - **Communication:** Team collaboration quality, cross-team friction, documentation quality
     - **Efficiency:** Build/deploy friction, PR review speed perception, onboarding experience
   - Mix of Likert scale (1-5), multiple choice, and open text

3. **Custom surveys:** Admin can create custom question sets

### Survey Distribution & Collection

- Surveys created and distributed within DevPulse (no external tool needed)
- Anonymous by default (configurable: anonymous, pseudonymous, identified)
- Notification via dashboard banner + optional Slack notification (if P1-02 is implemented)
- Response deadline with reminders
- Minimum response threshold before results are visible (prevent de-anonymization)

### Analytics & Correlation

- **Survey trend dashboard:** Track satisfaction scores over time
- **Metric correlation:** Overlay survey sentiment with system metrics
  - e.g., "Teams reporting low productivity also have highest context-switching (PR review load)"
  - e.g., "Satisfaction dropped the month cycle time increased 40%"
- **Team comparison:** Anonymous team-level aggregates (min 5 responses per team)
- **Open text analysis:** Optional AI summarization of free-text responses (uses existing Claude integration)

## Backend Changes

### New Models

**`surveys` table:**
```
id, title, description, template_type ("pulse" | "comprehensive" | "custom"),
questions (JSONB), status ("draft" | "active" | "closed"),
anonymity ("anonymous" | "pseudonymous" | "identified"),
min_responses_for_results (int, default 5),
created_by (FK developers), created_at,
opens_at, closes_at, reminder_sent_at
```

**`survey_responses` table:**
```
id, survey_id (FK), respondent_id (FK developers, nullable if anonymous),
respondent_hash (str, for pseudonymous dedup),
answers (JSONB), submitted_at
```

**`survey_questions` JSONB schema:**
```json
[{
  "id": "q1",
  "text": "How productive did you feel this week?",
  "type": "likert_5" | "yes_no" | "multiple_choice" | "open_text",
  "options": ["Option A", "Option B"],  // for multiple_choice
  "required": true,
  "category": "satisfaction"  // for SPACE framework grouping
}]
```

### New Service: `backend/app/services/surveys.py`
- `create_survey(template_type, overrides)` — create from template or custom
- `submit_response(survey_id, answers, respondent)` — validate + store
- `get_survey_results(survey_id)` — aggregate scores, enforce min response threshold
- `get_survey_trends(team_id, category)` — track scores over time
- `correlate_with_metrics(survey_id, metric_type)` — join survey scores with system metrics
- `summarize_open_text(survey_id, question_id)` — AI summarization of free-text (optional)

### New Router: `backend/app/api/surveys.py`
- `POST /api/surveys` — create survey (admin)
- `GET /api/surveys` — list surveys (all users see active, admin sees all)
- `GET /api/surveys/{id}` — survey detail + questions (for responding)
- `POST /api/surveys/{id}/respond` — submit response
- `GET /api/surveys/{id}/results` — aggregated results (admin, respects min threshold)
- `GET /api/surveys/trends` — satisfaction trends over time
- `PUT /api/surveys/{id}/close` — close survey early

## Frontend Changes

### Survey Response Page (`/surveys/{id}`)
- Clean, focused survey form
- Progress indicator for multi-question surveys
- Anonymous submission confirmation
- "Already submitted" state

### Survey Dashboard (`/insights/surveys`)
- Active surveys with response rate
- Historical trend charts (satisfaction over time per SPACE dimension)
- Team comparison (anonymous aggregates)
- Correlation panel: overlay satisfaction with system metrics
- Open text summary (AI-powered, if enabled)

### Survey Admin (`/admin/surveys`)
- Create from template or custom
- Set schedule, anonymity level, reminder config
- View response rates per active survey
- Close/archive surveys

### Dashboard Integration
- Active survey banner on main dashboard ("Complete the weekly pulse survey")
- Satisfaction trend widget on Executive Dashboard

## Privacy & Security
- Anonymous responses: `respondent_id` is NULL, only `respondent_hash` (salted hash of user ID) stored for dedup
- Minimum response threshold enforced server-side (results return 403 if below threshold)
- Admin cannot see individual anonymous responses
- Survey data never leaves the self-hosted instance
- AI summarization is opt-in and uses existing AI settings/budget controls

## Testing
- Unit test anonymity enforcement (no respondent_id leak)
- Unit test minimum response threshold
- Unit test survey template generation
- Unit test response validation (required fields, type checking)
- Unit test trend computation and SPACE dimension aggregation
- Test deduplication (one response per user per survey)

## Acceptance Criteria
- [ ] Quick Pulse and Comprehensive DX survey templates available
- [ ] Custom survey creation for admins
- [ ] Anonymous response collection with dedup
- [ ] Minimum response threshold before results visible
- [ ] Satisfaction trends over time (per SPACE dimension)
- [ ] Team-level anonymous aggregation
- [ ] Correlation with system metrics (cycle time, workload, etc.)
- [ ] Optional AI summarization of open-text responses
- [ ] Active survey banner on dashboard
- [ ] All data stays self-hosted (core differentiator)
