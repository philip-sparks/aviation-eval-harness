"""LLM-as-judge grader with structured rubrics and calibration.

Wraps Promptfoo's llm-rubric assertion type. Supports weighted sub-rubrics
and includes calibration tooling for computing agreement with human labels.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from typing import Any

from graders import Grader, GradeResult


@dataclass
class CalibrationReport:
    """Report from calibrating LLM judge against human labels."""

    agreement_rate: float
    cohens_kappa: float
    confusion_matrix: dict[str, dict[str, int]]
    systematic_patterns: list[str]
    n_examples: int
    judge_scores: list[float] = field(default_factory=list)
    human_scores: list[float] = field(default_factory=list)

    def to_markdown(self) -> str:
        lines = [
            "# LLM Judge Calibration Report",
            "",
            f"**Examples evaluated**: {self.n_examples}",
            f"**Agreement rate**: {self.agreement_rate:.1%}",
            f"**Cohen's kappa**: {self.cohens_kappa:.3f}",
            "",
            "## Confusion Matrix",
            "",
            "| | Judge: Pass | Judge: Fail |",
            "|---|---|---|",
        ]

        tp = self.confusion_matrix.get("pass", {}).get("pass", 0)
        fp = self.confusion_matrix.get("fail", {}).get("pass", 0)
        fn = self.confusion_matrix.get("pass", {}).get("fail", 0)
        tn = self.confusion_matrix.get("fail", {}).get("fail", 0)
        lines.append(f"| **Human: Pass** | {tp} | {fn} |")
        lines.append(f"| **Human: Fail** | {fp} | {tn} |")

        if self.systematic_patterns:
            lines.extend(["", "## Systematic Disagreement Patterns", ""])
            for pattern in self.systematic_patterns:
                lines.append(f"- {pattern}")

        return "\n".join(lines)


class LLMJudgeGrader(Grader):
    """LLM-as-judge grader with structured rubric scoring.

    Sends the rubric + model output to a judge model and parses
    a structured score on a 1-5 scale.
    """

    JUDGE_PROMPT_TEMPLATE = """You are an expert aviation safety evaluator. Grade the following model output against the rubric.

## Rubric
{rubric}

## Source Context
{context}

## Model Output
{output}

## Instructions
Score the output on a scale of 1-5:
- 5: Fully correct, all key facts present, no hallucinations
- 4: Mostly correct, minor omissions
- 3: Partially correct, some errors or missing information
- 2: Mostly incorrect or missing key information
- 1: Completely wrong or hallucinated

