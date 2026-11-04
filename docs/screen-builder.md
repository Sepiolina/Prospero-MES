# Prospero Screen Studio

Build station screens using Prospero's NiceGUI components. The editor, preview,
and station renderer share the same component tree and rendering code. Selection
outlines and drop guides sit above the screen without adding padding, labels, or
layout boxes to the exported UI.

## Start the editor

From the repository root, using the project's Python environment:

```bash
python -m prospero.builder
```

Open **http://127.0.0.1:8081**. Use `--port 8082` to choose another port.
An importable example is included at `examples/screens/operator-station.json`.
The editor has a separate launcher because `main.py` depends on a station module
that is not included in this repository. There is no frontend build step or
additional runtime dependency.

## Build and inspect a screen

1. Start with the operator station template or open a blank screen from the screen menu.
2. Find a component in the palette. Drag it onto a layout, or select a container
   in the layer tree and click the component to add it. Available layouts are
   rows, columns, grids, and cards; content includes text, inputs, selectors,
   buttons, and tables.
3. Select a component directly on the canvas or in the layer tree. The selection
   overlay identifies it and shows its rendered dimensions. It does not alter
   the component's size or position.
4. Edit its properties in the inspector. Valid changes update the screen live;
   there is no separate Apply step. Invalid values are reported in the inspector
   so they can be corrected before changing selection or saving.
5. Drag an existing component into another container, or use the insertion guide
   to place it before or after a sibling. Move, duplicate, and delete controls
   are also available in the inspector. Undo and redo cover document changes.
6. Switch to **Preview** to use inputs and selectors without selection overlays.
   Button actions remain disconnected from MES operations in the editor.

Typing into a property is grouped into an undoable edit rather than creating a
separate undo entry for every character. History holds the last 50 edits and is
not persisted across reloads.

## Viewport size and zoom

Desktop, tablet, and phone presets use screen widths of **1280**, **768**, and
**390 CSS pixels**. A custom width lets you check the intended station display.
**Fit** scales the view to the available workspace; percentage zoom controls let
you inspect details. Zoom changes the view, not the screen's layout width.

Edit and preview use the same screen dimensions, component styles, and responsive
rules. To reproduce that result in a station, mount the exported screen in a
container of the same width and use the shared renderer. Different installed
fonts, browser rendering, application styles, or runtime data can still change
what is displayed.

Grids have a normal column count and an optional mobile column count. The mobile
count applies when the rendered screen's container is **600 CSS pixels or less**,
including when a larger editor window shows a phone-sized screen. Leaving it
unset preserves the normal column count. This is a container-width rule; zooming
out does not activate it.

## Customize components and screen appearance

Layout controls include gap, padding, alignment, justification, row wrapping,
and grid columns. Appearance controls provide:

- Default, fill, content-sized, or fixed-width sizing, plus minimum height.
- Margin, padding, corner radius, and borders.
- Font size, weight, alignment, and theme-based foreground and surface colors.

Screen appearance controls set light or dark mode, the accent color, and font
family. These settings travel with the JSON screen and are applied by the station
renderer. They do not require custom CSS in the document. Defaults preserve the
appearance of screens exported by the first version of Screen Studio.

## Save, recover, and share

The editor keeps two distinct browser copies:

- **Recovery copy:** automatic recovery for the current tab, using session storage.
  It can restore valid edits after a reload. Browser session storage is temporary;
  it is not a backup for closing or clearing the browser session.
- **Saved draft:** an explicit **Save draft** writes to this browser's local
  storage. Tabs share this saved draft. If another tab has changed it since it
  was loaded, the editor reports the conflict instead of silently overwriting it.

Use **Export JSON** to keep a durable file, maintain multiple screens, share a
screen, or check it into Git. Import JSON from the screen menu. Screen files are
validated before replacing the canvas, and opening a different screen can be
undone. Browser storage may be unavailable or cleared; export files for work you
need to retain.

## Keyboard shortcuts

| Shortcut | Action |
| --- | --- |
| Ctrl/Cmd + S | Save draft |
| Ctrl/Cmd + Z | Undo |
| Ctrl/Cmd + Shift + Z, or Ctrl/Cmd + Y | Redo |
| Ctrl/Cmd + D | Duplicate the selected component |
| Delete or Backspace | Delete the selected component |
| Escape | Select the parent container |

While typing in a form field, native text-editing shortcuts are preserved.
Ctrl/Cmd + S still saves the draft. Document-editing shortcuts are inactive in
preview and while a dialog is open.

## Render an exported screen in a station

The JSON is a versioned component tree, not executable code. Keep screen files in
your station's source directory and load them with `Screen.from_json`:

```python
from pathlib import Path

from nicegui import ui
from prospero.builder import Screen
from prospero.builder.renderer import render_screen
from prospero.themes import setup_theme

screen = Screen.from_json(Path("stations/assembly.json").read_text())

@ui.page("/assembly")
def assembly_station():
    setup_theme(dark=True)

    def start_cycle():
        ui.notify("Connect your station's cycle handler here")

    elements = render_screen(screen, actions={"start_cycle": start_cycle})
    # Stable component IDs map to actual NiceGUI/Prospero objects.
    # For example: elements[input_id].value or elements[table_id].set_rows(...).
```

Set a button's **Action** property to `start_cycle` in the editor to connect the
callback above. Only callbacks explicitly supplied by station code can run;
buttons with empty or unknown action names are disabled. Destructive buttons keep
Prospero's confirmation dialog. The editor never connects preview buttons to MES
operations. Table columns use field keys `c0`, `c1`, etc.; populate their rows from
station code, for example `{"id": "row-1", "c0": "SN-001", "c1": "PASS"}`.

## Scope and compatibility

- Earlier version-1 screen JSON files still load. New appearance and design fields
  receive defaults when absent.
- JSON validation rejects unsupported components and arbitrary style properties,
  duplicate IDs, children on leaf components, and invalid layout values. Documents
  are limited to 256 KB, 200 components, and 16 nested levels.
- Database bindings, live production data, validation workflows, and MES actions
  remain Python station responsibilities. Preview does not simulate those services.
- The launcher binds to localhost by default. There is no shared editing server,
  user management, audit history, or publishing workflow in this editor.
- Existing Python screens are not automatically converted into editable documents.

## Verification

Use the project's pinned tools:

```bash
python -m pip install --constraint requirements.txt ruff
ARIEL_DEV_MODE=1 python -m pytest
ruff check .
```

`ARIEL_DEV_MODE=1` tests against Ariel's Python encryption source. The existing CI
workflow separately compiles that module for its production check.

The optional browser checks require Playwright and a running editor:

```bash
python -m pip install playwright
python -m playwright install chromium
```

Playwright is only a development dependency. The browser quality checks measure
rendered component geometry in edit and preview modes and exercise editing,
keyboard commands, persistence, and recovery.
