# Changelog

## v0.1.0 - Initial public release (April 2026)

First public version of the aviation eval harness.

### Evaluation categories

- Grounding (N=60): factual coverage with sub-rubric decomposition
- Tool use (N=35): selection, arguments, and sequencing
- Robustness (N=35): six perturbation types, Jaccard + embedding metrics
- Refusals (N=25): semantic classifier
- Regression: paired bootstrap comparison

### Methodology

- Multi-layered grading (literal, semantic equivalence, LLM judge)
- Weighted sub-rubrics (30/30/25/15)
- Bootstrap confidence intervals (10,000 iterations)
- LLM-vs-LLM calibration study (Cohen's kappa = 1.0 binary)

### Documentation

- Methodological findings writeup (docs/findings.md)
- Dataset provenance and synthetic generation notes
- Reproducibility instructions
