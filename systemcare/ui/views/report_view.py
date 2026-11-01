"""
Health Reports View.
Generates comprehensive diagnostic audit reports detailing detected issues,
likely causes, evidence, recommended fixes, and before/after resource metrics.
Supports exporting to Markdown and JSON formats.
"""

from typing import Optional
import tkinter.filedialog as filedialog
import tkinter.messagebox as msgbox
import customtkinter as ctk

from ...core.boost_engine import BoostResult
from ...core.diagnosis import PerformanceDiagnosis
from ...core.monitor import SystemMonitor
from ...core.process_manager import ProcessManager
from ...core.report_generator import HealthReportData, HealthReportGenerator
from ..theme import (
    FONT_BIG_NUMBER,
    FONT_BODY,
    FONT_BODY_BOLD,
    FONT_MONO,
    FONT_SMALL,
    FONT_SUBTITLE,
    FONT_TITLE,
)


class ReportView(ctk.CTkScrollableFrame):
    """
    Health report view displaying full audit and export capabilities.
    """

    def __init__(
        self,
        master,
        monitor: SystemMonitor,
        process_manager: Optional[ProcessManager] = None,
        latest_boost_result: Optional[BoostResult] = None,
        **kwargs,
    ):
        super().__init__(master, fg_color="transparent", **kwargs)
        self.monitor = monitor
        self.process_manager = process_manager or ProcessManager()
        self.latest_boost_result = latest_boost_result
        self.generator = HealthReportGenerator()
        self.diag_engine = PerformanceDiagnosis()
        self.current_report_data: Optional[HealthReportData] = None

        self._build_header()
        self._build_content_area()
        self.generate_report()

    def _build_header(self) -> None:
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.pack(fill="x", padx=16, pady=(12, 10))

        title = ctk.CTkLabel(header, text="System Reports", font=FONT_TITLE, anchor="w")
        title.pack(side="left")

        btn_box = ctk.CTkFrame(header, fg_color="transparent")
        btn_box.pack(side="right")

        btn_gen = ctk.CTkButton(
            btn_box,
            text="Update Report",
            font=FONT_BODY,
            width=115,
            height=32,
            corner_radius=6,
            fg_color=("#0066cc", "#2563eb"),
            hover_color=("#0052a3", "#1d4ed8"),
            command=self.generate_report,
        )
        btn_gen.pack(side="left", padx=(0, 8))

        btn_exp_md = ctk.CTkButton(
            btn_box,
            text="Export as Markdown",
            font=FONT_BODY,
            width=135,
            height=32,
            corner_radius=6,
            fg_color=("#f3f4f6", "#2a2e35"),
            text_color=("#111827", "#f3f4f6"),
            hover_color=("#e5e7eb", "#323740"),
            command=lambda: self._export_report("markdown"),
        )
        btn_exp_md.pack(side="left", padx=(0, 8))

        btn_exp_json = ctk.CTkButton(
            btn_box,
            text="Export as JSON",
            font=FONT_BODY,
            width=110,
            height=32,
            corner_radius=6,
            fg_color=("#f3f4f6", "#2a2e35"),
            text_color=("#111827", "#f3f4f6"),
            hover_color=("#e5e7eb", "#323740"),
            command=lambda: self._export_report("json"),
        )
        btn_exp_json.pack(side="left")

    def _build_content_area(self) -> None:
        self.content_container = ctk.CTkFrame(self, fg_color="transparent")
        self.content_container.pack(fill="both", expand=True, padx=16, pady=(0, 20))

    def set_latest_boost_result(self, result: BoostResult) -> None:
        self.latest_boost_result = result
        self.generate_report()

    def generate_report(self) -> None:
        """Collect metrics and render fresh report."""
        snap = self.monitor.get_latest_snapshot()
        top_cpu = self.process_manager.get_top_cpu_processes(limit=3)
        top_ram = self.process_manager.get_top_ram_processes(limit=3)
        diag = self.diag_engine.evaluate(snap, top_cpu, top_ram)

        data = self.generator.build_report_data(
            snapshot=snap,
            diag_report=diag,
            latest_boost_result=self.latest_boost_result,
        )
        self.current_report_data = data
        self._render_report(data)

    def _render_report(self, data: HealthReportData) -> None:
        for child in self.content_container.winfo_children():
            child.destroy()

        # 1. Summary Card
        card = ctk.CTkFrame(
            self.content_container,
            corner_radius=6,
            fg_color=("#ffffff", "#22252a"),
            border_width=1,
            border_color=("#e5e7eb", "#2e3440"),
        )
        card.pack(fill="x", pady=(0, 12))

        inner = ctk.CTkFrame(card, fg_color="transparent")
        inner.pack(fill="x", padx=18, pady=16)

        score_color = "#16a34a" if data.health_score >= 85 else "#d97706" if data.health_score >= 60 else "#dc2626"

        score_box = ctk.CTkFrame(inner, fg_color="transparent")
        score_box.pack(side="left", padx=(0, 20))

        ctk.CTkLabel(score_box, text=f"{data.health_score}/100", font=FONT_BIG_NUMBER, text_color=score_color).pack()
        ctk.CTkLabel(score_box, text=data.health_status.upper(), font=FONT_SMALL, text_color=score_color).pack()

        info_box = ctk.CTkFrame(inner, fg_color="transparent")
        info_box.pack(side="left", fill="both", expand=True)

        ctk.CTkLabel(
            info_box, text=f"System Health Report — {data.hostname}", font=FONT_SUBTITLE, anchor="w"
        ).pack(anchor="w")

        meta_text = (
            f"Generated: {data.generated_at} | OS: {data.os_name} | System Uptime: {data.uptime}\n"
            f"CPU: {data.cpu_percent:.1f}% | Memory: {data.ram_percent:.1f}% | Thermal: {data.temperature_status}"
        )
        ctk.CTkLabel(info_box, text=meta_text, font=FONT_SMALL, text_color=("#6b7280", "#9ca3af"), anchor="w", justify="left").pack(
            anchor="w", pady=(4, 0)
        )

        # 2. Before / After Optimization Snapshot (If available)
        if data.recent_boost_metrics:
            b = data.recent_boost_metrics
            b_card = ctk.CTkFrame(
                self.content_container,
                corner_radius=6,
                fg_color=("#ffffff", "#22252a"),
                border_width=1,
                border_color=("#e5e7eb", "#2e3440"),
            )
            b_card.pack(fill="x", pady=(0, 12))

            b_inner = ctk.CTkFrame(b_card, fg_color="transparent")
            b_inner.pack(fill="x", padx=18, pady=14)

            ctk.CTkLabel(b_inner, text="Optimization Impact", font=FONT_SUBTITLE).pack(
                anchor="w", pady=(0, 6)
            )

            b_stats = ctk.CTkLabel(
                b_inner,
                text=(
                    f"Timestamp: {b['timestamp']} | RAM: {b['ram_before']} ➔ {b['ram_after']} | "
                    f"Available RAM Delta: {b['memory_freed']} | Disk Reclaimed: {b['disk_freed']}"
                ),
                font=FONT_BODY_BOLD,
                text_color=("#16a34a", "#22c55e"),
                anchor="w",
            )
            b_stats.pack(anchor="w", pady=(0, 4))

            for act in b["actions"]:
                ctk.CTkLabel(b_inner, text=f"  ✔ {act}", font=FONT_SMALL, text_color=("#6b7280", "#9ca3af"), anchor="w").pack(
                    anchor="w"
                )

        # 3. Detected Issues & Recommendations
        issues_card = ctk.CTkFrame(
            self.content_container,
            corner_radius=6,
            fg_color=("#ffffff", "#22252a"),
            border_width=1,
            border_color=("#e5e7eb", "#2e3440"),
        )
        issues_card.pack(fill="x", pady=(0, 12))

        i_inner = ctk.CTkFrame(issues_card, fg_color="transparent")
        i_inner.pack(fill="x", padx=18, pady=14)

        ctk.CTkLabel(
            i_inner,
            text=f"Detected Issues & Recommendations ({len(data.issues)})",
            font=FONT_SUBTITLE,
            anchor="w",
        ).pack(anchor="w", pady=(0, 8))

        if not data.issues:
            ctk.CTkLabel(
                i_inner,
                text="✔ No performance bottlenecks detected. System is operating cleanly.",
                font=FONT_BODY,
                text_color=("#16a34a", "#22c55e"),
                anchor="w",
            ).pack(anchor="w")
        else:
            for idx, iss in enumerate(data.issues, start=1):
                i_box = ctk.CTkFrame(i_inner, fg_color=("#f9fafb", "#1e222a"), corner_radius=4)
                i_box.pack(fill="x", pady=4)

                ib_inner = ctk.CTkFrame(i_box, fg_color="transparent")
                ib_inner.pack(fill="x", padx=12, pady=10)

                ctk.CTkLabel(
                    ib_inner,
                    text=f"{idx}. [{iss['severity'].upper()}] {iss['title']} ({iss['category']})",
                    font=FONT_BODY_BOLD,
                    anchor="w",
                ).pack(anchor="w")

                ctk.CTkLabel(
                    ib_inner,
                    text=f"Summary: {iss['summary']}\nEvidence: {iss['evidence']}",
                    font=FONT_SMALL,
                    text_color=("#4b5563", "#9ca3af"),
                    anchor="w",
                    justify="left",
                ).pack(anchor="w", pady=(2, 4))

                ctk.CTkLabel(
                    ib_inner,
                    text=f"Recommendation: {iss['recommendation']}",
                    font=FONT_SMALL,
                    text_color=("#16a34a", "#22c55e"),
                    anchor="w",
                ).pack(anchor="w")

        # 4. Storage Summary
        storage_card = ctk.CTkFrame(
            self.content_container,
            corner_radius=6,
            fg_color=("#ffffff", "#22252a"),
            border_width=1,
            border_color=("#e5e7eb", "#2e3440"),
        )
        storage_card.pack(fill="x", pady=(0, 12))

        s_inner = ctk.CTkFrame(storage_card, fg_color="transparent")
        s_inner.pack(fill="x", padx=18, pady=14)

        ctk.CTkLabel(s_inner, text="Storage Drive Partitions", font=FONT_SUBTITLE, anchor="w").pack(
            anchor="w", pady=(0, 6)
        )

        for d in data.disks_summary:
            ctk.CTkLabel(
                s_inner,
                text=f"Drive {d['mountpoint']}: {d['used']} used of {d['total']} ({d['free']} free, {d['percent']} utilized)",
                font=FONT_BODY,
                text_color=("#4b5563", "#9ca3af"),
                anchor="w",
            ).pack(anchor="w", pady=1)

    def _export_report(self, format_type: str) -> None:
        if not self.current_report_data:
            return

        ext = ".md" if format_type == "markdown" else ".json"
        ftypes = [("Markdown Files", "*.md")] if format_type == "markdown" else [("JSON Files", "*.json")]

        save_path = filedialog.asksaveasfilename(
            defaultextension=ext,
            filetypes=ftypes,
            initialfile=f"systemcare_health_report_{self.current_report_data.hostname.lower()}{ext}",
        )
        if not save_path:
            return

        success = self.generator.export_report(self.current_report_data, save_path, format_type=format_type)
        if success:
            msgbox.showinfo("Report Exported", f"Health report successfully saved to:\n{save_path}")
        else:
            msgbox.showerror("Export Failed", "Could not write report to specified file.")
