"""prospero.components.alert — PAlert"""

from __future__ import annotations

from typing import Literal

from nicegui import ui

from prospero.themes import ALERT_ICON_MAP, ALERT_TONE_MAP

AlertType = Literal["positive", "negative", "warning"]


class PAlert(ui.element):
    def __init__(self, message: str, type: AlertType = "positive") -> None:  # noqa: A002
        super().__init__("div")
        fg, bg_dark, bg_light = ALERT_TONE_MAP[type]
        icon = ALERT_ICON_MAP[type]

        self.classes("p-alert-anchor w-full rounded-md p-4 flex items-center gap-3")
        self.style(f"background-color: {bg_dark}; border-left-color: {fg};")
        self._props["data-ptype"] = type

        with self:
            ui.icon(icon).style(f"color: {fg}; font-size: 1.5rem;")
            ui.label(message).style(f"color: {fg};").classes("text-base font-medium")

        ui.add_css(
            f".body--light .p-alert-anchor[data-ptype='{type}'] {{"
            f"background-color: {bg_light} !important; }}"
        )
