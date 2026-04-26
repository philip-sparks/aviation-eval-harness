# Datasets

## Overview

This directory contains evaluation datasets for the aviation eval harness. **All data is fully synthetic.** No verbatim ASRS reports, NTSB investigation records, or proprietary data are included. Narratives are original compositions that follow realistic aviation safety patterns; all details (altitudes, airspeeds, crew actions, outcomes, report numbers) are fabricated.

Public reference material -ICAO airport identifiers, aircraft type designators, FAR section numbers, METAR format conventions -is used as schema for realism but carries no proprietary content.

## Dataset Files

### `grounding_cases.jsonl`
**60 aviation safety grounding cases.**

Schema:
```json
{
  "case_id": "GND-ASRS-001",
  "source_type": "asrs | ntsb | far_aim",
  "event_type": "unstable_approach | go_around | tcas_ra | runway_excursion | surface_safety | runway_incursion",
  "airport_icao": "KDFW",
  "context": "Source document text...",
  "query": "Analysis question...",
  "expected_facts": ["fact1", "fact2"],
  "negative_facts": ["wrong_airport", "wrong_aircraft"],
  "difficulty": "easy | medium | hard",
  "metadata": {"aircraft_type": "B738", "phase_of_flight": "approach"}
}
```

Provenance:
- **Generation method**: Hand-authored by the project author. Each narrative is an original synthetic composition modeled on the structure and language of publicly available aviation safety documents.
- **ASRS-style cases** (prefix `GND-ASRS-`): Follow the narrative structure of NASA ASRS voluntary safety reports. No verbatim text from real ASRS reports is included. Report numbers (ACN values) are fictional.
- **NTSB-style cases** (prefix `GND-NTSB-`): Follow the probable-cause summary format used in public NTSB reports. All incident details are fabricated.
- **FAR/AIM cases** (prefix `GND-FAR-`): Reference real public Federal Aviation Regulations by section number. The regulatory text is paraphrased, not copied verbatim.
- **No real identifying information**: No real pilot names, active operator callsigns, or flight numbers appear. Aircraft types (B737-800, A320, etc.) and airport codes (KDFW, KJFK, etc.) are public identifiers used for realism.
- **Labeling**: Expected facts and negative facts are hand-labeled by the project author.
- **Known limitations**: 60 cases is sufficient for evaluation but too small for distribution-level conclusions. Difficulty ratings are subjective. Event type distribution skews toward approach-phase events.

### `tool_use_cases.jsonl`
**35 tool use scenarios.**

Schema:
```json
{
  "case_id": "TOOL-001",
  "query": "User question...",
  "context": "Optional background...",
  "expected_tools": [{"tool": "metar_lookup", "args": {"icao_code": "KDFW"}}],
  "expected_sequence": ["metar_lookup", "airport_info"],
  "distractor_tools": [{"tool": "track_query", "reasoning": "Wrong tool for weather"}],
  "difficulty": "easy | medium | hard",
  "metadata": {}
}
```

Provenance:
- **Generation method**: Hand-authored by the project author.
- **Tool schemas**: Based on the 6 mock tools defined in `evals/tool_use/mock_tools.py` (metar_lookup, track_query, regulation_search, airport_info, notam_check, aircraft_info).
- **Mode S hex codes**: All Mode S hex codes (e.g., A4B210, A0F2C8) are fictional and do not correspond to real aircraft.
- **Distractor tools**: Each case includes at least one plausible but incorrect tool to test selectivity.
- **Known limitations**: 35 cases cover 1-to-6-tool combinations but do not exhaustively test all tool×argument permutations.

### `adversarial_prompts.jsonl`
**35 perturbation templates for robustness testing.**

Schema:
```json
{
  "case_id": "ADV-001",
  "base_prompt": "Original clean prompt...",
  "perturbation_type": "paraphrase | typo | distractor_injection | synonym | nearby_airport_swap | conflicting_metar",
  "perturbed_prompt": "Modified version...",
  "expected_behavior": "same_answer | detect_error | robust_to_change",
  "baseline_expected_facts": ["fact1"],
  "difficulty": "easy | medium | hard",
  "metadata": {}
}
```

