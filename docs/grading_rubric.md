# Grounding Evaluation Grading Rubric

This document defines the scoring criteria for the four sub-rubrics used in the grounding evaluation. Each sub-rubric is scored on a 1-5 scale. The sub-rubrics are combined using weights of 30/30/25/15 to produce an aggregate grounding score normalized to 0-1.

## Sub-Rubric 1: Airport Correctness (Weight: 30%)

Evaluates whether the output correctly identifies the airport(s), runway(s), and location-specific information.

| Score | Description | Example |
|-------|-------------|---------|
| **5** | All airports, ICAO codes, and runway designations are correct. Location-specific details (elevation, layout references) are accurate. | Output correctly identifies KDFW, RWY 18R, and references DFW-specific geography. |
| **4** | Airport and runway are correct but minor location details are missing or imprecise. | Correctly identifies KJFK RWY 4R but does not mention the airport's proximity to water or other relevant terrain. |
| **3** | Airport is correct but runway is wrong, or airport is named but ICAO code is wrong/missing. | Says "Dallas Fort Worth" but refers to RWY 36L instead of the correct RWY 18R. |
| **2** | Airport is partially correct (e.g., right city, wrong airport) or significant location errors. | Refers to "Dallas" but discusses Love Field (KDAL) when the event occurred at DFW (KDFW). |
| **1** | Airport is completely wrong or not mentioned when required by the query. | Discusses an event at KORD when the source context describes an event at KDFW. |

## Sub-Rubric 2: Event Analysis Quality (Weight: 30%)

Evaluates whether the output correctly classifies and analyzes the aviation safety event.

| Score | Description | Example |
|-------|-------------|---------|
| **5** | Event type is correctly classified. All contributing factors identified. Causal chain is accurate and complete. Timeline of events is correct. | Correctly identifies an unstable approach, notes the airspeed deviation, configuration issue, and crew decision-making sequence. |
| **4** | Event type is correct. Most contributing factors identified. Minor gaps in causal reasoning or timeline. | Identifies the go-around and its trigger but omits one contributing factor mentioned in the source. |
| **3** | Event type is correct but analysis is superficial. Some contributing factors identified but causal reasoning has errors. | Correctly calls it a TCAS RA event but confuses which aircraft received the climb vs. descend advisory. |
| **2** | Event type is misclassified or analysis contains significant factual errors about what happened. | Describes a runway incursion as a runway excursion, or reverses the sequence of crew actions. |
| **1** | Event type is wrong and analysis is unrelated to what the source context describes. | Discusses wind shear recovery when the source describes a ground vehicle conflict during taxi. |

## Sub-Rubric 3: Fact Extraction Accuracy (Weight: 25%)

Evaluates whether specific factual details (aircraft type, altitude, speed, configurations, distances, times) are accurately extracted from the source context.

| Score | Description | Example |
|-------|-------------|---------|
| **5** | All key facts from the source are present in the output. Numerical values are accurate (within tolerances: altitude +/-500ft, speed +/-10kt, heading +/-10deg). No fabricated details. | Output includes "15 knots above Vref at 500 feet AGL" matching the source exactly. |
| **4** | Most key facts present. One minor numerical inaccuracy or one minor omission. No fabricated details. | Reports "approximately 500 feet AGL" when source says exactly "500 feet AGL" — close but slightly imprecise. Also omits one of four expected facts. |
| **3** | Some key facts present. Two or more minor omissions or inaccuracies. No fabricated details. | Reports the airspeed deviation and altitude but omits the runway designation and aircraft type. |
| **2** | Few key facts present. Significant omissions or numerical errors beyond tolerance. May include minor fabrication. | Reports "1,000 feet AGL" when the source says "500 feet AGL" — outside tolerance. |
| **1** | Key facts are mostly absent or wrong. Fabricated details present. | Claims the aircraft was at FL350 when the source describes a 500-foot approach event. Invents an aircraft type not mentioned in the source. |

## Sub-Rubric 4: Flight Phase Relevance (Weight: 15%)

Evaluates whether the output correctly identifies the phase of flight and uses phase-appropriate analysis.

| Score | Description | Example |
|-------|-------------|---------|
| **5** | Phase of flight is correctly identified. Analysis uses phase-appropriate parameters and references (e.g., approach speeds for approach events, taxi procedures for surface events). | Correctly identifies an approach-phase event and discusses Vref, glideslope, and decision altitude — all approach-relevant parameters. |
| **4** | Phase of flight is correct. Analysis mostly uses appropriate parameters but includes one irrelevant reference. | Correctly identifies a landing-roll event but briefly discusses approach speed (a different phase) when braking distance is the relevant parameter. |
| **3** | Phase of flight is correct but analysis applies parameters from a different phase. | Identifies a surface event but discusses altitude and airspeed (irrelevant to taxi operations). |
| **2** | Phase of flight is wrong but related (e.g., says "approach" for a landing-roll event). | Describes a taxi event as "ground operations during departure" when the aircraft had already landed. |
| **1** | Phase of flight is completely wrong (e.g., says "cruise" for a surface event). | Discusses cruise-altitude procedures for a pushback incident at the gate. |

## Usage Notes

- **Score independently**: Score each sub-rubric based on its own criteria. Do not let a high score in one rubric influence another.
- **Use the source context as ground truth**: The source context provided in the eval case is the sole reference. If a fact is not in the source context, the model should not include it.
- **Fabrication vs. omission**: Fabricated details (facts not in the source) are penalized more heavily than omissions (facts in the source that the model missed). A score of 3 with omissions is better than a score of 3 with fabrications.
- **Tolerance for paraphrasing**: The model may paraphrase facts from the source. As long as the meaning is preserved, paraphrasing should not reduce the score. "Go-around" and "missed approach" are equivalent. "TCAS RA" and "resolution advisory" are equivalent.
- **Aggregate calculation**: `aggregate = (airport * 0.30 + event * 0.30 + facts * 0.25 + phase * 0.15) / 5.0` to normalize from 1-5 to 0-1.
