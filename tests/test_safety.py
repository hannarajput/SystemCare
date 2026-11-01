"""Unit tests for safety guardrails and system protection."""

import os
import unittest
from systemcare.utils.safety import (
    CRITICAL_SYSTEM_FILES,
    PROTECTED_PROCESS_NAMES,
    is_protected_cleanup_path,
    is_system_process,
)


class TestSafety(unittest.TestCase):

    def test_system_process_detection(self):
        # Kernel PIDs
        self.assertTrue(is_system_process(0, "System Idle Process"))
        self.assertTrue(is_system_process(4, "System"))

        # Core OS executables
        self.assertTrue(is_system_process(1234, "csrss.exe"))
        self.assertTrue(is_system_process(5678, "svchost.exe"))
        self.assertTrue(is_system_process(9999, "explorer.exe"))
        self.assertTrue(is_system_process(1001, "dwm.exe"))
        self.assertTrue(is_system_process(1002, "lsass.exe"))
        self.assertTrue(is_system_process(1003, "services.exe"))
        self.assertTrue(is_system_process(1004, "MsMpEng.exe"))  # Windows Defender

        # User applications should NOT be system
        self.assertFalse(is_system_process(8888, "notepad.exe"))
        self.assertFalse(is_system_process(7777, "calculator.exe"))
        self.assertFalse(is_system_process(6666, "mycustomapp.exe"))

    def test_protected_cleanup_paths(self):
        # Windows directory
        win_dir = os.environ.get("SystemRoot", r"C:\Windows")
        self.assertTrue(is_protected_cleanup_path(win_dir))
        self.assertTrue(is_protected_cleanup_path(os.path.join(win_dir, "System32")))
        self.assertTrue(is_protected_cleanup_path(os.path.join(win_dir, "System32", "kernel32.dll")))

        # Program Files
        prog_files = os.environ.get("ProgramFiles", r"C:\Program Files")
        self.assertTrue(is_protected_cleanup_path(prog_files))

        # Personal user libraries
        user_profile = os.environ.get("USERPROFILE", "")
        if user_profile:
            self.assertTrue(is_protected_cleanup_path(user_profile))
            self.assertTrue(is_protected_cleanup_path(os.path.join(user_profile, "Documents")))
            self.assertTrue(is_protected_cleanup_path(os.path.join(user_profile, "Desktop")))
            self.assertTrue(is_protected_cleanup_path(os.path.join(user_profile, "Pictures")))

        # Critical swap / hiberfil files
        for cf in CRITICAL_SYSTEM_FILES:
            self.assertTrue(is_protected_cleanup_path(f"C:\\{cf}"))

        # Empty / None path should be guarded
        self.assertTrue(is_protected_cleanup_path(""))
        self.assertTrue(is_protected_cleanup_path("C:\\"))

    def test_user_temp_path_not_blocked(self):
        # A file inside user temp folder should not be blocked as a protected directory
        user_temp = os.environ.get("TEMP")
        if user_temp:
            sample_temp = os.path.join(user_temp, "systemcare_scratch_test.tmp")
            self.assertFalse(is_protected_cleanup_path(sample_temp))

    def test_personal_folder_children_and_subdirectories_protected(self):
        user_profile = os.environ.get("USERPROFILE", "")
        if user_profile:
            # Subdirectories and files within personal libraries MUST be strictly protected
            doc_file = os.path.join(user_profile, "Documents", "financial_records.xlsx")
            desktop_sub = os.path.join(user_profile, "Desktop", "MyFolder", "project.py")
            pictures_file = os.path.join(user_profile, "Pictures", "Vacation", "img.jpg")
            self.assertTrue(is_protected_cleanup_path(doc_file))
            self.assertTrue(is_protected_cleanup_path(desktop_sub))
            self.assertTrue(is_protected_cleanup_path(pictures_file))

    def test_path_traversal_detection(self):
        user_temp = os.environ.get("TEMP", r"C:\Windows\Temp")
        # Attempt traversal from temp to Windows or Documents
        traversal_attack = os.path.join(user_temp, "..", "..", "Windows", "System32", "calc.exe")
        self.assertTrue(is_protected_cleanup_path(traversal_attack))

    def test_drive_roots_strictly_protected(self):
        for root in ["C:\\", "D:\\", "C:", "c:/", "\\\\localhost\\c$"]:
            self.assertTrue(is_protected_cleanup_path(root))


if __name__ == "__main__":
    unittest.main()
