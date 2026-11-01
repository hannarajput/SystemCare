"""
Storage Analyzer and Safe Space Cleaner.
Discovers disk space hogs, identifies cleanable temporary/cache files,
and guarantees Windows OS and user personal folders are protected.
"""

import os
import shutil
import threading
from dataclasses import dataclass, field
from typing import Callable, Dict, List, Optional, Set, Tuple

from ..utils.logger import logger
from ..utils.safety import (
    canonicalize_path,
    is_allowlisted_cleanup_path,
    is_protected_cleanup_path,
    send_to_recycle_bin,
)

# File extension categories
EXTENSION_CATEGORIES = {
    "Archives": {".zip", ".rar", ".7z", ".tar", ".gz", ".bz2", ".xz", ".iso", ".img", ".vmdk"},
    "Videos": {".mp4", ".mkv", ".avi", ".mov", ".wmv", ".flv", ".webm", ".m4v"},
    "Installers": {".exe", ".msi", ".bat", ".cmd", ".ps1"},
    "Audio": {".mp3", ".wav", ".flac", ".m4a", ".aac", ".ogg", ".wma"},
    "Documents": {".pdf", ".docx", ".xlsx", ".pptx", ".doc", ".xls", ".ppt", ".txt", ".csv"},
    "Virtual Disks": {".vhd", ".vhdx", ".vdi", ".qcow2"},
}


@dataclass
class LargeFileItem:
    path: str
    filename: str
    size_bytes: int
    category: str
    modified_time: float


@dataclass
class CleanableGroup:
    id: str
    name: str
    description: str
    safety_rating: str  # "Very Safe", "Safe", "Caution"
    items_count: int = 0
    total_bytes: int = 0
    file_paths: List[str] = field(default_factory=list)


@dataclass
class StorageAnalysisResult:
    target_path: str
    scanned_files_count: int
    total_size_scanned_bytes: int
    large_files: List[LargeFileItem]
    cleanable_groups: List[CleanableGroup]


@dataclass
class StorageCleanupResult:
    files_recycled_count: int
    bytes_moved_to_recycle_bin: int
    actual_disk_freed_bytes: int
    skipped_count: int
    skipped_reasons: List[str] = field(default_factory=list)

    def __iter__(self):
        return iter((self.files_recycled_count, self.bytes_moved_to_recycle_bin, self.skipped_count))


