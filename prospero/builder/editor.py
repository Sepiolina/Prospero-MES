"""Visual station authoring with shared rendering, live properties and draft recovery."""

from __future__ import annotations

import json
from pathlib import Path
from datetime import datetime, timezone

from nicegui import events, ui
from pydantic import ValidationError

from .renderer import render_screen
from .surface import StudioSurface
from .schema import (
    CONTAINERS,
    KINDS,
    MAX_DOCUMENT_BYTES,
    Appearance,
    EditorState,
    Node,
    Screen,
    ScreenDesign,
    find,
    json_literal,
    parent_of,
    starter_screen,
    walk,
)

ICONS = {
    "column": "view_agenda",
    "row": "view_column",
    "grid": "grid_view",
    "card": "crop_square",
    "text": "title",
    "input": "input",
    "select": "list",
    "button": "smart_button",
    "table": "table_chart",
}
STORAGE_KEY = "prospero.screen-builder.v1"
RECOVERY_KEY = "prospero.screen-studio.recovery.v1"
CHOICES = {
    "variant": ["normal", "label", "h1", "h2", "h3"],
    "type": ["primary", "destructive"],
    "align": ["stretch", "start", "center", "end"],
    "justify": ["start", "center", "end", "space-between", "space-around"],
    "width": ["default", "fill", "content", "fixed"],
    "font_weight": ["inherit", "400", "500", "600", "700"],
    "text_align": ["inherit", "left", "center", "right"],
    "foreground": [
        "inherit",
        "text",
        "muted",
        "accent",
        "positive",
        "negative",
        "warning",
    ],
    "surface": ["inherit", "base", "panel"],
    "mode": ["dark", "light"],
    "font": ["Arial", "System", "Georgia"],
}
LABELS = {
    "width_px": "Fixed width (px)",
    "width": "Width mode",
    "min_height": "Minimum height (px)",
    "font_size": "Font size (px)",
    "font_weight": "Font weight",
    "mobile_columns": "Phone columns",
    "text_align": "Text alignment",
    "foreground": "Text color",
    "surface": "Background",
    "radius": "Corner radius (px)",
}
NUMBERS = {
    "gap": (0, 64),
    "padding": (0, 96),
    "columns": (1, 6),
    "mobile_columns": (1, 6),
    "width_px": (24, 3840),
    "min_height": (0, 2160),
    "margin": (0, 96),
    "radius": (0, 48),
    "font_size": (8, 96),
}
OPTIONAL = {"mobile_columns", "radius", "font_size"}


