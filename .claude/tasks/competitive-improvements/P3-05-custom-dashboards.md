# P3-05: Custom Dashboards

> Priority: 3 (Nice-to-Have) | Effort: Large | Impact: Medium
> Competitive gap: Fixed dashboard layouts. No drag-and-drop or custom metric composition.

## Context

DevPulse has fixed dashboard layouts. Different roles want different views: a CTO might want DORA + investment + headcount on one screen; a tech lead might want risk + review quality + CI health. Custom dashboards let users compose their own views.

## What to Build

### Dashboard Builder

**Widget types (each maps to an existing metric/visualization):**

| Widget | Data Source | Sizes |
|--------|-----------|-------|
| Stat Card | Any single metric (cycle time, PR count, etc.) | 1x1 |
| Trend Chart | Any trended metric | 2x1, 3x1 |
| DORA Summary | DORA metrics | 2x2 |
| Risk PRs | Risk assessment list | 2x2 |
| Stale PRs | Stale PR list | 2x1 |
| Workload Heatmap | Workload scores | 2x2, 3x2 |
| Collaboration Matrix | Collaboration data | 3x3 |
| Review Quality Donut | Review quality distribution | 1x1 |
| Leaderboard | Top N developers by metric | 1x2 |
| Goal Progress | Team/developer goal progress | 2x1 |
| Investment Pie | Work categorization breakdown | 1x1 |
| Benchmark Comparison | Industry/team benchmarks | 2x1 |
| Survey Score | Latest survey results | 1x1 |
| Text/Markdown | Static text, notes, links | Any |

### Layout System

- CSS Grid-based layout (12-column grid)
- Drag-and-drop widget placement (using `@dnd-kit/core`)
- Resize handles on widgets
- Responsive: widgets reflow on smaller screens
- Save/load named dashboard configurations

### Dashboard Features

- **Personal dashboards:** Each user can create their own
- **Shared dashboards:** Admin/team_lead can create team-visible dashboards
- **Default dashboard:** Admin sets the org-wide default
- **Dashboard templates:** Pre-built layouts matching current fixed pages

## Backend Changes

### New Model: `dashboards` table
```
id, name, description, owner_id (FK developers),
visibility ("personal" | "team" | "org"),
team_scope (str, nullable), is_default (bool),
layout (JSONB — widget positions and configs),
created_at, updated_at
```

### Dashboard Layout JSONB Schema
```json
{
  "columns": 12,
  "widgets": [
    {
      "id": "w1",
      "type": "stat_card",
      "config": { "metric": "avg_cycle_time", "scope": "team" },
      "position": { "x": 0, "y": 0, "w": 3, "h": 1 }
    },
    {
      "id": "w2",
      "type": "trend_chart",
      "config": { "metric": "pr_throughput", "period": "weekly" },
      "position": { "x": 3, "y": 0, "w": 6, "h": 2 }
    }
  ]
}
```

### New Router: `backend/app/api/dashboards.py`
- `POST /api/dashboards` — create dashboard
- `GET /api/dashboards` — list accessible dashboards
- `GET /api/dashboards/{id}` — get dashboard with layout
- `PUT /api/dashboards/{id}` — save layout changes
- `DELETE /api/dashboards/{id}` — delete (owner or admin)
- `POST /api/dashboards/{id}/clone` — clone dashboard
- `PUT /api/dashboards/default` — set org default (admin)

### Widget Data Endpoint
- `GET /api/dashboards/widget-data?type={type}&config={json}` — generic endpoint that routes to existing stat services based on widget type/config
- Avoids frontend needing to know which API to call for each widget type

## Frontend Changes

### Dashboard Viewer (`/dashboard/custom/{id}`)
- Render grid layout from saved configuration
- Each widget fetches its own data via TanStack Query
- Date range picker applies to all widgets
- Auto-refresh on configured interval

### Dashboard Builder (`/dashboard/edit/{id}`)
- Widget palette (sidebar with draggable widget types)
- Grid canvas with snap-to-grid placement
- Widget configuration panel (metric picker, size, title override)
- Drag-and-drop reordering (`@dnd-kit/core` + `@dnd-kit/sortable`)
- Resize handles on widget corners
- Preview mode toggle
- Save/discard buttons

### Dashboard Switcher
- Dropdown in header to switch between dashboards
- "Create new dashboard" option
- Star/favorite dashboards

### Widget Components (`frontend/src/components/widgets/`)
- Base `DashboardWidget` wrapper (handles loading, error, sizing)
- One component per widget type, reusing existing chart/stat components
- `WidgetRegistry` maps type → component + default config

## Dependencies
- `@dnd-kit/core` + `@dnd-kit/sortable` for drag-and-drop
- No additional backend dependencies

## Testing
- Unit test layout serialization/deserialization
- Unit test widget data routing
- Unit test visibility/permission logic (personal vs. team vs. org)
- Frontend: test widget rendering with mock data
- Test dashboard CRUD operations

## Acceptance Criteria
- [ ] Users can create personal dashboards
- [ ] Admins can create shared/org-default dashboards
- [ ] Drag-and-drop widget placement on grid
- [ ] Widget resize support
- [ ] 10+ widget types covering existing metrics
- [ ] Dashboard save/load/clone
- [ ] Dashboard switcher in header
- [ ] Pre-built templates matching current fixed layouts
- [ ] Responsive widget reflow
