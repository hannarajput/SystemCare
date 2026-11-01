"""Unit tests for StorageAnalyzer."""

import os
import shutil
import tempfile
import unittest
from systemcare.core.storage_analyzer import StorageAnalyzer


class TestStorageAnalyzer(unittest.TestCase):

    def setUp(self):
        self.analyzer = StorageAnalyzer()
        self.test_dir = tempfile.mkdtemp(prefix="systemcare_storage_test_")

        # Create a large dummy archive (1 MB) and a small document
        self.large_archive = os.path.join(self.test_dir, "backup.zip")
        with open(self.large_archive, "wb") as f:
            f.write(b"Z" * (1024 * 1024))

        self.small_doc = os.path.join(self.test_dir, "readme.txt")
        with open(self.small_doc, "w") as f:
            f.write("small text")

    def tearDown(self):
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_extension_categorization(self):
        self.assertEqual(self.analyzer._categorize_extension("movie.mp4"), "Videos")
        self.assertEqual(self.analyzer._categorize_extension("archive.tar.gz"), "Archives")
        self.assertEqual(self.analyzer._categorize_extension("installer.msi"), "Installers")
        self.assertEqual(self.analyzer._categorize_extension("doc.pdf"), "Documents")
        self.assertEqual(self.analyzer._categorize_extension("unknown.xyz123"), "Other")

    def test_analyze_target(self):
        # min 0.5 MB so the 1MB file is captured, scan_system_caches=False for isolated unit test
        result = self.analyzer.analyze_target(self.test_dir, min_large_file_mb=0.5, scan_system_caches=False)
        self.assertGreaterEqual(result.scanned_files_count, 2)
        self.assertEqual(len(result.large_files), 1)
        self.assertEqual(result.large_files[0].filename, "backup.zip")
        self.assertEqual(result.large_files[0].category, "Archives")

    def test_clean_files_safely(self):
        # Clean the large_archive
        result = self.analyzer.clean_files([self.large_archive], use_recycle_bin=True)
        self.assertEqual(result.files_recycled_count, 1)
        self.assertGreater(result.bytes_moved_to_recycle_bin, 0)
        self.assertFalse(os.path.exists(self.large_archive))


if __name__ == "__main__":
    unittest.main()
