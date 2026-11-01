"""
Safe Boost Engine.
Analyzes system opportunities for safe memory page trimming and disk temporary file cleanup.
Prioritizes system stability and transparency: never terminates processes blindly,
never promises synthetic performance gains, and executes only user-confirmed actions.
"""

import ctypes
import os
import shutil
import time
from ctypes import wintypes
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

import psutil

from ..utils.formatters import format_bytes, format_percent
from ..utils.logger import logger
from ..utils.safety import (
    is_allowlisted_cleanup_path,
    is_protected_cleanup_path,
    is_system_process,
    send_to_recycle_bin,
)
from .monitor import SystemMonitor, SystemSnapshot
from .storage_analyzer import StorageAnalyzer

PROCESS_QUERY_INFORMATION = 0x0400
PROCESS_SET_QUOTA = 0x0100

# Configure Windows API ctypes signatures
_kernel32 = ctypes.windll.kernel32
_psapi = ctypes.windll.psapi

_OpenProcess = _kernel32.OpenProcess
_OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
_OpenProcess.restype = wintypes.HANDLE

_CloseHandle = _kernel32.CloseHandle
_CloseHandle.argtypes = [wintypes.HANDLE]
_CloseHandle.restype = wintypes.BOOL

_EmptyWorkingSet = _psapi.EmptyWorkingSet
_EmptyWorkingSet.argtypes = [wintypes.HANDLE]
_EmptyWorkingSet.restype = wintypes.BOOL


@dataclass
class BoostAction:
    id: str
    title: str
    category: str  # "Memory", "Storage", "Apps"
    description: str
    safety_rating: str  # "Very Safe", "Safe"
    estimated_benefit: str
    selected: bool = True
    is_applicable: bool = True


@dataclass
class BoostResult:
    timestamp: float
    actions_executed: List[str]
    working_set_trimmed_bytes: int
    memory_freed_bytes: int  # Delta in system available physical memory
    bytes_recycled: int      # File bytes safely transferred to Recycle Bin
    disk_freed_bytes: int    # Actual physical free disk space increase measured
    ram_before_percent: float
    ram_after_percent: float
    cpu_before_percent: float
    cpu_after_percent: float
    details: List[str] = field(default_factory=list)


