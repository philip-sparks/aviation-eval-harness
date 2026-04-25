"""Custom Promptfoo provider for the aviation eval harness.

This module is called by Promptfoo via `python:runners/promptfoo_provider.py`.
It routes prompts through the model adapter layer.

Promptfoo calls `call_api(prompt, options, context) -> dict` which must return:
    {"output": str, "metadata": dict, "tokenUsage": dict}
"""

from __future__ import annotations

import json
import os
import time
from typing import Any

# Module-level cache for adapter (reused across Promptfoo worker calls)
_adapter_cache: dict[str, Any] = {}


def _get_adapter():
    """Get or create the model adapter, caching for reuse."""
    if "adapter" in _adapter_cache:
        return _adapter_cache["adapter"]

    from models.adapters import create_adapter

    provider = os.environ.get("EVAL_PROVIDER", "anthropic")
    model_id = os.environ.get("EVAL_MODEL_ID", "claude-sonnet-4-20250514")
    max_tokens = int(os.environ.get("EVAL_MAX_TOKENS", "4096"))
    temperature = float(os.environ.get("EVAL_TEMPERATURE", "0.0"))

    # Check for sidecar config
    config_path = os.environ.get("EVAL_PROVIDER_CONFIG")
    if config_path and os.path.exists(config_path):
        with open(config_path) as f:
            config = json.load(f)
        provider = config.get("provider", provider)
        model_id = config.get("model_id", model_id)
        max_tokens = config.get("max_tokens", max_tokens)
        temperature = config.get("temperature", temperature)

    adapter = create_adapter(
        provider,
        model=model_id,
        max_tokens=max_tokens,
        temperature=temperature,
    )
    _adapter_cache["adapter"] = adapter
    return adapter


def call_api(prompt: str, options: dict | None = None, context: dict | None = None) -> dict:
    """Promptfoo provider entry point.

    Args:
        prompt: The rendered prompt from Promptfoo.
        options: Provider options from the config.
        context: Test context (vars, assertions).

    Returns:
        Dict with output, metadata, and tokenUsage.
    """
    options = options or {}
    context = context or {}

    adapter = _get_adapter()

    # Extract system prompt if present in context vars
    system_prompt = None
    if "vars" in context:
        system_prompt = context["vars"].get("system_prompt")

    config = {}
    if "config" in options:
        config = options["config"]

    try:
        start = time.monotonic()
        response = adapter.generate(prompt, system_prompt=system_prompt, config=config)
        latency_ms = (time.monotonic() - start) * 1000

        return {
            "output": response.text,
            "metadata": {
                "model_id": response.model_id,
                "latency_ms": latency_ms,
            },
            "tokenUsage": {
                "total": response.usage.get("input_tokens", 0) + response.usage.get("output_tokens", 0),
                "prompt": response.usage.get("input_tokens", 0),
                "completion": response.usage.get("output_tokens", 0),
            },
        }
    except Exception as e:
        return {
            "output": f"ERROR: {str(e)}",
            "metadata": {"error": str(e)},
            "tokenUsage": {"total": 0, "prompt": 0, "completion": 0},
        }


def promptfoo_results_to_result(promptfoo_output: dict, eval_name: str) -> "Result":
    """Convert Promptfoo's native JSON output into the harness's Result schema.

    Args:
        promptfoo_output: Promptfoo's JSON results.
        eval_name: Name of the eval category.

    Returns:
        Result object with per-example scores and traces.
    """
    from datetime import datetime
    from evals.base import Result, ExampleResult

    examples = []
    results_list = promptfoo_output.get("results", [])

    for i, pf_result in enumerate(results_list):
        # Extract scores from assertions
        scores = {}
        passed = True
        grader_results = {}

        for assertion in pf_result.get("gradingResult", {}).get("componentResults", []):
            name = assertion.get("assertion", {}).get("type", f"assertion_{i}")
            score = 1.0 if assertion.get("pass", False) else 0.0
            scores[name] = score
            grader_results[name] = {
                "pass": assertion.get("pass", False),
                "reason": assertion.get("reason", ""),
            }
            if not assertion.get("pass", False):
                passed = False

        example = ExampleResult(
            example_id=pf_result.get("description", f"example_{i}"),
            input=pf_result.get("vars", {}),
            output=pf_result.get("response", {}).get("output", ""),
            scores=scores,
            traces=[],
            grader_results=grader_results,
            passed=passed,
        )
        examples.append(example)

    # Compute aggregate metrics
    total = len(examples)
    pass_count = sum(1 for e in examples if e.passed)
    aggregate = {
        "accuracy": pass_count / total if total > 0 else 0.0,
        "pass_count": float(pass_count),
        "total_count": float(total),
    }

    return Result(
        eval_name=eval_name,
        model_id=promptfoo_output.get("stats", {}).get("provider", "unknown"),
        timestamp=datetime.now(),
        examples=examples,
        aggregate_metrics=aggregate,
        confidence_intervals={},
        run_config=promptfoo_output.get("config", {}),
    )
