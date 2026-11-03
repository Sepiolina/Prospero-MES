# Prospero Screen Studio

Build station screens visually with Prospero's existing NiceGUI components.

## Start the editor

From the repository root, using the project's Python environment:

```bash
python -m prospero.builder
```

Open **http://127.0.0.1:8081**. Use `--port 8082` to choose another port.
An importable example is included at `examples/screens/operator-station.json`.
The editor has a separate launcher because `main.py` depends on a station module
that is not included in this repository. It uses the same Prospero theme and
component library; there is no frontend build step or additional runtime dependency.

## Build a screen

1. Start with the operator station template, or use the screen menu to open a blank screen.
2. Drag a row, column, grid, or card from the palette onto a container's drop area.
3. Drop text, inputs, selectors, buttons, and tables into those layouts.
   Clicking a palette item also adds it inside the selected container, or next to
   the selected leaf component. The screen tree selects nested components.
4. Edit properties on the right and click **Apply properties** before changing
   selection. Layouts control gap, padding, alignment, and grid column count.
5. Drag existing components between containers, or onto the top edge of a component
   to insert before it. The inspector also has move, duplicate, and delete controls.
6. Use **Preview** to interact with inputs and inspect the screen at desktop,
   tablet, or phone widths. Button actions are disabled in the editor.
7. **Save draft** keeps one screen in this browser's local storage and restores it
   after a reload. Each tab edits its own document; the last explicit save wins
   for the shared browser draft. Use **Export JSON** to keep multiple screens,
   share them, or check them into Git. Import JSON through the screen menu.

Undo and redo cover document edits, including opening another screen. History
holds the last 50 edits and is not persisted. Export and save include applied
properties; unfinished property fields must be applied first.

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
    # elements maps stable component IDs to the actual NiceGUI/Prospero objects.
    # For example: elements[input_id].value, or elements[table_id].set_rows(...).
```

Set a button's **Action** property to `start_cycle` in the editor to connect the
callback above. Only callbacks explicitly supplied by station code can run;
buttons with empty or unknown action names are disabled. Destructive buttons keep
Prospero's confirmation dialog. The editor never connects preview buttons to MES
operations. Table columns use field keys `c0`, `c1`, etc.; populate their rows from
your station code, for example `{"id": "row-1", "c0": "SN-001", "c1": "PASS"}`.

## Scope of this version

- Nine component types, nested layouts, editable properties, and one starter template.
- Layouts use flow positioning, with wrapping rows and explicit grid columns.
  Width previews help inspect layouts; there are no per-breakpoint overrides yet.
- Forms, tables, and events connect to Python through the returned element handles
  and named callbacks. Database bindings, live production data, and workflow logic
  are implemented in station code.
- JSON validation rejects unsupported component types, arbitrary properties,
  duplicate IDs, children on leaf components, and invalid layout values. Documents
  are limited to 256 KB, 200 components, and 16 nested levels.
- The launcher binds to localhost by default. It is an authoring tool; there is
  no user management, shared draft service, or publishing workflow.
- Existing Python screens are not automatically converted into editable documents.

## Verification

```bash
ARIEL_DEV_MODE=1 python -m pytest
ruff check .
```

`ARIEL_DEV_MODE=1` is for testing against Ariel's Python encryption source. The
existing CI workflow separately compiles that module for its production check.

For the optional browser regression check, start the editor in a separate terminal:

```bash
python -m pip install playwright
python -m playwright install chromium
python tests/browser_builder.py
```

Use `--url http://127.0.0.1:8082` for a different port and `--browser /path/to/chromium`
to use an installed Chromium. Screenshots and the exported test screen are saved
under `work/builder-browser/`. This checks native dragging, properties, undo/redo,
copy/delete, JSON import/export, malformed imports, draft persistence, preview,
and client isolation. Playwright is only a development dependency.
