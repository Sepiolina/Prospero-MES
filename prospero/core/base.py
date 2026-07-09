"""
prospero.core.base
===================
Shared plumbing every Prospero component inherits from
"""

from __future__ import annotations

from typing import TYPE_CHECKING
from nicegui.element import Element

from prospero.themes import Theme


if TYPE_CHECKING:
    _MixinBase = Element
else:
    _MixinBase = object


class StateMixin(_MixinBase):
    __slots__ = ("_p_enabled", "other_attribute")

    _p_enabled: bool

    def _init_state(self, enabled: bool = True) -> None:
        self._p_enabled = enabled
        if not enabled:
            self._apply_disabled_style()

    @property
    def is_enabled(self) -> bool:
        return getattr(self, "_p_enabled", True)

    def enable(self) -> "StateMixin":
        self._p_enabled = True
        self.classes(remove=Theme.DISABLED)
        if hasattr(super(StateMixin, self), "enable"):
            super(StateMixin, self).enable()  # type: ignore[misc]
        self.update()
        return self

    def disable(self) -> "StateMixin":
        self._p_enabled = False
        self._apply_disabled_style()
        if hasattr(super(StateMixin, self), "disable"):
            super(StateMixin, self).disable()  # type: ignore[misc]
        self.update()
        return self

    def toggle_enabled(self) -> "StateMixin":
        return self.disable() if self.is_enabled else self.enable()

    def _apply_disabled_style(self) -> None:
        self.classes(add=Theme.DISABLED)


class TouchTargetMixin(_MixinBase):
    def _apply_touch_target(self) -> None:
        self.classes(add=Theme.TOUCH_TARGET + " p-focusable")


def bezel_safe(element: Element) -> Element:
    element.classes(add=Theme.BEZEL_SAFE)
    return element
