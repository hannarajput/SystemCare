"""
Storage Analyzer and Safe Space Cleaner View.
Discovers large space hogs and safe-to-clean temporary caches (User Temp, Crash Dumps, Browser Caches).
Provides file preview and requires explicit user confirmation before any deletion.
Protects system files and personal folders at all times.
"""

import os
import subprocess
import threading
from typing import List, Optional
import tkinter.filedialog as filedialog
import tkinter.messagebox as msgbox
import customtkinter as ctk

from ...core.storage_analyzer import (
    CleanableGroup,
    LargeFileItem,
    StorageAnalysisResult,
    StorageAnalyzer,
    StorageCleanupResult,
)
from ...utils.formatters import format_bytes, format_timestamp
from ..theme import (
    FONT_BODY,
    FONT_BODY_BOLD,
    FONT_MONO,
    FONT_SMALL,
    FONT_SUBTITLE,
    FONT_TITLE,
)


class StorageView(ctk.CTkScrollableFrame):
    """
    Storage Analyzer with large file identification and previewed temporary file cleanup.
    """

    def __init__(self, master, storage_analyzer: Optional[StorageAnalyzer] = None, **kwargs):
        super().__init__(master, fg_color="transparent", **kwargs)
        self.analyzer = storage_analyzer or StorageAnalyzer()
        self.analysis_result: Optional[StorageAnalysisResult] = None
        self.cached_large_files: List[LargeFileItem] = []
        self._is_cleaning = False

        self._build_header()
        self._build_safety_banner()
        self._build_toolbar()
        self._build_cleanable_section()
        self._build_large_files_section()

    def cancel_active_tasks(self) -> None:
        """Cancel active storage analysis when application exits."""
        if self.analyzer.is_analyzing:
            self.analyzer.cancel_analysis()

    def _build_header(self) -> None:
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.pack(fill="x", padx=16, pady=(12, 10))

        title = ctk.CTkLabel(header, text="Storage Analysis", font=FONT_TITLE, anchor="w")
        title.pack(side="left")

        self.status_label = ctk.CTkLabel(
            header, text="Ready to scan", font=FONT_BODY, text_color=("#6b7280", "#9ca3af")
        )
        self.status_label.pack(side="right")

    def _build_safety_banner(self) -> None:
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
            text=" SAFETY ",
            font=FONT_SMALL,
            fg_color=("#f0fdf4", "#1a2a1f"),
            text_color=("#16a34a", "#22c55e"),
            corner_radius=4,
        )
        tag.pack(side="left", padx=(0, 12))

        text_box = ctk.CTkFrame(inner, fg_color="transparent")
        text_box.pack(side="left", fill="both", expand=True)

        lbl = ctk.CTkLabel(
            text_box,
            text="Protected Locations",
            font=FONT_BODY_BOLD,
            anchor="w",
        )
        lbl.pack(anchor="w")

        sub = ctk.CTkLabel(
            text_box,
            text=(
                "Windows system directories (C:\\Windows, System32), Program Files, and personal document folders "
                "are strictly protected. Only non-essential scratch files (%TEMP%, crash dumps, web caches) are eligible for cleaning."
            ),
            font=FONT_SMALL,
            text_color=("#4b5563", "#9ca3af"),
            anchor="w",
            wraplength=700,
            justify="left",
        )
        sub.pack(anchor="w", pady=(2, 0))

    def _build_toolbar(self) -> None:
        bar = ctk.CTkFrame(
            self,
            fg_color=("#ffffff", "#22252a"),
            corner_radius=6,
            border_width=1,
            border_color=("#e5e7eb", "#2e3440"),
        )
        bar.pack(fill="x", padx=16, pady=(0, 12))

        inner = ctk.CTkFrame(bar, fg_color="transparent")
        inner.pack(fill="x", padx=12, pady=10)

        # Target folder entry
        default_dir = os.environ.get("USERPROFILE", "C:\\")
        self.path_var = ctk.StringVar(value=default_dir)

        lbl = ctk.CTkLabel(inner, text="Target Path:", font=FONT_BODY_BOLD)
        lbl.pack(side="left", padx=(0, 8))

        self.entry_path = ctk.CTkEntry(inner, textvariable=self.path_var, width=280, height=32, font=FONT_BODY, corner_radius=6)
        self.entry_path.pack(side="left", padx=(0, 8))

        btn_browse = ctk.CTkButton(
            inner,
            text="Browse...",
            width=90,
            height=32,
            font=FONT_BODY,
            corner_radius=6,
            fg_color=("#f3f4f6", "#2a2e35"),
            text_color=("#111827", "#f3f4f6"),
            hover_color=("#e5e7eb", "#323740"),
            command=self._browse_directory,
        )
        btn_browse.pack(side="left", padx=(0, 10))

        # Min file size dropdown
        lbl_sz = ctk.CTkLabel(inner, text="Min Large File:", font=FONT_BODY)
        lbl_sz.pack(side="left", padx=(0, 6))

        self.size_var = ctk.StringVar(value="50 MB")
        self.size_menu = ctk.CTkOptionMenu(
            inner,
            values=["20 MB", "50 MB", "100 MB", "250 MB", "500 MB", "1 GB"],
            variable=self.size_var,
            width=100,
            height=32,
            font=FONT_BODY,
            corner_radius=6,
        )
        self.size_menu.pack(side="left", padx=(0, 12))

        self.btn_analyze = ctk.CTkButton(
            inner,
            text="Analyze Storage",
            font=FONT_BODY_BOLD,
            width=135,
            height=32,
            corner_radius=6,
            fg_color=("#0066cc", "#2563eb"),
            hover_color=("#0052a3", "#1d4ed8"),
            command=self._start_analysis_thread,
        )
        self.btn_analyze.pack(side="right")

    def _build_cleanable_section(self) -> None:
        self.cleanable_frame = ctk.CTkFrame(
            self,
            corner_radius=6,
            fg_color=("#ffffff", "#22252a"),
            border_width=1,
            border_color=("#e5e7eb", "#2e3440"),
        )
        self.cleanable_frame.pack(fill="x", padx=16, pady=(0, 12))

        hdr = ctk.CTkFrame(self.cleanable_frame, fg_color="transparent")
        hdr.pack(fill="x", padx=16, pady=(12, 6))

        t = ctk.CTkLabel(hdr, text="Temporary Files", font=FONT_SUBTITLE)
        t.pack(side="left")

        self.cleanable_container = ctk.CTkFrame(self.cleanable_frame, fg_color="transparent")
        self.cleanable_container.pack(fill="x", padx=16, pady=(0, 14))

        # Initial prompt
        init_lbl = ctk.CTkLabel(
            self.cleanable_container,
            text="Click 'Analyze Storage' to discover cleanable scratch caches.",
            font=FONT_BODY,
            text_color=("#6b7280", "#9ca3af"),
        )
        init_lbl.pack(pady=15)

    def _build_large_files_section(self) -> None:
        self.large_frame = ctk.CTkFrame(
            self,
            corner_radius=6,
            fg_color=("#ffffff", "#22252a"),
            border_width=1,
            border_color=("#e5e7eb", "#2e3440"),
        )
        self.large_frame.pack(fill="x", padx=16, pady=(0, 16))

        hdr = ctk.CTkFrame(self.large_frame, fg_color="transparent")
        hdr.pack(fill="x", padx=16, pady=(12, 6))

        t = ctk.CTkLabel(hdr, text="Large Files", font=FONT_SUBTITLE)
        t.pack(side="left")

        self.large_container = ctk.CTkFrame(self.large_frame, fg_color="transparent")
        self.large_container.pack(fill="x", padx=16, pady=(0, 14))

        init_lbl = ctk.CTkLabel(
            self.large_container,
            text="Large files exceeding the threshold will be listed here after analysis.",
            font=FONT_BODY,
            text_color=("#6b7280", "#9ca3af"),
        )
        init_lbl.pack(pady=15)

    def _browse_directory(self) -> None:
        chosen = filedialog.askdirectory(initialdir=self.path_var.get())
        if chosen:
            self.path_var.set(chosen)

    def _start_analysis_thread(self) -> None:
        if self.analyzer.is_analyzing or self._is_cleaning:
            return

        target = self.path_var.get().strip()
        if not target or not os.path.exists(target):
            msgbox.showerror("Invalid Path", "Please provide a valid existing directory.")
            return

        size_text = self.size_var.get()
        size_mb = float(size_text.replace("MB", "").replace("GB", "").strip())
        if "GB" in size_text:
            size_mb *= 1024.0

        self.btn_analyze.configure(state="disabled")
        self.status_label.configure(text="Analyzing storage spaces...")

        def worker():
            res = self.analyzer.analyze_target(
                target_path=target,
                min_large_file_mb=size_mb,
                max_large_files=50,
            )
            try:
                if self.winfo_exists():
                    self.after(0, lambda: self._on_analysis_done(res))
            except Exception:
                pass

        threading.Thread(target=worker, daemon=True).start()

    def _on_analysis_done(self, result: StorageAnalysisResult) -> None:
        self.btn_analyze.configure(state="normal")
        self.analysis_result = result
        self.cached_large_files = result.large_files

        self.status_label.configure(
            text=f"Analysis complete: {result.scanned_files_count} files ({format_bytes(result.total_size_scanned_bytes)})"
        )
        self._render_cleanable(result.cleanable_groups)
        self._render_large_files(result.large_files)

    def _render_cleanable(self, groups: List[CleanableGroup]) -> None:
        for child in self.cleanable_container.winfo_children():
            child.destroy()

        if not groups:
            lbl = ctk.CTkLabel(
                self.cleanable_container,
                text="✔ No temporary files or caches found. Disk is clean!",
                font=FONT_BODY,
                text_color="#3fb950",
            )
            lbl.pack(pady=15)
            return

        for grp in groups:
            row = ctk.CTkFrame(self.cleanable_container, fg_color=("#f0f3f8", "#16191f"), corner_radius=6)
            row.pack(fill="x", pady=4)

            inner = ctk.CTkFrame(row, fg_color="transparent")
            inner.pack(fill="x", padx=12, pady=10)

            # Left info
            left = ctk.CTkFrame(inner, fg_color="transparent")
            left.pack(side="left", fill="both", expand=True)

            t_box = ctk.CTkFrame(left, fg_color="transparent")
            t_box.pack(fill="x")

            title_lbl = ctk.CTkLabel(t_box, text=grp.name, font=FONT_BODY_BOLD, anchor="w")
            title_lbl.pack(side="left", padx=(0, 8))

            badge = ctk.CTkLabel(
                t_box,
                text=f" {grp.safety_rating} ",
                font=FONT_SMALL,
                text_color="#ffffff",
                fg_color="#1a7f37" if "Very" in grp.safety_rating else "#0969da",
                corner_radius=4,
            )
            badge.pack(side="left")

            desc_lbl = ctk.CTkLabel(
                left,
                text=grp.description,
                font=FONT_SMALL,
                text_color="#8b949e",
                anchor="w",
            )
            desc_lbl.pack(anchor="w", pady=(2, 0))

            # Right info & Clean Button
            right = ctk.CTkFrame(inner, fg_color="transparent")
            right.pack(side="right", padx=(10, 0))

            sz_lbl = ctk.CTkLabel(
                right,
                text=f"{format_bytes(grp.total_bytes)} ({grp.items_count} files)",
                font=FONT_BODY_BOLD,
                text_color="#c9d1d9",
                anchor="e",
            )
            sz_lbl.pack(side="left", padx=(0, 12))

            btn_clean = ctk.CTkButton(
                right,
                text="Preview & Clean",
                font=FONT_SMALL,
                width=110,
                height=28,
                fg_color=("#0969da", "#2f81f7"),
                hover_color=("#0854b0", "#1f6feb"),
                command=lambda g=grp: self._preview_and_clean_group(g),
            )
            btn_clean.pack(side="left")

    def _render_large_files(self, files: List[LargeFileItem]) -> None:
        for child in self.large_container.winfo_children():
            child.destroy()

        if not files:
            lbl = ctk.CTkLabel(
                self.large_container,
                text="No files exceeded the specified large file threshold.",
                font=FONT_BODY,
                text_color="#8b949e",
            )
            lbl.pack(pady=15)
            return

        # Header
        hdr = ctk.CTkFrame(self.large_container, height=30, fg_color=("#e6ebf2", "#16191f"), corner_radius=4)
        hdr.pack(fill="x", pady=(0, 4))
        for t, w in [("Filename", 220), ("Category", 110), ("Size", 100), ("Path", 320), ("Action", 100)]:
            ctk.CTkLabel(hdr, text=t, width=w, font=FONT_BODY_BOLD, text_color="#8b949e", anchor="w").pack(
                side="left", padx=6
            )

        for item in files[:35]:
            row = ctk.CTkFrame(self.large_container, fg_color=("#f0f3f8", "#16191f"), corner_radius=4)
            row.pack(fill="x", pady=2)

            # Name
            n_text = item.filename if len(item.filename) <= 24 else item.filename[:22] + "..."
            ctk.CTkLabel(row, text=n_text, width=220, font=FONT_BODY_BOLD, anchor="w").pack(side="left", padx=6)

            # Category
            ctk.CTkLabel(row, text=item.category, width=110, font=FONT_SMALL, text_color="#8b949e", anchor="w").pack(
                side="left", padx=6
            )

            # Size
            ctk.CTkLabel(row, text=format_bytes(item.size_bytes), width=100, font=FONT_MONO, anchor="w").pack(
                side="left", padx=6
            )

            # Path
            p_text = item.path if len(item.path) <= 45 else "..." + item.path[-42:]
            ctk.CTkLabel(row, text=p_text, width=320, font=FONT_SMALL, text_color="#8b949e", anchor="w").pack(
                side="left", padx=6
            )

            # Action
            act_box = ctk.CTkFrame(row, width=100, fg_color="transparent")
            act_box.pack(side="left", padx=6)

            btn_show = ctk.CTkButton(
                act_box,
                text="Show",
                width=45,
                height=22,
                font=FONT_SMALL,
                fg_color=("#e6ebf2", "#2d3442"),
                text_color=("#1f2328", "#c9d1d9"),
                command=lambda p=item.path: subprocess.run(["explorer", f"/select,{os.path.normpath(p)}"]),
            )
            btn_show.pack(side="left", padx=(0, 4))

            btn_rec = ctk.CTkButton(
                act_box,
                text="Recycle",
                width=50,
                height=22,
                font=FONT_SMALL,
                fg_color="#cf222e",
                hover_color="#f85149",
                command=lambda it=item: self._recycle_single_large_file(it),
            )
            btn_rec.pack(side="left")

    def _preview_and_clean_group(self, group: CleanableGroup) -> None:
        """Show preview dialog of files to clean and obtain explicit confirmation."""
        preview_win = ctk.CTkToplevel(self)
        preview_win.title(f"Preview & Confirm: {group.name}")
        preview_win.geometry("650x450")
        preview_win.grab_set()

        hdr = ctk.CTkFrame(preview_win, fg_color="transparent")
        hdr.pack(fill="x", padx=20, pady=(15, 10))

        ctk.CTkLabel(hdr, text=f"Review Files to Clean: {group.name}", font=FONT_SUBTITLE).pack(anchor="w")
        ctk.CTkLabel(
            hdr,
            text=f"Total: {group.items_count} files ({format_bytes(group.total_bytes)}). Targets will be moved to the Recycle Bin.",
            font=FONT_SMALL,
            text_color="#8b949e",
        ).pack(anchor="w")

        # Scrollable preview list
        list_box = ctk.CTkScrollableFrame(preview_win, height=270)
        list_box.pack(fill="both", expand=True, padx=20, pady=(0, 15))

        for fpath in group.file_paths[:100]:
            f_row = ctk.CTkFrame(list_box, fg_color="transparent")
            f_row.pack(fill="x", pady=2)
            try:
                sz = os.path.getsize(fpath)
                sz_str = format_bytes(sz)
            except OSError:
                sz_str = "0 B"
            ctk.CTkLabel(f_row, text=os.path.basename(fpath)[:35], font=FONT_SMALL, width=220, anchor="w").pack(
                side="left"
            )
            ctk.CTkLabel(f_row, text=sz_str, font=FONT_MONO, width=80, anchor="w").pack(side="left")
            ctk.CTkLabel(f_row, text=fpath[:45], font=FONT_SMALL, text_color="#8b949e", anchor="w").pack(
                side="left", fill="x", expand=True
            )

        # Action Buttons
        bot_bar = ctk.CTkFrame(preview_win, fg_color="transparent")
        bot_bar.pack(fill="x", padx=20, pady=(0, 15))

        def execute_clean():
            preview_win.destroy()
            self._is_cleaning = True
            self.btn_analyze.configure(state="disabled")

            def worker():
                res: StorageCleanupResult = self.analyzer.clean_files(group.file_paths)
                try:
                    if self.winfo_exists():
                        self.after(0, lambda: self._on_clean_completed(res))
                except Exception:
                    pass

            threading.Thread(target=worker, daemon=True).start()

        btn_cancel = ctk.CTkButton(bot_bar, text="Cancel", width=90, command=preview_win.destroy)
        btn_cancel.pack(side="right", padx=(8, 0))

        btn_confirm = ctk.CTkButton(
            bot_bar,
            text=f"Confirm Move to Recycle Bin ({format_bytes(group.total_bytes)})",
            font=FONT_BODY_BOLD,
            fg_color="#cf222e",
            hover_color="#f85149",
            command=execute_clean,
        )
        btn_confirm.pack(side="right")

    def _on_clean_completed(self, res: StorageCleanupResult) -> None:
        self._is_cleaning = False
        self.btn_analyze.configure(state="normal")

        msgbox.showinfo(
            "Cleanup Finished",
            f"Successfully moved {res.files_recycled_count} file(s) to the Windows Recycle Bin!\n"
            f"File size moved to Recycle Bin: {format_bytes(res.bytes_moved_to_recycle_bin)}.\n"
            f"Actual physical disk space freed: {format_bytes(res.actual_disk_freed_bytes)}.\n"
            f"Skipped / In-use files: {res.skipped_count}.",
        )
        # Re-analyze to refresh cleanable status
        self._start_analysis_thread()

    def _recycle_single_large_file(self, item: LargeFileItem) -> None:
        confirmed = msgbox.askyesno(
            title="Confirm Recycle",
            message=(
                f"Move this file to the Windows Recycle Bin?\n\n"
                f"File: {item.filename}\n"
                f"Size: {format_bytes(item.size_bytes)}\n"
                f"Location: {item.path}\n\n"
                f"You can restore it from the Recycle Bin if needed."
            ),
            icon="warning",
        )
        if not confirmed:
            return

        res: StorageCleanupResult = self.analyzer.clean_files([item.path])
        if res.files_recycled_count > 0:
            msgbox.showinfo(
                "File Recycled",
                f"Moved '{item.filename}' to the Recycle Bin ({format_bytes(res.bytes_moved_to_recycle_bin)}).\n"
                f"Actual physical disk space freed: {format_bytes(res.actual_disk_freed_bytes)}.",
            )
            self._start_analysis_thread()
        else:
            msgbox.showwarning("Notice", f"Could not recycle file: {res.skipped_reasons}")
