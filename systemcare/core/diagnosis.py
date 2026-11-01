"""
Performance Diagnosis Engine.
Analyzes real-time metrics, memory pressure, disk bottlenecks, and thermal factors
to identify performance issues and generate simple, evidence-based recommendations.
"""

from dataclasses import dataclass
from enum import Enum
from typing import Dict, List, Optional

from ..utils.formatters import format_bytes, format_percent
from .monitor import SystemSnapshot


class DiagnosticSeverity(str, Enum):
    HEALTHY = "Healthy"
    INFO = "Info"
    WARNING = "Warning"
    CRITICAL = "Critical"


class DiagnosticCategory(str, Enum):
    CPU = "CPU & Processor"
    MEMORY = "Memory & RAM"
    DISK = "Storage & Disks"
    THERMAL = "Thermal & Cooling"
    BACKGROUND = "Background Tasks"


@dataclass
class DiagnosticIssue:
    id: str
    category: DiagnosticCategory
    severity: DiagnosticSeverity
    title: str
    summary: str
    evidence: str
    recommendation: str


@dataclass
class DiagnosticReport:
    overall_score: int  # 0 to 100
    overall_status: str  # Excellent, Good, Fair, Needs Attention
    issues: List[DiagnosticIssue]
    healthy_checks: List[str]
    timestamp: float


