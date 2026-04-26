# Top Disagreements Between Raters

Showing the 5 examples with the largest aggregate score difference.

## 1. GND-FAR-007 (difference: 0.530)

**Primary aggregate**: 0.470
**Second rater aggregate**: 1.000

| Sub-Rubric | Primary | Second |
|---|---|---|
| airport_correctness | 1 | 5 |
| event_analysis_quality | 1 | 5 |
| fact_extraction_accuracy | 4 | 5 |
| flight_phase_relevance | 5 | 5 |

**Second rater reasoning**: This response directly addresses the regulatory requirement from FAR 91.175(c) without involving specific airports or flight incidents. Airport_correctness scores 5 because no airport information was required or presented—the query is purely regulatory. Event_analysis_quality scores 5 because the response correctly identifies the regulation type and accurately breaks down both mandatory conditions (positioning and visibility) with proper causal logic. Fact_extraction_accuracy scores 5 because all key facts from the source are present and accurately extracted with no fabrication or omissions—the two core requirements are quoted directly and explained thoroughly. Flight_phase_relevance scores 5 because the response correctly identifies this applies to the approach phase (specifically below DA/DH) and uses phase-appropriate parameters (normal rate of descent, normal maneuvers, stabilized approach, visibility minimums). The response demonstrates clear understanding of the binary AND logic required by the regulation and explains the safety rationale appropriately.

**Model output (first 300 chars)**: Based on the provided source context, FAR 91.175(c) establishes specific requirements that must be met before a pilot may continue an approach below the Decision Altitude/Decision Height (DA/DH). Here is my detailed analysis:

## Primary Requirements for Descent Below DA/DH

FAR 91.175(c) prohibits 

---

## 2. GND-FAR-047 (difference: 0.480)

**Primary aggregate**: 0.520
**Second rater aggregate**: 1.000

| Sub-Rubric | Primary | Second |
|---|---|---|
| airport_correctness | 1 | 5 |
| event_analysis_quality | 1 | 5 |
| fact_extraction_accuracy | 5 | 5 |
| flight_phase_relevance | 5 | 5 |

**Second rater reasoning**: The model output directly addresses Class D airport surface operations without requiring specific airport identification, making airport correctness fully applicable and correct. Event analysis is excellent—it correctly identifies runway incursion as the safety concern, accurately traces the causal chain from non-compliance to incursions, and identifies all contributing factors (ATC compliance, read-back procedures, explicit clearance requirements). Fact extraction is accurate and complete: FAR 91.129(i) requirements are correctly stated, AIM 4-3-18 procedures are accurately presented, and the runway incursion causal relationship is properly extracted from source material with no fabrication. Flight phase relevance is perfect—the response appropriately focuses on surface operations (taxi, ground movement) with phase-appropriate parameters (runway hold short markings, ATC clearances for surface movement, read-back procedures) and avoids irrelevant flight phase references. The analysis demonstrates strong understanding of regulatory requirements and safety implications.

**Model output (first 300 chars)**: ## Pilot Responsibilities for Surface Operations at Class D Airports

Based on the provided aviation safety data, pilots operating at Class D airports have specific regulatory and procedural responsibilities for surface operations:

### Regulatory Requirements

**FAR 91.129(i) Compliance:**
- Pilots

---

## 3. GND-FAR-009 (difference: 0.240)

**Primary aggregate**: 0.760
**Second rater aggregate**: 1.000

| Sub-Rubric | Primary | Second |
|---|---|---|
| airport_correctness | 5 | 5 |
| event_analysis_quality | 1 | 5 |
| fact_extraction_accuracy | 5 | 5 |
| flight_phase_relevance | 5 | 5 |

**Second rater reasoning**: This is a regulatory interpretation query rather than an accident/incident analysis. Airport Correctness scores 5 because no specific airport is referenced—the regulation is generic. Event Analysis Quality scores 5 because the model correctly identifies the regulatory requirement type and accurately explains the causal framework (deviation → go-around unless correctable). Fact Extraction Accuracy scores 5 because all key facts from the source are present and accurate: the dual obligation to establish and use procedures, the four mandatory parameters (approach speed, configuration, rate of descent, power setting), the altitude-specific requirement, and the deviation protocol with the PIC exception. No fabrication or inaccuracies detected. Flight Phase Relevance scores 5 because the analysis correctly focuses on the approach phase and uses phase-appropriate parameters (descent rate, configuration, approach speed, power setting) throughout. The model's structured breakdown and safety implications discussion are accurate and well-supported by the source context.

