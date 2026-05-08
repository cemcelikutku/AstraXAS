from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml


class ScenarioError(ValueError):
    """Raised when a beamtime replay scenario is missing or malformed."""


def _require_mapping(data: Any) -> dict:
    if not isinstance(data, dict):
        raise ScenarioError("Scenario file must contain a YAML mapping.")
    return data


def _require_number(data: dict, key: str) -> float:
    value = data.get(key)
    if value is None:
        raise ScenarioError(f"Scenario is missing required key: {key}")
    try:
        value = float(value)
    except (TypeError, ValueError):
        raise ScenarioError(f"Scenario key {key!r} must be a number.") from None
    if value < 0:
        raise ScenarioError(f"Scenario key {key!r} must be non-negative.")
    return value


def load_scenario(path: str | Path) -> dict:
    path = Path(path).expanduser()
    try:
        with path.open("r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
    except OSError as exc:
        raise ScenarioError(f"Could not read scenario file {path}: {exc}") from exc

    data = _require_mapping(data)
    for key in ("source_dir", "target_dir", "interval_s"):
        if key not in data:
            raise ScenarioError(f"Scenario is missing required key: {key}")

    scenario = {
        "source_dir": Path(str(data["source_dir"])).expanduser(),
        "target_dir": Path(str(data["target_dir"])).expanduser(),
        "interval_s": _require_number(data, "interval_s"),
        "jitter_s": float(data.get("jitter_s", 0.0) or 0.0),
        "shuffle": bool(data.get("shuffle", False)),
        "seed": data.get("seed", None),
        "inject": data.get("inject", []) or [],
    }
    if scenario["jitter_s"] < 0:
        raise ScenarioError("Scenario key 'jitter_s' must be non-negative.")
    if scenario["seed"] is not None:
        try:
            scenario["seed"] = int(scenario["seed"])
        except (TypeError, ValueError):
            raise ScenarioError("Scenario key 'seed' must be an integer or null.") from None
    if not isinstance(scenario["inject"], list):
        raise ScenarioError("Scenario key 'inject' must be a list.")
    for idx, item in enumerate(scenario["inject"], start=1):
        if not isinstance(item, dict):
            raise ScenarioError(f"Inject entry {idx} must be a mapping.")
        if "scan_index" not in item or "type" not in item:
            raise ScenarioError(f"Inject entry {idx} must include scan_index and type.")
        try:
            scan_index = int(item["scan_index"])
        except (TypeError, ValueError):
            raise ScenarioError(f"Inject entry {idx} scan_index must be an integer.") from None
        if scan_index < 1:
            raise ScenarioError(f"Inject entry {idx} scan_index must be 1 or greater.")
        item["scan_index"] = scan_index
        item["type"] = str(item["type"])
    return scenario
