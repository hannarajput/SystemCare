"""
Settings & System Logs View.
Configures UI preferences (appearance mode, polling interval), provides live in-app
diagnostic log viewing, and displays local offline privacy guarantees.
"""

from typing import Optional
import customtkinter as ctk

from ...core.monitor import SystemMonitor
from ...utils.logger import clear_recent_logs, get_recent_logs
from ..theme import (
    FONT_BODY,
    FONT_BODY_BOLD,
    FONT_MONO,
    FONT_SMALL,
    FONT_SUBTITLE,
    FONT_TITLE,
)


class SettingsView(ctk.CTkScrollableFrame):
    """
    Settings interface with appearance toggles, refresh rate controls,
    in-app log inspection, and privacy guarantees.
    """

    def __init__(self, master, monitor: SystemMonitor, **kwargs):
        super().__init__(master, fg_color="transparent", **kwargs)
        self.monitor = monitor

        self._build_header()
        self._build_privacy_guarantee()
        self._build_preferences()
        self._build_log_viewer()

    def _build_header(self) -> None:
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.pack(fill="x", padx=16, pady=(12, 10))

        title = ctk.CTkLabel(header, text="Settings & Logs", font=FONT_TITLE, anchor="w")
        title.pack(side="left")

    def _build_privacy_guarantee(self) -> None:
        card = ctk.CTkFrame(
            self,
            corner_radius=6,
            fg_color=("#ffffff", "#22252a"),
            border_width=1,
            border_color=("#e5e7eb", "#2e3440"),
        )
        card.pack(fill="x", padx=16, pady=(0, 12))

        inner = ctk.CTkFrame(card, fg_color="transparent")
        inner.pack(fill="x", padx=16, pady=12)

        tag = ctk.CTkLabel(
            inner,
            text=" PRIVACY ",
            font=FONT_SMALL,
            fg_color=("#f0fdf4", "#1a2a1f"),
            text_color=("#16a34a", "#22c55e"),
            corner_radius=4,
        )
        tag.pack(side="left", padx=(0, 12))

        box = ctk.CTkFrame(inner, fg_color="transparent")
        box.pack(side="left", fill="both", expand=True)

        ctk.CTkLabel(box, text="Local Execution & Zero Telemetry", font=FONT_BODY_BOLD, anchor="w").pack(anchor="w")
        ctk.CTkLabel(
            box,
            text=(
                "SystemCare functions completely offline on your Windows computer. It does not send analytics, "
                "upload hardware telemetry, or transmit your files or system diagnostics to external servers."
            ),
            font=FONT_SMALL,
            text_color=("#4b5563", "#9ca3af"),
            anchor="w",
            wraplength=700,
            justify="left",
        ).pack(anchor="w", pady=(2, 0))

    def _build_preferences(self) -> None:
        card = ctk.CTkFrame(
            self,
            corner_radius=6,
            fg_color=("#ffffff", "#22252a"),
            border_width=1,
            border_color=("#e5e7eb", "#2e3440"),
        )
        card.pack(fill="x", padx=16, pady=(0, 12))

        inner = ctk.CTkFrame(card, fg_color="transparent")
        inner.pack(fill="x", padx=16, pady=14)

        ctk.CTkLabel(inner, text="Preferences", font=FONT_SUBTITLE, anchor="w").pack(anchor="w", pady=(0, 12))

        # 1. Appearance Mode
        row1 = ctk.CTkFrame(inner, fg_color="transparent")
        row1.pack(fill="x", pady=6)

        lbl1 = ctk.CTkLabel(row1, text="Color Theme:", font=FONT_BODY_BOLD, width=170, anchor="w")
        lbl1.pack(side="left")

        theme_mode = ctk.get_appearance_mode()
        self.theme_menu = ctk.CTkOptionMenu(
            row1,
            values=["Dark", "Light", "System"],
            command=self._change_theme,
            font=FONT_BODY,
            width=140,
            height=30,
            corner_radius=6,
        )
        self.theme_menu.set(theme_mode)
        self.theme_menu.pack(side="left")

        # 2. Polling interval
        row2 = ctk.CTkFrame(inner, fg_color="transparent")
        row2.pack(fill="x", pady=6)

        lbl2 = ctk.CTkLabel(row2, text="Monitoring Refresh Rate:", font=FONT_BODY_BOLD, width=170, anchor="w")
        lbl2.pack(side="left")

        self.interval_menu = ctk.CTkOptionMenu(
            row2,
            values=["1.0 second", "1.5 seconds", "2.0 seconds", "3.0 seconds"],
            command=self._change_interval,
            font=FONT_BODY,
            width=140,
            height=30,
            corner_radius=6,
        )
        curr_int = f"{self.monitor.interval:.1f} second{'s' if self.monitor.interval != 1.0 else ''}"
        self.interval_menu.set(curr_int)
        self.interval_menu.pack(side="left")

    def _build_log_viewer(self) -> None:
        card = ctk.CTkFrame(
            self,
            corner_radius=6,
            fg_color=("#ffffff", "#22252a"),
            border_width=1,
            border_color=("#e5e7eb", "#2e3440"),
        )
        card.pack(fill="x", padx=16, pady=(0, 16))

        inner = ctk.CTkFrame(card, fg_color="transparent")
        inner.pack(fill="x", padx=16, pady=14)

        hdr = ctk.CTkFrame(inner, fg_color="transparent")
        hdr.pack(fill="x", pady=(0, 8))

        ctk.CTkLabel(hdr, text="Activity Logs", font=FONT_SUBTITLE, anchor="w").pack(side="left")

        btn_box = ctk.CTkFrame(hdr, fg_color="transparent")
        btn_box.pack(side="right")

        ctk.CTkButton(
            btn_box,
            text="Refresh",
            width=80,
            height=26,
            font=FONT_SMALL,
            corner_radius=4,
            fg_color=("#f3f4f6", "#2a2e35"),
            text_color=("#111827", "#f3f4f6"),
            hover_color=("#e5e7eb", "#323740"),
            command=self.refresh_logs,
        ).pack(side="left", padx=(0, 6))

        ctk.CTkButton(
            btn_box,
            text="Clear",
            width=70,
            height=26,
            font=FONT_SMALL,
            corner_radius=4,
            fg_color=("#f3f4f6", "#2a2e35"),
            text_color=("#111827", "#f3f4f6"),
            hover_color=("#e5e7eb", "#323740"),
            command=self._clear_logs,
        ).pack(side="left")

        ctk.CTkButton(
            btn_box,
            text="Clear",
            width=70,
            height=26,
            font=FONT_SMALL,
            fg_color=("#e6ebf2", "#2d3442"),
            text_color=("#1f2328", "#c9d1d9"),
            command=self._clear_logs,
        ).pack(side="left")

        self.log_textbox = ctk.CTkTextbox(
            inner, height=220, font=FONT_MONO, state="normal", wrap="none"
        )
        self.log_textbox.pack(fill="both", expand=True, pady=(4, 0))
        self.refresh_logs()

    def refresh_logs(self) -> None:
        logs = get_recent_logs()
        self.log_textbox.configure(state="normal")
        self.log_textbox.delete("1.0", "end")
        if logs:
            self.log_textbox.insert("end", "\n".join(logs))
            self.log_textbox.see("end")
        else:
            self.log_textbox.insert("end", "[No activity logs recorded yet]")
        self.log_textbox.configure(state="disabled")

    def _clear_logs(self) -> None:
        clear_recent_logs()
        self.refresh_logs()

    def _change_theme(self, choice: str) -> None:
        ctk.set_appearance_mode(choice.lower())

    def _change_interval(self, choice: str) -> None:
        val = float(choice.split()[0])
        self.monitor.interval = val
