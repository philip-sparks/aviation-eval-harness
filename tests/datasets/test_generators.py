"""Tests for datasets/generators/ — METAR, track, and scenario generators."""

import re

import pytest

from datasets.generators.generate_metar import generate_metar, PRESETS
from datasets.generators.generate_tracks import generate_track
from datasets.generators.generate_scenarios import generate_scenario


# ---------------------------------------------------------------------------
# METAR generator
# ---------------------------------------------------------------------------

class TestGenerateMeatar:
    def test_starts_with_icao(self):
        metar = generate_metar("KDFW")
        assert metar.startswith("KDFW")

    def test_contains_wind(self):
        metar = generate_metar("KORD", conditions={"wind_dir": 270, "wind_speed": 15})
        assert "27015KT" in metar

    def test_contains_wind_with_gust(self):
        metar = generate_metar("KORD", conditions={"wind_dir": 270, "wind_speed": 15, "wind_gust": 25})
        assert "27015G25KT" in metar

    def test_contains_visibility(self):
        metar = generate_metar("KLAX", conditions={"visibility_sm": 10})
        assert "10SM" in metar

    def test_contains_temperature(self):
        metar = generate_metar("KSFO", conditions={"temperature_c": 20, "dewpoint_c": 12})
        assert "20/12" in metar

    def test_negative_temperature(self):
        metar = generate_metar("KDEN", conditions={"temperature_c": -5, "dewpoint_c": -8})
        assert "M05/M08" in metar

    def test_contains_altimeter(self):
        metar = generate_metar("KATL", conditions={"altimeter_inhg": 29.92})
        assert "A2992" in metar

    def test_valid_format_structure(self):
        """A complete METAR should have the core components."""
        metar = generate_metar("KDFW", conditions={
            "wind_dir": 180,
            "wind_speed": 10,
            "visibility_sm": 10,
            "temperature_c": 25,
            "dewpoint_c": 15,
            "altimeter_inhg": 30.00,
            "ceiling_type": "CLR",
        })
        parts = metar.split()
        assert parts[0] == "KDFW"
        # Second part should be datetime group ending in Z
        assert parts[1].endswith("Z")
        # Should have KT somewhere (wind)
        assert any("KT" in p for p in parts)
        # Should have SM somewhere (visibility)
        assert any("SM" in p for p in parts)
        # Should have altimeter A-group
        assert any(p.startswith("A") and len(p) == 5 for p in parts)


# ---------------------------------------------------------------------------
# Preset METAR conditions
# ---------------------------------------------------------------------------

class TestMETARPresets:
    def test_low_vis_approach_visibility(self):
        """low_vis_approach preset must have visibility < 1SM."""
        preset = PRESETS["low_vis_approach"]
        assert preset["visibility_sm"] < 1.0

        metar = generate_metar("KSFO", preset="low_vis_approach")
        # Should contain fractional visibility (1/2SM or 1/4SM), not 10SM
        assert "10SM" not in metar
        # Should contain fog
        assert "FG" in metar

    def test_gusty_crosswind_has_gust(self):
        preset = PRESETS["gusty_crosswind"]
        assert preset["wind_gust"] is not None
        assert preset["wind_gust"] > preset["wind_speed"]

        metar = generate_metar("KDFW", preset="gusty_crosswind")
        assert "G" in metar  # Gust indicator

    def test_clear_day_good_visibility(self):
        preset = PRESETS["clear_day"]
        assert preset["visibility_sm"] >= 10
        assert preset["ceiling_type"] == "CLR"

    def test_winter_ops_has_snow(self):
        metar = generate_metar("KORD", preset="winter_ops")
        assert "SN" in metar

    def test_thunderstorm_has_tsra(self):
        metar = generate_metar("KATL", preset="thunderstorm")
        assert "TSRA" in metar


# ---------------------------------------------------------------------------
# Track generator
# ---------------------------------------------------------------------------

