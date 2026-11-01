"""
UI Styling, Color Schemes, and Design System for SystemCare.
Inspired by clean, professional Windows system utilities (Windows 11 Settings, PowerToys).
Prioritizes usability, legibility, and restraint over decoration.
"""

from typing import Dict, Tuple

# Restrained Professional Color Palette (Light Theme, Dark Theme)
COLORS: Dict[str, Tuple[str, str]] = {
    # Backgrounds
    "bg_main": ("#f8f9fa", "#1a1c20"),
    "bg_sidebar": ("#f0f2f5", "#141619"),
    "bg_card": ("#ffffff", "#22252a"),
    "bg_card_secondary": ("#f3f4f6", "#2a2e35"),
    "bg_card_hover": ("#e5e7eb", "#323740"),
    "border": ("#e5e7eb", "#333740"),
    "border_subtle": ("#f0f2f5", "#2a2d34"),
    # Typography
    "text_primary": ("#111827", "#f3f4f6"),
    "text_secondary": ("#4b5563", "#9ca3af"),
    "text_muted": ("#9ca3af", "#6b7280"),
    # Accents & Brands (Muted Professional Blue)
    "primary": ("#0066cc", "#2563eb"),
    "primary_hover": ("#0052a3", "#1d4ed8"),
    "nav_active_bg": ("#e0edff", "#1e293b"),
    "nav_active_text": ("#0066cc", "#38bdf8"),
    # Restrained Status Indicators
    "success": ("#16a34a", "#22c55e"),
    "success_bg": ("#f0fdf4", "#14291c"),
    "warning": ("#d97706", "#f59e0b"),
    "warning_bg": ("#fffbeb", "#2a2314"),
    "danger": ("#dc2626", "#ef4444"),
    "danger_hover": ("#b91c1c", "#dc2626"),
    "info": ("#0066cc", "#38bdf8"),
    "system_tag": ("#6b7280", "#9ca3af"),
}

# Native Windows Typography Hierarchy
FONT_FAMILY = "Segoe UI"
FONT_TITLE = (FONT_FAMILY, 20, "bold")
FONT_SUBTITLE = (FONT_FAMILY, 15, "bold")
FONT_SECTION = (FONT_FAMILY, 14, "bold")
FONT_BODY = (FONT_FAMILY, 13)
FONT_BODY_BOLD = (FONT_FAMILY, 13, "bold")
FONT_SMALL = (FONT_FAMILY, 11)
FONT_MONO = ("Consolas", 12)
FONT_BIG_NUMBER = (FONT_FAMILY, 26, "bold")


def get_color(color_name: str, mode: str = "dark") -> str:
    """Retrieve color hex for current appearance mode (light / dark)."""
    pair = COLORS.get(color_name, ("#ffffff", "#1a1c20"))
    return pair[1] if mode.lower() == "dark" else pair[0]