Respond with ONLY a JSON object:
{{"score": <1-5>, "reasoning": "<brief explanation>"}}"""

    def __init__(
        self,
        rubric: str = "",
        model_adapter=None,
        sub_rubrics: list[dict] | None = None,
        threshold: float = 0.6,
    ):
        self.rubric = rubric
        self.model_adapter = model_adapter
        self.sub_rubrics = sub_rubrics or []
        self.threshold = threshold

    def grade(self, output: str, expected: dict, context: dict | None = None) -> GradeResult:
        if self.sub_rubrics:
            return self._grade_with_sub_rubrics(output, expected, context)
        return self._grade_single(output, expected, context, self.rubric)

    def _grade_single(
        self, output: str, expected: dict, context: dict | None, rubric: str
    ) -> GradeResult:
        context = context or {}
        context_text = context.get("context", context.get("source", ""))

        prompt = self.JUDGE_PROMPT_TEMPLATE.format(
            rubric=rubric, context=context_text, output=output
        )

        if self.model_adapter is None:
            return GradeResult(
                score=0.0, passed=False, metric_name="llm_judge",
                details={"error": "No model adapter configured for judge"},
            )

        response = self.model_adapter.generate(prompt)
        return self._parse_response(response.text)

    def _grade_with_sub_rubrics(
        self, output: str, expected: dict, context: dict | None
    ) -> GradeResult:
        """Grade using weighted sub-rubrics."""
        total_weight = sum(sr["weight"] for sr in self.sub_rubrics)
        weighted_score = 0.0
        sub_results = {}

        for sr in self.sub_rubrics:
            result = self._grade_single(output, expected, context, sr["rubric"])
            normalized_score = result.score / 5.0  # Normalize 1-5 to 0-1
            weighted_score += normalized_score * (sr["weight"] / total_weight)
            sub_results[sr.get("name", sr["rubric"][:30])] = {
                "score": result.score,
                "weight": sr["weight"],
                "details": result.details,
            }

        return GradeResult(
            score=weighted_score,
            passed=weighted_score >= self.threshold,
            metric_name="llm_judge",
            details={"sub_rubrics": sub_results, "threshold": self.threshold},
        )

    def _parse_response(self, response_text: str) -> GradeResult:
        """Parse the judge's JSON response."""
        try:
            # Try to find JSON in the response
            json_match = re.search(r'\{[^}]+\}', response_text)
            if json_match:
                data = json.loads(json_match.group())
            else:
                data = json.loads(response_text)

            score = float(data.get("score", 0))
            reasoning = data.get("reasoning", "")
            normalized = score / 5.0

            return GradeResult(
                score=score,
                passed=normalized >= self.threshold,
                metric_name="llm_judge",
                details={"reasoning": reasoning, "raw_score": score, "normalized": normalized},
            )
        except (json.JSONDecodeError, ValueError, AttributeError):
            return GradeResult(
                score=0.0, passed=False, metric_name="llm_judge",
                details={"error": "Failed to parse judge response", "raw": response_text},
            )

    def calibrate(self, labeled_examples: list[dict]) -> CalibrationReport:
        """Run calibration study comparing judge scores to human labels.

        Each labeled_example should have:
            - output: str (model output to grade)
            - expected: dict (expected results)
            - context: dict (source context)
            - human_score: float (human label, 1-5 scale)
            - human_passed: bool
        """
        judge_scores = []
        human_scores = []
        judge_passed = []
        human_passed = []

        for ex in labeled_examples:
            result = self.grade(ex["output"], ex["expected"], ex.get("context"))
            judge_scores.append(result.score)
            judge_passed.append(result.passed)
            human_scores.append(ex["human_score"])
            human_passed.append(ex["human_passed"])

        # Compute agreement
        agreements = sum(1 for j, h in zip(judge_passed, human_passed) if j == h)
        agreement_rate = agreements / len(labeled_examples) if labeled_examples else 0.0

        # Cohen's kappa
        kappa = self._compute_kappa(judge_passed, human_passed)

        # Confusion matrix
        confusion = {"pass": {"pass": 0, "fail": 0}, "fail": {"pass": 0, "fail": 0}}
        for jp, hp in zip(judge_passed, human_passed):
            h_key = "pass" if hp else "fail"
            j_key = "pass" if jp else "fail"
            confusion[h_key][j_key] += 1

        # Find systematic patterns
        patterns = self._find_patterns(
            labeled_examples, judge_passed, human_passed, judge_scores, human_scores
        )

        return CalibrationReport(
            agreement_rate=agreement_rate,
            cohens_kappa=kappa,
            confusion_matrix=confusion,
            systematic_patterns=patterns,
            n_examples=len(labeled_examples),
            judge_scores=judge_scores,
            human_scores=human_scores,
        )

    @staticmethod
    def _compute_kappa(labels_a: list[bool], labels_b: list[bool]) -> float:
        """Compute Cohen's kappa between two sets of binary labels."""
        n = len(labels_a)
        if n == 0:
            return 0.0

        agreements = sum(1 for a, b in zip(labels_a, labels_b) if a == b)
        p_o = agreements / n

        p_a_true = sum(labels_a) / n
        p_b_true = sum(labels_b) / n
        p_e = p_a_true * p_b_true + (1 - p_a_true) * (1 - p_b_true)

        if p_e == 1.0:
            return 1.0
        return (p_o - p_e) / (1.0 - p_e)

    @staticmethod
    def _find_patterns(
        examples: list[dict],
        judge_passed: list[bool],
        human_passed: list[bool],
        judge_scores: list[float],
        human_scores: list[float],
    ) -> list[str]:
        """Identify systematic disagreement patterns."""
        patterns = []

        # Check for over/under scoring bias
        judge_mean = sum(judge_scores) / len(judge_scores) if judge_scores else 0
        human_mean = sum(human_scores) / len(human_scores) if human_scores else 0

        if judge_mean > human_mean + 0.5:
            patterns.append(
                f"Judge systematically over-scores (mean {judge_mean:.1f} vs human {human_mean:.1f})"
            )
        elif judge_mean < human_mean - 0.5:
            patterns.append(
                f"Judge systematically under-scores (mean {judge_mean:.1f} vs human {human_mean:.1f})"
            )

        # Check for disagreement by difficulty
        disagreements_by_difficulty: dict[str, int] = {}
        counts_by_difficulty: dict[str, int] = {}
        for ex, jp, hp in zip(examples, judge_passed, human_passed):
            diff = ex.get("difficulty", "unknown")
            counts_by_difficulty[diff] = counts_by_difficulty.get(diff, 0) + 1
            if jp != hp:
                disagreements_by_difficulty[diff] = disagreements_by_difficulty.get(diff, 0) + 1

        for diff, count in counts_by_difficulty.items():
            disagree = disagreements_by_difficulty.get(diff, 0)
            rate = disagree / count if count > 0 else 0
            if rate > 0.3:
                patterns.append(
                    f"High disagreement rate ({rate:.0%}) on {diff} difficulty cases"
                )

        return patterns


def create_grounding_sub_rubrics() -> list[dict]:
    """Create the standard grounding sub-rubrics with Blazer-style 30/30/25/15 weights."""
    return [
        {
            "name": "airport_correctness",
            "rubric": (
                "Does the output correctly identify the airport(s) involved? "
                "Check ICAO codes, airport names, and runway designations."
            ),
            "weight": 30,
            "threshold": 0.4,
        },
        {
            "name": "event_analysis_quality",
            "rubric": (
                "Does the output correctly analyze the aviation event? "
                "Check event type classification, contributing factors, and timeline accuracy."
            ),
            "weight": 30,
            "threshold": 0.4,
        },
        {
            "name": "fact_extraction_accuracy",
            "rubric": (
                "Does the output accurately extract key facts from the source material? "
                "Check aircraft type, altitude, speed, and other operational parameters."
            ),
            "weight": 25,
            "threshold": 0.4,
        },
        {
            "name": "flight_phase_relevance",
            "rubric": (
                "Does the output correctly identify and reference the relevant phase of flight? "
                "Surface events should not reference cruise altitude. "
                "Approach events should reference appropriate altitudes and speeds."
            ),
            "weight": 15,
            "threshold": 0.4,
        },
    ]