**Model output (first 300 chars)**: ## Analysis of FAR 121.651 Stabilized Approach Requirements

Based on the provided source context, FAR 121.651 establishes comprehensive requirements for stabilized approach procedures that certificate holders must implement and follow.

### Primary Regulatory Requirement

FAR 121.651 mandates that 

---

## 4. GND-FAR-060 (difference: 0.230)

**Primary aggregate**: 0.770
**Second rater aggregate**: 1.000

| Sub-Rubric | Primary | Second |
|---|---|---|
| airport_correctness | 5 | 5 |
| event_analysis_quality | 2 | 5 |
| fact_extraction_accuracy | 4 | 5 |
| flight_phase_relevance | 5 | 5 |

**Second rater reasoning**: The model output accurately extracts and presents all key regulatory and advisory information from the source context. Airport Correctness scores 5 because no specific airports or runways are discussed in the query—the question asks about general rules and recommendations, which the model correctly addresses. Event Analysis Quality scores 5 because the model correctly identifies the regulatory framework (FAR 91.113(b)) and advisory guidance (AIM 4-3-14), accurately explains the right-of-way hierarchy, and properly identifies contributing factors to surface safety (situational awareness, visual aids, unfamiliar airport risk). Fact Extraction Accuracy scores 5 because all key facts are present and accurate: the right-of-way rule for aircraft to the right, the applicability to departing aircraft, the emphasis on situational awareness, and all four recommended visual aids (airport diagrams, enhanced taxiway markings, cockpit moving map displays, and the specific focus on unfamiliar airports). No fabrication or inaccuracies are present. Flight Phase Relevance scores 5 because the analysis correctly focuses on surface operations (taxiing/ground movement phase) and uses phase-appropriate parameters including surface-specific rules, taxiway markings, and airport diagrams rather than en route or approach-phase considerations.

**Model output (first 300 chars)**: ## Analysis of Right-of-Way Rules and Recommendations for Surface Operations

Based on the provided aviation safety data, there are specific regulatory requirements and safety recommendations that govern aircraft surface operations at airports.

### Regulatory Right-of-Way Rules

**FAR 91.113(b) Rig

---

## 5. GND-FAR-017 (difference: 0.200)

**Primary aggregate**: 0.800
**Second rater aggregate**: 1.000

| Sub-Rubric | Primary | Second |
|---|---|---|
| airport_correctness | 5 | 5 |
| event_analysis_quality | 5 | 5 |
| fact_extraction_accuracy | 1 | 5 |
| flight_phase_relevance | 5 | 5 |

**Second rater reasoning**: This response is not about a specific airport incident but rather a regulatory interpretation question. Airport_correctness scores 5 because the query doesn't involve airport identification—it's a regulatory question, so this dimension is N/A but marked as fully correct since no airport claims are made. Event_analysis_quality scores 5: the model correctly identifies the event type (missed approach execution requirements), accurately extracts the causal framework (safety determination triggers timing), and presents the complete causal chain from FAR 91.175(e) through AIM 5-4-21 clarification. Fact_extraction_accuracy scores 5: all key facts are present and accurate—the three trigger conditions (weather, equipment failure, other circumstances), the mandatory language, the final approach segment applicability, the visual reference requirement, and the missed approach point timing limit. No fabrication or inaccuracies detected. Flight_phase_relevance scores 5: the response correctly identifies and analyzes the final approach segment phase, uses phase-appropriate parameters (visual reference criteria, missed approach point), and maintains consistency with instrument approach procedures throughout. The response demonstrates comprehensive understanding of the regulatory framework with no errors or omissions.

**Model output (first 300 chars)**: Based on the provided source context, the Federal Aviation Regulations (FARs) and Aeronautical Information Manual (AIM) establish clear requirements for missed approach execution:

## FAR 91.175(e) Requirements

**Mandatory Execution Triggers:**
The regulation requires pilots to immediately execute 

---
