# Task P3-05: PR Risk Scoring

## Phase
Phase 3 — Make It Proactive

## Status
pending

## Blocked By
- P2-05-pr-metadata-capture
- P2-02-review-round-trips

## Blocks
None

## Description
Automatically score open PRs by risk level to help team leads and reviewers prioritize review effort. High-risk PRs (large changes, junior authors, fast-tracked merges) deserve more thorough review. Currently, all PRs are treated equally with no risk signal.

## Deliverables

### backend/app/services/risk.py (new)
New function: `async def compute_pr_risk(session, pr_id) -> RiskAssessment`

Risk factors computable from existing data (no new tables needed):

| Factor | Condition | Weight |
|--------|-----------|--------|
| Large PR | additions > 500 | +0.20 |
| Very large PR | additions > 1000 | +0.15 (additional) |
| Many files | changed_files > 15 | +0.10 |
| New contributor | author has < 5 merged PRs in this repo | +0.15 |
| No review | is_merged and no APPROVED review | +0.25 |
| Rubber-stamp only | all reviews are rubber_stamp tier | +0.20 |
| Fast-tracked | time_to_merge_s < 7200 (2 hours) | +0.15 |
| Self-merged | is_self_merged = True | +0.10 |
| High review rounds | review_round_count >= 3 | +0.10 |
| Hotfix branch | head_branch starts with "hotfix/" or "fix/" | +0.10 |

Risk score = min(1.0, sum of applicable weights)
Risk level: low (0-0.3), medium (0.3-0.6), high (0.6-0.8), critical (0.8-1.0)

### backend/app/schemas/schemas.py (extend)
```python
class RiskFactor(BaseModel):
    factor: str
    weight: float
    description: str

class RiskAssessment(BaseModel):
    pr_id: int
    risk_score: float  # 0.0-1.0
    risk_level: str  # low/medium/high/critical
    risk_factors: list[RiskFactor]

class TeamRiskSummary(BaseModel):
    high_risk_prs: list[RiskAssessment]
    avg_risk_score: float
    prs_merged_high_risk: int
```

### backend/app/api/stats.py (extend)
New routes:
- `GET /api/stats/pr/{id}/risk` — risk assessment for a single PR
- `GET /api/stats/risk-summary` — team-level risk summary for the period
  - Query params: `date_from`, `date_to`, `team`, `min_risk_level` (default "medium")

### Frontend integration
- Add risk badge to stale PR list items (P2-01)
- Add "High-Risk PRs" section to Dashboard "Needs Attention" zone
- Color-code: green (low), amber (medium), orange (high), red (critical)
