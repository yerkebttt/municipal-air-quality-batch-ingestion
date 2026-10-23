"""Stakeholder-oriented MongoDB queries and repeatable latency checks."""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from time import perf_counter
from typing import Any, Callable

from pymongo import MongoClient
from pymongo.collection import Collection
from pymongo.database import Database


DEFAULT_STATION = "Aotizhongxin"
DEFAULT_FROM = datetime(2017, 1, 1, tzinfo=timezone.utc)
DEFAULT_TO = datetime(2017, 2, 1, tzinfo=timezone.utc)


def daily_trend_pipeline(
    station: str,
    pollutant: str,
    start: datetime,
    end: datetime,
) -> list[dict[str, Any]]:
    field = f"$measurements.{pollutant}"
    return [
        {"$match": {
            "station": station,
            "timestamp": {"$gte": start, "$lt": end},
            f"measurements.{pollutant}": {"$exists": True},
        }},
        {"$group": {
            "_id": {"$dateToString": {"format": "%Y-%m-%d", "date": "$timestamp"}},
            "average": {"$avg": field},
            "minimum": {"$min": field},
            "maximum": {"$max": field},
            "observations": {"$sum": 1},
        }},
        {"$sort": {"_id": 1}},
    ]


def compare_stations_pipeline(
    pollutant: str,
    start: datetime,
    end: datetime,
) -> list[dict[str, Any]]:
    field = f"$measurements.{pollutant}"
    return [
        {"$match": {
            "timestamp": {"$gte": start, "$lt": end},
            f"measurements.{pollutant}": {"$exists": True},
        }},
        {"$group": {
            "_id": "$station",
            "average": {"$avg": field},
            "minimum": {"$min": field},
            "maximum": {"$max": field},
            "observations": {"$sum": 1},
        }},
        {"$sort": {"average": -1}},
    ]


def timed_query(name: str, sla_ms: int, operation: Callable[[], list[Any]]) -> dict[str, Any]:
    started = perf_counter()
    rows = operation()
    elapsed_ms = round((perf_counter() - started) * 1000, 3)
    return {
        "query": name,
        "rows_returned": len(rows),
        "elapsed_ms": elapsed_ms,
        "sla_ms": sla_ms,
        "meets_sla": elapsed_ms <= sla_ms,
        "results": rows,
    }


def latest_readings(collection: Collection, station: str, limit: int = 24) -> list[dict[str, Any]]:
    projection = {"_id": 0, "station": 1, "timestamp": 1, "measurements": 1, "quality": 1}
    return list(collection.find({"station": station}, projection).sort("timestamp", -1).limit(limit))


def daily_trend(
    collection: Collection,
    station: str,
    pollutant: str,
    start: datetime,
    end: datetime,
    max_time_ms: int,
) -> list[dict[str, Any]]:
    return list(collection.aggregate(
        daily_trend_pipeline(station, pollutant, start, end), maxTimeMS=max_time_ms
    ))


def compare_stations(
    collection: Collection,
    pollutant: str,
    start: datetime,
    end: datetime,
    max_time_ms: int,
) -> list[dict[str, Any]]:
    return list(collection.aggregate(
        compare_stations_pipeline(pollutant, start, end), maxTimeMS=max_time_ms
    ))


def quality_summary(collection: Collection, max_time_ms: int) -> list[dict[str, Any]]:
    return list(collection.aggregate([
        {"$group": {
            "_id": "$quality.status",
            "records": {"$sum": 1},
            "average_pollutant_completeness": {"$avg": "$quality.pollutant_completeness"},
        }},
        {"$sort": {"_id": 1}},
    ], maxTimeMS=max_time_ms))


def alert_candidates(
    collection: Collection,
    thresholds: dict[str, Any],
    start: datetime,
    end: datetime,
    max_time_ms: int,
) -> list[dict[str, Any]]:
    conditions = [
        {f"measurements.{name}": {"$gte": value}}
        for name, value in thresholds.items()
        if name != "policy_status" and isinstance(value, (int, float))
    ]
    if not conditions:
        raise ValueError("threshold file contains no numeric pollutant thresholds")
    return list(collection.find({
        "timestamp": {"$gte": start, "$lt": end},
        "quality.status": "accepted",
        "$or": conditions,
    }, {"_id": 0, "station": 1, "timestamp": 1, "measurements": 1}).sort("timestamp", 1).limit(100).max_time_ms(max_time_ms))


