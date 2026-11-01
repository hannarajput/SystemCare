"""
Background Application and Process Manager.
Enumerates processes, computes CPU and RAM consumption, classifies system vs user apps,
and enforces strict safety protections against terminating OS services.
Protects against PID reuse through identity and creation time revalidation.
"""

import time
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

import psutil

from ..utils.logger import logger
from ..utils.safety import is_system_process


@dataclass
class ProcessInfo:
    pid: int
    name: str
    cpu_percent: float
    memory_mb: float
    memory_percent: float
    status: str
    username: str
    exe_path: str
    is_system: bool
    is_killable: bool
    create_time: float = 0.0


class ProcessManager:
    """
    Manages process enumeration, categorization, and safe termination.
    Features short-lived caching for high responsiveness across views.
    """

    def __init__(self) -> None:
        self._cached_procs: List[ProcessInfo] = []
        self._cache_timestamp: float = 0.0
        self._cache_ttl: float = 3.0  # seconds
        # Prime psutil CPU percent calculations
        self._prime_cpu()

    def _prime_cpu(self) -> None:
        """Prime cpu_percent for all processes without blocking."""
        try:
            for p in psutil.process_iter(["pid", "cpu_percent"]):
                pass
        except Exception:
            pass

    def list_processes(
        self,
        sort_by: str = "cpu_percent",
        reverse: bool = True,
        filter_text: str = "",
        include_system: bool = True,
        force_refresh: bool = False,
    ) -> List[ProcessInfo]:
        """
        List currently running processes with detailed memory and CPU info.
        Uses a short cache TTL (3s) to prevent redundant heavy process scans.
        """
        now = time.time()
        if force_refresh or (now - self._cache_timestamp > self._cache_ttl) or not self._cached_procs:
            results: List[ProcessInfo] = []
            for proc in psutil.process_iter(
                ["pid", "name", "cpu_percent", "memory_info", "memory_percent", "status", "create_time"]
            ):
                try:
                    info = proc.info
                    pid = info["pid"]
                    name = info["name"] or f"Process {pid}"
                    is_sys = is_system_process(pid, name)

                    mem_info = info.get("memory_info")
                    mem_bytes = mem_info.rss if mem_info else 0
                    mem_mb = mem_bytes / (1024 * 1024)

                    cpu_pct = float(info.get("cpu_percent") or 0.0)
                    mem_pct = float(info.get("memory_percent") or 0.0)
                    status = str(info.get("status") or "running")
                    user = "System" if is_sys else "User"
                    exe = ""
                    create_t = float(info.get("create_time") or 0.0)

                    results.append(
                        ProcessInfo(
                            pid=pid,
                            name=name,
                            cpu_percent=round(cpu_pct, 1),
                            memory_mb=round(mem_mb, 1),
                            memory_percent=round(mem_pct, 1),
                            status=status,
                            username=user,
                            exe_path=exe,
                            is_system=is_sys,
                            is_killable=not is_sys,
                            create_time=create_t,
                        )
                    )
                except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                    continue
                except Exception:
                    continue

            self._cached_procs = results
            self._cache_timestamp = now

        # Filter & Sort
        procs = list(self._cached_procs)
        if not include_system:
            procs = [p for p in procs if not p.is_system]

        filter_lower = filter_text.lower().strip()
        if filter_lower:
            procs = [
                p for p in procs
                if filter_lower in p.name.lower() or filter_lower in str(p.pid)
            ]

        def sort_key(item: ProcessInfo):
            val = getattr(item, sort_by, item.cpu_percent)
            if isinstance(val, str):
                return val.lower()
            return val or 0

        procs.sort(key=sort_key, reverse=reverse)
        return procs

    def get_top_cpu_processes(self, limit: int = 5) -> List[Dict]:
        """Get top processes by CPU utilization."""
        procs = self.list_processes(sort_by="cpu_percent", reverse=True, include_system=True)
        return [
            {"pid": p.pid, "name": p.name, "cpu_percent": p.cpu_percent, "is_system": p.is_system}
            for p in procs[:limit]
        ]

    def get_top_ram_processes(self, limit: int = 5) -> List[Dict]:
        """Get top processes by Memory utilization."""
        procs = self.list_processes(sort_by="memory_mb", reverse=True, include_system=True)
        return [
            {"pid": p.pid, "name": p.name, "memory_mb": p.memory_mb, "is_system": p.is_system}
            for p in procs[:limit]
        ]

    def terminate_process(
        self,
        pid: int,
        force: bool = False,
        expected_name: Optional[str] = None,
        expected_create_time: Optional[float] = None,
    ) -> Tuple[bool, str]:
        """
        Safely terminate a user process with PID reuse and identity revalidation.
        Strictly rejects system processes and OS services.
        """
        try:
            proc = psutil.Process(pid)
            cur_name = proc.name()
            cur_create_time = proc.create_time()
        except psutil.NoSuchProcess:
            return False, f"Process with PID {pid} is no longer running."
        except Exception as err:
            return False, f"Could not inspect process {pid}: {err}"

        # PID reuse verification: check process name
        if expected_name and cur_name.lower() != expected_name.lower():
            msg = (
                f"Security Protection: Process identity mismatch on PID {pid}. "
                f"Expected '{expected_name}', but found '{cur_name}'. The PID was reassigned by the OS. "
                "Termination aborted for safety."
            )
            logger.warning(msg)
            return False, msg

        # PID reuse verification: check creation timestamp
        if expected_create_time and abs(cur_create_time - expected_create_time) > 1.0:
            msg = (
                f"Security Protection: Process instance on PID {pid} has changed (creation timestamp mismatch). "
                "Termination aborted for safety."
            )
            logger.warning(msg)
            return False, msg

        # Strict safety check against protected system and OS components
        if is_system_process(pid, cur_name):
            msg = f"Security Protection: '{cur_name}' (PID: {pid}) is a critical Windows system component and cannot be terminated."
            logger.warning(msg)
            return False, msg

        try:
            if force:
                proc.kill()
                action_text = "force-killed"
            else:
                proc.terminate()
                action_text = "terminated"

            logger.info(f"User {action_text} application: {cur_name} (PID: {pid})")
            # Invalidate cache so UI refreshes accurately
            self._cached_procs = []
            return True, f"Successfully {action_text} {cur_name} (PID: {pid})."

        except psutil.AccessDenied:
            msg = f"Access Denied: Standard user permissions cannot close {cur_name} (PID: {pid})."
            logger.warning(msg)
            return False, msg
        except psutil.NoSuchProcess:
            return True, f"Process {cur_name} (PID: {pid}) has already exited."
        except Exception as err:
            msg = f"Failed to terminate {cur_name} (PID: {pid}): {err}"
            logger.error(msg)
            return False, msg
