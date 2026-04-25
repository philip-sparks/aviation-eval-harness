"""Aviation mock tool schemas and simulated responses.

Defines 6 aviation tools with JSON Schema parameters and
simulate() methods that return plausible mock data.
"""

from __future__ import annotations

import json
import random
from dataclasses import dataclass
from typing import Any

from evals.aviation_domain import AIRPORTS
from datasets.generators.generate_metar import generate_metar


@dataclass
class ToolSchema:
    """Mock tool definition."""

    name: str
    description: str
    parameters: dict  # JSON Schema

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "description": self.description,
            "parameters": self.parameters,
        }

    def simulate(self, args: dict) -> dict:
        """Simulate tool execution with plausible mock data."""
        return TOOL_SIMULATORS[self.name](args)


# Tool schemas
METAR_LOOKUP = ToolSchema(
    name="metar_lookup",
    description="Retrieve weather observations (METAR) for an airport at a given time.",
    parameters={
        "type": "object",
        "properties": {
            "icao_code": {"type": "string", "description": "ICAO airport code (e.g., KDFW)"},
            "timestamp": {"type": "string", "description": "ISO 8601 timestamp"},
        },
        "required": ["icao_code"],
    },
)

TRACK_QUERY = ToolSchema(
    name="track_query",
    description="Retrieve ADS-B track points for an aircraft by Mode S hex code and time window.",
    parameters={
        "type": "object",
        "properties": {
            "mode_s_hex": {"type": "string", "description": "Mode S transponder hex code"},
            "time_window": {
                "type": "object",
                "properties": {
                    "start": {"type": "string", "description": "ISO 8601 start time"},
                    "end": {"type": "string", "description": "ISO 8601 end time"},
                },
            },
        },
        "required": ["mode_s_hex"],
    },
)

REGULATION_SEARCH = ToolSchema(
    name="regulation_search",
    description="Look up a specific FAR/AIM section by reference number.",
    parameters={
        "type": "object",
        "properties": {
            "far_section": {"type": "string", "description": "FAR section reference (e.g., 91.175)"},
        },
        "required": ["far_section"],
    },
)

AIRPORT_INFO = ToolSchema(
    name="airport_info",
    description="Retrieve airport metadata including runways, elevation, and coordinates.",
    parameters={
        "type": "object",
        "properties": {
            "icao_code": {"type": "string", "description": "ICAO airport code"},
        },
        "required": ["icao_code"],
    },
)

NOTAM_CHECK = ToolSchema(
    name="notam_check",
    description="Check NOTAMs (Notices to Air Missions) for an airport on a given date.",
    parameters={
        "type": "object",
        "properties": {
            "icao_code": {"type": "string", "description": "ICAO airport code"},
            "date": {"type": "string", "description": "Date in YYYY-MM-DD format"},
        },
        "required": ["icao_code", "date"],
    },
)

AIRCRAFT_INFO = ToolSchema(
    name="aircraft_info",
    description="Retrieve aircraft performance characteristics by ICAO type designator.",
    parameters={
        "type": "object",
        "properties": {
            "icao_type_designator": {
                "type": "string",
                "description": "ICAO aircraft type designator (e.g., B738, A320)",
            },
        },
        "required": ["icao_type_designator"],
    },
)

# Registry of all tools
TOOL_REGISTRY: dict[str, ToolSchema] = {
    "metar_lookup": METAR_LOOKUP,
    "track_query": TRACK_QUERY,
    "regulation_search": REGULATION_SEARCH,
    "airport_info": AIRPORT_INFO,
    "notam_check": NOTAM_CHECK,
    "aircraft_info": AIRCRAFT_INFO,
}


def get_tool_schemas_json() -> str:
    """Get all tool schemas as a JSON string."""
    return json.dumps([t.to_dict() for t in TOOL_REGISTRY.values()], indent=2)


# Simulators
def _simulate_metar(args: dict) -> dict:
    icao = args.get("icao_code", "KDFW")
    return {
        "icao": icao,
        "metar": generate_metar(icao, preset="clear_day"),
        "observed_at": args.get("timestamp", "2024-01-15T12:00:00Z"),
    }


