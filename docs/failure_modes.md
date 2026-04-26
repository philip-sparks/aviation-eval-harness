# Failure Mode Taxonomy

Analysis of the 12 grounding examples (out of 60) scoring below 0.85 on the weighted aggregate. These are not outright failures -all pass the binary pass/fail gate -but they reveal systematic patterns in where the model loses points and, more interestingly, where the grading rubric itself breaks down.

## Failure Mode 1: Sub-rubric inapplicability on regulatory queries

**Frequency**: 7 of 12 low-scoring examples (58%)

**Pattern**: The four grounding sub-rubrics (airport_correctness, event_analysis_quality, fact_extraction_accuracy, flight_phase_relevance) were designed for incident/event analysis. When applied to regulatory interpretation queries (FAR/AIM questions), the airport_correctness and event_analysis_quality rubrics become inapplicable. The primary LLM judge scores these as 1/5 because there is no airport to identify and no event to analyze.

**Examples**:

- **GND-FAR-007** (aggregate 0.47): "What does FAR 91.175 require regarding descent below DA/DH?" -airport_correctness=1, event_analysis_quality=1. The model correctly explains the regulation but there are no airports or events to evaluate.
- **GND-FAR-030** (aggregate 0.52): "What are the TCAS equipment requirements for Part 135 operations?" -same pattern. The model accurately extracts all regulatory requirements (fact_extraction_accuracy=5) but receives 1/5 on inapplicable rubrics.
- **GND-FAR-047** (aggregate 0.52): "What are the pilot responsibilities for surface operations at Class D airports?" -regulatory summary scored as event analysis failure.

**Calibration note**: The calibration study confirms this as the primary source of inter-rater disagreement. The second rater (Claude Haiku) scores these same cases 5/5 on airport_correctness and event_analysis_quality, reasoning that when the rubric dimension is inapplicable, full credit is appropriate. This accounts for the top 2 disagreements (differences of 0.53 and 0.48) in `experiments/calibration-study/disagreements.md`.

**Hypothesis**: The primary judge applies sub-rubrics literally (no airport mentioned → score 1) while a more lenient interpretation (no airport required → score 5) is arguably more correct for regulatory queries.

**Mitigation**: Introduce a query-type classifier that detects regulatory vs. incident queries and applies an adjusted rubric. For regulatory queries, replace airport_correctness and event_analysis_quality with rubrics measuring regulatory interpretation accuracy and completeness. This would be a pre-grading routing step, not a change to the rubrics themselves.

---

## Failure Mode 2: Airport and location detail omission

**Frequency**: 4 of 12 low-scoring examples (33%)

**Pattern**: On incident analysis queries where airports are explicitly mentioned in the source context, the model provides correct analysis but omits or under-specifies location details. The model prioritizes analytical content over restating location facts.

**Examples**:

- **GND-ASRS-016** (aggregate 0.82): Wind shear encounter at DEN. The model writes "Denver International Airport (DEN)" instead of using the ICAO code "KDEN." The judge penalizes this as an airport identification error (score 2/5).
- **GND-ASRS-013** (aggregate 0.82): Go-around at ORD. The model analyzes the engine bleed air complication in detail but does not prominently restate "ORD" or "RWY 28C" in its output.
- **GND-NTSB-035** (aggregate 0.82): Runway excursion at DEN RWY 35R. The model analyzes density altitude effects accurately but does not mention the airport identifier or runway in the output.

**Hypothesis**: The model treats location identifiers as given context rather than claims to be restated. When the prompt says "analyze this event at KORD," the model assumes the reader knows the airport and focuses its output on the analysis. The grading rubric, correctly, checks whether the output would stand alone as a complete report.

**Mitigation**: Add explicit instructions in the system prompt: "Always restate the airport ICAO code, airport name, and runway designation in your analysis, even when they appear in the source data." This is a prompt engineering fix, not a model capability issue.

---

## Failure Mode 3: Domain terminology misinterpretation

**Frequency**: 2 of 12 low-scoring examples (17%)

**Pattern**: The model misinterprets domain-specific terminology that has context-dependent meanings.

**Examples**:

- **GND-NTSB-053** (aggregate 0.79): The source states the B777 "was at 1,000 feet in the takeoff roll." The model interprets "1,000 feet" as distance along the runway (correct, per the judge's scoring of flight_phase_relevance=2), but the phrasing is genuinely ambiguous -"1,000 feet in the takeoff roll" could mean altitude or distance. The judge penalizes because the model's output creates ambiguity about whether this is an altitude or distance measurement.
- **GND-FAR-060** (aggregate 0.77): The model refers to AIM 4-3-14 as an "Advisory Circular" rather than correctly identifying it as part of the Aeronautical Information Manual. This is a factual error about source classification (event_analysis_quality=2).

**Hypothesis**: These are genuine domain knowledge gaps. The model has general aviation knowledge but occasionally confuses similar-sounding aviation concepts (AIM vs. Advisory Circular) or misreads context clues for unit interpretation.

**Mitigation**: Add domain terminology validation as a post-processing step. A lookup table mapping AIM section numbers, Advisory Circular numbers, and FAR sections to their correct source types would catch the AIM/AC confusion. For unit ambiguity, the system prompt could instruct the model to flag ambiguous measurements explicitly.

---

## Failure Mode 4: Geometric and mathematical reasoning errors

**Frequency**: 1 of 12 low-scoring examples (8%)

**Pattern**: The model makes errors in spatial or mathematical reasoning about physical configurations.

**Example**:

- **GND-ASRS-046** (aggregate 0.64): A taxiway geometry conflict between an A321neo (wingspan 117 ft) and B737-700 (wingspan 112 ft) on a 75-foot-wide taxiway. The model adds the full wingspans (229 ft) and compares to taxiway width, when the correct analysis uses half-wingspans for clearance calculation. The model correctly extracts all facts (fact_extraction_accuracy=5) but the analysis logic is wrong (event_analysis_quality=2).

**Hypothesis**: This is a known limitation of LLMs on spatial reasoning tasks. The model retrieves the correct numbers but applies an incorrect geometric model. The error is in reasoning, not fact extraction.

**Mitigation**: For safety-critical geometric calculations, use deterministic computation rather than LLM reasoning. Extract the relevant dimensions and apply the clearance formula programmatically, then provide the result to the model for narrative interpretation.

---

## Summary

| Failure Mode | Count | % of Low-Scoring | Root Cause | Fix Type |
|---|---|---|---|---|
| Sub-rubric inapplicability | 7 | 58% | Grading rubric | Query-type routing |
| Location detail omission | 4 | 33% | Prompt design | Prompt engineering |
| Terminology misinterpretation | 2 | 17% | Domain knowledge gap | Validation layer |
| Mathematical reasoning | 1 | 8% | Reasoning limitation | Deterministic computation |

The largest failure mode (58%) is a grading artifact, not a model failure. The grading rubric penalizes regulatory queries for not containing information that was never relevant. Fixing the rubric routing would raise the aggregate score from 0.924 to approximately 0.97, but this would also reduce the rubric's sensitivity to airport identification errors on actual incident cases. The tradeoff between rubric generality and query-type specificity is a design decision that should be made explicitly.
