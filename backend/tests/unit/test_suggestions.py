"""Unit tests for _suggest_category hint matching."""

from app.services.work_categories import _suggest_category


def test_suggest_bugfix():
    assert _suggest_category("bug") == "bugfix"
    assert _suggest_category("BUG") == "bugfix"
    assert _suggest_category("hotfix-urgent") == "bugfix"
    assert _suggest_category("regression") == "bugfix"
    assert _suggest_category("defect") == "bugfix"


def test_suggest_feature():
    assert _suggest_category("feature") == "feature"
    assert _suggest_category("enhancement") == "feature"
    assert _suggest_category("new-feature") == "feature"
    assert _suggest_category("story") == "feature"


def test_suggest_tech_debt():
    assert _suggest_category("refactor") == "tech_debt"
    assert _suggest_category("chore") == "tech_debt"
    assert _suggest_category("dependencies") == "tech_debt"
    assert _suggest_category("cleanup") == "tech_debt"
    assert _suggest_category("tech-debt") == "tech_debt"
    assert _suggest_category("deps") == "tech_debt"


def test_suggest_ops():
    assert _suggest_category("infrastructure") == "ops"
    assert _suggest_category("deploy") == "ops"
    assert _suggest_category("documentation") == "ops"
    assert _suggest_category("devops") == "ops"
    assert _suggest_category("ci/cd") == "ops"
    assert _suggest_category("pipeline") == "ops"


def test_suggest_unknown():
    assert _suggest_category("priority-high") == "unknown"
    assert _suggest_category("wontfix") == "unknown"
    assert _suggest_category("good first issue") == "unknown"
    assert _suggest_category("help wanted") == "unknown"
    assert _suggest_category("Epic") == "unknown"
