# Aviation Eval Harness

A research-grade agent evaluation harness for aviation safety analysis. Decomposes LLM behavior into five measurable dimensions — grounding, tool use, robustness, refusals, and regression — using multi-layered grading (literal assertions + semantic equivalence + calibrated LLM judge), all reported with bootstrap confidence intervals. Built on lessons from production aviation safety systems where eval improvements drove composite fidelity from 4.85% to 91.9%.

## Quick Start

```bash
# Install
git clone <repo-url> && cd aviation-eval-harness
uv pip install -e ".[dev]"

# Set your API key
export ANTHROPIC_API_KEY=your-key-here

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

| Eval | Model | Score | 95% CI | Notes |
|------|-------|-------|--------|-------|
| Grounding | claude-sonnet-4-20250514 | — | — | Pending initial run |
| Tool Use | claude-sonnet-4-20250514 | — | — | Pending initial run |
| Robustness | claude-sonnet-4-20250514 | — | — | Pending initial run |
| Refusals | claude-sonnet-4-20250514 | — | — | Pending initial run |

*Run `run-eval run --eval <category>` to populate results.*

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
