"""Operational monitoring stored alongside the data in MongoDB."""

from __future__ import annotations

import json
import os
import sys
import uuid
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from time import perf_counter
from typing import Any

from pymongo import MongoClient
from pymongo.database import Database


@dataclass
class RunCounters:
    rows_seen: int = 0
    accepted_rows: int = 0
    warning_rows: int = 0
    rejected_rows: int = 0
    inserted_rows: int = 0
    existing_rows: int = 0


class RunMonitor:
    """Persist run status, counters, heartbeat and failure details."""

    def __init__(self, database: Database, dataset_url: str) -> None:
        self.collection = database["ingestion_runs"]
        self.run_id = str(uuid.uuid4())
        self.started_at = datetime.now(timezone.utc)
        self.started_clock = perf_counter()
        self.counters = RunCounters()
        self.collection.insert_one({
            "_id": self.run_id,
            "status": "running",
            "dataset_url": dataset_url,
            "started_at": self.started_at,
            "last_heartbeat_at": self.started_at,
            "counters": asdict(self.counters),
        })

    def heartbeat(self) -> None:
        self.collection.update_one(
            {"_id": self.run_id},
            {"$set": {
                "last_heartbeat_at": datetime.now(timezone.utc),
                "counters": asdict(self.counters),
            }},
        )

    def succeed(self, stored_rows: int) -> None:
        finished_at = datetime.now(timezone.utc)
        self.collection.update_one(
            {"_id": self.run_id},
            {"$set": {
                "status": "succeeded",
                "finished_at": finished_at,
                "last_heartbeat_at": finished_at,
                "duration_seconds": round(perf_counter() - self.started_clock, 3),
                "stored_rows": stored_rows,
                "counters": asdict(self.counters),
            }},
        )

    def fail(self, error: BaseException) -> None:
        finished_at = datetime.now(timezone.utc)
        self.collection.update_one(
            {"_id": self.run_id},
            {"$set": {
                "status": "failed",
                "finished_at": finished_at,
                "last_heartbeat_at": finished_at,
                "duration_seconds": round(perf_counter() - self.started_clock, 3),
                "error_type": type(error).__name__,
                "error_message": str(error)[:1000],
                "counters": asdict(self.counters),
            }},
        )


def latest_health(database: Database) -> dict[str, Any]:
    latest = database["ingestion_runs"].find_one(sort=[("started_at", -1)])
    last_success = database["ingestion_runs"].find_one(
        {"status": "succeeded"}, sort=[("finished_at", -1)]
    )
    return {
        "healthy": bool(latest and latest.get("status") == "succeeded"),
        "latest_run": latest,
        "last_success": last_success,
    }


def main() -> None:
    mongo_uri = os.getenv("MONGO_URI", "mongodb://localhost:27017")
    database_name = os.getenv("MONGO_DATABASE", "city_air")
    with MongoClient(mongo_uri, serverSelectionTimeoutMS=10_000) as client:
        report = latest_health(client[database_name])
    print(json.dumps(report, default=str, indent=2))
    if not report["healthy"]:
        sys.exit(2)


if __name__ == "__main__":
    main()
