"""Unit tests for DuplicateFinder."""

import os
import shutil
import tempfile
import time
import unittest
from systemcare.core.duplicate_finder import DuplicateFinder


class TestDuplicateFinder(unittest.TestCase):

    def setUp(self):
        self.finder = DuplicateFinder()
        self.test_dir = tempfile.mkdtemp(prefix="systemcare_dup_test_")

        # Create test files
        # File A1 and A2 have identical content "ALPHA CONTENT 1234567890"
        self.file_a1 = os.path.join(self.test_dir, "file_a1.txt")
        self.file_a2 = os.path.join(self.test_dir, "file_a2.txt")
        with open(self.file_a1, "w", encoding="utf-8") as f:
            f.write("ALPHA CONTENT 1234567890")
        time.sleep(0.05)
        with open(self.file_a2, "w", encoding="utf-8") as f:
            f.write("ALPHA CONTENT 1234567890")

        # File B has unique size
        self.file_b = os.path.join(self.test_dir, "file_b.txt")
        with open(self.file_b, "w", encoding="utf-8") as f:
            f.write("UNIQUE FILE CONTENT")

        # File C1 and C2 have identical content
        self.file_c1 = os.path.join(self.test_dir, "file_c1.bin")
        self.file_c2 = os.path.join(self.test_dir, "file_c2.bin")
        payload = b"BIN_DATA_" * 1000
        with open(self.file_c1, "wb") as f:
            f.write(payload)
        time.sleep(0.05)
        with open(self.file_c2, "wb") as f:
            f.write(payload)

    def tearDown(self):
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_duplicate_scan_accuracy(self):
        groups = self.finder.scan_folder(self.test_dir, min_size_bytes=1)
        # Should detect exactly 2 duplicate groups: (A1, A2) and (C1, C2)
        self.assertEqual(len(groups), 2)

        total_dups = sum(len(g.files) for g in groups)
        self.assertEqual(total_dups, 4)

        reclaimable = sum(g.reclaimable_bytes for g in groups)
        self.assertGreater(reclaimable, 0)

    def test_auto_selection_keep_newest(self):
        groups = self.finder.scan_folder(self.test_dir, min_size_bytes=1)
        self.finder.auto_select_duplicates(groups, strategy="keep_newest")

        for g in groups:
            # Exactly one file should remain unselected (the kept newest one)
            selected_count = sum(1 for f in g.files if f.selected)
            self.assertEqual(selected_count, len(g.files) - 1)

    def test_delete_selected_files_safely(self):
        groups = self.finder.scan_folder(self.test_dir, min_size_bytes=1)
        self.finder.auto_select_duplicates(groups, strategy="keep_newest")

        to_delete = []
        for g in groups:
            for f in g.files:
                if f.selected:
                    to_delete.append(f.path)

        self.assertEqual(len(to_delete), 2)

        # Safely delete via Recycle Bin
        cnt, freed, errors = self.finder.delete_selected_files(to_delete, use_recycle_bin=True)
        self.assertEqual(cnt, 2)
        self.assertGreater(freed, 0)
        self.assertEqual(len(errors), 0)

        # Verify files are removed from original location
        for p in to_delete:
            self.assertFalse(os.path.exists(p))


if __name__ == "__main__":
    unittest.main()
