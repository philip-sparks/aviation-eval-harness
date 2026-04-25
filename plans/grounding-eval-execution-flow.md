# Execution Flow: `run-eval run --eval grounding`

How the grounding evaluation executes end-to-end when you run:

```bash
run-eval run --eval grounding --model anthropic:claude-sonnet-4-20250514 --output results_grounding_baseline.json
```

---

## Phase 1: CLI Bootstrap

### `runners/run_eval.py` (entry point)

The `[project.scripts]` entry in `pyproject.toml` maps `run-eval` to `runners.run_eval:cli`. Click parses the command-line arguments and dispatches to the `run()` command handler.

1. **`load_dotenv()`** (line 21) — Loads `ANTHROPIC_API_KEY` from `.env` into `os.environ`. This avoids manual `export` before each run.

2. **Parse model spec** (lines 69-71) — Splits `"anthropic:claude-sonnet-4-20250514"` into `provider="anthropic"` and `model_id="claude-sonnet-4-20250514"`.

3. **Create model adapter** (line 79) — Calls `create_adapter("anthropic", model="claude-sonnet-4-20250514")`.

### `models/adapters.py`

4. **`create_adapter()`** (line 182) — Factory function. For `provider="anthropic"`, instantiates `AnthropicAdapter`.

5. **`AnthropicAdapter.__init__()`** (lines 63-79) — Reads `ANTHROPIC_API_KEY` from env, creates both sync (`anthropic.Anthropic`) and async (`anthropic.AsyncAnthropic`) clients. Sets `temperature=0.0` and `max_tokens=4096` as defaults.

### `runners/cache.py`

6. **`ResponseCache()`** (line 80 of run_eval.py) — Creates SQLite database at `.eval_cache/responses.db` with a `responses` table keyed by SHA-256 hash of `(model_id, prompt, system_prompt, config)`.

7. **`CachedAdapter(adapter, cache)`** (line 81) — Wraps the `AnthropicAdapter`. On each `generate()` call, checks the cache first. If a cached response exists for the same prompt+config, returns it without an API call. Otherwise, calls through to the real adapter and stores the result.

---

## Phase 2: Eval Setup

### `runners/run_eval.py` (continued)

8. **`_load_eval_class("grounding")`** (line 85) — Looks up `"evals.grounding.grounding_eval:GroundingEval"` in `EVAL_REGISTRY`, dynamically imports the module, and returns the class.

9. **Instantiate eval** (lines 88-90) — Creates `GroundingEval(judge_adapter=adapter)`, passing the same model adapter so the LLM judge can make API calls.

### `evals/grounding/grounding_eval.py`

10. **`GroundingEval.__init__()`** (lines 37-62) — Sets up four graders:

    | Grader | Source File | Purpose |
    |--------|------------|---------|
    | `ContainsGrader` | `graders/rule_based.py:16` | Exact case-insensitive substring match for each `expected_facts` entry |
    | `NotContainsGrader` | `graders/rule_based.py:42` | Anti-hallucination — fails if any `negative_facts` appear in output |
    | `SemanticEquivalenceGrader` | `graders/rule_based.py:157` | Substring match with synonym expansion from `SEMANTIC_EQUIVALENCES` |
    | `LLMJudgeGrader` | `graders/llm_judge.py` | LLM-as-judge with 4 weighted sub-rubrics (30/30/25/15) |

11. **`create_grounding_sub_rubrics()`** (`graders/llm_judge.py`) — Returns four sub-rubric definitions used by the LLM judge:
    - `airport_correctness` (weight 30)
    - `event_analysis_quality` (weight 30)
    - `fact_extraction_accuracy` (weight 25)
    - `flight_phase_relevance` (weight 15)

### `evals/base.py`

12. **`Eval.load_dataset()`** — Reads `datasets/grounding_cases.jsonl` line-by-line, `json.loads()` each line into a dict. Returns a list of 60 case dicts.

### `datasets/grounding_cases.jsonl`

13. **Dataset schema** — Each case contains:
    ```json
    {
      "case_id": "GND-ASRS-001",
      "category": "unstable_approach",
      "source_type": "ASRS",
      "difficulty": "easy|medium|hard",
      "context": "...(narrative text)...",
      "query": "What factors made this approach unstable...?",
      "expected_facts": ["airspeed was 15 knots above Vref", ...],
      "negative_facts": ["the approach was to RWY 36L", ...],
      "semantic_equivalences": {"go-around": ["missed approach", ...]}
    }
    ```

---

## Phase 3: Evaluation Loop

### `evals/grounding/grounding_eval.py` — `run()` method (line 64)

14. **Iterates over all 60 cases**, calling `run_single(adapter, case)` for each.

### `run_single()` (line 113)

For each case:

15. **Construct prompt** (line 117):
    ```
    Source Context:
    {context}

    Question: {query}

    Provide a thorough analysis.
    ```

16. **Call model** (line 118) — `adapter.generate(prompt, system_prompt=SYSTEM_PROMPT)` flows through:
    - `CachedAdapter.generate()` → checks SQLite cache
    - On cache miss: `AnthropicAdapter.generate()` → `anthropic.Anthropic.messages.create()` → Anthropic API
    - Returns `ModelResponse(text=..., model_id=..., usage={input_tokens, output_tokens}, latency_ms=...)`

