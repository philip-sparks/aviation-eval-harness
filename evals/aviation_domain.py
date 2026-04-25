"""Aviation domain constants for the evaluation harness.

Centralizes event taxonomy, airport data, semantic equivalences,
and numeric tolerances used across all eval categories.
"""

from dataclasses import dataclass


# ---------------------------------------------------------------------------
# Event type taxonomy
# ---------------------------------------------------------------------------

EVENT_TYPES = {
    "SST": "Surface Safety Event",
    "REX": "Runway Excursion",
    "IRT": "Irregular Turn",
    "RWT": "Wrong Taxiway/Runway",
    "MAR": "Missed Approach / Go-Around",
    "RRS": "Runway-Related Safety",
    "UA": "Unstable Approach",
    "TCAS_RA": "TCAS Resolution Advisory",
    "RI": "Runway Incursion",
}

# Mapping from normalized event names used in datasets
EVENT_TYPE_ALIASES = {
    "surface_safety": "SST",
    "runway_excursion": "REX",
    "irregular_turn": "IRT",
    "wrong_taxiway": "RWT",
    "go_around": "MAR",
    "missed_approach": "MAR",
    "runway_safety": "RRS",
    "unstable_approach": "UA",
    "tcas_ra": "TCAS_RA",
    "runway_incursion": "RI",
}

# ---------------------------------------------------------------------------
# Airport coordinate lookup table (lat, lon, elevation_ft)
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class AirportInfo:
    icao: str
    name: str
    lat: float
    lon: float
    elevation_ft: int
    runways: list[str]


AIRPORTS: dict[str, AirportInfo] = {
    "KATL": AirportInfo("KATL", "Hartsfield-Jackson Atlanta", 33.6407, -84.4277, 1026, ["08L/26R", "08R/26L", "09L/27R", "09R/27L", "10/28"]),
    "KDFW": AirportInfo("KDFW", "Dallas/Fort Worth International", 32.8998, -97.0403, 607, ["13L/31R", "13R/31L", "17C/35C", "17L/35R", "17R/35L", "18L/36R", "18R/36L"]),
    "KJFK": AirportInfo("KJFK", "John F. Kennedy International", 40.6413, -73.7781, 13, ["04L/22R", "04R/22L", "13L/31R", "13R/31L"]),
    "KORD": AirportInfo("KORD", "Chicago O'Hare International", 41.9742, -87.9073, 672, ["04L/22R", "04R/22L", "09C/27C", "09L/27R", "09R/27L", "10C/28C", "10L/28R", "10R/28L"]),
    "KLAX": AirportInfo("KLAX", "Los Angeles International", 33.9425, -118.4081, 128, ["06L/24R", "06R/24L", "07L/25R", "07R/25L"]),
    "KSFO": AirportInfo("KSFO", "San Francisco International", 37.6213, -122.3790, 13, ["01L/19R", "01R/19L", "10L/28R", "10R/28L"]),
    "KDEN": AirportInfo("KDEN", "Denver International", 39.8561, -104.6737, 5431, ["07/25", "08/26", "16L/34R", "16R/34L", "17L/35R", "17R/35L"]),
    "KLAS": AirportInfo("KLAS", "Harry Reid International", 36.0840, -115.1537, 2181, ["01L/19R", "01R/19L", "08L/26R", "08R/26L"]),
    "KPDX": AirportInfo("KPDX", "Portland International", 45.5898, -122.5951, 31, ["10L/28R", "10R/28L", "03/21"]),
    "KSNA": AirportInfo("KSNA", "John Wayne Airport", 33.6757, -117.8683, 56, ["02L/20R", "02R/20L"]),
    "KOKC": AirportInfo("KOKC", "Will Rogers World Airport", 35.3931, -97.6007, 1295, ["13/31", "17L/35R", "17R/35L"]),
    "KIAD": AirportInfo("KIAD", "Washington Dulles International", 38.9531, -77.4565, 313, ["01C/19C", "01L/19R", "01R/19L", "12/30"]),
    "KDAL": AirportInfo("KDAL", "Dallas Love Field", 32.8471, -96.8518, 487, ["13L/31R", "13R/31L", "18/36"]),
    "KBOS": AirportInfo("KBOS", "Boston Logan International", 42.3656, -71.0096, 20, ["04L/22R", "04R/22L", "09/27", "14/32", "15R/33L"]),
    "KMIA": AirportInfo("KMIA", "Miami International", 25.7959, -80.2870, 8, ["08L/26R", "08R/26L", "09/27", "12/30"]),
    "KSEA": AirportInfo("KSEA", "Seattle-Tacoma International", 47.4502, -122.3088, 433, ["16C/34C", "16L/34R", "16R/34L"]),
    "KPHX": AirportInfo("KPHX", "Phoenix Sky Harbor International", 33.4373, -112.0078, 1135, ["07L/25R", "07R/25L", "08/26"]),
    "KMSP": AirportInfo("KMSP", "Minneapolis-Saint Paul International", 44.8848, -93.2223, 841, ["04/22", "12L/30R", "12R/30L", "17/35"]),
}

