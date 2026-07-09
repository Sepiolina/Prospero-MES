"""
prospero.themes
================
Single source of truth for colors, typography, spacing, and layout
tokens used across the entire Prospero component library.

No component and no station should ever reference a raw hex code or a
raw Tailwind color utility (bg-blue-500, text-red-600, etc). Everything
must flow through `Theme` / `ThemeColors` so that:

  1. The 60-30-10 rule is enforced centrally.
  2. The single "action color" stays truly single.
  3. Contrast ratios can be audited/changed in one place.
  4. The glare-defense light/dark toggle repaints everything for free.

Rule references (see project docs).
"""

from __future__ import annotations

from nicegui import ui
from pydantic import BaseModel
from prospero.ariel import ariel


class ThemeColors:
    # ---- 60%: Neutral backgrounds (Rule 2) ------------------------------
    DARK_BG = "#1a1d23"  # deep charcoal
    LIGHT_BG = "#eef0f3"  # light gray (glare defense, Rule 14)

    # ---- 30%: Structural panels / cards ---------------------------------
    DARK_PANEL = "#262a33"
    DARK_PANEL_BORDER = "#383d4a"
    LIGHT_PANEL = "#ffffff"
    LIGHT_PANEL_BORDER = "#d3d7de"

    # ---- Muted operational text (Rule 4) ---------------------------------
    DARK_TEXT = "#e8e9ec"
    DARK_TEXT_MUTED = "#9aa0ac"
    LIGHT_TEXT = "#1a1d23"
    LIGHT_TEXT_MUTED = "#5b6270"

    # ---- 10%: Single action color ---
    ACCENT = "#2f7dfa"  # vibrant blue
    ACCENT_HOVER = "#1c66e0"
    ACCENT_TEXT = "#ffffff"

    # ---- Semantic alert tones, each >= 4.5:1 contrast -----------
    POSITIVE = "#22c55e"
    POSITIVE_BG_DARK = "#12321f"
    POSITIVE_BG_LIGHT = "#e3f6ea"

    NEGATIVE = "#ef4444"
    NEGATIVE_BG_DARK = "#3a1414"
    NEGATIVE_BG_LIGHT = "#fbe6e6"

    WARNING = "#f5a623"
    WARNING_BG_DARK = "#3a2c0f"
    WARNING_BG_LIGHT = "#fbf0dd"

    # ---- Destructive workflows ---------------------------------
    DESTRUCTIVE = "#c0392b"
    DESTRUCTIVE_HOVER = "#a52f22"
    DESTRUCTIVE_TEXT = "#ffffff"

    # ---- Disabled state ---------------------------------------------------
    DISABLED_BG = "#3a3f4a"
    DISABLED_TEXT = "#6b7280"


# ---- Pydantic Schemas for Semantic Configurations -----------------------


class AlertConfig(BaseModel):
    icon: str
    foreground: str
    bg_dark: str
    bg_light: str


class AlertSettings(BaseModel):
    positive: AlertConfig
    negative: AlertConfig
    warning: AlertConfig


# Centralized configuration container
ALERT_SETTINGS = AlertSettings(
    positive=AlertConfig(
        icon="✔️",
        foreground=ThemeColors.POSITIVE,
        bg_dark=ThemeColors.POSITIVE_BG_DARK,
        bg_light=ThemeColors.POSITIVE_BG_LIGHT,
    ),
    negative=AlertConfig(
        icon="😱",
        foreground=ThemeColors.NEGATIVE,
        bg_dark=ThemeColors.NEGATIVE_BG_DARK,
        bg_light=ThemeColors.NEGATIVE_BG_LIGHT,
    ),
    warning=AlertConfig(
        icon="⚠️",
        foreground=ThemeColors.WARNING,
        bg_dark=ThemeColors.WARNING_BG_DARK,
        bg_light=ThemeColors.WARNING_BG_LIGHT,
    ),
)

# Semantic type -> (foreground, bg-dark, bg-light) lookup, used by PAlert
ALERT_TONE_MAP = {
    "positive": (
        ALERT_SETTINGS.positive.foreground,
        ALERT_SETTINGS.positive.bg_dark,
        ALERT_SETTINGS.positive.bg_light,
    ),
    "negative": (
        ALERT_SETTINGS.negative.foreground,
        ALERT_SETTINGS.negative.bg_dark,
        ALERT_SETTINGS.negative.bg_light,
    ),
    "warning": (
        ALERT_SETTINGS.warning.foreground,
        ALERT_SETTINGS.warning.bg_dark,
        ALERT_SETTINGS.warning.bg_light,
    ),
}

