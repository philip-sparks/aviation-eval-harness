"""Synthetic ADS-B track generator.

Produces synthetic ADS-B track points using physics-based flight profiles
at real airports. Supports approach, departure, taxi, and go-around profiles.
"""

from __future__ import annotations

import math
import random
import time
from typing import Any

from evals.aviation_domain import AIRPORTS


def generate_track(
    airport_icao: str,
    runway: str | None = None,
    profile_type: str = "approach",
    aircraft_type: str = "B738",
    n_points: int = 60,
) -> list[dict]:
    """Generate synthetic ADS-B track points.

    Args:
        airport_icao: ICAO airport code.
        runway: Runway designator (e.g., "13L"). If None, picks from airport.
        profile_type: One of "approach", "departure", "taxi", "go_around".
        aircraft_type: ICAO type designator (e.g., "B738", "A320").
        n_points: Number of track points to generate.

    Returns:
        List of track point dicts with:
            timestamp_ms, latitude, longitude, altitude_ft,
            heading, ground_speed_kt, vertical_rate_fpm
    """
    airport = AIRPORTS.get(airport_icao)
    if airport is None:
        raise ValueError(f"Unknown airport: {airport_icao}")

    if runway is None:
        runway = airport.runways[0].split("/")[0] if airport.runways else "01"

    # Determine runway heading from designator
    rwy_heading = _runway_heading(runway)

    generators = {
        "approach": _generate_approach,
        "departure": _generate_departure,
        "taxi": _generate_taxi,
        "go_around": _generate_go_around,
    }

    generator = generators.get(profile_type)
    if generator is None:
        raise ValueError(f"Unknown profile type: {profile_type}. Use: {list(generators.keys())}")

    return generator(airport, rwy_heading, aircraft_type, n_points)


def _runway_heading(runway: str) -> float:
    """Extract heading from runway designator."""
    # Strip L/R/C suffix
    num_str = runway.rstrip("LRC")
    return int(num_str) * 10.0


def _generate_approach(airport, rwy_heading: float, aircraft_type: str, n_points: int) -> list[dict]:
    """Generate approach profile: 3-degree glideslope from ~10nm final."""
    points = []
    base_time = int(time.time() * 1000)

    # Start ~10nm from airport on extended centerline
    start_distance_nm = 10.0
    start_alt = airport.elevation_ft + 3000  # ~3000 ft AGL at 10nm on 3-deg glideslope

    # Performance by aircraft type
    approach_speed = _approach_speed(aircraft_type)

    for i in range(n_points):
        progress = i / max(n_points - 1, 1)

        # Distance from airport decreases linearly
        distance_nm = start_distance_nm * (1 - progress)

        # Altitude decreases along 3-degree glideslope
        alt_agl = distance_nm * 318  # ~318 ft/nm on 3-degree glideslope
        altitude = airport.elevation_ft + max(alt_agl, 0)

        # Speed decreases approaching threshold
        speed = approach_speed + (approach_speed * 0.3) * (1 - progress)
        speed = max(speed * (1 - 0.15 * progress), approach_speed * 0.9)

        # Vertical rate
        vrate = -700 if distance_nm > 0.5 else -300

        # Position: project from airport along reciprocal heading
        bearing_rad = math.radians((rwy_heading + 180) % 360)
        lat, lon = _project_position(
            airport.lat, airport.lon, bearing_rad, distance_nm
        )

        # Add small noise
        lat += random.gauss(0, 0.0001)
        lon += random.gauss(0, 0.0001)

        points.append({
            "timestamp_ms": base_time + i * 5000,  # 5-second intervals
            "latitude": round(lat, 6),
            "longitude": round(lon, 6),
            "altitude_ft": round(altitude),
            "heading": round(rwy_heading + random.gauss(0, 1), 1),
            "ground_speed_kt": round(speed),
            "vertical_rate_fpm": round(vrate + random.gauss(0, 30)),
        })

    return points


