"""Tool use evaluation: measures correct tool selection, arguments, and sequencing."""

from __future__ import annotations

import json
import re
from datetime import datetime
from pathlib import Path
from typing import Any

from evals.base import Eval, Result, ExampleResult
from evals.tool_use.mock_tools import TOOL_REGISTRY, get_tool_schemas_json


SYSTEM_PROMPT = (
    "You are an aviation safety analyst with access to tools. "
    "When given a query, determine which tools to call and in what order. "
    "Respond with a JSON array of tool calls, each with 'tool' and 'args' keys."
)

DEFAULT_DATASET = Path(__file__).parent.parent.parent / "datasets" / "tool_use_cases.jsonl"


class ToolUseEval(Eval):
    """Tool use evaluation.

    Measures:
    - tool_selection_accuracy: correct tool(s) selected
    - argument_accuracy: correct arguments provided
    - sequence_accuracy: correct tool call ordering
    """

    def __init__(self, dataset_path: Path | str | None = None):
        super().__init__(name="tool_use")
        self.dataset_path = Path(dataset_path) if dataset_path else DEFAULT_DATASET

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

        aggregate = {
            "tool_selection_accuracy": sum(e.scores.get("tool_selection", 0) for e in examples) / n,
            "argument_accuracy": sum(e.scores.get("argument_accuracy", 0) for e in examples) / n,
            "sequence_accuracy": sum(e.scores.get("sequence_accuracy", 0) for e in examples) / n,
            "pass_rate": sum(1 for e in examples if e.passed) / n,
        }

        return Result(
            eval_name=self.name, model_id=model.model_id,
            timestamp=datetime.now(), examples=examples,
            aggregate_metrics=aggregate, confidence_intervals={},
            run_config={"dataset": str(self.dataset_path)},
        )

    def run_single(self, model, example: dict) -> ExampleResult:
        query = example.get("query", "")
        context = example.get("context", "")

        prompt = (
            f"Available tools:\n{get_tool_schemas_json()}\n\n"
            f"{'Context: ' + context + chr(10) + chr(10) if context else ''}"
            f"Query: {query}\n\n"
            "Respond with a JSON array of tool calls."
        )

        response = model.generate(prompt, system_prompt=SYSTEM_PROMPT)
        output = response.text

        # Parse model's tool calls
        predicted_calls = self._parse_tool_calls(output)
        expected_tools = example.get("expected_tools", [])
        expected_sequence = example.get("expected_sequence", [])

        # Score tool selection
        predicted_tool_names = [tc.get("tool", "") for tc in predicted_calls]
        expected_tool_names = [tc.get("tool", "") for tc in expected_tools]

        selection_score = self._score_tool_selection(predicted_tool_names, expected_tool_names)
        argument_score = self._score_arguments(predicted_calls, expected_tools)
        sequence_score = self._score_sequence(predicted_tool_names, expected_sequence)

        scores = {
            "tool_selection": selection_score,
            "argument_accuracy": argument_score,
            "sequence_accuracy": sequence_score,
        }

        passed = selection_score >= 0.8 and argument_score >= 0.5

        return ExampleResult(
            example_id=example.get("case_id", ""),
            input={"query": query},
            output=output,
            scores=scores,
            traces=[{"predicted_calls": predicted_calls}],
            grader_results={
                "predicted_tools": predicted_tool_names,
                "expected_tools": expected_tool_names,
            },
            passed=passed,
        )

    def _parse_tool_calls(self, output: str) -> list[dict]:
        """Parse tool calls from model output."""
        # Try to find JSON array in output
        try:
            match = re.search(r'\[.*\]', output, re.DOTALL)
            if match:
                return json.loads(match.group())
        except (json.JSONDecodeError, ValueError):
            pass

        # Try to find individual JSON objects
        calls = []
        for match in re.finditer(r'\{[^{}]+\}', output):
            try:
                obj = json.loads(match.group())
                if "tool" in obj:
                    calls.append(obj)
            except json.JSONDecodeError:
                continue
        return calls

    @staticmethod
    def _score_tool_selection(predicted: list[str], expected: list[str]) -> float:
        if not expected:
            return 1.0
        correct = sum(1 for t in expected if t in predicted)
        extra = sum(1 for t in predicted if t not in expected)
        # Penalize for extra tools but less heavily
        score = correct / len(expected) - 0.1 * extra
        return max(0.0, min(1.0, score))

    @staticmethod
    def _score_arguments(predicted: list[dict], expected: list[dict]) -> float:
        if not expected:
            return 1.0

        scores = []
        for exp_call in expected:
            exp_tool = exp_call.get("tool", "")
            exp_args = exp_call.get("args", {})

            # Find matching predicted call
            match = None
            for pred_call in predicted:
                if pred_call.get("tool") == exp_tool:
                    match = pred_call
                    break

            if match is None:
                scores.append(0.0)
                continue

            pred_args = match.get("args", {})
            if not exp_args:
                scores.append(1.0)
                continue

            # Compare arguments
            correct = 0
            for key, exp_val in exp_args.items():
                pred_val = pred_args.get(key)
                if pred_val is not None:
                    # Fuzzy match for strings
                    if isinstance(exp_val, str) and isinstance(pred_val, str):
                        if exp_val.upper() == pred_val.upper():
                            correct += 1
                    elif exp_val == pred_val:
                        correct += 1
            scores.append(correct / len(exp_args))

        return sum(scores) / len(scores) if scores else 0.0

    @staticmethod
    def _score_sequence(predicted: list[str], expected_sequence: list[str]) -> float:
        if not expected_sequence:
            return 1.0
        if not predicted:
            return 0.0

        # Longest common subsequence ratio
        m, n = len(predicted), len(expected_sequence)
        dp = [[0] * (n + 1) for _ in range(m + 1)]
        for i in range(1, m + 1):
            for j in range(1, n + 1):
                if predicted[i-1] == expected_sequence[j-1]:
                    dp[i][j] = dp[i-1][j-1] + 1
                else:
                    dp[i][j] = max(dp[i-1][j], dp[i][j-1])

        lcs = dp[m][n]
        return lcs / len(expected_sequence)
