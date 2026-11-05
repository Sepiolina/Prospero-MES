"""Versioned, data-only screen documents and atomic editing operations."""

from __future__ import annotations

import json
from collections.abc import Callable, Iterator
from typing import Literal
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field, model_validator

MAX_DOCUMENT_BYTES = 256_000
CONTAINERS = {"column", "row", "grid", "card"}
KINDS = ("column", "row", "grid", "card", "text", "input", "select", "button", "table")
Kind = Literal[
    "column", "row", "grid", "card", "text", "input", "select", "button", "table"
]


class Properties(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)


class LayoutProperties(Properties):
    gap: int = Field(default=16, ge=0, le=64)
    padding: int = Field(default=16, ge=0, le=64)
    columns: int = Field(default=2, ge=1, le=6)
    align: Literal["stretch", "start", "center", "end"] = "stretch"
    justify: Literal["start", "center", "end", "space-between", "space-around"] = (
        "start"
    )
    wrap: bool = True
    mobile_columns: int | None = Field(default=None, ge=1, le=6)


class Appearance(Properties):
    """Typed appearance controls; screen files never contain executable CSS."""

    width: Literal["default", "fill", "content", "fixed"] = "default"
    width_px: int = Field(default=240, ge=24, le=3840)
    min_height: int = Field(default=0, ge=0, le=2160)
    margin: int = Field(default=0, ge=0, le=96)
    padding: int | None = Field(default=None, ge=0, le=96)
    radius: int | None = Field(default=None, ge=0, le=48)
    font_size: int | None = Field(default=None, ge=8, le=96)
    font_weight: Literal["inherit", "400", "500", "600", "700"] = "inherit"
    text_align: Literal["inherit", "left", "center", "right"] = "inherit"
    foreground: Literal[
        "inherit", "text", "muted", "accent", "positive", "negative", "warning"
    ] = "inherit"
    surface: Literal["inherit", "base", "panel"] = "inherit"
    border: bool = False


class ScreenDesign(Properties):
    mode: Literal["dark", "light"] = "dark"
    accent: str = Field(default="#2f7dfa", pattern=r"^#[0-9a-fA-F]{6}$")
    font: Literal["Arial", "System", "Georgia"] = "Arial"


class TextProperties(Properties):
    text: str = Field(default="Text", max_length=4000)
    variant: Literal["normal", "label", "h1", "h2", "h3"] = "normal"


class InputProperties(Properties):
    label: str = Field(default="Serial number", max_length=200)
    placeholder: str = Field(default="Scan or enter a value", max_length=200)
    required: bool = False


class SelectProperties(Properties):
    label: str = Field(default="Production line", max_length=200)
    options: list[str] = Field(
        default_factory=lambda: ["Line 1", "Line 2"], max_length=100
    )
    required: bool = False

    @model_validator(mode="after")
    def unique_options(self) -> SelectProperties:
        if any(not value or len(value) > 200 for value in self.options):
            raise ValueError("Options must contain 1–200 characters")
        if len(set(self.options)) != len(self.options):
            raise ValueError("Options must be unique")
        return self


class ButtonProperties(Properties):
    text: str = Field(default="Start cycle", max_length=200)
    type: Literal["primary", "destructive"] = "primary"
    action: str = Field(default="", max_length=100, pattern=r"^[A-Za-z0-9_.-]*$")


class TableProperties(Properties):
    title: str = Field(default="Recent results", max_length=200)
    columns: list[str] = Field(
        default_factory=lambda: ["Serial", "Result", "Time"],
        min_length=1,
        max_length=20,
    )

    @model_validator(mode="after")
    def unique_columns(self) -> TableProperties:
        if any(not value or len(value) > 100 for value in self.columns):
            raise ValueError("Column names must contain 1–100 characters")
        if len(set(self.columns)) != len(self.columns):
            raise ValueError("Column names must be unique")
        return self


PROPERTY_MODELS = {
    **{kind: LayoutProperties for kind in CONTAINERS},
    "text": TextProperties,
    "input": InputProperties,
    "select": SelectProperties,
    "button": ButtonProperties,
    "table": TableProperties,
}


