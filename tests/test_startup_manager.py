"""Unit tests for StartupManager."""

import unittest
from systemcare.core.startup_manager import StartupItem, StartupManager


class TestStartupManager(unittest.TestCase):

    def setUp(self):
        self.sm = StartupManager()

    def test_list_startup_items(self):
        items = self.sm.list_startup_items()
        self.assertIsInstance(items, list)
        # Even if system has few startup items, list should return properly without error
        for it in items:
            self.assertIsInstance(it, StartupItem)
            self.assertTrue(hasattr(it, "name"))
            self.assertTrue(hasattr(it, "command"))
            self.assertIn(it.impact, ("Essential", "High", "Medium", "Low", "Unknown"))
            self.assertIsInstance(it.can_toggle, bool)

    def test_startup_analysis(self):
        # Known impact tests
        imp, desc, guide = self.sm._analyze_startup_entry("OneDrive", "C:\\OneDrive.exe")
        self.assertEqual(imp, "Medium")
        self.assertIn("OneDrive", desc)

        imp, desc, guide = self.sm._analyze_startup_entry("SecurityHealth", "SecurityHealthSystray.exe")
        self.assertEqual(imp, "Essential")
        self.assertIn("Essential", guide)

    def test_prevent_toggle_essential_item(self):
        item = StartupItem(
            id="test_essential",
            name="SecurityHealth",
            command="SecurityHealthSystray.exe",
            location_type="Registry (User)",
            location_path="",
            is_enabled=True,
            impact="Essential",
            description="",
            guidance="",
            can_toggle=False,
        )
        success, msg = self.sm.toggle_startup_item(item)
        self.assertFalse(success)
        self.assertIn("cannot be disabled", msg.lower())


if __name__ == "__main__":
    unittest.main()
