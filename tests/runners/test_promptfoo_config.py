"""Tests for runners/promptfoo_config.py — Promptfoo YAML config generation."""

import json

import pytest
import yaml

from runners.promptfoo_config import (
    generate_config,
    generate_grounding_config,
    write_config,
    _build_assertions,
)


# ---------------------------------------------------------------------------
# generate_config structure
# ---------------------------------------------------------------------------

class TestGenerateConfig:
    def test_produces_valid_structure(self):
        config = generate_config(
            eval_category="grounding",
            dataset_path="/nonexistent/path.jsonl",  # won't be read if file missing
            model_config={
                "provider": "anthropic",
                "model_id": "claude-sonnet-4-20250514",
                "max_tokens": 4096,
            },
            grader_configs=[],
        )

        # Must have top-level keys
        assert "providers" in config
        assert "prompts" in config
        assert "tests" in config
        assert "defaultTest" in config
        assert "description" in config
        assert "grounding" in config["description"]

        # Providers should be a list with at least one entry
        assert isinstance(config["providers"], list)
        assert len(config["providers"]) >= 1

        # Prompts should be a list with at least one string
        assert isinstance(config["prompts"], list)

    def test_serializes_to_valid_yaml(self, tmp_path):
        config = generate_config(
            eval_category="grounding",
            dataset_path="/nonexistent.jsonl",
            model_config={"provider": "anthropic", "model_id": "claude-sonnet-4-20250514"},
        )
        out_path = tmp_path / "config.yaml"
        write_config(config, out_path)

        assert out_path.exists()
        loaded = yaml.safe_load(out_path.read_text())
        assert loaded["description"] == config["description"]
        assert "providers" in loaded

    def test_with_real_dataset(self, tmp_path):
        """Config with a real dataset file should produce test cases."""
        dataset = tmp_path / "cases.jsonl"
        dataset.write_text(
            json.dumps({
                "case_id": "c1",
                "context": "Go-around at KDFW",
                "query": "What happened?",
                "expected_facts": ["KDFW", "go-around"],
                "negative_facts": ["KJFK"],
            }) + "\n"
        )

        config = generate_config(
            eval_category="grounding",
            dataset_path=str(dataset),
            model_config={"provider": "anthropic", "model_id": "claude-sonnet-4-20250514"},
        )
        assert len(config["tests"]) == 1
        test_case = config["tests"][0]
        assert test_case["vars"]["context"] == "Go-around at KDFW"
        assert test_case["description"] == "c1"


# ---------------------------------------------------------------------------
# Grader-to-assertion mapping
# ---------------------------------------------------------------------------

class TestGraderToAssertionMapping:
    def test_contains_grader_maps_to_icontains(self, tmp_path):
        dataset = tmp_path / "data.jsonl"
        dataset.write_text(
            json.dumps({"expected_facts": ["KDFW"], "negative_facts": []}) + "\n"
        )

        config = generate_config(
            eval_category="grounding",
            dataset_path=str(dataset),
            model_config={"provider": "anthropic", "model_id": "test"},
        )
        assertions = config["tests"][0]["assert"]
        types = [a["type"] for a in assertions]
        assert "icontains" in types

    def test_not_contains_maps_to_not_icontains(self, tmp_path):
        dataset = tmp_path / "data.jsonl"
        dataset.write_text(
            json.dumps({"expected_facts": [], "negative_facts": ["KJFK"]}) + "\n"
        )

        config = generate_config(
            eval_category="grounding",
            dataset_path=str(dataset),
            model_config={"provider": "anthropic", "model_id": "test"},
        )
        assertions = config["tests"][0]["assert"]
        types = [a["type"] for a in assertions]
        assert "not-icontains" in types

    def test_llm_judge_grader_maps_to_llm_rubric(self):
        case = {"expected_facts": [], "negative_facts": []}
        grader_configs = [
            {"type": "llm_judge", "rubric": "Check correctness", "threshold": 0.4},
        ]
        assertions = _build_assertions(case, "grounding", grader_configs)
        types = [a["type"] for a in assertions]
        assert "llm-rubric" in types

    def test_regex_grader_maps_to_regex(self):
        case = {"expected_facts": [], "negative_facts": []}
        grader_configs = [
            {"type": "regex", "pattern": r"FL\d{3}"},
        ]
        assertions = _build_assertions(case, "grounding", grader_configs)
        types = [a["type"] for a in assertions]
        assert "regex" in types

    def test_numeric_tolerance_maps_to_javascript(self):
        case = {"expected_facts": [], "negative_facts": []}
        grader_configs = [
            {"type": "numeric_tolerance", "value": 15000, "tolerance": 500},
        ]
        assertions = _build_assertions(case, "grounding", grader_configs)
        types = [a["type"] for a in assertions]
        assert "javascript" in types


# ---------------------------------------------------------------------------
# generate_grounding_config
# ---------------------------------------------------------------------------

class TestGroundingConfig:
    def test_includes_weighted_sub_rubrics(self, tmp_path):
        dataset = tmp_path / "data.jsonl"
        dataset.write_text(
            json.dumps({
                "context": "Event at KDFW",
                "query": "Analyze",
                "expected_facts": ["KDFW"],
                "negative_facts": ["KJFK"],
            }) + "\n"
        )

        config = generate_grounding_config(
            dataset_path=str(dataset),
            model_config={"provider": "anthropic", "model_id": "claude-sonnet-4-20250514"},
        )

        # Should have 4 llm-rubric assertions (the sub-rubrics) + icontains + not-icontains
        assertions = config["tests"][0]["assert"]
        llm_rubric_assertions = [a for a in assertions if a["type"] == "llm-rubric"]
        assert len(llm_rubric_assertions) == 4

        # Should also have anti-hallucination check
        not_icontains = [a for a in assertions if a["type"] == "not-icontains"]
        assert len(not_icontains) >= 1

    def test_grounding_prompt_template(self, tmp_path):
        dataset = tmp_path / "data.jsonl"
        dataset.write_text(
            json.dumps({"context": "test", "query": "test"}) + "\n"
        )
        config = generate_grounding_config(
            dataset_path=str(dataset),
            model_config={"provider": "anthropic", "model_id": "test"},
        )
        prompt = config["prompts"][0]
        assert "aviation safety analyst" in prompt.lower()
        assert "{{context}}" in prompt
        assert "{{query}}" in prompt
