"""Grounding evaluation: measures whether generated claims are supported by context.

Uses dual graders (rule-based and LLM judge) and reports agreement between them.
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any

from evals.base import Eval, Result, ExampleResult
from graders import GradeResult
from graders.rule_based import ContainsGrader, NotContainsGrader, SemanticEquivalenceGrader
from graders.llm_judge import LLMJudgeGrader, create_grounding_sub_rubrics


SYSTEM_PROMPT = (
    "You are an aviation safety analyst. Analyze the provided aviation safety data "
    "and provide a detailed, factual assessment. Base your analysis only on the "
    "information given in the source context. Do not speculate or introduce facts "
    "not present in the source material."
)

DEFAULT_DATASET = Path(__file__).parent.parent.parent / "datasets" / "grounding_cases.jsonl"


class GroundingEval(Eval):
    """Grounding evaluation with dual graders.

    Measures:
    - grounding_accuracy: fraction of expected facts found in output
    - hallucination_rate: fraction of negative facts that appear (should be 0)
    - grader_agreement_rate: agreement between rule-based and LLM judge
    """

    def __init__(
        self,
        judge_adapter=None,
        dataset_path: Path | str | None = None,
    ):
        super().__init__(name="grounding")

        # Rule-based graders
        self.contains_grader = ContainsGrader()
        self.not_contains_grader = NotContainsGrader()
        self.semantic_grader = SemanticEquivalenceGrader()

        # LLM judge grader
        self.llm_judge = LLMJudgeGrader(
            model_adapter=judge_adapter,
            sub_rubrics=create_grounding_sub_rubrics(),
            threshold=0.4,
        )

        self.dataset_path = Path(dataset_path) if dataset_path else DEFAULT_DATASET
        self.graders = [
            self.contains_grader,
            self.not_contains_grader,
            self.semantic_grader,
            self.llm_judge,
        ]

    def run(self, model, dataset: list[dict] | None = None) -> Result:
        if dataset is None:
            dataset = self.load_dataset(self.dataset_path)

        examples = []
        for case in dataset:
            example = self.run_single(model, case)
            examples.append(example)

        # Compute aggregates
        n = len(examples)
        if n == 0:
            return Result(
                eval_name=self.name, model_id=model.model_id,
                timestamp=datetime.now(), examples=[], aggregate_metrics={},
                confidence_intervals={}, run_config={},
            )

        grounding_scores = [e.scores.get("semantic_equivalence", 0) for e in examples]
        hallucination_scores = [e.scores.get("not_contains", 1) for e in examples]

        # Agreement between rule-based and LLM judge
        agreements = 0
        judged = 0
        for e in examples:
            rule_passed = e.grader_results.get("contains", {}).get("passed")
            judge_passed = e.grader_results.get("llm_judge", {}).get("passed")
            if rule_passed is not None and judge_passed is not None:
                judged += 1
                if rule_passed == judge_passed:
                    agreements += 1

        aggregate = {
            "grounding_accuracy": sum(grounding_scores) / n,
            "hallucination_rate": 1.0 - (sum(hallucination_scores) / n),
            "grader_agreement_rate": agreements / judged if judged > 0 else 0.0,
            "pass_rate": sum(1 for e in examples if e.passed) / n,
        }

        return Result(
            eval_name=self.name,
            model_id=model.model_id,
            timestamp=datetime.now(),
            examples=examples,
            aggregate_metrics=aggregate,
            confidence_intervals={},
            run_config={"dataset": str(self.dataset_path)},
        )

    def run_single(self, model, example: dict) -> ExampleResult:
        context = example.get("context", "")
        query = example.get("query", "")

        prompt = f"Source Context:\n{context}\n\nQuestion: {query}\n\nProvide a thorough analysis."
        response = model.generate(prompt, system_prompt=SYSTEM_PROMPT)
        output = response.text

        # Grade with rule-based graders
        contains_result = self.contains_grader.grade(output, example)
        not_contains_result = self.not_contains_grader.grade(output, example)
        semantic_result = self.semantic_grader.grade(output, example)

        # Grade with LLM judge (may skip if no adapter)
        judge_result = self.llm_judge.grade(output, example, {"context": context})

        scores = {
            "contains": contains_result.score,
            "not_contains": not_contains_result.score,
            "semantic_equivalence": semantic_result.score,
            "llm_judge": judge_result.score,
        }

        grader_results = {
            "contains": {"passed": contains_result.passed, **contains_result.details},
            "not_contains": {"passed": not_contains_result.passed, **not_contains_result.details},
            "semantic_equivalence": {"passed": semantic_result.passed, **semantic_result.details},
            "llm_judge": {"passed": judge_result.passed, **judge_result.details},
        }

        # Overall pass: must pass both contains and not-contains
        passed = contains_result.passed and not_contains_result.passed

        return ExampleResult(
            example_id=example.get("case_id", ""),
            input={"context": context[:200], "query": query},
            output=output,
            scores=scores,
            traces=[{"model_response": response.usage}],
            grader_results=grader_results,
            passed=passed,
        )
