## Relevant Files

- `pyproject.toml` - Project packaging, dependencies, and CLI entry points
- `evals/__init__.py` - Eval package init, registry of available eval categories
- `evals/base.py` - Abstract `Eval` class, `Result` and `ExampleResult` dataclasses
- `evals/grounding/__init__.py` - Grounding eval implementation
- `evals/grounding/grounding_eval.py` - `GroundingEval` class implementing `Eval`
- `evals/tool_use/__init__.py` - Tool use eval implementation
- `evals/tool_use/tool_use_eval.py` - `ToolUseEval` class, mock tool definitions
- `evals/tool_use/mock_tools.py` - Aviation mock tool schemas and simulated responses
- `evals/robustness/__init__.py` - Robustness eval implementation
- `evals/robustness/robustness_eval.py` - `RobustnessEval` class, perturbation engine
- `evals/robustness/perturbations.py` - Perturbation templates and generators
- `evals/refusals/__init__.py` - Refusals eval implementation
- `evals/refusals/refusals_eval.py` - `RefusalsEval` class
- `evals/regression/__init__.py` - Regression eval implementation
- `evals/regression/regression_eval.py` - `RegressionEval` class, diff report generation
- `models/__init__.py` - Models package init
- `models/adapters.py` - Abstract `ModelAdapter`, `AnthropicAdapter`, response dataclasses
- `datasets/README.md` - Dataset provenance, schemas, labeling process, known issues
- `datasets/grounding_cases.jsonl` - 50-100 aviation grounding test cases
- `datasets/adversarial_prompts.jsonl` - 30-50 robustness perturbation templates
- `datasets/tool_use_cases.jsonl` - 30-50 tool use scenarios
- `datasets/refusal_cases.jsonl` - 20-30 refusal boundary cases
- `datasets/generators/__init__.py` - Generators package init
- `datasets/generators/generate_tracks.py` - Synthetic ADS-B track generator
- `datasets/generators/generate_metar.py` - Synthetic METAR string generator
- `datasets/generators/generate_scenarios.py` - Composite scenario generator
- `graders/__init__.py` - Graders package init
- `graders/llm_judge.py` - LLM-as-judge with rubric, calibration study logic
- `graders/rule_based.py` - Deterministic graders (contains, numeric tolerance, regex, anti-hallucination)
- `graders/human_agreement.py` - Inter-rater agreement (Cohen's kappa, Krippendorff's alpha)
- `runners/__init__.py` - Runners package init
- `runners/run_eval.py` - CLI entry point wrapping Promptfoo
- `runners/parallel.py` - Async/batched model call orchestration
- `runners/cache.py` - Response caching layer for reproducibility
- `runners/promptfoo_config.py` - Programmatic Promptfoo YAML config generation
- `runners/promptfoo_provider.py` - Custom Promptfoo provider calling model adapters
- `analysis/__init__.py` - Analysis package init
- `analysis/significance.py` - Bootstrap CIs, paired bootstrap comparison tests
- `analysis/failure_clustering.py` - Embedding + clustering of failed examples
- `analysis/dashboards/report.py` - Static HTML/matplotlib result visualization
- `docs/methodology.md` - What is measured, why, how cases were constructed
- `docs/threat-model.md` - Failure modes the eval suite catches, by severity
- `docs/results/` - Experiment writeups directory
- `experiments/template/` - Experiment directory template (config, results, writeup)
- `tests/test_base.py` - Tests for Eval base class and Result schema
- `tests/test_adapters.py` - Tests for model adapter interface and AnthropicAdapter
- `tests/graders/test_rule_based.py` - Tests for rule-based graders
- `tests/graders/test_llm_judge.py` - Tests for LLM judge grader
- `tests/graders/test_human_agreement.py` - Tests for inter-rater agreement
- `tests/runners/test_cache.py` - Tests for response caching
- `tests/runners/test_promptfoo_config.py` - Tests for config generation
- `tests/analysis/test_significance.py` - Tests for bootstrap CI computation
- `tests/analysis/test_failure_clustering.py` - Tests for failure clustering
- `tests/datasets/test_generators.py` - Tests for synthetic data generators
- `README.md` - Project pitch, results table, quick-start, known limitations

