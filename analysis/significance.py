"""Statistical significance analysis for evaluation results.

Provides bootstrap confidence intervals and paired comparison tests.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import numpy as np


def bootstrap_ci(
    scores: list[float],
    n_bootstrap: int = 10000,
    ci: float = 0.95,
    seed: int | None = 42,
) -> tuple[float, float, float]:
    """Compute bootstrap confidence interval for a metric.

    Args:
        scores: List of per-example scores.
        n_bootstrap: Number of bootstrap samples.
        ci: Confidence level (e.g., 0.95 for 95% CI).
        seed: Random seed for reproducibility.

    Returns:
        Tuple of (mean, lower_bound, upper_bound).
    """
    if not scores:
        return (0.0, 0.0, 0.0)

    rng = np.random.RandomState(seed)
    arr = np.array(scores)
    n = len(arr)
    mean = float(np.mean(arr))

    # Bootstrap
    boot_means = np.empty(n_bootstrap)
    for i in range(n_bootstrap):
        sample = rng.choice(arr, size=n, replace=True)
        boot_means[i] = np.mean(sample)

    alpha = 1 - ci
    lower = float(np.percentile(boot_means, 100 * alpha / 2))
    upper = float(np.percentile(boot_means, 100 * (1 - alpha / 2)))

    return (mean, lower, upper)


def paired_bootstrap_test(
    scores_a: list[float],
    scores_b: list[float],
    n_bootstrap: int = 10000,
    seed: int | None = 42,
) -> tuple[float, float, bool]:
    """Paired bootstrap test for comparing two systems.

    Tests whether system B is significantly different from system A.

    Args:
        scores_a: Per-example scores from system A.
        scores_b: Per-example scores from system B.
        n_bootstrap: Number of bootstrap iterations.
        seed: Random seed.

    Returns:
        Tuple of (observed_delta, p_value, significant_at_005).
    """
    if len(scores_a) != len(scores_b) or not scores_a:
        return (0.0, 1.0, False)

    rng = np.random.RandomState(seed)
    arr_a = np.array(scores_a)
    arr_b = np.array(scores_b)
    n = len(arr_a)

    observed_delta = float(np.mean(arr_b) - np.mean(arr_a))

    # Under the null: no difference between A and B
    # We test by bootstrap resampling the differences
    diffs = arr_b - arr_a
    count_extreme = 0

    for _ in range(n_bootstrap):
        sample = rng.choice(diffs, size=n, replace=True)
        boot_delta = np.mean(sample)
        # Two-sided test
        if abs(boot_delta) >= abs(observed_delta):
            count_extreme += 1

    p_value = count_extreme / n_bootstrap
    # Correction: the p-value should check if 0 is in the bootstrap distribution of deltas
    # More standard approach:
    boot_deltas = np.empty(n_bootstrap)
    for i in range(n_bootstrap):
        indices = rng.randint(0, n, size=n)
        boot_deltas[i] = np.mean(arr_b[indices]) - np.mean(arr_a[indices])

    # Two-sided: what fraction of bootstrap deltas have sign opposite to observed?
    if observed_delta > 0:
        p_value = float(np.mean(boot_deltas <= 0))
    elif observed_delta < 0:
        p_value = float(np.mean(boot_deltas >= 0))
    else:
        p_value = 1.0

    # Convert to two-sided
    p_value = min(2 * p_value, 1.0)

    return (observed_delta, p_value, p_value < 0.05)


@dataclass
class ComparisonReport:
    """Report comparing two evaluation runs."""

    eval_name: str
    model_a: str
    model_b: str
    metrics: dict[str, dict[str, Any]] = field(default_factory=dict)

    def to_markdown(self) -> str:
        lines = [
            f"# Comparison: {self.model_a} vs {self.model_b}",
            f"**Eval**: {self.eval_name}",
            "",
            "| Metric | {a} | {b} | Delta | CI | p-value | Sig. |".format(
                a=self.model_a[:20], b=self.model_b[:20]
            ),
            "|--------|------|------|-------|----|---------|----- |",
        ]

        for metric, info in self.metrics.items():
            sig = "***" if info.get("significant", False) else ""
            ci = info.get("ci", (0, 0))
            lines.append(
                f"| {metric} | {info['mean_a']:.4f} | {info['mean_b']:.4f} | "
                f"{info['delta']:+.4f} | [{ci[0]:+.4f}, {ci[1]:+.4f}] | "
                f"{info.get('p_value', 'N/A'):.4f} | {sig} |"
            )

        return "\n".join(lines)

    def to_json(self) -> dict:
        return {
            "eval_name": self.eval_name,
            "model_a": self.model_a,
            "model_b": self.model_b,
            "metrics": self.metrics,
        }


def compare_runs(result_a, result_b) -> ComparisonReport:
    """Compare two Result objects with statistical tests.

    Args:
        result_a: Baseline result.
        result_b: Comparison result.

    Returns:
        ComparisonReport with per-metric deltas, CIs, and significance.
    """
    report = ComparisonReport(
        eval_name=result_a.eval_name,
        model_a=result_a.model_id,
        model_b=result_b.model_id,
    )

    all_metrics = set(result_a.aggregate_metrics.keys()) | set(result_b.aggregate_metrics.keys())

    for metric in sorted(all_metrics):
        val_a = result_a.aggregate_metrics.get(metric, 0.0)
        val_b = result_b.aggregate_metrics.get(metric, 0.0)

        # Extract per-example scores for this metric
        scores_a = [e.scores.get(metric, float(e.passed)) for e in result_a.examples]
        scores_b = [e.scores.get(metric, float(e.passed)) for e in result_b.examples]

        # Bootstrap CI on the delta
        if len(scores_a) == len(scores_b) and scores_a:
            deltas = [b - a for a, b in zip(scores_a, scores_b)]
            _, ci_lower, ci_upper = bootstrap_ci(deltas)
            delta_val, p_val, sig = paired_bootstrap_test(scores_a, scores_b)
        else:
            ci_lower, ci_upper = 0.0, 0.0
            delta_val = val_b - val_a
            p_val = 1.0
            sig = False

        report.metrics[metric] = {
            "mean_a": val_a,
            "mean_b": val_b,
            "delta": delta_val,
            "ci": (ci_lower, ci_upper),
            "p_value": p_val,
            "significant": sig,
        }

    return report
