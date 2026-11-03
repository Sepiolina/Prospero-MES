"""Screen persistence, tree invariants, editing transactions, and runtime integration."""

import json

import pytest

from prospero.builder.schema import (
    MAX_DOCUMENT_BYTES,
    EditorState,
    Node,
    Screen,
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
