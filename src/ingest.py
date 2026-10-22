"""Retryable batch loader for the UCI Beijing Multi-Site Air Quality data."""

from __future__ import annotations

import csv
import hashlib
import io
import logging
import os
import tempfile
import time
import urllib.request
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator

from pymongo import MongoClient, UpdateOne
from pymongo.collection import Collection
from pymongo.errors import AutoReconnect, NetworkTimeout, PyMongoError, ServerSelectionTimeoutError

from src.monitoring import RunMonitor
from src.quality import load_quality_rules
from src.transform import batched, normalize_row

LOG = logging.getLogger("air_quality_ingest")
DATASET_NAME = "UCI Beijing Multi-Site Air Quality"
DATASET_URL = (
    "https://archive.ics.uci.edu/static/public/501/"
    "beijing+multi+site+air+quality+data.zip"
)

def write_batch_with_retry(
    collection: Collection,
    batch: list[dict[str, Any]],
    max_retries: int,
    retry_base_seconds: float,
) -> tuple[int, int]:
    """Upsert a batch; deterministic keys make retries safe after partial/uncertain writes."""
    operations = [
        UpdateOne({"_id": document["_id"]}, {"$setOnInsert": document}, upsert=True)
        for document in batch
    ]
    for attempt in range(max_retries + 1):
        try:
            result = collection.bulk_write(operations, ordered=False)
            inserted = result.upserted_count
            return inserted, len(batch) - inserted
        except PyMongoError as exc:
            retryable = isinstance(exc, (AutoReconnect, NetworkTimeout, ServerSelectionTimeoutError))
            retryable = retryable or exc.has_error_label("RetryableWriteError")
            if not retryable or attempt >= max_retries:
                raise
            delay = retry_base_seconds * (2**attempt)
            LOG.warning("Batch write failed; retry %s/%s in %.1fs", attempt + 1, max_retries, delay)
            time.sleep(delay)


def download_dataset(url: str, destination: Path) -> Path:
    request = urllib.request.Request(url, headers={"User-Agent": "municipal-air-quality-course-project/1.0"})
    with urllib.request.urlopen(request, timeout=90) as response, destination.open("wb") as output:
        while chunk := response.read(1024 * 1024):
            output.write(chunk)
    return destination


def iter_csv_rows(archive_path: Path) -> Iterator[dict[str, str]]:
    with zipfile.ZipFile(archive_path) as archive:
        nested_names = sorted(name for name in archive.namelist() if name.lower().endswith(".zip"))
        if nested_names:
            for nested_name in nested_names:
                LOG.info("Opening nested archive %s", nested_name)
                with archive.open(nested_name) as nested_raw:
                    nested_bytes = io.BytesIO(nested_raw.read())
                with zipfile.ZipFile(nested_bytes) as nested_archive:
                    yield from _iter_csv_rows_from_archive(nested_archive)
            return
        yield from _iter_csv_rows_from_archive(archive)


def _iter_csv_rows_from_archive(archive: zipfile.ZipFile) -> Iterator[dict[str, str]]:
    csv_names = sorted(name for name in archive.namelist() if name.lower().endswith(".csv"))
    if not csv_names:
        raise ValueError("dataset archive contains no CSV files")
    for name in csv_names:
        LOG.info("Reading %s", name)
        with archive.open(name) as raw, io.TextIOWrapper(raw, encoding="utf-8-sig", newline="") as stream:
            yield from csv.DictReader(stream)


def _rejection_id(row: dict[str, str]) -> str:
    payload = "|".join(str(row.get(key, "")) for key in sorted(row))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def ingest(
    collection: Collection,
    rejected_collection: Collection,
    monitor: RunMonitor,
    archive_path: Path,
    batch_size: int,
    max_retries: int,
    retry_base_seconds: float,
    quality_rules: dict[str, Any],
) -> int:
    pending: list[dict[str, Any]] = []
    batch_number = 0

    def flush() -> None:
        nonlocal batch_number
        if not pending:
            return
        inserted, existing = write_batch_with_retry(
            collection, pending, max_retries, retry_base_seconds
        )
        monitor.counters.inserted_rows += inserted
        monitor.counters.existing_rows += existing
        pending.clear()
        batch_number += 1
        if batch_number % 50 == 0:
            monitor.heartbeat()
            LOG.info("Acknowledged %s source records", monitor.counters.rows_seen)

    for row in iter_csv_rows(archive_path):
        monitor.counters.rows_seen += 1
        try:
            document = normalize_row(row, quality_rules)
        except (KeyError, TypeError, ValueError) as error:
            monitor.counters.rejected_rows += 1
            rejected_collection.update_one(
                {"_id": _rejection_id(row)},
                {"$setOnInsert": {
                    "row": row,
                    "reason": str(error),
                    "dataset": DATASET_NAME,
                    "quarantined_at": datetime.now(timezone.utc),
                }},
                upsert=True,
            )
            continue
        status = document["quality"]["status"]
        if status == "accepted":
            monitor.counters.accepted_rows += 1
        else:
            monitor.counters.warning_rows += 1
        pending.append(document)
        if len(pending) == batch_size:
            flush()
    flush()
    monitor.heartbeat()
    return monitor.counters.rows_seen


def main() -> None:
    logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"), format="%(asctime)s %(levelname)s %(message)s")
    mongo_uri = os.getenv("MONGO_URI", "mongodb://localhost:27017")
    database_name = os.getenv("MONGO_DATABASE", "city_air")
    collection_name = os.getenv("MONGO_COLLECTION", "measurements")
    batch_size = int(os.getenv("BATCH_SIZE", "1000"))
    max_retries = int(os.getenv("MAX_RETRIES", "5"))
    retry_base_seconds = float(os.getenv("RETRY_BASE_SECONDS", "1"))
    dataset_url = os.getenv("DATASET_URL", DATASET_URL)
    quality_rules = load_quality_rules(os.getenv("QUALITY_RULES_PATH"))

    with tempfile.TemporaryDirectory(prefix="air-quality-") as temporary_directory:
        archive_path = download_dataset(dataset_url, Path(temporary_directory) / "dataset.zip")
        with MongoClient(mongo_uri, serverSelectionTimeoutMS=10_000) as client:
            client.admin.command("ping")
            database = client[database_name]
            collection = database[collection_name]
            monitor = RunMonitor(database, dataset_url)
            try:
                total = ingest(
                    collection,
                    database["rejected_measurements"],
                    monitor,
                    archive_path,
                    batch_size,
                    max_retries,
                    retry_base_seconds,
                    quality_rules,
                )
                stored = collection.count_documents({})
                monitor.succeed(stored)
                LOG.info(
                    "Run complete: seen=%s accepted=%s warnings=%s rejected=%s stored=%s",
                    total,
                    monitor.counters.accepted_rows,
                    monitor.counters.warning_rows,
                    monitor.counters.rejected_rows,
                    stored,
                )
            except BaseException as error:
                monitor.fail(error)
                raise


if __name__ == "__main__":
    main()
