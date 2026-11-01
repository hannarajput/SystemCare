"""
Background Application and Process Manager View.
Displays active user applications and background processes with real-time CPU and memory metrics.
Allows safe manual closure of user apps while strictly guarding system processes.
"""

from typing import List, Optional
import tkinter.messagebox as msgbox
import customtkinter as ctk

from ...core.process_manager import ProcessInfo, ProcessManager
from ...utils.formatters import format_bytes, format_percent
from ..theme import (
    FONT_BODY,
    FONT_BODY_BOLD,
    FONT_MONO,
    FONT_SMALL,
    FONT_SUBTITLE,
    FONT_TITLE,
)


class ProcessView(ctk.CTkFrame):
    """
    Process Manager interface with search, sorting, system process protection,
    and confirmation dialogs for terminating user applications.
    """

    def __init__(self, master, process_manager: Optional[ProcessManager] = None, **kwargs):
        super().__init__(master, fg_color="transparent", **kwargs)
        self.pm = process_manager or ProcessManager()
        self.cached_processes: List[ProcessInfo] = []

        self._build_header()
        self._build_toolbar()
        self._build_table()
        self.refresh_process_list()

    def _build_header(self) -> None:
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.pack(fill="x", padx=16, pady=(12, 10))

        title = ctk.CTkLabel(
            header, text="Running Applications", font=FONT_TITLE, anchor="w"
        )
        title.pack(side="left")

        self.summary_label = ctk.CTkLabel(
            header, text="Loading processes...", font=FONT_BODY, text_color=("#6b7280", "#9ca3af")
        )
        self.summary_label.pack(side="right")

    def _build_toolbar(self) -> None:
        bar = ctk.CTkFrame(
            self,
            fg_color=("#ffffff", "#22252a"),
            corner_radius=6,
            border_width=1,
            border_color=("#e5e7eb", "#2e3440"),
        )
        bar.pack(fill="x", padx=16, pady=(0, 10))

        inner = ctk.CTkFrame(bar, fg_color="transparent")
        inner.pack(fill="x", padx=12, pady=10)

        # Search Entry
        self.search_var = ctk.StringVar()
        self.search_var.trace_add("write", lambda *args: self._apply_filters())
        self.search_entry = ctk.CTkEntry(
            inner,
            placeholder_text="Search process or PID...",
            textvariable=self.search_var,
            width=260,
            height=32,
            font=FONT_BODY,
            corner_radius=6,
        )
        self.search_entry.pack(side="left", padx=(0, 12))

        # Filter Segment: All vs User Only
        self.filter_mode = ctk.StringVar(value="User Apps Only")
        self.seg_filter = ctk.CTkSegmentedButton(
            inner,
            values=["User Apps Only", "All Processes"],
            variable=self.filter_mode,
            command=lambda v: self._apply_filters(),
            font=FONT_BODY,
            height=32,
            corner_radius=6,
        )
        self.seg_filter.pack(side="left", padx=(0, 12))

        # Sort Dropdown
        self.sort_var = ctk.StringVar(value="Highest CPU")
        self.sort_menu = ctk.CTkOptionMenu(
            inner,
            values=["Highest CPU", "Highest Memory", "Process Name", "Process ID (PID)"],
            variable=self.sort_var,
            command=lambda v: self._apply_filters(),
            font=FONT_BODY,
            height=32,
            width=160,
            corner_radius=6,
        )
        self.sort_menu.pack(side="left")

        # Refresh Button
        self.btn_refresh = ctk.CTkButton(
            inner,
            text="Refresh",
            font=FONT_BODY_BOLD,
            width=90,
            height=32,
            corner_radius=6,
            fg_color=("#0066cc", "#2563eb"),
            hover_color=("#0052a3", "#1d4ed8"),
            command=self.refresh_process_list,
        )
        self.btn_refresh.pack(side="right")

    def _build_table(self) -> None:
        # Table Header
        self.table_header = ctk.CTkFrame(
            self,
            height=34,
            fg_color=("#f3f4f6", "#1e222a"),
            corner_radius=6,
            border_width=1,
            border_color=("#e5e7eb", "#2e3440"),
        )
        self.table_header.pack(fill="x", padx=16, pady=(0, 4))

        cols = [
            ("PID", 80),
            ("Process Name", 240),
            ("Type", 140),
            ("CPU %", 100),
            ("Memory", 110),
            ("User", 110),
            ("Action", 110),
        ]

        for title, width in cols:
            lbl = ctk.CTkLabel(
                self.table_header,
                text=title,
                width=width,
                font=FONT_BODY_BOLD,
                text_color=("#4b5563", "#9ca3af"),
                anchor="w",
            )
            lbl.pack(side="left", padx=8)

        # Scrollable rows container
        self.rows_container = ctk.CTkScrollableFrame(self, fg_color="transparent")
        self.rows_container.pack(fill="both", expand=True, padx=16, pady=(0, 10))

    def refresh_process_list(self) -> None:
        """Fetch fresh process data from ProcessManager."""
        self.cached_processes = self.pm.list_processes(sort_by="cpu_percent", reverse=True)
        self._apply_filters()

    def _apply_filters(self) -> None:
        filter_text = self.search_var.get().strip().lower()
        mode = self.filter_mode.get()
        sort_choice = self.sort_var.get()

        procs = list(self.cached_processes)

        # Filter mode
        if mode == "User Apps Only":
            procs = [p for p in procs if not p.is_system]

        # Search query
        if filter_text:
            procs = [
                p for p in procs
                if filter_text in p.name.lower() or filter_text in str(p.pid)
            ]

        # Sorting
        if sort_choice == "Highest CPU":
            procs.sort(key=lambda x: x.cpu_percent, reverse=True)
        elif sort_choice == "Highest Memory":
            procs.sort(key=lambda x: x.memory_mb, reverse=True)
        elif sort_choice == "Process Name":
            procs.sort(key=lambda x: x.name.lower())
        elif sort_choice == "Process ID (PID)":
            procs.sort(key=lambda x: x.pid)

        self._render_rows(procs)

    def _render_rows(self, procs: List[ProcessInfo]) -> None:
        for child in self.rows_container.winfo_children():
            child.destroy()

        self.summary_label.configure(
            text=f"Showing {len(procs)} of {len(self.cached_processes)} active processes"
        )

        if not procs:
            empty_lbl = ctk.CTkLabel(
                self.rows_container,
                text="No processes match your filter query.",
                font=FONT_BODY,
                text_color="#8b949e",
            )
            empty_lbl.pack(pady=30)
            return

        # Render top 50 processes for smooth responsive UI
        for p in procs[:50]:
            row = ctk.CTkFrame(
                self.rows_container,
                height=38,
                fg_color=("#ffffff", "#22252a"),
                corner_radius=4,
                border_width=1,
                border_color=("#f3f4f6", "#2a2d34"),
            )
            row.pack(fill="x", pady=2)

            # PID
            pid_lbl = ctk.CTkLabel(row, text=str(p.pid), width=80, font=FONT_MONO, anchor="w")
            pid_lbl.pack(side="left", padx=8)

            # Name
            name_text = p.name if len(p.name) <= 28 else p.name[:26] + "..."
            name_lbl = ctk.CTkLabel(row, text=name_text, width=240, font=FONT_BODY_BOLD, anchor="w")
            name_lbl.pack(side="left", padx=8)

            # Category / Protected Badge
            cat_box = ctk.CTkFrame(row, width=140, fg_color="transparent")
            cat_box.pack(side="left", padx=8)
            if p.is_system:
                badge = ctk.CTkLabel(
                    cat_box,
                    text=" System ",
                    font=FONT_SMALL,
                    text_color=("#6b7280", "#9ca3af"),
                    fg_color=("#f3f4f6", "#2a2e35"),
                    corner_radius=4,
                )
            else:
                badge = ctk.CTkLabel(
                    cat_box,
                    text=" User ",
                    font=FONT_SMALL,
                    text_color=("#0066cc", "#38bdf8"),
                    fg_color=("#e0edff", "#1e293b"),
                    corner_radius=4,
                )
            badge.pack(anchor="w")

            # CPU %
            cpu_color = "#dc2626" if p.cpu_percent >= 50 else "#d97706" if p.cpu_percent >= 20 else ("#374151", "#d1d5db")
            cpu_lbl = ctk.CTkLabel(
                row,
                text=format_percent(p.cpu_percent),
                width=100,
                font=FONT_MONO,
                text_color=cpu_color,
                anchor="w",
            )
            cpu_lbl.pack(side="left", padx=8)

            # Memory MB
            mem_str = f"{p.memory_mb:.1f} MB"
            mem_lbl = ctk.CTkLabel(row, text=mem_str, width=110, font=FONT_MONO, anchor="w")
            mem_lbl.pack(side="left", padx=8)

            # User
            clean_user = p.username.split("\\")[-1] if "\\" in p.username else p.username
            user_lbl = ctk.CTkLabel(row, text=clean_user[:14], width=110, font=FONT_SMALL, text_color=("#6b7280", "#9ca3af"), anchor="w")
            user_lbl.pack(side="left", padx=8)

            # Action Button
            action_box = ctk.CTkFrame(row, width=110, fg_color="transparent")
            action_box.pack(side="left", padx=8)

            if p.is_killable:
                btn_kill = ctk.CTkButton(
                    action_box,
                    text="End Task",
                    width=85,
                    height=26,
                    font=FONT_SMALL,
                    corner_radius=4,
                    fg_color=("#dc2626", "#dc2626"),
                    hover_color=("#b91c1c", "#b91c1c"),
                    command=lambda proc_info=p: self._confirm_terminate_process(proc_info),
                )
                btn_kill.pack(side="left")
            else:
                lbl_locked = ctk.CTkLabel(
                    action_box, text="Protected", font=FONT_SMALL, text_color=("#9ca3af", "#6b7280")
                )
                lbl_locked.pack(side="left")

    def _confirm_terminate_process(self, proc: ProcessInfo) -> None:
        """Ask confirmation before terminating user process."""
        ans = msgbox.askyesno(
            title="Confirm Application Termination",
            message=(
                f"Are you sure you want to close '{proc.name}' (PID: {proc.pid})?\n\n"
                f"Memory in use: {proc.memory_mb:.1f} MB\n"
                f"CPU in use: {proc.cpu_percent:.1f}%\n\n"
                f"Any unsaved work in this application may be lost."
            ),
            icon="warning",
        )
        if not ans:
            return

        success, msg = self.pm.terminate_process(
            proc.pid,
            expected_name=proc.name,
            expected_create_time=proc.create_time,
        )
        if success:
            msgbox.showinfo("Process Terminated", msg)
        else:
            msgbox.showwarning("Action Blocked", msg)

        self.refresh_process_list()
