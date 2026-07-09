"""prospero.components.input — PInput"""

from __future__ import annotations

import re
from typing import Callable, Literal, Optional

from nicegui import ui

from prospero.core.base import StateMixin, TouchTargetMixin
from prospero.core.focus_manager import FocusRouter, default_router


class PInput(StateMixin, TouchTargetMixin, ui.input):
    def __init__(
        self,
        label: str,
        *,
        required: bool = False,
        help: Optional[str] = None,
        pattern: Optional[str] = None,
        pattern_mode: Literal["validation", "mask", "strict"] = "validation",
        min_length: Optional[int] = None,
        max_length: Optional[int] = None,
        placeholder: Optional[str] = None,
        fill_mask: Optional[str] = None,
        password: bool = False,
        routing: Optional[int] = None,
        router: Optional[FocusRouter] = None,
        on_clear: Optional[Callable] = None,
    ) -> None:
        self._required = required
        self._help = help
        self._min_length = min_length
        self._max_length = max_length
        self._on_clear = on_clear
        self._is_resetting = False

        if pattern and pattern_mode == "mask":
            self._pattern = None
        else:
            self._pattern = re.compile(pattern) if pattern else None

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

        if self._help is not None:
            self._props["hint"] = self._help

        if self._min_length is not None:
            self._props["minlength"] = self._min_length

        if self._max_length is not None:
            self._props["maxlength"] = self._max_length

        if pattern and pattern_mode == "mask":
            self._props["mask"] = pattern

        if fill_mask:
            self.props["fill-mask"] = fill_mask

        self.on("clear", self._handle_clear)

        if routing is not None:
            (router or default_router).register(routing, self)

    def _validate(self, value: str) -> Optional[str]:
        if self._is_resetting:
            return None

        if self._required and not value:
            return "This field is required."

        if not value:
            return None

        if self._min_length is not None and len(value) < self._min_length:
            return f"Must be at least {self._min_length} characters."

        if self._max_length is not None and len(value) > self._max_length:
            return f"Cannot exceed {self._max_length} characters."

        if self._pattern and not self._pattern.fullmatch(value):
            return "Invalid format."

        return None

    def reset(self) -> None:
        self._is_resetting = True
        self.value = ""
        self._props["error"] = False
        self._props.pop("error-message", None)
        self.update()
        self.run_method("resetValidation")

        self._is_resetting = False

    def _handle_clear(self) -> None:
        if self._on_clear is not None:
            self._on_clear()

    def is_valid(self) -> bool:
        return self._validate(self.value or "") is None
