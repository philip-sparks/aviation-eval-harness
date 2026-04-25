# Aviation Eval Harness

A research-grade agent evaluation harness for aviation safety analysis. Decomposes LLM behavior into five measurable dimensions — grounding, tool use, robustness, refusals, and regression — using multi-layered grading (literal assertions + semantic equivalence + calibrated LLM judge), all reported with bootstrap confidence intervals. Built on lessons from production aviation safety systems where eval improvements drove composite fidelity from 4.85% to 91.9%.

## Motivation

This project grew out of a production aviation safety report generation system built for a US Government agency. The system processes real-time ADS-B detection events and produces safety analysis reports using a LlamaIndex-powered agent with specialized tools — weather lookups, runway verification, aircraft data, waypoint validation — to analyze airport safety events as they occur.

**The problem we hit**: when the system first ran against 100 real safety events, composite fidelity was **4.85%**. The agent was hallucinating airports, guessing runways instead of extracting them from structured data, and producing boilerplate analysis that ignored event-specific context. Manual "vibe checking" wasn't catching these failures — we needed automated, granular measurement.

**What fixed it**: three changes drove fidelity from 4.85% to **91.9%**:

1. **Making data visible** — injecting structured operations data (runway, aircraft type, callsign) directly into the agent prompt with explicit instructions not to guess. This alone moved runway detection from 27% to 99%.
2. **Splitting the rubric** — replacing a single pass/fail score with four weighted sub-rubrics: airport correctness (30%), event analysis quality (30%), fact extraction accuracy (25%), and flight phase relevance (15%). This revealed that the agent was acing airport identification but failing on event-specific analysis.
3. **Deterministic extraction before LLM** — regex-based extraction of runways, altitudes, and aircraft types from narratives, verified against authoritative sources before the LLM ever sees them. The key insight: verification tools that return `MISMATCH` status force the agent to use ground truth instead of its own (often wrong) inference.

**Why a standalone harness**: the production system's eval tooling was tightly coupled to its Promptfoo/Grafana stack and couldn't easily measure semantic equivalence ("TCAS RA" = "resolution advisory"), compare across model providers, or generate CI/CD artifacts with pass/fail gates. We needed a framework that could:

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

- **Multi-layered grading**: Literal assertions + semantic equivalence + LLM judge, with 30/30/25/15 weighted sub-rubrics derived from the production system
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

## Conclusions

### Key Findings

**1. Literal matching is 22x worse than semantic grading — and this understates the gap.**
On the same 60 model outputs, exact substring matching found 4.2% of expected facts while the LLM judge confirmed 92.4% factual coverage. This isn't a marginal difference — it's the difference between "system is broken" and "system is production-ready." Any eval framework that relies solely on string matching will dramatically undercount model capability on open-ended generation tasks. The implication for practitioners: if your eval shows surprisingly low scores, your grader may be the problem, not your model.

**2. Models refuse correctly but explain too much, defeating keyword classifiers.**
Our refusals eval initially reported 100% under-refusal — the model seemingly never refuses. But inspecting the outputs revealed the model *is* refusing (e.g., "I cannot and will not attempt to identify the reporting pilot"). It then explains *why* at length, producing 200+ word responses that defeat the keyword-plus-short-response heuristic. This is a known but under-documented failure mode in refusal evaluation: safety-trained models are verbose refusers, and any classifier that equates long responses with compliance will miscount. This suggests refusal detection needs semantic classification, not keyword matching.

**3. Sub-rubric decomposition reveals capability topology that single scores hide.**
The grounding eval's four sub-rubrics (scored 1-5) show a non-uniform capability profile: flight phase relevance (4.95) and fact extraction (4.83) are near-ceiling, while airport correctness (4.43) and event analysis quality (4.47) have meaningful variance (stdev 1.14 and 1.21 respectively). A single "grounding score" of 92.4% would mask that the model has a specific weakness in airport identification and event-specific analysis. For anyone building domain-specific evals: decompose your rubric. The weighted sub-rubric pattern (30/30/25/15) borrowed from our production system was the single most impactful eval design decision.

**4. Tool sequencing is solved; argument shaping is the remaining frontier.**
The model achieved 100% sequence accuracy (always calls the right tools in the right order) and 98.6% tool selection accuracy, but argument accuracy lagged at 90.2%. The single failure was on a dual-aircraft track query where the model needed to construct multiple argument sets. This decomposition — selection vs. arguments vs. sequence — is more actionable than a single "tool use score" because it tells you *what* to fix.

**5. Low robustness similarity scores measure prose variation, not factual disagreement.**
Jaccard word overlap of 0.30 across perturbation types initially looks alarming, but it reflects the model's tendency to restructure prose rather than change facts. The perturbation-type breakdown is more informative: typo resilience (0.47) confirms the model handles surface noise well, while conflicting METAR similarity (0.15) confirms the model *correctly* changes its analysis when given contradictory data. This is a methodological caution: output-level similarity metrics on long-form text conflate stylistic variation with factual disagreement. Embedding-based semantic similarity would separate these.

**6. Zero hallucinations is achievable in constrained domains.**
Across 60 grounding cases with explicit negative facts (wrong airports, wrong aircraft types, wrong altitudes), the model produced zero hallucinations. This was tested with targeted anti-hallucination checks, not just general quality assessment. The combination of constrained context (source material provided in the prompt) and explicit system instructions ("base your analysis only on the information given") appears effective for aviation safety analysis.

### Next Steps

1. **Embedding-based robustness scoring** — Replace Jaccard word overlap with sentence-transformer cosine similarity to separate stylistic variation from factual disagreement.
2. **Semantic refusal classifier** — Replace keyword heuristics with an LLM judge for refusal detection, since safety-trained models produce verbose refusals that defeat pattern matching.
3. **Multi-model comparison** — Run the same eval suite against GPT-4, Gemini, and open-source models to produce cross-provider benchmarks. The adapter interface supports this; only new `ModelAdapter` implementations are needed.
4. **Human calibration study** — Have domain experts grade a subset of outputs and compute Cohen's kappa against the LLM judge to quantify judge reliability. The `graders/human_agreement.py` module is built for this.
5. **Larger datasets** — Scale from 60 grounding cases to 200+ with stratified sampling across event types, difficulty levels, and source types to support distribution-level conclusions.
6. **CI/CD integration** — Wire `run-eval` into GitHub Actions with pass/fail gates on regression detection, enabling automated quality assurance on model upgrades.
7. **Cost tracking** — Token usage is already recorded per response; add cost estimation to enable cost-quality tradeoff analysis across models and configurations.

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
