"""Unit tests for sprint stats computations."""

import pytest

from app.services.sprint_stats import _pearson_correlation


class TestPearsonCorrelation:
    def test_perfect_positive(self):
        result = _pearson_correlation([1, 2, 3, 4, 5], [2, 4, 6, 8, 10])
        assert result == 1.0

    def test_perfect_negative(self):
        result = _pearson_correlation([1, 2, 3, 4, 5], [10, 8, 6, 4, 2])
        assert result == -1.0

    def test_no_correlation(self):
        result = _pearson_correlation([1, 2, 3, 4, 5], [5, 1, 5, 1, 5])
        assert result is not None
        assert abs(result) < 0.5

    def test_too_few_points(self):
        assert _pearson_correlation([1, 2], [3, 4]) is None

    def test_constant_x(self):
        assert _pearson_correlation([5, 5, 5], [1, 2, 3]) is None

    def test_constant_y(self):
        assert _pearson_correlation([1, 2, 3], [5, 5, 5]) is None
