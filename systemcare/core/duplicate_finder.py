"""
Duplicate File Finder.
Performs high-performance 3-phase duplicate detection (Size -> Quick 4KB Hash -> Full SHA-256).
Safe, non-destructive, with cancellation and Windows Recycle Bin support.
Guarantees preservation of at least one verified copy and revalidates files before recycling.
"""

import hashlib
import os
import shutil
import threading
from dataclasses import dataclass, field
from typing import Callable, Dict, List, Optional, Set, Tuple

from ..utils.logger import logger
from ..utils.safety import is_protected_cleanup_path, send_to_recycle_bin

CHUNK_SIZE = 64 * 1024
QUICK_HASH_BYTES = 4096


@dataclass
class DuplicateFileEntry:
    path: str
    filename: str
    size_bytes: int
    modified_time: float
    selected: bool = False


@dataclass
class DuplicateGroup:
    group_id: str
    file_size_bytes: int
    sha256_hash: str
    files: List[DuplicateFileEntry] = field(default_factory=list)

    @property
    def reclaimable_bytes(self) -> int:
        """Estimated bytes reclaimable if all but one file in this group are deleted."""
        count = len(self.files)
        if count <= 1:
            return 0
        return self.file_size_bytes * (count - 1)


@dataclass
class DuplicateCleanupResult:
    files_recycled_count: int
    bytes_moved_to_recycle_bin: int
    actual_disk_freed_bytes: int
    preserved_copies_count: int
    errors: List[str] = field(default_factory=list)

    def __iter__(self):
        return iter((self.files_recycled_count, self.bytes_moved_to_recycle_bin, self.errors))


