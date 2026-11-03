"""NiceGUI visual authoring UI. Each connected browser tab owns its editor state."""

from __future__ import annotations

from pathlib import Path

from nicegui import events, ui

from .renderer import layout_style, render_component, render_screen
from .schema import (
    CONTAINERS,
    KINDS,
    MAX_DOCUMENT_BYTES,
    EditorState,
    Node,
    Screen,
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


class ScreenEditor:
    def __init__(self) -> None:
        self.state = EditorState()
        self.saved_json = ""
        self.preview = False
        self.viewport = "Desktop"

    async def build(self) -> None:
        ui.add_css(Path(__file__).with_name("editor.css").read_text())
        with ui.column().classes("builder-shell"):
            with ui.row().classes("builder-header"):
                ui.icon("dashboard_customize", size="28px").classes("builder-accent")
                with ui.column().classes("gap-0"):
                    ui.label("PROSPERO").classes("builder-eyebrow")
                    ui.label("Screen studio").classes("text-lg font-semibold")
                ui.space()
                self.status = ui.label("Unsaved draft").classes("builder-muted text-xs")
                ui.button("Save draft", icon="save", on_click=self.save).props(
                    "flat no-caps"
                )
                ui.button("Export JSON", icon="download", on_click=self.export).props(
                    "unelevated no-caps"
                )
            self.toolbar()
            self.workspace()
        await ui.context.client.connected()
        try:
            saved = await ui.run_javascript(
                f"localStorage.getItem({json_literal(STORAGE_KEY)})"
            )
            if saved:
                self.state = EditorState(Screen.from_json(saved))
                self.saved_json = self.state.screen.to_json()
                self.refresh()
        except (ValueError, TypeError):
            ui.notify(
                "The saved draft could not be opened. Import a valid screen file to recover it.",
                type="warning",
            )
        except (RuntimeError, TimeoutError):
            ui.notify(
                "Browser storage is unavailable. Use Export JSON to keep your work.",
                type="warning",
            )

    @ui.refreshable
    def toolbar(self) -> None:
        with ui.row().classes("builder-toolbar"):
            title = (
                ui.input(value=self.state.screen.name)
                .props('dense borderless aria-label="Screen name"')
                .classes("w-56")
            )
            title.on("blur", lambda: self.rename(title.value))
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
            ui.button(
                icon="undo", on_click=lambda: self.change(self.state.history)
            ).props('flat round aria-label="Undo"').set_enabled(
                bool(self.state.undo_stack)
            )
            ui.button(
                icon="redo",
                on_click=lambda: self.change(lambda: self.state.history(redo=True)),
            ).props('flat round aria-label="Redo"').set_enabled(
                bool(self.state.redo_stack)
            )
            ui.space()
            ui.select(
                ["Desktop", "Tablet", "Phone"],
                value=self.viewport,
                on_change=self.set_viewport,
            ).props('dense outlined aria-label="Preview width"').classes("w-32")
            ui.button(
                "Edit" if self.preview else "Preview",
                icon="edit" if self.preview else "play_arrow",
                on_click=self.toggle_preview,
            ).props("outline no-caps")

    @ui.refreshable
    def workspace(self) -> None:
        with ui.element("div").classes("builder-workspace"):
            with ui.column().classes("builder-sidebar"):
                ui.label("COMPONENTS").classes("builder-eyebrow")
                ui.label("Drag onto the canvas, or click to add.").classes(
                    "builder-muted text-xs"
                )
                with ui.element("div").classes("builder-palette"):
                    for kind in KINDS:
                        button = (
                            ui.button(
                                kind.title(),
                                icon=ICONS[kind],
                                on_click=lambda k=kind: self.add(k),
                            )
                            .props("flat no-caps")
                            .classes("builder-palette-item")
                        )
                        self.drag(button, {"kind": kind})
                        button.set_enabled(not self.preview)
                ui.label("SCREEN TREE").classes("builder-eyebrow mt-6")
                ui.label("Select a container to add inside it.").classes(
                    "builder-muted text-xs"
                )
                self.tree(self.state.screen.root)
            with ui.column().classes("builder-stage"):
                with ui.row().classes("w-full items-center"):
                    ui.label("PREVIEW" if self.preview else "CANVAS").classes(
                        "builder-eyebrow"
                    )
                    ui.space()
                    count = len(list(walk(self.state.screen.root)))
                    ui.label(
                        f"{count} {'component' if count == 1 else 'components'}"
                    ).classes("builder-muted text-xs")
                if self.preview:
                    ui.label(
                        "Try inputs and layouts. Station actions are disabled in preview."
                    ).classes("builder-muted text-sm")
                else:
                    ui.label(
                        "Drop inside a container. Use the top edge of a component to insert before it."
                    ).classes("builder-muted text-xs")
                width = {"Desktop": "100%", "Tablet": "768px", "Phone": "390px"}[
                    self.viewport
                ]
                with (
                    ui.column()
                    .classes("builder-canvas")
                    .style(f"width: {width}; max-width: 100%;")
                ):
                    if self.preview:
                        render_screen(self.state.screen)
                    else:
                        self.canvas_node(self.state.screen.root)
            with ui.column().classes("builder-inspector"):
                self.inspector()

    def tree(self, node: Node, depth: int = 0) -> None:
        button = (
            ui.button(
                node.name or node.kind.title(),
                icon=ICONS[node.kind],
                on_click=lambda: self.select(node.id),
            )
            .props("flat no-caps align=left")
            .classes("builder-tree-item")
        )
        button.style(f"padding-left: {8 + depth * 12}px;")
        if node.id == self.state.selected_id:
            button.classes("is-selected")
        for child in node.children:
            self.tree(child, depth + 1)

    def canvas_node(
        self, node: Node, parent: Node | None = None, index: int = 0
    ) -> None:
        with (
            ui.column()
            .classes("builder-node")
            .props(f'data-node-id="{node.id}"') as wrapper
        ):
            if node.id == self.state.selected_id:
                wrapper.classes("is-selected")
            wrapper.on(
                "click",
                lambda: self.select(node.id),
                js_handler="event => { event.stopPropagation(); emit(); }",
            )
            if parent:
                self.drag(wrapper, {"id": node.id})
                before = (
                    ui.element("div")
                    .classes("builder-insert")
                    .props('title="Insert before this component"')
                )
                self.drop(before, parent.id, index)
            with ui.row().classes("builder-node-label"):
                ui.icon(ICONS[node.kind], size="14px")
                ui.label(node.name or node.kind.title())
                ui.space()
                if parent:
                    ui.icon("drag_indicator", size="14px")
            if node.kind in CONTAINERS:
                with (
                    ui.element("div")
                    .style(layout_style(node))
                    .classes("builder-layout") as container
                ):
                    if node.kind == "card":
                        container.classes("builder-card")
                    for child_index, child in enumerate(node.children):
                        self.canvas_node(child, node, child_index)
                    zone = ui.label("+ Drop here or select this container").classes(
                        "builder-dropzone"
                    )
                    self.drop(zone, node.id, len(node.children))
                    self.drop(container, node.id, len(node.children))
            else:
                with ui.column().classes("builder-component"):
                    render_component(node)

    @staticmethod
    def drag(element, payload: dict) -> None:
        element.props("draggable=true")
        element.on(
            "dragstart",
            js_handler="event => { event.stopPropagation(); event.dataTransfer.effectAllowed = 'copyMove'; "
            f"event.dataTransfer.setData('application/x-prospero', {json_literal(json_literal(payload))}); }}",
        )

    def drop(self, element, parent_id: str, index: int) -> None:
        element.on(
            "dragover",
            js_handler="event => { event.preventDefault(); event.stopPropagation(); event.currentTarget.classList.add('drop-active'); }",
        )
        element.on(
            "dragleave",
            js_handler="event => { event.currentTarget.classList.remove('drop-active'); }",
        )
        element.on(
            "drop",
            lambda e: self.handle_drop(e.args, parent_id, index),
            js_handler="""event => {
            event.preventDefault(); event.stopPropagation();
            event.currentTarget.classList.remove('drop-active');
            const data = event.dataTransfer.getData('application/x-prospero');
            if (data) { try { emit(JSON.parse(data)); } catch {} }
        }""",
        )

    def handle_drop(self, payload: dict, parent_id: str, index: int) -> None:
        if self.preview or not isinstance(payload, dict):
            return
        if isinstance(payload.get("id"), str):
            self.change(lambda: self.state.move(payload["id"], parent_id, index))
        elif payload.get("kind") in KINDS:
            self.change(lambda: self.state.add(payload["kind"], parent_id, index))

    def inspector(self) -> None:
        node = self.state.selected
        ui.label("PROPERTIES").classes("builder-eyebrow")
        ui.label(node.kind.title()).classes("text-lg font-semibold")
        if self.preview:
            ui.label("Return to Edit to change this screen.").classes("builder-muted")
            return
        name = (
            ui.input("Component name", value=node.name)
            .props("dense outlined")
            .classes("w-full")
        )
        inputs = {}
        for key, value in node.props.items():
            if key == "columns" and node.kind in CONTAINERS and node.kind != "grid":
                continue
            label = key.replace("_", " ").title()
            if isinstance(value, bool):
                field = ui.checkbox(label, value=value)
            elif isinstance(value, int):
                field = ui.number(
                    label,
                    value=value,
                    min=1 if key == "columns" else 0,
                    max=6 if key == "columns" else 64,
                    step=1,
                ).props("dense outlined")
            elif key in {"variant", "type", "align"}:
                options = {
                    "variant": ["normal", "label", "h1", "h2", "h3"],
                    "type": ["primary", "destructive"],
                    "align": ["stretch", "start", "center", "end"],
                }[key]
                field = ui.select(options, value=value, label=label).props(
                    "dense outlined"
                )
            elif isinstance(value, list):
                field = ui.textarea(
                    f"{label} (one per line)", value="\n".join(value)
                ).props("dense outlined autogrow")
            elif key == "text":
                field = ui.textarea(label, value=value).props("dense outlined autogrow")
            else:
                field = ui.input(label, value=value).props("dense outlined")
            field.classes("w-full")
            inputs[key] = field
        if node.kind == "button":
            ui.label(
                "Action names connect to Python callbacks in your station. They do not run in the editor."
            ).classes("builder-muted text-xs")

        def apply() -> None:
            props = dict(node.props)
            for key, field in inputs.items():
                original = node.props[key]
                value = field.value
                if isinstance(original, list):
                    value = [
                        line.strip() for line in value.splitlines() if line.strip()
                    ]
                elif isinstance(original, int) and not isinstance(original, bool):
                    if value is None or value != int(value):
                        ui.notify(
                            "Enter whole numbers for layout values", type="warning"
                        )
                        return
                    value = int(value)
                props[key] = value
            self.change(lambda: self.state.update_selected(name.value, props))

        ui.button("Apply properties", icon="check", on_click=apply).props(
            "unelevated no-caps"
        ).classes("w-full")
        ui.label("Apply changes before selecting another component.").classes(
            "builder-muted text-xs"
        )
        if node.id != self.state.screen.root.id:
            ui.label("ARRANGE").classes("builder-eyebrow mt-4")
            excluded = {n.id for n in walk(node)}
            parents = {
                n.id: n.name or n.kind.title()
                for n in walk(self.state.screen.root)
                if n.kind in CONTAINERS and n.id not in excluded
            }
            parent = parent_of(self.state.screen.root, node.id)
            target = (
                ui.select(parents, value=parent.id, label="Move into container")
                .props("dense outlined")
                .classes("w-full")
            )

            def reparent() -> None:
                from .schema import find

                count = len(find(self.state.screen.root, target.value).children)
                self.change(lambda: self.state.move(node.id, target.value, count))

            ui.button("Move to container", on_click=reparent).props(
                "flat no-caps"
            ).classes("w-full")
            position = parent.children.index(node)
            with ui.row().classes("gap-1"):
                ui.button(
                    icon="arrow_upward",
                    on_click=lambda: self.change(
                        lambda: self.state.move(node.id, parent.id, position - 1)
                    ),
                ).props('flat aria-label="Move earlier"').set_enabled(position > 0)
                ui.button(
                    icon="arrow_downward",
                    on_click=lambda: self.change(
                        lambda: self.state.move(node.id, parent.id, position + 2)
                    ),
                ).props('flat aria-label="Move later"').set_enabled(
                    position < len(parent.children) - 1
                )
                ui.button(
                    icon="content_copy",
                    on_click=lambda: self.change(self.state.duplicate),
                ).props('flat aria-label="Duplicate component"')
                ui.button(
                    icon="delete_outline",
                    on_click=lambda: self.change(self.state.delete),
                ).props('flat aria-label="Delete component"')
        ui.label(f"ID: {node.id}").classes("builder-muted text-xs break-all mt-4")

    def change(self, operation) -> None:
        try:
            operation()
        except (ValueError, TypeError) as error:
            ui.notify(f"Could not apply change: {str(error)[:250]}", type="warning")
            return
        self.refresh()

    def refresh(self) -> None:
        self.toolbar.refresh()
        self.workspace.refresh()
        self.status.set_text(
            "Draft saved in this browser"
            if self.state.screen.to_json() == self.saved_json
            else "Unsaved draft"
        )

    def select(self, node_id: str) -> None:
        self.state.selected_id = node_id
        self.workspace.refresh()

    def add(self, kind: str) -> None:
        if self.preview:
            return
        node = self.state.selected
        parent = (
            node
            if node.kind in CONTAINERS
            else parent_of(self.state.screen.root, node.id)
        )
        self.change(lambda: self.state.add(kind, parent.id))

    def rename(self, name: str) -> None:
        if name.strip() == self.state.screen.name:
            return
        self.change(
            lambda: self.state.edit(
                lambda screen: setattr(screen, "name", name.strip())
            )
        )

    def set_viewport(self, event: events.ValueChangeEventArguments) -> None:
        self.viewport = event.value
        self.workspace.refresh()

    def toggle_preview(self) -> None:
        self.preview = not self.preview
        self.refresh()

    async def save(self) -> None:
        content = self.state.screen.to_json()
        try:
            result = await ui.run_javascript(f"""(() => {{
                try {{ localStorage.setItem({json_literal(STORAGE_KEY)}, {json_literal(content)}); return true; }}
                catch {{ return false; }}
            }})()""")
            if not result:
                raise RuntimeError("Storage unavailable")
        except (RuntimeError, TimeoutError):
            ui.notify(
                "Could not save in this browser. Export JSON to keep your work.",
                type="negative",
            )
            return
        self.saved_json = content
        self.refresh()
        ui.notify("Draft saved in this browser", type="positive")

    def export(self) -> None:
        ui.download.content(
            self.state.screen.to_json(),
            "prospero-screen.json",
            media_type="application/json",
        )

    def confirm_replace(self, screen: Screen) -> None:
        with ui.dialog() as dialog, ui.card():
            ui.label(f'Open "{screen.name}"?').classes("text-lg font-semibold")
            ui.label("This replaces the canvas. You can undo the change.")
            with ui.row():
                ui.button("Cancel", on_click=dialog.close).props("flat no-caps")

                def replace() -> None:
                    self.change(lambda: self.state.replace(screen))
                    dialog.close()

                ui.button("Open screen", on_click=replace).props("no-caps")
        dialog.open()

    def import_dialog(self) -> None:
        with ui.dialog() as dialog, ui.card().classes("w-96"):
            ui.label("Import a screen").classes("text-lg font-semibold")
            ui.label("Choose a Prospero JSON screen, up to 256 KB.").classes(
                "builder-muted"
            )

            async def uploaded(event: events.UploadEventArguments) -> None:
                try:
                    screen = Screen.from_json(await event.file.read())
                except (ValueError, TypeError) as error:
                    ui.notify(
                        f"Invalid screen file: {str(error)[:250]}", type="negative"
                    )
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
