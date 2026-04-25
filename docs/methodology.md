# Evaluation Methodology

## What We Measure

This harness evaluates five dimensions of LLM behavior in the context of aviation safety analysis:

### 1. Grounding (Factual Attribution)
**Question**: Are generated claims supported by the provided source context?

We present models with aviation safety documents (ASRS narratives, NTSB summaries, FAR excerpts) and analysis questions. Outputs are graded on:
- **Fact extraction accuracy**: Are all key facts from the source present in the output?
- **Anti-hallucination**: Does the output introduce facts not present in the source (wrong airport codes, invented altitudes, incorrect aircraft types)?
- **Event analysis quality**: Is the event type correctly identified and analyzed?
- **Phase-of-flight awareness**: Does the output correctly reference the relevant phase of flight?

Two grading approaches are applied in parallel — rule-based (literal string matching with semantic equivalence) and LLM-as-judge (structured rubric) — and their agreement is reported as a calibration signal.

### 2. Tool Use (Correct Tool Selection and Sequencing)
**Question**: Does the model select the right tools with correct arguments in the right order?

Models receive a set of six aviation mock tools (METAR lookup, ADS-B track query, regulation search, airport info, NOTAM check, aircraft info) and must determine which to call for a given query. Scoring evaluates:
- **Tool selection**: Binary — was the correct tool chosen?
- **Argument accuracy**: Fuzzy match on ICAO codes, timestamps, and identifiers.
- **Sequence accuracy**: Longest common subsequence ratio against expected ordering.

Each case includes distractor tools (plausible but wrong choices) to test selectivity.

### 3. Robustness (Stability Under Perturbation)
**Question**: Does the model's output degrade under input modifications?

We measure score degradation (not raw accuracy) when prompts are perturbed via:
- **Paraphrase**: Same meaning, different wording
- **Typo**: ICAO code typos (e.g., "KFWD" for "KDFW")
- **Distractor injection**: Irrelevant information added to context
- **Synonym swap**: Aviation term synonyms (go-around ↔ missed approach)
- **Nearby airport swap**: KDAL ↔ KDFW (geographically proximate but distinct)
- **Conflicting METAR**: Contradictory weather data injected

A robust model should show minimal degradation across perturbation types.

### 4. Refusals (Boundary Calibration)
**Question**: Does the model refuse when it should, and answer when it should?

We test three categories:
- **Legitimate questions** (should answer): Standard safety analysis, regulatory questions
- **Should refuse**: Identifying de-identified ASRS reporters, speculating about fault/blame
- **Borderline** (should hedge): Causal attribution from incomplete data

Metrics distinguish over-refusal (refusing legitimate queries) from under-refusal (answering when it should decline).

### 5. Regression (Cross-Version Comparison)
**Question**: Did a model change make things better or worse?

Paired comparison of two result sets on identical test cases, with:
- Per-metric deltas with statistical significance (paired bootstrap test)
- Per-example regression/improvement identification
- Markdown diff reports

## How Cases Were Constructed

### Source Material
- **ASRS narratives**: NASA Aviation Safety Reporting System public database. De-identified voluntary safety reports covering go-arounds, TCAS events, unstable approaches, runway incursions.
- **NTSB summaries**: Public probable cause findings with structured factual data.
- **FAR/AIM excerpts**: Federal Aviation Regulations and Aeronautical Information Manual — public regulatory text.

### Synthetic Data
Synthetic generators produce:
- **METAR strings**: Valid format, tied to scenario conditions (low visibility, crosswinds, etc.)
- **ADS-B tracks**: Physics-based flight profiles (3-degree glideslope approaches, standard climb rates, taxi movements)
- **Composite scenarios**: Combining narrative, weather, tracks, and operations data with fictional callsigns and real aircraft types

### Labeling
Expected facts and negative facts are hand-labeled by the author. Each case specifies:
- Facts that MUST appear (expected_facts)
- Facts that must NOT appear (negative_facts / anti-hallucination targets)
- Difficulty rating (easy/medium/hard)

## What Is Explicitly Not Measured

- **Multi-turn conversation quality**: All evaluations use single-turn interactions
- **Real-time performance**: No latency benchmarks or throughput measurements
- **Cost efficiency**: No token cost comparisons
- **Fine-tuning effectiveness**: This harness evaluates, it does not train
- **Non-English language capability**: All content is English
- **Production system reliability**: No uptime, retry, or error-recovery testing
- **Embedding quality**: Only text generation is evaluated

## Grading Methodology

### Multi-Layer Assertions
Following patterns established in the Blazer project, each grounding case uses layered grading:
1. **Literal assertions**: `contains` / `not-contains` for specific facts
2. **Semantic equivalence**: Synonym-aware matching (TCAS RA = TCAS Resolution Advisory)
3. **LLM rubric**: Structured scoring on a 1-5 scale with sub-rubrics

### Weighted Sub-Rubrics
Grounding evaluation uses weighted dimensions (inspired by Blazer's 30/30/25/15 split):
- Airport correctness: 30%
- Event analysis quality: 30%
- Fact extraction accuracy: 25%
- Flight phase relevance: 15%

LLM judge scores use calibrated thresholds (0.4) for partial credit.

### Calibration
The LLM judge is calibrated against human labels:
- Cohen's kappa measures agreement
- Systematic disagreement patterns are identified (over-scoring, difficulty-dependent bias)
- Confusion matrices quantify false positive/negative rates

## Statistical Approach

All aggregate metrics are reported with **95% bootstrap confidence intervals** (10,000 iterations).

Cross-model comparisons use **paired bootstrap tests**:
- Same test cases, different models
- Two-sided test with p < 0.05 threshold
- We do not claim "Model A > Model B" without statistical significance
