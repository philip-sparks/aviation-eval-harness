"""Tests for graders/llm_judge.py — LLM-as-judge grader with rubric scoring."""

from unittest.mock import MagicMock

import pytest

from graders.llm_judge import (
    LLMJudgeGrader,
    CalibrationReport,
    create_grounding_sub_rubrics,
)
from models.adapters import ModelResponse


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _mock_adapter(score: int = 4, reasoning: str = "Good answer"):
    """Return a mock model adapter that always returns a fixed judge score."""
    adapter = MagicMock()
    adapter.generate.return_value = ModelResponse(
        text=f'{{"score": {score}, "reasoning": "{reasoning}"}}',
        model_id="judge-model",
    )
    return adapter


# ---------------------------------------------------------------------------
# LLMJudgeGrader — single rubric
# ---------------------------------------------------------------------------

class TestLLMJudgeGrader:
    def test_grade_with_mocked_adapter(self):
        adapter = _mock_adapter(score=4)
        grader = LLMJudgeGrader(rubric="Check correctness", model_adapter=adapter)

        result = grader.grade(
            output="KDFW go-around due to traffic on runway.",
            expected={},
            context={"context": "Go-around event at KDFW"},
        )
        assert result.score == 4.0
        assert result.passed is True  # 4/5 = 0.8 >= 0.6 threshold
        assert result.metric_name == "llm_judge"
        assert result.details["raw_score"] == 4
        adapter.generate.assert_called_once()

    def test_grade_without_adapter_returns_error(self):
        grader = LLMJudgeGrader(rubric="Check correctness", model_adapter=None)
        result = grader.grade(output="test", expected={})
        assert result.passed is False
        assert "No model adapter" in result.details["error"]

    def test_grade_with_low_score_fails(self):
        adapter = _mock_adapter(score=2)
        grader = LLMJudgeGrader(rubric="Check correctness", model_adapter=adapter)
        result = grader.grade(output="wrong answer", expected={})
        # 2/5 = 0.4, threshold = 0.6
        assert result.passed is False

    def test_parse_malformed_response(self):
        adapter = MagicMock()
        adapter.generate.return_value = ModelResponse(
            text="This is not JSON at all.", model_id="judge"
        )
        grader = LLMJudgeGrader(rubric="test", model_adapter=adapter)
        result = grader.grade(output="test", expected={})
        assert result.passed is False
        assert "Failed to parse" in result.details["error"]


# ---------------------------------------------------------------------------
# Weighted sub-rubric aggregation
# ---------------------------------------------------------------------------

class TestSubRubricAggregation:
    def test_weighted_30_30_25_15(self):
        """Sub-rubrics with 30/30/25/15 weights produce correct weighted score."""
        adapter = _mock_adapter(score=5)  # All sub-rubrics get perfect 5
        sub_rubrics = [
            {"name": "airport_correctness", "rubric": "Check airports", "weight": 30},
            {"name": "event_analysis", "rubric": "Check analysis", "weight": 30},
            {"name": "fact_extraction", "rubric": "Check facts", "weight": 25},
            {"name": "flight_phase", "rubric": "Check phase", "weight": 15},
        ]

        grader = LLMJudgeGrader(
            rubric="",
            model_adapter=adapter,
            sub_rubrics=sub_rubrics,
            threshold=0.6,
        )
        result = grader.grade(output="perfect output", expected={})

        # All scores are 5 -> normalized 5/5 = 1.0 for each
        # weighted_score = sum(1.0 * weight/100 for each) = 1.0
        assert result.score == pytest.approx(1.0, abs=0.01)
        assert result.passed is True
        assert "sub_rubrics" in result.details

    def test_mixed_sub_rubric_scores(self):
        """Different sub-rubric scores should produce correct weighted average."""
        # Return scores of 5, 3, 4, 2 for the four sub-rubric calls
        call_count = 0
        scores = [5, 3, 4, 2]

        def mock_generate(prompt):
            nonlocal call_count
            s = scores[call_count % len(scores)]
            call_count += 1
            return ModelResponse(
                text=f'{{"score": {s}, "reasoning": "test"}}',
                model_id="judge",
            )

        adapter = MagicMock()
        adapter.generate.side_effect = mock_generate

        sub_rubrics = [
            {"name": "r1", "rubric": "r1", "weight": 30},
            {"name": "r2", "rubric": "r2", "weight": 30},
            {"name": "r3", "rubric": "r3", "weight": 25},
            {"name": "r4", "rubric": "r4", "weight": 15},
        ]
        grader = LLMJudgeGrader(
            rubric="", model_adapter=adapter, sub_rubrics=sub_rubrics
        )
        result = grader.grade(output="test", expected={})

        # Expected: (5/5)*(30/100) + (3/5)*(30/100) + (4/5)*(25/100) + (2/5)*(15/100)
        #         = 1.0*0.3 + 0.6*0.3 + 0.8*0.25 + 0.4*0.15
        #         = 0.30 + 0.18 + 0.20 + 0.06 = 0.74
        assert result.score == pytest.approx(0.74, abs=0.02)


