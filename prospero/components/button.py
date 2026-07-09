"""prospero.components.button — PButton"""

from __future__ import annotations

from typing import Callable, Literal, Optional

from nicegui import ui

from prospero.core.base import StateMixin, TouchTargetMixin
from prospero.themes import Theme, ThemeColors, ALERT_ICON_MAP

ButtonType = Literal["primary", "destructive"]


class PButton(StateMixin, TouchTargetMixin, ui.button):
    def __init__(
        self,
        text: str,
        type: ButtonType = "primary",  # noqa: A002
        on_click: Optional[Callable] = None,
        confirm_message: Optional[str] = None,
    ) -> None:
        self._button_type = type
        self._real_on_click = on_click

        super().__init__(text, on_click=self._handle_click)
        self._apply_touch_target()
        self._init_state(enabled=True)

        if type == "destructive":
            self.props("unelevated")
            self.style(
                f"background-color: {ThemeColors.DESTRUCTIVE} !important; "
                f"color: {ThemeColors.DESTRUCTIVE_TEXT} !important;"
            )
            self._confirm_message = confirm_message or (
                f'Confirm "{text}"? This action cannot be undone.'
            )
        else:
            self.props("unelevated")
            self.style(
                f"background-color: var(--p-accent) !important; "
                f"color: {ThemeColors.ACCENT_TEXT} !important;"
            )
            self._confirm_message = ""

        self.classes("rounded-md font-semibold px-6")

    def _handle_click(self) -> None:
        if not self.is_enabled:
            return
        if self._button_type == "destructive":
            self._open_confirm_dialog()
        elif self._real_on_click is not None:
            self._real_on_click()

    def _open_confirm_dialog(self) -> None:
        with ui.dialog() as dialog, ui.card().classes(Theme.CARD + " gap-4"):
            ui.icon(ALERT_ICON_MAP["warning"]).style(
                f"color: {ThemeColors.WARNING}; font-size: 2rem;"
            )

            ui.label(self._confirm_message).classes(Theme.BODY_TEXT)
            with ui.row().classes("w-full justify-end gap-2"):
                ui.button("Cancel", on_click=dialog.close).props("flat").classes(
                    Theme.TOUCH_TARGET
                )

                def _confirmed() -> None:
                    dialog.close()
                    if self._real_on_click is not None:
                        self._real_on_click()

                confirm_btn = ui.button("Confirm", on_click=_confirmed).classes(
                    Theme.TOUCH_TARGET + " rounded-md font-semibold"
                )
                confirm_btn.style(
                    f"background-color: {ThemeColors.DESTRUCTIVE} !important; "
                    f"color: {ThemeColors.DESTRUCTIVE_TEXT} !important;"
                )
        dialog.open()