### Notes

- Unit tests should be placed in `tests/` mirroring the source structure (e.g., `tests/test_base.py`, `tests/graders/test_rule_based.py`).
- Use `pytest` to run tests. Running `pytest` without arguments executes all tests.
- Promptfoo configs are generated programmatically — do not hand-edit YAML files.
- All paths above are relative to the project root (`agent-evals/` or repo root depending on final layout decision).
- Aviation domain constants (event types, airport coordinates, semantic equivalence rules) should be centralized in a `evals/aviation_domain.py` or similar shared module.

## Instructions for Completing Tasks

**IMPORTANT:** As you complete each task, you must check it off in this markdown file by changing `- [ ]` to `- [x]`. This helps track progress and ensures you don't skip any steps.

Example:
- `- [x]1.1 Read file` → `- [x] 1.1 Read file` (after completing)

Update the file after completing each sub-task, not just after completing an entire parent task.

## Tasks

- [x]0.0 Create feature branch
  - [x]0.1 Create and checkout a new branch for this feature (e.g., `git checkout -b feature/agent-eval-harness`)

- [x]1.0 Scaffold project structure and packaging
  - [x]1.1 Create the full directory tree as specified in PRD Section 4.1: `evals/`, `evals/grounding/`, `evals/tool_use/`, `evals/robustness/`, `evals/refusals/`, `evals/regression/`, `datasets/`, `datasets/generators/`, `graders/`, `runners/`, `analysis/`, `analysis/dashboards/`, `models/`, `tests/`, `tests/graders/`, `tests/runners/`, `tests/analysis/`, `tests/datasets/`, `experiments/`, `docs/`, `docs/results/`
  - [x]1.2 Create `pyproject.toml` with project metadata, Python 3.10+ requirement, and dependencies: `anthropic`, `pyyaml`, `click` (CLI), `scipy`, `scikit-learn`, `sentence-transformers`, `matplotlib`, `numpy`. Include optional dev dependencies: `pytest`, `pytest-asyncio`, `ruff`. Define CLI entry point `run-eval = "runners.run_eval:cli"`
  - [x]1.3 Add `__init__.py` files to all Python packages: `evals/`, `evals/grounding/`, `evals/tool_use/`, `evals/robustness/`, `evals/refusals/`, `evals/regression/`, `models/`, `datasets/generators/`, `graders/`, `runners/`, `analysis/`, `analysis/dashboards/`
  - [x]1.4 Create `.gitignore` with Python defaults, `.env`, `__pycache__/`, `.promptfoo_cache/`, `experiments/*/results/`, `*.jsonl` exclusions (except committed dataset files)
  - [x]1.5 Create a shared aviation domain constants module (`evals/aviation_domain.py`) containing: event type taxonomy (SST, REX, IRT, RWT, MAR, RRS, UA, TCAS_RA), airport coordinate lookup table (KOKC, KIAD, KDFW, KATL, KJFK, KORD, KSFO, KLAS, KPDX, KSNA and others), semantic equivalence dictionaries (event type synonyms), and standard numeric tolerances (altitude ±500ft, descent rate ±200fpm, heading ±10deg)

- [x]2.0 Build core infrastructure (base classes, result schema, config)
  - [x]2.1 Implement `evals/base.py`: define abstract `Eval` class with methods `run(model: ModelAdapter, dataset: list[dict]) -> Result` and `run_single(model: ModelAdapter, example: dict) -> ExampleResult`. The `Eval` class should accept a model adapter and a list of graders
  - [x]2.2 Define `Result` dataclass in `evals/base.py` with fields: `eval_name: str`, `model_id: str`, `timestamp: datetime`, `examples: list[ExampleResult]`, `aggregate_metrics: dict[str, float]`, `confidence_intervals: dict[str, tuple[float, float]]`, `run_config: dict`
  - [x]2.3 Define `ExampleResult` dataclass with fields: `example_id: str`, `input: dict`, `output: str`, `scores: dict[str, float]`, `traces: list[dict]`, `grader_results: dict[str, Any]`, `passed: bool`
  - [x]2.4 Add `Result` methods: `to_json() -> str`, `to_summary() -> str` (human-readable), `from_json(json_str) -> Result` (deserialization), and `save(path: Path)` / `load(path: Path)` for file I/O
  - [x]2.5 Create a config loading utility (`evals/config.py`) that reads YAML or JSON experiment configs and resolves model adapter settings, dataset paths, and grader selections

