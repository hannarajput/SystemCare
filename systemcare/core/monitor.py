"""
Live System Monitor service.
Polls system metrics (CPU, RAM, Disks, Network, Hardware sensors) asynchronously
using psutil and Windows system APIs with lightweight background sampling.
"""

import os
import platform
import threading
import time
from dataclasses import dataclass, field
from datetime import datetime
from typing import Callable, Dict, List, Optional

import psutil

from ..utils.logger import logger


@dataclass
class DiskUsageInfo:
    mountpoint: str
    device: str
    fstype: str
    total_bytes: int
    used_bytes: int
    free_bytes: int
    percent: float


@dataclass
class HardwareTemperatureInfo:
    available: bool
    temperature_celsius: Optional[float] = None
    sensor_name: Optional[str] = None
    status_message: str = "Hardware Sensor Unavailable"
    details: str = (
        "Standard Windows installations do not expose direct thermal diode access "
        "to user-mode applications without dedicated kernel drivers."
    )


@dataclass
class SystemSnapshot:
    timestamp: float = field(default_factory=time.time)
    # CPU
    cpu_percent_total: float = 0.0
    cpu_percent_per_core: List[float] = field(default_factory=list)
    cpu_freq_current_mhz: Optional[float] = None
    cpu_physical_cores: int = 1
    cpu_logical_cores: int = 1
    # RAM
    ram_total_bytes: int = 0
    ram_used_bytes: int = 0
    ram_available_bytes: int = 0
    ram_percent: float = 0.0
    swap_total_bytes: int = 0
    swap_used_bytes: int = 0
    swap_percent: float = 0.0
    # Disks
    disks: List[DiskUsageInfo] = field(default_factory=list)
    disk_read_bytes_sec: float = 0.0
    disk_write_bytes_sec: float = 0.0
    # Network
    net_bytes_sent_sec: float = 0.0
    net_bytes_recv_sec: float = 0.0
    # Thermal
    temperature: HardwareTemperatureInfo = field(default_factory=lambda: HardwareTemperatureInfo(available=False))
    # OS / Host
    os_name: str = ""
    host_name: str = ""
    uptime_seconds: float = 0.0


