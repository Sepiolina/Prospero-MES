"""
prospero.core.focus_manager
============================
Implements sequential focus routing for `PInput(routing=N)`.

On a shop-floor tablet, operators frequently use a barcode scanner or a
gloved finger with no real keyboard "Tab" affordance. Routing lets a
station author declare the intended fill order once, and Prospero takes
care of moving focus to the next field on Enter and, optionally,
auto-submitting when the last field in the sequence is completed.

Each `Layout` / station creates its own `FocusRouter` instance so that
routing indices are scoped per-screen rather than globally.
"""

from __future__ import annotations

from typing import Any, Callable, Dict, Optional


class FocusRouter:
    def __init__(self) -> None:
        self._fields: Dict[int, Any] = {}
        self._on_complete: Optional[Callable[[], None]] = None

    def register(self, index: int, field: Any) -> None:
        self._fields[index] = field
        min_index = min(self._fields.keys())
        for idx, f in self._fields.items():
            if idx == min_index:
                if hasattr(f, "is_enabled") and not f.is_enabled:
                    f.enable()
            else:
                if hasattr(f, "is_enabled") and f.is_enabled:
                    f.disable()

        field.on("keydown.enter", lambda _, i=index: self._advance(i))

    def on_complete(self, callback: Callable[[], None]) -> None:
        self._on_complete = callback

    def _advance(self, current_index: int) -> None:
        current_field = self._fields.get(current_index)

        if current_field is not None:
            if hasattr(current_field, "validate"):
                if not current_field.validate():
                    return
            elif hasattr(current_field, "is_valid"):
                if not current_field.is_valid():
                    return
        # -------------------------------------------

        higher_keys = [k for k in self._fields.keys() if k > current_index]
        if higher_keys:
            next_index = min(higher_keys)

            for idx, field in self._fields.items():
                if idx == next_index:
                    field.enable()
                    field.run_method("focus")
                else:
                    field.disable()
        elif self._on_complete is not None:
            self._on_complete()

    def focus_first(self) -> None:
        if not self._fields:
            return

        min_index = min(self._fields.keys())
        for idx, field in self._fields.items():
            if idx == min_index:
                field.enable()
                field.run_method("focus")
            else:
                field.disable()


default_router = FocusRouter()
