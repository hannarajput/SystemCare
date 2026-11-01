"""Unit tests for SafeBoostEngine."""

import unittest
from unittest.mock import MagicMock, patch
from systemcare.core.boost_engine import BoostResult, SafeBoostEngine


class TestBoostEngine(unittest.TestCase):

    def setUp(self):
        self.engine = SafeBoostEngine()

    def test_analyze_system_actions(self):
        actions = self.engine.analyze_system()
        self.assertIsInstance(actions, list)
        self.assertGreaterEqual(len(actions), 2)

        action_ids = [a.id for a in actions]
        self.assertIn("trim_memory", action_ids)
        self.assertIn("clean_user_temp", action_ids)

        # Check safety ratings
        for act in actions:
            self.assertIn(act.safety_rating, ("Very Safe", "Safe"))

    @patch("systemcare.core.boost_engine._OpenProcess")
    @patch("systemcare.core.boost_engine._EmptyWorkingSet")
    @patch("systemcare.core.boost_engine._CloseHandle")
    def test_execute_memory_trim_boost_mocked(self, mock_close, mock_empty, mock_open):
        # Mock Windows API handle return
        mock_open.return_value = 12345
        mock_empty.return_value = 1
        mock_close.return_value = 1

        result = self.engine.execute_boost(["trim_memory"])
        self.assertIsInstance(result, BoostResult)
        self.assertGreaterEqual(result.ram_after_percent, 0.0)
        self.assertLessEqual(result.ram_after_percent, 100.0)
        self.assertIn("Trim Idle Process Working Sets", result.actions_executed)
        self.assertGreaterEqual(result.working_set_trimmed_bytes, 0)

    @patch("systemcare.core.boost_engine._OpenProcess")
    def test_windows_api_permission_denied_handled_safely(self, mock_open):
        # Simulate OpenProcess returning NULL (Access Denied / Insufficient Privileges)
        mock_open.return_value = 0

        # Reset cooldown for test
        self.engine._last_trim_timestamp = 0.0
        result = self.engine.execute_boost(["trim_memory"])
        self.assertIsInstance(result, BoostResult)
        # Should complete gracefully without raising uncaught exception
        self.assertIn("Trim Idle Process Working Sets", result.actions_executed)


if __name__ == "__main__":
    unittest.main()
