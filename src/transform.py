"""Pure data shaping helpers for the municipal sensor ingestion prototype."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Iterable, Iterator
from zoneinfo import ZoneInfo

from src.quality import DEFAULT_RULES, assess_document

DATASET_NAME = "UCI Beijing Multi-Site Air Quality"
SOURCE_TZ = ZoneInfo("Asia/Shanghai")
NUMERIC_COLUMNS = {
    "PM2.5": "pm25", "PM10": "pm10", "SO2": "so2", "NO2": "no2", "CO": "co",
    "O3": "o3", "TEMP": "temperature_c", "PRES": "pressure_hpa", "DEWP": "dew_point_c",
    "RAIN": "rain_mm", "WSPM": "wind_speed_m_s",
}
STRING_COLUMNS = {"wd": "wind_direction"}


def _number(value: str | None) -> float | None:
    if value is None or value.strip() in {"", "NA", "NaN", "nan"}:
        return None
    try:
        return float(value)
    except ValueError:
        return None


def normalize_row(
    row: dict[str, str],
    quality_rules: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Convert one source CSV row into a queryable, schema-tolerant document."""
    station = (row.get("station") or "").strip()
    if not station:
        raise ValueError("row has no station")

    timestamp = datetime(
        int(row["year"]), int(row["month"]), int(row["day"]), int(row["hour"]),
        tzinfo=SOURCE_TZ,
    )
    measurements: dict[str, Any] = {}
    for source_name, target_name in NUMERIC_COLUMNS.items():
        value = _number(row.get(source_name))
        if value is not None:
            measurements[target_name] = value
    for source_name, target_name in STRING_COLUMNS.items():
        value = (row.get(source_name) or "").strip()
        if value and value not in {"NA", "NaN", "nan"}:
            measurements[target_name] = value

    # Preserve unrecognised fields so a future sensor metric is not silently lost.
    known = set(NUMERIC_COLUMNS) | set(STRING_COLUMNS) | {
        "No", "year", "month", "day", "hour", "station"
    }
    for source_name, raw_value in row.items():
        if source_name not in known and raw_value and raw_value.strip() not in {"NA", "NaN", "nan"}:
            value = _number(raw_value)
            measurements[source_name.strip().lower()] = value if value is not None else raw_value.strip()

    timestamp_text = timestamp.isoformat(timespec="seconds")
    document = {
        "_id": f"{station}|{timestamp_text}",
        "station": station,
        "timestamp": timestamp,
        "source_timezone": "Asia/Shanghai",
        "measurements": measurements,
        "source": DATASET_NAME,
        "source_record_number": (row.get("No") or "").strip() or None,
        "ingested_at": datetime.now(timezone.utc),
    }
    return assess_document(document, quality_rules or DEFAULT_RULES)


def batched(items: Iterable[dict[str, Any]], size: int) -> Iterator[list[dict[str, Any]]]:
    if size < 1:
        raise ValueError("batch size must be positive")
    batch: list[dict[str, Any]] = []
    for item in items:
        batch.append(item)
        if len(batch) == size:
            yield batch
            batch = []
    if batch:
        yield batch
