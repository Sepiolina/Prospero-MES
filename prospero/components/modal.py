"""prospero.components.modal — PModal"""

from __future__ import annotations

from typing import Optional

from nicegui import ui

from prospero.themes import Theme

Z_MODAL_BACKDROP = 9000
Z_MODAL_CONTENT = 9001
Z_LOADING_OVERLAY = 9999


class PModal(ui.dialog):
    """Popup with explicit z-index handling to sit on top of all layers.

    ``with PModal(title="Confirm Scrap") as modal:``
    ``    PText("Are you sure?")``
    ``    PButton("Close", on_click=modal.close)``
    ``modal.open()``
    """

    def __init__(self, title: Optional[str] = None) -> None:
        super().__init__()
        self.style(f"z-index: {Z_MODAL_BACKDROP} !important;")
        self.card = ui.card().classes(Theme.CARD + " gap-4 min-w-[320px]")
        self.card.style(f"z-index: {Z_MODAL_CONTENT} !important;")
        self._card_context = self.card

        # `ui.dialog` is itself a context manager whose children get
        # placed as siblings; nest everything inside `self.card` so
        # callers can `with PModal(...):` and get card styling easily.
        self.__enter_stack: list = []

        if title:
            with self.card:
                ui.label(title).classes(Theme.H3_TEXT)

    def __enter__(self):
        super().__enter__()
        self.card.__enter__()
        return self

    def __exit__(self, *exc):
        self.card.__exit__(*exc)
        return super().__exit__(*exc)