# Redundant coding: every alert type also gets a fixed icon so
# color-blind operators never rely on hue alone.
ALERT_ICON_MAP = {
    "positive": ALERT_SETTINGS.positive.icon,
    "negative": ALERT_SETTINGS.negative.icon,
    "warning": ALERT_SETTINGS.warning.icon,
}


class Theme:
    FONT_FAMILY = "Arial, Helvetica, sans-serif"

    # Page-level neutral background (60%)
    CONTAINER = (
        "w-full min-h-screen bg-[var(--p-bg)] text-[var(--p-text)] "
        "p-6 gap-4 font-[var(--p-font)]"
    )

    # Structural panel / card (30%)
    CARD = (
        "bg-[var(--p-panel)] border border-[var(--p-panel-border)] "
        "rounded-lg p-6 gap-3 shadow-none"
    )

    # Bezel clearance helper: apply to any layer holding
    # critical touch targets near the physical screen edge.
    BEZEL_SAFE = "m-6"  # 24px minimum clearance

    # Minimum touch target size
    TOUCH_TARGET = "min-w-[48px] min-h-[48px]"

    LABEL_TEXT = "text-[var(--p-text-muted)] text-sm tracking-wide uppercase"
    BODY_TEXT = "text-[var(--p-text)] text-base"
    H1_TEXT = "text-[var(--p-text)] text-3xl font-bold"
    H2_TEXT = "text-[var(--p-text)] text-2xl font-bold"
    H3_TEXT = "text-[var(--p-text)] text-xl font-semibold"

    DISABLED = "opacity-50 cursor-not-allowed pointer-events-none"


_CSS = f"""
:root, .body--dark {{
    --p-bg: {ThemeColors.DARK_BG};
    --p-panel: {ThemeColors.DARK_PANEL};
    --p-panel-border: {ThemeColors.DARK_PANEL_BORDER};
    --p-text: {ThemeColors.DARK_TEXT};
    --p-text-muted: {ThemeColors.DARK_TEXT_MUTED};
    --p-accent: {ThemeColors.ACCENT};
    --p-accent-hover: {ThemeColors.ACCENT_HOVER};
    --p-font: Arial, Helvetica, sans-serif;
}}

.body--light {{
    --p-bg: {ThemeColors.LIGHT_BG};
    --p-panel: {ThemeColors.LIGHT_PANEL};
    --p-panel-border: {ThemeColors.LIGHT_PANEL_BORDER};
    --p-text: {ThemeColors.LIGHT_TEXT};
    --p-text-muted: {ThemeColors.LIGHT_TEXT_MUTED};
    --p-accent: {ThemeColors.ACCENT};
    --p-accent-hover: {ThemeColors.ACCENT_HOVER};
}}

/* Hyper-minimalism (Rule 9): kill default Quasar shadows/dividers that
   read as decorative clutter on a factory-floor display. */
*:not(.q-icon) {{
    font-family: var(--p-font) !important;
}}
.q-card {{
    box-shadow: none !important;
}}
.q-separator {{
    display: none;
}}

/* No-flashing failure indicator (Rule 8): a static pulse-free ring
   instead of a blink animation. */
.p-alert-anchor {{
    border-left-width: 4px;
    border-left-style: solid;
}}

/* Focus ring: always visible, never removed, for keyboard/scanner nav. */
.p-focusable:focus-visible {{
    outline: 3px solid var(--p-accent);
    outline-offset: 2px;
}}
"""


def setup_theme(dark: bool = True) -> None:
    """Call once at app startup, before building any UI."""
    ui.add_css(_CSS)

    ui.colors(
        primary=ThemeColors.ACCENT,
        secondary=ThemeColors.DARK_PANEL,
        accent=ThemeColors.ACCENT,
        positive=ThemeColors.POSITIVE,
        negative=ThemeColors.NEGATIVE,
        warning=ThemeColors.WARNING,
        dark=ThemeColors.DARK_BG,
    )

    ariel.set("theme_settings", "prospero_dark_mode", dark)
    stored = ariel.get("theme_settings", "prospero_dark_mode")
    ui.dark_mode(False)
