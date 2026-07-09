"""prospero.components.scroll — PScrollArea"""

from __future__ import annotations

from nicegui import ui

from prospero.core.base import StateMixin


class PScrollArea(StateMixin, ui.scroll_area):
    def __init__(self, height: str = "100%", width: str = "100%") -> None:
        super().__init__()
        self._init_state(enabled=True)
        self.classes("rounded-lg border border-[var(--p-panel-border)]")
        self.style(
            f"height: {height}; width: {width}; background-color: var(--p-panel);"
        )
