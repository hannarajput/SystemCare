"""UI Views for SystemCare."""

from .boost_view import BoostView
from .dashboard_view import DashboardView
from .diagnosis_view import DiagnosisView
from .duplicate_view import DuplicateView
from .process_view import ProcessView
from .report_view import ReportView
from .settings_view import SettingsView
from .startup_view import StartupView
from .storage_view import StorageView

__all__ = [
    "DashboardView",
    "DiagnosisView",
    "ProcessView",
    "StartupView",
    "DuplicateView",
    "StorageView",
    "BoostView",
    "ReportView",
    "SettingsView",
]
