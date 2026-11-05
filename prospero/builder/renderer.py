"""The single rendering path used by design, preview, and deployed stations."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from pathlib import Path

from nicegui import ui
from nicegui.element import Element

from prospero.components import PButton, PDataTable, PInput, PSelect, PText
from prospero.themes import Theme, ThemeColors
from .schema import CONTAINERS, Node, Screen


def layout_style(node: Node) -> str:
    p = node.props
    base = f"gap: {p['gap']}px; padding: {p['padding']}px; align-items: {p['align']}; justify-content: {p['justify']}; width: 100%; min-width: 0;"
    if node.kind == "grid":
        return (
            base
            + f" display: grid; --p-columns: {p['columns']}; --p-mobile-columns: {p['mobile_columns'] or p['columns']};"
        )
    direction = "row" if node.kind == "row" else "column"
    return (
        base
        + f" display: flex; flex-direction: {direction}; flex-wrap: {'wrap' if p['wrap'] else 'nowrap'};"
    )


def appearance_style(node: Node) -> str:
    a = node.appearance
    styles = []
    if a.min_height:
        styles.append(f"min-height: {a.min_height}px")
    if a.margin:
        styles.append(f"margin: {a.margin}px")
    if a.width == "fill":
        styles += ["width: 100%", "flex: 1 1 0%"]
    elif a.width == "content":
        styles += ["width: max-content", "flex: 0 0 auto", "align-self: flex-start"]
    elif a.width == "fixed":
        styles += [f"width: {a.width_px}px", f"flex: 0 0 {a.width_px}px"]
    for key in ("padding", "radius", "font_size"):
        value = getattr(a, key)
        css = {
            "padding": "padding",
            "radius": "border-radius",
            "font_size": "font-size",
        }[key]
        if value is not None:
            styles.append(f"{css}: {value}px !important")
    if a.font_weight != "inherit":
        styles.append(f"font-weight: {a.font_weight} !important")
    if a.text_align != "inherit":
        styles.append(f"text-align: {a.text_align}")
    if a.foreground != "inherit":
        token = {"text": "text", "muted": "text-muted"}.get(a.foreground, a.foreground)
        styles.append(f"color: var(--p-{token}) !important")
    if a.surface != "inherit":
        styles.append(
            f"background: var(--p-{'bg' if a.surface == 'base' else 'panel'}) !important"
        )
    if a.border:
        styles.append("border: 1px solid var(--p-panel-border)")
    return "; ".join(styles)


def render_component(
    node: Node, actions: Mapping[str, Callable] | None = None
) -> Element:
    p = node.props
    if node.kind in CONTAINERS:
        element = ui.element("div").style(layout_style(node)).classes("p-screen-layout")
        if node.kind == "grid":
            element.classes("p-screen-grid")
        if node.kind == "card":
            element.classes(Theme.CARD)
        return element
    if node.kind == "text":
        return PText(p["text"], variant=p["variant"])
    if node.kind == "input":
        return PInput(**p).classes("w-full")
    if node.kind == "select":
        return PSelect(**p)
    if node.kind == "button":
        callback = (actions or {}).get(p["action"])
        button = PButton(p["text"], type=p["type"], on_click=callback)
        if callback is None:
            button.disable()
        return button
    if node.kind == "table":
        columns = [
            {"name": f"c{i}", "field": f"c{i}", "label": label, "align": "left"}
            for i, label in enumerate(p["columns"])
        ]
        return PDataTable(columns, [], title=p["title"])
    raise ValueError(f"Unsupported component: {node.kind}")


def render_screen(
    screen: Screen, *, actions: Mapping[str, Callable] | None = None
) -> dict[str, Element]:
    """Return stable ID → component handles, using identical DOM in every mode.

    Unknown action names stay disabled. Editor chrome belongs to the canvas
    overlay, never this tree. Responsive grids use the screen container width.
    """
    screen = Screen.model_validate(screen.model_dump())
    ui.add_css(Path(__file__).with_name("screen.css").read_text())
    design = screen.design
    dark = design.mode == "dark"
    palette = "DARK" if dark else "LIGHT"
    font = {
        "Arial": "Arial, Helvetica, sans-serif",
        "System": "system-ui, sans-serif",
        "Georgia": "Georgia, serif",
    }[design.font]
    tokens = {
        "bg": getattr(ThemeColors, f"{palette}_BG"),
        "panel": getattr(ThemeColors, f"{palette}_PANEL"),
        "panel-border": getattr(ThemeColors, f"{palette}_PANEL_BORDER"),
        "text": getattr(ThemeColors, f"{palette}_TEXT"),
        "text-muted": getattr(ThemeColors, f"{palette}_TEXT_MUTED"),
        "accent": design.accent,
        "font": font,
        "positive": ThemeColors.POSITIVE,
        "negative": ThemeColors.NEGATIVE,
        "warning": ThemeColors.WARNING,
    }
    elements: dict[str, Element] = {}

    def render(node: Node, parent: Node | None = None) -> None:
        element = render_component(node, actions)
        if parent is not None and parent.kind == "row":
            element.style("flex: 1 1 140px; min-width: 0;")
        element.style(appearance_style(node))
        element.props.update(
            {
                "data-screen-id": node.id,
                "data-screen-kind": node.kind,
                "data-screen-name": node.name or node.kind.title(),
                "data-screen-parent": parent.id if parent else "",
            }
        )
        if node.kind in {"input", "select", "table"}:
            element.props["dark"] = dark
        elements[node.id] = element
        with element:
            for child in node.children:
                render(child, node)

    with (
        ui.element("div")
        .classes("p-rendered-screen")
        .style("; ".join(f"--p-{k}: {v}" for k, v in tokens.items()))
    ):
        render(screen.root)
    return elements
