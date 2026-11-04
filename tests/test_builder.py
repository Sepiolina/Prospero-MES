"""Screen persistence, tree invariants, editing transactions, and runtime integration."""

import json
from pathlib import Path

import pytest

from prospero.builder.schema import (
    Appearance,
    MAX_DOCUMENT_BYTES,
    EditorState,
    Node,
    Screen,
    ScreenDesign,
    find,
    starter_screen,
    walk,
)


def simple_screen():
    return Screen(
        root=Node(
            id="root",
            kind="column",
            children=[
                Node(id="first", kind="text"),
                Node(
                    id="group", kind="row", children=[Node(id="nested", kind="input")]
                ),
                Node(id="last", kind="button"),
            ],
        )
    )


def test_round_trip_preserves_ids_and_properties():
    screen = starter_screen()
    assert Screen.from_json(screen.to_json()) == screen
    assert len({n.id for n in walk(screen.root)}) == 10


def test_original_screen_files_remain_loadable_without_new_fields():
    """The committed v1 example predates appearance and document design settings."""
    path = Path(__file__).parents[1] / "examples/screens/operator-station.json"
    legacy = json.loads(path.read_text())
    assert "design" not in legacy
    expected_ids = []

    def collect_ids(node):
        expected_ids.append(node["id"])
        assert "appearance" not in node
        for child in node["children"]:
            collect_ids(child)

    collect_ids(legacy["root"])
    loaded = Screen.from_json(json.dumps(legacy))
    assert [node.id for node in walk(loaded.root)] == expected_ids
    assert loaded.design == ScreenDesign()
    assert all(node.appearance == Appearance() for node in walk(loaded.root))
    assert Screen.from_json(loaded.to_json()) == loaded


@pytest.mark.parametrize(
    "appearance",
    [
        {"width": "fixed", "width_px": 0},
        {"width_px": "200"},
        {"padding": -1},
        {"font_size": 500},
        {"radius": 100},
        {"foreground": "url(https://example.com)"},
        {"style": "position: fixed"},
    ],
)
def test_invalid_appearance_never_changes_document_or_history(appearance):
    state = EditorState(simple_screen())
    state.selected_id = "first"
    before = state.screen.to_json()
    with pytest.raises(ValueError):
        state.update_selected("Modified", {"text": "Changed"}, appearance=appearance)
    assert state.screen.to_json() == before
    assert not state.undo_stack


@pytest.mark.parametrize(
    "design",
    [
        {"accent": "red; background: url(https://example.com)"},
        {"accent": "#fff"},
        {"mode": "arbitrary"},
        {"font": "https://example.com/font.woff"},
    ],
)
def test_document_theme_rejects_unsupported_values(design):
    data = simple_screen().model_dump()
    data["design"] = design
    with pytest.raises(ValueError):
        Screen.from_json(json.dumps(data))


def test_typing_group_is_one_undo_step_and_new_focus_is_a_new_step():
    state = EditorState(simple_screen())
    state.selected_id = "first"
    original = state.screen.to_json()
    for text in ["S", "St", "Station"]:
        state.update_selected("Heading", {"text": text}, group="first.text")
    assert len(state.undo_stack) == 1
    first_edit = state.screen.to_json()
    state.end_edit_group()
    state.update_selected("Heading", {"text": "Station A"}, group="first.text")
    assert len(state.undo_stack) == 2
    state.history()
    assert state.screen.to_json() == first_edit
    state.history()
    assert state.screen.to_json() == original
    state.history(redo=True)
    assert state.screen.to_json() == first_edit


def test_appearance_edit_and_document_theme_survive_export_and_undo():
    state = EditorState(simple_screen())
    state.selected_id = "first"
    before = state.screen.to_json()
    appearance = {
        "width": "fixed",
        "width_px": 320,
        "font_size": 32,
        "font_weight": "700",
        "foreground": "accent",
        "margin": 8,
    }
    state.update_selected("Custom heading", {"text": "Assembly"}, appearance=appearance)
    state.edit(
        lambda screen: setattr(
            screen,
            "design",
            ScreenDesign(mode="light", accent="#126647", font="System"),
        )
    )
    restored = Screen.from_json(state.screen.to_json())
    assert find(restored.root, "first").appearance.width_px == 320
    assert restored.design.mode == "light"
    state.history()
    assert state.screen.design == ScreenDesign()
    state.history()
    assert state.screen.to_json() == before


def test_structural_edit_breaks_typing_group_and_does_not_merge_undo_steps():
    state = EditorState(simple_screen())
    state.selected_id = "first"
    state.update_selected("Heading", {"text": "One"}, group="first.text")
    state.add("input", "root")
    added = state.selected_id
    state.selected_id = "first"
    state.update_selected("Heading", {"text": "Two"}, group="first.text")
    state.history()
    assert find(state.screen.root, "first").props["text"] == "One"
    assert find(state.screen.root, added).kind == "input"
    state.history()
    with pytest.raises(ValueError):
        find(state.screen.root, added)


def test_responsive_grid_settings_round_trip_and_reject_invalid_columns():
    node = Node(
        kind="grid",
        props={"columns": 3, "mobile_columns": 1, "justify": "center", "wrap": False},
    )
    screen = Screen(root=node)
    restored = Screen.from_json(screen.to_json())
    assert restored.root.props == node.props
    with pytest.raises(ValueError):
        Node(kind="grid", props={"mobile_columns": 0})


