"""Unit tests for compute_pr_risk — pure function, no DB needed."""

import pytest

from app.services.risk import compute_pr_risk, _risk_level


class FakeReview:
    """Minimal stand-in for PRReview ORM object."""

    def __init__(self, state: str = "APPROVED", quality_tier: str = "standard"):
        self.state = state
        self.quality_tier = quality_tier


class FakePR:
    """Minimal stand-in for PullRequest ORM object."""

    def __init__(self, **kwargs):
        defaults = {
            "additions": 100,
            "deletions": 50,
            "changed_files": 5,
            "is_merged": False,
            "is_self_merged": False,
            "time_to_merge_s": None,
            "review_round_count": 0,
            "head_branch": "feature/foo",
            "state": "open",
            "reviews": [],
        }
        defaults.update(kwargs)
        for k, v in defaults.items():
            setattr(self, k, v)


class TestRiskLevel:
    def test_low(self):
        assert _risk_level(0.0) == "low"
        assert _risk_level(0.29) == "low"

    def test_medium(self):
        assert _risk_level(0.3) == "medium"
        assert _risk_level(0.59) == "medium"

    def test_high(self):
        assert _risk_level(0.6) == "high"
        assert _risk_level(0.79) == "high"

    def test_critical(self):
        assert _risk_level(0.8) == "critical"
        assert _risk_level(1.0) == "critical"


