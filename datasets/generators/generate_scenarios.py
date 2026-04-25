"""Composite scenario generator.

Combines narratives, synthetic tracks, weather, and operations data
into full synthetic event scenarios matching the dataset JSONL schema.
"""

from __future__ import annotations

import random
from datetime import datetime, timedelta
from typing import Any

from evals.aviation_domain import AIRPORTS, EVENT_TYPES, EVENT_TYPE_ALIASES
from datasets.generators.generate_metar import generate_metar
from datasets.generators.generate_tracks import generate_track


# Aircraft type pool
AIRCRAFT_TYPES = [
    "B738", "B739", "A320", "A321", "B752", "E175", "CRJ9",
    "B772", "A332", "B763", "A319", "CRJ7",
]

# Narrative templates by event type
NARRATIVE_TEMPLATES = {
    "go_around": [
        "On approach to runway {runway} at {airport_name} ({airport_icao}), the crew of {callsign} "
        "({aircraft_type}) initiated a go-around at approximately {altitude} feet AGL due to {reason}. "
        "Weather at the time included {weather_desc}. The aircraft climbed to {climb_alt} feet and "
        "was vectored for another approach.",
        "{callsign}, a {aircraft_type}, was on final approach to {airport_icao} runway {runway} when "
        "the crew elected to go around at {altitude} feet. The reported reason was {reason}. "
        "Winds were {wind_desc}. The flight landed safely on the subsequent approach.",
    ],
    "unstable_approach": [
        "During approach to {airport_icao} runway {runway}, {callsign} ({aircraft_type}) was observed "
        "to be {instability_desc} inside {distance} miles. The crew {action} at {altitude} feet AGL. "
        "Approach speed was {speed} knots. Weather: {weather_desc}.",
        "The crew of {callsign} reported an unstable approach to runway {runway} at {airport_name}. "
        "The {aircraft_type} was {instability_desc} at {altitude} feet on {distance}-mile final. "
        "{action_desc}. Wind was {wind_desc}.",
    ],
    "tcas_ra": [
        "At {altitude} feet MSL, {callsign} ({aircraft_type}) received a TCAS Resolution Advisory "
        "({ra_type}) while {phase}. The crew {response}. Traffic was a {traffic_type} at "
        "{separation} feet vertical separation, approximately {lateral_dist} nm lateral distance. "
        "The event occurred in {airspace} airspace near {airport_icao}.",
        "A TCAS RA event occurred involving {callsign} ({aircraft_type}) at {altitude} feet near "
        "{airport_name}. The RA commanded {ra_type}. The crew responded by {response}. "
        "The intruder aircraft was a {traffic_type}.",
    ],
    "runway_excursion": [
        "During {phase} on runway {runway} at {airport_icao}, {callsign} ({aircraft_type}) "
        "departed the runway surface. Contributing factors included {factors}. "
        "Weather at the time: {weather_desc}. The runway condition was {rwy_condition}.",
    ],
    "surface_safety": [
        "A surface safety event occurred at {airport_name} ({airport_icao}) involving {callsign} "
        "({aircraft_type}). While taxiing on taxiway {taxiway}, the aircraft {event_desc}. "
        "Ground visibility was {visibility}. The event was classified as {severity}.",
    ],
    "runway_incursion": [
        "A runway incursion occurred at {airport_icao} when {callsign} ({aircraft_type}) "
        "{incursion_desc} runway {runway} while {other_traffic} was {other_action}. "
        "The event was categorized as Category {category}. Weather: {weather_desc}.",
    ],
}


def generate_scenario(
    event_type: str,
    airport_icao: str,
    difficulty: str = "medium",
    seed: int | None = None,
) -> dict:
    """Generate a full synthetic event scenario.

    Args:
        event_type: Event type key (e.g., "go_around", "tcas_ra").
        airport_icao: ICAO airport code.
        difficulty: "easy", "medium", or "hard".
        seed: Random seed for reproducibility.

    Returns:
        Dict matching the grounding_cases JSONL schema.
    """
    if seed is not None:
        random.seed(seed)

    airport = AIRPORTS.get(airport_icao)
    if airport is None:
        raise ValueError(f"Unknown airport: {airport_icao}")

    # Generate components
    callsign = f"SYN{random.randint(100, 999)}"
    aircraft_type = random.choice(AIRCRAFT_TYPES)
    runway = random.choice(airport.runways).split("/")[0]
    timestamp = datetime.utcnow() - timedelta(days=random.randint(1, 365))

    # Generate weather
    weather_preset = _weather_for_event(event_type)
    metar = generate_metar(airport_icao, preset=weather_preset, timestamp=timestamp)

    # Generate track
    profile = _profile_for_event(event_type)
    track = generate_track(airport_icao, runway, profile, aircraft_type, n_points=30)

    # Generate narrative
    narrative = _generate_narrative(
        event_type, airport, runway, callsign, aircraft_type, metar, difficulty
    )

    # Generate expected and negative facts
    expected_facts, negative_facts = _generate_facts(
        event_type, airport, runway, callsign, aircraft_type, difficulty
    )

    # Build case ID
    event_code = EVENT_TYPE_ALIASES.get(event_type, event_type).upper()
    case_id = f"SYN-{event_code}-{airport_icao}-{random.randint(1000, 9999)}"

    return {
        "case_id": case_id,
        "source_type": "synthetic",
        "event_type": event_type,
        "airport_icao": airport_icao,
        "context": narrative,
        "query": _generate_query(event_type, airport_icao),
        "expected_facts": expected_facts,
        "negative_facts": negative_facts,
        "difficulty": difficulty,
        "metadata": {
            "aircraft_type": aircraft_type,
            "callsign": callsign,
            "runway": runway,
            "metar": metar,
            "track_points": len(track),
            "phase_of_flight": profile,
            "generated": datetime.utcnow().isoformat(),
        },
    }


