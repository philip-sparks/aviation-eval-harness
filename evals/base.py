"""Base classes for the evaluation harness.

Defines the abstract Eval class and Result/ExampleResult dataclasses
that all eval categories implement.
"""

from __future__ import annotations

import json
from abc import ABC, abstractmethod
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path
from typing import Any


@dataclass
class ExampleResult:
    """Result for a single evaluation example."""

    example_id: str
    input: dict
    output: str
    scores: dict[str, float]
    traces: list[dict]
    grader_results: dict[str, Any]
    passed: bool

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class Result:
    """Aggregate result for an evaluation run."""

    eval_name: str
    model_id: str
    timestamp: datetime
    examples: list[ExampleResult]
    aggregate_metrics: dict[str, float]
    confidence_intervals: dict[str, tuple[float, float]]
    run_config: dict

    def to_dict(self) -> dict:
        d = asdict(self)
        d["timestamp"] = self.timestamp.isoformat()
        return d

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), indent=2, default=str)

    def to_summary(self) -> str:
        lines = [
            f"Eval: {self.eval_name}",
            f"Model: {self.model_id}",
            f"Timestamp: {self.timestamp.isoformat()}",
            f"Examples: {len(self.examples)} ({sum(1 for e in self.examples if e.passed)} passed)",
            "",
            "Aggregate Metrics:",
        ]
        for metric, value in self.aggregate_metrics.items():
            ci = self.confidence_intervals.get(metric)
            if ci:
                lines.append(f"  {metric}: {value:.4f} [{ci[0]:.4f}, {ci[1]:.4f}]")
            else:
                lines.append(f"  {metric}: {value:.4f}")
        return "\n".join(lines)

    def save(self, path: Path) -> None:
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(self.to_json())

    @classmethod
    def from_json(cls, json_str: str) -> Result:
        d = json.loads(json_str)
        d["timestamp"] = datetime.fromisoformat(d["timestamp"])
        d["examples"] = [ExampleResult(**ex) for ex in d["examples"]]
        d["confidence_intervals"] = {
            k: tuple(v) for k, v in d["confidence_intervals"].items()
        }
        return cls(**d)

    @classmethod
    def load(cls, path: Path) -> Result:
        return cls.from_json(Path(path).read_text())


class Eval(ABC):
    """Abstract base class for all evaluation categories."""

    def __init__(self, name: str, graders: list | None = None):
        self.name = name
        self.graders = graders or []

    @abstractmethod
    def run(self, model, dataset: list[dict]) -> Result:
        """Run the full evaluation on a dataset."""
        ...

    @abstractmethod
    def run_single(self, model, example: dict) -> ExampleResult:
        """Run evaluation on a single example."""
        ...

    def load_dataset(self, path: Path) -> list[dict]:
        """Load a JSONL dataset file."""
        examples = []
        with open(path) as f:
            for line in f:
                line = line.strip()
                if line:
                    examples.append(json.loads(line))
        return examples