# Nearby airport pairs (for adversarial swap testing)
NEARBY_AIRPORT_PAIRS = [
    ("KDFW", "KDAL"),   # Dallas area
    ("KJFK", "KLGA"),   # New York area
    ("KIAD", "KDCA"),   # Washington DC area
    ("KSFO", "KOAK"),   # San Francisco Bay area
    ("KLAX", "KSNA"),   # Los Angeles area
]


# ---------------------------------------------------------------------------
# Semantic equivalence dictionaries
# ---------------------------------------------------------------------------

SEMANTIC_EQUIVALENCES: dict[str, list[str]] = {
    # Event types
    "go-around": ["go around", "go-around", "missed approach", "went around", "balked landing"],
    "tcas ra": ["tcas ra", "tcas resolution advisory", "resolution advisory", "ra event", "tcas alert"],
    "unstable approach": ["unstable approach", "unstabilized approach", "non-stabilized approach"],
    "runway excursion": ["runway excursion", "runway overrun", "veer-off", "veer off"],
    "runway incursion": ["runway incursion", "runway conflict", "runway transgression"],

    # Aircraft components
    "flight management system": ["fms", "flight management system", "flight management computer"],
    "instrument landing system": ["ils", "instrument landing system"],
    "traffic collision avoidance system": ["tcas", "traffic collision avoidance system", "traffic alert"],

    # Phases of flight
    "initial approach": ["initial approach", "initial approach fix", "iaf"],
    "final approach": ["final approach", "final approach fix", "faf", "on final"],
    "short final": ["short final", "on short final"],
    "touchdown": ["touchdown", "landing", "touched down"],
    "rotation": ["rotation", "rotate", "vr"],
    "initial climb": ["initial climb", "after takeoff", "departure climb"],

    # Common abbreviations
    "above ground level": ["agl", "above ground level"],
    "mean sea level": ["msl", "mean sea level"],
    "knots": ["kt", "kts", "knots"],
    "feet per minute": ["fpm", "feet per minute", "ft/min"],
    "nautical miles": ["nm", "nautical miles", "nmi"],
}


# ---------------------------------------------------------------------------
# Numeric tolerances for grading
# ---------------------------------------------------------------------------

NUMERIC_TOLERANCES = {
    "altitude_ft": 500,         # ±500 ft
    "descent_rate_fpm": 200,    # ±200 fpm
    "heading_deg": 10,          # ±10 degrees
    "speed_kt": 10,             # ±10 knots
    "distance_nm": 1.0,         # ±1.0 nm
    "visibility_sm": 0.25,      # ±0.25 statute miles
    "temperature_c": 2,         # ±2 degrees C
    "wind_speed_kt": 5,         # ±5 knots
    "altimeter_inhg": 0.02,     # ±0.02 inHg
}


# ---------------------------------------------------------------------------
# Phase-of-flight validation rules
# ---------------------------------------------------------------------------

PHASE_OF_FLIGHT = {
    "surface": {"max_altitude_ft": 200, "max_speed_kt": 30, "description": "Ground operations"},
    "takeoff": {"min_speed_kt": 60, "max_altitude_ft": 1500, "description": "Takeoff roll and initial climb"},
    "departure": {"min_altitude_ft": 500, "max_altitude_ft": 18000, "description": "Departure climb"},
    "cruise": {"min_altitude_ft": 10000, "description": "En route cruise"},
    "approach": {"min_altitude_ft": 200, "max_altitude_ft": 10000, "description": "Approach phase"},
    "landing": {"max_altitude_ft": 200, "max_speed_kt": 170, "description": "Landing phase"},
}


# ---------------------------------------------------------------------------
# Weighted sub-rubric defaults (matching Blazer 30/30/25/15 split)
# ---------------------------------------------------------------------------

GROUNDING_RUBRIC_WEIGHTS = {
    "airport_correctness": 0.30,
    "event_analysis_quality": 0.30,
    "fact_extraction_accuracy": 0.25,
    "flight_phase_relevance": 0.15,
}

# Anti-hallucination — common wrong airports to check
COMMON_HALLUCINATION_AIRPORTS = [
    "KJFK", "KOKC", "KORD", "KATL", "KLAX", "KDFW", "KSFO", "KDEN",
]
