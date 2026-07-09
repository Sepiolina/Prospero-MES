"""prospero.components.layout — Layout / ThemeToggle"""

from __future__ import annotations
from nicegui import ui
from prospero.ariel import ariel


class Layout(ui.row):
    def __init__(self) -> None:
        super().__init__()
        self.classes("w-full flex-1 items-stretch gap-4 flex-nowrap")


class ThemeToggle(ui.element):
    def __init__(self) -> None:
        super().__init__("div")
        self.classes(
            "fixed top-4 right-4 z-[9500] rounded-full "
            "min-w-[48px] min-h-[48px] flex items-center justify-center "
            "cursor-pointer bg-[var(--p-panel)] border border-[var(--p-panel-border)]"
        )
        dark_mode = ui.dark_mode()

        with self:
            icon = ui.icon("dark_mode" if dark_mode.value else "light_mode").style(
                "color: var(--p-accent); font-size: 1.5rem;"
            )

        def _toggle() -> None:
            dark_mode.toggle()
            new_value = dark_mode.value
            ariel.set("theme_settings", "prospero_dark_mode", new_value)
            icon.props(f"name={'dark_mode' if new_value else 'light_mode'}")

        self.on("click", _toggle)