class ScreenEditor:
    def __init__(self) -> None:
        self.state = EditorState()
        self.preview = False
        self.width = 1280
        self.zoom = "Fit"
        self.saved_raw = None
        self.saved_json = ""
        self.recovered_json = ""
        self.invalid = False
        self.ready = False
        self.storage_error = False
        self.surface = None
        self.collapsed = set()

    async def build(self) -> None:
        ui.add_css(Path(__file__).with_name("editor.css").read_text())
        with ui.column().classes("studio-shell"):
            with ui.row().classes("studio-header"):
                with ui.row().classes("studio-brand"):
                    ui.icon("dashboard_customize", size="26px")
                    with ui.column().classes("gap-0"):
                        ui.label("PROSPERO").classes("studio-eyebrow")
                        ui.label("Screen Studio").classes("studio-brand-title")
                self.title = (
                    ui.input(value=self.state.screen.name)
                    .props('dense borderless aria-label="Screen name"')
                    .classes("studio-title-input")
                )
                self.title.on_value_change(lambda e: self.rename(e.value))
                self.title.on("blur", self.state.end_edit_group)
                with ui.button(icon="more_horiz").props(
                    'flat round aria-label="Screen menu"'
                ):
                    with ui.menu():
                        ui.menu_item(
                            "New blank screen", lambda: self.confirm_replace(Screen())
                        )
                        ui.menu_item(
                            "Operator station template",
                            lambda: self.confirm_replace(starter_screen()),
                        )
                        ui.menu_item("Import JSON", self.import_dialog)
                ui.space()
                self.status = ui.label("Opening workspace…").classes(
                    "studio-save-status"
                )
                ui.button("Save draft", icon="save", on_click=self.save).props(
                    "flat no-caps"
                ).tooltip("Save in this browser · Ctrl/Cmd+S")
                ui.button("Export JSON", icon="download", on_click=self.export).props(
                    "unelevated no-caps"
                )
            with ui.row().classes("studio-toolbar"):
                self.undo = (
                    ui.button(icon="undo", on_click=lambda: self.history())
                    .props('flat round aria-label="Undo"')
                    .tooltip("Undo · Ctrl/Cmd+Z")
                )
                self.redo = (
                    ui.button(icon="redo", on_click=lambda: self.history(True))
                    .props('flat round aria-label="Redo"')
                    .tooltip("Redo · Ctrl/Cmd+Shift+Z")
                )
                ui.label("VIEWPORT").classes("studio-eyebrow ml-4")
                for label, width, icon in [
                    ("Desktop", 1280, "desktop_windows"),
                    ("Tablet", 768, "tablet_mac"),
                    ("Phone", 390, "smartphone"),
                ]:
                    ui.button(
                        icon=icon, on_click=lambda w=width: self.set_width(w)
                    ).props(f'flat round aria-label="{label} viewport"').tooltip(
                        f"{label} · {width}px"
                    )
                self.width_field = (
                    ui.number(
                        value=self.width,
                        min=320,
                        max=3840,
                        step=1,
                        on_change=lambda e: self.set_width(e.value),
                    )
                    .props('dense outlined suffix=px aria-label="Viewport width"')
                    .classes("studio-width")
                )
                ui.select(
                    ["Fit", "50", "75", "100", "125", "150"],
                    value=self.zoom,
                    on_change=lambda e: self.set_zoom(e.value),
                ).props('dense outlined aria-label="Canvas zoom"').classes(
                    "studio-zoom"
                )
                self.scale_label = ui.label("").classes("studio-muted text-xs")
                ui.space()
                self.mode_hint = ui.label("DESIGN").classes("studio-mode")
                self.preview_button = ui.button(
                    "Preview", icon="play_arrow", on_click=self.toggle_preview
                ).props("outline no-caps")
            with ui.element("div").classes("studio-workspace"):
                with ui.column().classes("studio-sidebar"):
                    ui.label("INSERT").classes("studio-eyebrow")
                    ui.input(
                        placeholder="Find a component…",
                        on_change=lambda e: self.filter_palette(e.value),
                    ).props(
                        'dense outlined clearable aria-label="Find components"'
                    ).classes("w-full")
                    self.palette_buttons = {}
                    with ui.element("div").classes("studio-palette"):
                        for kind in KINDS:
                            button = (
                                ui.button(
                                    kind.title(),
                                    icon=ICONS[kind],
                                    on_click=lambda k=kind: self.add(k),
                                )
                                .props("flat no-caps")
                                .classes("studio-palette-item")
                            )
                            self.drag(button, {"kind": kind})
                            self.palette_buttons[kind] = button
                    ui.label("Drag to the screen or click to insert.").classes(
                        "studio-muted text-xs"
                    )
                    with ui.row().classes("w-full items-center mt-5"):
                        ui.label("LAYERS").classes("studio-eyebrow")
                        ui.space()
                        self.count_label = ui.label("").classes("studio-muted text-xs")
                    with ui.column().classes("studio-tree-scroll"):
                        self.tree_panel()
                with ui.column().classes("studio-center"):
                    with ui.row().classes("studio-canvas-bar"):
                        self.breadcrumb = ui.label("Screen").classes(
                            "studio-muted text-xs"
                        )
                        ui.space()
                        self.canvas_hint = ui.label(
                            "Select to edit · drag to arrange"
                        ).classes("studio-muted text-xs")
                    with ui.element("div").classes("studio-stage"):
                        self.canvas()
                    with ui.row().classes("studio-footer"):
                        ui.icon("check_circle", size="14px")
                        ui.label("Shared renderer · actual screen dimensions")
                        ui.space()
                        ui.button("Shortcuts", on_click=self.shortcuts).props(
                            "flat dense no-caps"
                        )
                with ui.column().classes("studio-inspector"):
                    self.inspector()
        await ui.context.client.connected()
        try:
            saved = await ui.run_javascript(
                f"({{saved: localStorage.getItem({json_literal(STORAGE_KEY)}), recovery: sessionStorage.getItem({json_literal(RECOVERY_KEY)})}})"
            )
            self.saved_raw = saved["saved"]
            if saved["saved"]:
                screen = Screen.from_json(saved["saved"])
                self.state = EditorState(screen)
                self.saved_json = screen.to_json()
            if saved["recovery"]:
                recovery = json.loads(saved["recovery"])
                recovered = Screen.from_json(recovery["screen"])
                if recovered.to_json() != self.saved_json:
                    self.state = EditorState(recovered)
                    self.saved_raw = recovery.get("base")
                    ui.notify("Recovered this tab’s unfinished work", type="info")
                self.recovered_json = recovered.to_json()
        except (ValueError, TypeError, KeyError):
            ui.notify(
                "A stored draft could not be opened. Export your work before replacing it.",
                type="warning",
            )
        except (RuntimeError, TimeoutError):
            self.storage_error = True
        self.ready = True
        self.title.value = self.state.screen.name
        self.refresh()
        ui.timer(1, self.recover, immediate=False)

    @ui.refreshable
    def canvas(self) -> None:
        self.surface = StudioSurface(
            selected=self.state.selected_id,
            width=self.width,
            zoom=self.zoom,
            editing=not self.preview,
            dirty=self.invalid or self.state.screen.to_json() != self.saved_json,
        )
        self.surface.on("select", lambda e: self.select(e.args))
        self.surface.on("drop-node", lambda e: self.drop(e.args))
        self.surface.on("command", self.command)
        self.surface.on("scale", lambda e: self.scale_label.set_text(f"{e.args}%"))
        self.surface.on(
            "focus-properties",
            lambda: (
                self.name_field.run_method("focus")
                if hasattr(self, "name_field")
                else None
            ),
        )
        with self.surface:
            render_screen(self.state.screen)

    @ui.refreshable
    def tree_panel(self) -> None:
        self.tree(self.state.screen.root)

    def tree(self, node: Node, depth: int = 0) -> None:
        with (
            ui.row()
            .classes(
                "studio-tree-row"
                + (" is-selected" if node.id == self.state.selected_id else "")
            )
            .style(f"padding-left: {depth * 12}px")
        ):
            if node.children:
                ui.button(
                    icon="chevron_right"
                    if node.id in self.collapsed
                    else "expand_more",
                    on_click=lambda: self.collapse(node.id),
                ).props("flat dense round").classes("studio-collapse").tooltip(
                    "Collapse or expand children"
                )
            else:
                ui.element("div").classes("studio-tree-indent")
            button = (
                ui.button(
                    node.name or node.kind.title(),
                    icon=ICONS[node.kind],
                    on_click=lambda: self.select(node.id),
                )
                .props("flat no-caps align=left")
                .classes("studio-tree-item")
            )
            if node.id != self.state.screen.root.id:
                self.drag(button, {"id": node.id})
        if node.id not in self.collapsed:
            for child in node.children:
                self.tree(child, depth + 1)

    def collapse(self, node_id: str) -> None:
        self.collapsed.symmetric_difference_update({node_id})
        self.tree_panel.refresh()

    def filter_palette(self, query: str) -> None:
        for kind, button in self.palette_buttons.items():
            button.set_visibility((query or "").lower() in kind)

    @staticmethod
    def drag(element, payload: dict) -> None:
        element.props("draggable=true")
        element.on(
            "dragstart",
            js_handler="event => { event.stopPropagation(); event.dataTransfer.effectAllowed = 'copyMove'; "
            f"event.dataTransfer.setData('application/x-prospero', {json_literal(json_literal(payload))}); }}",
        )

    def drop(self, payload: dict) -> None:
        if self.preview or not isinstance(payload, dict) or not self.can_leave():
            return
        if isinstance(payload.get("id"), str):
            self.change(
                lambda: self.state.move(
                    payload["id"], payload["parent"], payload["index"]
                )
            )
        elif payload.get("kind") in KINDS:
            self.change(
                lambda: self.state.add(
                    payload["kind"], payload["parent"], payload["index"]
                )
            )

    @ui.refreshable
    def inspector(self) -> None:
        self.invalid = False
        node = self.state.selected
        self.field_values = {
            "name": node.name,
            "props": dict(node.props),
            "appearance": node.appearance.model_dump(),
            "design": self.state.screen.design.model_dump(),
        }
        with ui.row().classes("w-full items-center"):
            ui.icon(ICONS[node.kind]).classes("studio-muted")
            ui.label(node.kind.title()).classes("text-base font-semibold")
            ui.space()
            if node.id != self.state.screen.root.id:
                ui.button(
                    icon="content_copy",
                    on_click=lambda: self.change(self.state.duplicate),
                ).props('flat round dense aria-label="Duplicate component"').tooltip(
                    "Duplicate · Ctrl/Cmd+D"
                ).set_enabled(not self.preview)
                ui.button(
                    icon="delete_outline",
                    on_click=lambda: self.change(self.state.delete),
                ).props('flat round dense aria-label="Delete component"').tooltip(
                    "Delete · Del"
                ).set_enabled(not self.preview)
        if self.preview:
            ui.label(
                "Try the screen as an operator. Station actions remain disconnected."
            ).classes("studio-muted text-sm")
            ui.label("Return to Design to customize components.").classes(
                "studio-muted text-sm"
            )
            return
        self.error_label = (
            ui.label("").classes("studio-field-error").props("role=alert")
        )
        self.error_label.set_visibility(False)
        self.revert_button = ui.button(
            "Revert invalid edits", on_click=self.revert_fields
        ).props("flat dense no-caps")
        self.revert_button.set_visibility(False)
        self.name_field = self.field("name", "name", node.name, label="Component name")
        ui.label("CONTENT & LAYOUT").classes("studio-eyebrow mt-3")
        for key, value in node.props.items():
            if (
                key in {"columns", "mobile_columns"}
                and node.kind in CONTAINERS
                and node.kind != "grid"
            ):
                continue
            if key == "wrap" and node.kind != "row":
                continue
            self.field("props", key, value)
        if node.kind == "grid":
            ui.label(
                "Phone columns apply at screen widths of 600px or less. Leave blank to inherit."
            ).classes("studio-muted text-xs")
        if node.kind == "button":
            ui.label(
                "Action names connect to your station’s Python callbacks."
            ).classes("studio-muted text-xs")
        with ui.expansion("Size & spacing", icon="straighten", value=True).classes(
            "studio-section"
        ):
            for key in (
                "width",
                "width_px",
                "min_height",
                "margin",
                "padding",
                "radius",
            ):
                self.field("appearance", key, self.field_values["appearance"][key])
        with ui.expansion("Typography & color", icon="format_paint").classes(
            "studio-section"
        ):
            for key in (
                "font_size",
                "font_weight",
                "text_align",
                "foreground",
                "surface",
                "border",
            ):
                self.field("appearance", key, self.field_values["appearance"][key])
        if node.id != self.state.screen.root.id:
            with ui.expansion("Arrange", icon="swap_vert").classes("studio-section"):
                excluded = {n.id for n in walk(node)}
                parents = {
                    n.id: n.name or n.kind.title()
                    for n in walk(self.state.screen.root)
                    if n.kind in CONTAINERS and n.id not in excluded
                }
                parent = parent_of(self.state.screen.root, node.id)
                target = (
                    ui.select(parents, value=parent.id, label="Parent container")
                    .props("dense outlined")
                    .classes("w-full")
                )
                ui.button(
                    "Move into container",
                    on_click=lambda: self.change(
                        lambda: self.state.move(
                            node.id,
                            target.value,
                            len(find(self.state.screen.root, target.value).children),
                        )
                    ),
                ).props("flat no-caps")
                position = parent.children.index(node)
                with ui.row().classes("w-full"):
                    ui.button(
                        "Earlier",
                        icon="arrow_upward",
                        on_click=lambda: self.change(
                            lambda: self.state.move(node.id, parent.id, position - 1)
                        ),
                    ).props("flat no-caps").set_enabled(position > 0)
                    ui.button(
                        "Later",
                        icon="arrow_downward",
                        on_click=lambda: self.change(
                            lambda: self.state.move(node.id, parent.id, position + 2)
                        ),
                    ).props("flat no-caps").set_enabled(
                        position < len(parent.children) - 1
                    )
        with ui.expansion("Screen appearance", icon="palette").classes(
            "studio-section"
        ):
            for key, value in self.field_values["design"].items():
                self.field("design", key, value)
            ui.label("These settings are saved with the screen.").classes(
                "studio-muted text-xs"
            )
        with ui.expansion("Component reference", icon="code").classes("studio-section"):
            ui.label(node.id).classes("studio-muted text-xs break-all select-text")
        ui.label("Changes update the screen immediately.").classes(
            "studio-muted text-xs mt-3"
        )

    def field(self, section: str, key: str, value, label: str | None = None):
        label = label or LABELS.get(key, key.replace("_", " ").title())
        if isinstance(value, bool):
            control = ui.switch(label, value=value)
        elif key in NUMBERS and not isinstance(value, list):
            low, high = NUMBERS[key]
            control = ui.number(label, value=value, min=low, max=high, step=1).props(
                "dense outlined"
            )
            if value is None:
                control.props("placeholder=Auto clearable")
        elif key in CHOICES:
            control = ui.select(CHOICES[key], label=label, value=value).props(
                "dense outlined"
            )
        elif isinstance(value, list):
            control = ui.textarea(
                f"{label} (one per line)", value="\n".join(value)
            ).props("dense outlined autogrow")
        elif key == "text":
            control = ui.textarea(label, value=value).props("dense outlined autogrow")
        else:
            control = ui.input(label, value=value).props("dense outlined")
        control.classes("w-full studio-field")
        control.on_value_change(lambda e: self.field_changed(section, key, e.value))
        control.on("blur", self.state.end_edit_group)
        return control

    def field_changed(self, section: str, key: str, value) -> None:
        if self.preview:
            return
        if (
            section == "props"
            and key in {"options", "columns"}
            and isinstance(self.state.selected.props[key], list)
        ):
            value = [
                line.strip() for line in (value or "").splitlines() if line.strip()
            ]
        elif (
            key in NUMBERS
            and value is not None
            and isinstance(value, (int, float))
            and value == int(value)
        ):
            value = int(value)
        if section == "name":
            self.field_values["name"] = value
        else:
            self.field_values[section][key] = value
        try:
            candidate = self.state.screen.model_copy(deep=True)
            node = find(candidate.root, self.state.selected_id)
            node.name = self.field_values["name"]
            node.props = self.field_values["props"]
            node.appearance = Appearance.model_validate(self.field_values["appearance"])
            candidate.design = ScreenDesign.model_validate(self.field_values["design"])
            self.state.replace(candidate, group=f"{node.id}:{section}:{key}")
        except (ValueError, TypeError) as error:
            self.invalid = True
            self.error_label.set_text(self.error_message(error))
            self.error_label.set_visibility(True)
            self.revert_button.set_visibility(True)
            self.update_status()
            return
        self.invalid = False
        self.error_label.set_visibility(False)
        self.revert_button.set_visibility(False)
        self.canvas.refresh()
        if section == "name":
            self.tree_panel.refresh()
        self.update_status()

    @staticmethod
    def error_message(error: Exception) -> str:
        if isinstance(error, ValidationError):
            first = error.errors()[0]
            return f"{str(first['loc'][-1]).replace('_', ' ').title()}: {first['msg']}"
        return str(error)[:180]

    def revert_fields(self) -> None:
        self.inspector.refresh()
        self.update_status()

    def can_leave(self) -> bool:
        if self.invalid:
            ui.notify(
                "Fix the highlighted property or revert invalid edits first.",
                type="warning",
            )
            return False
        return True

    def change(self, operation) -> None:
        if self.preview or not self.can_leave():
            return
        try:
            operation()
        except (ValueError, TypeError, KeyError) as error:
            ui.notify(self.error_message(error), type="warning")
            return
        self.refresh()

    def refresh(self) -> None:
        self.canvas.refresh()
        self.tree_panel.refresh()
        self.inspector.refresh()
        self.update_status()

    def update_status(self) -> None:
        if not hasattr(self, "status"):
            return
        self.undo.set_enabled(bool(self.state.undo_stack) and not self.preview)
        self.redo.set_enabled(bool(self.state.redo_stack) and not self.preview)
        content = self.state.screen.to_json()
        dirty = content != self.saved_json
        text = (
            "Fix property values"
            if self.invalid
            else ("Draft saved" if not dirty else "Unsaved changes")
        )
        if self.storage_error:
            text = "Storage unavailable · export to keep work"
        self.status.set_text(text)
        self.count_label.set_text(str(len(list(walk(self.state.screen.root)))))
        selected = self.state.selected
        self.breadcrumb.set_text(
            f"{self.state.screen.name} / {selected.name or selected.kind.title()}"
        )
        if self.surface:
            self.surface.configure(
                dirty=dirty or self.invalid, selected=self.state.selected_id
            )

    def select(self, node_id: str) -> None:
        if not self.can_leave():
            return
        try:
            find(self.state.screen.root, node_id)
        except ValueError:
            return
        self.state.end_edit_group()
        self.state.selected_id = node_id
        self.tree_panel.refresh()
        self.inspector.refresh()
        self.update_status()

    def add(self, kind: str) -> None:
        node = self.state.selected
        parent = (
            node
            if node.kind in CONTAINERS
            else parent_of(self.state.screen.root, node.id)
        )
        self.change(lambda: self.state.add(kind, parent.id))

    def rename(self, value: str) -> None:
        if not self.ready or value == self.state.screen.name:
            return
        if not value.strip() or len(value) > 100:
            self.title.props('error error-message="Use 1–100 characters"')
            return
        self.title.props(remove="error error-message")
        self.state.edit(
            lambda screen: setattr(screen, "name", value), group="screen-name"
        )
        self.update_status()

    def set_width(self, width) -> None:
        if width is None or not 320 <= width <= 3840 or int(width) != width:
            return
        self.width = int(width)
        self.width_field.value = self.width
        if self.surface:
            self.surface.configure(width=self.width)

    def set_zoom(self, zoom: str) -> None:
        self.zoom = zoom
        self.surface.configure(zoom=zoom)

    def history(self, redo: bool = False) -> None:
        if not self.can_leave() or self.preview:
            return
        self.state.history(redo=redo)
        self.title.value = self.state.screen.name
        self.refresh()

    def toggle_preview(self) -> None:
        if not self.can_leave():
            return
        self.preview = not self.preview
        self.surface.configure(editing=not self.preview)
        self.mode_hint.set_text("PREVIEW" if self.preview else "DESIGN")
        self.preview_button.set_text("Back to design" if self.preview else "Preview")
        self.preview_button.props(f"icon={'edit' if self.preview else 'play_arrow'}")
        self.canvas_hint.set_text(
            "Interactive preview · actions disconnected"
            if self.preview
            else "Select to edit · drag to arrange"
        )
        for button in self.palette_buttons.values():
            button.set_enabled(not self.preview)
        self.inspector.refresh()
        self.update_status()

    async def command(self, event: events.GenericEventArguments) -> None:
        action = event.args
        if action == "save":
            await self.save()
        elif action in {"undo", "redo"}:
            self.history(action == "redo")
        elif not self.preview and self.state.selected_id != self.state.screen.root.id:
            if action == "duplicate":
                self.change(self.state.duplicate)
            elif action == "delete":
                self.change(self.state.delete)
            elif action == "parent":
                self.select(
                    parent_of(self.state.screen.root, self.state.selected_id).id
                )

    async def recover(self) -> None:
        content = self.state.screen.to_json()
        if not self.ready or content == self.recovered_json:
            return
        recovery = json.dumps(
            {
                "screen": content,
                "base": self.saved_raw,
                "time": datetime.now(timezone.utc).isoformat(),
            }
        )
        try:
            ok = await ui.run_javascript(
                f"(() => {{ try {{ sessionStorage.setItem({json_literal(RECOVERY_KEY)}, {json_literal(recovery)}); return true; }} catch {{ return false; }} }})()"
            )
            if ok:
                self.recovered_json = content
            else:
                self.storage_error = True
        except (RuntimeError, TimeoutError):
            self.storage_error = True
        self.update_status()

    async def save(self) -> None:
        if not self.ready or not self.can_leave():
            return
        content = self.state.screen.to_json()
        try:
            result = await ui.run_javascript(f"""(() => {{
                try {{
                    const current = localStorage.getItem({json_literal(STORAGE_KEY)});
                    if (current !== {json_literal(self.saved_raw)}) return 'conflict';
                    localStorage.setItem({json_literal(STORAGE_KEY)}, {json_literal(content)});
                    return 'saved';
                }} catch {{ return 'error'; }}
            }})()""")
        except (RuntimeError, TimeoutError):
            result = "error"
        if result == "conflict":
            with ui.dialog() as dialog, ui.card().classes("studio-dialog"):
                ui.label("A newer draft was saved in another tab").classes(
                    "text-lg font-semibold"
                )
                ui.label(
                    "Your changes are still here. Export a copy to keep both versions, or reload the saved draft."
                )
                with ui.row():
                    ui.button("Keep editing", on_click=dialog.close).props(
                        "flat no-caps"
                    )
                    ui.button(
                        "Export my copy",
                        on_click=lambda: (self.export(), dialog.close()),
                    ).props("no-caps")
            dialog.open()
            return
        if result != "saved":
            self.storage_error = True
            ui.notify("Could not save. Export JSON to keep your work.", type="negative")
        else:
            self.saved_raw = self.saved_json = content
            self.recovered_json = ""
            self.storage_error = False
            await self.recover()
        self.update_status()

    def export(self) -> None:
        if not self.can_leave():
            return
        ui.download.content(
            self.state.screen.to_json(),
            "prospero-screen.json",
            media_type="application/json",
        )

    def confirm_replace(self, screen: Screen) -> None:
        if not self.can_leave():
            return
        with ui.dialog() as dialog, ui.card().classes("studio-dialog"):
            ui.label(f"Open “{screen.name}”?").classes("text-lg font-semibold")
            ui.label(
                "This replaces the canvas. Your previous screen remains available through Undo."
            )
            with ui.row().classes("w-full justify-end"):
                ui.button("Cancel", on_click=dialog.close).props("flat no-caps")

                def replace():
                    self.preview = False
                    self.state.replace(screen)
                    self.title.value = screen.name
                    self.preview_button.set_text("Preview")
                    for button in self.palette_buttons.values():
                        button.enable()
                    self.refresh()
                    dialog.close()

                ui.button("Open screen", on_click=replace).props("no-caps")
        dialog.open()

    def import_dialog(self) -> None:
        if not self.can_leave():
            return
        with ui.dialog() as dialog, ui.card().classes("studio-dialog"):
            ui.label("Import a screen").classes("text-lg font-semibold")
            ui.label("Prospero JSON · up to 256 KB").classes("studio-muted")

            async def uploaded(event: events.UploadEventArguments):
                try:
                    screen = Screen.from_json(await event.file.read())
                except (ValueError, TypeError) as error:
                    ui.notify(self.error_message(error), type="negative")
                    return
                dialog.close()
                self.confirm_replace(screen)

            ui.upload(
                on_upload=uploaded,
                auto_upload=True,
                max_file_size=MAX_DOCUMENT_BYTES,
                on_rejected=lambda: ui.notify(
                    "Choose a JSON file smaller than 256 KB", type="warning"
                ),
            ).props('accept=".json,application/json"').classes("w-full")
            ui.button("Cancel", on_click=dialog.close).props("flat no-caps")
        dialog.open()

    @staticmethod
    def shortcuts() -> None:
        with ui.dialog() as dialog, ui.card().classes("studio-dialog"):
            ui.label("Keyboard shortcuts").classes("text-lg font-semibold")
            for action, keys in [
                ("Save draft", "Ctrl / Cmd + S"),
                ("Undo", "Ctrl / Cmd + Z"),
                ("Redo", "Ctrl / Cmd + Shift + Z"),
                ("Duplicate selection", "Ctrl / Cmd + D"),
                ("Delete selection", "Delete"),
                ("Select parent", "Esc"),
            ]:
                with ui.row().classes("w-full justify-between"):
                    ui.label(action)
                    ui.label(keys).classes("studio-muted")
            ui.label("Text fields keep their native editing shortcuts.").classes(
                "studio-muted text-sm"
            )
            ui.button("Done", on_click=dialog.close).props("no-caps")
        dialog.open()
