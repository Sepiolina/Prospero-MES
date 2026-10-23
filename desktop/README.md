# Prospero Station Studio — migration milestone 1

A standalone React + TypeScript station editor hosted by a minimal Tauri 2 shell. The Python/NiceGUI application and Ariel storage remain available unchanged. This milestone does not call Python, launch a sidecar, access equipment, or run a production station.

## Run and test

Use Node 22.12+ (Node 24 recommended), npm, and a supported browser:

```sh
cd desktop
npm ci
npm run dev
npm test
npm run build
npx playwright install chromium
npm run test:e2e
```

Open http://127.0.0.1:1420. For the native window, install stable Rust and the [Tauri platform prerequisites](https://v2.tauri.app/start/prerequisites/), then run `npm run tauri dev`. On Debian/Ubuntu, prerequisites include `libwebkit2gtk-4.1-dev`, `build-essential`, `curl`, `wget`, `file`, `libxdo-dev`, `libssl-dev`, `librsvg2-dev`, and `libayatana-appindicator3-dev`. `npm run tauri build -- --no-bundle` compiles the desktop application. Installer bundling is intentionally disabled until platform packaging/signing is configured.

The onboarding environment can test/build the browser frontend. Native compilation requires GTK/WebKit development packages unavailable in that environment; the included Linux CI job checks the shell with those packages installed. Native release behavior and installers still require platform verification.

## Try the milestone

1. In **Station layout**, add a component, select its frame, edit the label, and move it up/down. Scan inputs can be disabled; action buttons also support confirmation. Removing a component asks for confirmation.
2. In **Workflow**, drag nodes and edit labels, expected scan, and result messages. Add decision/result nodes and connect their handles. Choose the branch before connecting: scan nodes need one `next`; decisions need one `pass` and one `fail`. Select an edge/node and press Delete to remove it. Every node must be reachable; result nodes must be terminal; cycles are rejected. The single scan entry cannot be deleted.
3. In **Operator preview**, scan/type `PART-001`, then press **Verify part**. Try another barcode for the rejection path. The console's **Run workflow** independently exercises the graph, even if the visual station action is disabled. Enter in the scan field does not submit. The trace lists exactly which nodes executed.
4. **Export JSON** validates and downloads a version 1 document. **Import JSON** validates before replacing the station and asks for confirmation. Invalid imports preserve the current design. Work remains in memory until exported; closing/reloading discards edits.

The example is defined in `src/model.ts`. Both canvas and operator views render the same registry in `src/registry.tsx`; registry entries define component names, defaults and editable flags. `src/tokens.ts` mirrors Python theme values, including 48 px targets, 24 px bezel clearance, visible keyboard focus, disabled controls and static textual status. Theme synchronization across languages is currently manual. The constrained layout is an ordered vertical stack, not arbitrary pixel placement. Components are heading, instruction, scan input, action button and status; table, select, PDF, scroll, modal and loading parity remains future work. UI labels are rendered as text, never HTML.

## Contract and execution limits

`src/model.ts` owns the strict Zod schema and serializer. Imports reject unsupported versions/unknown fields, duplicate IDs, dangling edges, invalid branches, unreachable nodes and cycles. Documents are bounded to 30 components, 50 nodes, 100 edges and a 1 MB import file. Export and simulation revalidate edits, so incomplete graphs can be edited but cannot execute or export. Simulation compares the original scan string exactly and follows a single branch per step; it is synchronous, deterministic and side-effect free. It has no code evaluation, arbitrary expressions, retries, timers, I/O or durable execution. All buttons in the operator station invoke that same workflow; separate event-to-workflow bindings are future work.

JSON is a local frontend document, not an Ariel database migration. Native import/export use Tauri dialog and filesystem plugins, with access granted only for paths selected in the native dialogs. The browser preview uses file input/download APIs. Native confirmation uses the dialog plugin; browser preview uses window.confirm. No shell plugins or custom backend IPC commands are enabled. CSP forbids remote production resources and object/frame embedding. Native file dialogs and packaging still require verification on each target platform.

Tests cover round-trip persistence, malformed/unsupported imports, graph invariants, deterministic pass/fail execution, exact matching, chained decisions and invalid execution. Browser regression tests cover visible graph nodes/edges, edge deletion, pass/fail simulation, trace retention and disabled action behavior. Native I/O unit tests mock the selected-path dialog/filesystem boundary. CI also builds the frontend and checks the native shell. No hardware behavior is claimed by these tests.

## Next migration milestones

1. Define a typed, versioned IPC boundary and Python sidecar lifecycle; integrate Ariel with explicit ownership of transactions, errors, credentials and database migrations.
2. Port remaining component behavior and accessibility; add event bindings, richer validated layouts, focus/scanner routing, live data and theme parity.
3. Design durable production execution with validated hardware adapters, interlocks, timeouts, cancellation, retries, recovery and audit records; prove it against equipment simulators before hardware rollout.
4. Verify Windows/Linux/macOS webviews, configure installer assets/signing/upgrades, and run deployment and operator acceptance tests. Existing NiceGUI stations need explicit migration tooling and parity review before retirement.