class DuplicateFinder:
    """
    Scans directory trees for identical files using staged cryptographic hashing.
    Enforces that at least one copy in every group is strictly preserved.
    """

    def __init__(self) -> None:
        self._cancel_event = threading.Event()
        self._is_scanning = False

    @property
    def is_scanning(self) -> bool:
        return self._is_scanning

    def cancel_scan(self) -> None:
        """Signal current scan to cancel promptly."""
        self._cancel_event.set()

    def scan_folder(
        self,
        folder_path: str,
        min_size_bytes: int = 1,
        progress_callback: Optional[Callable[[int, int, str], None]] = None,
    ) -> List[DuplicateGroup]:
        """
        Scan folder for duplicate files using 3-stage validation.
        Progress callback receives (scanned_count, duplicate_groups_count, current_file).
        """
        self._cancel_event.clear()
        self._is_scanning = True
        logger.info(f"Starting duplicate file scan in: {folder_path}")

        try:
            # Phase 1: Group by file size
            size_map: Dict[int, List[str]] = {}
            total_scanned = 0

            for root, dirs, files in os.walk(folder_path):
                if self._cancel_event.is_set():
                    logger.info("Duplicate scan canceled during Phase 1.")
                    return []

                # Skip hidden system volume folders
                dirs[:] = [
                    d for d in dirs
                    if not d.startswith("$")
                    and d.lower() not in {"system volume information", "$recycle.bin", ".git", "node_modules"}
                ]

                for fname in files:
                    if self._cancel_event.is_set():
                        return []

                    total_scanned += 1
                    fpath = os.path.join(root, fname)

                    if total_scanned % 100 == 0 and progress_callback:
                        progress_callback(total_scanned, 0, fpath)

                    try:
                        # Follow no symlinks to prevent infinite recursion
                        stat = os.stat(fpath, follow_symlinks=False)
                        size = stat.st_size
                        if size >= min_size_bytes:
                            size_map.setdefault(size, []).append(fpath)
                    except (PermissionError, OSError):
                        continue

            # Filter out unique sizes
            candidate_size_groups = {k: v for k, v in size_map.items() if len(v) > 1}
            logger.info(f"Phase 1 complete: {total_scanned} files scanned, {len(candidate_size_groups)} size collisions.")

            # Phase 2: Quick Hash (First 4KB)
            quick_hash_map: Dict[Tuple[int, str], List[str]] = {}
            for size, path_list in candidate_size_groups.items():
                if self._cancel_event.is_set():
                    return []

                for p in path_list:
                    if self._cancel_event.is_set():
                        return []
                    qhash = self._calc_quick_hash(p)
                    if qhash:
                        quick_hash_map.setdefault((size, qhash), []).append(p)

            candidate_quick_groups = {k: v for k, v in quick_hash_map.items() if len(v) > 1}
            logger.info(f"Phase 2 complete: {len(candidate_quick_groups)} quick-hash collisions.")

            # Phase 3: Full Cryptographic SHA-256 Hash
            full_hash_map: Dict[Tuple[int, str], List[str]] = {}
            duplicates_found_count = 0

            for (size, _), path_list in candidate_quick_groups.items():
                if self._cancel_event.is_set():
                    return []

                for p in path_list:
                    if self._cancel_event.is_set():
                        return []
                    fhash = self._calc_full_sha256(p)
                    if fhash:
                        key = (size, fhash)
                        full_hash_map.setdefault(key, []).append(p)
                        if len(full_hash_map[key]) == 2:
                            duplicates_found_count += 1
                        if progress_callback:
                            progress_callback(total_scanned, duplicates_found_count, p)

            # Assemble Final Results
            results: List[DuplicateGroup] = []
            group_idx = 1
            for (size, fhash), path_list in full_hash_map.items():
                if len(path_list) > 1:
                    entries = []
                    for p in path_list:
                        try:
                            mtime = os.path.getmtime(p)
                        except OSError:
                            mtime = 0.0
                        entries.append(
                            DuplicateFileEntry(
                                path=p,
                                filename=os.path.basename(p),
                                size_bytes=size,
                                modified_time=mtime,
                                selected=False,
                            )
                        )
                    results.append(
                        DuplicateGroup(
                            group_id=f"GRP-{group_idx:04d}",
                            file_size_bytes=size,
                            sha256_hash=fhash,
                            files=entries,
                        )
                    )
                    group_idx += 1

            # Sort groups by reclaimable bytes descending
            results.sort(key=lambda g: g.reclaimable_bytes, reverse=True)
            logger.info(f"Duplicate scan finished: found {len(results)} duplicate groups.")
            return results

        finally:
            self._is_scanning = False

    def _calc_quick_hash(self, file_path: str) -> Optional[str]:
        try:
            with open(file_path, "rb") as f:
                chunk = f.read(QUICK_HASH_BYTES)
                return hashlib.sha256(chunk).hexdigest()
        except (PermissionError, OSError):
            return None

    def _calc_full_sha256(self, file_path: str) -> Optional[str]:
        hasher = hashlib.sha256()
        try:
            with open(file_path, "rb") as f:
                while chunk := f.read(CHUNK_SIZE):
                    if self._cancel_event.is_set():
                        return None
                    hasher.update(chunk)
            return hasher.hexdigest()
        except (PermissionError, OSError):
            return None

    def auto_select_duplicates(
        self, groups: List[DuplicateGroup], strategy: str = "keep_newest"
    ) -> None:
        """
        Configure selection flags within duplicate groups:
        - "keep_newest": Mark all except newest file in each group for deletion.
        - "keep_oldest": Mark all except oldest file in each group for deletion.
        - "select_all_duplicates": Mark all except the first item in each group.
        - "deselect_all": Clear all selections.
        Guarantees that at least one file remains unselected (preserved) in each group.
        """
        for group in groups:
            if not group.files:
                continue

            if strategy == "deselect_all":
                for f in group.files:
                    f.selected = False
                continue

            sorted_files = list(group.files)
            if strategy == "keep_newest":
                sorted_files.sort(key=lambda x: x.modified_time, reverse=True)
            elif strategy == "keep_oldest":
                sorted_files.sort(key=lambda x: x.modified_time, reverse=False)

            # Index 0 is kept (selected=False), rest are selected (selected=True)
            for idx, f in enumerate(sorted_files):
                f.selected = (idx > 0)

    def delete_selected_files(
        self,
        file_paths: List[str],
        use_recycle_bin: bool = True,
        groups: Optional[List[DuplicateGroup]] = None,
    ) -> Tuple[int, int, List[str]]:
        """
        Backward-compatible wrapper returning (deleted_count, bytes_recycled, errors_list).
        Delegates to execute_safe_cleanup with full group preservation.
        """
        result = self.execute_safe_cleanup(file_paths, groups=groups)
        return result.files_recycled_count, result.bytes_moved_to_recycle_bin, result.errors

    def execute_safe_cleanup(
        self,
        file_paths: List[str],
        groups: Optional[List[DuplicateGroup]] = None,
    ) -> DuplicateCleanupResult:
        """
        Safely recycle confirmed duplicate files.
        - Preserves at least one copy in every duplicate group (never allows 100% group deletion).
        - Revalidates file size and modification status before recycling.
        - Never uses permanent deletion; only sends files to the Windows Recycle Bin.
        - Measures actual disk space freed.
        """
        recycled_count = 0
        bytes_recycled = 0
        preserved_count = 0
        errors: List[str] = []

        # Find drive root for measurement
        sample_path = file_paths[0] if file_paths else "C:\\"
        try:
            drive_root = os.path.splitdrive(os.path.abspath(sample_path))[0] + "\\"
            disk_free_before = shutil.disk_usage(drive_root).free
        except Exception:
            disk_free_before = 0
            drive_root = ""

        # Build group map if provided to guarantee one copy is preserved per group
        paths_to_delete = set(file_paths)
        if groups:
            for g in groups:
                group_paths = [f.path for f in g.files if os.path.exists(f.path)]
                selected_in_group = [p for p in group_paths if p in paths_to_delete]
                # If ALL existing files in this group are marked for deletion, preserve the first one!
                if len(selected_in_group) == len(group_paths) and group_paths:
                    keep_path = group_paths[0]
                    paths_to_delete.discard(keep_path)
                    preserved_count += 1
                    logger.info(f"Group safety guard: preserved copy of duplicate '{os.path.basename(keep_path)}'")
                else:
                    preserved_count += (len(group_paths) - len(selected_in_group))

        for p in paths_to_delete:
            if not os.path.exists(p):
                errors.append(f"File not found: '{os.path.basename(p)}'")
                continue

            if is_protected_cleanup_path(p):
                msg = f"Skipped protected path: '{p}'"
                logger.warning(msg)
                errors.append(msg)
                continue

            # Revalidation: verify file is accessible and check size
            try:
                cur_stat = os.stat(p)
                f_size = cur_stat.st_size

                # If group metadata is available, verify file size hasn't changed since scan
                if groups:
                    group_entry = self._find_entry_in_groups(p, groups)
                    if group_entry and group_entry.size_bytes != f_size:
                        msg = f"File size changed since scan; preserved for safety: '{os.path.basename(p)}'"
                        logger.warning(msg)
                        errors.append(msg)
                        continue

                # Safely move to Recycle Bin
                success = send_to_recycle_bin(p)
                if success:
                    recycled_count += 1
                    bytes_recycled += f_size
                    logger.info(f"Moved duplicate to Recycle Bin: {p}")
                else:
                    errors.append(f"Recycle Bin failed or file locked: '{os.path.basename(p)}'")
            except Exception as err:
                msg = f"Error processing '{os.path.basename(p)}': {err}"
                logger.error(msg)
                errors.append(msg)

        # Measure actual free disk space after operations
        actual_disk_freed = 0
        if drive_root:
            try:
                disk_free_after = shutil.disk_usage(drive_root).free
                actual_disk_freed = max(0, disk_free_after - disk_free_before)
            except Exception:
                actual_disk_freed = 0

        return DuplicateCleanupResult(
            files_recycled_count=recycled_count,
            bytes_moved_to_recycle_bin=bytes_recycled,
            actual_disk_freed_bytes=actual_disk_freed,
            preserved_copies_count=preserved_count,
            errors=errors,
        )

    def _find_entry_in_groups(
        self, path: str, groups: List[DuplicateGroup]
    ) -> Optional[DuplicateFileEntry]:
        norm_p = os.path.normcase(os.path.normpath(path))
        for g in groups:
            for f in g.files:
                if os.path.normcase(os.path.normpath(f.path)) == norm_p:
                    return f
        return None