class TestGenerateTrack:
    def test_produces_track_points(self):
        track = generate_track("KDFW", runway="13L", profile_type="approach", n_points=20)
        assert len(track) == 20

    def test_track_point_fields(self):
        track = generate_track("KATL", profile_type="approach", n_points=5)
        point = track[0]
        assert "timestamp_ms" in point
        assert "latitude" in point
        assert "longitude" in point
        assert "altitude_ft" in point
        assert "heading" in point
        assert "ground_speed_kt" in point
        assert "vertical_rate_fpm" in point

    def test_valid_lat_lon_ranges(self):
        track = generate_track("KJFK", profile_type="approach", n_points=30)
        for pt in track:
            assert -90 <= pt["latitude"] <= 90
            assert -180 <= pt["longitude"] <= 180

    def test_valid_altitude_range(self):
        track = generate_track("KDFW", profile_type="approach", n_points=30)
        for pt in track:
            assert pt["altitude_ft"] >= 0
            assert pt["altitude_ft"] <= 60000  # reasonable upper bound

    def test_approach_profile_descends(self):
        """Approach track should generally have decreasing altitude."""
        track = generate_track("KSFO", profile_type="approach", n_points=30)
        # First point should be higher than last point
        assert track[0]["altitude_ft"] > track[-1]["altitude_ft"]

    def test_departure_profile_ascends(self):
        """Departure track should generally have increasing altitude."""
        track = generate_track("KORD", profile_type="departure", n_points=30)
        assert track[-1]["altitude_ft"] > track[0]["altitude_ft"]

    def test_taxi_stays_on_ground(self):
        """Taxi track altitude should stay at airport elevation."""
        track = generate_track("KDFW", profile_type="taxi", n_points=10)
        for pt in track:
            # KDFW elevation is 607 ft; taxi should be at that elevation
            assert pt["altitude_ft"] == 607

    def test_unknown_airport_raises(self):
        with pytest.raises(ValueError, match="Unknown airport"):
            generate_track("XXXX", profile_type="approach")

    def test_unknown_profile_raises(self):
        with pytest.raises(ValueError, match="Unknown profile type"):
            generate_track("KDFW", profile_type="barrel_roll")


# ---------------------------------------------------------------------------
# Scenario generator
# ---------------------------------------------------------------------------

class TestGenerateScenario:
    def test_produces_dict_with_required_fields(self):
        scenario = generate_scenario("go_around", "KDFW", seed=42)

        assert isinstance(scenario, dict)
        assert "case_id" in scenario
        assert "source_type" in scenario
        assert scenario["source_type"] == "synthetic"
        assert "event_type" in scenario
        assert scenario["event_type"] == "go_around"
        assert "airport_icao" in scenario
        assert scenario["airport_icao"] == "KDFW"
        assert "context" in scenario
        assert "query" in scenario
        assert "expected_facts" in scenario
        assert "negative_facts" in scenario
        assert "difficulty" in scenario
        assert "metadata" in scenario

    def test_metadata_fields(self):
        scenario = generate_scenario("tcas_ra", "KJFK", seed=42)
        meta = scenario["metadata"]
        assert "aircraft_type" in meta
        assert "callsign" in meta
        assert "runway" in meta
        assert "metar" in meta
        assert "track_points" in meta
        assert "phase_of_flight" in meta

    def test_expected_facts_include_airport(self):
        scenario = generate_scenario("go_around", "KATL", seed=42)
        assert "KATL" in scenario["expected_facts"]

    def test_negative_facts_exclude_correct_airport(self):
        scenario = generate_scenario("go_around", "KDFW", seed=42)
        assert "KDFW" not in scenario["negative_facts"]

    def test_unknown_airport_raises(self):
        with pytest.raises(ValueError, match="Unknown airport"):
            generate_scenario("go_around", "XXXX", seed=42)

    def test_case_id_format(self):
        scenario = generate_scenario("go_around", "KDFW", seed=42)
        assert scenario["case_id"].startswith("SYN-")
        assert "MAR" in scenario["case_id"]  # go_around maps to MAR

    def test_reproducibility_with_seed(self):
        s1 = generate_scenario("tcas_ra", "KORD", seed=123)
        s2 = generate_scenario("tcas_ra", "KORD", seed=123)
        assert s1["case_id"] == s2["case_id"]
        assert s1["metadata"]["aircraft_type"] == s2["metadata"]["aircraft_type"]
        assert s1["metadata"]["callsign"] == s2["metadata"]["callsign"]
