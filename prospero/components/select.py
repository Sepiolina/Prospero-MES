"""prospero.components.select — PSelect"""

from __future__ import annotations

from typing import Any, Callable, Dict, List, Optional, Union

from nicegui import ui

from prospero.core.base import StateMixin, TouchTargetMixin


class PSelect(StateMixin, TouchTargetMixin, ui.select):
    """Simple choice selector / dropdown.

    ``station_select = PSelect(["Line 1", "Line 2", "Line 3"], label="Line")``
    ``status_select = PSelect({"ok": "OK", "ng": "Not Good"}, label="Status")``
    """

    def __init__(
        self,
        options: Union[List[Any], Dict[Any, Any]],
        *,
        label: Optional[str] = None,
        value: Optional[Any] = None,
        on_change: Optional[Callable] = None,
        required: bool = False,
    ) -> None:
        super().__init__(options, label=label, value=value, on_change=on_change)
        self._apply_touch_target()
        self._init_state(enabled=True)
        self._required = required

        self.props("outlined dense clearable" if not required else "outlined dense")
        self.classes(
            "w-full rounded-md "
            "[&_.q-field__control]:min-h-[48px] "
            "[&_.q-field__native]:text-[var(--p-text)] "
            "[&_.q-field__label]:text-[var(--p-text-muted)]"
        )
        self.style("--q-primary: var(--p-accent);")