class SafeBoostEngine:
    """
    Coordinates safe, transparent PC optimization routines.
    """

    def __init__(self, monitor: Optional[SystemMonitor] = None) -> None:
        self.monitor = monitor or SystemMonitor()
        self.storage_analyzer = StorageAnalyzer()
        self._last_trim_time: float = 0.0
        self._trim_cooldown_seconds: float = 15.0

    def analyze_system(self) -> List[BoostAction]:
        """
        Analyze current system state and formulate genuine, safe optimization recommendations
        based strictly on observed metrics.
        """
        snap = self.monitor.get_latest_snapshot()
        actions: List[BoostAction] = []

        # 1. Memory Working Set Optimization
        ram_pct = snap.ram_percent
        actions.append(
            BoostAction(
                id="trim_memory",
                title="Trim Idle Process Working Sets",
                category="Memory",
                description=(
                    "Signals the Windows Memory Manager (EmptyWorkingSet) to transfer unreferenced "
                    "memory pages from idle user applications into the standby list. "
                    "Does not terminate processes or risk application stability."
                ),
                safety_rating="Safe",
                estimated_benefit=(
                    f"Reduces working set footprint of idle user apps (Current RAM: {format_percent(ram_pct)})"
                ),
                selected=(ram_pct > 65.0),
                is_applicable=True,
            )
        )

        # 2. Clean User Temporary Cache
        user_temp = os.environ.get("TEMP")
        temp_bytes = 0
        temp_file_count = 0
        if user_temp and os.path.exists(user_temp):
            try:
                for root, _, files in os.walk(user_temp):
                    for f in files[:100]:  # Non-blocking sample
                        try:
                            temp_bytes += os.path.getsize(os.path.join(root, f))
                            temp_file_count += 1
                        except OSError:
                            pass
            except Exception:
                pass

        actions.append(
            BoostAction(
                id="clean_user_temp",
                title="Clean User Temporary Files",
                category="Storage",
                description=(
                    "Safely moves discarded scratch files from your %TEMP% folder to the Recycle Bin. "
                    "Files currently in use or protected are automatically preserved."
                ),
                safety_rating="Very Safe",
                estimated_benefit=(
                    f"Sample scan detected {temp_file_count}+ temporary files (~{format_bytes(temp_bytes)})"
                    if temp_file_count > 0
                    else "Cleans temporary scratch files created by completed tasks"
                ),
                selected=True,
                is_applicable=True,
            )
        )

        # 3. Clean Application Crash Dumps
        local_app = os.environ.get("LOCALAPPDATA")
        crash_dir = os.path.join(local_app, "CrashDumps") if local_app else None
        crash_count = 0
        crash_bytes = 0
        if crash_dir and os.path.exists(crash_dir):
            try:
                for fname in os.listdir(crash_dir):
                    fpath = os.path.join(crash_dir, fname)
                    if os.path.isfile(fpath):
                        crash_count += 1
                        try:
                            crash_bytes += os.path.getsize(fpath)
                        except OSError:
                            pass
            except Exception:
                pass

        if crash_count > 0:
            actions.append(
                BoostAction(
                    id="clean_crash_dumps",
                    title="Clean Application Crash Dumps",
                    category="Storage",
                    description=(
                        "Moves stale .dmp diagnostic files from AppData\\Local\\CrashDumps to the Recycle Bin."
                    ),
                    safety_rating="Very Safe",
                    estimated_benefit=f"Removes {crash_count} crash dump file(s) ({format_bytes(crash_bytes)})",
                    selected=True,
                    is_applicable=True,
                )
            )

        # 4. Clean Edge/Chrome Browser Cache
        actions.append(
            BoostAction(
                id="clean_browser_cache",
                title="Flush Web Browser Disk Caches",
                category="Storage",
                description=(
                    "Moves cached web images, scripts, and temporary media from Edge and Chrome to the Recycle Bin. "
                    "Saved passwords, bookmarks, and login sessions are strictly preserved."
                ),
                safety_rating="Safe",
                estimated_benefit="Recovers cached web asset storage without modifying personal browser data",
                selected=False,  # Unchecked by default for explicit user opt-in
                is_applicable=True,
            )
        )

        return actions

    def execute_boost(self, selected_action_ids: List[str]) -> BoostResult:
        """
        Execute only user-approved boost actions and measure empirical before/after telemetry.
        Never permanently deletes files; only uses Windows Recycle Bin.
        """
        logger.info(f"Executing Safe Boost with actions: {selected_action_ids}")
        details: List[str] = []
        executed_names: List[str] = []

        # Baseline system state
        mem_before = psutil.virtual_memory()
        cpu_before = psutil.cpu_percent(interval=None)

        # Baseline disk free on primary system drive
        sys_drive = os.environ.get("SystemDrive", "C:") + "\\"
        try:
            disk_free_before = shutil.disk_usage(sys_drive).free
        except Exception:
            disk_free_before = 0

        working_set_trimmed_total = 0
        bytes_recycled_total = 0

        # Action 1: Memory Trim (with cooldown check)
        if "trim_memory" in selected_action_ids:
            now = time.time()
            if now - self._last_trim_time < self._trim_cooldown_seconds:
                executed_names.append("Trim Idle Process Working Sets (Cooldown Active)")
                details.append("Memory trim was skipped because it was executed recently (cooldown active).")
            else:
                trimmed = self._trim_working_sets()
                self._last_trim_time = now
                working_set_trimmed_total += trimmed
                executed_names.append("Trim Idle Process Working Sets")
                details.append(
                    f"Trimmed idle memory working sets: {format_bytes(trimmed)} moved to standby pages."
                )

        # Action 2: Clean User Temp
        if "clean_user_temp" in selected_action_ids:
            user_temp = os.environ.get("TEMP")
            if user_temp and os.path.exists(user_temp):
                cnt, b_recycled, _ = self._clean_folder_contents(user_temp)
                bytes_recycled_total += b_recycled
                executed_names.append("Clean User Temporary Files")
                details.append(
                    f"Recycled {cnt} temporary file(s) ({format_bytes(b_recycled)} sent to Recycle Bin)."
                )

        # Action 3: Clean Crash Dumps
        if "clean_crash_dumps" in selected_action_ids:
            local_app = os.environ.get("LOCALAPPDATA")
            if local_app:
                crash_dir = os.path.join(local_app, "CrashDumps")
                if os.path.exists(crash_dir):
                    cnt, b_recycled, _ = self._clean_folder_contents(crash_dir)
                    bytes_recycled_total += b_recycled
                    executed_names.append("Clean Application Crash Dumps")
                    details.append(
                        f"Recycled {cnt} crash dump file(s) ({format_bytes(b_recycled)} sent to Recycle Bin)."
                    )

        # Action 4: Clean Browser Cache
        if "clean_browser_cache" in selected_action_ids:
            local_app = os.environ.get("LOCALAPPDATA")
            b_cnt = 0
            b_recycled = 0
            if local_app:
                for b_name, rel_path in [
                    ("Edge", r"Microsoft\Edge\User Data\Default\Cache\Cache_Data"),
                    ("Chrome", r"Google\Chrome\User Data\Default\Cache\Cache_Data"),
                ]:
                    target = os.path.join(local_app, rel_path)
                    if os.path.exists(target):
                        c, b, _ = self._clean_folder_contents(target)
                        b_cnt += c
                        b_recycled += b
            bytes_recycled_total += b_recycled
            executed_names.append("Flush Web Browser Disk Caches")
            details.append(
                f"Recycled {b_cnt} web cache file(s) ({format_bytes(b_recycled)} sent to Recycle Bin)."
            )

        # Settle pause for telemetry
        time.sleep(0.3)

        # Post-operation system state
        mem_after = psutil.virtual_memory()
        cpu_after = psutil.cpu_percent(interval=None)

        try:
            disk_free_after = shutil.disk_usage(sys_drive).free
            actual_disk_freed = max(0, disk_free_after - disk_free_before)
        except Exception:
            actual_disk_freed = 0

        # Physical available RAM delta (positive if available RAM increased)
        avail_ram_delta = max(0, mem_after.available - mem_before.available)

        result = BoostResult(
            timestamp=time.time(),
            actions_executed=executed_names,
            working_set_trimmed_bytes=working_set_trimmed_total,
            memory_freed_bytes=avail_ram_delta,
            bytes_recycled=bytes_recycled_total,
            disk_freed_bytes=actual_disk_freed,
            ram_before_percent=mem_before.percent,
            ram_after_percent=mem_after.percent,
            cpu_before_percent=cpu_before,
            cpu_after_percent=cpu_after,
            details=details,
        )

        logger.info(
            f"Safe Boost complete. RAM: {result.ram_before_percent:.1f}% -> {result.ram_after_percent:.1f}%. "
            f"Working Set Trimmed: {format_bytes(result.working_set_trimmed_bytes)}, "
            f"Recycled: {format_bytes(result.bytes_recycled)}, Actual Disk Freed: {format_bytes(result.disk_freed_bytes)}."
        )
        return result

    def _trim_working_sets(self) -> int:
        """
        Safely trim unneeded memory working sets of user processes using EmptyWorkingSet.
        Strictly guards system processes, kernel PIDs, and protected processes.
        Properly opens and closes Windows process handles with try...finally.
        """
        total_rss_reduced = 0
        cur_pid = os.getpid()

        for proc in psutil.process_iter(["pid", "name"]):
            handle = None
            try:
                pid = proc.info["pid"]
                name = proc.info["name"] or ""

                # Strictly protect system processes and current app process
                if pid == cur_pid or is_system_process(pid, name):
                    continue

                mem_before = proc.memory_info().rss

                handle = _OpenProcess(
                    PROCESS_QUERY_INFORMATION | PROCESS_SET_QUOTA, False, pid
                )
                if handle and handle != wintypes.HANDLE(-1).value and handle != 0:
                    try:
                        ok = _EmptyWorkingSet(handle)
                        if ok:
                            try:
                                mem_after = proc.memory_info().rss
                                if mem_before > mem_after:
                                    total_rss_reduced += (mem_before - mem_after)
                            except (psutil.NoSuchProcess, psutil.AccessDenied):
                                pass
                    finally:
                        _CloseHandle(handle)
                        handle = None

            except (psutil.NoSuchProcess, psutil.AccessDenied, PermissionError):
                continue
            except Exception as err:
                logger.debug(f"Process memory trim notice for PID {getattr(proc, 'pid', 'unknown')}: {err}")
                continue
            finally:
                if handle and handle != wintypes.HANDLE(-1).value and handle != 0:
                    try:
                        _CloseHandle(handle)
                    except Exception:
                        pass

        return total_rss_reduced

    def _clean_folder_contents(self, folder_path: str) -> Tuple[int, int, List[str]]:
        """
        Safely clean files inside an allowlisted temporary directory by sending them to Recycle Bin.
        Never uses permanent deletion (os.remove).
        Skips currently locked, in-use, or protected files.
        """
        cleaned_count = 0
        bytes_recycled = 0
        skipped: List[str] = []

        if not os.path.exists(folder_path):
            return 0, 0, []

        try:
            for root, _, files in os.walk(folder_path):
                for fname in files:
                    fpath = os.path.join(root, fname)

                    # Strictly enforce safety boundaries & allowlist
                    if is_protected_cleanup_path(fpath) or not is_allowlisted_cleanup_path(fpath):
                        continue

                    try:
                        sz = os.path.getsize(fpath)
                        if send_to_recycle_bin(fpath):
                            cleaned_count += 1
                            bytes_recycled += sz
                        else:
                            skipped.append(fname)
                    except (PermissionError, OSError):
                        # Normal for active/locked temp files
                        skipped.append(fname)
                    except Exception as err:
                        skipped.append(f"{fname}: {err}")
        except Exception as err:
            logger.debug(f"Notice while scanning folder {folder_path}: {err}")

        return cleaned_count, bytes_recycled, skipped
