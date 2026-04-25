"""Tests for graders/human_agreement.py — inter-rater agreement metrics."""

import pytest

from graders.human_agreement import cohens_kappa, krippendorffs_alpha, disagreement_report


# ---------------------------------------------------------------------------
# Cohen's kappa
# ---------------------------------------------------------------------------

class TestCohensKappa:
    def test_perfect_agreement(self):
        labels_a = [True, True, False, False, True, False]
        labels_b = [True, True, False, False, True, False]
        kappa = cohens_kappa(labels_a, labels_b)
        assert kappa == pytest.approx(1.0)

    def test_no_agreement(self):
        """Complete disagreement with mixed marginals yields negative kappa."""
        # Swap every label so observed agreement < chance
        labels_a = [True, False, True, False, True, False]
        labels_b = [False, True, False, True, False, True]
        kappa = cohens_kappa(labels_a, labels_b)
        assert kappa < 0

    def test_random_agreement_near_zero(self):
        """Roughly random labels should produce kappa near 0."""
        # Construct labels where agreement matches chance expectation
        # 50/50 distribution for both raters, exactly half agree by coincidence
        labels_a = [True, False, True, False, True, False, True, False]
        labels_b = [True, True, False, False, True, True, False, False]
        kappa = cohens_kappa(labels_a, labels_b)
        # Should be near 0 (chance-level agreement)
        assert abs(kappa) < 0.5

    def test_multi_class_labels(self):
        """Should work with string labels, not just booleans."""
        labels_a = ["A", "B", "C", "A", "B"]
        labels_b = ["A", "B", "C", "A", "B"]
        kappa = cohens_kappa(labels_a, labels_b)
        assert kappa == pytest.approx(1.0)

    def test_empty_labels(self):
        assert cohens_kappa([], []) == 0.0

    def test_mismatched_lengths(self):
        assert cohens_kappa([True, False], [True]) == 0.0


# ---------------------------------------------------------------------------
# Krippendorff's alpha
# ---------------------------------------------------------------------------

class TestKrippendorffsAlpha:
    def test_perfect_agreement_two_raters(self):
        annotations = [
            [1, 2, 3, 1, 2],
            [1, 2, 3, 1, 2],
        ]
        alpha = krippendorffs_alpha(annotations, level="nominal")
        assert alpha == pytest.approx(1.0)

    def test_total_disagreement(self):
        """Two raters that never agree should produce alpha near -1 or very low."""
        annotations = [
            [1, 1, 1, 1],
            [2, 2, 2, 2],
        ]
        alpha = krippendorffs_alpha(annotations, level="nominal")
        assert alpha < 0

    def test_three_raters(self):
        """Should handle more than two raters."""
        annotations = [
            [1, 2, 3, 1],
            [1, 2, 3, 1],
            [1, 2, 3, 1],
        ]
        alpha = krippendorffs_alpha(annotations, level="nominal")
        assert alpha == pytest.approx(1.0)

    def test_with_missing_values(self):
        """None indicates a missing annotation."""
        annotations = [
            [1, 2, None, 1],
            [1, 2, 3, 1],
        ]
        # Should not raise
        alpha = krippendorffs_alpha(annotations, level="nominal")
        assert isinstance(alpha, float)

    def test_single_category(self):
        """When only one category is used, alpha should be 1.0."""
        annotations = [
            [1, 1, 1],
            [1, 1, 1],
        ]
        alpha = krippendorffs_alpha(annotations, level="nominal")
        assert alpha == pytest.approx(1.0)

    def test_too_few_raters(self):
        assert krippendorffs_alpha([[1, 2, 3]]) == 0.0
        assert krippendorffs_alpha([]) == 0.0

    def test_mismatched_lengths_raises(self):
        with pytest.raises(ValueError, match="same length"):
            krippendorffs_alpha([[1, 2], [1, 2, 3]])

    def test_interval_level(self):
        """Interval level measurement should work with numeric data."""
        annotations = [
            [1, 2, 3, 4],
            [1, 2, 3, 4],
        ]
        alpha = krippendorffs_alpha(annotations, level="interval")
        assert alpha == pytest.approx(1.0)


# ---------------------------------------------------------------------------
# Disagreement report
# ---------------------------------------------------------------------------

class TestDisagreementReport:
    def test_produces_markdown_with_disagreements(self):
        labels_a = [True, True, False, True]
        labels_b = [True, False, False, True]
        examples = [
            {"case_id": "c1", "query": "query 1"},
            {"case_id": "c2", "query": "query 2"},
            {"case_id": "c3", "query": "query 3"},
            {"case_id": "c4", "query": "query 4"},
        ]
        report = disagreement_report(labels_a, labels_b, examples)

        assert "# Disagreement Report" in report
        assert "**Total examples**: 4" in report
        assert "**Agreements**: 3" in report
        assert "**Disagreements**: 1" in report
        assert "Cohen's kappa" in report
        assert "## Disagreement Cases" in report
        assert "### Case c2" in report
        assert "**Grader A**: True" in report
        assert "**Grader B**: False" in report

    def test_perfect_agreement_report(self):
        labels_a = [True, True, False]
        labels_b = [True, True, False]
        examples = [{"case_id": "c1"}, {"case_id": "c2"}, {"case_id": "c3"}]
        report = disagreement_report(labels_a, labels_b, examples)

        assert "perfect agreement" in report
        assert "Disagreement Cases" not in report

    def test_uses_example_id_fallback(self):
        labels_a = [True]
        labels_b = [False]
        examples = [{"example_id": "ex-99"}]
        report = disagreement_report(labels_a, labels_b, examples)
        assert "ex-99" in report
