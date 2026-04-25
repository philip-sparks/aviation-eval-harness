"""Tests for graders/rule_based.py — deterministic rule-based graders."""

import pytest

from graders.rule_based import (
    ContainsGrader,
    NotContainsGrader,
    NumericToleranceGrader,
    RegexGrader,
    SemanticEquivalenceGrader,
)


# ---------------------------------------------------------------------------
# ContainsGrader
# ---------------------------------------------------------------------------

class TestContainsGrader:
    def test_case_insensitive_match(self):
        grader = ContainsGrader()
        result = grader.grade(
            output="The aircraft performed a GO-AROUND at KDFW.",
            expected={"expected_facts": ["go-around", "KDFW"]},
        )
        assert result.passed is True
        assert result.score == 1.0
        assert result.metric_name == "contains"

    def test_partial_match(self):
        grader = ContainsGrader()
        result = grader.grade(
            output="The aircraft landed at KDFW.",
            expected={"expected_facts": ["KDFW", "go-around"]},
        )
        assert result.passed is False
        assert result.score == pytest.approx(0.5)
        assert "go-around" in result.details["missing"]
        assert "KDFW" in result.details["found"]

    def test_no_facts_means_pass(self):
        grader = ContainsGrader()
        result = grader.grade(output="anything", expected={})
        assert result.passed is True
        assert result.score == 1.0


# ---------------------------------------------------------------------------
# NotContainsGrader
# ---------------------------------------------------------------------------

class TestNotContainsGrader:
    def test_passes_when_absent(self):
        grader = NotContainsGrader()
        result = grader.grade(
            output="The event occurred at KDFW with a B738.",
            expected={"negative_facts": ["KJFK", "A320"]},
        )
        assert result.passed is True
        assert result.score == 1.0
        assert len(result.details["violations"]) == 0

    def test_fails_when_present(self):
        grader = NotContainsGrader()
        result = grader.grade(
            output="The event occurred at KJFK.",
            expected={"negative_facts": ["KJFK", "KLAX"]},
        )
        assert result.passed is False
        assert "KJFK" in result.details["violations"]
        assert "KLAX" in result.details["clean"]
        assert result.score == pytest.approx(0.5)

    def test_no_negative_facts_means_pass(self):
        grader = NotContainsGrader()
        result = grader.grade(output="anything", expected={})
        assert result.passed is True


# ---------------------------------------------------------------------------
# NumericToleranceGrader
# ---------------------------------------------------------------------------

class TestNumericToleranceGrader:
    def test_altitude_within_tolerance(self):
        grader = NumericToleranceGrader()
        result = grader.grade(
            output="The aircraft was at 15200 feet when the event occurred.",
            expected={"value": 15000, "tolerance_key": "altitude_ft"},
        )
        # tolerance is 500 ft, diff is 200, so should pass
        assert result.passed is True
        assert result.score == 1.0
        assert result.details["extracted"] == 15200.0

    def test_altitude_outside_tolerance(self):
        grader = NumericToleranceGrader()
        result = grader.grade(
            output="The aircraft was at 16000 feet.",
            expected={"value": 15000, "tolerance_key": "altitude_ft"},
        )
        # tolerance is 500, diff is 1000 — outside tolerance
        assert result.passed is False

    def test_explicit_tolerance(self):
        grader = NumericToleranceGrader()
        result = grader.grade(
            output="Speed was 142 knots on approach.",
            expected={"value": 140, "tolerance": 10},
        )
        assert result.passed is True
        assert result.details["extracted"] == 142.0

    def test_no_numeric_value_in_output(self):
        grader = NumericToleranceGrader()
        result = grader.grade(
            output="No numbers here at all.",
            expected={"value": 15000, "tolerance": 500},
        )
        assert result.passed is False
        assert "No numeric value" in result.details["error"]

    def test_no_expected_value(self):
        grader = NumericToleranceGrader()
        result = grader.grade(
            output="altitude 15000",
            expected={},
        )
        assert result.passed is False
        assert "No expected value" in result.details["error"]


# ---------------------------------------------------------------------------
# RegexGrader
# ---------------------------------------------------------------------------

class TestRegexGrader:
    def test_pattern_match(self):
        grader = RegexGrader()
        result = grader.grade(
            output="TCAS RA event at FL350",
            expected={"pattern": r"FL\d{3}"},
        )
        assert result.passed is True
        assert result.details["matched"] == "FL350"

    def test_pattern_no_match(self):
        grader = RegexGrader()
        result = grader.grade(
            output="No flight level mentioned.",
            expected={"pattern": r"FL\d{3}"},
        )
        assert result.passed is False
        assert result.score == 0.0

    def test_case_insensitive_by_default(self):
        grader = RegexGrader()
        result = grader.grade(
            output="metar kdfw",
            expected={"pattern": r"METAR KDFW"},
        )
        assert result.passed is True

    def test_no_pattern_provided(self):
        grader = RegexGrader()
        result = grader.grade(output="anything", expected={})
        assert result.passed is False
        assert "No pattern" in result.details["error"]


# ---------------------------------------------------------------------------
# SemanticEquivalenceGrader
# ---------------------------------------------------------------------------

class TestSemanticEquivalenceGrader:
    def test_exact_match(self):
        grader = SemanticEquivalenceGrader()
        result = grader.grade(
            output="A TCAS RA was issued.",
            expected={"expected_facts": ["TCAS RA"]},
        )
        assert result.passed is True

    def test_synonym_match(self):
        """'TCAS RA' and 'resolution advisory' should be recognized as equivalent."""
        grader = SemanticEquivalenceGrader()
        result = grader.grade(
            output="A resolution advisory was issued to the crew.",
            expected={"expected_facts": ["tcas ra"]},
        )
        assert result.passed is True
        assert result.score == 1.0

    def test_custom_equivalences(self):
        custom = {
            "go-around": ["go-around", "missed approach", "balked landing"],
        }
        grader = SemanticEquivalenceGrader(equivalences=custom)
        result = grader.grade(
            output="The crew performed a balked landing.",
            expected={"expected_facts": ["go-around"]},
        )
        assert result.passed is True

    def test_no_equivalence_found(self):
        grader = SemanticEquivalenceGrader()
        result = grader.grade(
            output="The flight was normal with no events.",
            expected={"expected_facts": ["tcas ra"]},
        )
        assert result.passed is False
        assert "tcas ra" in result.details["missing"]
