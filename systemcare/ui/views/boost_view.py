"""
Safe Boost View.
Transparent, evidence-based PC optimization center.
Presents genuine, selectable system improvements (memory working set trimming,
temporary cache removal) without false claims or aggressive background kills.
Displays precise before/after resource metrics.
"""

import threading
from typing import Callable, Dict, List, Optional
import tkinter.messagebox as msgbox
import customtkinter as ctk

from ...core.boost_engine import BoostAction, BoostResult, SafeBoostEngine
from ...core.monitor import SystemMonitor
from ...utils.formatters import format_bytes, format_percent
from ..theme import (
    FONT_BIG_NUMBER,
    FONT_BODY,
    FONT_BODY_BOLD,
    FONT_MONO,
    FONT_SMALL,
    FONT_SUBTITLE,
    FONT_TITLE,
)


class BoostView(ctk.CTkScrollableFrame):
    """
    Interactive safe boost mode with customizable action checkboxes
    and before/after telemetry tracking.
    """

    def __init__(
        self,
        master,
        monitor: SystemMonitor,
        boost_engine: Optional[SafeBoostEngine] = None,
        on_boost_completed: Optional[Callable[[BoostResult], None]] = None,
        **kwargs,
    ):
        super().__init__(master, fg_color="transparent", **kwargs)
        self.monitor = monitor
        self.engine = boost_engine or SafeBoostEngine(monitor)
        self.on_boost_completed = on_boost_completed

        self.available_actions: List[BoostAction] = []
        self.action_checkbox_vars: Dict[str, ctk.BooleanVar] = {}
        self.latest_result: Optional[BoostResult] = None

        self._build_header()
        self._build_transparency_notice()
        self._build_baseline_card()
        self._build_actions_checklist()
        self._build_results_section()
        self.refresh_analysis()

    def _build_header(self) -> None:
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.pack(fill="x", padx=16, pady=(12, 10))

        title = ctk.CTkLabel(header, text="Safe Boost", font=FONT_TITLE, anchor="w")
        title.pack(side="left")

        self.btn_reanalyze = ctk.CTkButton(
            header,
            text="Re-scan System",
            font=FONT_BODY,
            width=125,
            height=34,
            corner_radius=6,
            fg_color=("#0066cc", "#2563eb"),
            hover_color=("#0052a3", "#1d4ed8"),
            command=self.refresh_analysis,
        )
        self.btn_reanalyze.pack(side="right")

    def _build_transparency_notice(self) -> None:
        card = ctk.CTkFrame(
            self,
            corner_radius=6,
            fg_color=("#ffffff", "#22252a"),
            border_width=1,
            border_color=("#e5e7eb", "#2e3440"),
        )
        card.pack(fill="x", padx=16, pady=(0, 10))

        inner = ctk.CTkFrame(card, fg_color="transparent")
        inner.pack(fill="x", padx=16, pady=12)

        tag = ctk.CTkLabel(
            inner,
            text=" STANDARD ",
            font=FONT_SMALL,
            fg_color=("#e0edff", "#1e293b"),
            text_color=("#0066cc", "#38bdf8"),
            corner_radius=4,
        )
        tag.pack(side="left", padx=(0, 12))

        box = ctk.CTkFrame(inner, fg_color="transparent")
        box.pack(side="left", fill="both", expand=True)

        ctk.CTkLabel(box, text="Safe Optimization Standard", font=FONT_BODY_BOLD, anchor="w").pack(anchor="w")
        ctk.CTkLabel(
            box,
            text=(
                "Unlike aggressive utilities, SystemCare never terminates background apps blindly or alters core security services. "
                "All actions rely on documented Windows APIs (such as working set trimming) and verified safe scratch cleanups."
            ),
            font=FONT_SMALL,
            text_color=("#4b5563", "#9ca3af"),
            anchor="w",
            wraplength=700,
            justify="left",
        ).pack(anchor="w", pady=(2, 0))

    def _build_baseline_card(self) -> None:
        self.baseline_frame = ctk.CTkFrame(
            self,
            corner_radius=6,
            fg_color=("#ffffff", "#22252a"),
            border_width=1,
            border_color=("#e5e7eb", "#2e3440"),
        )
        self.baseline_frame.pack(fill="x", padx=16, pady=(0, 12))

        inner = ctk.CTkFrame(self.baseline_frame, fg_color="transparent")
        inner.pack(fill="x", padx=16, pady=10)

        ctk.CTkLabel(inner, text="Current Baseline", font=FONT_SUBTITLE).pack(side="left", padx=(0, 20))

        self.lbl_base_ram = ctk.CTkLabel(inner, text="RAM: --", font=FONT_BODY_BOLD, text_color=("#16a34a", "#22c55e"))
        self.lbl_base_ram.pack(side="left", padx=(0, 16))

        self.lbl_base_cpu = ctk.CTkLabel(inner, text="CPU: --", font=FONT_BODY_BOLD, text_color=("#0066cc", "#2563eb"))
        self.lbl_base_cpu.pack(side="left")

    def _build_actions_checklist(self) -> None:
        self.actions_container = ctk.CTkFrame(self, fg_color="transparent")
        self.actions_container.pack(fill="x", padx=16, pady=(0, 12))

        # Bottom Apply Button Bar
        btn_bar = ctk.CTkFrame(self, fg_color="transparent")
        btn_bar.pack(fill="x", padx=16, pady=(0, 12))

        self.btn_apply = ctk.CTkButton(
            btn_bar,
            text="Optimize Selected Items",
            font=FONT_BODY_BOLD,
            height=38,
            corner_radius=6,
            fg_color=("#0066cc", "#2563eb"),
            hover_color=("#0052a3", "#1d4ed8"),
            command=self._execute_boost_thread,
        )
        self.btn_apply.pack(fill="x")

    def _build_results_section(self) -> None:
        self.results_frame = ctk.CTkFrame(
            self,
            corner_radius=6,
            fg_color=("#ffffff", "#22252a"),
            border_width=1,
            border_color=("#e5e7eb", "#2e3440"),
        )
        self.results_frame.pack(fill="x", padx=16, pady=(0, 16))

        inner = ctk.CTkFrame(self.results_frame, fg_color="transparent")
        inner.pack(fill="x", padx=16, pady=12)

        self.results_title = ctk.CTkLabel(inner, text="Optimization Results", font=FONT_SUBTITLE, anchor="w")
        self.results_title.pack(anchor="w")

        self.results_body = ctk.CTkLabel(
            inner,
            text="Select your desired optimizations above and click 'Optimize Selected Items'.",
            font=FONT_BODY,
            text_color=("#4b5563", "#9ca3af"),
            anchor="w",
            wraplength=700,
            justify="left",
        )
        self.results_body.pack(anchor="w", pady=(3, 0))

        self.results_metrics_box = ctk.CTkFrame(inner, fg_color="transparent")
        self.results_metrics_box.pack(fill="x", pady=(8, 0))

    def refresh_analysis(self) -> None:
        """Scan system opportunities for safe optimization."""
        snap = self.monitor.get_latest_snapshot()
        self.lbl_base_ram.configure(
            text=f"RAM: {format_percent(snap.ram_percent)} ({format_bytes(snap.ram_used_bytes)} / {format_bytes(snap.ram_total_bytes)})"
        )
        self.lbl_base_cpu.configure(text=f"CPU: {format_percent(snapshot_total:=snap.cpu_percent_total)}")

        self.available_actions = self.engine.analyze_system()
        self._render_actions()

    def _render_actions(self) -> None:
        for child in self.actions_container.winfo_children():
            child.destroy()

        self.action_checkbox_vars.clear()

        for act in self.available_actions:
            card = ctk.CTkFrame(
                self.actions_container,
                corner_radius=6,
                fg_color=("#ffffff", "#22252a"),
                border_width=1,
                border_color=("#e5e7eb", "#2e3440"),
            )
            card.pack(fill="x", pady=4)

            inner = ctk.CTkFrame(card, fg_color="transparent")
            inner.pack(fill="x", padx=14, pady=12)

            # Checkbox
            var = ctk.BooleanVar(value=act.selected)
            self.action_checkbox_vars[act.id] = var

            chk = ctk.CTkCheckBox(
                inner,
                text="",
                variable=var,
                width=24,
            )
            chk.pack(side="left", padx=(0, 10))

            # Details
            box = ctk.CTkFrame(inner, fg_color="transparent")
            box.pack(side="left", fill="both", expand=True)

            title_row = ctk.CTkFrame(box, fg_color="transparent")
            title_row.pack(fill="x")

            t_lbl = ctk.CTkLabel(title_row, text=act.title, font=FONT_BODY_BOLD, anchor="w")
            t_lbl.pack(side="left", padx=(0, 8))

            badge = ctk.CTkLabel(
                title_row,
                text=f" {act.safety_rating} ",
                font=FONT_SMALL,
                text_color="#ffffff",
                fg_color="#16a34a" if "Very" in act.safety_rating else "#0066cc",
                corner_radius=4,
            )
            badge.pack(side="left")

            desc_lbl = ctk.CTkLabel(
                box,
                text=act.description,
                font=FONT_SMALL,
                text_color=("#4b5563", "#9ca3af"),
                anchor="w",
                wraplength=650,
                justify="left",
            )
            desc_lbl.pack(anchor="w", pady=(2, 2))

            est_lbl = ctk.CTkLabel(
                box,
                text=f"Estimated Benefit: {act.estimated_benefit}",
                font=FONT_SMALL,
                text_color=("#16a34a", "#22c55e"),
                anchor="w",
            )
            est_lbl.pack(anchor="w")

    def _execute_boost_thread(self) -> None:
        selected_ids = [
            act_id for act_id, var in self.action_checkbox_vars.items() if var.get()
        ]

        if not selected_ids:
            msgbox.showinfo("No Actions Selected", "Please select at least one optimization action.")
            return

        self.btn_apply.configure(state="disabled", text="Optimizing System...")

        def worker():
            res = self.engine.execute_boost(selected_ids)
            self.after(0, lambda: self._on_boost_done(res))

        threading.Thread(target=worker, daemon=True).start()

    def _on_boost_done(self, result: BoostResult) -> None:
        self.latest_result = result
        self.btn_apply.configure(state="normal", text="Optimize Selected Items")

        # Notify parent app / reports
        if self.on_boost_completed:
            self.on_boost_completed(result)

        # Update Results View
        self.results_title.configure(text="Optimization Complete")
        self.results_body.configure(
            text=f"Executed {len(result.actions_executed)} optimization task(s). Telemetry updated below."
        )

        for child in self.results_metrics_box.winfo_children():
            child.destroy()

        metrics_grid = ctk.CTkFrame(self.results_metrics_box, fg_color="transparent")
        metrics_grid.pack(fill="x", pady=6)
        metrics_grid.columnconfigure((0, 1, 2, 3), weight=1)

        # 1. RAM %
        c1 = ctk.CTkFrame(metrics_grid, fg_color=("#f0f3f8", "#16191f"), corner_radius=6)
        c1.grid(row=0, column=0, padx=4, pady=4, sticky="nsew")
        ctk.CTkLabel(c1, text="RAM USAGE", font=FONT_SMALL, text_color="#8b949e").pack(padx=8, pady=(8, 2))
        ctk.CTkLabel(
            c1,
            text=f"{result.ram_before_percent:.1f}% ➔ {result.ram_after_percent:.1f}%",
            font=FONT_BODY_BOLD,
            text_color="#3fb950",
        ).pack(padx=8, pady=(0, 8))

        # 2. Working Set Trimmed
        c2 = ctk.CTkFrame(metrics_grid, fg_color=("#f0f3f8", "#16191f"), corner_radius=6)
        c2.grid(row=0, column=1, padx=4, pady=4, sticky="nsew")
        ctk.CTkLabel(c2, text="WORKING SET TRIMMED", font=FONT_SMALL, text_color="#8b949e").pack(padx=8, pady=(8, 2))
        ctk.CTkLabel(
            c2, text=format_bytes(result.working_set_trimmed_bytes), font=FONT_BODY_BOLD, text_color="#2f81f7"
        ).pack(padx=8, pady=(0, 8))

        # 3. Available RAM Delta
        c3 = ctk.CTkFrame(metrics_grid, fg_color=("#f0f3f8", "#16191f"), corner_radius=6)
        c3.grid(row=0, column=2, padx=4, pady=4, sticky="nsew")
        ctk.CTkLabel(c3, text="AVAILABLE RAM DELTA", font=FONT_SMALL, text_color="#8b949e").pack(padx=8, pady=(8, 2))
        ctk.CTkLabel(
            c3, text=format_bytes(result.memory_freed_bytes), font=FONT_BODY_BOLD, text_color="#3fb950"
        ).pack(padx=8, pady=(0, 8))

        # 4. Sent to Recycle Bin vs Physical Disk Space
        c4 = ctk.CTkFrame(metrics_grid, fg_color=("#f0f3f8", "#16191f"), corner_radius=6)
        c4.grid(row=0, column=3, padx=4, pady=4, sticky="nsew")
        ctk.CTkLabel(c4, text="RECYCLED / FREED DISK", font=FONT_SMALL, text_color="#8b949e").pack(padx=8, pady=(8, 2))
        ctk.CTkLabel(
            c4,
            text=f"{format_bytes(result.bytes_recycled)} / {format_bytes(result.disk_freed_bytes)}",
            font=FONT_BODY_BOLD,
            text_color="#d29922",
        ).pack(padx=8, pady=(0, 8))

        # Refresh analysis
        self.refresh_analysis()
