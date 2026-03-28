# Task P4-04: Executive Reporting Dashboard

## Phase
Phase 4 — Make It Best-in-Class

## Status
pending

## Blocked By
- P1-05-recharts-trend-viz
- P2-08-workload-collaboration-pages
- P3-02-sprint-model
- P4-02-work-categorization

## Blocks
None

## Description
Build a director/VP-level dashboard that shows team health at a strategic level: velocity trends, work allocation, quality indicators, and risk signals. This is a different view than the team lead dashboard — it answers "is this team healthy and shipping?" rather than "what needs my attention today?"

## Deliverables

### frontend/src/pages/ExecutiveDashboard.tsx (new)
Route: `/executive` (admin-only)

**Section 1: Team Velocity**
- Line chart: PRs merged per week over the last 12 weeks
- Line chart: Avg time to merge per week
- Sprint-over-sprint velocity comparison (if sprints are configured)
- Delta vs previous quarter

**Section 2: Investment Allocation**
- Donut chart: feature vs bugfix vs tech-debt vs ops (from P4-02)
- Stacked area chart: allocation trend over time (monthly)
- Comparison to previous quarter

**Section 3: Quality Indicators**
- Revert rate trend (from P2-06)
- Review quality score trend (team average)
- PRs merged without review count
- CI failure rate trend (from P3-07, if available)

**Section 4: Team Health Summary**
- Bus factor alerts (repos with single-reviewer dependency)
- Silo alerts (teams not reviewing each other's code)
- Workload distribution: is work spread evenly?
- Developer growth: goals achieved this quarter

**Section 5: Risks**
- High-risk PRs merged this period (from P3-05)
- Developers with declining trends
- Stale PR backlog size

### Backend
No new backend endpoints needed — this page composes existing endpoints:
- `GET /api/stats/team` (with current + previous quarter date ranges)
- `GET /api/stats/workload`
- `GET /api/stats/collaboration`
- `GET /api/stats/benchmarks`
- `GET /api/stats/work-allocation` (P4-02)
- `GET /api/stats/risk-summary` (P3-05)

### Navigation
- Add "Executive" as an admin-only nav item
- Only visible when authenticated with admin token
