"""Grading infrastructure for the evaluation harness."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any


@dataclass
class GradeResult:
    """Result of grading a single example."""

    score: float
    passed: bool
    metric_name: str
    details: dict = field(default_factory=dict)


class Grader(ABC):
    """Abstract base class for all graders."""

    @abstractmethod
    def grade(self, output: str, expected: dict, context: dict | None = None) -> GradeResult:
        """Grade a model output against expected results.

        Args:
            output: The model's output text.
            expected: Expected results (facts, values, patterns).
            context: Additional context (source document, metadata).

        Returns:
            GradeResult with score, pass/fail, and details.
        """
        ...
