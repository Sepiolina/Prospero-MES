"""prospero.components.text — PText"""

from __future__ import annotations

from typing import Literal

from nicegui import ui

from prospero.themes import Theme

Variant = Literal["normal", "label", "h1", "h2", "h3"]

_VARIANT_CLASSES = {
    "normal": Theme.BODY_TEXT,
    "label": Theme.LABEL_TEXT,
    "h1": Theme.H1_TEXT,
    "h2": Theme.H2_TEXT,
    "h3": Theme.H3_TEXT,
}

_VARIANT_TAG = {
    "normal": "span",
    "label": "span",
    "h1": "h1",
    "h2": "h2",
    "h3": "h3",
}


class PText(ui.element):
    """Static text / headers / labels.

    ``PText("MES TOPIC", variant="h1")``

    Variants: ``normal`` (default), ``label``, ``h1``, ``h2``, ``h3``.
    Colors always come from `Theme' never pass raw color classes to a PText instance.
    """

    def __init__(self, text: str, variant: Variant = "normal") -> None:
        tag = _VARIANT_TAG.get(variant, "span")
        super().__init__(tag)
        classes = _VARIANT_CLASSES.get(variant, Theme.BODY_TEXT)
        self.classes(classes)
        self._text: str | None = text

    @property
    def text(self) -> str | None:
        """The text content of the element."""
        return self._text

    @text.setter
    def text(self, text: str) -> None:
        self.set_text(text)

    def set_text(self, text: str) -> None:
        """Update the text content and trigger a UI refresh."""
        if self._text != text:
            self._text = text
            self.update()
