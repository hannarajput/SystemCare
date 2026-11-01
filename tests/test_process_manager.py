"""Unit tests for ProcessManager."""

import os
import unittest
from systemcare.core.process_manager import ProcessInfo, ProcessManager


class TestProcessManager(unittest.TestCase):

    def setUp(self):
        self.pm = ProcessManager()

    def test_list_processes(self):
        procs = self.pm.list_processes()
        self.assertIsInstance(procs, list)
        self.assertGreater(len(procs), 0)

        # Check fields of first process
        first = procs[0]
        self.assertIsInstance(first, ProcessInfo)
        self.assertIsInstance(first.pid, int)
        self.assertIsInstance(first.name, str)
        self.assertGreaterEqual(first.memory_mb, 0.0)

    def test_system_process_rejection_for_termination(self):
        # Attempt to terminate PID 0 or PID 4 or svchost.exe
        procs = self.pm.list_processes()
        system_procs = [p for p in procs if p.is_system or p.name.lower() in ("system", "svchost.exe", "explorer.exe")]
        self.assertGreater(len(system_procs), 0)

        target = system_procs[0]
        success, msg = self.pm.terminate_process(target.pid)
        self.assertFalse(success)
        self.assertIn("Security Protection", msg)

    def test_current_python_process_safety(self):
        # Current python process should be protected as well
        cur_pid = os.getpid()
        success, msg = self.pm.terminate_process(cur_pid)
        self.assertFalse(success)
        self.assertIn("Security Protection", msg)

    def test_nonexistent_process_termination(self):
        # High PID that doesn't exist
        fake_pid = 9999999
        success, msg = self.pm.terminate_process(fake_pid)
        self.assertFalse(success)
        self.assertIn("no longer running", msg)

    def test_pid_reuse_prevention(self):
        # Even if a PID exists, if expected name or create_time mismatches, it must reject
        cur_pid = os.getpid()
        success, msg = self.pm.terminate_process(
            cur_pid,
            expected_name="malicious_spoofed_process.exe",
        )
        self.assertFalse(success)

    def test_top_process_getters(self):
        top_cpu = self.pm.get_top_cpu_processes(limit=3)
        top_ram = self.pm.get_top_ram_processes(limit=3)
        self.assertLessEqual(len(top_cpu), 3)
        self.assertLessEqual(len(top_ram), 3)


if __name__ == "__main__":
    unittest.main()
