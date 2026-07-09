"""prospero.components.input — PInput"""

from __future__ import annotations

import re
from typing import Callable, Optional

from nicegui import ui

from prospero.core.base import StateMixin, TouchTargetMixin
from prospero.core.focus_manager import FocusRouter, default_router


class PInput(StateMixin, TouchTargetMixin, ui.input):
    def __init__(
        self,
        label: str,
        *,
        required: bool = False,
        pattern: Optional[str] = None,
        placeholder: Optional[str] = None,
        password: bool = False,
        routing: Optional[int] = None,
        router: Optional[FocusRouter] = None,
        on_clear: Optional[Callable] = None,
    ) -> None:
        self._required = required
        self._pattern = re.compile(pattern) if pattern else None
        self._on_clear = on_clear

        super().__init__(
            label=label,
            placeholder=placeholder or "",
            password=password,
            validation=self._validate,
        )
        self._apply_touch_target()
        self._init_state(enabled=True)

        self.props("clearable outlined dense")

        self.classes()

        self.style(
            "--q-primary: var(--p-accent); --q-negative: var(--p-error, #f43f5e); "
        )
        self.on("clear", self._handle_clear)

        if routing is not None:
            (router or default_router).register(routing, self)

    def _validate(self, value: str) -> Optional[str]:
        if self._required and not value:
            return "This field is required."
        if self._pattern and value and not self._pattern.fullmatch(value):
            return "Invalid format."
        return None

    def _handle_clear(self) -> None:
        if self._on_clear is not None:
            self._on_clear()

    def is_valid(self) -> bool:
        return self._validate(self.value or "") is None
