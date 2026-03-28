# Task P2-09: Goals Management Page

## Phase
Phase 2 — Make It Smart

## Status
pending

## Blocked By
- M6-developer-goals
- P1-05-recharts-trend-viz

## Blocks
None

## Description
Build a dedicated Goals page that surfaces the fully-implemented goals API (`/api/goals`). Currently, goals have full CRUD API with 8-week progress history and auto-achievement detection, but zero frontend UI. A team lead cannot create, view, or track goals from the browser.

## Deliverables

### frontend/src/pages/Goals.tsx (new)
Route: `/goals`

**Team view (admin):**
- Filter by developer (dropdown) or show all
- List of all goals grouped by developer:
  - Goal card: metric name, target value, current value, progress bar (baseline -> current -> target)
  - Status badge: active (blue), achieved (green), abandoned (gray)
  - Target date with "N days remaining" or "overdue" indicator
  - 8-week sparkline showing progress history (Recharts `Sparkline` or small `LineChart`)
- "Create Goal" button → modal/dialog with form:
  - Developer selector
  - Metric key selector (dropdown of MetricKey enum values with human-readable labels)
  - Target value input
  - Target date picker
  - Optional notes field

**Developer view (personal token):**
- Shows only own goals
- "Add Personal Goal" button (calls `POST /api/goals/self` from P1-03)
- Same goal cards with progress bars and sparklines

### frontend/src/hooks/useGoals.ts (new)
- `useGoals(developerId?: number)` — `GET /api/goals?developer_id={id}`
- `useGoalProgress(goalId: number)` — `GET /api/goals/{id}/progress`
- `useCreateGoal()` — mutation for `POST /api/goals`
- `useUpdateGoal()` — mutation for `PATCH /api/goals/{id}`

### frontend/src/utils/types.ts (extend)
Add interfaces for: `DeveloperGoal`, `GoalCreate`, `GoalUpdate`, `GoalProgressResponse`, `GoalProgressPoint`

### Goal metric labels
Map `MetricKey` enum values to human-readable labels:
```typescript
const METRIC_LABELS: Record<string, string> = {
  avg_pr_additions: "Avg PR Size (additions)",
  time_to_merge_h: "Time to Merge (hours)",
  reviews_given: "Reviews Given",
  review_quality_score: "Review Quality Score",
  prs_merged: "PRs Merged",
  time_to_first_review_h: "Time to First Review (hours)",
  issues_closed: "Issues Closed",
  prs_opened: "PRs Opened",
}
```

### Navigation
- Add "Goals" to primary or secondary nav in `Layout.tsx`
- Add route in `App.tsx`: `/goals` -> `Goals`
