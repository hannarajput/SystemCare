"""
SystemCare — PC Health & Performance Optimizer
Main application entry point.
"""

import ctypes
import os
import sys

# Ensure application root directory is on PYTHONPATH
APP_ROOT = os.path.dirname(os.path.abspath(__file__))
if APP_ROOT not in sys.path:
    sys.path.insert(0, APP_ROOT)

from systemcare.ui.app import SystemCareApp
from systemcare.utils.logger import logger


def configure_windows_dpi():
    """Enable Windows Per-Monitor DPI awareness for crisp rendering."""
    try:
        # DPI_AWARENESS_CONTEXT_PER_MONITOR_AWARE_V2 (-4)
        ctypes.windll.user32.SetProcessDpiAwarenessContext(-4)
    except Exception:
        try:
            # Fallback to PROCESS_PER_MONITOR_DPI_AWARE (2)
            ctypes.windll.shcore.SetProcessDpiAwareness(2)
        except Exception:
            pass


def main():
    logger.info("Starting SystemCare — PC Health & Performance Optimizer...")
    configure_windows_dpi()

    try:
        app = SystemCareApp()
        app.mainloop()
    except KeyboardInterrupt:
        logger.info("Application terminated by keyboard interrupt.")
    except Exception as err:
        logger.critical(f"Unhandled exception in SystemCare: {err}", exc_info=True)
        raise


if __name__ == "__main__":
    main()
