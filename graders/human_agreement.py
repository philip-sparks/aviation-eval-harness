"""Inter-rater agreement analysis tooling.

Computes Cohen's kappa, Krippendorff's alpha, and produces
disagreement reports for calibrating graders against human labels.
"""

from __future__ import annotations

from typing import Any


def cohens_kappa(labels_a: list, labels_b: list) -> float:
    """Compute Cohen's kappa between two annotators.

    Works with any discrete label type (bool, int, str).

    Args:
        labels_a: Labels from annotator A.
        labels_b: Labels from annotator B.

    Returns:
        Cohen's kappa coefficient (-1 to 1). 1.0 = perfect agreement,
        0.0 = agreement expected by chance, < 0 = less than chance.
    """
    n = len(labels_a)
    if n == 0 or n != len(labels_b):
        return 0.0

    # Get all categories
    categories = sorted(set(labels_a) | set(labels_b), key=str)

    # Observed agreement
    agreements = sum(1 for a, b in zip(labels_a, labels_b) if a == b)
    p_o = agreements / n

    # Expected agreement by chance
    p_e = 0.0
    for cat in categories:
        p_a = sum(1 for a in labels_a if a == cat) / n
        p_b = sum(1 for b in labels_b if b == cat) / n
        p_e += p_a * p_b

    if p_e == 1.0:
        return 1.0

    return (p_o - p_e) / (1.0 - p_e)


def krippendorffs_alpha(annotations: list[list], level: str = "nominal") -> float:
    """Compute Krippendorff's alpha for inter-rater reliability.

    Args:
        annotations: List of annotation vectors, one per rater.
            Each vector has one value per item (None for missing).
        level: Measurement level ("nominal", "ordinal", "interval", "ratio").
            Currently implements nominal and interval.

    Returns:
        Krippendorff's alpha (-1 to 1). 1.0 = perfect reliability.
    """
    if not annotations or len(annotations) < 2:
        return 0.0

    n_items = len(annotations[0])
    n_raters = len(annotations)

    if any(len(a) != n_items for a in annotations):
        raise ValueError("All annotation vectors must have the same length")

    # Build coincidence matrix
    categories = set()
    for rater_annotations in annotations:
        for val in rater_annotations:
            if val is not None:
                categories.add(val)

    categories = sorted(categories, key=str)
    cat_to_idx = {c: i for i, c in enumerate(categories)}
    n_cats = len(categories)

    if n_cats < 2:
        return 1.0  # Only one category used

    # Coincidence matrix
    coincidence = [[0.0] * n_cats for _ in range(n_cats)]

    for item in range(n_items):
        # Get all non-None ratings for this item
        ratings = [annotations[r][item] for r in range(n_raters) if annotations[r][item] is not None]
        m = len(ratings)
        if m < 2:
            continue

        for i, r1 in enumerate(ratings):
            for j, r2 in enumerate(ratings):
                if i != j:
                    ci = cat_to_idx[r1]
                    cj = cat_to_idx[r2]
                    coincidence[ci][cj] += 1.0 / (m - 1)

    # Compute D_o (observed disagreement)
    total = sum(sum(row) for row in coincidence)
    if total == 0:
        return 0.0

    # Marginal frequencies
    n_c = [sum(coincidence[c][k] for k in range(n_cats)) for c in range(n_cats)]

    # Observed disagreement
    if level == "nominal":
        d_o = 0.0
        for c in range(n_cats):
            for k in range(n_cats):
                if c != k:
                    d_o += coincidence[c][k]
        d_o /= total

        # Expected disagreement
        d_e = 0.0
        for c in range(n_cats):
            for k in range(n_cats):
                if c != k:
                    d_e += n_c[c] * n_c[k]
        d_e /= (total * (total - 1)) if total > 1 else 1

    elif level == "interval":
        d_o = 0.0
        for c in range(n_cats):
            for k in range(n_cats):
                val_c = categories[c] if isinstance(categories[c], (int, float)) else c
                val_k = categories[k] if isinstance(categories[k], (int, float)) else k
                d_o += coincidence[c][k] * (val_c - val_k) ** 2
        d_o /= total

        d_e = 0.0
        for c in range(n_cats):
            for k in range(n_cats):
                val_c = categories[c] if isinstance(categories[c], (int, float)) else c
                val_k = categories[k] if isinstance(categories[k], (int, float)) else k
                d_e += n_c[c] * n_c[k] * (val_c - val_k) ** 2
        d_e /= (total * (total - 1)) if total > 1 else 1
    else:
        # Fall back to nominal
        return krippendorffs_alpha(annotations, level="nominal")

    if d_e == 0:
        return 1.0

    return 1.0 - (d_o / d_e)


def disagreement_report(labels_a: list, labels_b: list, examples: list[dict]) -> str:
    """Produce a markdown report listing all disagreement cases.

    Args:
        labels_a: Labels from annotator/grader A.
        labels_b: Labels from annotator/grader B.
        examples: The evaluated examples (for context).

    Returns:
        Markdown-formatted disagreement report.
    """
    n = min(len(labels_a), len(labels_b), len(examples))
    kappa = cohens_kappa(labels_a[:n], labels_b[:n])

    agreements = sum(1 for i in range(n) if labels_a[i] == labels_b[i])
    disagreements = []

    for i in range(n):
        if labels_a[i] != labels_b[i]:
            disagreements.append((i, labels_a[i], labels_b[i], examples[i]))

    lines = [
        "# Disagreement Report",
        "",
        f"**Total examples**: {n}",
        f"**Agreements**: {agreements} ({agreements/n:.1%})" if n > 0 else "**Agreements**: 0",
        f"**Disagreements**: {len(disagreements)}",
        f"**Cohen's kappa**: {kappa:.3f}",
        "",
    ]

    if disagreements:
        lines.append("## Disagreement Cases")
        lines.append("")
        for idx, label_a, label_b, example in disagreements:
            example_id = example.get("case_id", example.get("example_id", f"#{idx}"))
            lines.append(f"### Case {example_id}")
            lines.append(f"- **Grader A**: {label_a}")
            lines.append(f"- **Grader B**: {label_b}")
            query = example.get("query", example.get("input", ""))
            if isinstance(query, str) and query:
                lines.append(f"- **Query**: {query[:200]}")
            lines.append("")
    else:
        lines.append("*No disagreements found — perfect agreement.*")

    return "\n".join(lines)
