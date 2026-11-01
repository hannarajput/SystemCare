"""
Dashboard & Live System Monitor View.
Displays real-time hardware gauges, CPU per-core loads, RAM, Disks, Network,
thermal status with graceful hardware fallbacks, and quick diagnosis shortcuts.
"""

from typing import Callable, Optional

import customtkinter as ctk

from ...core.diagnosis import DiagnosticReport, PerformanceDiagnosis
from ...core.monitor import SystemMonitor, SystemSnapshot
from ...utils.formatters import format_bytes, format_percent, format_speed
from ..theme import (
    FONT_BIG_NUMBER,
    FONT_BODY,
    FONT_BODY_BOLD,
    FONT_SMALL,
    FONT_SUBTITLE,
    FONT_TITLE,
)


class DashboardView(ctk.CTkScrollableFrame):
    """
    Main dashboard displaying live system monitors and health summary.
    """

    def __init__(
        self,
        master,
        monitor: SystemMonitor,
        on_navigate: Optional[Callable[[str], None]] = None,
        **kwargs,
    ):
        super().__init__(master, fg_color="transparent", **kwargs)
        self.monitor = monitor
        self.on_navigate = on_navigate
        self.diagnosis_engine = PerformanceDiagnosis()

        self._build_header()
        self._build_health_card()
        self._build_metric_cards()
        self._build_per_core_section()
        self._build_disk_section()

    def _build_header(self) -> None:
        header_frame = ctk.CTkFrame(self, fg_color="transparent")
        header_frame.pack(fill="x", padx=16, pady=(12, 12))

        title = ctk.CTkLabel(
            header_frame,
            text="Overview",
            font=FONT_TITLE,
            anchor="w",
        )
        title.pack(side="left")

        self.uptime_label = ctk.CTkLabel(
            header_frame,
            text="Uptime: Loading...",
            font=FONT_BODY,
            text_color=("#6b7280", "#9ca3af"),
            anchor="e",
        )
        self.uptime_label.pack(side="right")

    def _build_health_card(self) -> None:
        self.health_card = ctk.CTkFrame(
            self,
            corner_radius=6,
            fg_color=("#ffffff", "#22252a"),
            border_width=1,
            border_color=("#e5e7eb", "#2e3440"),
        )
        self.health_card.pack(fill="x", padx=16, pady=(0, 12))

        inner = ctk.CTkFrame(self.health_card, fg_color="transparent")
        inner.pack(fill="x", padx=18, pady=16)

        # Left: Score badge
        score_box = ctk.CTkFrame(inner, fg_color="transparent")
        score_box.pack(side="left", padx=(0, 20))

        self.score_label = ctk.CTkLabel(
            score_box, text="--", font=FONT_BIG_NUMBER, text_color=("#16a34a", "#22c55e")
        )
        self.score_label.pack()

        score_sub = ctk.CTkLabel(
            score_box, text="HEALTH SCORE", font=FONT_SMALL, text_color=("#6b7280", "#9ca3af")
        )
        score_sub.pack()

        # Middle: Summary text
        mid_box = ctk.CTkFrame(inner, fg_color="transparent")
        mid_box.pack(side="left", fill="both", expand=True)

        self.health_status_label = ctk.CTkLabel(
            mid_box, text="Analyzing System State...", font=FONT_SUBTITLE, anchor="w"
        )
        self.health_status_label.pack(anchor="w")

        self.health_desc_label = ctk.CTkLabel(
            mid_box,
            text="Real-time monitoring active. System resources are operating within normal parameters.",
            font=FONT_BODY,
            text_color=("#4b5563", "#9ca3af"),
            anchor="w",
            wraplength=520,
            justify="left",
        )
        self.health_desc_label.pack(anchor="w", pady=(3, 0))

        # Right: Quick actions
        btn_box = ctk.CTkFrame(inner, fg_color="transparent")
        btn_box.pack(side="right", padx=(10, 0))

        self.btn_boost = ctk.CTkButton(
            btn_box,
            text="Optimize System",
            fg_color=("#0066cc", "#2563eb"),
            hover_color=("#0052a3", "#1d4ed8"),
            font=FONT_BODY_BOLD,
            width=135,
            height=34,
            corner_radius=6,
            command=lambda: self._navigate("boost"),
        )
        self.btn_boost.pack(pady=(0, 6))

        self.btn_diag = ctk.CTkButton(
            btn_box,
            text="View Health Details",
            fg_color=("#f3f4f6", "#2a2e35"),
            text_color=("#111827", "#f3f4f6"),
            hover_color=("#e5e7eb", "#323740"),
            font=FONT_BODY,
            width=135,
            height=32,
            corner_radius=6,
            command=lambda: self._navigate("diagnosis"),
        )
        self.btn_diag.pack()

    def _build_metric_cards(self) -> None:
        grid = ctk.CTkFrame(self, fg_color="transparent")
        grid.pack(fill="x", padx=16, pady=(0, 12))
        grid.columnconfigure((0, 1, 2, 3), weight=1, uniform="metric_cards")

        # 1. CPU Card
        self.cpu_card = ctk.CTkFrame(
            grid,
            corner_radius=6,
            fg_color=("#ffffff", "#22252a"),
            border_width=1,
            border_color=("#e5e7eb", "#2e3440"),
        )
        self.cpu_card.grid(row=0, column=0, padx=(0, 6), sticky="nsew")
        self._populate_card_header(self.cpu_card, "Processor (CPU)", "#2563eb")
        self.cpu_val = ctk.CTkLabel(self.cpu_card, text="0.0%", font=FONT_BIG_NUMBER)
        self.cpu_val.pack(padx=14, pady=(0, 4))
        self.cpu_bar = ctk.CTkProgressBar(self.cpu_card, height=5, progress_color="#2563eb")
        self.cpu_bar.set(0.0)
        self.cpu_bar.pack(fill="x", padx=14, pady=(0, 6))
        self.cpu_sub = ctk.CTkLabel(
            self.cpu_card, text="Loading clock...", font=FONT_SMALL, text_color=("#6b7280", "#9ca3af")
        )
        self.cpu_sub.pack(padx=14, pady=(0, 10))

        # 2. RAM Card
        self.ram_card = ctk.CTkFrame(
            grid,
            corner_radius=6,
            fg_color=("#ffffff", "#22252a"),
            border_width=1,
            border_color=("#e5e7eb", "#2e3440"),
        )
        self.ram_card.grid(row=0, column=1, padx=3, sticky="nsew")
        self._populate_card_header(self.ram_card, "Memory (RAM)", "#22c55e")
        self.ram_val = ctk.CTkLabel(self.ram_card, text="0.0%", font=FONT_BIG_NUMBER)
        self.ram_val.pack(padx=14, pady=(0, 4))
        self.ram_bar = ctk.CTkProgressBar(self.ram_card, height=5, progress_color="#22c55e")
        self.ram_bar.set(0.0)
        self.ram_bar.pack(fill="x", padx=14, pady=(0, 6))
        self.ram_sub = ctk.CTkLabel(
            self.ram_card, text="Loading usage...", font=FONT_SMALL, text_color=("#6b7280", "#9ca3af")
        )
        self.ram_sub.pack(padx=14, pady=(0, 10))

        # 3. Disk I/O & Network Card
        self.net_card = ctk.CTkFrame(
            grid,
            corner_radius=6,
            fg_color=("#ffffff", "#22252a"),
            border_width=1,
            border_color=("#e5e7eb", "#2e3440"),
        )
        self.net_card.grid(row=0, column=2, padx=3, sticky="nsew")
        self._populate_card_header(self.net_card, "Network & Disk I/O", "#f59e0b")
        self.net_val = ctk.CTkLabel(self.net_card, text="↓ 0 B/s", font=FONT_BIG_NUMBER)
        self.net_val.pack(padx=14, pady=(0, 4))
        self.net_sub = ctk.CTkLabel(
            self.net_card, text="↑ 0 B/s | Disk: 0 B/s", font=FONT_SMALL, text_color=("#6b7280", "#9ca3af")
        )
        self.net_sub.pack(padx=14, pady=(6, 10))

        # 4. Thermal / Hardware Sensor Card
        self.temp_card = ctk.CTkFrame(
            grid,
            corner_radius=6,
            fg_color=("#ffffff", "#22252a"),
            border_width=1,
            border_color=("#e5e7eb", "#2e3440"),
        )
        self.temp_card.grid(row=0, column=3, padx=(6, 0), sticky="nsew")
        self._populate_card_header(self.temp_card, "Thermal Sensor", "#6b7280")
        self.temp_val = ctk.CTkLabel(self.temp_card, text="N/A", font=FONT_BIG_NUMBER)
        self.temp_val.pack(padx=14, pady=(0, 4))
        self.temp_sub = ctk.CTkLabel(
            self.temp_card,
            text="Sensor driver unexposed to user-mode",
            font=FONT_SMALL,
            text_color=("#6b7280", "#9ca3af"),
            wraplength=170,
        )
        self.temp_sub.pack(padx=14, pady=(6, 10))

    def _populate_card_header(self, card: ctk.CTkFrame, title: str, color: str) -> None:
        hdr = ctk.CTkFrame(card, fg_color="transparent")
        hdr.pack(fill="x", padx=14, pady=(10, 4))
        dot = ctk.CTkLabel(hdr, text="●", font=(FONT_TITLE[0], 9), text_color=color)
        dot.pack(side="left", padx=(0, 5))
        lbl = ctk.CTkLabel(hdr, text=title, font=FONT_SMALL, text_color=("#4b5563", "#9ca3af"))
        lbl.pack(side="left")

    def _build_per_core_section(self) -> None:
        self.core_frame = ctk.CTkFrame(
            self,
            corner_radius=6,
            fg_color=("#ffffff", "#22252a"),
            border_width=1,
            border_color=("#e5e7eb", "#2e3440"),
        )
        self.core_frame.pack(fill="x", padx=16, pady=(0, 12))

        hdr = ctk.CTkFrame(self.core_frame, fg_color="transparent")
        hdr.pack(fill="x", padx=14, pady=(10, 6))
        lbl = ctk.CTkLabel(hdr, text="Logical Core Distribution", font=FONT_SUBTITLE)
        lbl.pack(side="left")

        self.core_bars_container = ctk.CTkFrame(self.core_frame, fg_color="transparent")
        self.core_bars_container.pack(fill="x", padx=14, pady=(0, 12))

        self.core_bar_widgets = []
        snap = self.monitor.get_latest_snapshot()
        core_count = max(1, len(snap.cpu_percent_per_core))

        # Up to 16 cores per row
        cols = min(8, core_count)
        for i in range(core_count):
            row = i // cols
            col = i % cols
            cbox = ctk.CTkFrame(self.core_bars_container, fg_color="transparent")
            cbox.grid(row=row, column=col, padx=4, pady=3, sticky="ew")
            self.core_bars_container.columnconfigure(col, weight=1)

            clbl = ctk.CTkLabel(cbox, text=f"C{i+1}: 0%", font=FONT_SMALL, text_color=("#6b7280", "#9ca3af"))
            clbl.pack(anchor="w")
            cbar = ctk.CTkProgressBar(cbox, height=4, progress_color="#2563eb")
            cbar.set(0.0)
            cbar.pack(fill="x", pady=(2, 0))
            self.core_bar_widgets.append((clbl, cbar))

    def _build_disk_section(self) -> None:
        self.disk_card = ctk.CTkFrame(
            self,
            corner_radius=6,
            fg_color=("#ffffff", "#22252a"),
            border_width=1,
            border_color=("#e5e7eb", "#2e3440"),
        )
        self.disk_card.pack(fill="x", padx=16, pady=(0, 16))

        hdr = ctk.CTkFrame(self.disk_card, fg_color="transparent")
        hdr.pack(fill="x", padx=14, pady=(10, 6))
        lbl = ctk.CTkLabel(hdr, text="Storage Drive Volumes", font=FONT_SUBTITLE)
        lbl.pack(side="left")

        self.disks_container = ctk.CTkFrame(self.disk_card, fg_color="transparent")
        self.disks_container.pack(fill="x", padx=14, pady=(0, 12))

    def update_snapshot(self, snapshot: SystemSnapshot) -> None:
        """Update dashboard widgets with fresh telemetry data."""
        # 1. CPU
        self.cpu_val.configure(text=format_percent(snapshot.cpu_percent_total))
        self.cpu_bar.set(snapshot.cpu_percent_total / 100.0)
        self.cpu_bar.configure(
            progress_color="#f85149"
            if snapshot.cpu_percent_total >= 90
            else "#d29922"
            if snapshot.cpu_percent_total >= 75
            else "#2f81f7"
        )
        freq_str = f"{snapshot.cpu_freq_current_mhz:.0f} MHz" if snapshot.cpu_freq_current_mhz else "N/A"
        self.cpu_sub.configure(
            text=f"{snapshot.cpu_physical_cores} Cores / {snapshot.cpu_logical_cores} Threads | {freq_str}"
        )

        # 2. RAM
        self.ram_val.configure(text=format_percent(snapshot.ram_percent))
        self.ram_bar.set(snapshot.ram_percent / 100.0)
        self.ram_bar.configure(
            progress_color="#f85149"
            if snapshot.ram_percent >= 90
            else "#d29922"
            if snapshot.ram_percent >= 80
            else "#3fb950"
        )
        self.ram_sub.configure(
            text=f"{format_bytes(snapshot.ram_used_bytes)} used of {format_bytes(snapshot.ram_total_bytes)} ({format_bytes(snapshot.ram_available_bytes)} free)"
        )

        # 3. Network & Disk I/O
        self.net_val.configure(text=f"↓ {format_speed(snapshot.net_bytes_recv_sec)}")
        disk_rate = format_speed(snapshot.disk_read_bytes_sec + snapshot.disk_write_bytes_sec)
        self.net_sub.configure(
            text=f"↑ {format_speed(snapshot.net_bytes_sent_sec)} | Disk I/O: {disk_rate}"
        )

        # 4. Temperature
        t_info = snapshot.temperature
        if t_info.available and t_info.temperature_celsius is not None:
            self.temp_val.configure(
                text=f"{t_info.temperature_celsius:.1f}°C",
                text_color="#f85149" if t_info.temperature_celsius >= 85 else "#3fb950",
            )
            self.temp_sub.configure(text=t_info.sensor_name or "Hardware Sensor")
        else:
            self.temp_val.configure(text="Unavailable", text_color="#8b949e")
            self.temp_sub.configure(text="Sensor driver unexposed to user-mode")

        # 5. Logical Cores
        for i, (clbl, cbar) in enumerate(self.core_bar_widgets):
            if i < len(snapshot.cpu_percent_per_core):
                pct = snapshot.cpu_percent_per_core[i]
                clbl.configure(text=f"C{i+1}: {pct:.0f}%")
                cbar.set(pct / 100.0)
                cbar.configure(
                    progress_color="#f85149" if pct >= 90 else "#d29922" if pct >= 75 else "#2f81f7"
                )

        # 6. Disks Container
        self._refresh_disks(snapshot.disks)

        # 7. Health Evaluation
        report = self.diagnosis_engine.evaluate(snapshot)
        self.score_label.configure(
            text=str(report.overall_score),
            text_color="#3fb950" if report.overall_score >= 85 else "#d29922" if report.overall_score >= 60 else "#f85149",
        )
        self.health_status_label.configure(text=f"System Status: {report.overall_status}")
        if report.issues:
            top_issue = report.issues[0]
            self.health_desc_label.configure(
                text=f"Warning: {top_issue.title}. {top_issue.summary}"
            )
        else:
            self.health_desc_label.configure(
                text="All system metrics are balanced. Physical memory and processor headroom are optimal."
            )

        # 8. Uptime
        uptime_h = int(snapshot.uptime_seconds // 3600)
        uptime_m = int((snapshot.uptime_seconds % 3600) // 60)
        self.uptime_label.configure(text=f"System Uptime: {uptime_h}h {uptime_m}m")

    def _refresh_disks(self, disks) -> None:
        # Recreate disk widgets if count changed
        if not hasattr(self, "_disk_widgets") or len(self._disk_widgets) != len(disks):
            for child in self.disks_container.winfo_children():
                child.destroy()
            self._disk_widgets = []

            for d in disks:
                d_box = ctk.CTkFrame(self.disks_container, fg_color="transparent")
                d_box.pack(fill="x", pady=4)

                top_row = ctk.CTkFrame(d_box, fg_color="transparent")
                top_row.pack(fill="x")

                d_lbl = ctk.CTkLabel(
                    top_row,
                    text=f"Drive {d.mountpoint} ({d.fstype})",
                    font=FONT_BODY_BOLD,
                    anchor="w",
                )
                d_lbl.pack(side="left")

                d_usage = ctk.CTkLabel(
                    top_row,
                    text="",
                    font=FONT_BODY,
                    text_color=("#6b7280", "#9ca3af"),
                    anchor="e",
                )
                d_usage.pack(side="right")

                bar = ctk.CTkProgressBar(d_box, height=5)
                bar.pack(fill="x", pady=(3, 0))
                self._disk_widgets.append((d_lbl, d_usage, bar))

        for (d_lbl, d_usage, bar), d in zip(self._disk_widgets, disks):
            d_usage.configure(
                text=f"{format_bytes(d.used_bytes)} / {format_bytes(d.total_bytes)} ({format_percent(d.percent)})"
            )
            bar.set(d.percent / 100.0)
            bar_color = "#dc2626" if d.percent >= 90 else "#d97706" if d.percent >= 80 else "#2563eb"
            bar.configure(progress_color=bar_color)

    def _navigate(self, view_name: str) -> None:
        if self.on_navigate:
            self.on_navigate(view_name)
