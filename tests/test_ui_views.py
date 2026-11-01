"""
Headless UI and View Integration Tests.
Instantiates SystemCareApp and navigates through all views to verify
complete rendering and error-free operation.
"""

import unittest
from systemcare.ui.app import SystemCareApp


class TestUIViews(unittest.TestCase):

    def setUp(self):
        self.app = SystemCareApp()
        # Withdraw window to prevent popping up during automated tests
        self.app.withdraw()

    def tearDown(self):
        self.app.on_closing()

    def test_navigate_all_views(self):
        views_to_test = [
            "dashboard",
            "diagnosis",
            "boost",
            "processes",
            "startup",
            "duplicate",
            "storage",
            "reports",
            "settings",
        ]

        for v_name in views_to_test:
            with self.subTest(view=v_name):
                self.app.navigate_to(v_name)
                # Pump Tkinter event loop to ensure layout computations succeed
                self.app.update_idletasks()
                self.assertIn(v_name, self.app.views)
                self.assertIsNotNone(self.app.views[v_name])


if __name__ == "__main__":
    unittest.main()
