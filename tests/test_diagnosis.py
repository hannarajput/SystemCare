"""Unit tests for PerformanceDiagnosis."""

import unittest
from systemcare.core.diagnosis import (
    DiagnosticCategory,
    DiagnosticReport,
    DiagnosticSeverity,
    PerformanceDiagnosis,
)
from systemcare.core.monitor import DiskUsageInfo, HardwareTemperatureInfo, SystemSnapshot


class TestDiagnosis(unittest.TestCase):

    def setUp(self):
        self.diag = PerformanceDiagnosis()

    def test_normal_healthy_system(self):
        snap = SystemSnapshot(
            cpu_percent_total=25.0,
            ram_percent=45.0,
            ram_total_bytes=16 * 1024**3,
            ram_used_bytes=7 * 1024**3,
            ram_available_bytes=9 * 1024**3,
            disks=[
                DiskUsageInfo(
                    mountpoint="C:\\",
                    device="C:\\",
                    fstype="NTFS",
                    total_bytes=500 * 1024**3,
                    used_bytes=200 * 1024**3,
                    free_bytes=300 * 1024**3,
                    percent=40.0,
                )
            ],
            temperature=HardwareTemperatureInfo(
                available=True, temperature_celsius=52.0, sensor_name="Core 0"
            ),
        )
        report = self.diag.evaluate(snap)
        self.assertIsInstance(report, DiagnosticReport)
        self.assertEqual(report.overall_status, "Excellent")
        self.assertGreaterEqual(report.overall_score, 90)
        self.assertEqual(len(report.issues), 0)
        self.assertGreater(len(report.healthy_checks), 0)

    def test_high_cpu_critical_issue(self):
        snap = SystemSnapshot(
            cpu_percent_total=95.0,
            ram_percent=50.0,
            ram_total_bytes=16 * 1024**3,
            ram_used_bytes=8 * 1024**3,
            ram_available_bytes=8 * 1024**3,
            disks=[],
        )
        top_cpu = [{"name": "heavy_encoder.exe", "cpu_percent": 82.5}]
        report = self.diag.evaluate(snap, top_cpu_processes=top_cpu)

        # Should identify critical CPU issue
        cpu_issues = [i for i in report.issues if i.category == DiagnosticCategory.CPU]
        self.assertEqual(len(cpu_issues), 1)
        self.assertEqual(cpu_issues[0].severity, DiagnosticSeverity.CRITICAL)
        self.assertIn("heavy_encoder.exe", cpu_issues[0].evidence)
        self.assertLess(report.overall_score, 80)

    def test_memory_pressure_critical(self):
        snap = SystemSnapshot(
            cpu_percent_total=20.0,
            ram_percent=94.0,
            ram_total_bytes=16 * 1024**3,
            ram_used_bytes=15 * 1024**3,
            ram_available_bytes=1 * 1024**3,
            swap_percent=88.0,
            swap_total_bytes=8 * 1024**3,
            swap_used_bytes=7 * 1024**3,
            disks=[],
        )
        report = self.diag.evaluate(snap)
        ram_issues = [i for i in report.issues if i.category == DiagnosticCategory.MEMORY]
        self.assertGreaterEqual(len(ram_issues), 1)
        self.assertTrue(any(i.severity == DiagnosticSeverity.CRITICAL for i in ram_issues))

    def test_disk_bottleneck_detection(self):
        snap = SystemSnapshot(
            cpu_percent_total=10.0,
            ram_percent=40.0,
            ram_total_bytes=16 * 1024**3,
            ram_used_bytes=6 * 1024**3,
            ram_available_bytes=10 * 1024**3,
            disks=[
                DiskUsageInfo(
                    mountpoint="C:\\",
                    device="C:\\",
                    fstype="NTFS",
                    total_bytes=256 * 1024**3,
                    used_bytes=251 * 1024**3,
                    free_bytes=5 * 1024**3,  # 5 GB free (critical < 10GB)
                    percent=98.0,
                )
            ],
        )
        report = self.diag.evaluate(snap)
        disk_issues = [i for i in report.issues if i.category == DiagnosticCategory.DISK]
        self.assertGreaterEqual(len(disk_issues), 1)
        self.assertEqual(disk_issues[0].severity, DiagnosticSeverity.CRITICAL)


if __name__ == "__main__":
    unittest.main()