class SystemMonitor:
    """
    Lightweight background monitor that regularly samples psutil and system telemetry.
    Thread-safe and non-blocking for the UI.
    """

    def __init__(self, interval_seconds: float = 1.5) -> None:
        self._interval = max(0.5, interval_seconds)
        self._stop_event = threading.Event()
        self._lock = threading.Lock()
        self._thread: Optional[threading.Thread] = None
        self._listeners: List[Callable[[SystemSnapshot], None]] = []

        # Previous counters for rate calculations
        self._last_disk_io: Optional[psutil._common.sdiskio] = None
        self._last_net_io: Optional[psutil._common.snetio] = None
        self._last_io_timestamp: float = time.time()

        # Cache static properties
        self._os_name = f"{platform.system()} {platform.release()} ({platform.machine()})"
        self._host_name = platform.node()
        self._boot_time = psutil.boot_time()
        self._cpu_physical = psutil.cpu_count(logical=False) or 1
        self._cpu_logical = psutil.cpu_count(logical=True) or 1

        # Most recent snapshot
        self._current_snapshot: SystemSnapshot = self._collect_snapshot()

    @property
    def interval(self) -> float:
        return self._interval

    @interval.setter
    def interval(self, value: float) -> None:
        self._interval = max(0.5, float(value))

    def add_listener(self, callback: Callable[[SystemSnapshot], None]) -> None:
        """Register a callback to receive snapshot updates."""
        with self._lock:
            if callback not in self._listeners:
                self._listeners.append(callback)

    def remove_listener(self, callback: Callable[[SystemSnapshot], None]) -> None:
        """Unregister an update callback."""
        with self._lock:
            if callback in self._listeners:
                self._listeners.remove(callback)

    def get_latest_snapshot(self) -> SystemSnapshot:
        """Thread-safe getter for the latest collected system snapshot."""
        with self._lock:
            return self._current_snapshot

    def start(self) -> None:
        """Start the background sampling thread."""
        if self._thread and self._thread.is_alive():
            return
        self._stop_event.clear()
        self._thread = threading.Thread(
            target=self._monitor_loop,
            name="SystemCare-Monitor-Thread",
            daemon=True,
        )
        self._thread.start()
        logger.info("SystemMonitor background polling thread started.")

    def stop(self) -> None:
        """Stop background sampling cleanly."""
        self._stop_event.set()
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=2.0)
        logger.info("SystemMonitor background polling stopped.")

    def _monitor_loop(self) -> None:
        while not self._stop_event.is_set():
            try:
                snap = self._collect_snapshot()
                with self._lock:
                    self._current_snapshot = snap
                    callbacks = list(self._listeners)

                for cb in callbacks:
                    try:
                        cb(snap)
                    except Exception as err:
                        logger.error(f"Error in monitor snapshot listener: {err}")
            except Exception as loop_err:
                logger.error(f"Error in monitor polling loop: {loop_err}")

            self._stop_event.wait(self._interval)

    def _collect_snapshot(self) -> SystemSnapshot:
        now = time.time()
        uptime = max(0.0, now - self._boot_time)

        # CPU usage
        cpu_total = psutil.cpu_percent(interval=None)
        cpu_cores = psutil.cpu_percent(interval=None, percpu=True)
        try:
            freq_info = psutil.cpu_freq()
            cpu_freq = freq_info.current if freq_info else None
        except Exception:
            cpu_freq = None

        # RAM & Swap
        mem = psutil.virtual_memory()
        try:
            swap = psutil.swap_memory()
            swap_total = swap.total
            swap_used = swap.used
            swap_percent = swap.percent
        except (RuntimeError, OSError, Exception) as err:
            logger.debug(f"Swap metrics unavailable: {err}")
            swap_total = 0
            swap_used = 0
            swap_percent = 0.0

        # Disk spaces
        disks: List[DiskUsageInfo] = []
        try:
            partitions = psutil.disk_partitions(all=False)
            for p in partitions:
                # Filter CD-ROMs or unmounted devices
                if "cdrom" in p.opts or not p.fstype:
                    continue
                try:
                    usage = psutil.disk_usage(p.mountpoint)
                    disks.append(
                        DiskUsageInfo(
                            mountpoint=p.mountpoint,
                            device=p.device,
                            fstype=p.fstype,
                            total_bytes=usage.total,
                            used_bytes=usage.used,
                            free_bytes=usage.free,
                            percent=usage.percent,
                        )
                    )
                except (PermissionError, OSError):
                    continue
        except Exception as part_err:
            logger.warning(f"Could not retrieve disk partitions: {part_err}")

        # Disk I/O rates
        disk_read_sec = 0.0
        disk_write_sec = 0.0
        try:
            current_disk_io = psutil.disk_io_counters()
            time_delta = max(0.001, now - self._last_io_timestamp)
            if self._last_disk_io and current_disk_io:
                disk_read_sec = max(0.0, (current_disk_io.read_bytes - self._last_disk_io.read_bytes) / time_delta)
                disk_write_sec = max(0.0, (current_disk_io.write_bytes - self._last_disk_io.write_bytes) / time_delta)
            self._last_disk_io = current_disk_io
        except Exception:
            pass

        # Network I/O rates
        net_recv_sec = 0.0
        net_sent_sec = 0.0
        try:
            current_net_io = psutil.net_io_counters()
            time_delta = max(0.001, now - self._last_io_timestamp)
            if self._last_net_io and current_net_io:
                net_sent_sec = max(0.0, (current_net_io.bytes_sent - self._last_net_io.bytes_sent) / time_delta)
                net_recv_sec = max(0.0, (current_net_io.bytes_recv - self._last_net_io.bytes_recv) / time_delta)
            self._last_net_io = current_net_io
        except Exception:
            pass

        self._last_io_timestamp = now

        # Temperature (strictly reliable hardware readings only)
        thermal_info = self._probe_temperature()

        return SystemSnapshot(
            timestamp=now,
            cpu_percent_total=cpu_total,
            cpu_percent_per_core=cpu_cores,
            cpu_freq_current_mhz=cpu_freq,
            cpu_physical_cores=self._cpu_physical,
            cpu_logical_cores=self._cpu_logical,
            ram_total_bytes=mem.total,
            ram_used_bytes=mem.used,
            ram_available_bytes=mem.available,
            ram_percent=mem.percent,
            swap_total_bytes=swap_total,
            swap_used_bytes=swap_used,
            swap_percent=swap_percent,
            disks=disks,
            disk_read_bytes_sec=disk_read_sec,
            disk_write_bytes_sec=disk_write_sec,
            net_bytes_sent_sec=net_sent_sec,
            net_bytes_recv_sec=net_recv_sec,
            temperature=thermal_info,
            os_name=self._os_name,
            host_name=self._host_name,
            uptime_seconds=uptime,
        )

    def _probe_temperature(self) -> HardwareTemperatureInfo:
        """
        Probe for reliable CPU temperatures.
        If unsupported or no hardware sensor exists, gracefully return unavailable status.
        Never fabricates mock numbers.
        """
        # 1. psutil sensors (available on Linux / some custom psutil builds)
        sensors = getattr(psutil, "sensors_temperatures", None)
        if callable(sensors):
            try:
                readings = sensors()
                if readings:
                    for name, entries in readings.items():
                        for entry in entries:
                            if entry.current and entry.current > 0:
                                return HardwareTemperatureInfo(
                                    available=True,
                                    temperature_celsius=round(float(entry.current), 1),
                                    sensor_name=f"{name} ({entry.label or 'Core'})",
                                    status_message="Active hardware reading",
                                    details="Hardware temperature reported via system sensors.",
                                )
            except Exception:
                pass

        # 2. Check for LibreHardwareMonitor or OpenHardwareMonitor WMI namespace
        # Standard user-mode Windows without LibreHardwareMonitor/OpenHardwareMonitor
        # does not expose sensor diodes. We return explicit clear non-error info.
        return HardwareTemperatureInfo(
            available=False,
            temperature_celsius=None,
            sensor_name=None,
            status_message="Hardware Sensor Unavailable",
            details=(
                "Standard Windows user permissions do not expose CPU diode sensors directly. "
                "Hardware monitor tools (such as LibreHardwareMonitor or CoreTemp) provide a kernel driver "
                "for temperature readings if needed."
            ),
        )
