"""Render saved screens with Prospero's real components and explicit Python actions."""

from __future__ import annotations

from collections.abc import Callable, Mapping

from nicegui import ui
from nicegui.element import Element

from prospero.components import PButton, PDataTable, PInput, PSelect, PText
from prospero.themes import Theme

from .schema import CONTAINERS, Node, Screen


def layout_style(node: Node) -> str:
    props = node.props
    base = f"gap: {props['gap']}px; padding: {props['padding']}px; align-items: {props['align']}; width: 100%; min-width: 0;"
    if node.kind == "grid":
        return (
            base
            + f" display: grid; grid-template-columns: repeat({props['columns']}, minmax(0, 1fr));"
        )
    direction = "row" if node.kind == "row" else "column"
    return base + f" display: flex; flex-direction: {direction}; flex-wrap: wrap;"


def render_component(
    node: Node, actions: Mapping[str, Callable] | None = None
) -> Element:
    """Create one component. Children are handled by the caller."""
    props = node.props
    if node.kind in CONTAINERS:
        element = ui.element("div").style(layout_style(node)).classes("p-screen-layout")
        if node.kind == "card":
            element.classes(Theme.CARD)
        return element
    if node.kind == "text":
        return PText(props["text"], variant=props["variant"])
    if node.kind == "input":
        return PInput(**props).classes("w-full")
    if node.kind == "select":
        return PSelect(**props)
    if node.kind == "button":
        callback = (actions or {}).get(props["action"])
        button = PButton(props["text"], type=props["type"], on_click=callback)
        if callback is None:
            button.disable()
        return button
    if node.kind == "table":
        columns = [
            {"name": f"c{i}", "field": f"c{i}", "label": label, "align": "left"}
            for i, label in enumerate(props["columns"])
        ]
        return PDataTable(columns, [], title=props["title"])
    raise ValueError(f"Unsupported component: {node.kind}")


def render_screen(
    screen: Screen, *, actions: Mapping[str, Callable] | None = None
) -> dict[str, Element]:
    """Return ID → element handles for station data binding and input access.

    Only supplied action callbacks can execute. Unbound buttons stay disabled.
    No code, imports, HTML, or CSS from the document is evaluated.
    """
    screen = Screen.model_validate(screen.model_dump())
    elements: dict[str, Element] = {}

    def render(node: Node, parent: Node | None = None) -> None:
        element = render_component(node, actions)
        if parent is not None and parent.kind == "row":
            element.style("flex: 1 1 140px; min-width: 0;")
        elements[node.id] = element
        with element:
            for child in node.children:
                render(child, node)

    render(screen.root)
    return elements