- [x]3.0 Implement model adapter layer
  - [x]3.1 Define abstract `ModelAdapter` base class in `models/adapters.py` with methods: `generate(prompt: str, system_prompt: str | None, config: dict) -> ModelResponse`, `batch_generate(prompts: list[str], system_prompt: str | None, config: dict) -> list[ModelResponse]`, and properties: `model_id: str`, `model_version: str`
  - [x]3.2 Define `ModelResponse` dataclass with fields: `text: str`, `model_id: str`, `usage: dict` (input/output tokens), `latency_ms: float`, `raw_response: Any`
  - [x]3.3 Implement `AnthropicAdapter(ModelAdapter)` using the Anthropic Python SDK. Support configurable `model` (default `claude-sonnet-4-20250514`), `max_tokens`, `temperature`, and `system` prompt. Load API key from `ANTHROPIC_API_KEY` env var
  - [x]3.4 Implement `batch_generate` on `AnthropicAdapter` using `asyncio.gather` with configurable concurrency limit (default 5)
  - [x]3.5 Add adapter factory function `create_adapter(provider: str, **kwargs) -> ModelAdapter` that returns the appropriate adapter based on provider name, raising `NotImplementedError` for unsupported providers with a clear message about how to add one

- [x]4.0 Build datasets and synthetic data generators
  - [x]4.1 Create `datasets/generators/generate_metar.py`: function `generate_metar(icao: str, conditions: dict) -> str` that produces valid METAR strings. Support parameters: wind direction/speed/gusts, visibility, ceiling, temperature, dewpoint, altimeter. Include presets for common scenarios: `low_vis_approach` (visibility < 1SM, low ceiling), `gusty_crosswind` (gusts > 25kt), `clear_day` (CAVOK equivalent), `winter_ops` (freezing precip)
  - [x]4.2 Create `datasets/generators/generate_tracks.py`: function `generate_track(airport_icao: str, runway: str, profile_type: str, aircraft_type: str) -> list[dict]` producing synthetic ADS-B track points. Each point: `{timestamp_ms, latitude, longitude, altitude_ft, heading, ground_speed_kt, vertical_rate_fpm}`. Profile types: `approach` (3-degree glideslope from ~10nm final), `departure` (standard climb), `taxi` (ground movement at 15-25kt), `go_around` (approach followed by climb). Use airport coordinates from `aviation_domain.py`
  - [x]4.3 Create `datasets/generators/generate_scenarios.py`: function `generate_scenario(event_type: str, airport_icao: str, difficulty: str) -> dict` that composes a full synthetic event scenario combining: a narrative (ASRS-style text), synthetic tracks, synthetic METAR, operations data (fictional callsign, real aircraft type, runway), and score/severity metadata. Output matches the dataset JSONL schema from PRD Section 4.4
  - [x]4.4 Write `datasets/grounding_cases.jsonl` — author 50-100 grounding cases using a mix of: (a) real ASRS narrative excerpts (public domain, de-identified) with hand-labeled expected_facts and negative_facts, (b) FAR/AIM regulatory excerpts with factual questions, (c) NTSB probable cause summaries. Each case follows the schema in PRD Section 4.4 requirement 19. Cover event types: unstable_approach, go_around, tcas_ra, runway_excursion, surface_safety, runway_incursion. Distribute across difficulty levels (easy/medium/hard) and multiple airports
  - [x]4.5 Write `datasets/tool_use_cases.jsonl` — author 30-50 tool use scenarios. Each case specifies: a user query about an aviation event, the expected sequence of tool calls (from the 6 mock tools in PRD 4.3.2), expected arguments for each call, and at least one plausible-but-wrong tool choice as a distractor. Example: "What was the weather at KDFW when flight SYN042 executed a go-around?" → expected: `metar_lookup("KDFW", <timestamp>)`, distractor: `track_query` (wrong tool for weather)
  - [x]4.6 Write `datasets/adversarial_prompts.jsonl` — author 30-50 perturbation templates. Each template: `{base_prompt, perturbation_type, perturbed_prompt, expected_behavior}`. Perturbation types: `paraphrase` (same meaning, different phrasing), `typo` (ICAO code typos like "KFWD" for "KDFW"), `distractor_injection` (inject irrelevant airport/runway into context), `synonym` (TCAS RA → resolution advisory), `nearby_airport_swap` (KDAL ↔ KDFW), `conflicting_metar` (inject contradictory weather data)
  - [x]4.7 Write `datasets/refusal_cases.jsonl` — author 20-30 refusal boundary cases. Each case: `{case_id, query, context, expected_behavior: "answer" | "refuse" | "hedge", category: "over_refusal" | "under_refusal" | "borderline", rationale}`. Cover: legitimate safety analysis questions (should answer), speculation about fault/blame (should refuse), attempts to identify de-identified ASRS reporters (should refuse), causal attribution from incomplete data (should hedge)
  - [x]4.8 Write `datasets/README.md` documenting: dataset schemas, provenance (ASRS query parameters, NTSB report IDs, FAR sections used), labeling process (who labeled, criteria), known issues and limitations, and instructions for adding new cases

