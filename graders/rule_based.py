"""Deterministic rule-based graders.

Includes string matching, anti-hallucination checks, numeric tolerance,
regex extraction, and semantic equivalence grading.
"""

from __future__ import annotations

import re
from typing import Any

from graders import Grader, GradeResult
from evals.aviation_domain import SEMANTIC_EQUIVALENCES, NUMERIC_TOLERANCES


class ContainsGrader(Grader):
    """Case-insensitive string containment check."""

    def grade(self, output: str, expected: dict, context: dict | None = None) -> GradeResult:
        facts = expected.get("expected_facts", [])
        if not facts:
            return GradeResult(score=1.0, passed=True, metric_name="contains", details={})

        output_lower = output.lower()
        found = []
        missing = []
        for fact in facts:
            if fact.lower() in output_lower:
                found.append(fact)
            else:
                missing.append(fact)

        score = len(found) / len(facts) if facts else 1.0
        return GradeResult(
            score=score,
            passed=len(missing) == 0,
            metric_name="contains",
            details={"found": found, "missing": missing},
        )


class NotContainsGrader(Grader):
    """Anti-hallucination grader. Fails if output contains forbidden strings."""

    def grade(self, output: str, expected: dict, context: dict | None = None) -> GradeResult:
        negative_facts = expected.get("negative_facts", [])
        if not negative_facts:
            return GradeResult(score=1.0, passed=True, metric_name="not_contains", details={})

        output_lower = output.lower()
        violations = []
        clean = []
        for fact in negative_facts:
            if fact.lower() in output_lower:
                violations.append(fact)
            else:
                clean.append(fact)

        score = len(clean) / len(negative_facts) if negative_facts else 1.0
        return GradeResult(
            score=score,
            passed=len(violations) == 0,
            metric_name="not_contains",
            details={"violations": violations, "clean": clean},
        )


class NumericToleranceGrader(Grader):
    """Extract a numeric value and check it within tolerance.

    Expects `expected` to contain:
        - `value`: the expected numeric value
        - `tolerance_key`: key into NUMERIC_TOLERANCES (e.g., "altitude_ft")
          OR `tolerance`: explicit tolerance value
        - `pattern`: optional regex to extract the number (default: any number)
    """

    def grade(self, output: str, expected: dict, context: dict | None = None) -> GradeResult:
        target = expected.get("value")
        if target is None:
            return GradeResult(
                score=0.0, passed=False, metric_name="numeric_tolerance",
                details={"error": "No expected value provided"},
            )

        tolerance_key = expected.get("tolerance_key")
        tolerance = expected.get("tolerance")
        if tolerance is None and tolerance_key:
            tolerance = NUMERIC_TOLERANCES.get(tolerance_key, 0)
        if tolerance is None:
            tolerance = 0

        pattern = expected.get("pattern", r"[\d,]+\.?\d*")
        matches = re.findall(pattern, output)
        if not matches:
            return GradeResult(
                score=0.0, passed=False, metric_name="numeric_tolerance",
                details={"error": "No numeric value found in output", "pattern": pattern},
            )

        # Check if any extracted number is within tolerance
        for match in matches:
            try:
                extracted = float(match.replace(",", ""))
                if abs(extracted - target) <= tolerance:
                    return GradeResult(
                        score=1.0, passed=True, metric_name="numeric_tolerance",
                        details={"extracted": extracted, "target": target, "tolerance": tolerance},
                    )
            except ValueError:
                continue

        # Best match
        closest = None
        closest_diff = float("inf")
        for match in matches:
            try:
                extracted = float(match.replace(",", ""))
                diff = abs(extracted - target)
                if diff < closest_diff:
                    closest = extracted
                    closest_diff = diff
            except ValueError:
                continue

        score = max(0.0, 1.0 - (closest_diff / (tolerance if tolerance > 0 else 1.0)))
        return GradeResult(
            score=score, passed=False, metric_name="numeric_tolerance",
            details={"closest": closest, "target": target, "tolerance": tolerance, "diff": closest_diff},
        )


class RegexGrader(Grader):
    """Match output against a regex pattern."""

    def grade(self, output: str, expected: dict, context: dict | None = None) -> GradeResult:
        pattern = expected.get("pattern", "")
        if not pattern:
            return GradeResult(
                score=0.0, passed=False, metric_name="regex",
                details={"error": "No pattern provided"},
            )

        flags = re.IGNORECASE if expected.get("case_insensitive", True) else 0
        match = re.search(pattern, output, flags)
        return GradeResult(
            score=1.0 if match else 0.0,
            passed=match is not None,
            metric_name="regex",
            details={
                "pattern": pattern,
                "matched": match.group(0) if match else None,
            },
        )


class SemanticEquivalenceGrader(Grader):
    """Check for semantic equivalence using aviation domain synonym lists.

    Before failing a contains check, expands the expected fact using
    SEMANTIC_EQUIVALENCES to allow equivalent phrasings.
    """

    def __init__(self, equivalences: dict[str, list[str]] | None = None):
        self._equivalences = equivalences or SEMANTIC_EQUIVALENCES

    def grade(self, output: str, expected: dict, context: dict | None = None) -> GradeResult:
        facts = expected.get("expected_facts", [])
        if not facts:
            return GradeResult(score=1.0, passed=True, metric_name="semantic_equivalence", details={})

        output_lower = output.lower()
        found = []
        missing = []

        for fact in facts:
            if self._check_with_equivalences(fact.lower(), output_lower):
                found.append(fact)
            else:
                missing.append(fact)

        score = len(found) / len(facts) if facts else 1.0
        return GradeResult(
            score=score,
            passed=len(missing) == 0,
            metric_name="semantic_equivalence",
            details={"found": found, "missing": missing},
        )

    def _check_with_equivalences(self, fact: str, output: str) -> bool:
        """Check if fact or any equivalent is present in output."""
        if fact in output:
            return True

        # Check all equivalence lists
        for _canonical, equivalents in self._equivalences.items():
            lower_equivalents = [e.lower() for e in equivalents]
            if fact in lower_equivalents:
                # Fact is part of this equivalence group; check if ANY equivalent is in output
                for equiv in lower_equivalents:
                    if equiv in output:
                        return True
        return False
