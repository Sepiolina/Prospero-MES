"""prospero.components.table — PDataTable"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from nicegui import ui

from prospero.core.base import StateMixin


class PDataTable(StateMixin, ui.table):
    def __init__(
        self,
        columns: List[Dict[str, Any]],
        rows: List[Dict[str, Any]],
        row_key: str = "id",
        title: Optional[str] = None,
    ) -> None:
        super().__init__(columns=columns, rows=rows, row_key=row_key, title=title)
        self._init_state(enabled=True)

        self.classes(
            "w-full rounded-lg "
            "[&_.q-table__top]:bg-[var(--p-panel)] "
            "[&_thead]:bg-[var(--p-panel)] "
            "[&_th]:text-[var(--p-text-muted)] "
            "[&_td]:text-[var(--p-text)] "
            "[&_tbody_tr]:border-[var(--p-panel-border)]"
        )
        self.style("background-color: var(--p-panel);")
        self.props("flat dense")

    def set_rows(self, rows: List[Dict[str, Any]]) -> None:
        self.rows = rows
        self.update()