- [x]5.0 Implement graders (rule-based, LLM judge, human agreement)
  - [x]5.1 Define abstract `Grader` base class in `graders/__init__.py` with method `grade(output: str, expected: dict, context: dict) -> GradeResult`. Define `GradeResult` dataclass: `{score: float, passed: bool, metric_name: str, details: dict}`
  - [x]5.2 Implement `graders/rule_based.py` with grader classes: `ContainsGrader` (case-insensitive string matching), `NotContainsGrader` (anti-hallucination — fails if output contains a forbidden string), `NumericToleranceGrader` (extract number via regex, check within ±tolerance), `RegexGrader` (match output against a regex pattern), `SemanticEquivalenceGrader` (check against aviation_domain.py synonym lists before failing a contains check)
  - [x]5.3 Implement `graders/llm_judge.py` with `LLMJudgeGrader` class. Takes a rubric string and a `ModelAdapter` (for the judge model). Sends the rubric + model output to the judge, parses a structured score (1-5 scale). Support weighted sub-rubrics (list of `{rubric, weight, threshold}` dicts). Include Promptfoo `llm-rubric` compatible output format
  - [x]5.4 Add calibration study method to `LLMJudgeGrader`: `calibrate(labeled_examples: list[dict]) -> CalibrationReport`. Takes examples with human labels, runs the judge, and computes: agreement rate, Cohen's kappa, confusion matrix, and a list of systematic disagreement patterns (cases where judge consistently over/under-scores vs. human). `CalibrationReport` is a dataclass with these fields plus a `to_markdown()` method
  - [x]5.5 Implement `graders/human_agreement.py` with functions: `cohens_kappa(labels_a, labels_b) -> float`, `krippendorffs_alpha(annotations: list[list]) -> float`, `disagreement_report(labels_a, labels_b, examples) -> str` (markdown report listing all disagreement cases with context)

- [x]6.0 Build Promptfoo integration layer (config generation, custom providers)
  - [x]6.1 Create `runners/promptfoo_config.py` with function `generate_config(eval_category: str, dataset_path: str, model_config: dict, grader_configs: list[dict]) -> dict` that builds a Promptfoo YAML-compatible config dict. Map grader configs to Promptfoo assertion types: `ContainsGrader` → `icontains`, `NotContainsGrader` → `not-icontains`, `NumericToleranceGrader` → `javascript` (with tolerance logic), `LLMJudgeGrader` → `llm-rubric` with provider and threshold fields
  - [x]6.2 Add `write_config(config: dict, output_path: Path)` that serializes to YAML and validates the structure against Promptfoo's expected schema (providers, prompts, tests with assertions)
  - [x]6.3 Create `runners/promptfoo_provider.py` — a custom Promptfoo provider script (Python, callable by Promptfoo via `python:runners/promptfoo_provider.py`) that: receives the prompt from Promptfoo, calls the model adapter layer, returns the response in Promptfoo's expected format. Support passing adapter config via environment variables or a sidecar JSON config
  - [x]6.4 Add per-eval-category config generators: `generate_grounding_config(dataset_path, model_config)`, `generate_tool_use_config(...)`, `generate_robustness_config(...)`, etc. Each uses the graders and assertion types appropriate to that eval category. Grounding config should include weighted sub-rubrics (airport_correctness 30%, event_analysis 30%, fact_extraction 25%, flight_phase 15%) and anti-hallucination not-contains checks
  - [x]6.5 Add result translation: `promptfoo_results_to_result(promptfoo_output: dict, eval_name: str) -> Result` that converts Promptfoo's native JSON output into the harness's `Result` schema, preserving per-example scores and traces

