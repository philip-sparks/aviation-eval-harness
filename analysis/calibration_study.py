"""Calibration study: compares LLM judge scores against a second rater.

Loads grounding evaluation results, re-scores a subset with a second rater
(a different LLM acting as a stand-in for human labels), and computes
inter-rater agreement metrics.

Usage:
    python -m analysis.calibration_study \
        --results results_grounding_baseline_v2.json \
        --n 30 \
        --output-dir experiments/calibration-study
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

load_dotenv()


SECOND_RATER_SYSTEM_PROMPT = """You are an independent aviation safety evaluation expert performing a calibration study. You will grade model outputs against source context using a structured rubric.

You must score INDEPENDENTLY — do not try to match what another grader might give. Apply the rubric literally."""


SECOND_RATER_PROMPT = """Grade the following model output on four sub-rubrics, each on a 1-5 scale.

## Rubric Definitions

### Airport Correctness (1-5)
- 5: All airports, ICAO codes, runways correct
- 4: Airport/runway correct, minor location details missing
- 3: Airport correct but runway wrong, or ICAO code wrong
- 2: Partially correct (right city, wrong airport)
- 1: Airport completely wrong or missing

### Event Analysis Quality (1-5)
- 5: Event type correct, all contributing factors identified, causal chain accurate
- 4: Event type correct, most factors identified, minor gaps
- 3: Event type correct but analysis superficial or has errors
- 2: Event type misclassified or significant factual errors
- 1: Event type wrong and analysis unrelated

### Fact Extraction Accuracy (1-5)
- 5: All key facts present and accurate, no fabrication
- 4: Most facts present, one minor inaccuracy or omission
- 3: Some facts present, two or more minor issues
- 2: Few facts present, significant errors
- 1: Key facts mostly absent or wrong, fabrication present

### Flight Phase Relevance (1-5)
- 5: Phase correct, analysis uses phase-appropriate parameters
- 4: Phase correct, one irrelevant reference
- 3: Phase correct but wrong parameters used
- 2: Phase wrong but related
- 1: Phase completely wrong

## Source Context
{context}

## Query
{query}

## Model Output to Grade
{output}