17. **Grade with all 4 graders** (lines 122-127):

    **a. `ContainsGrader.grade()`** (`graders/rule_based.py:19`) — For each string in `expected_facts`, checks if `fact.lower() in output.lower()`. Returns score = found/total, passed = all found.

    **b. `NotContainsGrader.grade()`** (`graders/rule_based.py:45`) — For each string in `negative_facts`, checks it does NOT appear. Returns score = clean/total, passed = no violations.

    **c. `SemanticEquivalenceGrader.grade()`** (`graders/rule_based.py:167`) — Same as contains but first expands each fact through `SEMANTIC_EQUIVALENCES` from `evals/aviation_domain.py`. E.g., if expected fact contains "TCAS RA", also checks for "TCAS Resolution Advisory", "resolution advisory", etc.

    **d. `LLMJudgeGrader.grade()`** (`graders/llm_judge.py`) — For each of the 4 sub-rubrics:
    - Constructs a judge prompt with the rubric, output text, and context
    - Calls `adapter.generate()` (another API call per sub-rubric = 4 calls per case)
    - Parses JSON response `{"score": 1-5, "reasoning": "..."}`
    - Computes weighted average: `sum(score/5 * weight/100)` across sub-rubrics

18. **Determine pass/fail** (lines 144-151):
    ```python
    factual_ok = (
        contains_result.passed
        or semantic_result.passed
        or judge_result.passed
        or semantic_result.score >= 0.5
    )
    passed = not_contains_result.passed and factual_ok
    ```
    Must have zero hallucinations AND at least one grader confirms factual coverage.

19. **Return `ExampleResult`** — Wraps all scores, grader details, pass/fail, and model output into a dataclass.

---

## Phase 4: Aggregation and Output

### `evals/grounding/grounding_eval.py` — `run()` (continued)

20. **Compute aggregate metrics** (lines 96-106):
    - `grounding_accuracy`: mean of `max(contains, semantic)` across examples
    - `llm_judge`: mean LLM judge score
    - `hallucination_rate`: fraction of examples with negative fact violations
    - `grader_agreement_rate`: % where contains and judge agree on pass/fail
    - `pass_rate`: fraction of examples that passed overall

21. **Return `Result`** — Dataclass from `evals/base.py` with eval_name, model_id, timestamp, all examples, aggregate metrics.

### `runners/run_eval.py` — back in `run()` command

22. **Bootstrap CIs** (lines 101-118) — For each aggregate metric, extracts per-example scores via metric-specific extractors, then calls `bootstrap_ci()`.

### `analysis/significance.py`

23. **`bootstrap_ci(scores)`** — Resamples the score array 10,000 times with replacement, computes the mean of each resample, returns the 2.5th and 97.5th percentiles as the 95% confidence interval.

### `runners/run_eval.py` — final output

24. **`result.to_summary()`** (line 111) — Prints human-readable summary with metrics and CIs.

25. **`result.save(Path(output_path))`** (line 117) — Serializes the full `Result` (all 60 examples with scores, grader details, model outputs) to JSON.

---

## API Call Count

For 60 grounding cases:
- **60 model calls** for generating responses (1 per case)
- **240 judge calls** for LLM judge sub-rubrics (4 per case)
- **Total: ~300 API calls**

With caching enabled, a second run with the same prompts and model hits the SQLite cache and makes zero API calls.

---

## Files NOT Used in This Flow

These files exist in the project but are not invoked during the grounding eval:

| File | Purpose |
|------|---------|
| `graders/human_agreement.py` | Cohen's kappa and Krippendorff's alpha for comparing two sets of human/grader labels. Used in calibration studies and disagreement reports, not during eval runs. |
| `runners/promptfoo_config.py` | Generates Promptfoo-compatible YAML config files. An alternative execution path — instead of our native runner, you can export configs for Promptfoo to execute. |
| `runners/promptfoo_provider.py` | Custom Promptfoo provider script (`call_api` entry point). Only used when running evals through Promptfoo rather than our CLI. |
| `runners/parallel.py` | `ParallelRunner` with asyncio for concurrent eval execution. The current `run()` method processes cases sequentially; this module enables batch parallelism for future use. |
| `evals/tool_use/` | Tool selection/sequencing eval. Only loaded when `--eval tool_use`. |
| `evals/robustness/` | Perturbation robustness eval. Only loaded when `--eval robustness`. |
| `evals/refusals/` | Refusal boundary eval. Only loaded when `--eval refusals`. |
| `evals/regression/` | Cross-version comparison eval. Used via the `compare` CLI command, not `run`. |
| `analysis/failure_clustering.py` | Clusters failed examples by TF-IDF/embedding similarity to identify failure themes. Post-hoc analysis tool, not part of the eval pipeline. |
| `analysis/dashboards/report.py` | Generates self-contained HTML reports with embedded matplotlib charts. Post-hoc reporting tool. |
| `datasets/generators/` | Synthetic METAR, ADS-B track, and scenario generators. Used to create datasets, not during eval runs. |
| `datasets/tool_use_cases.jsonl` | Dataset for tool_use eval. |
| `datasets/adversarial_prompts.jsonl` | Dataset for robustness eval. |
| `datasets/refusal_cases.jsonl` | Dataset for refusals eval. |
| `evals/aviation_domain.py` | Domain constants (airports, event types, tolerances). Partially used — `SEMANTIC_EQUIVALENCES` is loaded by `SemanticEquivalenceGrader`, and `GROUNDING_RUBRIC_WEIGHTS` by `create_grounding_sub_rubrics()`. The rest (airport coordinates, event taxonomy, numeric tolerances) supports other evals. |
| `evals/config.py` | YAML/JSON config file loader. Only used when `--config` is passed to override defaults. |
