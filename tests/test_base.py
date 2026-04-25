"""Tests for evals/base.py — Result, ExampleResult, and Eval base class."""

import json
from datetime import datetime

import pytest

from evals.base import ExampleResult, Result, Eval


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

def _make_example_result(**overrides) -> ExampleResult:
    defaults = {
        "example_id": "ex-001",
        "input": {"query": "What happened?", "context": "A go-around at KDFW"},
        "output": "The aircraft executed a go-around.",
        "scores": {"contains": 1.0, "llm_judge": 0.8},
        "traces": [{"step": "grading", "grader": "contains"}],
        "grader_results": {"contains": {"found": ["go-around"], "missing": []}},
        "passed": True,
    }
    defaults.update(overrides)
    return ExampleResult(**defaults)


def _make_result(**overrides) -> Result:
    ex1 = _make_example_result(example_id="ex-001", passed=True)
    ex2 = _make_example_result(example_id="ex-002", passed=False, scores={"contains": 0.5})
    defaults = {
        "eval_name": "grounding",
        "model_id": "claude-sonnet-4-20250514",
        "timestamp": datetime(2025, 6, 15, 12, 0, 0),
        "examples": [ex1, ex2],
        "aggregate_metrics": {"contains": 0.75, "llm_judge": 0.8},
        "confidence_intervals": {"contains": (0.60, 0.90)},
        "run_config": {"max_tokens": 4096},
    }
    defaults.update(overrides)
    return Result(**defaults)


# ---------------------------------------------------------------------------
# ExampleResult tests
# ---------------------------------------------------------------------------

class TestExampleResult:
    def test_construction(self):
        er = _make_example_result()
        assert er.example_id == "ex-001"
        assert er.passed is True
        assert er.scores["contains"] == 1.0

    def test_to_dict_round_trip(self):
        er = _make_example_result()
        d = er.to_dict()
        assert isinstance(d, dict)
        assert d["example_id"] == "ex-001"
        reconstructed = ExampleResult(**d)
        assert reconstructed.example_id == er.example_id
        assert reconstructed.scores == er.scores


# ---------------------------------------------------------------------------
# Result tests
# ---------------------------------------------------------------------------

class TestResult:
    def test_to_json_from_json_round_trip(self):
        original = _make_result()
        json_str = original.to_json()

        # Should be valid JSON
        parsed = json.loads(json_str)
        assert parsed["eval_name"] == "grounding"

        # Round-trip
        restored = Result.from_json(json_str)
        assert restored.eval_name == original.eval_name
        assert restored.model_id == original.model_id
        assert restored.timestamp == original.timestamp
        assert len(restored.examples) == len(original.examples)
        assert restored.aggregate_metrics == original.aggregate_metrics
        # Confidence intervals round-trip preserves tuples
        assert restored.confidence_intervals["contains"] == (0.60, 0.90)

    def test_to_summary_produces_readable_output(self):
        result = _make_result()
        summary = result.to_summary()

        assert "Eval: grounding" in summary
        assert "Model: claude-sonnet-4-20250514" in summary
        assert "Examples: 2 (1 passed)" in summary
        assert "Aggregate Metrics:" in summary
        assert "contains:" in summary
        # CI should be present for the contains metric
        assert "[0.6000, 0.9000]" in summary
        # llm_judge has no CI in our fixture, should still appear
        assert "llm_judge:" in summary

    def test_save_and_load(self, tmp_path):
        original = _make_result()
        file_path = tmp_path / "results" / "test_result.json"
        original.save(file_path)

        assert file_path.exists()
        loaded = Result.load(file_path)
        assert loaded.eval_name == original.eval_name
        assert len(loaded.examples) == 2


# ---------------------------------------------------------------------------
# Eval base class tests
# ---------------------------------------------------------------------------

class TestEvalBase:
    def test_abstract_run_raises(self):
        """Instantiating Eval directly or calling abstract methods should fail."""

        class IncompleteEval(Eval):
            pass

        with pytest.raises(TypeError):
            IncompleteEval(name="test")

    def test_abstract_methods_on_subclass(self):
        """A concrete subclass must implement run and run_single."""

        class ConcreteEval(Eval):
            def run(self, model, dataset):
                return super().run(model, dataset)

            def run_single(self, model, example):
                return super().run_single(model, example)

        # Should be instantiable
        ev = ConcreteEval(name="test")
        assert ev.name == "test"

    def test_load_dataset(self, tmp_path):
        """load_dataset should parse JSONL correctly."""

        class MinimalEval(Eval):
            def run(self, model, dataset):
                pass

            def run_single(self, model, example):
                pass

        ev = MinimalEval(name="test")
        jsonl = tmp_path / "data.jsonl"
        jsonl.write_text(
            '{"case_id": "c1", "query": "q1"}\n'
            '{"case_id": "c2", "query": "q2"}\n'
        )
        examples = ev.load_dataset(jsonl)
        assert len(examples) == 2
        assert examples[0]["case_id"] == "c1"