## Instructions
Score each sub-rubric independently. Respond with ONLY a JSON object:
{{"airport_correctness": <1-5>, "event_analysis_quality": <1-5>, "fact_extraction_accuracy": <1-5>, "flight_phase_relevance": <1-5>, "reasoning": "<brief explanation of scores>"}}"""


def load_results(path: str) -> dict:
    """Load evaluation results JSON."""
    with open(path) as f:
        return json.load(f)


def load_dataset_case(case_id: str, dataset_path: str) -> dict | None:
    """Load a specific case from the JSONL dataset by case_id."""
    with open(dataset_path) as f:
        for line in f:
            case = json.loads(line.strip())
            if case.get("case_id") == case_id:
                return case
    return None


def score_with_second_rater(
    adapter, example: dict, dataset_path: str
) -> dict | None:
    """Score an example with the second rater model."""
    case_id = example["example_id"]
    case = load_dataset_case(case_id, dataset_path)
    if case is None:
        return None

    context = case.get("context", "")
    query = case.get("query", "")
    output = example["output"]

    prompt = SECOND_RATER_PROMPT.format(
        context=context, query=query, output=output
    )

    import re

    try:
        response = adapter.generate(prompt, system_prompt=SECOND_RATER_SYSTEM_PROMPT)
        # Parse JSON from response
        json_match = re.search(r'\{[^}]+\}', response.text, re.DOTALL)
        if json_match:
            data = json.loads(json_match.group())
        else:
            data = json.loads(response.text)

        required = [
            "airport_correctness", "event_analysis_quality",
            "fact_extraction_accuracy", "flight_phase_relevance",
        ]
        for key in required:
            if key not in data:
                return None
            data[key] = int(data[key])

        return data
    except Exception as e:
        print(f"  Error scoring {case_id}: {e}", file=sys.stderr)
        return None


def compute_weighted_score(scores: dict) -> float:
    """Compute weighted aggregate score from sub-rubric scores."""
    weights = {
        "airport_correctness": 30,
        "event_analysis_quality": 30,
        "fact_extraction_accuracy": 25,
        "flight_phase_relevance": 15,
    }
    total_weight = sum(weights.values())
    weighted = sum(scores[k] * weights[k] / total_weight for k in weights)
    return weighted / 5.0  # Normalize to 0-1


def run_calibration(
    results_path: str,
    dataset_path: str,
    n_examples: int,
    second_rater_model: str,
    output_dir: str,
) -> None:
    """Run the full calibration study."""
    from models.adapters import create_adapter
    from graders.human_agreement import cohens_kappa, krippendorffs_alpha

    print(f"Loading results from {results_path}...")
    results = load_results(results_path)
    examples = results["examples"]

    # Select n examples, stratified by score range
    examples_sorted = sorted(examples, key=lambda e: e["scores"].get("llm_judge", 0))
    if n_examples < len(examples_sorted):
        # Take evenly spaced examples to get full score range
        indices = [int(i * len(examples_sorted) / n_examples) for i in range(n_examples)]
        selected = [examples_sorted[i] for i in indices]
    else:
        selected = examples_sorted

    print(f"Selected {len(selected)} examples for calibration")
    print(f"Second rater model: {second_rater_model}")

    # Create second rater adapter
    adapter = create_adapter("anthropic", model=second_rater_model, temperature=0.0)

    # Score each example with second rater
    calibration_data = []
    for i, ex in enumerate(selected):
        case_id = ex["example_id"]
        print(f"  [{i+1}/{len(selected)}] Scoring {case_id}...")

        second_scores = score_with_second_rater(adapter, ex, dataset_path)
        if second_scores is None:
            print(f"    Skipped (scoring failed)")
            continue

        # Extract primary judge sub-rubric scores
        judge_subs = ex["grader_results"].get("llm_judge", {}).get("sub_rubrics", {})
        primary_scores = {}
        for key in ["airport_correctness", "event_analysis_quality",
                     "fact_extraction_accuracy", "flight_phase_relevance"]:
            primary_scores[key] = int(judge_subs.get(key, {}).get("score", 0))

        calibration_data.append({
            "case_id": case_id,
            "primary_scores": primary_scores,
            "second_rater_scores": {
                k: second_scores[k] for k in primary_scores
            },
            "primary_aggregate": compute_weighted_score(primary_scores),
            "second_rater_aggregate": compute_weighted_score(second_scores),
            "second_rater_reasoning": second_scores.get("reasoning", ""),
            "model_output_preview": ex["output"][:300],
        })

    if not calibration_data:
        print("ERROR: No examples were successfully scored.")
        sys.exit(1)

    print(f"\nSuccessfully scored {len(calibration_data)} examples")

    # Save calibration dataset
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)

    dataset_out = Path("datasets/calibration")
    dataset_out.mkdir(parents=True, exist_ok=True)
    labels_path = dataset_out / "grounding_human_labels.jsonl"
    with open(labels_path, "w") as f:
        for item in calibration_data:
            f.write(json.dumps(item) + "\n")
    print(f"Calibration dataset saved to {labels_path}")

    # Compute agreement metrics
    print("\n=== Computing agreement metrics ===")

    # Per-sub-rubric agreement
    sub_rubrics = [
        "airport_correctness", "event_analysis_quality",
        "fact_extraction_accuracy", "flight_phase_relevance",
    ]

    report_lines = [
        "# Calibration Study Report",
        "",
        f"**Primary rater**: LLM Judge ({results.get('model_id', 'unknown')})",
        f"**Second rater**: {second_rater_model}",
        f"**Examples evaluated**: {len(calibration_data)}",
        "",
        "## Methodology",
        "",
        "Both raters scored the same model outputs using the grading rubric defined in",
        "`docs/grading_rubric.md`. The primary rater is the LLM judge used during the",
        "grounding evaluation. The second rater is a different model acting as a stand-in",
        "for an independent human rater. This is a known limitation: both raters are LLMs",
        "from the same model family, which may inflate agreement compared to true human-LLM",
        "agreement. Results should be interpreted as an upper bound on inter-rater reliability.",
        "",
        "## Aggregate Agreement",
        "",
    ]

    # Aggregate scores
    primary_agg = [d["primary_aggregate"] for d in calibration_data]
    second_agg = [d["second_rater_aggregate"] for d in calibration_data]

    # Mean absolute error
    mae = sum(abs(p - s) for p, s in zip(primary_agg, second_agg)) / len(calibration_data)
    report_lines.append(f"**Mean absolute error (aggregate)**: {mae:.4f}")

    # Pearson correlation
    mean_p = sum(primary_agg) / len(primary_agg)
    mean_s = sum(second_agg) / len(second_agg)
    cov = sum((p - mean_p) * (s - mean_s) for p, s in zip(primary_agg, second_agg))
    std_p = (sum((p - mean_p) ** 2 for p in primary_agg)) ** 0.5
    std_s = (sum((s - mean_s) ** 2 for s in second_agg)) ** 0.5
    pearson = cov / (std_p * std_s) if std_p * std_s > 0 else 0.0
    report_lines.append(f"**Pearson correlation (aggregate)**: {pearson:.3f}")

    # Binary pass/fail agreement (threshold 0.4)
    primary_pass = [p >= 0.4 for p in primary_agg]
    second_pass = [s >= 0.4 for s in second_agg]
    binary_agree = sum(1 for p, s in zip(primary_pass, second_pass) if p == s)
    report_lines.append(
        f"**Binary pass/fail agreement**: {binary_agree}/{len(calibration_data)} "
        f"({binary_agree/len(calibration_data):.1%})"
    )

    kappa_binary = cohens_kappa(primary_pass, second_pass)
    report_lines.append(f"**Cohen's kappa (binary pass/fail)**: {kappa_binary:.3f}")

    report_lines.extend(["", "## Per-Sub-Rubric Agreement", ""])
    report_lines.append(
        "| Sub-Rubric | Cohen's Kappa | Krippendorff's Alpha | MAE | Primary Mean | Second Mean |"
    )
    report_lines.append("|---|---|---|---|---|---|")

    for sr in sub_rubrics:
        p_scores = [d["primary_scores"][sr] for d in calibration_data]
        s_scores = [d["second_rater_scores"][sr] for d in calibration_data]

        # Cohen's kappa (exact match on 1-5 scale)
        kappa = cohens_kappa(p_scores, s_scores)

        # Krippendorff's alpha (interval)
        alpha = krippendorffs_alpha([p_scores, s_scores], level="interval")

        # MAE
        sr_mae = sum(abs(p - s) for p, s in zip(p_scores, s_scores)) / len(p_scores)

        p_mean = sum(p_scores) / len(p_scores)
        s_mean = sum(s_scores) / len(s_scores)

        report_lines.append(
            f"| {sr} | {kappa:.3f} | {alpha:.3f} | {sr_mae:.2f} | {p_mean:.2f} | {s_mean:.2f} |"
        )

    # Identify top 5 disagreements
    disagreements = []
    for d in calibration_data:
        diff = abs(d["primary_aggregate"] - d["second_rater_aggregate"])
        disagreements.append((diff, d))
    disagreements.sort(key=lambda x: x[0], reverse=True)

    report_lines.extend(["", "## Systematic Patterns", ""])

    # Check for systematic bias
    bias = sum(primary_agg) / len(primary_agg) - sum(second_agg) / len(second_agg)
    if abs(bias) > 0.02:
        direction = "higher" if bias > 0 else "lower"
        report_lines.append(
            f"- Primary rater scores systematically {direction} than second rater "
            f"(mean difference: {bias:+.3f})"
        )
    else:
        report_lines.append("- No systematic scoring bias detected between raters")

    # Check per-rubric bias
    for sr in sub_rubrics:
        p_mean = sum(d["primary_scores"][sr] for d in calibration_data) / len(calibration_data)
        s_mean = sum(d["second_rater_scores"][sr] for d in calibration_data) / len(calibration_data)
        diff = p_mean - s_mean
        if abs(diff) > 0.3:
            direction = "higher" if diff > 0 else "lower"
            report_lines.append(
                f"- Primary rater scores {direction} on {sr} "
                f"(primary {p_mean:.2f} vs second {s_mean:.2f})"
            )

    # Disagreements file
    disagree_lines = [
        "# Top Disagreements Between Raters",
        "",
        f"Showing the {min(5, len(disagreements))} examples with the largest aggregate score difference.",
        "",
    ]

    for i, (diff, d) in enumerate(disagreements[:5]):
        disagree_lines.append(f"## {i+1}. {d['case_id']} (difference: {diff:.3f})")
        disagree_lines.append("")
        disagree_lines.append(f"**Primary aggregate**: {d['primary_aggregate']:.3f}")
        disagree_lines.append(f"**Second rater aggregate**: {d['second_rater_aggregate']:.3f}")
        disagree_lines.append("")
        disagree_lines.append("| Sub-Rubric | Primary | Second |")
        disagree_lines.append("|---|---|---|")
        for sr in sub_rubrics:
            disagree_lines.append(
                f"| {sr} | {d['primary_scores'][sr]} | {d['second_rater_scores'][sr]} |"
            )
        disagree_lines.append("")
        disagree_lines.append(f"**Second rater reasoning**: {d['second_rater_reasoning']}")
        disagree_lines.append("")
        disagree_lines.append(f"**Model output (first 300 chars)**: {d['model_output_preview']}")
        disagree_lines.append("")
        disagree_lines.append("---")
        disagree_lines.append("")

    # Write outputs
    report_path = out / "report.md"
    report_path.write_text("\n".join(report_lines))
    print(f"\nReport saved to {report_path}")

    disagree_path = out / "disagreements.md"
    disagree_path.write_text("\n".join(disagree_lines))
    print(f"Disagreements saved to {disagree_path}")

    # Print summary
    print("\n=== Summary ===")
    print(f"Cohen's kappa (binary): {kappa_binary:.3f}")
    print(f"MAE (aggregate): {mae:.4f}")
    print(f"Pearson correlation: {pearson:.3f}")
    print(f"Mean primary: {sum(primary_agg)/len(primary_agg):.3f}")
    print(f"Mean second: {sum(second_agg)/len(second_agg):.3f}")


def main():
    parser = argparse.ArgumentParser(description="Run calibration study")
    parser.add_argument(
        "--results", default="results_grounding_baseline_v2.json",
        help="Path to grounding results JSON"
    )
    parser.add_argument(
        "--dataset", default="datasets/grounding_cases.jsonl",
        help="Path to grounding cases JSONL"
    )
    parser.add_argument(
        "--n", type=int, default=30,
        help="Number of examples to calibrate"
    )
    parser.add_argument(
        "--second-rater", default="claude-haiku-4-5-20251001",
        help="Model ID for second rater"
    )
    parser.add_argument(
        "--output-dir", default="experiments/calibration-study",
        help="Output directory for reports"
    )
    args = parser.parse_args()

    run_calibration(
        results_path=args.results,
        dataset_path=args.dataset,
        n_examples=args.n,
        second_rater_model=args.second_rater,
        output_dir=args.output_dir,
    )


if __name__ == "__main__":
    main()
