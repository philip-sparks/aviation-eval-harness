# Reproducibility

This document provides everything needed to reproduce the results reported in the README.

## Model Versions

All baseline results were produced with:

| Role | Model | Version |
|------|-------|---------|
| Model under test | Claude Sonnet | `claude-sonnet-4-20250514` |
| Primary LLM judge | Claude Sonnet | `claude-sonnet-4-20250514` |
| Calibration second rater | Claude Haiku | `claude-haiku-4-5-20251001` |

Temperature is set to 0.0 for all API calls. Temperature 0 does not guarantee deterministic outputs from the API; the SQLite response cache (`runners/cache.py`) provides exact reproducibility for cached runs.

## Random Seeds

| Component | Seed | Location |
|-----------|------|----------|
| Bootstrap confidence intervals | 42 | `analysis/significance.py` |
| Dataset generators | configurable | `datasets/generators/generate_scenarios.py` |

## Dataset Checksums

Verify dataset integrity with `sha256sum datasets/*.jsonl datasets/calibration/*.jsonl`:

| File | SHA256 |
|------|--------|
| `datasets/grounding_cases.jsonl` | `1166ba35a18cff7f5b7939cae094a6bac8b13491ee43d06e6e17a9812d050fde` |
| `datasets/tool_use_cases.jsonl` | `dfa2834e19e2577561532a818b5b80e2d063fcb16d400aa01399107ad35cda3c` |
| `datasets/adversarial_prompts.jsonl` | `d5c1738b068b1afce880c3311941f28cdfae657754d1f64508f8a508728fb5c6` |
| `datasets/refusal_cases.jsonl` | `7f871d57fecc212bfbd77e4c8b760eddef08643f939709e786ab8875ad3f64d7` |
| `datasets/calibration/grounding_human_labels.jsonl` | `86a7e4233dff783565ed7955091f7776bd5dffd1af20c8204c993ff2b4360754` |

## Reproduce Commands

### Prerequisites

```bash
git clone <repo-url> && cd aviation-eval-harness
uv pip install -e ".[dev]"
echo "ANTHROPIC_API_KEY=your-key-here" > .env
```

### Individual Evals

```bash
# Grounding (N=60) -~2 min, ~$0.50
run-eval run --eval grounding --output results_grounding.json

# Tool Use (N=35) -~1 min, ~$0.30
run-eval run --eval tool_use --output results_tool_use.json

# Robustness (N=35, runs 2x per case) -~3 min, ~$0.60
run-eval run --eval robustness --output results_robustness.json

# Refusals (N=25) -~1 min, ~$0.25
run-eval run --eval refusals --output results_refusals.json
```

### Calibration Study

```bash
# Requires grounding results to exist first
python -m analysis.calibration_study --results results_grounding.json --n 30
```

### Full Reproduction

```bash
# Run all evals and calibration in sequence
./scripts/reproduce.sh
```

## Expected Results

Results should match the README within normal API variance. With the response cache enabled (default), re-runs against cached data will produce identical results. Fresh API calls may show minor variation due to non-deterministic API behavior at temperature 0.

| Eval | Primary Metric | Expected Score | Expected 95% CI |
|------|---------------|----------------|-----------------|
| Grounding | LLM Judge (weighted) | 0.924 | [0.890, 0.954] |
| Tool Use | Tool Selection Accuracy | 0.986 | [0.914, 1.000] |
| Robustness | Embedding Cosine Similarity | 0.784 | -|
| Refusals | Accuracy (semantic) | 0.920 | [0.800, 1.000] |

## Approximate Cost

A full reproduction run (all 4 evals + calibration) costs approximately $2-3 in API credits and takes 8-10 minutes with default concurrency (5 parallel calls).
