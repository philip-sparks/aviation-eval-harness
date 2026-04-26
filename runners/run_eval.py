"""CLI entry point for the aviation eval harness.

Commands:
    run            Run an evaluation
    compare        Compare two result files
    new-experiment Scaffold a new experiment directory
"""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

import click
from dotenv import load_dotenv

load_dotenv()

from evals.base import Result
from evals.config import load_config, save_config
from models.adapters import create_adapter
from runners.cache import ResponseCache, CachedAdapter


EVAL_REGISTRY = {
    "grounding": "evals.grounding.grounding_eval:GroundingEval",
    "tool_use": "evals.tool_use.tool_use_eval:ToolUseEval",
    "robustness": "evals.robustness.robustness_eval:RobustnessEval",
    "refusals": "evals.refusals.refusals_eval:RefusalsEval",
}

DATASET_DEFAULTS = {
    "grounding": "datasets/grounding_cases.jsonl",
    "tool_use": "datasets/tool_use_cases.jsonl",
    "robustness": "datasets/adversarial_prompts.jsonl",
    "refusals": "datasets/refusal_cases.jsonl",
}


@click.group()
def cli():
    """Aviation Agent Evaluation Harness."""
    pass


@cli.command()
@click.option("--eval", "eval_name", required=True,
              type=click.Choice(list(EVAL_REGISTRY.keys())),
              help="Evaluation category to run.")
@click.option("--model", "model_spec", default="anthropic:claude-sonnet-4-20250514",
              help="Model spec as provider:model_id.")
@click.option("--dataset", "dataset_path", default=None,
              help="Path to dataset JSONL (overrides default).")
@click.option("--config", "config_path", default=None,
              help="Path to YAML config file.")
@click.option("--output", "output_path", default=None,
              help="Output path for results JSON.")
@click.option("--use-cache/--no-cache", default=True,
              help="Use response cache for reproducibility.")
@click.option("--concurrency", default=5, help="Max concurrent API calls.")
def run(eval_name, model_spec, dataset_path, config_path, output_path, use_cache, concurrency):
    """Run an evaluation."""
    click.echo(f"Running {eval_name} evaluation...")

    # Parse model spec
    parts = model_spec.split(":", 1)
    provider = parts[0]
    model_id = parts[1] if len(parts) > 1 else "claude-sonnet-4-20250514"

    # Load config if provided
    config = {}
    if config_path:
        config = load_config(config_path)

    # Create model adapter
    adapter = create_adapter(provider, model=model_id)
    if use_cache:
        cache = ResponseCache()
        adapter = CachedAdapter(adapter, cache)

    # Load eval class
    eval_cls = _load_eval_class(eval_name)

    # Pass judge adapter for evals that need it
    eval_kwargs = {}
    if eval_name in ("grounding", "refusals"):
        eval_kwargs["judge_adapter"] = adapter
    eval_instance = eval_cls(**eval_kwargs)

    # Load dataset
    dataset = None
    if dataset_path:
        dataset = eval_instance.load_dataset(Path(dataset_path))
    elif DATASET_DEFAULTS.get(eval_name):
        default_ds = Path(DATASET_DEFAULTS[eval_name])
        if default_ds.exists():
            dataset = eval_instance.load_dataset(default_ds)

    # Run evaluation
    result = eval_instance.run(adapter, dataset)

    # Add bootstrap CIs
    try:
        from analysis.significance import bootstrap_ci

        # Map aggregate metric names to per-example score extraction
        ci_extractors = {
            "grounding_accuracy": lambda e: max(
                e.scores.get("semantic_equivalence", 0),
                e.scores.get("contains", 0),
            ),
            "hallucination_rate": lambda e: 1.0 - e.scores.get("not_contains", 1.0),
            "pass_rate": lambda e: float(e.passed),
            "llm_judge": lambda e: e.scores.get("llm_judge", 0),
        }
        default_extractor = lambda e: float(e.passed)

        for metric in result.aggregate_metrics:
            extractor = ci_extractors.get(metric, default_extractor)
            scores = [extractor(e) for e in result.examples]
            if scores:
                _, lower, upper = bootstrap_ci(scores)
                result.confidence_intervals[metric] = (lower, upper)
    except Exception:
        pass

    # Output results
    click.echo(result.to_summary())

    if output_path is None:
        output_path = f"results_{eval_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"

    result.save(Path(output_path))
    click.echo(f"\nResults saved to: {output_path}")


@cli.command()
@click.argument("result_a_path")
@click.argument("result_b_path")
@click.option("--output", "output_path", default=None, help="Output path for comparison report.")
def compare(result_a_path, result_b_path, output_path):
    """Compare two evaluation results."""
    result_a = Result.load(Path(result_a_path))
    result_b = Result.load(Path(result_b_path))

    from analysis.significance import compare_runs
    report = compare_runs(result_a, result_b)

    markdown = report.to_markdown()
    click.echo(markdown)

    if output_path:
        Path(output_path).write_text(markdown)
        click.echo(f"\nReport saved to: {output_path}")


@cli.command("new-experiment")
@click.argument("description")
@click.option("--template", "template_dir", default="experiments/template",
              help="Template directory to copy from.")
def new_experiment(description, template_dir):
    """Scaffold a new experiment directory."""
    date_prefix = datetime.now().strftime("%Y-%m")
    slug = description.lower().replace(" ", "-")[:40]
    dirname = f"{date_prefix}-{slug}"
    target = Path("experiments") / dirname

    if target.exists():
        click.echo(f"Error: {target} already exists.", err=True)
        sys.exit(1)

    template = Path(template_dir)
    if template.exists():
        shutil.copytree(template, target)
    else:
        target.mkdir(parents=True, exist_ok=True)
        (target / "results").mkdir(exist_ok=True)

        # Create default config
        save_config({
            "eval": "",
            "model": {"provider": "anthropic", "model_id": "claude-sonnet-4-20250514"},
            "dataset": "",
            "description": description,
        }, target / "config.yaml")

        # Create writeup template
        (target / "writeup.md").write_text(
            f"# Experiment: {description}\n\n"
            f"**Date**: {datetime.now().strftime('%Y-%m-%d')}\n\n"
            "## Hypothesis\n\n\n"
            "## Setup\n\n\n"
            "## Results\n\n\n"
            "## Discussion\n\n\n"
            "## Next Steps\n\n"
        )

    click.echo(f"Created experiment: {target}")


def _load_eval_class(eval_name: str):
    """Dynamically load an eval class from the registry."""
    module_path, class_name = EVAL_REGISTRY[eval_name].rsplit(":", 1)
    import importlib
    module = importlib.import_module(module_path)
    return getattr(module, class_name)


if __name__ == "__main__":
    cli()
