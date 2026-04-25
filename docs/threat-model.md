# Threat Model: Failure Modes in Aviation Safety LLM Analysis

This document catalogs the failure modes the evaluation suite is designed to detect, organized by severity.

## Critical Severity

### C1: Hallucinated Safety-Critical Facts
**Description**: Model invents airports, altitudes, aircraft types, or other safety-critical parameters not present in the source data.

**Example**: Source describes an event at KDFW, model outputs analysis referencing KJFK with fabricated altitude values.

**Detection**: `NotContainsGrader` checks negative_facts (wrong airports, wrong aircraft types). `NumericToleranceGrader` validates extracted numeric values against expected ranges.

**Mitigation**: Anti-hallucination assertions in every grounding test case. Multiple wrong-airport checks per case.

### C2: Fabricated Regulatory References
**Description**: Model cites non-existent FAR sections or misquotes regulations.

**Example**: "Per FAR 91.999, the minimum descent altitude for this approach is..." (no such FAR section).

**Detection**: `RegexGrader` validates FAR section format. Grounding cases with FAR source material check correct extraction.

**Mitigation**: Include FAR/AIM source cases with expected regulatory content.

### C3: Wrong Causal Attribution in Safety Events
**Description**: Model attributes the cause of a safety event to the wrong factor, potentially misleading safety analysis.

**Example**: Attributing a runway excursion to pilot error when the source data indicates contaminated runway as the primary factor.

**Detection**: `LLMJudgeGrader` with event analysis rubric. Expected_facts include correct contributing factors.

**Mitigation**: Sub-rubric for event analysis quality (30% weight).

## High Severity

### H1: Wrong Tool Selection
**Description**: Model selects a plausible but incorrect tool, leading to missing or wrong context.

**Example**: Using `aircraft_info` instead of `metar_lookup` when asked about weather at an airport.

**Detection**: `ToolUseEval` scores tool selection accuracy. Each case includes distractor tools.

**Mitigation**: Test cases with plausible-but-wrong tool choices as explicit distractors.

### H2: Phase-of-Flight Confusion
**Description**: Model references flight parameters from the wrong phase (e.g., cruise altitude in a surface event).

**Example**: "The aircraft was at 35,000 feet during the runway incursion..." (surface events occur at ground level).

**Detection**: Flight phase relevance sub-rubric (15% weight). Phase-specific altitude/speed validation.

**Mitigation**: `PHASE_OF_FLIGHT` constraints in `aviation_domain.py` define valid parameter ranges per phase.

### H3: Under-Refusal on Speculation Requests
**Description**: Model provides confident causal attribution or identifies de-identified reporters when it should decline.

**Example**: "Based on this ASRS report, the pilot was likely Captain John Smith..." (ASRS reports are de-identified).

**Detection**: `RefusalsEval` classifies responses and scores against expected behavior.

**Mitigation**: Explicit refusal boundary test cases covering reporter identification and blame attribution.

## Medium Severity

### M1: Score Degradation Under Benign Rephrasings
**Description**: Model gives materially different answers when the same question is rephrased or aviation jargon is expanded.

**Example**: Different analysis quality for "TCAS RA" vs "TCAS Resolution Advisory" — these are semantically identical.

**Detection**: `RobustnessEval` measures degradation between base and paraphrased prompts.

**Mitigation**: `SemanticEquivalenceGrader` allows synonym matching. Robustness test cases cover paraphrase and synonym perturbations.

### M2: Sensitivity to Distractor Information
**Description**: Model's analysis is corrupted by irrelevant information injected into the context.

**Example**: Adding "NOTAM: RWY 27R at KBOS closed" to a KDFW scenario causes the model to discuss KBOS.

**Detection**: `RobustnessEval` with distractor injection perturbation type.

**Mitigation**: Anti-hallucination checks catch wrong-airport references introduced by distractors.

### M3: ICAO Code Typo Sensitivity
**Description**: Single-character typo in an ICAO code causes model to either fail completely or analyze the wrong airport.

**Example**: "KFWD" (typo for KDFW) causes model to reference a different or non-existent airport.

**Detection**: `RobustnessEval` with typo perturbation type.

**Mitigation**: Robustness cases with known ICAO code typos and expected behavior (detect error or robust to change).

## Low Severity

### L1: Over-Refusal on Legitimate Queries
**Description**: Model refuses to answer standard aviation safety analysis questions that are clearly legitimate.

**Example**: Refusing to explain stabilized approach criteria because it's "too dangerous."

**Detection**: `RefusalsEval` over_refusal_rate metric.

**Mitigation**: Test cases with clearly legitimate queries expected to receive full answers.

### L2: Regression on Previously Passing Cases
**Description**: A model update causes previously correct answers to become incorrect.

**Detection**: `RegressionEval` with per-example pass/fail diff and significance testing.

**Mitigation**: Cached baselines enable exact comparison across model versions.

### L3: Inconsistent Numeric Extraction
**Description**: Model extracts numerical values (altitudes, speeds, rates) with inconsistent formatting or rounding.

**Example**: Source says "15,000 feet", model outputs "fifteen thousand ft" or "15000'" in different cases.

**Detection**: `NumericToleranceGrader` with configurable tolerance per parameter type.

**Mitigation**: Standard tolerances defined in `NUMERIC_TOLERANCES` (altitude ±500ft, speed ±10kt, etc.).
