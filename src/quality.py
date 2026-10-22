"""Data-quality rules for municipal air-quality observations.

The numerical ranges are screening limits, not medical or regulatory thresholds.
Values outside them are retained and flagged so an analyst can investigate them.
"""

from __future__ import annotations

import json
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


DEFAULT_RULES: dict[str, Any] = {
    "version": "1.0",
    "required_pollutants": ["pm25", "pm10", "so2", "no2", "co", "o3"],
    "plausible_ranges": {
        "pm25": [0, 1000],
        "pm10": [0, 1500],
        "so2": [0, 1000],
        "no2": [0, 1000],
        "co": [0, 20000],
        "o3": [0, 1000],
        "temperature_c": [-50, 60],
        "pressure_hpa": [850, 1100],
        "dew_point_c": [-70, 60],
        "rain_mm": [0, 500],
        "wind_speed_m_s": [0, 75],
    },
}


def load_quality_rules(path: str | Path | None = None) -> dict[str, Any]:
    """Load configurable screening rules or return an isolated default copy."""
    if path is None:
        return deepcopy(DEFAULT_RULES)
    with Path(path).open(encoding="utf-8") as stream:
        rules = json.load(stream)
    if not isinstance(rules.get("required_pollutants"), list):
        raise ValueError("quality rules require a required_pollutants list")
    if not isinstance(rules.get("plausible_ranges"), dict):
        raise ValueError("quality rules require a plausible_ranges object")
    return rules


def assess_document(document: dict[str, Any], rules: dict[str, Any]) -> dict[str, Any]:
    """Attach transparent quality flags while retaining the source observation."""
    measurements = document["measurements"]
    required = rules["required_pollutants"]
    missing = [name for name in required if name not in measurements]
    out_of_range: list[dict[str, Any]] = []

    for name, limits in rules["plausible_ranges"].items():
        if name not in measurements:
            continue
        lower, upper = limits
        value = measurements[name]
        if isinstance(value, (int, float)) and not lower <= value <= upper:
            out_of_range.append({"field": name, "value": value, "range": [lower, upper]})

    flags: list[str] = []
    if missing:
        flags.append("missing_pollutants")
    if out_of_range:
        flags.append("outside_screening_range")

    document["quality"] = {
        "status": "warning" if flags else "accepted",
        "flags": flags,
        "missing_pollutants": missing,
        "outside_screening_range": out_of_range,
        "pollutant_completeness": round((len(required) - len(missing)) / len(required), 4),
        "rules_version": str(rules.get("version", "unknown")),
        "checked_at": datetime.now(timezone.utc),
    }
    return document