Provenance:
- **Generation method**: Hand-authored by the project author. Each case consists of a base prompt and a systematically perturbed variant.
- **Perturbation types**: 6 perturbation categories (paraphrase, typo, distractor injection, synonym swap, nearby airport swap, conflicting METAR). Distribution is approximately even across categories.
- **METAR strings**: Synthetic weather observations following standard METAR format. No real METARs are used.
- **Known limitations**: Perturbation severity is not quantified. Some perturbation types (e.g., conflicting METAR) are inherently more disruptive than others (e.g., typo), making cross-type comparison imprecise.

### `refusal_cases.jsonl`
**25 refusal boundary cases.**

Schema:
```json
{
  "case_id": "REF-001",
  "query": "Question...",
  "context": "Optional context...",
  "expected_behavior": "answer | refuse | hedge",
  "category": "over_refusal | under_refusal | borderline",
  "rationale": "Why this behavior is expected...",
  "metadata": {}
}
```

Provenance:
- **Generation method**: Hand-authored by the project author.
- **Category distribution**: 8 over-refusal cases (legitimate questions that should be answered), 8 under-refusal cases (requests that should be declined), 9 borderline cases (ambiguous situations requiring caveats).
- **Over-refusal cases**: Cover publicly available safety knowledge (stabilized approach criteria, FARs, TCAS procedures, aeromedical factors). These should never be refused.
- **Under-refusal cases**: Cover ASRS reporter re-identification, pilot blame attribution, safety data fabrication, and maintenance record fraud. ASRS report numbers (e.g., ACN 1987432) are fictional.
- **Borderline cases**: Cover causal attribution from incomplete data, comparative performance analysis, and future safety event prediction. Expected behavior is "hedge" (answer with caveats).
- **Known limitations**: 25 cases is a small sample. The boundary between "refuse" and "hedge" is inherently subjective. No adversarial jailbreak prompts are included.

## Synthetic Data Generators

Located in `generators/`:

- **`generate_metar.py`**: Produces valid METAR strings with presets (low_vis_approach, gusty_crosswind, clear_day, winter_ops, thunderstorm). Uses standard METAR encoding format; no remarks section.
- **`generate_tracks.py`**: Produces ADS-B track points with flight profiles (approach, departure, taxi, go_around). Uses simplified physics (no wind modeling, constant descent rates).
- **`generate_scenarios.py`**: Composes full synthetic event scenarios combining narratives, weather, tracks, and operations data.

All generators produce fully synthetic output. No real ADS-B data, real METARs, or real safety reports are used as seeds.

## Labeling Process

- Expected facts and negative facts are hand-labeled by the project author
- Each case specifies difficulty level based on the complexity of the analysis required
- Negative facts are chosen to be plausible hallucinations (nearby airports, similar aircraft types)

## Known Issues and Limitations

- All narratives are synthetic recreations of realistic patterns, not verbatim copies of real reports
- Synthetic METAR strings use a simplified format (no remarks section)
- ADS-B tracks use simplified physics (no wind modeling, constant descent rates)
- Difficulty ratings are subjective
- The dataset is not large enough for training; it is designed for evaluation only
- Single labeler (the project author) -no inter-rater reliability computed for labels

## Adding New Cases

1. Follow the schema for the relevant dataset
2. Assign a unique `case_id` with appropriate prefix
3. Include at least 2 expected_facts and 1 negative_fact
4. Set difficulty based on: easy (single fact extraction), medium (multi-fact analysis), hard (requires inference)
5. Validate JSONL: `python -c "import json; [json.loads(l) for l in open('your_file.jsonl')]"`
6. **All contributed data must be fully synthetic** -see [CONTRIBUTING.md](../CONTRIBUTING.md)
