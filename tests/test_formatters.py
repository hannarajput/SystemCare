"""Unit tests for formatting helpers."""

import unittest
from systemcare.utils.formatters import (
    format_bytes,
    format_duration,
    format_percent,
    format_speed,
    format_timestamp,
)


class TestFormatters(unittest.TestCase):

    def test_format_bytes(self):
        self.assertEqual(format_bytes(0), "0 B")
        self.assertEqual(format_bytes(512), "512 B")
        self.assertEqual(format_bytes(1024), "1.0 KB")
        self.assertEqual(format_bytes(1024 * 1024), "1.0 MB")
        self.assertEqual(format_bytes(1024 * 1024 * 1024), "1.0 GB")
        self.assertEqual(format_bytes(1536 * 1024 * 1024), "1.5 GB")
        self.assertEqual(format_bytes(None), "0 B")
        self.assertEqual(format_bytes(-2048), "-2.0 KB")

    def test_format_speed(self):
        self.assertEqual(format_speed(1024 * 1024), "1.0 MB/s")
        self.assertEqual(format_speed(500), "500 B/s")

    def test_format_percent(self):
        self.assertEqual(format_percent(50.25), "50.2%")
        self.assertEqual(format_percent(100.0), "100.0%")
        self.assertEqual(format_percent(None), "0.0%")

    def test_format_duration(self):
        self.assertEqual(format_duration(45), "45s")
        self.assertEqual(format_duration(125), "2m 5s")
        self.assertEqual(format_duration(3665), "1h 1m 5s")
        self.assertEqual(format_duration(-10), "0s")

    def test_format_timestamp(self):
        ts_str = format_timestamp()
        self.assertRegex(ts_str, r"^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}$")


if __name__ == "__main__":
    unittest.main()