@pytest.mark.parametrize(
    "change",
    [
        lambda d: d.update(version=2),
        lambda d: d["root"].update(kind="script"),
        lambda d: d["root"]["props"].update(gap=-1),
        lambda d: d["root"]["props"].update(padding="16"),
        lambda d: d["root"]["props"].update(
            style="background: url(https://example.com)"
        ),
        lambda d: d["root"]["children"][0].update(id="root"),
        lambda d: d["root"]["children"][0].update(children=[{"kind": "text"}]),
        lambda d: d["root"]["children"][2]["props"].update(action="__import__('os')"),
    ],
)
def test_rejects_unsupported_or_malformed_documents(change):
    data = simple_screen().model_dump()
    change(data)
    with pytest.raises(ValueError):
        Screen.from_json(json.dumps(data))


def test_document_size_and_tree_limits():
    with pytest.raises(ValueError, match="256 KB"):
        Screen.from_json(" " * (MAX_DOCUMENT_BYTES + 1))
    with pytest.raises(ValueError, match="200 components"):
        Screen(
            root=Node(kind="column", children=[Node(kind="text") for _ in range(200)])
        )
    root = Node(kind="column")
    for _ in range(17):
        root = Node(kind="column", children=[root])
    with pytest.raises(ValueError, match="16 nested"):
        Screen(root=root)
    with pytest.raises(ValueError, match="256 KB"):
        Screen(
            root=Node(
                kind="column",
                children=[
                    Node(kind="text", props={"text": "x" * 4000}) for _ in range(70)
                ],
            )
        )


def test_move_within_parent_and_between_containers():
    state = EditorState(simple_screen())
    state.move("first", "root", 3)
    assert [n.id for n in state.screen.root.children] == ["group", "last", "first"]
    state.move("first", "root", 0)
    assert [n.id for n in state.screen.root.children] == ["first", "group", "last"]
    state.move("last", "group", 0)
    assert [n.id for n in find(state.screen.root, "group").children] == [
        "last",
        "nested",
    ]


@pytest.mark.parametrize(
    "node,target,index",
    [
        ("root", "group", 0),
        ("group", "group", 0),
        ("group", "nested", 0),
        ("nested", "first", 0),
        ("nested", "root", -1),
        ("nested", "root", 99),
        ("missing", "root", 0),
    ],
)
def test_invalid_moves_leave_document_and_history_unchanged(node, target, index):
    state = EditorState(simple_screen())
    original = state.screen.to_json()
    with pytest.raises(ValueError):
        state.move(node, target, index)
    assert state.screen.to_json() == original
    assert state.undo_stack == []


def test_deep_cycle_is_rejected_atomically():
    state = EditorState(
        Screen(
            root=Node(
                id="root",
                kind="column",
                children=[
                    Node(
                        id="outer", kind="card", children=[Node(id="inner", kind="row")]
                    ),
                ],
            )
        )
    )
    original = state.screen.to_json()
    with pytest.raises(ValueError):
        state.move("outer", "inner", 0)
    assert state.screen.to_json() == original


def test_duplicate_delete_undo_and_redo():
    state = EditorState(simple_screen())
    original = state.screen.to_json()
    state.selected_id = "group"
    state.duplicate()
    duplicate = state.selected
    assert duplicate.id != "group"
    assert duplicate.children[0].id != "nested"
    assert duplicate.props == find(state.screen.root, "group").props
    assert len(list(walk(state.screen.root))) == 7
    copied = state.screen.to_json()
    state.history()
    assert state.screen.to_json() == original
    state.history(redo=True)
    assert state.screen.to_json() == copied
    state.selected_id = duplicate.id
    state.delete()
    assert state.screen.to_json() == original
    state.history()
    state.add("text", "root")
    assert not state.redo_stack


def test_root_delete_and_invalid_property_edits_are_atomic():
    state = EditorState(simple_screen())
    original = state.screen.to_json()
    with pytest.raises(ValueError):
        state.delete()
    with pytest.raises(ValueError):
        state.update_selected("Screen", {"gap": 100})
    assert state.screen.to_json() == original
    assert not state.undo_stack


def test_add_select_update_and_history_limit():
    state = EditorState(simple_screen())
    state.add("select", "group", 0)
    state.update_selected("Line selector", {"options": ["A", "B"], "required": True})
    assert state.selected.name == "Line selector"
    assert state.selected.props["options"] == ["A", "B"]
    for i in range(60):
        state.update_selected(f"Selector {i}", state.selected.props)
    assert len(state.undo_stack) == 50


def test_renderer_uses_prospero_components_and_only_registered_actions():
    from nicegui import ui
    from prospero.builder.renderer import render_screen
    from prospero.components import PButton, PInput, PSelect, PText, PDataTable

    called = []
    screen = starter_screen()
    button_node = next(n for n in walk(screen.root) if n.kind == "button")
    button_node.props["action"] = "start_cycle"
    with ui.element("div") as host:
        elements = render_screen(
            screen, actions={"start_cycle": lambda: called.append("cycle")}
        )
    assert len(elements) == 10
    assert {type(e) for e in elements.values()} >= {
        PButton,
        PInput,
        PSelect,
        PText,
        PDataTable,
    }
    button = elements[button_node.id]
    assert button.is_enabled
    button._handle_click()
    assert called == ["cycle"]
    with host:
        preview = render_screen(screen)
    assert not preview[button_node.id].is_enabled
    preview[button_node.id]._handle_click()
    assert called == ["cycle"]
    host.delete()
