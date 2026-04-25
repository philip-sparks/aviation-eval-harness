# Aviation Eval Harness

A research-grade agent evaluation harness for aviation safety analysis. Decomposes LLM behavior into five measurable dimensions — grounding, tool use, robustness, refusals, and regression — using multi-layered grading (literal assertions + semantic equivalence + calibrated LLM judge), all reported with bootstrap confidence intervals. Built on lessons from production aviation safety systems where eval improvements drove composite fidelity from 4.85% to 91.9%.

## Motivation

This project grew out of [Blazer](https://github.com/philip-sparks/blazer), a production aviation safety report generation system that processes real-time ADS-B detection events and produces safety analysis reports for ISAM (a safety review platform). Blazer uses a LlamaIndex-powered agent with specialized tools — weather lookups, runway verification, aircraft data, waypoint validation — to analyze events from the ASAIC pipeline (Airport Safety Analysis & Intelligence Capability).

**The problem we hit**: when Blazer first ran against 100 real ASAIC events, composite fidelity was **4.85%**. The agent was hallucinating airports, guessing runways instead of extracting them from structured data, and producing boilerplate analysis that ignored event-specific context. Manual "vibe checking" wasn't catching these failures — we needed automated, granular measurement.

**What fixed it**: three changes drove fidelity from 4.85% to **91.9%**:

1. **Making data visible** — injecting structured OPERATIONS data (runway, aircraft type, callsign) directly into the agent prompt with explicit instructions not to guess. This alone moved runway detection from 27% to 99%.
2. **Splitting the rubric** — replacing a single pass/fail score with four weighted sub-rubrics: airport correctness (30%), event analysis quality (30%), fact extraction accuracy (25%), and flight phase relevance (15%). This revealed that the agent was acing airport identification but failing on event-specific analysis.
3. **Deterministic extraction before LLM** — regex-based extraction of runways, altitudes, and aircraft types from narratives, verified against authoritative sources before the LLM ever sees them. The key insight: verification tools that return `MISMATCH` status force the agent to use ground truth instead of its own (often wrong) inference.

**Why a standalone harness**: Blazer's eval tooling was tightly coupled to its Promptfoo/Grafana stack and couldn't easily measure semantic equivalence ("TCAS RA" = "resolution advisory"), compare across model providers, or generate CI/CD artifacts with pass/fail gates. We needed a framework that could:

- Grade with multiple layers (literal assertions catch exact facts, LLM judge catches paraphrased correctness, anti-hallucination checks catch fabricated details)
- Report uncertainty (bootstrap confidence intervals on every metric)
- Detect regressions across model versions with paired statistical tests
- Cluster failure modes to identify systematic weaknesses
- Run against any model provider through a clean adapter interface

This repo extracts those patterns into a general-purpose harness, with datasets inspired by real ASRS reports, NTSB investigations, and FAR regulatory scenarios.

## Quick Start

```bash
# Install
git clone <repo-url> && cd aviation-eval-harness
uv pip install -e ".[dev]"

# Set your API key (auto-loaded from .env)
echo "ANTHROPIC_API_KEY=your-key-here" > .env

# Run one eval
run-eval run --eval grounding --model anthropic:claude-sonnet-4-20250514

# Compare two results
run-eval compare results_a.json results_b.json

# Scaffold a new experiment
run-eval new-experiment "grounding-baseline"
```

## Project Structure

```
aviation-eval-harness/
├── evals/                    # Eval implementations
│   ├── base.py               #   Abstract Eval class, Result schema
│   ├── aviation_domain.py    #   Domain constants (events, airports, tolerances)
│   ├── config.py             #   Config loader
│   ├── grounding/            #   Fact attribution eval
│   ├── tool_use/             #   Tool selection/sequencing eval
│   ├── robustness/           #   Perturbation robustness eval
│   ├── refusals/             #   Refusal boundary eval
│   └── regression/           #   Cross-version comparison
├── datasets/                 # JSONL datasets + synthetic generators
│   ├── grounding_cases.jsonl
│   ├── tool_use_cases.jsonl
│   ├── adversarial_prompts.jsonl
│   ├── refusal_cases.jsonl
│   └── generators/           #   METAR, ADS-B track, scenario generators
├── graders/                  # Grading infrastructure
│   ├── rule_based.py         #   Contains, not-contains, numeric, regex, semantic
│   ├── llm_judge.py          #   LLM-as-judge with calibration
│   └── human_agreement.py    #   Cohen's kappa, Krippendorff's alpha
├── runners/                  # Execution infrastructure
│   ├── run_eval.py           #   CLI entry point
│   ├── promptfoo_config.py   #   Promptfoo YAML generation
│   ├── promptfoo_provider.py #   Custom Promptfoo provider
│   ├── cache.py              #   SQLite response cache
│   └── parallel.py           #   Async parallel runner
├── analysis/                 # Analysis tools
│   ├── significance.py       #   Bootstrap CIs, paired comparison
│   ├── failure_clustering.py #   Embed + cluster failure modes
│   └── dashboards/report.py  #   Static HTML reports
├── models/
│   └── adapters.py           #   ModelAdapter ABC + AnthropicAdapter
├── experiments/              # Dated experiment logs
├── docs/                     # Methodology and threat model
└── tests/                    # pytest suite
```

## Results

Baseline run on `claude-sonnet-4-20250514` (April 2026):

| Eval | Primary Metric | Score | 95% CI | N | Notes |
|------|---------------|-------|--------|---|-------|
| Grounding | LLM Judge (weighted sub-rubrics) | **0.924** | [0.890, 0.954] | 60 | 0% hallucination rate |
| Tool Use | Tool Selection Accuracy | **0.986** | [0.914, 1.000] | 35 | 1 failure (argument accuracy on dual-aircraft query) |
| Robustness | Mean Output Similarity | **0.303** | — | 35 | Typo most robust (0.47), conflicting METAR least (0.15) |
| Refusals | Accuracy | **0.680** | [0.480, 0.840] | 25 | 0% over-refusal, 100% under-refusal on refuse cases |

### Grounding Detail

| Sub-Metric | Score |
|-----------|-------|
| LLM Judge (aggregate) | 0.924 |
| Hallucination Rate | 0.000 |
| Verbatim Fact Match | 0.042 |
| Pass Rate | 100% |

The model produces excellent factual analyses but paraphrases heavily — verbatim substring matching captures only 4.2% of expected facts while the LLM judge confirms 92.4% factual coverage. This validates the multi-layered grading design.

### Tool Use Detail

| Sub-Metric | Score |
|-----------|-------|
| Tool Selection | 0.986 |
| Argument Accuracy | 0.902 |
| Sequence Accuracy | 1.000 |
| Pass Rate | 97.1% |

### Robustness Detail (Output Similarity by Perturbation Type)

| Perturbation | Avg Similarity | Interpretation |
|-------------|---------------|----------------|
| Typo | 0.469 | Most robust — typos barely affect output |
| Nearby Airport Swap | 0.371 | Expected — different airports yield different content |
| Paraphrase | 0.297 | Model varies prose structure for same-meaning prompts |
| Synonym | 0.282 | Similar to paraphrase |
| Distractor Injection | 0.226 | Distractors shift output focus |
| Conflicting METAR | 0.150 | Expected — conflicting data should change analysis |

Note: Jaccard word overlap is a conservative metric for long-form text. The model's tendency to vary prose structure contributes to lower similarity scores even when content is semantically equivalent.

### Refusals Detail

| Sub-Metric | Score |
|-----------|-------|
| Accuracy | 68.0% |
| Over-Refusal Rate | 0.0% |
| Under-Refusal Rate | 100% |
| Borderline Accuracy | 100% |

The model correctly answers all legitimate safety questions and handles all borderline/hedge cases, but answers all 8 "should refuse" cases (speculation/blame attribution) instead of declining.

*Run `run-eval run --eval <category>` to reproduce these results.*

## Eval Categories

### Grounding
Measures whether generated claims are supported by provided aviation safety context. Uses dual graders (rule-based + LLM judge) with agreement tracking. Anti-hallucination checks prevent wrong airports, altitudes, and aircraft types.

### Tool Use
Evaluates correct tool selection, argument shaping, and call sequencing across 6 aviation mock tools (METAR lookup, track query, regulation search, airport info, NOTAM check, aircraft info). Each case includes distractor tools.

### Robustness
Measures score *degradation* (not raw accuracy) under 6 perturbation types: paraphrase, typo, distractor injection, synonym swap, nearby airport swap, and conflicting METAR injection.

### Refusals
Tests the model's boundary between answering and refusing. Covers legitimate safety questions (should answer), speculation/blame (should refuse), and ambiguous causal attribution (should hedge).

### Regression
Compares two result sets with paired bootstrap significance tests and per-example diff reports.

## Key Design Decisions

- **Multi-layered grading**: Literal assertions + semantic equivalence + LLM judge, inspired by the Blazer eval system's 30/30/25/15 weighted sub-rubrics
- **Calibrated thresholds**: LLM judge uses threshold 0.4 for partial credit (strict binary grading misses nuanced improvements)
- **Semantic equivalence**: "TCAS RA" = "TCAS Resolution Advisory" = "resolution advisory" — prevents false negatives from phrasing variation
- **Anti-hallucination**: Every grounding case includes negative_facts (wrong airports, wrong aircraft) that must NOT appear
- **Bootstrap CIs on everything**: No point estimates without uncertainty quantification

## Known Limitations

1. **Single-turn only**: All evaluations use single-turn interactions. Multi-turn conversation quality is not measured.
2. **English only**: All datasets and prompts are English. No cross-lingual evaluation.
3. **Synthetic data**: While based on real aviation patterns, synthetic cases may not capture the full complexity of real safety events.
4. **LLM judge circularity**: Using an LLM to judge another LLM has known biases (e.g., verbosity preference, position bias). Calibration study partially addresses this but does not eliminate it.
5. **Limited model coverage**: Only Anthropic Claude models are implemented in v1. The adapter interface supports others but they are not tested.
6. **Small dataset sizes**: 50-100 grounding cases is sufficient for evaluation but too small for distribution-level conclusions.
7. **No cost tracking**: Token usage is recorded but cost comparison across models is not automated.
8. **Determinism**: Temperature 0 does not guarantee identical outputs across API calls. Response caching provides reproducibility within a run.

## Adding a New Eval

1. Create a directory under `evals/` (e.g., `evals/my_eval/`)
2. Implement `class MyEval(Eval)` with `run()` and `run_single()` methods
3. Create a JSONL dataset under `datasets/`
4. Register in `runners/run_eval.py:EVAL_REGISTRY`

## Adding a New Model Provider

1. Implement `class MyAdapter(ModelAdapter)` in `models/adapters.py`
2. Register in `create_adapter()` factory function
3. No changes needed to eval or runner code

## Documentation

- [Methodology](docs/methodology.md) — What we measure, how, and why
- [Threat Model](docs/threat-model.md) — Failure modes the suite detects
- [Datasets](datasets/README.md) — Schema, provenance, and labeling process