def _generate_departure(airport, rwy_heading: float, aircraft_type: str, n_points: int) -> list[dict]:
    """Generate departure profile: takeoff roll + standard climb."""
    points = []
    base_time = int(time.time() * 1000)

    climb_rate = 2000 if "B7" in aircraft_type else 1800
    rotate_speed = 145 if "B7" in aircraft_type else 135

    for i in range(n_points):
        progress = i / max(n_points - 1, 1)

        if progress < 0.1:
            # Ground roll
            altitude = airport.elevation_ft
            speed = rotate_speed * (progress / 0.1)
            vrate = 0
        else:
            # Climb
            climb_progress = (progress - 0.1) / 0.9
            altitude = airport.elevation_ft + climb_rate * climb_progress * 5
            speed = rotate_speed + 30 * climb_progress
            vrate = climb_rate

        distance_nm = progress * 15  # ~15nm departure track
        bearing_rad = math.radians(rwy_heading)
        lat, lon = _project_position(airport.lat, airport.lon, bearing_rad, distance_nm)

        points.append({
            "timestamp_ms": base_time + i * 5000,
            "latitude": round(lat + random.gauss(0, 0.0001), 6),
            "longitude": round(lon + random.gauss(0, 0.0001), 6),
            "altitude_ft": round(altitude),
            "heading": round(rwy_heading + random.gauss(0, 2), 1),
            "ground_speed_kt": round(speed),
            "vertical_rate_fpm": round(vrate + random.gauss(0, 50)),
        })

    return points


def _generate_taxi(airport, rwy_heading: float, aircraft_type: str, n_points: int) -> list[dict]:
    """Generate taxi profile: ground movement at 15-25 kt."""
    points = []
    base_time = int(time.time() * 1000)

    # Random taxi path with turns
    heading = rwy_heading
    lat, lon = airport.lat, airport.lon

    for i in range(n_points):
        speed = random.randint(5, 25)

        # Occasional turns
        if random.random() < 0.15:
            heading = (heading + random.choice([-90, -45, 45, 90])) % 360

        # Move position
        distance_nm = speed / 3600 * 5  # 5-second intervals
        bearing_rad = math.radians(heading)
        lat, lon = _project_position(lat, lon, bearing_rad, distance_nm)

        points.append({
            "timestamp_ms": base_time + i * 5000,
            "latitude": round(lat, 6),
            "longitude": round(lon, 6),
            "altitude_ft": airport.elevation_ft,
            "heading": round(heading, 1),
            "ground_speed_kt": speed,
            "vertical_rate_fpm": 0,
        })

    return points


def _generate_go_around(airport, rwy_heading: float, aircraft_type: str, n_points: int) -> list[dict]:
    """Generate go-around profile: approach followed by climb-out."""
    points = []

    # First half: approach to low altitude
    approach_points = n_points // 2
    approach = _generate_approach(airport, rwy_heading, aircraft_type, approach_points)

    # Modify last few approach points to be very low
    for pt in approach[-3:]:
        pt["altitude_ft"] = airport.elevation_ft + random.randint(100, 300)
        pt["vertical_rate_fpm"] = -200

    points.extend(approach)

    # Second half: go-around climb
    base_time = approach[-1]["timestamp_ms"] + 5000
    last_lat = approach[-1]["latitude"]
    last_lon = approach[-1]["longitude"]
    climb_rate = 2500

    for i in range(n_points - approach_points):
        progress = i / max(n_points - approach_points - 1, 1)

        altitude = airport.elevation_ft + 200 + climb_rate * progress * 3
        speed = _approach_speed(aircraft_type) + 20 * progress

        distance_nm = progress * 5
        bearing_rad = math.radians(rwy_heading)
        lat, lon = _project_position(last_lat, last_lon, bearing_rad, distance_nm)

        points.append({
            "timestamp_ms": base_time + i * 5000,
            "latitude": round(lat + random.gauss(0, 0.0001), 6),
            "longitude": round(lon + random.gauss(0, 0.0001), 6),
            "altitude_ft": round(altitude),
            "heading": round(rwy_heading + random.gauss(0, 2), 1),
            "ground_speed_kt": round(speed),
            "vertical_rate_fpm": round(climb_rate + random.gauss(0, 100)),
        })

    return points


def _approach_speed(aircraft_type: str) -> int:
    """Get typical approach speed for aircraft type."""
    speeds = {
        "B738": 140, "B737": 137, "B739": 142,
        "B752": 140, "B753": 145, "B763": 140, "B772": 145, "B77W": 148,
        "A319": 131, "A320": 137, "A321": 140, "A332": 140, "A333": 142,
        "A388": 150, "E175": 130, "CRJ9": 135, "CRJ7": 132,
    }
    return speeds.get(aircraft_type, 140)


def _project_position(lat: float, lon: float, bearing_rad: float, distance_nm: float) -> tuple[float, float]:
    """Project a position given bearing and distance."""
    # Approximate: 1 degree lat ≈ 60 nm, 1 degree lon ≈ 60 * cos(lat) nm
    d_lat = distance_nm * math.cos(bearing_rad) / 60.0
    d_lon = distance_nm * math.sin(bearing_rad) / (60.0 * math.cos(math.radians(lat)))
    return lat + d_lat, lon + d_lon