# ---------------------------------------------------------------------------
# CalibrationReport
# ---------------------------------------------------------------------------

class TestCalibrationReport:
    def test_to_markdown_produces_valid_markdown(self):
        report = CalibrationReport(
            agreement_rate=0.85,
            cohens_kappa=0.70,
            confusion_matrix={
                "pass": {"pass": 10, "fail": 2},
                "fail": {"pass": 1, "fail": 7},
            },
            systematic_patterns=["Judge systematically over-scores (mean 4.2 vs human 3.5)"],
            n_examples=20,
            judge_scores=[4.0] * 20,
            human_scores=[3.5] * 20,
        )
        md = report.to_markdown()

        assert "# LLM Judge Calibration Report" in md
        assert "85.0%" in md
        assert "0.700" in md
        assert "Confusion Matrix" in md
        assert "| **Human: Pass** | 10 | 2 |" in md
        assert "| **Human: Fail** | 1 | 7 |" in md
        assert "Systematic Disagreement Patterns" in md
        assert "over-scores" in md

    def test_to_markdown_without_patterns(self):
        report = CalibrationReport(
            agreement_rate=1.0,
            cohens_kappa=1.0,
            confusion_matrix={"pass": {"pass": 5, "fail": 0}, "fail": {"pass": 0, "fail": 5}},
            systematic_patterns=[],
            n_examples=10,
        )
        md = report.to_markdown()
        assert "Systematic Disagreement" not in md


# ---------------------------------------------------------------------------
# Calibration kappa computation
# ---------------------------------------------------------------------------

class TestCalibrationKappa:
    def test_perfect_agreement(self):
        """Identical label sets should yield kappa = 1.0."""
        kappa = LLMJudgeGrader._compute_kappa(
            [True, True, False, False, True],
            [True, True, False, False, True],
        )
        assert kappa == pytest.approx(1.0)

    def test_no_agreement_beyond_chance(self):
        """Completely opposing labels with mixed marginals yield kappa < 0."""
        kappa = LLMJudgeGrader._compute_kappa(
            [True, False, True, False, True, False],
            [False, True, False, True, False, True],
        )
        assert kappa < 0

    def test_empty_labels(self):
        kappa = LLMJudgeGrader._compute_kappa([], [])
        assert kappa == 0.0


# ---------------------------------------------------------------------------
# create_grounding_sub_rubrics helper
# ---------------------------------------------------------------------------

class TestGroundingSubRubrics:
    def test_returns_four_rubrics_with_correct_weights(self):
        rubrics = create_grounding_sub_rubrics()
        assert len(rubrics) == 4
        weights = [r["weight"] for r in rubrics]
        assert weights == [30, 30, 25, 15]
        names = [r["name"] for r in rubrics]
        assert "airport_correctness" in names
        assert "flight_phase_relevance" in names