class StorageAnalyzer:
    """
    Analyzes directories for large files and cleanable temporary items.
    Enforces strict safety boundaries and native Recycle Bin preservation.
    """

    def __init__(self) -> None:
        self._cancel_event = threading.Event()
        self._is_analyzing = False

    @property
    def is_analyzing(self) -> bool:
        return self._is_analyzing

    def cancel_analysis(self) -> None:
        self._cancel_event.set()

    def analyze_target(
        self,
        target_path: str,
        min_large_file_mb: float = 50.0,
        max_large_files: int = 50,
        progress_callback: Optional[Callable[[int, str], None]] = None,
        scan_system_caches: bool = True,
    ) -> StorageAnalysisResult:
        """
        Scan target directory for large files and evaluate system cleanable caches.
        """
        self._cancel_event.clear()
        self._is_analyzing = True
        logger.info(f"Storage analysis starting on: {target_path}")

        large_files: List[LargeFileItem] = []
        min_bytes = int(min_large_file_mb * 1024 * 1024)
        total_scanned = 0
        total_bytes = 0

        try:
            for root, dirs, files in os.walk(target_path):
                if self._cancel_event.is_set():
                    logger.info("Storage scan canceled by user.")
                    break

                # Exclude protected/system volume roots
                dirs[:] = [
                    d for d in dirs
                    if not d.startswith("$")
                    and d.lower() not in {"system volume information", "$recycle.bin", ".git"}
                ]

                for fname in files:
                    if self._cancel_event.is_set():
                        break

                    total_scanned += 1
                    fpath = os.path.join(root, fname)

                    if total_scanned % 150 == 0 and progress_callback:
                        progress_callback(total_scanned, fpath)

                    try:
                        stat = os.stat(fpath, follow_symlinks=False)
                        fsize = stat.st_size
                        total_bytes += fsize

                        if fsize >= min_bytes:
                            cat = self._categorize_extension(fname)
                            large_files.append(
                                LargeFileItem(
                                    path=fpath,
                                    filename=fname,
                                    size_bytes=fsize,
                                    category=cat,
                                    modified_time=stat.st_mtime,
                                )
                            )
                    except (PermissionError, OSError):
                        continue

            # Sort largest files first and truncate to top N
            large_files.sort(key=lambda x: x.size_bytes, reverse=True)
            large_files = large_files[:max_large_files]

            # Discover cleanable caches if requested
            cleanable = self.discover_cleanable_caches() if scan_system_caches else []

            return StorageAnalysisResult(
                target_path=target_path,
                scanned_files_count=total_scanned,
                total_size_scanned_bytes=total_bytes,
                large_files=large_files,
                cleanable_groups=cleanable,
            )

        finally:
            self._is_analyzing = False

    def discover_cleanable_caches(self) -> List[CleanableGroup]:
        """
        Discover safe-to-clean temporary caches (User Temp, Crash Dumps, Browser Caches).
        Strictly excludes system folders or user document libraries.
        """
        groups: List[CleanableGroup] = []

        # 1. User Temporary Files (%TEMP%)
        user_temp = os.environ.get("TEMP") or os.environ.get("TMP")
        if user_temp and os.path.exists(user_temp):
            grp = self._scan_cleanable_directory(
                group_id="user_temp",
                name="User Temporary Files",
                description="Temporary workspace files created by running programs (%TEMP%). Safe to remove.",
                safety="Very Safe",
                directory=user_temp,
            )
            if grp.items_count > 0:
                groups.append(grp)

        # 2. Windows Crash Dumps (%LOCALAPPDATA%\CrashDumps)
        local_app_data = os.environ.get("LOCALAPPDATA")
        if local_app_data:
            crash_dir = os.path.join(local_app_data, "CrashDumps")
            if os.path.exists(crash_dir):
                grp = self._scan_cleanable_directory(
                    group_id="crash_dumps",
                    name="Application Crash Dumps",
                    description="Diagnostic error dumps generated after previous application crashes.",
                    safety="Very Safe",
                    directory=crash_dir,
                )
                if grp.items_count > 0:
                    groups.append(grp)

        # 3. Microsoft Edge Browser Cache
        if local_app_data:
            edge_cache = os.path.join(
                local_app_data, "Microsoft", "Edge", "User Data", "Default", "Cache", "Cache_Data"
            )
            if os.path.exists(edge_cache):
                grp = self._scan_cleanable_directory(
                    group_id="edge_cache",
                    name="Microsoft Edge Web Cache",
                    description="Web page cached images, scripts, and media from Edge.",
                    safety="Safe",
                    directory=edge_cache,
                )
                if grp.items_count > 0:
                    groups.append(grp)

        # 4. Google Chrome Browser Cache
        if local_app_data:
            chrome_cache = os.path.join(
                local_app_data, "Google", "Chrome", "User Data", "Default", "Cache", "Cache_Data"
            )
            if os.path.exists(chrome_cache):
                grp = self._scan_cleanable_directory(
                    group_id="chrome_cache",
                    name="Google Chrome Web Cache",
                    description="Web page cached images, scripts, and temporary media from Chrome.",
                    safety="Safe",
                    directory=chrome_cache,
                )
                if grp.items_count > 0:
                    groups.append(grp)

        return groups

    def _scan_cleanable_directory(
        self, group_id: str, name: str, description: str, safety: str, directory: str
    ) -> CleanableGroup:
        """Scan a designated temporary directory for cleanable files."""
        count = 0
        total_bytes = 0
        file_paths: List[str] = []

        try:
            for root, dirs, files in os.walk(directory):
                for fname in files:
                    fpath = os.path.join(root, fname)
                    if is_protected_cleanup_path(fpath):
                        continue
                    try:
                        sz = os.path.getsize(fpath)
                        count += 1
                        total_bytes += sz
                        file_paths.append(fpath)
                    except (PermissionError, OSError):
                        continue
        except Exception as err:
            logger.debug(f"Notice scanning directory '{directory}': {err}")

        return CleanableGroup(
            id=group_id,
            name=name,
            description=description,
            safety_rating=safety,
            items_count=count,
            total_bytes=total_bytes,
            file_paths=file_paths,
        )

    def clean_files(
        self, file_paths: List[str], use_recycle_bin: bool = True
    ) -> StorageCleanupResult:
        """
        Clean the specified list of files by transferring them to the Windows Recycle Bin.
        Permanent deletion is strictly disabled in normal cleanup workflows.
        Measures real physical free disk space before and after the operation.
        Returns a StorageCleanupResult distinguishing recycled bytes from actual disk space freed.
        """
        recycled_count = 0
        bytes_recycled = 0
        skipped: List[str] = []

        # Find drive root for measurement
        sample_path = file_paths[0] if file_paths else "C:\\"
        try:
            drive_root = os.path.splitdrive(os.path.abspath(sample_path))[0] + "\\"
            free_before = shutil.disk_usage(drive_root).free
        except Exception:
            free_before = 0
            drive_root = ""

        for p in file_paths:
            if not os.path.exists(p):
                skipped.append(f"Not found: {os.path.basename(p)}")
                continue

            # Strict revalidation immediately before action
            if is_protected_cleanup_path(p):
                skipped.append(f"Protected path skipped: {p}")
                continue

            try:
                sz = os.path.getsize(p)
                # Never fall back to os.remove. Only send to Recycle Bin.
                if send_to_recycle_bin(p):
                    recycled_count += 1
                    bytes_recycled += sz
                else:
                    skipped.append(f"Locked or in-use: {os.path.basename(p)}")
            except (PermissionError, OSError):
                skipped.append(f"Locked by active process: {os.path.basename(p)}")
            except Exception as err:
                skipped.append(f"Error processing {os.path.basename(p)}: {err}")

        # Measure disk free space after operation
        actual_disk_freed = 0
        if drive_root:
            try:
                free_after = shutil.disk_usage(drive_root).free
                actual_disk_freed = max(0, free_after - free_before)
            except Exception:
                actual_disk_freed = 0

        logger.info(
            f"Cleaned {recycled_count} files ({bytes_recycled} bytes moved to Recycle Bin, "
            f"{actual_disk_freed} bytes physical disk freed), {len(skipped)} skipped."
        )

        return StorageCleanupResult(
            files_recycled_count=recycled_count,
            bytes_moved_to_recycle_bin=bytes_recycled,
            actual_disk_freed_bytes=actual_disk_freed,
            skipped_count=len(skipped),
            skipped_reasons=skipped,
        )

    def _categorize_extension(self, filename: str) -> str:
        ext = os.path.splitext(filename)[1].lower()
        for cat_name, ext_set in EXTENSION_CATEGORIES.items():
            if ext in ext_set:
                return cat_name
        return "Other"