def _weather_for_event(event_type: str) -> str:
    """Select appropriate weather preset for event type."""
    mapping = {
        "unstable_approach": "gusty_crosswind",
        "go_around": "low_vis_approach",
        "runway_excursion": "winter_ops",
        "surface_safety": "low_vis_approach",
        "runway_incursion": "low_vis_approach",
        "tcas_ra": "clear_day",
    }
    return mapping.get(event_type, "clear_day")


def _profile_for_event(event_type: str) -> str:
    """Select track profile type for event type."""
    mapping = {
        "go_around": "go_around",
        "unstable_approach": "approach",
        "tcas_ra": "approach",
        "runway_excursion": "approach",
        "surface_safety": "taxi",
        "runway_incursion": "taxi",
    }
    return mapping.get(event_type, "approach")


def _generate_narrative(
    event_type: str, airport, runway: str, callsign: str,
    aircraft_type: str, metar: str, difficulty: str
) -> str:
    """Generate event narrative from templates."""
    templates = NARRATIVE_TEMPLATES.get(event_type, NARRATIVE_TEMPLATES.get("go_around", [""]))
    template = random.choice(templates)

    # Common fill values
    fill = {
        "airport_icao": airport.icao,
        "airport_name": airport.name,
        "runway": runway,
        "callsign": callsign,
        "aircraft_type": aircraft_type,
        "altitude": random.choice([200, 300, 500, 800, 1000, 1500]),
        "climb_alt": random.choice([3000, 4000, 5000]),
        "speed": random.randint(130, 165),
        "distance": random.choice(["3", "4", "5"]),
        "weather_desc": f"METAR: {metar}",
        "wind_desc": "variable",
        "reason": random.choice([
            "traffic on the runway", "unstabilized approach",
            "wind shear alert", "visual contact not established",
            "runway not clear", "ATC instruction",
        ]),
        "instability_desc": random.choice([
            "above glideslope", "fast on approach", "high and fast",
            "below glideslope with excessive sink rate",
        ]),
        "action": random.choice(["continued to land", "executed a go-around"]),
        "action_desc": random.choice([
            "The crew elected to continue the approach",
            "A go-around was executed",
        ]),
        "ra_type": random.choice(["Climb", "Descend", "Monitor Vertical Speed"]),
        "phase": random.choice(["in cruise", "on descent", "climbing through"]),
        "response": random.choice(["complied with the RA", "followed the RA guidance"]),
        "traffic_type": random.choice(["B738", "A320", "E175", "CRJ9"]),
        "separation": random.choice([300, 500, 700, 1000]),
        "lateral_dist": random.choice([1, 2, 3, 5]),
        "airspace": random.choice(["Class B", "Class C", "Class E"]),
        "factors": random.choice([
            "wet runway and gusty crosswind",
            "contaminated runway surface",
            "high approach speed",
        ]),
        "rwy_condition": random.choice(["wet", "dry", "contaminated with snow"]),
        "taxiway": random.choice(["A", "B", "C", "D", "K", "M"]),
        "event_desc": random.choice([
            "crossed a hold-short line without clearance",
            "came into close proximity with another aircraft",
        ]),
        "visibility": random.choice(["good", "reduced due to fog", "marginal"]),
        "severity": random.choice(["minor", "moderate"]),
        "incursion_desc": random.choice([
            "entered", "crossed", "taxied onto",
        ]),
        "other_traffic": random.choice(["a B738", "an A320", "another aircraft"]),
        "other_action": random.choice([
            "on short final", "on takeoff roll", "departing",
        ]),
        "category": random.choice(["A", "B", "C", "D"]),
    }

    try:
        return template.format(**fill)
    except KeyError:
        return template


def _generate_query(event_type: str, airport_icao: str) -> str:
    """Generate an analysis query for the event."""
    queries = {
        "go_around": f"Analyze this go-around event at {airport_icao}. What were the contributing factors and was the decision appropriate?",
        "unstable_approach": f"Assess this unstable approach at {airport_icao}. What parameters were outside stabilized approach criteria?",
        "tcas_ra": "Analyze this TCAS RA event. What was the threat geometry and was the crew response appropriate?",
        "runway_excursion": f"Analyze this runway excursion at {airport_icao}. What factors contributed to the excursion?",
        "surface_safety": f"Assess this surface safety event at {airport_icao}. What procedures were not followed?",
        "runway_incursion": f"Analyze this runway incursion at {airport_icao}. What category was the incursion and what were the contributing factors?",
    }
    return queries.get(event_type, f"Analyze this aviation safety event at {airport_icao}.")


def _generate_facts(
    event_type: str, airport, runway: str, callsign: str,
    aircraft_type: str, difficulty: str
) -> tuple[list[str], list[str]]:
    """Generate expected and negative facts."""
    expected = [airport.icao, event_type.replace("_", " ")]

    if difficulty in ("easy", "medium"):
        expected.extend([aircraft_type, runway])
    if difficulty == "easy":
        expected.append(callsign)

    # Negative facts: wrong airports, wrong event types, wrong aircraft
    wrong_airports = [a for a in ["KJFK", "KORD", "KLAX", "KATL", "KDEN"] if a != airport.icao]
    wrong_types = [t for t in AIRCRAFT_TYPES if t != aircraft_type]

    negative = [random.choice(wrong_airports)]
    if difficulty in ("medium", "hard"):
        negative.append(random.choice(wrong_types))
    if difficulty == "hard":
        negative.append(random.choice(wrong_airports[:2]))

    return expected, negative
