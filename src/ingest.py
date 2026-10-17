"""Retryable batch loader for the UCI Beijing Multi-Site Air Quality data."""

from __future__ import annotations

import csv
import io
import logging
import os
import tempfile
import time
import urllib.request
import zipfile
from pathlib import Path
from typing import Any, Iterator

from pymongo import MongoClient, UpdateOne
from pymongo.collection import Collection
from pymongo.errors import AutoReconnect, NetworkTimeout, PyMongoError, ServerSelectionTimeoutError

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
) -> None:
    """Upsert a batch; deterministic keys make retries safe after partial/uncertain writes."""
    operations = [
        UpdateOne({"_id": document["_id"]}, {"$setOnInsert": document}, upsert=True)
        for document in batch
    ]
    for attempt in range(max_retries + 1):
        try:
            collection.bulk_write(operations, ordered=False)
            return
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
        csv_names = sorted(name for name in archive.namelist() if name.lower().endswith(".csv"))
        if not csv_names:
            raise ValueError("dataset archive contains no CSV files")
        for name in csv_names:
            LOG.info("Reading %s", name)
            with archive.open(name) as raw, io.TextIOWrapper(raw, encoding="utf-8-sig", newline="") as stream:
                yield from csv.DictReader(stream)


def ingest(collection: Collection, archive_path: Path, batch_size: int, max_retries: int, retry_base_seconds: float) -> int:
    processed = 0
    for batch_number, batch in enumerate(
        batched((normalize_row(row) for row in iter_csv_rows(archive_path)), batch_size), start=1
    ):
        write_batch_with_retry(collection, batch, max_retries, retry_base_seconds)
        processed += len(batch)
        if batch_number % 50 == 0:
            LOG.info("Acknowledged %s source records", processed)
    return processed


def main() -> None:
    logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"), format="%(asctime)s %(levelname)s %(message)s")
    mongo_uri = os.getenv("MONGO_URI", "mongodb://localhost:27017")
    database_name = os.getenv("MONGO_DATABASE", "city_air")
    collection_name = os.getenv("MONGO_COLLECTION", "measurements")
    batch_size = int(os.getenv("BATCH_SIZE", "1000"))
    max_retries = int(os.getenv("MAX_RETRIES", "5"))
    retry_base_seconds = float(os.getenv("RETRY_BASE_SECONDS", "1"))
    dataset_url = os.getenv("DATASET_URL", DATASET_URL)

    with tempfile.TemporaryDirectory(prefix="air-quality-") as temporary_directory:
        archive_path = download_dataset(dataset_url, Path(temporary_directory) / "dataset.zip")
        with MongoClient(mongo_uri, serverSelectionTimeoutMS=10_000) as client:
            client.admin.command("ping")
            collection = client[database_name][collection_name]
            total = ingest(collection, archive_path, batch_size, max_retries, retry_base_seconds)
            stored = collection.count_documents({})
            LOG.info("Run complete: processed=%s stored=%s", total, stored)


if __name__ == "__main__":
    main()