def run_benchmark(database: Database, sla_ms: int) -> dict[str, Any]:
    collection = database["measurements"]
    checks = [
        timed_query(
            "dashboard_latest_24h",
            sla_ms,
            lambda: latest_readings(collection, DEFAULT_STATION, 24),
        ),
        timed_query(
            "analyst_daily_pm25_trend",
            sla_ms,
            lambda: daily_trend(
                collection, DEFAULT_STATION, "pm25", DEFAULT_FROM, DEFAULT_TO, sla_ms
            ),
        ),
        timed_query(
            "policy_station_comparison",
            sla_ms,
            lambda: compare_stations(collection, "pm25", DEFAULT_FROM, DEFAULT_TO, sla_ms),
        ),
        timed_query(
            "data_steward_quality_summary",
            sla_ms,
            lambda: quality_summary(collection, sla_ms),
        ),
    ]
    report = {
        "run_at": datetime.now(timezone.utc),
        "dataset_window": {"from": DEFAULT_FROM, "to": DEFAULT_TO},
        "all_queries_meet_sla": all(check["meets_sla"] for check in checks),
        "checks": [{key: value for key, value in check.items() if key != "results"} for check in checks],
    }
    database["query_benchmarks"].insert_one(report.copy())
    return report


def parse_datetime(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run stakeholder-oriented air-quality queries")
    parser.add_argument("command", choices=["latest", "trend", "compare", "quality", "alerts", "benchmark"])
    parser.add_argument("--station", default=DEFAULT_STATION)
    parser.add_argument("--pollutant", default="pm25")
    parser.add_argument("--from-time", default=DEFAULT_FROM.isoformat())
    parser.add_argument("--to-time", default=DEFAULT_TO.isoformat())
    parser.add_argument("--thresholds", default="config/alert_thresholds.example.json")
    parser.add_argument("--sla-ms", type=int, default=int(os.getenv("QUERY_SLA_MS", "2000")))
    return parser


def main() -> None:
    args = build_parser().parse_args()
    mongo_uri = os.getenv("MONGO_URI", "mongodb://localhost:27017")
    database_name = os.getenv("MONGO_DATABASE", "city_air")
    start, end = parse_datetime(args.from_time), parse_datetime(args.to_time)

    with MongoClient(mongo_uri, serverSelectionTimeoutMS=10_000) as client:
        database = client[database_name]
        collection = database["measurements"]
        if args.command == "latest":
            result: Any = timed_query(
                "dashboard_latest_24h", args.sla_ms,
                lambda: latest_readings(collection, args.station, 24),
            )
        elif args.command == "trend":
            result = timed_query(
                "analyst_daily_trend", args.sla_ms,
                lambda: daily_trend(collection, args.station, args.pollutant, start, end, args.sla_ms),
            )
        elif args.command == "compare":
            result = timed_query(
                "policy_station_comparison", args.sla_ms,
                lambda: compare_stations(collection, args.pollutant, start, end, args.sla_ms),
            )
        elif args.command == "quality":
            result = timed_query(
                "data_steward_quality_summary", args.sla_ms,
                lambda: quality_summary(collection, args.sla_ms),
            )
        elif args.command == "alerts":
            with Path(args.thresholds).open(encoding="utf-8") as stream:
                thresholds = json.load(stream)
            result = {
                "policy_status": thresholds.get("policy_status", "unspecified"),
                "notice": "Candidates only; no citizen notification is sent by this prototype.",
                "candidates": alert_candidates(collection, thresholds, start, end, args.sla_ms),
            }
        else:
            result = run_benchmark(database, args.sla_ms)

    print(json.dumps(result, default=str, indent=2))
    if args.command == "benchmark" and not result["all_queries_meet_sla"]:
        sys.exit(2)
    if isinstance(result, dict) and result.get("meets_sla") is False:
        sys.exit(2)


if __name__ == "__main__":
    main()