class TestComputePrRisk:
    def test_no_risk_factors(self):
        pr = FakePR()
        factors, score = compute_pr_risk(pr, author_merged_count=10)
        assert factors == []
        assert score == 0.0

    # --- Size factors ---

    def test_large_pr(self):
        pr = FakePR(additions=600)
        factors, score = compute_pr_risk(pr, author_merged_count=10)
        assert len(factors) == 1
        assert factors[0].factor == "large_pr"
        assert factors[0].weight == 0.20

    def test_very_large_pr(self):
        pr = FakePR(additions=1500)
        factors, score = compute_pr_risk(pr, author_merged_count=10)
        assert len(factors) == 1
        assert factors[0].factor == "very_large_pr"
        assert factors[0].weight == 0.35

    def test_large_pr_boundary_500(self):
        pr = FakePR(additions=500)
        factors, _ = compute_pr_risk(pr, author_merged_count=10)
        assert all(f.factor != "large_pr" for f in factors)

    def test_large_pr_boundary_501(self):
        pr = FakePR(additions=501)
        factors, _ = compute_pr_risk(pr, author_merged_count=10)
        assert any(f.factor == "large_pr" for f in factors)

    def test_many_files(self):
        pr = FakePR(changed_files=20)
        factors, _ = compute_pr_risk(pr, author_merged_count=10)
        assert any(f.factor == "many_files" for f in factors)

    def test_many_files_boundary(self):
        pr = FakePR(changed_files=15)
        factors, _ = compute_pr_risk(pr, author_merged_count=10)
        assert all(f.factor != "many_files" for f in factors)

    def test_null_additions(self):
        pr = FakePR(additions=None)
        factors, _ = compute_pr_risk(pr, author_merged_count=10)
        assert all(f.factor not in ("large_pr", "very_large_pr") for f in factors)

    # --- Author experience ---

    def test_new_contributor_low_count(self):
        pr = FakePR()
        factors, _ = compute_pr_risk(pr, author_merged_count=3)
        assert any(f.factor == "new_contributor" for f in factors)

    def test_new_contributor_external(self):
        pr = FakePR()
        factors, _ = compute_pr_risk(pr, author_merged_count=None)
        f = [x for x in factors if x.factor == "new_contributor"][0]
        assert "not in the team registry" in f.description

    def test_experienced_author(self):
        pr = FakePR()
        factors, _ = compute_pr_risk(pr, author_merged_count=5)
        assert all(f.factor != "new_contributor" for f in factors)

    # --- Review factors ---

    def test_no_review_merged(self):
        pr = FakePR(is_merged=True, reviews=[])
        factors, _ = compute_pr_risk(pr, author_merged_count=10)
        assert any(f.factor == "no_review" for f in factors)

    def test_no_review_not_merged(self):
        """no_review only applies to merged PRs."""
        pr = FakePR(is_merged=False, reviews=[])
        factors, _ = compute_pr_risk(pr, author_merged_count=10)
        assert all(f.factor != "no_review" for f in factors)

    def test_no_review_is_merged_none(self):
        """is_merged=None (unknown state) should not trigger no_review."""
        pr = FakePR(is_merged=None, reviews=[])
        factors, _ = compute_pr_risk(pr, author_merged_count=10)
        assert all(f.factor != "no_review" for f in factors)

    def test_fast_tracked_is_merged_none(self):
        """is_merged=None should not trigger fast_tracked."""
        pr = FakePR(is_merged=None, time_to_merge_s=1000)
        factors, _ = compute_pr_risk(pr, author_merged_count=10)
        assert all(f.factor != "fast_tracked" for f in factors)

    def test_rubber_stamp_only(self):
        reviews = [
            FakeReview(state="APPROVED", quality_tier="rubber_stamp"),
            FakeReview(state="APPROVED", quality_tier="rubber_stamp"),
        ]
        pr = FakePR(reviews=reviews)
        factors, _ = compute_pr_risk(pr, author_merged_count=10)
        assert any(f.factor == "rubber_stamp_only" for f in factors)

    def test_rubber_stamp_not_triggered_with_mixed(self):
        reviews = [
            FakeReview(state="APPROVED", quality_tier="rubber_stamp"),
            FakeReview(state="CHANGES_REQUESTED", quality_tier="standard"),
        ]
        pr = FakePR(reviews=reviews)
        factors, _ = compute_pr_risk(pr, author_merged_count=10)
        assert all(f.factor != "rubber_stamp_only" for f in factors)

    def test_no_review_takes_precedence_over_rubber_stamp(self):
        """Merged with no APPROVED review — should be no_review, not rubber_stamp."""
        reviews = [FakeReview(state="COMMENTED", quality_tier="rubber_stamp")]
        pr = FakePR(is_merged=True, reviews=reviews)
        factors, _ = compute_pr_risk(pr, author_merged_count=10)
        assert any(f.factor == "no_review" for f in factors)
        assert all(f.factor != "rubber_stamp_only" for f in factors)

    # --- Merge speed ---

    def test_fast_tracked(self):
        pr = FakePR(is_merged=True, time_to_merge_s=3600)
        factors, _ = compute_pr_risk(pr, author_merged_count=10)
        assert any(f.factor == "fast_tracked" for f in factors)

    def test_fast_tracked_boundary(self):
        pr = FakePR(is_merged=True, time_to_merge_s=7200)
        factors, _ = compute_pr_risk(pr, author_merged_count=10)
        assert all(f.factor != "fast_tracked" for f in factors)

    def test_fast_tracked_not_merged(self):
        pr = FakePR(is_merged=False, time_to_merge_s=1000)
        factors, _ = compute_pr_risk(pr, author_merged_count=10)
        assert all(f.factor != "fast_tracked" for f in factors)

    # --- Self-merged ---

    def test_self_merged(self):
        pr = FakePR(is_self_merged=True)
        factors, _ = compute_pr_risk(pr, author_merged_count=10)
        assert any(f.factor == "self_merged" for f in factors)

    # --- Review rounds ---

    def test_high_review_rounds(self):
        pr = FakePR(review_round_count=3)
        factors, _ = compute_pr_risk(pr, author_merged_count=10)
        assert any(f.factor == "high_review_rounds" for f in factors)

    def test_review_rounds_boundary(self):
        pr = FakePR(review_round_count=2)
        factors, _ = compute_pr_risk(pr, author_merged_count=10)
        assert all(f.factor != "high_review_rounds" for f in factors)

    # --- Hotfix branch ---

    def test_hotfix_branch(self):
        pr = FakePR(head_branch="hotfix/urgent-fix")
        factors, _ = compute_pr_risk(pr, author_merged_count=10)
        assert any(f.factor == "hotfix_branch" for f in factors)

    def test_fix_branch(self):
        pr = FakePR(head_branch="fix/login-bug")
        factors, _ = compute_pr_risk(pr, author_merged_count=10)
        assert any(f.factor == "hotfix_branch" for f in factors)

    def test_feature_branch_no_hotfix(self):
        pr = FakePR(head_branch="feature/new-thing")
        factors, _ = compute_pr_risk(pr, author_merged_count=10)
        assert all(f.factor != "hotfix_branch" for f in factors)

    def test_null_branch(self):
        pr = FakePR(head_branch=None)
        factors, _ = compute_pr_risk(pr, author_merged_count=10)
        assert all(f.factor != "hotfix_branch" for f in factors)

    # --- Score capping ---

    def test_score_capped_at_1(self):
        """Many factors should still cap at 1.0."""
        reviews = [FakeReview(state="APPROVED", quality_tier="rubber_stamp")]
        pr = FakePR(
            additions=1500,
            changed_files=20,
            is_merged=True,
            time_to_merge_s=1000,
            is_self_merged=True,
            review_round_count=5,
            head_branch="hotfix/critical",
            reviews=reviews,
        )
        factors, score = compute_pr_risk(pr, author_merged_count=0)
        assert score == 1.0

    # --- Composite scenarios ---

    def test_typical_safe_pr(self):
        reviews = [FakeReview(state="APPROVED", quality_tier="thorough")]
        pr = FakePR(
            additions=200,
            changed_files=5,
            is_merged=True,
            time_to_merge_s=86400,
            reviews=reviews,
        )
        factors, score = compute_pr_risk(pr, author_merged_count=20)
        assert score == 0.0
        assert factors == []

    def test_risky_merged_pr(self):
        """Large, self-merged, fast-tracked, new contributor."""
        pr = FakePR(
            additions=800,
            is_merged=True,
            time_to_merge_s=3000,
            is_self_merged=True,
            reviews=[],
        )
        factors, score = compute_pr_risk(pr, author_merged_count=2)
        factor_names = {f.factor for f in factors}
        assert "large_pr" in factor_names
        assert "new_contributor" in factor_names
        assert "no_review" in factor_names
        assert "fast_tracked" in factor_names
        assert "self_merged" in factor_names
        assert score == pytest.approx(0.85, abs=0.01)

    def test_reviews_param_overrides_pr_reviews(self):
        """Explicit reviews param should be used instead of pr.reviews."""
        pr = FakePR(reviews=[FakeReview(state="APPROVED", quality_tier="thorough")])
        override = [FakeReview(state="APPROVED", quality_tier="rubber_stamp")]
        factors, _ = compute_pr_risk(pr, author_merged_count=10, reviews=override)
        assert any(f.factor == "rubber_stamp_only" for f in factors)