def _simulate_track(args: dict) -> dict:
    return {
        "mode_s_hex": args.get("mode_s_hex", "A00000"),
        "track_points": [
            {"timestamp_ms": 1700000000000 + i * 5000,
             "latitude": 32.9 + i * 0.01,
             "longitude": -97.0 + i * 0.005,
             "altitude_ft": 10000 - i * 300,
             "heading": 180,
             "ground_speed_kt": 250 - i * 5,
             "vertical_rate_fpm": -700}
            for i in range(10)
        ],
        "aircraft_type": "B738",
    }


def _simulate_regulation(args: dict) -> dict:
    section = args.get("far_section", "91.175")
    regulations = {
        "91.175": {
            "title": "Takeoff and landing under IFR",
            "text": "No person may begin the final approach segment of an instrument approach "
                    "procedure unless the latest weather report indicates that weather conditions "
                    "are at or above the authorized IFR landing minimums for that procedure.",
        },
        "91.126": {
            "title": "Operating on or in the vicinity of an airport in Class G airspace",
            "text": "Each person operating an aircraft at an airport without a control tower "
                    "shall comply with the requirements of this section.",
        },
        "121.651": {
            "title": "Takeoff and landing weather minimums: IFR",
            "text": "No person may dispatch or release an aircraft for a domestic or flag "
                    "operation unless the appropriate weather reports and forecasts indicate "
                    "conditions at or above the authorized landing minimums.",
        },
    }
    reg = regulations.get(section, {"title": f"FAR {section}", "text": "Section text not found."})
    return {"section": section, **reg}


def _simulate_airport_info(args: dict) -> dict:
    icao = args.get("icao_code", "KDFW")
    airport = AIRPORTS.get(icao)
    if airport:
        return {
            "icao": airport.icao,
            "name": airport.name,
            "latitude": airport.lat,
            "longitude": airport.lon,
            "elevation_ft": airport.elevation_ft,
            "runways": airport.runways,
        }
    return {"icao": icao, "name": "Unknown Airport", "runways": [], "elevation_ft": 0}


def _simulate_notam(args: dict) -> dict:
    icao = args.get("icao_code", "KDFW")
    return {
        "icao": icao,
        "date": args.get("date", "2024-01-15"),
        "notams": [
            {"id": f"A{random.randint(1000,9999)}/{random.randint(24,25)}",
             "type": "RWY",
             "text": f"RWY 13L/31R CLSD FOR MAINT 0800-1200"},
            {"id": f"A{random.randint(1000,9999)}/{random.randint(24,25)}",
             "type": "NAV",
             "text": f"ILS RWY 13R GP OTS"},
        ],
    }


def _simulate_aircraft_info(args: dict) -> dict:
    designator = args.get("icao_type_designator", "B738")
    aircraft_db = {
        "B738": {"name": "Boeing 737-800", "category": "L", "approach_speed_kt": 140,
                 "max_range_nm": 2935, "mtow_lbs": 174200, "engines": "2x CFM56-7B"},
        "A320": {"name": "Airbus A320", "category": "L", "approach_speed_kt": 137,
                 "max_range_nm": 3300, "mtow_lbs": 170000, "engines": "2x CFM56-5A/B or IAE V2500"},
        "B772": {"name": "Boeing 777-200", "category": "H", "approach_speed_kt": 145,
                 "max_range_nm": 5240, "mtow_lbs": 545000, "engines": "2x GE90/PW4000/Trent800"},
        "E175": {"name": "Embraer E175", "category": "L", "approach_speed_kt": 130,
                 "max_range_nm": 2000, "mtow_lbs": 82012, "engines": "2x GE CF34-8E"},
        "CRJ9": {"name": "Bombardier CRJ-900", "category": "L", "approach_speed_kt": 135,
                 "max_range_nm": 1550, "mtow_lbs": 84500, "engines": "2x GE CF34-8C5"},
    }
    info = aircraft_db.get(designator, {
        "name": f"Unknown ({designator})", "category": "M", "approach_speed_kt": 140,
    })
    return {"icao_type": designator, **info}


TOOL_SIMULATORS = {
    "metar_lookup": _simulate_metar,
    "track_query": _simulate_track,
    "regulation_search": _simulate_regulation,
    "airport_info": _simulate_airport_info,
    "notam_check": _simulate_notam,
    "aircraft_info": _simulate_aircraft_info,
}
