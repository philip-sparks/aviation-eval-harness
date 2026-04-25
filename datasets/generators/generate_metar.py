"""Synthetic METAR string generator.

Produces valid METAR strings tied to scenario conditions for testing.
Supports presets for common weather scenarios.
"""

from __future__ import annotations

import random
from datetime import datetime


# Preset conditions
PRESETS = {
    "low_vis_approach": {
        "wind_dir": 180,
        "wind_speed": 8,
        "wind_gust": None,
        "visibility_sm": 0.5,
        "ceiling_ft": 200,
        "ceiling_type": "OVC",
        "temperature_c": 5,
        "dewpoint_c": 4,
        "altimeter_inhg": 29.92,
        "wx": "FG",
    },
    "gusty_crosswind": {
        "wind_dir": 270,
        "wind_speed": 18,
        "wind_gust": 32,
        "visibility_sm": 10,
        "ceiling_ft": 4500,
        "ceiling_type": "BKN",
        "temperature_c": 22,
        "dewpoint_c": 12,
        "altimeter_inhg": 29.85,
        "wx": None,
    },
    "clear_day": {
        "wind_dir": 200,
        "wind_speed": 5,
        "wind_gust": None,
        "visibility_sm": 10,
        "ceiling_ft": None,
        "ceiling_type": "CLR",
        "temperature_c": 25,
        "dewpoint_c": 10,
        "altimeter_inhg": 30.12,
        "wx": None,
    },
    "winter_ops": {
        "wind_dir": 350,
        "wind_speed": 12,
        "wind_gust": 20,
        "visibility_sm": 2,
        "ceiling_ft": 800,
        "ceiling_type": "OVC",
        "temperature_c": -5,
        "dewpoint_c": -7,
        "altimeter_inhg": 29.65,
        "wx": "SN",
    },
    "thunderstorm": {
        "wind_dir": 250,
        "wind_speed": 15,
        "wind_gust": 35,
        "visibility_sm": 3,
        "ceiling_ft": 2500,
        "ceiling_type": "BKN",
        "temperature_c": 28,
        "dewpoint_c": 24,
        "altimeter_inhg": 29.72,
        "wx": "TSRA",
    },
}


def generate_metar(
    icao: str,
    conditions: dict | None = None,
    preset: str | None = None,
    timestamp: datetime | None = None,
) -> str:
    """Generate a valid METAR string.

    Args:
        icao: ICAO airport code (e.g., "KDFW").
        conditions: Weather condition parameters. Keys:
            wind_dir, wind_speed, wind_gust, visibility_sm, ceiling_ft,
            ceiling_type, temperature_c, dewpoint_c, altimeter_inhg, wx
        preset: Preset name (low_vis_approach, gusty_crosswind, clear_day,
                winter_ops, thunderstorm). Overridden by explicit conditions.
        timestamp: Observation time. Defaults to current UTC.

    Returns:
        Valid METAR string.
    """
    # Start with preset, then override with explicit conditions
    if preset and preset in PRESETS:
        params = {**PRESETS[preset]}
    else:
        params = {}

    if conditions:
        params.update(conditions)

    # Defaults for any missing parameters
    params.setdefault("wind_dir", random.randint(0, 35) * 10)
    params.setdefault("wind_speed", random.randint(3, 15))
    params.setdefault("wind_gust", None)
    params.setdefault("visibility_sm", 10)
    params.setdefault("ceiling_ft", None)
    params.setdefault("ceiling_type", "CLR")
    params.setdefault("temperature_c", random.randint(5, 30))
    params.setdefault("dewpoint_c", params["temperature_c"] - random.randint(2, 10))
    params.setdefault("altimeter_inhg", round(29.80 + random.random() * 0.50, 2))
    params.setdefault("wx", None)

    if timestamp is None:
        timestamp = datetime.utcnow()

    parts = [icao]

    # Date/time group: DDHHMMz
    parts.append(f"{timestamp.day:02d}{timestamp.hour:02d}{timestamp.minute:02d}Z")

    # Wind: dddssKT or dddssGggKT
    wind_dir = params["wind_dir"]
    wind_speed = params["wind_speed"]
    wind_gust = params["wind_gust"]
    if wind_gust:
        parts.append(f"{wind_dir:03d}{wind_speed:02d}G{wind_gust:02d}KT")
    else:
        parts.append(f"{wind_dir:03d}{wind_speed:02d}KT")

    # Visibility
    vis = params["visibility_sm"]
    if vis >= 10:
        parts.append("10SM")
    elif vis >= 1:
        parts.append(f"{int(vis)}SM")
    elif vis >= 0.5:
        parts.append("1/2SM")
    elif vis >= 0.25:
        parts.append("1/4SM")
    else:
        parts.append("M1/4SM")

    # Weather phenomena
    if params["wx"]:
        parts.append(params["wx"])

    # Cloud layers
    ceiling_type = params["ceiling_type"]
    ceiling_ft = params["ceiling_ft"]
    if ceiling_type == "CLR":
        parts.append("CLR")
    elif ceiling_ft is not None:
        # Round to nearest hundred
        ceiling_hundreds = round(ceiling_ft / 100)
        parts.append(f"{ceiling_type}{ceiling_hundreds:03d}")
    else:
        parts.append("SKC")

    # Temperature/dewpoint
    temp = params["temperature_c"]
    dewp = params["dewpoint_c"]
    temp_str = f"M{abs(temp):02d}" if temp < 0 else f"{temp:02d}"
    dewp_str = f"M{abs(dewp):02d}" if dewp < 0 else f"{dewp:02d}"
    parts.append(f"{temp_str}/{dewp_str}")

    # Altimeter
    alt = params["altimeter_inhg"]
    alt_hundredths = round(alt * 100)
    parts.append(f"A{alt_hundredths:04d}")

    return " ".join(parts)
