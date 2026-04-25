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


def _output_similarity(text_a: str, text_b: str) -> float:
    """Compute similarity between two outputs using token overlap (Jaccard).

    Returns a value between 0 and 1 where 1 means identical content.
    Uses word-level Jaccard similarity — fast, no external dependencies.
    """
    words_a = set(text_a.lower().split())
    words_b = set(text_b.lower().split())
    if not words_a and not words_b:
        return 1.0
    if not words_a or not words_b:
        return 0.0
    intersection = words_a & words_b
    union = words_a | words_b
    return len(intersection) / len(union)


class RobustnessEval(Eval):
    """Robustness evaluation.

    Runs each base prompt to get a baseline score, then runs perturbation
    variants and measures score degradation.

    Scores each pair on two dimensions:
    - output_similarity: Jaccard word overlap between baseline and perturbed output
    - fact_coverage: SemanticEquivalenceGrader score (when expected facts exist)

    Metrics:
    - mean_degradation: average drop in fact coverage
    - max_degradation: worst-case fact coverage drop
    - mean_similarity: average output similarity (higher = more robust)
    - perturbation_type_breakdown: per-type similarity and degradation
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
        similarities = [e.scores.get("output_similarity", 0) for e in examples]

        # Breakdown by perturbation type
        type_stats: dict[str, dict[str, list[float]]] = {}
        for e in examples:
            ptype = e.input.get("perturbation_type", "unknown")
            bucket = type_stats.setdefault(ptype, {"degradation": [], "similarity": []})
            bucket["degradation"].append(e.scores.get("degradation", 0))
            bucket["similarity"].append(e.scores.get("output_similarity", 0))

        aggregate = {
            "mean_degradation": sum(degradations) / n,
            "max_degradation": max(degradations) if degradations else 0.0,
            "mean_similarity": sum(similarities) / n,
            "robustness_score": sum(similarities) / n,
            "pass_rate": sum(1 for e in examples if e.passed) / n,
            **{
                f"similarity_{k}": sum(v["similarity"]) / len(v["similarity"])
                for k, v in type_stats.items()
            },
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

        # Compute degradation (fact coverage drop)
        degradation = max(0.0, baseline_result.score - perturbed_result.score)

        # Compute output similarity (are the answers substantively the same?)
        similarity = _output_similarity(baseline_response.text, perturbed_response.text)

        scores = {
            "baseline_score": baseline_result.score,
            "perturbed_score": perturbed_result.score,
            "degradation": degradation,
            "output_similarity": similarity,
        }

        # Pass if outputs are similar (similarity >= 0.5) and no major degradation
        passed = similarity >= 0.5 and degradation < 0.2

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
