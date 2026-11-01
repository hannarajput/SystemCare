"""
Health Report Generator.
Generates comprehensive diagnostic audit reports including detected issues,
likely causes, actionable recommendations, and before/after resource metrics.
Supports exporting to Markdown and JSON formats with input validation.
"""

import json
import os
import time
from dataclasses import asdict, dataclass
from typing import Dict, List, Optional

from ..utils.formatters import (
    format_bytes,
    format_duration,
    format_percent,
    format_timestamp,
)
from ..utils.safety import is_protected_cleanup_path
from .boost_engine import BoostResult
from .diagnosis import DiagnosticReport
from .monitor import SystemSnapshot


@dataclass
class HealthReportData:
    generated_at: str
    hostname: str
    os_name: str
    uptime: str
    health_score: int
    health_status: str
    cpu_percent: float
    ram_used_bytes: int
    ram_total_bytes: int
    ram_percent: float
    temperature_status: str
    disks_summary: List[Dict]
    issues: List[Dict]
    recommendations: List[str]
    healthy_aspects: List[str]
    recent_boost_metrics: Optional[Dict] = None


class HealthReportGenerator:
    """
    Builds structured PC Health audit reports.
    """

    def build_report_data(
        self,
        snapshot: SystemSnapshot,
        diag_report: DiagnosticReport,
        latest_boost_result: Optional[BoostResult] = None,
    ) -> HealthReportData:
        disks_data = [
            {
                "mountpoint": d.mountpoint,
                "used": format_bytes(d.used_bytes),
                "total": format_bytes(d.total_bytes),
                "free": format_bytes(d.free_bytes),
                "percent": format_percent(d.percent),
            }
            for d in snapshot.disks
        ]

        issues_data = [
            {
                "category": iss.category.value,
                "severity": iss.severity.value,
                "title": iss.title,
                "summary": iss.summary,
                "evidence": iss.evidence,
                "recommendation": iss.recommendation,
            }
            for iss in diag_report.issues
        ]

        recs = [iss.recommendation for iss in diag_report.issues]

        temp_status = (
            f"{snapshot.temperature.temperature_celsius:.1f}°C ({snapshot.temperature.sensor_name})"
            if snapshot.temperature.available and snapshot.temperature.temperature_celsius is not None
            else snapshot.temperature.status_message
        )

        boost_data = None
        if latest_boost_result:
            boost_data = {
                "timestamp": format_timestamp(latest_boost_result.timestamp),
                "actions": latest_boost_result.actions_executed,
                "ram_before": format_percent(latest_boost_result.ram_before_percent),
                "ram_after": format_percent(latest_boost_result.ram_after_percent),
                "working_set_trimmed": format_bytes(latest_boost_result.working_set_trimmed_bytes),
                "memory_freed": format_bytes(latest_boost_result.memory_freed_bytes),
                "bytes_recycled": format_bytes(latest_boost_result.bytes_recycled),
                "disk_freed": format_bytes(latest_boost_result.disk_freed_bytes),
                "details": latest_boost_result.details,
            }

        return HealthReportData(
            generated_at=format_timestamp(),
            hostname=snapshot.host_name,
            os_name=snapshot.os_name,
            uptime=format_duration(snapshot.uptime_seconds),
            health_score=diag_report.overall_score,
            health_status=diag_report.overall_status,
            cpu_percent=snapshot.cpu_percent_total,
            ram_used_bytes=snapshot.ram_used_bytes,
            ram_total_bytes=snapshot.ram_total_bytes,
            ram_percent=snapshot.ram_percent,
            temperature_status=temp_status,
            disks_summary=disks_data,
            issues=issues_data,
            recommendations=recs,
            healthy_aspects=diag_report.healthy_checks,
            recent_boost_metrics=boost_data,
        )

    def to_markdown(self, data: HealthReportData) -> str:
        """Format health report as structured Markdown."""
        lines = [
            "# SystemCare — PC Health & Performance Audit Report",
            f"**Generated:** {data.generated_at} | **Host:** {data.hostname} | **OS:** {data.os_name} | **Uptime:** {data.uptime}",
            "",
            f"## Overall System Health Score: **{data.health_score}/100** ({data.health_status})",
            "",
            "### 1. Live Resource Baseline",
            f"- **CPU Utilization:** {format_percent(data.cpu_percent)}",
            f"- **Physical Memory:** {format_percent(data.ram_percent)} ({format_bytes(data.ram_used_bytes)} / {format_bytes(data.ram_total_bytes)})",
            f"- **Hardware Thermal Status:** {data.temperature_status}",
            "",
            "#### Storage Partitions:",
        ]

        for d in data.disks_summary:
            lines.append(f"- Drive **{d['mountpoint']}**: {d['used']} used of {d['total']} ({d['free']} free, {d['percent']} utilized)")

        lines.extend(["", "### 2. Detected Performance Issues & Bottlenecks"])
        if data.issues:
            for idx, iss in enumerate(data.issues, start=1):
                lines.extend([
                    f"#### {idx}. [{iss['severity'].upper()}] {iss['title']} ({iss['category']})",
                    f"- **Summary:** {iss['summary']}",
                    f"- **Observed Evidence:** {iss['evidence']}",
                    f"- **Recommended Fix:** {iss['recommendation']}",
                    "",
                ])
        else:
            lines.append("No critical issues or performance bottlenecks detected. System is running cleanly.")

        if data.healthy_aspects:
            lines.extend(["", "### 3. Verified Healthy System Subsystems"])
            for h in data.healthy_aspects:
                lines.append(f"- [x] {h}")

        if data.recent_boost_metrics:
            b = data.recent_boost_metrics
            lines.extend([
                "",
                "### 4. Recent Optimization (Before & After Metrics)",
                f"- **Optimization Run at:** {b['timestamp']}",
                f"- **RAM Utilization:** {b['ram_before']} -> **{b['ram_after']}**",
                f"- **Working Sets Trimmed:** {b.get('working_set_trimmed', '0 B')} (unreferenced pages moved to standby)",
                f"- **Available RAM Delta:** {b['memory_freed']}",
                f"- **Files Sent to Recycle Bin:** {b.get('bytes_recycled', '0 B')}",
                f"- **Actual Physical Disk Space Freed:** {b['disk_freed']}",
                "- **Executed Actions:**",
            ])
            for act in b["actions"]:
                lines.append(f"  - {act}")

        lines.extend([
            "",
            "---",
            "*Report generated locally by SystemCare PC Health & Performance Optimizer. No personal data was collected or transmitted.*",
        ])

        return "\n".join(lines)

    def export_report(self, data: HealthReportData, export_path: str, format_type: str = "markdown") -> bool:
        """
        Export report to a validated file path.
        Validates path security and handles write errors gracefully.
        """
        if not export_path:
            return False

        try:
            norm_dest = os.path.normpath(os.path.abspath(export_path))

            # Protect writing into critical system directories
            win_root = os.environ.get("SystemRoot", r"C:\Windows")
            if norm_dest.lower().startswith(win_root.lower() + "\\"):
                return False

            os.makedirs(os.path.dirname(norm_dest), exist_ok=True)
            if format_type.lower() == "json":
                with open(norm_dest, "w", encoding="utf-8") as f:
                    json.dump(asdict(data), f, indent=2)
            else:
                md_content = self.to_markdown(data)
                with open(norm_dest, "w", encoding="utf-8") as f:
                    f.write(md_content)
            return True
        except Exception:
            return False