class PerformanceDiagnosis:
    """
    Evaluates system metrics and processes against evidence-based performance thresholds.
    """

    def __init__(
        self,
        cpu_warning_threshold: float = 75.0,
        cpu_critical_threshold: float = 90.0,
        ram_warning_threshold: float = 80.0,
        ram_critical_threshold: float = 90.0,
        disk_free_warning_percent: float = 15.0,
        disk_free_critical_percent: float = 8.0,
    ) -> None:
        self.cpu_warn = cpu_warning_threshold
        self.cpu_crit = cpu_critical_threshold
        self.ram_warn = ram_warning_threshold
        self.ram_crit = ram_critical_threshold
        self.disk_warn = disk_free_warning_percent
        self.disk_crit = disk_free_critical_percent

    def evaluate(
        self,
        snapshot: SystemSnapshot,
        top_cpu_processes: Optional[List[Dict]] = None,
        top_ram_processes: Optional[List[Dict]] = None,
    ) -> DiagnosticReport:
        """
        Run diagnosis on the provided system snapshot and process lists.
        """
        issues: List[DiagnosticIssue] = []
        healthy: List[str] = []
        deductions = 0

        # --- 1. CPU Diagnosis ---
        cpu_val = snapshot.cpu_percent_total
        top_cpu_str = self._format_process_summary(top_cpu_processes, "cpu_percent", "%")

        if cpu_val >= self.cpu_crit:
            deductions += 30
            issues.append(
                DiagnosticIssue(
                    id="cpu_critical",
                    category=DiagnosticCategory.CPU,
                    severity=DiagnosticSeverity.CRITICAL,
                    title="Extreme CPU Utilization",
                    summary="Your processor is working near maximum capacity, which can cause system stutter and slow application responses.",
                    evidence=f"Total CPU usage is at {format_percent(cpu_val)}. Top consumers: {top_cpu_str or 'Various background tasks'}.",
                    recommendation="Review the Background App Manager to identify hung or runaway tasks and safely close unnecessary apps.",
                )
            )
        elif cpu_val >= self.cpu_warn:
            deductions += 15
            issues.append(
                DiagnosticIssue(
                    id="cpu_warning",
                    category=DiagnosticCategory.CPU,
                    severity=DiagnosticSeverity.WARNING,
                    title="Elevated CPU Activity",
                    summary="CPU activity is higher than normal for standard desktop use.",
                    evidence=f"Total CPU usage is at {format_percent(cpu_val)}. Primary tasks: {top_cpu_str or 'Active processes'}.",
                    recommendation="Close intensive background tabs or render tasks when not actively in use.",
                )
            )
        else:
            healthy.append(f"CPU load is normal and responsive ({format_percent(cpu_val)} utilization).")

        # --- 2. Memory / RAM Pressure ---
        ram_pct = snapshot.ram_percent
        top_ram_str = self._format_process_summary(top_ram_processes, "memory_mb", "MB")

        if ram_pct >= self.ram_crit:
            deductions += 30
            issues.append(
                DiagnosticIssue(
                    id="ram_critical",
                    category=DiagnosticCategory.MEMORY,
                    severity=DiagnosticSeverity.CRITICAL,
                    title="Severe Memory Pressure",
                    summary="Physical memory is almost full. Windows is forced to swap memory to disk, causing noticeable lag and app freeze.",
                    evidence=f"RAM usage is {format_percent(ram_pct)} ({format_bytes(snapshot.ram_used_bytes)} used of {format_bytes(snapshot.ram_total_bytes)}). Top memory users: {top_ram_str or 'System applications'}.",
                    recommendation="Use Safe Boost Mode to trim unneeded working sets or close memory-heavy web browser tabs.",
                )
            )
        elif ram_pct >= self.ram_warn:
            deductions += 15
            issues.append(
                DiagnosticIssue(
                    id="ram_warning",
                    category=DiagnosticCategory.MEMORY,
                    severity=DiagnosticSeverity.WARNING,
                    title="High Memory Usage",
                    summary="More than 80% of RAM is occupied, leaving limited headroom for opening new applications.",
                    evidence=f"RAM usage is {format_percent(ram_pct)} with only {format_bytes(snapshot.ram_available_bytes)} available. Top consumers: {top_ram_str or 'Active processes'}.",
                    recommendation="Consider running Safe Boost Mode to release standby memory or close idle background programs.",
                )
            )
        else:
            healthy.append(
                f"Memory is well-balanced ({format_percent(ram_pct)} used, {format_bytes(snapshot.ram_available_bytes)} free headroom)."
            )

        # Pagefile / Swap Check
        if snapshot.swap_percent > 80.0 and snapshot.swap_total_bytes > 0:
            deductions += 10
            issues.append(
                DiagnosticIssue(
                    id="swap_high",
                    category=DiagnosticCategory.MEMORY,
                    severity=DiagnosticSeverity.WARNING,
                    title="Heavy Virtual Memory Paging",
                    summary="Windows paging file is heavily utilized, which increases SSD wear and slows down window switching.",
                    evidence=f"Pagefile utilization is at {format_percent(snapshot.swap_percent)} ({format_bytes(snapshot.swap_used_bytes)}).",
                    recommendation="Freeing up physical RAM will immediately alleviate pagefile thrashing.",
                )
            )

        # --- 3. Disk Space & Bottlenecks ---
        disk_issues_found = False
        for disk in snapshot.disks:
            free_pct = (disk.free_bytes / max(1, disk.total_bytes)) * 100.0
            if free_pct <= self.disk_crit or disk.free_bytes < 10 * 1024 * 1024 * 1024:  # < 10 GB
                deductions += 20
                disk_issues_found = True
                issues.append(
                    DiagnosticIssue(
                        id=f"disk_critical_{disk.mountpoint.replace(':', '')}",
                        category=DiagnosticCategory.DISK,
                        severity=DiagnosticSeverity.CRITICAL,
                        title=f"Critically Low Storage on Drive {disk.mountpoint}",
                        summary=f"Drive {disk.mountpoint} has less than {format_percent(free_pct)} free space. Windows requires at least 15 GB for temporary caches, virtual memory paging, and updates.",
                        evidence=f"Only {format_bytes(disk.free_bytes)} free remaining out of {format_bytes(disk.total_bytes)} ({format_percent(disk.percent)} used).",
                        recommendation="Run the Storage Analyzer to safely clean temporary caches and use the Duplicate File Finder to reclaim space.",
                    )
                )
            elif free_pct <= self.disk_warn:
                deductions += 10
                disk_issues_found = True
                issues.append(
                    DiagnosticIssue(
                        id=f"disk_warning_{disk.mountpoint.replace(':', '')}",
                        category=DiagnosticCategory.DISK,
                        severity=DiagnosticSeverity.WARNING,
                        title=f"Low Storage Headroom on Drive {disk.mountpoint}",
                        summary=f"Drive {disk.mountpoint} is filling up ({format_percent(disk.percent)} used).",
                        evidence=f"{format_bytes(disk.free_bytes)} remaining available.",
                        recommendation="Review large files and old downloads in Storage Analyzer before space becomes critical.",
                    )
                )

        if not disk_issues_found and snapshot.disks:
            healthy.append(f"Storage partitions have healthy free headroom across all {len(snapshot.disks)} drives.")

        # --- 4. Thermal & Overheating Analysis ---
        temp_info = snapshot.temperature
        if temp_info.available and temp_info.temperature_celsius is not None:
            t_val = temp_info.temperature_celsius
            if t_val >= 90.0:
                deductions += 25
                issues.append(
                    DiagnosticIssue(
                        id="thermal_critical",
                        category=DiagnosticCategory.THERMAL,
                        severity=DiagnosticSeverity.CRITICAL,
                        title="High CPU Temperature Detected",
                        summary="Processor thermal sensors indicate near-throttle temperatures.",
                        evidence=f"Current reading: {t_val:.1f}°C from {temp_info.sensor_name}.",
                        recommendation="Ensure laptop cooling vents are completely unobstructed. Place laptop on a hard flat surface.",
                    )
                )
            elif t_val >= 80.0:
                deductions += 10
                issues.append(
                    DiagnosticIssue(
                        id="thermal_warning",
                        category=DiagnosticCategory.THERMAL,
                        severity=DiagnosticSeverity.WARNING,
                        title="Elevated CPU Temperature",
                        summary="CPU is running warm under sustained workload.",
                        evidence=f"Current reading: {t_val:.1f}°C from {temp_info.sensor_name}.",
                        recommendation="Avoid running multiple high-load applications simultaneously on battery power.",
                    )
                )
            else:
                healthy.append(f"CPU temperature is within optimal thermal limits ({t_val:.1f}°C).")
        else:
            # When direct sensor is unavailable, diagnose potential overheating causes via sustained CPU
            if cpu_val >= 85.0:
                issues.append(
                    DiagnosticIssue(
                        id="thermal_suspect",
                        category=DiagnosticCategory.THERMAL,
                        severity=DiagnosticSeverity.INFO,
                        title="High Sustained Load (Potential Thermal Build-up)",
                        summary="Direct thermal sensor is not accessible via Windows user APIs, but sustained 85%+ CPU utilization naturally generates heat in laptop chassis.",
                        evidence=f"Current continuous CPU usage: {format_percent(cpu_val)}.",
                        recommendation="Keep laptop intake vents elevated on a hard desk to maintain optimal airflow.",
                    )
                )
            else:
                healthy.append("Moderate workload indicates healthy thermal conditions (low heat generation).")

        # --- Calculate Health Score ---
        score = max(10, min(100, 100 - deductions))
        if score >= 90:
            status = "Excellent"
        elif score >= 75:
            status = "Good"
        elif score >= 55:
            status = "Fair"
        else:
            status = "Needs Attention"

        return DiagnosticReport(
            overall_score=score,
            overall_status=status,
            issues=issues,
            healthy_checks=healthy,
            timestamp=snapshot.timestamp,
        )

    def _format_process_summary(
        self, procs: Optional[List[Dict]], metric_key: str, unit: str
    ) -> str:
        if not procs:
            return ""
        items = []
        for p in procs[:3]:
            name = p.get("name", "Unknown")
            val = p.get(metric_key, 0)
            if unit == "%":
                items.append(f"{name} ({val:.1f}%)")
            elif unit == "MB":
                items.append(f"{name} ({val:.0f} MB)")
            else:
                items.append(f"{name} ({val})")
        return ", ".join(items)
