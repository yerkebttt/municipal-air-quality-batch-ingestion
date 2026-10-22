import unittest
import io
import tempfile
import zipfile
from datetime import datetime, timedelta, timezone
from pathlib import Path

from src.ingest import _rejection_id, iter_csv_rows, validate_reconciliation
from src.quality import DEFAULT_RULES, assess_document
from src.queries import compare_stations_pipeline, daily_trend_pipeline, timed_query
from src.transform import batched, normalize_row


class NormalizeRowTests(unittest.TestCase):
    def test_maps_measurements_and_missing_values(self):
        document = normalize_row({
            "year": "2013", "month": "3", "day": "1", "hour": "0", "station": "Station-A",
            "PM2.5": "12.5", "PM10": "NA", "TEMP": "-0.7", "wd": "NW",
        })
        self.assertEqual(document["_id"], "Station-A|2013-03-01T00:00:00+08:00")
        self.assertEqual(document["timestamp"], datetime(2013, 3, 1, tzinfo=timezone(timedelta(hours=8))))
        self.assertEqual(document["source_timezone"], "Asia/Shanghai")
        self.assertEqual(document["measurements"], {"pm25": 12.5, "temperature_c": -0.7, "wind_direction": "NW"})
        self.assertEqual(document["quality"]["status"], "warning")
        self.assertIn("missing_pollutants", document["quality"]["flags"])

    def test_preserves_unknown_future_measurement(self):
        document = normalize_row({
            "year": "2013", "month": "3", "day": "1", "hour": "1", "station": "Station-A",
            "CO2": "420.4",
        })
        self.assertEqual(document["measurements"]["co2"], 420.4)


class BatchTests(unittest.TestCase):
    def test_splits_without_losing_tail(self):
        self.assertEqual([len(batch) for batch in batched(({"n": i} for i in range(5)), 2)], [2, 2, 1])

    def test_rejects_invalid_size(self):
        with self.assertRaises(ValueError):
            list(batched([], 0))

    def test_reads_real_csv_from_nested_uci_archive(self):
        inner_bytes = io.BytesIO()
        with zipfile.ZipFile(inner_bytes, "w") as inner:
            inner.writestr("station.csv", "year,month,day,hour,station,PM2.5\n2017,1,2,3,S,10\n")
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "outer.zip"
            with zipfile.ZipFile(path, "w") as outer:
                outer.writestr("PRSA2017.zip", inner_bytes.getvalue())
                outer.writestr("data.csv", "not,the,measurement,file\n")
            rows = list(iter_csv_rows(path))
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["station"], "S")


class QualityTests(unittest.TestCase):
    def test_accepts_complete_pollutant_record(self):
        document = normalize_row({
            "year": "2017", "month": "1", "day": "2", "hour": "3", "station": "S",
            "PM2.5": "20", "PM10": "30", "SO2": "5", "NO2": "10", "CO": "500", "O3": "40",
        })
        self.assertEqual(document["quality"]["status"], "accepted")
        self.assertEqual(document["quality"]["pollutant_completeness"], 1.0)

    def test_flags_but_retains_outlier_for_review(self):
        document = {"measurements": {
            "pm25": 1200.0, "pm10": 30.0, "so2": 5.0,
            "no2": 10.0, "co": 500.0, "o3": 40.0,
        }}
        assessed = assess_document(document, DEFAULT_RULES)
        self.assertEqual(assessed["quality"]["status"], "warning")
        self.assertEqual(assessed["measurements"]["pm25"], 1200.0)
        self.assertEqual(assessed["quality"]["outside_screening_range"][0]["field"], "pm25")

    def test_rejection_id_is_stable_for_same_row(self):
        first = {"station": "", "year": "bad", "PM2.5": "10"}
        second = {"PM2.5": "10", "year": "bad", "station": ""}
        self.assertEqual(_rejection_id(first), _rejection_id(second))


class StakeholderQueryTests(unittest.TestCase):
    def setUp(self):
        self.start = datetime(2017, 1, 1, tzinfo=timezone.utc)
        self.end = datetime(2017, 2, 1, tzinfo=timezone.utc)

    def test_daily_trend_filters_station_time_and_metric(self):
        pipeline = daily_trend_pipeline("Station-A", "pm25", self.start, self.end)
        match = pipeline[0]["$match"]
        self.assertEqual(match["station"], "Station-A")
        self.assertEqual(match["timestamp"], {"$gte": self.start, "$lt": self.end})
        self.assertIn("measurements.pm25", match)

    def test_station_comparison_groups_by_station(self):
        pipeline = compare_stations_pipeline("pm25", self.start, self.end)
        self.assertEqual(pipeline[1]["$group"]["_id"], "$station")

    def test_latency_check_reports_sla_result(self):
        report = timed_query("test", 1000, lambda: [1, 2])
        self.assertEqual(report["rows_returned"], 2)
        self.assertTrue(report["meets_sla"])


class ReconciliationTests(unittest.TestCase):
    def test_accepts_complete_reconciliation(self):
        validate_reconciliation(10, 9, 1, 7, 2, 1, 10)

    def test_rejects_unexpected_source_size(self):
        with self.assertRaisesRegex(RuntimeError, "unexpected source size"):
            validate_reconciliation(9, 9, 0, 7, 2, 0, 10)

    def test_rejects_unclassified_rows(self):
        with self.assertRaisesRegex(RuntimeError, "classification mismatch"):
            validate_reconciliation(10, 10, 0, 7, 2, 0, 10)


if __name__ == "__main__":
    unittest.main()
