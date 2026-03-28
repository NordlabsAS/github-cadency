# Task P2-08: Workload, Collaboration, and Benchmarks Frontend Pages

## Phase
Phase 2 — Make It Smart

## Status
pending

## Blocked By
- P1-05-recharts-trend-viz
- P2-01-stale-pr-endpoint
- M4-workload-balance
- M5-collaboration-matrix
- M2-team-benchmarks

## Blocks
None

## Description
Build three new frontend pages for fully-implemented backend features that have zero UI representation: Workload Overview, Collaboration Matrix, and Team Benchmarks. These are the most manager-actionable views in DevPulse.

## Deliverables

### Navigation restructure
Update `Layout.tsx` and `App.tsx`:
- Add "Insights" as a primary nav item with sub-routes:
  - `/insights/workload`
  - `/insights/collaboration`
  - `/insights/benchmarks`
- Move "Sync" to a secondary/admin position or keep but de-emphasize

### frontend/src/pages/insights/WorkloadOverview.tsx (new)
Consumes `GET /api/stats/workload`:
- **Alert section**: render all `WorkloadAlert` items with severity color coding
- **Team workload grid**: one row per developer with:
  - Name (linked to detail page)
  - Horizontal bar showing workload score (color: green/amber/red)
  - Open PRs authored | PRs reviewing | Open issues | Reviews given
  - `prs_waiting_for_review` with age indicator
- **Stale PR list**: render results from `GET /api/stats/stale-prs` (P2-01)
  - Each PR: title (linked to GitHub), author, age badge, stale reason
- Sortable by any column, filterable by team

### frontend/src/pages/insights/CollaborationMatrix.tsx (new)
Consumes `GET /api/stats/collaboration`:
- **Heatmap grid**: Recharts heatmap or custom grid showing reviewer (rows) vs author (columns)
  - Cell color intensity = review count
  - Hover shows exact count and average turnaround
- **Insights panel**:
  - Bus factors: highlighted developers with >70% review share per repo
  - Silos: team pairs with zero cross-team reviews
  - Isolated developers: developers with minimal review interaction
  - Strongest pairs: top reviewer-author pairs
- **Reciprocity indicator**: for each pair, show if reviews are one-directional

### frontend/src/pages/insights/Benchmarks.tsx (new)
Consumes `GET /api/stats/benchmarks`:
- **Percentile table**: one row per metric showing p25, p50, p75 values
- **Developer ranking**: for each metric, show all developers ranked with their value and percentile band
  - Color-coded: above_p75 (green), p50_to_p75 (light green), p25_to_p50 (amber), below_p25 (red)
  - Polarity-aware (for time metrics, lower is better, so colors invert)
- **Box-and-whisker or dot-plot visualization** per metric showing team distribution

### frontend/src/hooks/useInsights.ts (new)
- `useWorkload()` — `GET /api/stats/workload`
- `useCollaboration()` — `GET /api/stats/collaboration`
- `useBenchmarks()` — `GET /api/stats/benchmarks`
- `useStalePRs()` — `GET /api/stats/stale-prs`

### frontend/src/utils/types.ts (extend)
Add interfaces for: `WorkloadResponse`, `DeveloperWorkload`, `WorkloadAlert`, `CollaborationResponse`, `CollaborationMatrix`, `CollaborationInsights`, `BenchmarksResponse`, `MetricBenchmark`, `StalePRsResponse`, `StalePR`
