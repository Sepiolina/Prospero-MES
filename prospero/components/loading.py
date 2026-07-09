"""prospero.components.loading — PLoadingOverlay"""

from __future__ import annotations

from typing import ClassVar, Dict

from nicegui import ui

from prospero.themes import ThemeColors


class PLoadingOverlay:
    """Full-screen modal/spinner overlay used to block interaction during
    async operations.

    ``PLoadingOverlay.show()``
    ``PLoadingOverlay.hide()``

    NiceGUI pages are per-client, so a single module-level overlay would
    leak across operators sharing a server. Instead we keep one overlay
    per connected client, keyed by `Client.id`, and lazily build it the
    first time a given client calls `.show()`.
    """

    _overlays: ClassVar[Dict[str, ui.element]] = {}

    @classmethod
    def _ensure_overlay(cls) -> ui.element:
        client_id = ui.context.client.id
        overlay = cls._overlays.get(client_id)
        if overlay is None:
            overlay = cls._build()
            cls._overlays[client_id] = overlay
            ui.context.client.on_disconnect(lambda: cls._overlays.pop(client_id, None))
        return overlay

    @classmethod
    def _build(cls) -> ui.element:
        overlay = ui.element("div").classes(
            "fixed inset-0 flex flex-col items-center justify-center gap-4"
        )
        overlay.style(
            "z-index: 9999; background-color: rgba(26, 29, 35, 0.85); "
            "backdrop-filter: blur(2px);"
        )
        overlay.set_visibility(False)
        with overlay:
            ui.spinner(size="3em").style(f"color: {ThemeColors.ACCENT};")
            ui.label("Please wait...").style(
                f"color: {ThemeColors.DARK_TEXT}; font-size: 1rem;"
            )
        return overlay

    @classmethod
    def show(cls) -> None:
        cls._ensure_overlay().set_visibility(True)

    @classmethod
    def hide(cls) -> None:
        cls._ensure_overlay().set_visibility(False)
