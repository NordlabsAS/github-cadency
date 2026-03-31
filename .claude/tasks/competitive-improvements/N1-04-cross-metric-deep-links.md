# N1-04: Cross-Metric Deep Links

> Priority: Notion-inspired | Effort: Low-Medium | Impact: Medium (Stickiness)
> Origin: Notion analysis — Notion's connected databases let everything link to everything

## Context

DevPulse computes rich interconnected metrics but the UI treats them as isolated views. When a manager sees a developer's cycle time percentile on the Benchmarks page, there's no way to click through to the underlying data. When workload shows someone as "overloaded", there's no link to their open PRs.

Notion's core insight: data becomes more valuable when everything links to everything. DevPulse already has the pages and data — it's about wiring clickable connections.

## Requirements

### Benchmark Page → Developer Detail
1. Developer names in the benchmark ranking table should link to `/team/{id}`
2. Individual metric cells (e.g., cycle time value) should link to `/team/{id}?tab=prs` or a relevant section
3. When clicking from a specific metric context, the developer detail page should scroll to or highlight the relevant section

### Workload Page → Developer Detail
1. Developer names in workload table link to `/team/{id}`
2. Workload score badge links to developer detail filtered to open items
3. "Overloaded" alerts link to the specific developer

### Dashboard Alerts → Source Data
1. Stale PR alerts → link to the PR on GitHub (already have `html_url`) AND to the author's developer detail
2. High-risk PR alerts → link to PR detail with risk factors visible
3. Workload warnings → link to developer detail page

### Collaboration Matrix → Pair Detail
1. Cells in the heatmap that show review counts should be clickable (this may already work — verify)
2. Bus factor warnings should link to the repo or developer detail

### Investment Donut → Category Items
1. Already partially implemented (clickable segments → `InvestmentCategory` page)
2. Ensure items in the category list link to their GitHub PR/issue URLs

### Repos Summary → Insight Pages
1. Already partially implemented (`?repo_id=` deep links to DORA, CI, Code Churn)
2. Add: repo name in other contexts (benchmarks, workload) should link to repo detail/expanded view

### Implementation Pattern
- Use React Router `<Link>` with query params for filtering: `?developer_id=`, `?repo_id=`, `?metric=`
- Receiving pages should read these params via `useSearchParams` and apply filters/scrolling
- Use `cursor-pointer` and subtle hover underline to indicate clickability without cluttering the UI

## Implementation Notes

- Audit each page to see what's already clickable — some of these may already be partially wired
- Don't over-link: metric values and developer names are the primary link targets. Don't make every cell clickable.
- For scroll-to-section, use `id` attributes on section headings and `scrollIntoView()` or hash fragments
- Consider adding `?from=benchmarks` or similar to enable context-aware breadcrumbs (ties into N1-03)

## Acceptance Criteria

- [ ] Developer names on Benchmarks page link to developer detail
- [ ] Developer names on Workload page link to developer detail
- [ ] Dashboard stale PR alerts link to PR author's detail page
- [ ] Dashboard risk alerts include actionable links
- [ ] Investment category items link to GitHub
- [ ] No dead-end pages — every entity mention is a potential navigation point
- [ ] Links are visually indicated (hover state) without cluttering the UI
