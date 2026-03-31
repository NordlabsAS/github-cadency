# N1-03: Breadcrumb Navigation on Drill-Down Pages

> Priority: Notion-inspired | Effort: Low | Impact: Medium (UX polish)
> Origin: Notion analysis — Notion's nested sidebar with breadcrumb trail makes deep hierarchies intuitive

## Context

DevPulse has several drill-down flows where users navigate from a summary view into detail:
- Benchmarks → Developer Detail
- Collaboration Matrix → Pair Detail (sheet or page)
- Investment → Category → Item list
- Repos → Repo detail (expanded row → DORA/CI/Churn pages with `?repo_id=`)
- Workload → Developer Detail
- Sync History → Sync Detail

Currently, navigating back relies on browser back button or re-clicking nav items. There's no visual trail showing where you are in the hierarchy.

## Requirements

### Component
1. Create a `Breadcrumb` component in `frontend/src/components/Breadcrumb.tsx`
2. Props: `items: Array<{ label: string, href?: string }>` — last item has no href (current page)
3. Styling: small text, muted color, separator (`/` or `>`), consistent with shadcn/ui design tokens
4. Truncate long labels with ellipsis if needed

### Integration Points
Add breadcrumbs to these pages:

| Page | Breadcrumb Trail |
|------|-----------------|
| `DeveloperDetail` | Team > @username |
| `CollaborationPairPage` | Insights > Collaboration > @reviewer → @author |
| `InvestmentCategory` | Insights > Investment > {category} |
| `SyncDetailPage` | Admin > Sync > Sync #{id} |
| `DORA` (with `?repo_id=`) | Insights > DORA > {repo_name} |
| `CIInsights` (with `?repo_id=`) | Insights > CI > {repo_name} |
| `CodeChurn` (with `?repo_id=`) | Insights > Code Churn > {repo_name} |

### UX
- Placed below the page header, above content — consistent position across all pages
- Breadcrumb items are clickable links (except the last/current one)
- When navigating from a specific context (e.g., Benchmarks → Developer), preserve the source in the breadcrumb via URL search params or referrer state

## Implementation Notes

- shadcn/ui has a `Breadcrumb` primitive — check if it's already installed, otherwise use a simple custom component
- For context-aware breadcrumbs (knowing the user came from Benchmarks vs. Team Registry), use `location.state` passed via React Router's `<Link state={}>` — fall back to generic trail if no state
- Keep it simple: static breadcrumbs based on the current route are sufficient for v1. Context-aware "you came from X" is a nice v2 enhancement.

## Acceptance Criteria

- [ ] Breadcrumb component created with consistent styling
- [ ] Breadcrumbs appear on all listed drill-down pages
- [ ] Each breadcrumb segment links to the correct parent page
- [ ] Current page shown as non-clickable last segment
- [ ] Visually consistent with existing shadcn/ui design
