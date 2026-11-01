"""
Main Application Window for SystemCare.
Features a fluent sidebar navigation, view router, live background monitoring hook,
and graceful application lifecycle management.
"""

from typing import Dict, Optional
import customtkinter as ctk

from ..core.boost_engine import BoostResult, SafeBoostEngine
from ..core.monitor import SystemMonitor, SystemSnapshot
from ..core.process_manager import ProcessManager
from ..core.startup_manager import StartupManager
from ..utils.formatters import format_percent
from ..utils.logger import logger
from .theme import (
    FONT_BODY,
    FONT_BODY_BOLD,
    FONT_SMALL,
    FONT_SUBTITLE,
    FONT_TITLE,
)
from .views.boost_view import BoostView
from .views.dashboard_view import DashboardView
from .views.diagnosis_view import DiagnosisView
from .views.duplicate_view import DuplicateView
from .views.process_view import ProcessView
from .views.report_view import ReportView
from .views.settings_view import SettingsView
from .views.startup_view import StartupView
from .views.storage_view import StorageView


class SystemCareApp(ctk.CTk):
    """
    Main application shell for SystemCare.
    """

    def __init__(self) -> None:
        super().__init__()

        # Window Configuration
        self.title("SystemCare — PC Health & Performance Optimizer")
        self.geometry("1180x760")
        self.minsize(980, 620)
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")

        # Initialize Core Services
        self.monitor = SystemMonitor(interval_seconds=1.5)
        self.process_manager = ProcessManager()
        self.startup_manager = StartupManager()
        self.boost_engine = SafeBoostEngine(self.monitor)
        self.latest_boost_result: Optional[BoostResult] = None

        # Build Layout
        self._build_layout()

        # Connect live monitoring callback
        self.monitor.add_listener(self._on_monitor_snapshot)
        self.monitor.start()

        # Hook window close event
        self.protocol("WM_DELETE_WINDOW", self.on_closing)

        # Show Dashboard initially
        self.navigate_to("dashboard")

    def _build_layout(self) -> None:
        # Layout: Grid with Sidebar (col 0) and Content (col 1)
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=1)

        self._build_sidebar()
        self._build_content_area()

    def _build_sidebar(self) -> None:
        self.sidebar = ctk.CTkFrame(self, width=220, corner_radius=0, fg_color=("#f0f2f5", "#141619"))
        self.sidebar.grid(row=0, column=0, sticky="nsew")
        self.sidebar.grid_rowconfigure(10, weight=1)

        # Brand Header
        brand_box = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        brand_box.pack(fill="x", padx=16, pady=(18, 14))

        logo_row = ctk.CTkFrame(brand_box, fg_color="transparent")
        logo_row.pack(anchor="w")

        brand_badge = ctk.CTkLabel(
            logo_row,
            text=" SC ",
            font=(FONT_BODY_BOLD[0], 11, "bold"),
            fg_color=("#0066cc", "#2563eb"),
            text_color="#ffffff",
            corner_radius=4,
        )
        brand_badge.pack(side="left", padx=(0, 10))

        brand_title = ctk.CTkLabel(logo_row, text="SystemCare", font=FONT_TITLE)
        brand_title.pack(side="left")

        brand_sub = ctk.CTkLabel(
            brand_box, text="PC Health & Performance", font=FONT_SMALL, text_color=("#6b7280", "#9ca3af")
        )
        brand_sub.pack(anchor="w", padx=(34, 0), pady=(1, 0))

        # Nav Buttons Container
        self.nav_buttons: Dict[str, ctk.CTkButton] = {}

        nav_items = [
            ("dashboard", "⊞  Overview"),
            ("diagnosis", "♥  System Health"),
            ("boost", "⚡  Safe Boost"),
            ("processes", "≡  Running Apps"),
            ("startup", "▶  Startup Apps"),
            ("duplicate", "⧉  Duplicate Files"),
            ("storage", "⛁  Storage Analyzer"),
            ("reports", "📋  Health Reports"),
            ("settings", "⚙  Settings & Logs"),
        ]

        for key, label in nav_items:
            btn = ctk.CTkButton(
                self.sidebar,
                text=label,
                anchor="w",
                font=FONT_BODY,
                height=36,
                corner_radius=6,
                fg_color="transparent",
                text_color=("#374151", "#9ca3af"),
                hover_color=("#e5e7eb", "#222731"),
                command=lambda k=key: self.navigate_to(k),
            )
            btn.pack(fill="x", padx=10, pady=2)
            self.nav_buttons[key] = btn

        # Bottom Sidebar Telemetry Capsule
        self.bottom_telemetry = ctk.CTkFrame(
            self.sidebar,
            fg_color=("#ffffff", "#1e222a"),
            corner_radius=6,
            border_width=1,
            border_color=("#e5e7eb", "#2a2d34"),
        )
        self.bottom_telemetry.pack(side="bottom", fill="x", padx=10, pady=16)

        self.lbl_side_cpu = ctk.CTkLabel(
            self.bottom_telemetry,
            text="CPU: 0.0%",
            font=FONT_SMALL,
            text_color=("#4b5563", "#9ca3af"),
            anchor="w",
        )
        self.lbl_side_cpu.pack(fill="x", padx=10, pady=(6, 2))

        self.lbl_side_ram = ctk.CTkLabel(
            self.bottom_telemetry,
            text="RAM: 0.0%",
            font=FONT_SMALL,
            text_color=("#4b5563", "#9ca3af"),
            anchor="w",
        )
        self.lbl_side_ram.pack(fill="x", padx=10, pady=(2, 6))

    def _build_content_area(self) -> None:
        self.content_frame = ctk.CTkFrame(self, fg_color=("#f8f9fa", "#1a1c20"), corner_radius=0)
        self.content_frame.grid(row=0, column=1, sticky="nsew")
        self.content_frame.grid_rowconfigure(0, weight=1)
        self.content_frame.grid_columnconfigure(0, weight=1)

        # Lazy views dictionary
        self.views: Dict[str, ctk.CTkFrame] = {}

    def navigate_to(self, view_key: str) -> None:
        """Switch current active view."""
        # Update sidebar button highlight
        for k, btn in self.nav_buttons.items():
            if k == view_key:
                btn.configure(
                    fg_color=("#e0edff", "#1e293b"),
                    text_color=("#0066cc", "#38bdf8"),
                    font=FONT_BODY_BOLD,
                )
            else:
                btn.configure(
                    fg_color="transparent",
                    text_color=("#374151", "#9ca3af"),
                    font=FONT_BODY,
                )

        # Lazy instantiate view if needed
        is_new_view = view_key not in self.views
        if is_new_view:
            view = self._create_view(view_key)
            self.views[view_key] = view

        # Hide all views and show target view
        for v in self.views.values():
            v.grid_forget()

        target_view = self.views[view_key]
        target_view.grid(row=0, column=0, sticky="nsew")

        # View specific refresh triggers (only when switching back to existing views)
        if not is_new_view:
            if view_key == "diagnosis" and hasattr(target_view, "refresh_diagnosis"):
                target_view.refresh_diagnosis()
            elif view_key == "processes" and hasattr(target_view, "refresh_process_list"):
                target_view.refresh_process_list()
            elif view_key == "startup" and hasattr(target_view, "refresh_startup_items"):
                target_view.refresh_startup_items()
            elif view_key == "boost" and hasattr(target_view, "refresh_analysis"):
                target_view.refresh_analysis()
            elif view_key == "reports" and hasattr(target_view, "generate_report"):
                target_view.generate_report()
            elif view_key == "settings" and hasattr(target_view, "refresh_logs"):
                target_view.refresh_logs()

    def _create_view(self, key: str) -> ctk.CTkFrame:
        if key == "dashboard":
            return DashboardView(
                self.content_frame,
                monitor=self.monitor,
                on_navigate=self.navigate_to,
            )
        elif key == "diagnosis":
            return DiagnosisView(
                self.content_frame,
                monitor=self.monitor,
                process_manager=self.process_manager,
                on_navigate=self.navigate_to,
            )
        elif key == "boost":
            return BoostView(
                self.content_frame,
                monitor=self.monitor,
                boost_engine=self.boost_engine,
                on_boost_completed=self._on_boost_completed,
            )
        elif key == "processes":
            return ProcessView(
                self.content_frame,
                process_manager=self.process_manager,
            )
        elif key == "startup":
            return StartupView(
                self.content_frame,
                startup_manager=self.startup_manager,
            )
        elif key == "duplicate":
            return DuplicateView(self.content_frame)
        elif key == "storage":
            return StorageView(self.content_frame)
        elif key == "reports":
            return ReportView(
                self.content_frame,
                monitor=self.monitor,
                process_manager=self.process_manager,
                latest_boost_result=self.latest_boost_result,
            )
        elif key == "settings":
            return SettingsView(self.content_frame, monitor=self.monitor)

        # Fallback
        return DashboardView(self.content_frame, monitor=self.monitor)

    def _on_monitor_snapshot(self, snapshot: SystemSnapshot) -> None:
        """Thread-safe update handler invoked by SystemMonitor."""
        try:
            if self.winfo_exists():
                self.after(0, lambda: self._apply_snapshot(snapshot))
        except (RuntimeError, Exception):
            pass

    def _apply_snapshot(self, snapshot: SystemSnapshot) -> None:
        try:
            if not self.winfo_exists():
                return
            # Update bottom sidebar telemetry
            self.lbl_side_cpu.configure(text=f"CPU: {format_percent(snapshot.cpu_percent_total)}")
            self.lbl_side_ram.configure(text=f"RAM: {format_percent(snapshot.ram_percent)}")

            # If Dashboard view is mounted, update it
            if "dashboard" in self.views:
                dash = self.views["dashboard"]
                if hasattr(dash, "update_snapshot"):
                    dash.update_snapshot(snapshot)
        except (RuntimeError, Exception):
            pass

    def _on_boost_completed(self, result: BoostResult) -> None:
        self.latest_boost_result = result
        # Update reports view if already created
        if "reports" in self.views:
            rep = self.views["reports"]
            if hasattr(rep, "set_latest_boost_result"):
                rep.set_latest_boost_result(result)

    def on_closing(self) -> None:
        """Gracefully terminate background threads on exit."""
        logger.info("Application exit requested. Cleaning up worker threads...")
        for view_name, view in list(self.views.items()):
            if hasattr(view, "cancel_active_tasks"):
                try:
                    view.cancel_active_tasks()
                except Exception as err:
                    logger.debug(f"Error cancelling tasks for {view_name}: {err}")
        try:
            self.monitor.stop()
        except Exception as err:
            logger.warning(f"Error stopping monitor: {err}")
        self.destroy()
