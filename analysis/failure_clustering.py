"""Failure clustering: embed and cluster failed examples to identify failure modes."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import numpy as np


@dataclass
class FailureCluster:
    """A cluster of similar failure cases."""

    cluster_id: int
    size: int
    centroid_example: dict
    theme_description: str
    examples: list[dict] = field(default_factory=list)


def cluster_failures(
    failed_examples: list,
    n_clusters: int = 5,
    use_embeddings: bool = True,
) -> list[FailureCluster]:
    """Cluster failed examples to identify failure modes.

    Args:
        failed_examples: List of ExampleResult objects (or dicts).
        n_clusters: Target number of clusters.
        use_embeddings: If True, use sentence-transformers for embeddings.
            If False, use TF-IDF (faster, no GPU needed).

    Returns:
        List of FailureCluster objects.
    """
    if not failed_examples:
        return []

    n_clusters = min(n_clusters, len(failed_examples))
    if n_clusters < 2:
        # Not enough for clustering
        ex = failed_examples[0]
        text = _get_text(ex)
        return [FailureCluster(
            cluster_id=0,
            size=len(failed_examples),
            centroid_example=_to_dict(ex),
            theme_description=f"All failures ({len(failed_examples)} cases)",
            examples=[_to_dict(e) for e in failed_examples],
        )]

    # Get text representations
    texts = [_get_text(ex) for ex in failed_examples]

    # Get embeddings
    if use_embeddings:
        try:
            embeddings = _get_sentence_embeddings(texts)
        except (ImportError, Exception):
            embeddings = _get_tfidf_embeddings(texts)
    else:
        embeddings = _get_tfidf_embeddings(texts)

    # Cluster
    from sklearn.cluster import KMeans

    kmeans = KMeans(n_clusters=n_clusters, random_state=42, n_init=10)
    labels = kmeans.fit_predict(embeddings)

    # Build clusters
    clusters = []
    for cluster_id in range(n_clusters):
        mask = labels == cluster_id
        cluster_indices = np.where(mask)[0]

        if len(cluster_indices) == 0:
            continue

        cluster_examples = [failed_examples[i] for i in cluster_indices]

        # Find centroid example (closest to cluster center)
        center = kmeans.cluster_centers_[cluster_id]
        distances = np.linalg.norm(embeddings[cluster_indices] - center, axis=1)
        centroid_idx = cluster_indices[np.argmin(distances)]

        theme = _describe_cluster(cluster_examples)

        clusters.append(FailureCluster(
            cluster_id=cluster_id,
            size=len(cluster_examples),
            centroid_example=_to_dict(failed_examples[centroid_idx]),
            theme_description=theme,
            examples=[_to_dict(e) for e in cluster_examples],
        ))

    # Sort by size descending
    clusters.sort(key=lambda c: c.size, reverse=True)
    return clusters


def generate_failure_report(clusters: list[FailureCluster]) -> str:
    """Generate a markdown report from failure clusters.

    Args:
        clusters: List of FailureCluster objects.

    Returns:
        Markdown-formatted failure analysis report.
    """
    total = sum(c.size for c in clusters)
    lines = [
        "# Failure Analysis Report",
        "",
        f"**Total failures analyzed**: {total}",
        f"**Clusters identified**: {len(clusters)}",
        "",
    ]

    for cluster in clusters:
        pct = cluster.size / total * 100 if total > 0 else 0
        lines.extend([
            f"## Cluster {cluster.cluster_id} (N={cluster.size}, {pct:.0f}%)",
            "",
            f"**Theme**: {cluster.theme_description}",
            "",
            "### Representative Example",
            "",
        ])

        centroid = cluster.centroid_example
        if "input" in centroid:
            inp = centroid["input"]
            if isinstance(inp, dict):
                query = inp.get("query", inp.get("base_prompt", str(inp)[:200]))
            else:
                query = str(inp)[:200]
            lines.append(f"**Input**: {query}")

        if "output" in centroid:
            lines.append(f"**Output** (truncated): {str(centroid['output'])[:300]}")

        if "scores" in centroid:
            lines.append(f"**Scores**: {centroid['scores']}")

        lines.append("")

        # Show a few more examples
        if cluster.size > 1:
            lines.append("### Other examples in this cluster")
            lines.append("")
            for ex in cluster.examples[1:4]:
                ex_id = ex.get("example_id", "unknown")
                lines.append(f"- {ex_id}")
            if cluster.size > 4:
                lines.append(f"- ... and {cluster.size - 4} more")
            lines.append("")

    return "\n".join(lines)


def _get_text(example) -> str:
    """Extract text representation from an example for embedding."""
    if hasattr(example, "input") and hasattr(example, "output"):
        inp = example.input
        if isinstance(inp, dict):
            input_text = inp.get("query", inp.get("base_prompt", str(inp)))
        else:
            input_text = str(inp)
        return f"{input_text} {example.output}"

    if isinstance(example, dict):
        inp = example.get("input", "")
        out = example.get("output", "")
        if isinstance(inp, dict):
            inp = inp.get("query", str(inp))
        return f"{inp} {out}"

    return str(example)


def _to_dict(example) -> dict:
    """Convert example to dict if needed."""
    if hasattr(example, "to_dict"):
        return example.to_dict()
    if isinstance(example, dict):
        return example
    return {"text": str(example)}


def _describe_cluster(examples: list) -> str:
    """Generate a brief description of what unites a cluster."""
    # Simple heuristic: look for common keywords in inputs/outputs
    texts = [_get_text(ex).lower() for ex in examples]
    all_text = " ".join(texts)

    patterns = [
        ("altitude", "Failures related to altitude or vertical parameters"),
        ("runway", "Failures related to runway identification or operations"),
        ("tcas", "Failures related to TCAS/traffic events"),
        ("weather", "Failures related to weather interpretation"),
        ("metar", "Failures related to METAR/weather data"),
        ("approach", "Failures related to approach procedures"),
        ("go-around", "Failures related to go-around scenarios"),
        ("airport", "Failures related to airport identification"),
        ("tool", "Failures related to tool selection or usage"),
        ("speed", "Failures related to speed/performance parameters"),
    ]

    for keyword, description in patterns:
        count = all_text.count(keyword)
        if count >= len(examples) * 0.5:
            return description

    return f"Mixed failure mode ({len(examples)} cases)"


def _get_sentence_embeddings(texts: list[str]) -> np.ndarray:
    """Get embeddings using sentence-transformers."""
    from sentence_transformers import SentenceTransformer
    model = SentenceTransformer("all-MiniLM-L6-v2")
    return model.encode(texts, show_progress_bar=False)


def _get_tfidf_embeddings(texts: list[str]) -> np.ndarray:
    """Get TF-IDF based embeddings (fallback, no model needed)."""
    from sklearn.feature_extraction.text import TfidfVectorizer
    vectorizer = TfidfVectorizer(max_features=500, stop_words="english")
    return vectorizer.fit_transform(texts).toarray()
