"""
Duplicate File Finder View.
Scans user-selected folders using staged cryptographic hashing (Size -> 4KB Hash -> SHA-256).
Presents duplicate groups with safe selection presets and moves confirmed files to Windows Recycle Bin.
Guarantees preservation of at least one copy and never deletes files automatically.
"""

import os
import subprocess
import threading
from typing import List, Optional
import tkinter.filedialog as filedialog
import tkinter.messagebox as msgbox
import customtkinter as ctk

from ...core.duplicate_finder import DuplicateCleanupResult, DuplicateFileEntry, DuplicateFinder, DuplicateGroup
from ...utils.formatters import format_bytes, format_timestamp
from ..theme import (
    FONT_BODY,
    FONT_BODY_BOLD,
    FONT_MONO,
    FONT_SMALL,
    FONT_SUBTITLE,
    FONT_TITLE,
)


class DuplicateView(ctk.CTkFrame):
    """
    Duplicate file detector interface with responsive multithreading,
    safe selection presets, and group preservation.
    """

    def __init__(self, master, duplicate_finder: Optional[DuplicateFinder] = None, **kwargs):
        super().__init__(master, fg_color="transparent", **kwargs)
        self.finder = duplicate_finder or DuplicateFinder()
        self.duplicate_groups: List[DuplicateGroup] = []
        self._is_deleting = False

        self._build_header()
        self._build_folder_selector()
        self._build_progress_bar()
        self._build_actions_toolbar()
        self._build_results_area()

    def cancel_active_tasks(self) -> None:
        """Cancel running duplicate scan when application is closing."""
        if self.finder.is_scanning:
            self.finder.cancel_scan()

    def _build_header(self) -> None:
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.pack(fill="x", padx=16, pady=(12, 10))

        title = ctk.CTkLabel(header, text="Duplicate Files", font=FONT_TITLE, anchor="w")
        title.pack(side="left")

        self.status_label = ctk.CTkLabel(
            header, text="Ready to scan", font=FONT_BODY, text_color=("#6b7280", "#9ca3af")
        )
        self.status_label.pack(side="right")

    def _build_folder_selector(self) -> None:
        box = ctk.CTkFrame(
            self,
            fg_color=("#ffffff", "#22252a"),
            corner_radius=6,
            border_width=1,
            border_color=("#e5e7eb", "#2e3440"),
        )
        box.pack(fill="x", padx=16, pady=(0, 10))

        inner = ctk.CTkFrame(box, fg_color="transparent")
        inner.pack(fill="x", padx=12, pady=10)

        # Default path to user Downloads
        default_dir = os.path.join(os.environ.get("USERPROFILE", "C:\\"), "Downloads")
        if not os.path.exists(default_dir):
            default_dir = os.environ.get("USERPROFILE", "C:\\")

        self.path_var = ctk.StringVar(value=default_dir)
        self.path_entry = ctk.CTkEntry(
            inner, textvariable=self.path_var, font=FONT_BODY, height=34, corner_radius=6
        )
        self.path_entry.pack(side="left", fill="x", expand=True, padx=(0, 10))

        btn_browse = ctk.CTkButton(
            inner,
            text="Browse...",
            font=FONT_BODY,
            width=110,
            height=34,
            corner_radius=6,
            fg_color=("#f3f4f6", "#2a2e35"),
            text_color=("#111827", "#f3f4f6"),
            hover_color=("#e5e7eb", "#323740"),
            command=self._browse_directory,
        )
        btn_browse.pack(side="left", padx=(0, 10))

        self.btn_scan = ctk.CTkButton(
            inner,
            text="Scan for Duplicates",
            font=FONT_BODY_BOLD,
            width=140,
            height=34,
            corner_radius=6,
            fg_color=("#0066cc", "#2563eb"),
            hover_color=("#0052a3", "#1d4ed8"),
            command=self._start_scan_thread,
        )
        self.btn_scan.pack(side="left", padx=(0, 6))

        self.btn_cancel = ctk.CTkButton(
            inner,
            text="Cancel",
            font=FONT_BODY,
            width=80,
            height=34,
            corner_radius=6,
            fg_color=("#dc2626", "#dc2626"),
            hover_color=("#b91c1c", "#b91c1c"),
            state="disabled",
            command=self._cancel_scan,
        )
        self.btn_cancel.pack(side="left")

    def _build_progress_bar(self) -> None:
        self.prog_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.prog_frame.pack(fill="x", padx=16, pady=(0, 8))

        self.prog_bar = ctk.CTkProgressBar(self.prog_frame, height=4, progress_color="#2563eb")
        self.prog_bar.set(0.0)
        self.prog_bar.pack(fill="x")

        self.prog_text = ctk.CTkLabel(
            self.prog_frame,
            text="Select a directory to scan. Duplicate files are identified using SHA-256 byte verification.",
            font=FONT_SMALL,
            text_color=("#6b7280", "#9ca3af"),
            anchor="w",
        )
        self.prog_text.pack(anchor="w", pady=(2, 0))

    def _build_actions_toolbar(self) -> None:
        self.actions_bar = ctk.CTkFrame(
            self,
            fg_color=("#ffffff", "#22252a"),
            corner_radius=6,
            border_width=1,
            border_color=("#e5e7eb", "#2e3440"),
        )
        self.actions_bar.pack(fill="x", padx=16, pady=(0, 10))

        inner = ctk.CTkFrame(self.actions_bar, fg_color="transparent")
        inner.pack(fill="x", padx=12, pady=8)

        lbl = ctk.CTkLabel(inner, text="Presets:", font=FONT_BODY_BOLD)
        lbl.pack(side="left", padx=(0, 8))

        btn_keep_new = ctk.CTkButton(
            inner,
            text="Keep Newest",
            font=FONT_SMALL,
            width=90,
            height=26,
            corner_radius=4,
            fg_color=("#f3f4f6", "#2a2e35"),
            text_color=("#111827", "#f3f4f6"),
            hover_color=("#e5e7eb", "#323740"),
            command=lambda: self._apply_selection_preset("keep_newest"),
        )
        btn_keep_new.pack(side="left", padx=4)

        btn_keep_old = ctk.CTkButton(
            inner,
            text="Keep Oldest",
            font=FONT_SMALL,
            width=90,
            height=26,
            corner_radius=4,
            fg_color=("#f3f4f6", "#2a2e35"),
            text_color=("#111827", "#f3f4f6"),
            hover_color=("#e5e7eb", "#323740"),
            command=lambda: self._apply_selection_preset("keep_oldest"),
        )
        btn_keep_old.pack(side="left", padx=4)

        btn_clear = ctk.CTkButton(
            inner,
            text="Clear Selection",
            font=FONT_SMALL,
            width=90,
            height=26,
            corner_radius=4,
            fg_color=("#f3f4f6", "#2a2e35"),
            text_color=("#111827", "#f3f4f6"),
            hover_color=("#e5e7eb", "#323740"),
            command=lambda: self._apply_selection_preset("clear"),
        )
        btn_clear.pack(side="left", padx=4)

        # Right-aligned Recycle Action Button
        self.btn_delete_selected = ctk.CTkButton(
            inner,
            text="Move Selected to Recycle Bin",
            font=FONT_BODY_BOLD,
            height=30,
            corner_radius=6,
            fg_color=("#dc2626", "#dc2626"),
            hover_color=("#b91c1c", "#b91c1c"),
            command=self._confirm_delete_selected,
        )
        self.btn_delete_selected.pack(side="right")

    def _build_results_area(self) -> None:
        self.results_scroll = ctk.CTkScrollableFrame(self, fg_color="transparent")
        self.results_scroll.pack(fill="both", expand=True, padx=16, pady=(0, 10))

    def _browse_directory(self) -> None:
        chosen = filedialog.askdirectory(initialdir=self.path_var.get())
        if chosen:
            self.path_var.set(chosen)

    def _start_scan_thread(self) -> None:
        if self.finder.is_scanning or self._is_deleting:
            return

        target = self.path_var.get().strip()
        if not target or not os.path.exists(target):
            msgbox.showerror("Invalid Directory", "Please select a valid folder on your computer.")
            return

        self.btn_scan.configure(state="disabled")
        self.btn_cancel.configure(state="normal")
        self.prog_bar.set(0.0)
        self.prog_bar.configure(mode="indeterminate")
        self.prog_bar.start()

        def scan_worker():
            def progress(count, dups, curr_file):
                try:
                    if self.winfo_exists():
                        self.after(
                            0,
                            lambda: self.prog_text.configure(
                                text=f"Scanning file #{count} | Found {dups} duplicate groups... ({os.path.basename(curr_file)[:35]})"
                            ),
                        )
                except Exception:
                    pass

            groups = self.finder.scan_folder(target, min_size_bytes=1, progress_callback=progress)
            try:
                if self.winfo_exists():
                    self.after(0, lambda: self._on_scan_completed(groups))
            except Exception:
                pass

        threading.Thread(target=scan_worker, daemon=True).start()

    def _cancel_scan(self) -> None:
        self.finder.cancel_scan()
        self.btn_cancel.configure(state="disabled")
        self.status_label.configure(text="Scan cancellation requested...")

    def _on_scan_completed(self, groups: List[DuplicateGroup]) -> None:
        self.prog_bar.stop()
        self.prog_bar.configure(mode="determinate")
        self.prog_bar.set(1.0)
        self.btn_scan.configure(state="normal")
        self.btn_cancel.configure(state="disabled")

        self.duplicate_groups = groups
        # Auto-select all except newest while preserving original
        self.finder.auto_select_duplicates(self.duplicate_groups, strategy="keep_newest")

        total_dups = sum(len(g.files) for g in groups)
        reclaimable = sum(g.reclaimable_bytes for g in groups)

        self.status_label.configure(
            text=f"Found {len(groups)} groups ({total_dups} duplicate files, estimated {format_bytes(reclaimable)} recoverable)"
        )
        self.prog_text.configure(
            text=f"Scan complete. {len(groups)} duplicate sets identified. Review files below before recycling."
        )

        self._render_groups()
        self._update_delete_button_label()

    def _apply_selection_preset(self, preset: str) -> None:
        self.finder.auto_select_duplicates(self.duplicate_groups, strategy=preset)
        self._render_groups()
        self._update_delete_button_label()

    def _update_delete_button_label(self) -> None:
        selected_count = 0
        selected_bytes = 0
        for g in self.duplicate_groups:
            for f in g.files:
                if f.selected:
                    selected_count += 1
                    selected_bytes += f.size_bytes

        self.btn_delete_selected.configure(
            text=f"Recycle Selected ({selected_count} files, {format_bytes(selected_bytes)})"
        )

    def _render_groups(self) -> None:
        for child in self.results_scroll.winfo_children():
            child.destroy()

        if not self.duplicate_groups:
            lbl = ctk.CTkLabel(
                self.results_scroll,
                text="No duplicate files found in this folder.",
                font=FONT_BODY,
                text_color=("#6b7280", "#9ca3af"),
            )
            lbl.pack(pady=40)
            return

        for g in self.duplicate_groups:
            group_card = ctk.CTkFrame(
                self.results_scroll,
                corner_radius=6,
                fg_color=("#ffffff", "#22252a"),
                border_width=1,
                border_color=("#e5e7eb", "#2e3440"),
            )
            group_card.pack(fill="x", pady=4)

            # Group header
            gh = ctk.CTkFrame(group_card, fg_color=("#f3f4f6", "#1e222a"), corner_radius=4)
            gh.pack(fill="x", padx=10, pady=(8, 4))

            g_title = ctk.CTkLabel(
                gh,
                text=f"{g.group_id} — {len(g.files)} Identical Copies ({format_bytes(g.file_size_bytes)} each)",
                font=FONT_BODY_BOLD,
                anchor="w",
            )
            g_title.pack(side="left", padx=10, pady=6)

            reclaim_lbl = ctk.CTkLabel(
                gh,
                text=f"Recoverable: {format_bytes(g.reclaimable_bytes)} | SHA256: {g.sha256_hash[:12]}...",
                font=FONT_SMALL,
                text_color="#8b949e",
                anchor="e",
            )
            reclaim_lbl.pack(side="right", padx=10)

            # File rows
            for f_entry in g.files:
                frow = ctk.CTkFrame(group_card, fg_color="transparent")
                frow.pack(fill="x", padx=12, pady=3)

                chk_var = ctk.BooleanVar(value=f_entry.selected)

                def on_toggle(entry=f_entry, var=chk_var, grp=g):
                    entry.selected = var.get()
                    # Check if all files in group are selected; if so, notify
                    all_sel = all(f.selected for f in grp.files)
                    if all_sel and len(grp.files) > 1:
                        # Uncheck this one and warn
                        entry.selected = False
                        var.set(False)
                        msgbox.showinfo(
                            "Copy Preserved",
                            f"Safety rule: At least one original copy of '{entry.filename}' must be preserved.",
                        )
                    self._update_delete_button_label()

                chk = ctk.CTkCheckBox(
                    frow,
                    text="",
                    variable=chk_var,
                    width=20,
                    command=on_toggle,
                )
                chk.pack(side="left", padx=(0, 8))

                name_lbl = ctk.CTkLabel(
                    frow, text=f_entry.filename, font=FONT_BODY_BOLD, width=200, anchor="w"
                )
                name_lbl.pack(side="left", padx=(0, 10))

                path_lbl = ctk.CTkLabel(
                    frow,
                    text=f_entry.path,
                    font=FONT_SMALL,
                    text_color="#8b949e",
                    anchor="w",
                )
                path_lbl.pack(side="left", fill="x", expand=True, padx=(0, 10))

                mtime_lbl = ctk.CTkLabel(
                    frow,
                    text=format_timestamp(f_entry.modified_time),
                    font=FONT_SMALL,
                    text_color="#8b949e",
                    width=130,
                    anchor="e",
                )
                mtime_lbl.pack(side="right", padx=(0, 8))

                btn_open = ctk.CTkButton(
                    frow,
                    text="Show",
                    font=FONT_SMALL,
                    width=50,
                    height=22,
                    fg_color=("#e6ebf2", "#2d3442"),
                    text_color=("#1f2328", "#c9d1d9"),
                    command=lambda p=f_entry.path: self._open_file_in_explorer(p),
                )
                btn_open.pack(side="right", padx=(0, 8))

    def _open_file_in_explorer(self, file_path: str) -> None:
        """Select file in Windows Explorer."""
        if os.path.exists(file_path):
            subprocess.run(["explorer", f"/select,{os.path.normpath(file_path)}"])

    def _confirm_delete_selected(self) -> None:
        if self._is_deleting or self.finder.is_scanning:
            return

        selected_paths: List[str] = []
        selected_bytes = 0
        for g in self.duplicate_groups:
            for f in g.files:
                if f.selected:
                    selected_paths.append(f.path)
                    selected_bytes += f.size_bytes

        if not selected_paths:
            msgbox.showinfo("No Files Selected", "Please select at least one duplicate file to recycle.")
            return

        confirmed = msgbox.askyesno(
            title="Confirm Moving Files to Recycle Bin",
            message=(
                f"Are you sure you want to move {len(selected_paths)} duplicate file(s) "
                f"({format_bytes(selected_bytes)}) to the Windows Recycle Bin?\n\n"
                f"Files are placed into the Recycle Bin and can be restored if needed.\n"
                f"At least one verified copy of each duplicate group is strictly preserved.\n"
                f"SystemCare never deletes files permanently without user override."
            ),
            icon="warning",
        )
        if not confirmed:
            return

        self._is_deleting = True
        self.btn_delete_selected.configure(state="disabled", text="Recycling Files...")
        self.btn_scan.configure(state="disabled")

        def delete_worker():
            cleanup_res: DuplicateCleanupResult = self.finder.execute_safe_cleanup(
                selected_paths, groups=self.duplicate_groups
            )
            try:
                if self.winfo_exists():
                    self.after(0, lambda: self._on_delete_completed(cleanup_res))
            except Exception:
                pass

        threading.Thread(target=delete_worker, daemon=True).start()

    def _on_delete_completed(self, res: DuplicateCleanupResult) -> None:
        self._is_deleting = False
        self.btn_delete_selected.configure(state="normal")
        self.btn_scan.configure(state="normal")

        if res.errors:
            msgbox.showwarning(
                "Cleanup Finished with Notices",
                f"Moved {res.files_recycled_count} file(s) to Recycle Bin ({format_bytes(res.bytes_moved_to_recycle_bin)}).\n"
                f"Physical disk space freed: {format_bytes(res.actual_disk_freed_bytes)}.\n\n"
                f"Notices:\n" + "\n".join(res.errors[:5]),
            )
        else:
            msgbox.showinfo(
                "Duplicate Cleanup Complete",
                f"Successfully moved {res.files_recycled_count} duplicate file(s) to the Windows Recycle Bin!\n"
                f"Total file size sent to Recycle Bin: {format_bytes(res.bytes_moved_to_recycle_bin)}.\n"
                f"Actual physical disk space freed: {format_bytes(res.actual_disk_freed_bytes)}.\n"
                f"Preserved original copies: {res.preserved_copies_count}.",
            )

        # Re-scan to refresh group status
        self._start_scan_thread()
