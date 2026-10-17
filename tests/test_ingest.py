import unittest
from datetime import datetime, timedelta, timezone

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


if __name__ == "__main__":
    unittest.main()
