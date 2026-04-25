"""Robustness evaluation: measures score degradation under prompt perturbations."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any

from evals.base import Eval, Result, ExampleResult
from evals.robustness.perturbations import apply_perturbation
from graders.rule_based import ContainsGrader, SemanticEquivalenceGrader


SYSTEM_PROMPT = (
    "You are an aviation safety analyst. Provide a factual analysis "
    "based on the information given."
)

DEFAULT_DATASET = Path(__file__).parent.parent.parent / "datasets" / "adversarial_prompts.jsonl"


class RobustnessEval(Eval):
    """Robustness evaluation.

    Runs each base prompt to get a baseline score, then runs perturbation
    variants and measures score degradation.

    Metrics:
    - mean_degradation: average score drop across perturbations
    - max_degradation: worst-case score drop
    - perturbation_type_breakdown: degradation by perturbation category
    """

    def __init__(self, dataset_path: Path | str | None = None):
        super().__init__(name="robustness")
        self.dataset_path = Path(dataset_path) if dataset_path else DEFAULT_DATASET
        self.grader = SemanticEquivalenceGrader()

    def run(self, model, dataset: list[dict] | None = None) -> Result:
        if dataset is None:
            dataset = self.load_dataset(self.dataset_path)

        examples = [self.run_single(model, case) for case in dataset]

        n = len(examples)
        if n == 0:
            return Result(
                eval_name=self.name, model_id=model.model_id,
                timestamp=datetime.now(), examples=[], aggregate_metrics={},
                confidence_intervals={}, run_config={},
            )

        degradations = [e.scores.get("degradation", 0) for e in examples]

        # Breakdown by perturbation type
        type_degradations: dict[str, list[float]] = {}
        for e in examples:
            ptype = e.input.get("perturbation_type", "unknown")
            type_degradations.setdefault(ptype, []).append(e.scores.get("degradation", 0))

        breakdown = {
            ptype: sum(vals) / len(vals)
            for ptype, vals in type_degradations.items()
        }

        aggregate = {
            "mean_degradation": sum(degradations) / n,
            "max_degradation": max(degradations) if degradations else 0.0,
            "robustness_score": 1.0 - (sum(degradations) / n),
            "pass_rate": sum(1 for e in examples if e.passed) / n,
            **{f"degradation_{k}": v for k, v in breakdown.items()},
        }

        return Result(
            eval_name=self.name, model_id=model.model_id,
            timestamp=datetime.now(), examples=examples,
            aggregate_metrics=aggregate, confidence_intervals={},
            run_config={"dataset": str(self.dataset_path)},
        )

    def run_single(self, model, example: dict) -> ExampleResult:
        base_prompt = example.get("base_prompt", "")
        perturbed_prompt = example.get("perturbed_prompt", "")
        perturbation_type = example.get("perturbation_type", "unknown")
        expected_facts = example.get("baseline_expected_facts", [])

        # Get baseline response
        baseline_response = model.generate(base_prompt, system_prompt=SYSTEM_PROMPT)
        baseline_result = self.grader.grade(
            baseline_response.text, {"expected_facts": expected_facts}
        )

        # Get perturbed response
        perturbed_response = model.generate(perturbed_prompt, system_prompt=SYSTEM_PROMPT)
        perturbed_result = self.grader.grade(
            perturbed_response.text, {"expected_facts": expected_facts}
        )

        # Compute degradation
        degradation = max(0.0, baseline_result.score - perturbed_result.score)

        scores = {
            "baseline_score": baseline_result.score,
            "perturbed_score": perturbed_result.score,
            "degradation": degradation,
        }

        # Pass if degradation is minimal (< 0.2)
        passed = degradation < 0.2

        return ExampleResult(
            example_id=example.get("case_id", ""),
            input={
                "base_prompt": base_prompt[:200],
                "perturbed_prompt": perturbed_prompt[:200],
                "perturbation_type": perturbation_type,
            },
            output=perturbed_response.text,
            scores=scores,
            traces=[
                {"baseline": baseline_response.text[:500]},
                {"perturbed": perturbed_response.text[:500]},
            ],
            grader_results={
                "baseline": baseline_result.details,
                "perturbed": perturbed_result.details,
            },
            passed=passed,
        )