- [x]7.0 Implement eval categories (grounding, tool_use, robustness, refusals, regression)
  - [x]7.1 Implement `evals/grounding/grounding_eval.py`: `GroundingEval(Eval)` that loads `grounding_cases.jsonl`, runs each case through the model, and applies both `RuleBasedGrader` (contains/not-contains for expected_facts/negative_facts) and `LLMJudgeGrader` (with aviation grounding rubric). Compute per-example agreement between graders. Aggregate metrics: `grounding_accuracy`, `hallucination_rate`, `grader_agreement_rate`
  - [x]7.2 Implement `evals/tool_use/mock_tools.py`: define the 6 aviation mock tools from PRD 4.3.2 as a tool schema registry. Each tool has: `name`, `description`, `parameters` (JSON Schema), and a `simulate(args: dict) -> dict` method that returns plausible mock data. Tools: `metar_lookup`, `track_query`, `regulation_search`, `airport_info`, `notam_check`, `aircraft_info`
  - [x]7.3 Implement `evals/tool_use/tool_use_eval.py`: `ToolUseEval(Eval)` that loads `tool_use_cases.jsonl`, presents each scenario to the model with the tool schemas, captures the model's tool call sequence, and scores: correct tool selected (binary), correct arguments (fuzzy match on ICAO codes, timestamps), correct ordering (sequence match). Aggregate metrics: `tool_selection_accuracy`, `argument_accuracy`, `sequence_accuracy`
  - [x]7.4 Implement `evals/robustness/perturbations.py`: perturbation engine with functions: `paraphrase(prompt: str) -> str`, `inject_typo(prompt: str, target: str) -> str`, `inject_distractor(prompt: str, distractor: str) -> str`, `swap_synonym(prompt: str, synonyms: dict) -> str`, `swap_nearby_airport(prompt: str, airport_pairs: dict) -> str`. Each returns the perturbed prompt
  - [x]7.5 Implement `evals/robustness/robustness_eval.py`: `RobustnessEval(Eval)` that loads `adversarial_prompts.jsonl`, runs each base prompt to get a baseline score, then runs each perturbation variant, and computes score degradation. Aggregate metrics: `mean_degradation`, `max_degradation`, `perturbation_type_breakdown` (degradation by category)
  - [x]7.6 Implement `evals/refusals/refusals_eval.py`: `RefusalsEval(Eval)` that loads `refusal_cases.jsonl`, runs each query, and classifies the model's response as `answered`, `refused`, or `hedged` (using a combination of keyword detection and LLM judge). Score against expected_behavior. Aggregate metrics: `over_refusal_rate`, `under_refusal_rate`, `accuracy` (correct behavior), `borderline_accuracy`
  - [x]7.7 Implement `evals/regression/regression_eval.py`: `RegressionEval(Eval)` that takes two `Result` objects (or result file paths) and produces a diff report. For each metric: compute delta, run paired bootstrap test for significance (using `analysis/significance.py`). Output a markdown diff report with: metric deltas, significance flags, per-example regressions (cases that passed before but fail now), and per-example improvements

