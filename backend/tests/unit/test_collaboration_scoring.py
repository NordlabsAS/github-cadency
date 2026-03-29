"""Tests for collaboration scoring normalization and helpers."""

from app.services.enhanced_collaboration import (
    _normalize,
    _canonical_pair,
    W_REVIEW,
    W_COAUTHOR,
    W_ISSUE_COMMENT,
    W_MENTION,
    W_CO_ASSIGNED,
)


def test_weights_sum_to_one():
    total = W_REVIEW + W_COAUTHOR + W_ISSUE_COMMENT + W_MENTION + W_CO_ASSIGNED
    assert abs(total - 1.0) < 1e-9


def test_normalize_zero():
    assert _normalize(0, 20) == 0.0


def test_normalize_at_cap():
    assert _normalize(20, 20) == 1.0


def test_normalize_above_cap():
    assert _normalize(50, 20) == 1.0


def test_normalize_below_cap():
    result = _normalize(10, 20)
    assert abs(result - 0.5) < 1e-9


def test_normalize_zero_cap():
    assert _normalize(5, 0) == 0.0


def test_canonical_pair_ordered():
    assert _canonical_pair(3, 1) == (1, 3)
    assert _canonical_pair(1, 3) == (1, 3)


def test_canonical_pair_same():
    assert _canonical_pair(5, 5) == (5, 5)
