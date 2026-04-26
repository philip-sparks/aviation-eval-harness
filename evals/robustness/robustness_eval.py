"""Robustness evaluation: measures score degradation under prompt perturbations."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any

import numpy as np

from evals.base import Eval, Result, ExampleResult
from evals.robustness.perturbations import apply_perturbation
from graders.rule_based import ContainsGrader, SemanticEquivalenceGrader


SYSTEM_PROMPT = (
    "You are an aviation safety analyst. Provide a factual analysis "
    "based on the information given."
)

DEFAULT_DATASET = Path(__file__).parent.parent.parent / "datasets" / "adversarial_prompts.jsonl"

# Lazy-loaded sentence transformer model
_EMBEDDING_MODEL = None


def _get_embedding_model():
    """Lazy-load the sentence transformer model."""
    global _EMBEDDING_MODEL
    if _EMBEDDING_MODEL is None:
        from sentence_transformers import SentenceTransformer
        _EMBEDDING_MODEL = SentenceTransformer("all-MiniLM-L6-v2")
    return _EMBEDDING_MODEL


def _jaccard_similarity(text_a: str, text_b: str) -> float:
    """Compute Jaccard word overlap between two texts.

    Returns a value between 0 and 1 where 1 means identical word sets.
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


def _embedding_similarity(text_a: str, text_b: str) -> float:
    """Compute cosine similarity between sentence embeddings.

    Uses all-MiniLM-L6-v2 to produce embeddings and computes cosine
    similarity. Returns a value between -1 and 1 where 1 means
    semantically identical.
    """
    model = _get_embedding_model()
    embeddings = model.encode([text_a, text_b], convert_to_numpy=True)
    # Cosine similarity
    a, b = embeddings[0], embeddings[1]
    dot = np.dot(a, b)
    norm = np.linalg.norm(a) * np.linalg.norm(b)
    if norm == 0:
        return 0.0
    return float(dot / norm)


class RobustnessEval(Eval):
    """Robustness evaluation.

    Runs each base prompt to get a baseline score, then runs perturbation
    variants and measures score degradation.

    Scores each pair on three dimensions:
    - jaccard_similarity: word overlap between baseline and perturbed output
    - embedding_similarity: cosine similarity of sentence embeddings
    - fact_coverage: SemanticEquivalenceGrader score (when expected facts exist)

    Metrics:
    - mean_degradation: average drop in fact coverage
    - max_degradation: worst-case fact coverage drop
    - mean_jaccard_similarity: average Jaccard word overlap
    - mean_embedding_similarity: average embedding cosine similarity
    - perturbation_type_breakdown: per-type metrics
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
        jaccard_sims = [e.scores.get("jaccard_similarity", 0) for e in examples]
        embedding_sims = [e.scores.get("embedding_similarity", 0) for e in examples]

        # Breakdown by perturbation type
        type_stats: dict[str, dict[str, list[float]]] = {}
        for e in examples:
            ptype = e.input.get("perturbation_type", "unknown")
            bucket = type_stats.setdefault(
                ptype, {"degradation": [], "jaccard": [], "embedding": []}
            )
            bucket["degradation"].append(e.scores.get("degradation", 0))
            bucket["jaccard"].append(e.scores.get("jaccard_similarity", 0))
            bucket["embedding"].append(e.scores.get("embedding_similarity", 0))

        aggregate = {
            "mean_degradation": sum(degradations) / n,
            "max_degradation": max(degradations) if degradations else 0.0,
            "mean_jaccard_similarity": sum(jaccard_sims) / n,
            "mean_embedding_similarity": sum(embedding_sims) / n,
            "mean_similarity": sum(jaccard_sims) / n,  # backward compat
            "robustness_score": sum(embedding_sims) / n,
            "pass_rate": sum(1 for e in examples if e.passed) / n,
        }

        # Per-type breakdown
        for k, v in type_stats.items():
            aggregate[f"jaccard_{k}"] = sum(v["jaccard"]) / len(v["jaccard"])
            aggregate[f"embedding_{k}"] = sum(v["embedding"]) / len(v["embedding"])
            # backward compat key
            aggregate[f"similarity_{k}"] = sum(v["jaccard"]) / len(v["jaccard"])

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

        # Compute both similarity metrics
        jaccard = _jaccard_similarity(baseline_response.text, perturbed_response.text)
        embedding = _embedding_similarity(baseline_response.text, perturbed_response.text)

        scores = {
            "baseline_score": baseline_result.score,
            "perturbed_score": perturbed_result.score,
            "degradation": degradation,
            "jaccard_similarity": jaccard,
            "embedding_similarity": embedding,
            "output_similarity": jaccard,  # backward compat
        }

        # Pass if embedding similarity is high and no major degradation
        passed = embedding >= 0.7 and degradation < 0.2

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