class Node(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: str = Field(
        default_factory=lambda: uuid4().hex, pattern=r"^[A-Za-z0-9_-]{1,64}$"
    )
    kind: Kind
    name: str = Field(default="", max_length=100)
    props: dict = Field(default_factory=dict)
    appearance: Appearance = Field(default_factory=Appearance)
    children: list[Node] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_component(self) -> Node:
        self.props = PROPERTY_MODELS[self.kind].model_validate(self.props).model_dump()
        if self.kind not in CONTAINERS and self.children:
            raise ValueError("Only layout containers can have children")
        return self


class Screen(BaseModel):
    model_config = ConfigDict(extra="forbid")
    version: Literal[1] = 1
    name: str = Field(default="Untitled station", min_length=1, max_length=100)
    design: ScreenDesign = Field(default_factory=ScreenDesign)
    root: Node = Field(default_factory=lambda: Node(kind="column", name="Screen"))

    @model_validator(mode="after")
    def validate_tree(self) -> Screen:
        if self.root.kind not in CONTAINERS:
            raise ValueError("The screen root must be a layout container")
        seen: set[str] = set()

        def visit(node: Node, depth: int) -> None:
            if depth > 16 or len(seen) >= 200:
                raise ValueError(
                    "Screens support up to 200 components and 16 nested levels"
                )
            if node.id in seen:
                raise ValueError("Component IDs must be unique")
            seen.add(node.id)
            for child in node.children:
                visit(child, depth + 1)

        visit(self.root, 0)
        if len(self.to_json().encode()) > MAX_DOCUMENT_BYTES:
            raise ValueError("Screen file exceeds 256 KB")
        return self

    @classmethod
    def from_json(cls, content: str | bytes) -> Screen:
        if (
            len(content.encode() if isinstance(content, str) else content)
            > MAX_DOCUMENT_BYTES
        ):
            raise ValueError("Screen file exceeds 256 KB")
        return cls.model_validate_json(content)

    def to_json(self) -> str:
        return self.model_dump_json(indent=2)


def walk(node: Node) -> Iterator[Node]:
    yield node
    for child in node.children:
        yield from walk(child)


def find(root: Node, node_id: str) -> Node:
    for node in walk(root):
        if node.id == node_id:
            return node
    raise ValueError("Component no longer exists")


def parent_of(root: Node, node_id: str) -> Node:
    for node in walk(root):
        if any(child.id == node_id for child in node.children):
            return node
    raise ValueError("The screen root cannot be moved or removed")


def starter_screen() -> Screen:
    return Screen(
        name="Operator station",
        root=Node(
            kind="column",
            name="Screen",
            children=[
                Node(
                    kind="text",
                    name="Station title",
                    props={"text": "Production station", "variant": "h1"},
                ),
                Node(
                    kind="text",
                    props={"text": "Scan a serial number to begin a new cycle."},
                ),
                Node(
                    kind="card",
                    name="Cycle details",
                    children=[
                        Node(
                            kind="text",
                            props={"text": "Cycle details", "variant": "h3"},
                        ),
                        Node(
                            kind="grid",
                            name="Station fields",
                            children=[Node(kind="input"), Node(kind="select")],
                        ),
                        Node(kind="button"),
                    ],
                ),
                Node(kind="table"),
            ],
        ),
    )


class EditorState:
    """One document per editor client; failed edits never corrupt the current tree."""

    def __init__(self, screen: Screen | None = None) -> None:
        self.screen = screen or starter_screen()
        self.selected_id = self.screen.root.id
        self.undo_stack: list[str] = []
        self.redo_stack: list[str] = []
        self._edit_group: str | None = None

    @property
    def selected(self) -> Node:
        return find(self.screen.root, self.selected_id)

    def replace(self, screen: Screen, *, group: str | None = None) -> None:
        validated = Screen.model_validate(screen.model_dump())
        before = self.screen.to_json()
        if validated.to_json() == before:
            return
        if group is None or group != self._edit_group:
            self.undo_stack = (self.undo_stack + [before])[-50:]
        self._edit_group = group
        self.redo_stack.clear()
        self.screen = validated
        if not any(node.id == self.selected_id for node in walk(validated.root)):
            self.selected_id = validated.root.id

    def edit(
        self, change: Callable[[Screen], None], *, group: str | None = None
    ) -> None:
        candidate = self.screen.model_copy(deep=True)
        change(candidate)
        self.replace(candidate, group=group)

    def end_edit_group(self) -> None:
        self._edit_group = None

    def add(self, kind: str, parent_id: str, index: int | None = None) -> None:
        node = Node(kind=kind)

        def change(screen: Screen) -> None:
            parent = find(screen.root, parent_id)
            if parent.kind not in CONTAINERS:
                raise ValueError("Drop components into a layout container")
            position = len(parent.children) if index is None else index
            if not 0 <= position <= len(parent.children):
                raise ValueError("Invalid drop position")
            parent.children.insert(position, node)

        self.edit(change)
        self.selected_id = node.id

    def move(self, node_id: str, target_id: str, index: int) -> None:
        def change(screen: Screen) -> None:
            node = find(screen.root, node_id)
            source = parent_of(screen.root, node_id)
            target = find(screen.root, target_id)
            if target.kind not in CONTAINERS or any(
                n.id == target_id for n in walk(node)
            ):
                raise ValueError(
                    "A component cannot be moved inside itself or a non-container"
                )
            if not 0 <= index <= len(target.children):
                raise ValueError("Invalid drop position")
            old_index = source.children.index(node)
            source.children.remove(node)
            position = index - 1 if source is target and old_index < index else index
            target.children.insert(position, node)

        self.edit(change)
        self.selected_id = node_id

    def delete(self) -> None:
        node_id = self.selected_id

        def change(screen: Screen) -> None:
            parent = parent_of(screen.root, node_id)
            parent.children = [n for n in parent.children if n.id != node_id]

        self.edit(change)

    def duplicate(self) -> None:
        node_id = self.selected_id
        clone = self.selected.model_copy(deep=True)
        for node in walk(clone):
            node.id = uuid4().hex

        def change(screen: Screen) -> None:
            parent = parent_of(screen.root, node_id)
            position = next(i for i, n in enumerate(parent.children) if n.id == node_id)
            parent.children.insert(position + 1, clone)

        self.edit(change)
        self.selected_id = clone.id

    def history(self, *, redo: bool = False) -> None:
        self.end_edit_group()
        source, target = (
            (self.redo_stack, self.undo_stack)
            if redo
            else (self.undo_stack, self.redo_stack)
        )
        if source:
            target.append(self.screen.to_json())
            self.screen = Screen.from_json(source.pop())
            self.selected_id = self.screen.root.id

    def update_selected(
        self,
        name: str,
        props: dict,
        *,
        appearance: dict | None = None,
        group: str | None = None,
    ) -> None:
        def change(screen: Screen) -> None:
            node = find(screen.root, self.selected_id)
            node.name, node.props = name, props
            if appearance is not None:
                node.appearance = Appearance.model_validate(appearance)

        self.edit(change, group=group)


def json_literal(value: object) -> str:
    """Encode values before passing them to the browser's JavaScript API."""
    return json.dumps(value, ensure_ascii=True)
