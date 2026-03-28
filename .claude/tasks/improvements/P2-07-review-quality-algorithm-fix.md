# Task P2-07: Fix Review Quality Classification Algorithm

## Phase
Phase 2 — Make It Smart

## Status
pending

## Blocked By
- M1-review-quality-signals

## Blocks
None

## Description
Rework `classify_review_quality()` to use multiple signals instead of only character count. The current algorithm penalizes concise, precise reviewers and rewards verbose but shallow reviewers. A `CHANGES_REQUESTED` review — the strongest quality signal — is ignored in classification.

## Current Algorithm (github_sync.py:242-261)
```
thorough:     body > 500 chars OR 3+ inline comments
standard:     body 100-500 chars
rubber_stamp: state=APPROVED AND body < 20 chars
minimal:      everything else
```

## New Algorithm
```
thorough:     body > 500 chars, OR 3+ inline comments, OR (CHANGES_REQUESTED AND body > 100 chars)
standard:     body 100-500 chars, OR CHANGES_REQUESTED (any length), OR body contains code blocks (```)
rubber_stamp: state=APPROVED AND body < 20 chars AND 0 inline comments
minimal:      everything else
```

Key changes:
1. `CHANGES_REQUESTED` automatically qualifies as minimum "standard" — blocking a merge is meaningful review work regardless of comment length
2. Code blocks in review body indicate technical substance (code suggestions, examples)
3. `rubber_stamp` now additionally requires 0 inline comments — if there are inline comments, the reviewer did engage with the code

## Deliverables

### backend/app/services/github_sync.py
Rewrite `classify_review_quality()`:

```python
def classify_review_quality(review_state: str, body_length: int, comment_count: int, body: str = "") -> str:
    has_code_blocks = "```" in body if body else False

    if body_length > 500 or comment_count >= 3:
        return "thorough"
    if review_state == "CHANGES_REQUESTED" and body_length > 100:
        return "thorough"
    if review_state == "CHANGES_REQUESTED":
        return "standard"
    if body_length >= 100 or has_code_blocks:
        return "standard"
    if review_state == "APPROVED" and body_length < 20 and comment_count == 0:
        return "rubber_stamp"
    return "minimal"
```

### Recompute existing data
Add a one-time migration script or management command that recomputes `quality_tier` for all existing reviews using the new algorithm. This can be a standalone script in `backend/scripts/recompute_review_quality.py`.

### Frontend label change
In any frontend component that displays the quality tier, rename "rubber_stamp" display label to "Quick Approval" — the backend value stays `rubber_stamp` for consistency, but the UI label is less stigmatizing.

## Testing
- Unit test: `CHANGES_REQUESTED` with empty body → "standard" (was "minimal")
- Unit test: `APPROVED` with 15-char body but 2 inline comments → "minimal" (not "rubber_stamp")
- Unit test: `COMMENTED` with code block in body → "standard"
- Unit test: backward compatibility — existing "thorough" classifications still hold
