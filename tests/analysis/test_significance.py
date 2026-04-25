"""Tests for analysis/significance.py — bootstrap CI and paired tests."""

import pytest

from analysis.significance import bootstrap_ci, paired_bootstrap_test


# ---------------------------------------------------------------------------
# bootstrap_ci
# ---------------------------------------------------------------------------

class TestBootstrapCI:
    def test_all_ones_ci_is_one(self):
        """Constant scores of 1.0 should give CI of [1.0, 1.0]."""
        mean, lower, upper = bootstrap_ci([1.0] * 100)
        assert mean == pytest.approx(1.0)
        assert lower == pytest.approx(1.0)
        assert upper == pytest.approx(1.0)

    def test_all_zeros_ci_is_zero(self):
        mean, lower, upper = bootstrap_ci([0.0] * 100)
        assert mean == pytest.approx(0.0)
        assert lower == pytest.approx(0.0)
        assert upper == pytest.approx(0.0)

    def test_ci_contains_mean(self):
        """The confidence interval should contain the sample mean."""
        scores = [0.1, 0.3, 0.5, 0.7, 0.9, 0.4, 0.6, 0.8, 0.2, 0.5]
        mean, lower, upper = bootstrap_ci(scores, seed=42)
        assert lower <= mean <= upper

    def test_wider_ci_with_high_variance(self):
        """High-variance data should produce a wider CI than low-variance data."""
        low_var = [0.5, 0.5, 0.5, 0.5, 0.5, 0.5, 0.5, 0.5, 0.5, 0.5]
        high_var = [0.0, 1.0, 0.0, 1.0, 0.0, 1.0, 0.0, 1.0, 0.0, 1.0]

        _, low_l, low_u = bootstrap_ci(low_var, seed=42)
        _, high_l, high_u = bootstrap_ci(high_var, seed=42)

        low_width = low_u - low_l
        high_width = high_u - high_l
        assert high_width > low_width

    def test_empty_scores(self):
        mean, lower, upper = bootstrap_ci([])
        assert mean == 0.0
        assert lower == 0.0
        assert upper == 0.0


# ---------------------------------------------------------------------------
# paired_bootstrap_test
# ---------------------------------------------------------------------------

class TestPairedBootstrapTest:
    def test_detects_significant_difference(self):
        """Clearly different score sets should be detected as significant."""
        scores_a = [0.1, 0.2, 0.1, 0.15, 0.2, 0.1, 0.15, 0.2, 0.1, 0.15,
                     0.1, 0.2, 0.1, 0.15, 0.2, 0.1, 0.15, 0.2, 0.1, 0.15]
        scores_b = [0.9, 0.85, 0.9, 0.95, 0.9, 0.85, 0.9, 0.95, 0.9, 0.85,
                     0.9, 0.85, 0.9, 0.95, 0.9, 0.85, 0.9, 0.95, 0.9, 0.85]

        delta, p_value, significant = paired_bootstrap_test(
            scores_a, scores_b, seed=42
        )
        assert delta > 0  # B is better
        assert p_value < 0.05
        assert significant is True

    def test_non_significant_for_similar(self):
        """Very similar score sets should NOT be significant."""
        scores_a = [0.50, 0.51, 0.49, 0.50, 0.52, 0.48, 0.50, 0.51, 0.49, 0.50]
        scores_b = [0.51, 0.50, 0.50, 0.49, 0.51, 0.49, 0.50, 0.50, 0.51, 0.49]

        delta, p_value, significant = paired_bootstrap_test(
            scores_a, scores_b, seed=42
        )
        assert abs(delta) < 0.05
        assert significant is False

    def test_mismatched_lengths(self):
        delta, p_value, significant = paired_bootstrap_test(
            [0.5, 0.6], [0.7], seed=42
        )
        assert delta == 0.0
        assert p_value == 1.0
        assert significant is False

    def test_empty_scores(self):
        delta, p_value, significant = paired_bootstrap_test([], [], seed=42)
        assert significant is False
