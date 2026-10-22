"""Reproduce the source-row and quality profile without requiring MongoDB."""

from __future__ import annotations

import argparse
import json
import tempfile
from collections import Counter
from pathlib import Path

from src.ingest import DATASET_URL, download_dataset, iter_csv_rows
from src.quality import load_quality_rules
from src.transform import normalize_row


def profile(archive_path: Path, rules_path: Path) -> dict[str, object]:
    rules = load_quality_rules(rules_path)
    statuses: Counter[str] = Counter()
    flags: Counter[str] = Counter()
    missing: Counter[str] = Counter()
    stations: Counter[str] = Counter()
    rejected = 0
    for row in iter_csv_rows(archive_path):
        try:
            document = normalize_row(row, rules)
        except (KeyError, TypeError, ValueError):
            rejected += 1
            continue
        quality = document["quality"]
        statuses[quality["status"]] += 1
        flags.update(quality["flags"])
        missing.update(quality["missing_pollutants"])
        stations[document["station"]] += 1
    return {
        "source": "UCI Beijing Multi-Site Air Quality",
        "source_url": DATASET_URL,
        "rules_version": str(rules.get("version", "unknown")),
        "source_rows": sum(statuses.values()) + rejected,
        "accepted_rows": statuses["accepted"],
        "warning_rows": statuses["warning"],
        "structurally_rejected_rows": rejected,
        "flags": dict(sorted(flags.items())),
        "missing_pollutant_values": dict(sorted(missing.items())),
        "stations": dict(sorted(stations.items())),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Profile the source archive and quality flags")
    parser.add_argument("--archive", type=Path)
    parser.add_argument("--rules", type=Path, default=Path("config/quality_rules.json"))
    args = parser.parse_args()
    if args.archive:
        report = profile(args.archive, args.rules)
    else:
        with tempfile.TemporaryDirectory(prefix="air-quality-profile-") as directory:
            archive = download_dataset(DATASET_URL, Path(directory) / "dataset.zip")
            report = profile(archive, args.rules)
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