- [x]8.0 Build runners (CLI entry point, parallel execution, caching)
  - [x]8.1 Implement `runners/run_eval.py` as a Click CLI application. Commands: `run` (run an eval), `compare` (compare two results), `new-experiment` (scaffold experiment dir). `run` accepts: `--eval` (category name), `--model` (adapter + model ID), `--dataset` (path override), `--config` (YAML config path), `--output` (results output path), `--use-cache/--no-cache`. It generates the Promptfoo config, invokes Promptfoo via subprocess, translates results, and outputs JSON + human-readable summary
  - [x]8.2 Implement `runners/cache.py`: `ResponseCache` class backed by a local SQLite database. Cache key: `hash(model_id + model_version + prompt_hash + config_hash)`. Methods: `get(key) -> ModelResponse | None`, `put(key, response)`, `invalidate(model_version: str)`, `stats() -> dict` (hit/miss counts, size). Cache file stored at `.eval_cache/responses.db`
  - [x]8.3 Implement `runners/parallel.py`: `ParallelRunner` class with method `run_batch(adapter: ModelAdapter, prompts: list[str], concurrency: int = 5) -> list[ModelResponse]` using `asyncio`. Integrate with `ResponseCache` — check cache before making API calls. Report progress (X/N completed) to stderr
  - [x]8.4 Wire cache into the model adapter layer: add a `CachedAdapter` wrapper class that wraps any `ModelAdapter`, checks `ResponseCache` before calling the underlying adapter, and stores responses after calls. This keeps caching transparent to eval implementations

- [x]9.0 Build analysis tools (significance, failure clustering, dashboards)
  - [x]9.1 Implement `analysis/significance.py`: function `bootstrap_ci(scores: list[float], n_bootstrap: int = 10000, ci: float = 0.95) -> tuple[float, float, float]` returning (mean, lower, upper). Function `paired_bootstrap_test(scores_a: list[float], scores_b: list[float], n_bootstrap: int = 10000) -> tuple[float, float, bool]` returning (delta, p_value, significant_at_005)
  - [x]9.2 Add `compare_runs(result_a: Result, result_b: Result) -> ComparisonReport` to `significance.py`. For each shared metric, compute delta with CI and significance. `ComparisonReport` dataclass with `to_markdown()` and `to_json()` methods
  - [x]9.3 Implement `analysis/failure_clustering.py`: function `cluster_failures(failed_examples: list[ExampleResult], n_clusters: int = 5) -> list[FailureCluster]`. Embed each failed example's input+output text using sentence-transformers, run KMeans or HDBSCAN, and return clusters. `FailureCluster` dataclass: `{cluster_id, size, centroid_example, theme_description: str, examples: list[ExampleResult]}`
  - [x]9.4 Add `generate_failure_report(clusters: list[FailureCluster]) -> str` that produces a markdown report: "Cluster 1 (N=12): Model fails on numerical reasoning involving altitudes — examples: ..." with representative examples from each cluster
  - [x]9.5 Implement `analysis/dashboards/report.py`: function `generate_report(results: list[Result], output_path: Path)` that produces a static HTML file with: results table (models × evals with CIs), per-eval bar charts, and a failure summary section. Use matplotlib for charts, embed as base64 PNGs in a self-contained HTML file

- [x]10.0 Create experiments framework and initial experiment
  - [x]10.1 Create `experiments/template/` directory with: `config.yaml` (template with placeholders for model, eval, dataset), `results/.gitkeep`, and `writeup.md` (template with sections: Hypothesis, Setup, Results, Discussion, Next Steps)
  - [x]10.2 Implement `new-experiment` CLI command in `runners/run_eval.py`: copies template to `experiments/YYYY-MM-description/`, fills in date, creates the directory structure
  - [x]10.3 Run the first experiment: `experiments/2026-04-grounding-baseline/`. Configure: GroundingEval against Claude Sonnet on the grounding_cases.jsonl dataset. Execute, capture results, compute bootstrap CIs, run failure clustering on failures. Write up findings in `writeup.md` with hypothesis ("Claude Sonnet achieves >80% grounding accuracy on aviation safety cases"), results, one surprising finding, and next steps

