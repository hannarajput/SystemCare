"""Unit tests for HealthReportGenerator."""

import os
import tempfile
import unittest
from systemcare.core.boost_engine import BoostResult
from systemcare.core.diagnosis import (
    DiagnosticCategory,
    DiagnosticIssue,
    DiagnosticReport,
    DiagnosticSeverity,
)
from systemcare.core.monitor import DiskUsageInfo, HardwareTemperatureInfo, SystemSnapshot
from systemcare.core.report_generator import HealthReportData, HealthReportGenerator


class TestReportGenerator(unittest.TestCase):

    def setUp(self):
        self.generator = HealthReportGenerator()
        self.snapshot = SystemSnapshot(
            cpu_percent_total=45.2,
            ram_total_bytes=16 * 1024**3,
            ram_used_bytes=8 * 1024**3,
            ram_available_bytes=8 * 1024**3,
            ram_percent=50.0,
            host_name="TEST-LAPTOP",
            os_name="Windows 11 (AMD64)",
            uptime_seconds=3600,
            disks=[
                DiskUsageInfo(
                    mountpoint="C:\\",
                    device="C:\\",
                    fstype="NTFS",
                    total_bytes=512 * 1024**3,
                    used_bytes=256 * 1024**3,
                    free_bytes=256 * 1024**3,
                    percent=50.0,
                )
            ],
            temperature=HardwareTemperatureInfo(available=False, status_message="Sensor Driver Not Found"),
        )
        self.diag = DiagnosticReport(
            overall_score=85,
            overall_status="Good",
            issues=[
                DiagnosticIssue(
                    id="ram_warning",
                    category=DiagnosticCategory.MEMORY,
                    severity=DiagnosticSeverity.WARNING,
                    title="High Memory Usage",
                    summary="Memory is elevated.",
                    evidence="RAM usage at 50%",
                    recommendation="Run Safe Boost Mode.",
                )
            ],
            healthy_checks=["CPU load is normal.", "Storage headroom is healthy."],
            timestamp=1700000000.0,
        )

    def test_build_report_data(self):
        data = self.generator.build_report_data(self.snapshot, self.diag)
        self.assertIsInstance(data, HealthReportData)
        self.assertEqual(data.health_score, 85)
        self.assertEqual(data.health_status, "Good")
        self.assertEqual(len(data.issues), 1)
        self.assertEqual(len(data.healthy_aspects), 2)

    def test_to_markdown_formatting(self):
        data = self.generator.build_report_data(self.snapshot, self.diag)
        md = self.generator.to_markdown(data)
        self.assertIn("# SystemCare — PC Health & Performance Audit Report", md)
        self.assertIn("85/100", md)
        self.assertIn("High Memory Usage", md)
        self.assertIn("Run Safe Boost Mode", md)

    def test_export_report_file(self):
        data = self.generator.build_report_data(self.snapshot, self.diag)
        with tempfile.TemporaryDirectory() as tmpdir:
            md_path = os.path.join(tmpdir, "report.md")
            success_md = self.generator.export_report(data, md_path, format_type="markdown")
            self.assertTrue(success_md)
            self.assertTrue(os.path.exists(md_path))

            json_path = os.path.join(tmpdir, "report.json")
            success_json = self.generator.export_report(data, json_path, format_type="json")
            self.assertTrue(success_json)
            self.assertTrue(os.path.exists(json_path))


if __name__ == "__main__":
    unittest.main()
