"""
Core modules for SystemCare PC Health & Performance Optimizer.
"""

from .boost_engine import BoostAction, BoostResult, SafeBoostEngine
from .diagnosis import (
    DiagnosticCategory,
    DiagnosticIssue,
    DiagnosticReport,
    DiagnosticSeverity,
    PerformanceDiagnosis,
)
from .duplicate_finder import (
    DuplicateCleanupResult,
    DuplicateFileEntry,
    DuplicateFinder,
    DuplicateGroup,
)
from .monitor import (
    DiskUsageInfo,
    HardwareTemperatureInfo,
    SystemMonitor,
    SystemSnapshot,
)
from .process_manager import ProcessInfo, ProcessManager
from .report_generator import HealthReportData, HealthReportGenerator
from .startup_manager import StartupItem, StartupManager
from .storage_analyzer import (
    CleanableGroup,
    LargeFileItem,
    StorageAnalysisResult,
    StorageAnalyzer,
    StorageCleanupResult,
)

__all__ = [
    "SystemMonitor",
    "SystemSnapshot",
    "DiskUsageInfo",
    "HardwareTemperatureInfo",
    "PerformanceDiagnosis",
    "DiagnosticReport",
    "DiagnosticIssue",
    "DiagnosticSeverity",
    "DiagnosticCategory",
    "ProcessManager",
    "ProcessInfo",
    "StartupManager",
    "StartupItem",
    "DuplicateFinder",
    "DuplicateGroup",
    "DuplicateFileEntry",
    "DuplicateCleanupResult",
    "StorageAnalyzer",
    "StorageAnalysisResult",
    "LargeFileItem",
    "CleanableGroup",
    "StorageCleanupResult",
    "SafeBoostEngine",
    "BoostAction",
    "BoostResult",
    "HealthReportGenerator",
    "HealthReportData",
]