- [x]11.0 Write documentation (methodology, threat model, README)
  - [x]11.1 Write `docs/methodology.md` (2-4 pages): what behaviors are measured (grounding, tool use, robustness, refusals, regression) and why these five. How cases were constructed (ASRS sourcing, synthetic generation, hand-labeling). What is explicitly not measured (real-time performance, cost efficiency, multi-turn conversation quality). Grading methodology (multi-layer assertions, weighted sub-rubrics, calibration against human labels). Statistical approach (bootstrap CIs, paired comparison tests)
  - [x]11.2 Write `docs/threat-model.md`: enumerate failure modes organized by severity (critical/high/medium/low). Critical: hallucinated safety-critical facts (wrong airport, wrong altitude in TCAS event). High: wrong tool selection leading to missing context. Medium: score degradation under benign rephrasings. Low: over-refusal on legitimate queries. For each: description, how the eval detects it, example, and mitigation strategy
  - [x]11.3 Write `README.md` with: one-paragraph pitch (what problem, approach, what's novel), quick-start (install, set API key, run one eval, see results — 5 commands max), project structure overview, results table (models × evals with CIs — populated from initial experiment), "Known Limitations" section (at least 5 items), one surprising finding with investigation writeup, contributing guidelines (how to add an eval, how to add a model adapter)

- [x]12.0 Write tests
  - [x]12.1 `tests/test_base.py`: test `Result` serialization round-trip (to_json → from_json), test `ExampleResult` construction, test `Result.to_summary()` produces readable output, test `Eval` base class raises `NotImplementedError` on abstract methods
  - [x]12.2 `tests/test_adapters.py`: test `ModelAdapter` abstract interface raises on direct instantiation, test `AnthropicAdapter` construction with mock API key, test `create_adapter("anthropic")` returns `AnthropicAdapter`, test `create_adapter("openai")` raises `NotImplementedError` with helpful message, test `ModelResponse` dataclass fields
  - [x]12.3 `tests/graders/test_rule_based.py`: test `ContainsGrader` case-insensitive matching, test `NotContainsGrader` anti-hallucination (passes when string absent, fails when present), test `NumericToleranceGrader` with altitude values (15000 ± 500), test `SemanticEquivalenceGrader` with aviation synonyms ("TCAS RA" matches "resolution advisory"), test `RegexGrader` pattern matching
  - [x]12.4 `tests/graders/test_llm_judge.py`: test `LLMJudgeGrader` with mocked model adapter (return a fixed score), test weighted sub-rubric aggregation (30/30/25/15 weights), test `CalibrationReport.to_markdown()` produces valid markdown, test calibration kappa computation against known label sets
  - [x]12.5 `tests/graders/test_human_agreement.py`: test `cohens_kappa` with known label pairs (perfect agreement → 1.0, random → ~0.0), test `krippendorffs_alpha` with known data, test `disagreement_report` produces a markdown string listing disagreements
  - [x]12.6 `tests/runners/test_cache.py`: test `ResponseCache` put/get round-trip, test cache miss returns None, test `invalidate(model_version)` removes matching entries, test `stats()` reports correct hit/miss counts
  - [x]12.7 `tests/runners/test_promptfoo_config.py`: test `generate_config` produces valid YAML structure with providers/prompts/tests, test grader-to-assertion mapping (ContainsGrader → icontains, LLMJudgeGrader → llm-rubric), test `generate_grounding_config` includes weighted sub-rubrics and anti-hallucination checks
  - [x]12.8 `tests/analysis/test_significance.py`: test `bootstrap_ci` on known data (e.g., all 1.0 → CI is [1.0, 1.0]), test `paired_bootstrap_test` detects significant difference between clearly different score sets, test non-significant result for similar score sets
  - [x]12.9 `tests/analysis/test_failure_clustering.py`: test `cluster_failures` with synthetic embedded examples groups similar failures together, test `generate_failure_report` produces markdown with cluster descriptions
  - [x]12.10 `tests/datasets/test_generators.py`: test `generate_metar` produces valid METAR format string (starts with ICAO code, contains wind/vis/temp groups), test `generate_track` produces track points with valid lat/lon/altitude ranges, test `generate_scenario` produces dict matching the grounding_cases schema, test preset METAR conditions (low_vis_approach has visibility < 1SM)
