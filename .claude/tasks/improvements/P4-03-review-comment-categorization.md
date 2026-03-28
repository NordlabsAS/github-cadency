# Task P4-03: Review Comment Categorization

## Phase
Phase 4 — Make It Best-in-Class

## Status
pending

## Blocked By
- M1-review-quality-signals

## Blocks
None

## Description
Categorize review comments into types (nit, blocker, architectural, question, praise) to distinguish meaningful review feedback from noise. A PR with 20 nit comments is very different from one with 3 architectural concerns, but the current quality tier treats them identically. Uses keyword/prefix detection on already-stored comment bodies.

## Deliverables

### Database migration
Add column to `pr_review_comments`:
- `comment_type` (String(30), default "general") — "nit", "blocker", "architectural", "question", "praise", "suggestion", "general"

### backend/app/services/github_sync.py (extend)
New helper: `classify_comment_type(body: str) -> str`

Keyword-based classification:
```python
def classify_comment_type(body: str) -> str:
    lower = body.lower().strip()
    # Common prefixes used by reviewers
    if lower.startswith(("nit:", "nit ", "nitpick:", "optional:", "minor:")):
        return "nit"
    if lower.startswith(("blocker:", "blocking:", "must fix:", "critical:")):
        return "blocker"
    if any(kw in lower for kw in ["architecture", "design concern", "separation of concern", "coupling"]):
        return "architectural"
    if lower.endswith("?") or lower.startswith(("why", "what", "how", "could you explain", "question:")):
        return "question"
    if any(kw in lower for kw in ["nice", "great", "well done", "lgtm", "love this", ":+1:", "good job"]):
        return "praise"
    if "suggestion" in lower or lower.startswith("consider:"):
        return "suggestion"
    return "general"
```

Call in the review comment upsert during sync.

### backend/app/services/stats.py (extend)
Add to review quality analysis:
- `comment_type_distribution` per developer (as reviewer): `{"nit": 15, "blocker": 3, ...}`
- `blocker_catch_rate` — percentage of reviews that contain at least one "blocker" comment
- `nit_ratio` — percentage of all comments that are nits (high ratio = reviewer may be too focused on style)

### backend/app/schemas/schemas.py (extend)
- Add `comment_type_distribution: dict[str, int]` to review quality section of `DeveloperStatsResponse`

### Integration with review quality scoring
Use comment types as an additional signal in `classify_review_quality()`:
- Reviews with a "blocker" comment → minimum "standard" tier
- Reviews with 3+ "architectural" comments → "thorough" tier regardless of body length
