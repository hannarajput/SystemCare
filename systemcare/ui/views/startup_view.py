"""
Startup Application Manager View.
Scans and presents Windows startup applications from Registry and Startup Folders.
Provides clear impact ratings, educational safety guidance, and confirmed safe toggling.
"""

from typing import List, Optional
import tkinter.messagebox as msgbox
import customtkinter as ctk

from ...core.startup_manager import StartupItem, StartupManager
from ..theme import (
    FONT_BODY,
    FONT_BODY_BOLD,
    FONT_MONO,
    FONT_SMALL,
    FONT_SUBTITLE,
    FONT_TITLE,
)


class StartupView(ctk.CTkFrame):
    """
    Startup manager view with impact evaluation and safe user toggling.
    """

    def __init__(self, master, startup_manager: Optional[StartupManager] = None, **kwargs):
        super().__init__(master, fg_color="transparent", **kwargs)
        self.sm = startup_manager or StartupManager()
        self.cached_items: List[StartupItem] = []

        self._build_header()
        self._build_guidance_banner()
        self._build_toolbar()
        self._build_table()
        self.refresh_startup_items()

    def _build_header(self) -> None:
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.pack(fill="x", padx=16, pady=(12, 10))

        title = ctk.CTkLabel(header, text="Startup Applications", font=FONT_TITLE, anchor="w")
        title.pack(side="left")

        self.btn_refresh = ctk.CTkButton(
            header,
            text="Refresh",
            font=FONT_BODY_BOLD,
            width=90,
            height=32,
            corner_radius=6,
            fg_color=("#0066cc", "#2563eb"),
            hover_color=("#0052a3", "#1d4ed8"),
            command=self.refresh_startup_items,
        )
        self.btn_refresh.pack(side="right")

    def _build_guidance_banner(self) -> None:
        banner = ctk.CTkFrame(
            self,
            corner_radius=6,
            fg_color=("#ffffff", "#22252a"),
            border_width=1,
            border_color=("#e5e7eb", "#2e3440"),
        )
        banner.pack(fill="x", padx=16, pady=(0, 10))

        inner = ctk.CTkFrame(banner, fg_color="transparent")
        inner.pack(fill="x", padx=16, pady=12)

        tag = ctk.CTkLabel(
            inner,
            text=" GUIDANCE ",
            font=FONT_SMALL,
            fg_color=("#e0edff", "#1e293b"),
            text_color=("#0066cc", "#38bdf8"),
            corner_radius=4,
        )
        tag.pack(side="left", padx=(0, 12))

        text_box = ctk.CTkFrame(inner, fg_color="transparent")
        text_box.pack(side="left", fill="both", expand=True)

        lbl_head = ctk.CTkLabel(
            text_box,
            text="About Startup Applications",
            font=FONT_BODY_BOLD,
            anchor="w",
        )
        lbl_head.pack(anchor="w")

        lbl_desc = ctk.CTkLabel(
            text_box,
            text=(
                "Startup applications automatically launch when signing into Windows. Disabling non-essential programs "
                "(such as game launchers, chat, or media players) reduces boot time and conserves memory. SystemCare safely "
                "backs up disabled registry keys, allowing instant restoration. Core security services remain protected."
            ),
            font=FONT_SMALL,
            text_color=("#4b5563", "#9ca3af"),
            anchor="w",
            wraplength=700,
            justify="left",
        )
        lbl_desc.pack(anchor="w", pady=(2, 0))

    def _build_toolbar(self) -> None:
        bar = ctk.CTkFrame(self, fg_color="transparent")
        bar.pack(fill="x", padx=16, pady=(0, 8))

        self.filter_var = ctk.StringVar(value="All Items")
        self.seg_filter = ctk.CTkSegmentedButton(
            bar,
            values=["All Items", "User-Level (Safe to Manage)", "System-Wide / Essential"],
            variable=self.filter_var,
            command=lambda v: self._apply_filter(),
            font=FONT_BODY,
            height=30,
            corner_radius=6,
        )
        self.seg_filter.pack(side="left")

        self.count_label = ctk.CTkLabel(
            bar, text="Scanning...", font=FONT_SMALL, text_color=("#6b7280", "#9ca3af")
        )
        self.count_label.pack(side="right")

    def _build_table(self) -> None:
        # Table Header
        header = ctk.CTkFrame(
            self,
            height=34,
            fg_color=("#f3f4f6", "#1e222a"),
            corner_radius=6,
            border_width=1,
            border_color=("#e5e7eb", "#2e3440"),
        )
        header.pack(fill="x", padx=16, pady=(0, 4))

        cols = [
            ("Application Name", 220),
            ("Impact", 110),
            ("Location", 150),
            ("Guidance / Description", 310),
            ("Action", 120),
        ]

        for title, width in cols:
            lbl = ctk.CTkLabel(
                header,
                text=title,
                width=width,
                font=FONT_BODY_BOLD,
                text_color=("#4b5563", "#9ca3af"),
                anchor="w",
            )
            lbl.pack(side="left", padx=8)

        # Scrollable container
        self.rows_container = ctk.CTkScrollableFrame(self, fg_color="transparent")
        self.rows_container.pack(fill="both", expand=True, padx=16, pady=(0, 10))

    def refresh_startup_items(self) -> None:
        self.cached_items = self.sm.list_startup_items()
        self._apply_filter()

    def _apply_filter(self) -> None:
        choice = self.filter_var.get()
        items = list(self.cached_items)

        if choice == "User-Level (Safe to Manage)":
            items = [it for it in items if it.can_toggle]
        elif choice == "System-Wide / Essential":
            items = [it for it in items if not it.can_toggle]

        self.count_label.configure(text=f"Showing {len(items)} startup items")
        self._render_rows(items)

    def _render_rows(self, items: List[StartupItem]) -> None:
        for child in self.rows_container.winfo_children():
            child.destroy()

        if not items:
            lbl = ctk.CTkLabel(
                self.rows_container,
                text="No startup applications found in this category.",
                font=FONT_BODY,
                text_color="#8b949e",
            )
            lbl.pack(pady=30)
            return

        for it in items:
            row = ctk.CTkFrame(
                self.rows_container,
                fg_color=("#ffffff", "#22252a"),
                corner_radius=4,
                border_width=1,
                border_color=("#f3f4f6", "#2a2d34"),
            )
            row.pack(fill="x", pady=2)

            inner = ctk.CTkFrame(row, fg_color="transparent")
            inner.pack(fill="x", padx=8, pady=8)

            # Name
            name_text = it.name if len(it.name) <= 24 else it.name[:22] + "..."
            name_lbl = ctk.CTkLabel(inner, text=name_text, width=220, font=FONT_BODY_BOLD, anchor="w")
            name_lbl.pack(side="left", padx=8)

            # Impact Badge
            imp_box = ctk.CTkFrame(inner, width=110, fg_color="transparent")
            imp_box.pack(side="left", padx=8)
            imp_color = (
                "#6b7280"
                if it.impact == "Essential"
                else "#d97706"
                if it.impact == "High"
                else "#0066cc"
                if it.impact == "Medium"
                else "#16a34a"
            )
            badge = ctk.CTkLabel(
                imp_box,
                text=f" {it.impact} ",
                font=FONT_SMALL,
                text_color="#ffffff",
                fg_color=imp_color,
                corner_radius=4,
            )
            badge.pack(anchor="w")

            # Location
            loc_lbl = ctk.CTkLabel(
                inner, text=it.location_type, width=150, font=FONT_SMALL, text_color=("#6b7280", "#9ca3af"), anchor="w"
            )
            loc_lbl.pack(side="left", padx=8)

            # Guidance & Description
            guide_lbl = ctk.CTkLabel(
                inner,
                text=it.guidance or it.description,
                width=310,
                font=FONT_SMALL,
                text_color=("#374151", "#d1d5db"),
                anchor="w",
                wraplength=300,
                justify="left",
            )
            guide_lbl.pack(side="left", padx=8)

            # Action / Toggle Button
            act_box = ctk.CTkFrame(inner, width=120, fg_color="transparent")
            act_box.pack(side="left", padx=8)

            if it.can_toggle:
                if it.is_enabled:
                    btn = ctk.CTkButton(
                        act_box,
                        text="Disable",
                        font=FONT_SMALL,
                        width=80,
                        height=26,
                        corner_radius=4,
                        fg_color=("#f3f4f6", "#2a2e35"),
                        text_color=("#111827", "#f3f4f6"),
                        hover_color=("#e5e7eb", "#323740"),
                        command=lambda item=it: self._confirm_toggle_startup(item),
                    )
                else:
                    btn = ctk.CTkButton(
                        act_box,
                        text="Enable",
                        font=FONT_SMALL,
                        width=80,
                        height=26,
                        corner_radius=4,
                        fg_color=("#0066cc", "#2563eb"),
                        hover_color=("#0052a3", "#1d4ed8"),
                        command=lambda item=it: self._confirm_toggle_startup(item),
                    )
                btn.pack(side="left")
            else:
                if it.impact == "Essential":
                    locked_lbl = ctk.CTkLabel(
                        act_box, text="Protected", font=FONT_SMALL, text_color=("#6b7280", "#9ca3af")
                    )
                else:
                    locked_lbl = ctk.CTkButton(
                        act_box,
                        text="Info",
                        font=FONT_SMALL,
                        width=70,
                        height=24,
                        corner_radius=4,
                        fg_color=("#f3f4f6", "#2a2e35"),
                        text_color=("#111827", "#f3f4f6"),
                        hover_color=("#e5e7eb", "#323740"),
                        command=lambda item=it: self._show_system_guidance(item),
                    )
                locked_lbl.pack(side="left")

    def _confirm_toggle_startup(self, item: StartupItem) -> None:
        action = "disable" if item.is_enabled else "enable"
        confirmed = msgbox.askyesno(
            title=f"Confirm Startup {action.capitalize()}",
            message=(
                f"Are you sure you want to {action} '{item.name}' from starting with Windows?\n\n"
                f"Impact: {item.impact}\n"
                f"Guidance: {item.guidance}\n\n"
                f"SystemCare will safely update your configuration. You can change this at any time."
            ),
            icon="question",
        )
        if not confirmed:
            return

        success, msg = self.sm.toggle_startup_item(item)
        if success:
            msgbox.showinfo("Startup Updated", msg)
        else:
            msgbox.showwarning("Startup Notice", msg)

        self.refresh_startup_items()

    def _show_system_guidance(self, item: StartupItem) -> None:
        msgbox.showinfo(
            "System-Wide Startup Item",
            f"Application: {item.name}\n"
            f"Location: {item.location_type}\n\n"
            f"{item.guidance}\n\n"
            "Because this item is registered system-wide (HKLM or Common Startup), "
            "it is safest to manage it via Windows Settings > Apps > Startup, or run SystemCare as Administrator.",
        )
