# Datasets

## Overview

This directory contains evaluation datasets for the aviation eval harness. All data is either from public sources or fully synthetic.

## Dataset Files

### `grounding_cases.jsonl`
**50-100 aviation safety grounding cases.**

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
- ASRS cases: Based on patterns from NASA ASRS public database narratives (de-identified, voluntary safety reports)
- NTSB cases: Based on patterns from public NTSB probable cause summaries
- FAR/AIM cases: Reference public Federal Aviation Regulations

### `tool_use_cases.jsonl`
**30-50 tool use scenarios.**

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

### `adversarial_prompts.jsonl`
**30-50 perturbation templates.**

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

### `refusal_cases.jsonl`
**20-30 refusal boundary cases.**

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

## Synthetic Data Generators

Located in `generators/`:

- **`generate_metar.py`**: Produces valid METAR strings with presets (low_vis_approach, gusty_crosswind, clear_day, winter_ops, thunderstorm)
- **`generate_tracks.py`**: Produces ADS-B track points with flight profiles (approach, departure, taxi, go_around)
- **`generate_scenarios.py`**: Composes full synthetic event scenarios combining narratives, weather, tracks, and operations data

## Labeling Process

- Expected facts and negative facts are hand-labeled by the project author
- Each case specifies difficulty level based on the complexity of the analysis required
- Negative facts are chosen to be plausible hallucinations (nearby airports, similar aircraft types)

## Known Issues and Limitations

- ASRS-style narratives are synthetic recreations of real report patterns, not verbatim copies
- Synthetic METAR strings use a simplified format (no remarks section)
- ADS-B tracks use simplified physics (no wind modeling, constant descent rates)
- Difficulty ratings are subjective
- The dataset is not large enough for training; it is designed for evaluation only

## Adding New Cases

1. Follow the schema for the relevant dataset
2. Assign a unique `case_id` with appropriate prefix
3. Include at least 2 expected_facts and 1 negative_fact
4. Set difficulty based on: easy (single fact extraction), medium (multi-fact analysis), hard (requires inference)
5. Validate JSONL: `python -c "import json; [json.loads(l) for l in open('your_file.jsonl')]"`
