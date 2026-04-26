# Calibration Study Report

**Primary rater**: LLM Judge (claude-sonnet-4-20250514)
**Second rater**: claude-haiku-4-5-20251001
**Examples evaluated**: 30

## Methodology

Both raters scored the same model outputs using the grading rubric defined in
`docs/grading_rubric.md`. The primary rater is the LLM judge used during the
grounding evaluation. The second rater is a different model acting as a stand-in
for an independent human rater. This is a known limitation: both raters are LLMs
from the same model family, which may inflate agreement compared to true human-LLM
agreement. Results should be interpreted as an upper bound on inter-rater reliability.

## Aggregate Agreement

**Mean absolute error (aggregate)**: 0.0840
**Pearson correlation (aggregate)**: -0.122
**Binary pass/fail agreement**: 30/30 (100.0%)
**Cohen's kappa (binary pass/fail)**: 1.000

## Per-Sub-Rubric Agreement

| Sub-Rubric | Cohen's Kappa | Krippendorff's Alpha | MAE | Primary Mean | Second Mean |
|---|---|---|---|---|---|
| airport_correctness | 0.394 | 0.053 | 0.53 | 4.43 | 4.83 |
| event_analysis_quality | -0.061 | -0.081 | 0.60 | 4.47 | 4.93 |
| fact_extraction_accuracy | 0.155 | 0.016 | 0.30 | 4.73 | 4.90 |
| flight_phase_relevance | 0.000 | 0.000 | 0.03 | 5.00 | 4.97 |

## Systematic Patterns

- Primary rater scores systematically lower than second rater (mean difference: -0.059)
- Primary rater scores lower on airport_correctness (primary 4.43 vs second 4.83)
- Primary rater scores lower on event_analysis_quality (primary 4.47 vs second 4.93)