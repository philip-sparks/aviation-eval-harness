"""Tests for analysis/failure_clustering.py — failure mode clustering."""

from unittest.mock import patch, MagicMock

import pytest
import numpy as np

from analysis.failure_clustering import (
    FailureCluster,
    cluster_failures,
    generate_failure_report,
    _get_text,
    _to_dict,
    _describe_cluster,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_failure_dict(example_id, input_text, output_text, scores=None):
    return {
        "example_id": example_id,
        "input": {"query": input_text},
        "output": output_text,
        "scores": scores or {"contains": 0.0},
        "passed": False,
    }


# ---------------------------------------------------------------------------
# cluster_failures
# ---------------------------------------------------------------------------

class TestClusterFailures:
    def test_empty_list_returns_empty(self):
        assert cluster_failures([]) == []

    def test_single_failure_returns_one_cluster(self):
        failures = [_make_failure_dict("ex1", "altitude query", "wrong answer")]
        clusters = cluster_failures(failures, n_clusters=3)
        assert len(clusters) == 1
        assert clusters[0].size == 1
        assert clusters[0].cluster_id == 0

    @patch("analysis.failure_clustering._get_tfidf_embeddings")
    @patch("sklearn.cluster.KMeans")
    def test_groups_similar_failures(self, MockKMeans, mock_tfidf):
        """Failures with similar text should end up in the same cluster."""
        failures = [
            _make_failure_dict("ex1", "altitude at KDFW", "altitude was wrong"),
            _make_failure_dict("ex2", "altitude at KORD", "altitude error"),
            _make_failure_dict("ex3", "runway at KLAX", "wrong runway"),
            _make_failure_dict("ex4", "runway at KSFO", "runway incorrect"),
        ]

        # Mock TF-IDF to return embeddings where first two and last two are close
        mock_embeddings = np.array([
            [1.0, 0.0],
            [0.9, 0.1],
            [0.0, 1.0],
            [0.1, 0.9],
        ])
        mock_tfidf.return_value = mock_embeddings

        # Mock KMeans to assign first two to cluster 0, last two to cluster 1
        mock_kmeans_instance = MagicMock()
        mock_kmeans_instance.fit_predict.return_value = np.array([0, 0, 1, 1])
        mock_kmeans_instance.cluster_centers_ = np.array([
            [0.95, 0.05],
            [0.05, 0.95],
        ])
        MockKMeans.return_value = mock_kmeans_instance

        clusters = cluster_failures(failures, n_clusters=2, use_embeddings=False)
        assert len(clusters) == 2

        # Each cluster should have 2 examples
        sizes = sorted([c.size for c in clusters])
        assert sizes == [2, 2]

    def test_n_clusters_clamped_to_sample_size(self):
        """n_clusters should be clamped to number of examples."""
        failures = [
            _make_failure_dict("ex1", "q1", "a1"),
        ]
        clusters = cluster_failures(failures, n_clusters=10)
        # With 1 example, n_clusters < 2, so returns single cluster
        assert len(clusters) == 1


# ---------------------------------------------------------------------------
# generate_failure_report
# ---------------------------------------------------------------------------

class TestGenerateFailureReport:
    def test_produces_markdown_with_cluster_descriptions(self):
        clusters = [
            FailureCluster(
                cluster_id=0,
                size=3,
                centroid_example={
                    "example_id": "ex-1",
                    "input": {"query": "What altitude?"},
                    "output": "The altitude was incorrect.",
                    "scores": {"contains": 0.0},
                },
                theme_description="Failures related to altitude or vertical parameters",
                examples=[
                    {"example_id": "ex-1", "input": {"query": "q1"}, "output": "o1"},
                    {"example_id": "ex-2", "input": {"query": "q2"}, "output": "o2"},
                    {"example_id": "ex-3", "input": {"query": "q3"}, "output": "o3"},
                ],
            ),
            FailureCluster(
                cluster_id=1,
                size=2,
                centroid_example={
                    "example_id": "ex-4",
                    "input": {"query": "Which runway?"},
                    "output": "Wrong runway identified.",
                    "scores": {"contains": 0.0},
                },
                theme_description="Failures related to runway identification",
                examples=[
                    {"example_id": "ex-4"},
                    {"example_id": "ex-5"},
                ],
            ),
        ]

        report = generate_failure_report(clusters)

        assert "# Failure Analysis Report" in report
        assert "**Total failures analyzed**: 5" in report
        assert "**Clusters identified**: 2" in report
        assert "## Cluster 0 (N=3, 60%)" in report
        assert "## Cluster 1 (N=2, 40%)" in report
        assert "altitude" in report.lower()
        assert "runway" in report.lower()
        assert "### Representative Example" in report

    def test_empty_clusters(self):
        report = generate_failure_report([])
        assert "# Failure Analysis Report" in report
        assert "**Total failures analyzed**: 0" in report


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

class TestHelpers:
    def test_get_text_from_dict(self):
        example = {"input": {"query": "What happened?"}, "output": "A go-around."}
        text = _get_text(example)
        assert "What happened?" in text
        assert "go-around" in text

    def test_get_text_from_object(self):
        class MockExample:
            input = {"query": "altitude question"}
            output = "15000 feet"

        text = _get_text(MockExample())
        assert "altitude" in text
        assert "15000" in text

    def test_to_dict_from_dict(self):
        d = {"example_id": "ex1"}
        assert _to_dict(d) == d

    def test_to_dict_from_object_with_to_dict(self):
        class MockExample:
            def to_dict(self):
                return {"example_id": "ex1"}

        result = _to_dict(MockExample())
        assert result == {"example_id": "ex1"}

    def test_describe_cluster_altitude_theme(self):
        examples = [
            {"input": {"query": "altitude"}, "output": "altitude was wrong"},
            {"input": {"query": "altitude check"}, "output": "altitude error"},
        ]
        desc = _describe_cluster(examples)
        assert "altitude" in desc.lower()

    def test_describe_cluster_mixed_theme(self):
        examples = [
            {"input": "abc", "output": "xyz"},
            {"input": "def", "output": "uvw"},
        ]
        desc = _describe_cluster(examples)
        assert "Mixed failure mode" in desc
