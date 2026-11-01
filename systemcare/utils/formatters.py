"""
Formatting helper utilities for human-readable byte sizes, transfer rates,
percentages, and timestamps.
"""

from datetime import datetime
from typing import Optional, Union


def format_bytes(size_bytes: Union[int, float], precision: int = 1) -> str:
    """Format byte sizes into B, KB, MB, GB, TB with readable precision."""
    if size_bytes is None:
        return "0 B"
    try:
        size = float(size_bytes)
    except (ValueError, TypeError):
        return "0 B"

    if size < 0:
        return "-" + format_bytes(-size, precision)
    if size < 1024:
        return f"{int(size)} B"

    size /= 1024.0
    units = ["KB", "MB", "GB", "TB", "PB"]
    unit_index = 0
    while size >= 1024.0 and unit_index < len(units) - 1:
        size /= 1024.0
        unit_index += 1

    return f"{size:.{precision}f} {units[unit_index]}"


def format_speed(bytes_per_sec: Union[int, float], precision: int = 1) -> str:
    """Format network or disk transfer speed (e.g. 1.2 MB/s)."""
    return f"{format_bytes(bytes_per_sec, precision)}/s"


def format_percent(value: Union[int, float], precision: int = 1) -> str:
    """Format a percentage value."""
    if value is None:
        return "0.0%"
    try:
        val = float(value)
    except (ValueError, TypeError):
        return "0.0%"
    return f"{val:.{precision}f}%"


def format_timestamp(ts: Optional[Union[datetime, float]] = None) -> str:
    """Format a timestamp into standard YYYY-MM-DD HH:MM:SS format."""
    if ts is None:
        dt = datetime.now()
    elif isinstance(ts, (int, float)):
        try:
            dt = datetime.fromtimestamp(ts)
        except (ValueError, OSError):
            dt = datetime.now()
    elif isinstance(ts, datetime):
        dt = ts
    else:
        dt = datetime.now()
    return dt.strftime("%Y-%m-%d %H:%M:%S")


def format_duration(seconds: Union[int, float]) -> str:
    """Format duration in seconds into human-readable string."""
    if seconds is None or seconds < 0:
        return "0s"
    s = int(seconds)
    hours, remainder = divmod(s, 3600)
    minutes, sec = divmod(remainder, 60)
    parts = []
    if hours > 0:
        parts.append(f"{hours}h")
    if minutes > 0 or hours > 0:
        parts.append(f"{minutes}m")
    parts.append(f"{sec}s")
    return " ".join(parts)
