# Phase 2: Full Stats Exclusion for Work Categories

## Status: Pending (depends on Phase 1 — configurable work categories)

## Problem

Phase 1 adds configurable work categories with an `exclude_from_stats` flag, but only the Investment page respects it initially. All other stats queries still include items from excluded categories (e.g., Epics), which inflates close times, cycle times, and velocity metrics.

## Goal

Every stats query that aggregates PR/issue data should filter out items whose `work_category` maps to a category with `exclude_from_stats=true`.

## How It Works

### The exclusion mechanism

1. `work_categories` table has `exclude_from_stats: bool` per category
2. `get_excluded_categories(db) -> set[str]` loads the excluded keys (defined in `backend/app/services/work_categories.py`)
3. Each stats query either:
   - **SQL-level**: Adds `WHERE work_category NOT IN (:excluded)` (or `WHERE work_category IS NULL OR work_category NOT IN (:excluded)` to handle unclassified items)
   - **Python-level**: Filters rows after fetch using the excluded set (preferred when queries already do heavy Python aggregation)

### Why not SQL JOINs?

Stats queries are already complex multi-join aggregations. Adding another JOIN to `work_categories` on every query is high-risk churn. Instead, load the excluded set once per request (tiny — typically 0-2 keys) and filter in Python or add a simple `NOT IN` clause.

## Files to Modify

### `backend/app/services/stats.py` — the main target

| Function | Line area | What it computes | How to exclude |
|----------|-----------|------------------|----------------|
| `get_developer_stats()` | ~120-200 | PR counts, cycle times, review counts per developer | Add `NOT IN` to PR/review queries |
| `get_team_stats()` | ~200-280 | Aggregated team metrics | Same — filter PR/issue queries |
| `get_developer_trends()` | ~280-370 | Weekly/monthly trend data points | Filter before bucketing |
| `get_workload()` | ~370-430 | Open PR/issue counts per developer | Filter open PRs/issues by category |
| `get_activity_summary()` | ~440-540 | All-time per-developer stats | Filter PR/issue queries; keep work_categories breakdown showing all (including excluded) with a flag |
| `get_repo_stats()` | ~540-620 | Per-repo PR/issue metrics | Filter queries |
| `get_repos_summary()` | ~620-750 | Batch repo metrics (avg merge time, PR count) | Filter PR queries |
| `_compute_per_developer_metrics()` | ~1050-1200 | Benchmark metrics (9 base + 5 extended) | Filter all 14 metric queries |
| `get_developer_benchmarks()` | ~1200-1400 | Percentile computation | Inherits from `_compute_per_developer_metrics` |

### `backend/app/services/collaboration.py`

| Function | What it computes | How to exclude |
|----------|------------------|----------------|
| `get_collaboration_matrix()` | Review pairs and counts | Probably should NOT exclude — reviews on epics are still real collaboration |
| `get_pair_detail()` | Per-pair review breakdown | Same — keep all reviews |

**Decision needed**: Should collaboration metrics exclude epic PRs? Likely no — a review is a review regardless of work type. But this should be confirmed.

### `backend/app/services/risk.py`

| Function | What it computes | How to exclude |
|----------|------------------|----------------|
| `compute_pr_risk()` | Per-PR risk score | Should NOT exclude — risk scoring is per-PR, not aggregated |
| `get_team_risk_summary()` | Aggregated risk overview | Could exclude, but epics being flagged as high-risk is actually useful information |

**Decision needed**: Risk scoring probably stays as-is. Epics are legitimately high-risk.

### `backend/app/services/goals.py`

| Function | What it computes | How to exclude |
|----------|------------------|----------------|
| `compute_goal_metric()` | Goal progress (PR count, review count, etc.) | Should exclude — goals like "merge 10 PRs" shouldn't count epics if excluded |

### Issue-specific stats

| Location | What it computes | How to exclude |
|----------|------------------|----------------|
| Issue Quality page queries | `time_to_close_s`, quality scores | **Critical** — this is the primary motivator. Epics with 6-week close times destroy averages. Add `NOT IN` filter. |
| DORA metrics | Lead time for changes | Filter deployment-linked PRs by category |

## Implementation Pattern

```python
# At the top of any stats function that needs exclusion:
from app.services.work_categories import get_excluded_categories

async def get_developer_stats(db: AsyncSession, ...):
    excluded = await get_excluded_categories(db)  # cached per request

    # Option A: SQL-level (for simple queries)
    query = select(...).where(
        PullRequest.work_category.notin_(excluded) if excluded else True
    )

    # Option B: Python-level (for complex aggregations)
    rows = (await db.execute(query)).all()
    rows = [r for r in rows if (r.work_category or "unknown") not in excluded]
```

## Testing Strategy

For each modified function:
1. Create a PR/issue with a category that has `exclude_from_stats=true`
2. Verify it's excluded from the stat computation
3. Verify items with `exclude_from_stats=false` categories are still included
4. Verify unclassified items (`work_category=NULL`) are still included
5. Verify manual overrides to excluded categories ARE excluded (the exclusion is by category, not by source)

## Edge Cases

- **NULL work_category**: Items not yet classified (legacy data before Phase 1). These should be INCLUDED in stats (treated as "unknown", which is never excluded).
- **Category deleted after items classified**: Items retain the stored `work_category` string. If the category no longer exists, treat as "unknown" (included in stats). The reclassify endpoint would fix these.
- **Activity summary work breakdown**: The stacked bar on DeveloperDetail should still show ALL categories including excluded ones — it's informational. Only the aggregate numbers (total PRs, avg cycle time) should exclude.

## Estimated Scope

- ~10 functions in `stats.py` need filtering
- ~2 functions in `goals.py`
- ~0-1 in `collaboration.py` and `risk.py` (likely no changes)
- ~5 new test cases
- No frontend changes (stats API responses already exclude; frontend just renders what it gets)
