"""
Performance Diagnosis View.
Presents detailed analysis of CPU bottlenecks, memory pressure, disk constraints,
and thermal factors with simple language explanations and evidence-based recommendations.
"""

from typing import Callable, Optional

import customtkinter as ctk

from ...core.diagnosis import (
    DiagnosticCategory,
    DiagnosticReport,
    DiagnosticSeverity,
    PerformanceDiagnosis,
)
from ...core.monitor import SystemMonitor
from ...core.process_manager import ProcessManager
from ..theme import (
    FONT_BIG_NUMBER,
    FONT_BODY,
    FONT_BODY_BOLD,
    FONT_SMALL,
    FONT_SUBTITLE,
    FONT_TITLE,
)


class DiagnosisView(ctk.CTkScrollableFrame):
    """
    Displays full diagnostic breakdown with issues, evidence, and recommendations.
    """

    def __init__(
        self,
        master,
        monitor: SystemMonitor,
        process_manager: Optional[ProcessManager] = None,
        on_navigate: Optional[Callable[[str], None]] = None,
        **kwargs,
    ):
        super().__init__(master, fg_color="transparent", **kwargs)
        self.monitor = monitor
        self.process_manager = process_manager or ProcessManager()
        self.on_navigate = on_navigate
        self.engine = PerformanceDiagnosis()

        self._build_header()
        self._build_score_banner()
        self._build_sections()
        self.refresh_diagnosis()

    def _build_header(self) -> None:
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.pack(fill="x", padx=16, pady=(12, 12))

        title = ctk.CTkLabel(
            header, text="System Health", font=FONT_TITLE, anchor="w"
        )
        title.pack(side="left")

        self.btn_refresh = ctk.CTkButton(
            header,
            text="Run Check",
            font=FONT_BODY_BOLD,
            width=130,
            height=34,
            corner_radius=6,
            fg_color=("#0066cc", "#2563eb"),
            hover_color=("#0052a3", "#1d4ed8"),
            command=self.refresh_diagnosis,
        )
        self.btn_refresh.pack(side="right")

    def _build_score_banner(self) -> None:
        self.banner = ctk.CTkFrame(
            self,
            corner_radius=6,
            fg_color=("#ffffff", "#22252a"),
            border_width=1,
            border_color=("#e5e7eb", "#2e3440"),
        )
        self.banner.pack(fill="x", padx=16, pady=(0, 12))

        inner = ctk.CTkFrame(self.banner, fg_color="transparent")
        inner.pack(fill="x", padx=18, pady=16)

        score_box = ctk.CTkFrame(inner, fg_color="transparent")
        score_box.pack(side="left", padx=(0, 20))

        self.score_val = ctk.CTkLabel(score_box, text="--", font=FONT_BIG_NUMBER)
        self.score_val.pack()

        score_sub = ctk.CTkLabel(
            score_box, text="OVERALL SCORE", font=FONT_SMALL, text_color=("#6b7280", "#9ca3af")
        )
        score_sub.pack()

        info_box = ctk.CTkFrame(inner, fg_color="transparent")
        info_box.pack(side="left", fill="both", expand=True)

        self.status_title = ctk.CTkLabel(info_box, text="Analyzing...", font=FONT_SUBTITLE, anchor="w")
        self.status_title.pack(anchor="w")

        self.status_summary = ctk.CTkLabel(
            info_box,
            text="Evaluating CPU bottlenecks, memory pressure, storage thresholds, and thermal indicators.",
            font=FONT_BODY,
            text_color=("#4b5563", "#9ca3af"),
            anchor="w",
            wraplength=600,
            justify="left",
        )
        self.status_summary.pack(anchor="w", pady=(3, 0))

    def _build_sections(self) -> None:
        # Container for issues
        self.issues_container = ctk.CTkFrame(self, fg_color="transparent")
        self.issues_container.pack(fill="x", padx=16, pady=(0, 12))

        # Container for healthy aspects
        self.healthy_container = ctk.CTkFrame(
            self,
            corner_radius=6,
            fg_color=("#ffffff", "#22252a"),
            border_width=1,
            border_color=("#e5e7eb", "#2e3440"),
        )
        self.healthy_container.pack(fill="x", padx=16, pady=(0, 16))

    def refresh_diagnosis(self) -> None:
        """Run fresh performance evaluation."""
        snap = self.monitor.get_latest_snapshot()
        top_cpu = self.process_manager.get_top_cpu_processes(limit=3)
        top_ram = self.process_manager.get_top_ram_processes(limit=3)

        report: DiagnosticReport = self.engine.evaluate(snap, top_cpu, top_ram)

        # Update Score Banner
        score_color = (
            "#16a34a"
            if report.overall_score >= 85
            else "#d97706"
            if report.overall_score >= 60
            else "#dc2626"
        )
        self.score_val.configure(
            text=f"{report.overall_score}/100",
            text_color=score_color,
        )
        self.status_title.configure(text=f"Health Status: {report.overall_status}")
        self.status_summary.configure(
            text=f"{len(report.issues)} item(s) require attention. {len(report.healthy_checks)} subsystem(s) confirmed healthy."
        )

        # Render Issues
        for child in self.issues_container.winfo_children():
            child.destroy()

        if not report.issues:
            no_issue_card = ctk.CTkFrame(
                self.issues_container,
                corner_radius=6,
                fg_color=("#ffffff", "#22252a"),
                border_width=1,
                border_color=("#e5e7eb", "#2e3440"),
            )
            no_issue_card.pack(fill="x", pady=4)
            msg = ctk.CTkLabel(
                no_issue_card,
                text="✔ No bottlenecks or resource starvation detected. All subsystems are healthy.",
                font=FONT_BODY_BOLD,
                text_color=("#16a34a", "#22c55e"),
            )
            msg.pack(padx=18, pady=20)
        else:
            for iss in report.issues:
                card = ctk.CTkFrame(
                    self.issues_container,
                    corner_radius=6,
                    fg_color=("#ffffff", "#22252a"),
                    border_width=1,
                    border_color=("#e5e7eb", "#2e3440"),
                )
                card.pack(fill="x", pady=4)

                inner = ctk.CTkFrame(card, fg_color="transparent")
                inner.pack(fill="x", padx=16, pady=12)

                # Header row: category and severity badges
                badge_row = ctk.CTkFrame(inner, fg_color="transparent")
                badge_row.pack(fill="x", pady=(0, 4))

                sev_color = (
                    "#dc2626"
                    if iss.severity == DiagnosticSeverity.CRITICAL
                    else "#d97706"
                    if iss.severity == DiagnosticSeverity.WARNING
                    else "#2563eb"
                )

                sev_badge = ctk.CTkLabel(
                    badge_row,
                    text=f" {iss.severity.value.upper()} ",
                    font=FONT_SMALL,
                    text_color="#ffffff",
                    fg_color=sev_color,
                    corner_radius=4,
                )
                sev_badge.pack(side="left", padx=(0, 6))

                cat_badge = ctk.CTkLabel(
                    badge_row,
                    text=f" {iss.category.value} ",
                    font=FONT_SMALL,
                    text_color=("#4b5563", "#9ca3af"),
                    fg_color=("#f3f4f6", "#2a2e35"),
                    corner_radius=4,
                )
                cat_badge.pack(side="left")

                # Title
                t_lbl = ctk.CTkLabel(inner, text=iss.title, font=FONT_SUBTITLE, anchor="w")
                t_lbl.pack(anchor="w", pady=(2, 3))

                # Summary (simple language)
                s_lbl = ctk.CTkLabel(
                    inner,
                    text=iss.summary,
                    font=FONT_BODY,
                    text_color=("#374151", "#d1d5db"),
                    anchor="w",
                    wraplength=700,
                    justify="left",
                )
                s_lbl.pack(anchor="w", pady=(0, 6))

                # Evidence Box
                ev_box = ctk.CTkFrame(inner, fg_color=("#f9fafb", "#1e222a"), corner_radius=4)
                ev_box.pack(fill="x", pady=(2, 4))
                ev_lbl = ctk.CTkLabel(
                    ev_box,
                    text=f"Evidence: {iss.evidence}",
                    font=FONT_BODY,
                    text_color=("#4b5563", "#9ca3af"),
                    anchor="w",
                    wraplength=680,
                    justify="left",
                )
                ev_lbl.pack(anchor="w", padx=10, pady=6)

                # Recommendation Box
                rec_box = ctk.CTkFrame(inner, fg_color=("#f0fdf4", "#1a2a1f"), corner_radius=4)
                rec_box.pack(fill="x", pady=(2, 0))
                rec_lbl = ctk.CTkLabel(
                    rec_box,
                    text=f"Recommendation: {iss.recommendation}",
                    font=FONT_BODY_BOLD,
                    text_color=("#16a34a", "#22c55e"),
                    anchor="w",
                    wraplength=680,
                    justify="left",
                )
                rec_lbl.pack(anchor="w", padx=10, pady=6)

        # Render Healthy Checks
        for child in self.healthy_container.winfo_children():
            child.destroy()

        h_hdr = ctk.CTkFrame(self.healthy_container, fg_color="transparent")
        h_hdr.pack(fill="x", padx=16, pady=(12, 6))
        h_title = ctk.CTkLabel(h_hdr, text="Healthy Subsystems", font=FONT_SUBTITLE)
        h_title.pack(side="left")

        h_content = ctk.CTkFrame(self.healthy_container, fg_color="transparent")
        h_content.pack(fill="x", padx=16, pady=(0, 12))

        for check_text in report.healthy_checks:
            row = ctk.CTkFrame(h_content, fg_color="transparent")
            row.pack(fill="x", pady=2)
            chk = ctk.CTkLabel(row, text="✔", font=FONT_BODY_BOLD, text_color=("#16a34a", "#22c55e"))
            chk.pack(side="left", padx=(0, 8))
            clbl = ctk.CTkLabel(row, text=check_text, font=FONT_BODY, text_color=("#4b5563", "#9ca3af"), anchor="w")
            clbl.pack(side="left")
