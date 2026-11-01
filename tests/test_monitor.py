"""Unit tests for SystemMonitor."""

import time
import unittest
from systemcare.core.monitor import SystemMonitor, SystemSnapshot


class TestMonitor(unittest.TestCase):

    def setUp(self):
        self.monitor = SystemMonitor(interval_seconds=1.0)

    def tearDown(self):
        self.monitor.stop()

    def test_collect_snapshot(self):
        snap = self.monitor.get_latest_snapshot()
        self.assertIsInstance(snap, SystemSnapshot)
        self.assertGreaterEqual(snap.cpu_percent_total, 0.0)
        self.assertLessEqual(snap.cpu_percent_total, 100.0)
        self.assertGreater(snap.ram_total_bytes, 0)
        self.assertGreater(snap.ram_used_bytes, 0)
        self.assertGreaterEqual(snap.ram_percent, 0.0)
        self.assertLessEqual(snap.ram_percent, 100.0)
        self.assertIsInstance(snap.disks, list)
        self.assertGreater(len(snap.disks), 0)
        self.assertIsInstance(snap.cpu_percent_per_core, list)
        self.assertGreater(len(snap.cpu_percent_per_core), 0)

    def test_temperature_safe_handling(self):
        # Must not crash even if sensors are missing
        snap = self.monitor.get_latest_snapshot()
        temp_info = snap.temperature
        self.assertIsNotNone(temp_info)
        # On Windows standard user session, temp is expected to be gracefully unavailable
        if not temp_info.available:
            self.assertIsNone(temp_info.temperature_celsius)
            self.assertIn("Unavailable", temp_info.status_message)
        else:
            self.assertGreater(temp_info.temperature_celsius, 0)

    def test_listener_callback(self):
        received = []

        def callback(snapshot):
            received.append(snapshot)

        self.monitor.add_listener(callback)
        self.monitor.start()
        # Wait slightly for at least one tick
        time.sleep(1.2)
        self.monitor.stop()
        self.assertGreaterEqual(len(received), 1)


if __name__ == "__main__":
    unittest.main()
