import datetime as dt
import unittest

from tsfmt import to_iso


class ToIso(unittest.TestCase):
    def test_aware_values_are_converted_to_utc(self):
        ts = dt.datetime(2026, 10, 14, 12, 0, tzinfo=dt.timezone(dt.timedelta(hours=2)))
        self.assertEqual(to_iso(ts), "2026-10-14T10:00:00+00:00")

    def test_output_has_seconds_precision(self):
        ts = dt.datetime(2026, 10, 14, 12, 0, 5, 123456, tzinfo=dt.timezone.utc)
        self.assertEqual(to_iso(ts), "2026-10-14T12:00:05+00:00")


if __name__ == "__main__":
    unittest.main()
