"""
Logging infrastructure for SystemCare.
Supports rotating file logs, privacy path sanitization, and an in-memory queue
for real-time in-app inspection.
"""

import collections
import logging
import os
import sys
from logging.handlers import RotatingFileHandler
from typing import List

# Fixed-size in-memory queue for GUI display
MAX_LOG_QUEUE_SIZE = 500
_in_memory_logs: collections.deque = collections.deque(maxlen=MAX_LOG_QUEUE_SIZE)


def sanitize_log_message(msg: str) -> str:
    """
    Sanitize sensitive personal paths from log messages.
    Replaces user profile path with '%USERPROFILE%' to preserve privacy.
    """
    if not msg:
        return ""
    user_prof = os.environ.get("USERPROFILE", "")
    if user_prof and len(user_prof) > 3:
        msg = msg.replace(user_prof, "%USERPROFILE%")
        # Also check lower case/alternate separator variants
        msg = msg.replace(user_prof.replace("\\", "/"), "%USERPROFILE%")
    return msg


class PrivacySanitizingFormatter(logging.Formatter):
    """Logging formatter that redacts personal directory paths for privacy."""

    def format(self, record: logging.LogRecord) -> str:
        orig = super().format(record)
        return sanitize_log_message(orig)


class InMemoryLogHandler(logging.Handler):
    """Custom log handler storing recent records for the UI view."""

    def emit(self, record: logging.LogRecord) -> None:
        try:
            msg = self.format(record)
            _in_memory_logs.append(msg)
        except Exception:
            self.handleError(record)


def get_recent_logs() -> List[str]:
    """Retrieve list of recent formatted log strings."""
    return list(_in_memory_logs)


def clear_recent_logs() -> None:
    """Clear memory log buffer."""
    _in_memory_logs.clear()


def setup_logger(name: str = "SystemCare", level: int = logging.INFO) -> logging.Logger:
    """Configure root SystemCare logger with file and console outputs."""
    logger = logging.getLogger(name)
    logger.setLevel(level)

    # Avoid adding duplicate handlers on multiple calls
    if logger.handlers:
        return logger

    formatter = PrivacySanitizingFormatter(
        fmt="[%(asctime)s] [%(levelname)s] [%(name)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    # In-memory handler for UI
    mem_handler = InMemoryLogHandler()
    mem_handler.setFormatter(formatter)
    logger.addHandler(mem_handler)

    # File handler in user local appdata or current dir
    try:
        appdata = os.environ.get("LOCALAPPDATA", os.path.expanduser("~"))
        log_dir = os.path.join(appdata, "SystemCare", "logs")
        os.makedirs(log_dir, exist_ok=True)
        log_path = os.path.join(log_dir, "systemcare.log")
        file_handler = RotatingFileHandler(
            log_path, maxBytes=2 * 1024 * 1024, backupCount=3, encoding="utf-8"
        )
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    except Exception as err:
        logger.warning(f"Could not initialize rotating file logger: {err}")

    return logger


logger = setup_logger()
