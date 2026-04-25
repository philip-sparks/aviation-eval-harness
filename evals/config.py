"""Configuration loading utilities for the evaluation harness."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import yaml


def load_config(path: str | Path) -> dict[str, Any]:
    """Load a YAML or JSON config file.

    Resolves model adapter settings, dataset paths, and grader selections.
    """
    path = Path(path)
    text = path.read_text()

    if path.suffix in (".yaml", ".yml"):
        config = yaml.safe_load(text)
    elif path.suffix == ".json":
        config = json.loads(text)
    else:
        # Try YAML first, fall back to JSON
        try:
            config = yaml.safe_load(text)
        except yaml.YAMLError:
            config = json.loads(text)

    return _resolve_config(config, path.parent)


def _resolve_config(config: dict, base_dir: Path) -> dict:
    """Resolve relative paths and defaults in the config."""
    # Resolve dataset path relative to config file
    if "dataset" in config and not Path(config["dataset"]).is_absolute():
        config["dataset"] = str(base_dir / config["dataset"])

    # Set model defaults
    model = config.get("model", {})
    model.setdefault("provider", "anthropic")
    model.setdefault("model_id", "claude-sonnet-4-20250514")
    model.setdefault("max_tokens", 4096)
    model.setdefault("temperature", 0.0)
    config["model"] = model

    # Set eval defaults
    config.setdefault("eval", {})
    config.setdefault("graders", [])
    config.setdefault("cache", True)
    config.setdefault("concurrency", 5)

    return config


def save_config(config: dict, path: str | Path) -> None:
    """Save config as YAML."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(config, default_flow_style=False, sort_keys=False))
