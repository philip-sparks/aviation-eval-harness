"""Regression evaluation: cross-model and cross-version comparison.

Produces diff reports showing score changes with statistical significance.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

from evals.base import Eval, Result, ExampleResult


@dataclass
class RegressionReport:
    """Report comparing two evaluation runs."""

    model_a: str
    model_b: str
    eval_name: str
    metric_deltas: dict[str, dict[str, Any]]
    regressions: list[dict]     # cases that passed in A but fail in B
    improvements: list[dict]    # cases that failed in A but pass in B
    unchanged: int

    def to_markdown(self) -> str:
        lines = [
            f"# Regression Report: {self.eval_name}",
            "",
            f"**Model A**: {self.model_a}",
            f"**Model B**: {self.model_b}",
            "",
            "## Metric Deltas",
            "",
            "| Metric | Model A | Model B | Delta | Significant |",
            "|--------|---------|---------|-------|-------------|",
        ]

        for metric, info in self.metric_deltas.items():
            sig = "Yes" if info.get("significant", False) else "No"
            lines.append(
                f"| {metric} | {info['value_a']:.4f} | {info['value_b']:.4f} | "
                f"{info['delta']:+.4f} | {sig} |"
            )

        lines.extend([
            "",
            f"## Summary",
            "",
            f"- **Regressions**: {len(self.regressions)} cases",
            f"- **Improvements**: {len(self.improvements)} cases",
            f"- **Unchanged**: {self.unchanged} cases",
        ])

        if self.regressions:
            lines.extend(["", "## Regressions (passed in A, fail in B)", ""])
            for reg in self.regressions[:10]:
                lines.append(f"- **{reg['example_id']}**: {reg.get('reason', 'score decreased')}")

        if self.improvements:
            lines.extend(["", "## Improvements (failed in A, pass in B)", ""])
            for imp in self.improvements[:10]:
                lines.append(f"- **{imp['example_id']}**: {imp.get('reason', 'score increased')}")

        return "\n".join(lines)

    def to_json(self) -> dict:
        return {
            "model_a": self.model_a,
            "model_b": self.model_b,
            "eval_name": self.eval_name,
            "metric_deltas": self.metric_deltas,
            "regressions": self.regressions,
            "improvements": self.improvements,
            "unchanged": self.unchanged,
        }


class RegressionEval(Eval):
    """Regression evaluation comparing two result sets."""

    def __init__(self):
        super().__init__(name="regression")

    def run(self, model, dataset: list[dict] | None = None) -> Result:
        raise NotImplementedError(
            "RegressionEval.run() is not used directly. "
            "Use compare() to compare two Result objects."
        )

    def run_single(self, model, example: dict) -> ExampleResult:
        raise NotImplementedError(
            "RegressionEval.run_single() is not used directly. "
            "Use compare() to compare two Result objects."
        )

    def compare(
        self,
        result_a: Result,
        result_b: Result,
        significance_test: bool = True,
    ) -> RegressionReport:
        """Compare two evaluation results and produce a regression report.

        Args:
            result_a: Baseline result (typically the earlier/reference run).
            result_b: New result to compare against baseline.
            significance_test: Whether to run paired bootstrap test.

        Returns:
            RegressionReport with deltas, regressions, and improvements.
        """
        # Compute metric deltas
        metric_deltas = {}
        all_metrics = set(result_a.aggregate_metrics.keys()) | set(result_b.aggregate_metrics.keys())

        for metric in all_metrics:
            val_a = result_a.aggregate_metrics.get(metric, 0.0)
            val_b = result_b.aggregate_metrics.get(metric, 0.0)
            delta = val_b - val_a

            info = {
                "value_a": val_a,
                "value_b": val_b,
                "delta": delta,
                "significant": False,
                "p_value": None,
            }

            # Run significance test if requested
            if significance_test:
                scores_a = self._extract_metric_scores(result_a, metric)
                scores_b = self._extract_metric_scores(result_b, metric)
                if scores_a and scores_b and len(scores_a) == len(scores_b):
                    try:
                        from analysis.significance import paired_bootstrap_test
                        _, p_val, significant = paired_bootstrap_test(scores_a, scores_b)
                        info["p_value"] = p_val
                        info["significant"] = significant
                    except (ImportError, Exception):
                        pass

            metric_deltas[metric] = info

        # Find per-example regressions and improvements
        examples_a = {e.example_id: e for e in result_a.examples}
        examples_b = {e.example_id: e for e in result_b.examples}

        regressions = []
        improvements = []
        unchanged = 0

        for eid in set(examples_a.keys()) & set(examples_b.keys()):
            ex_a = examples_a[eid]
            ex_b = examples_b[eid]

            if ex_a.passed and not ex_b.passed:
                regressions.append({
                    "example_id": eid,
                    "reason": "Passed in A, failed in B",
                    "scores_a": ex_a.scores,
                    "scores_b": ex_b.scores,
                })
            elif not ex_a.passed and ex_b.passed:
                improvements.append({
                    "example_id": eid,
                    "reason": "Failed in A, passed in B",
                    "scores_a": ex_a.scores,
                    "scores_b": ex_b.scores,
                })
            else:
                unchanged += 1

        return RegressionReport(
            model_a=result_a.model_id,
            model_b=result_b.model_id,
            eval_name=result_a.eval_name,
            metric_deltas=metric_deltas,
            regressions=regressions,
            improvements=improvements,
            unchanged=unchanged,
        )

    @staticmethod
    def _extract_metric_scores(result: Result, metric: str) -> list[float]:
        """Extract per-example scores for a given metric."""
        scores = []
        for ex in result.examples:
            if metric in ex.scores:
                scores.append(ex.scores[metric])
            elif ex.passed:
                scores.append(1.0)
            else:
                scores.append(0.0)
        return scores
