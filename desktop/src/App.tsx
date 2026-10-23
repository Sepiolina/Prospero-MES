import { useEffect, useRef, useState } from "react";
import {
  ReactFlow,
  Background,
  Controls,
  MarkerType,
  applyNodeChanges,
  type NodeChange,
  type Node,
  type Connection,
  type Edge,
  applyEdgeChanges,
} from "@xyflow/react";
import "@xyflow/react/dist/style.css";
import {
  componentKinds,
  example,
  parseStation,
  serializeStation,
  simulate,
  type Station,
  type Widget,
  type WorkflowNode,
} from "./model";
import {
  confirmAction,
  isTauri,
  openStationFile,
  saveStationFile,
} from "./files";
import { registry, StationView, type Runtime } from "./registry";
export function App() {
  const [station, setStation] = useState<Station>(() =>
    structuredClone(example),
  );
  const [tab, setTab] = useState<"layout" | "workflow" | "operator">("layout");
  const [selected, select] = useState("title");
  const [nodeId, selectNode] = useState("check");
  const [branch, setBranch] = useState<"next" | "pass" | "fail">("next");
  const [scan, setScanValue] = useState("");
  const setScan = (value: string) => {
    setScanValue(value);
    setResult("");
    setTrace([]);
  };
  const [result, setResult] = useState("");
  const [trace, setTrace] = useState<string[]>([]);
  const [message, setMessage] = useState(
    "Design locally. Export a JSON file to keep your work.",
  );
  const [selectedEdges, setSelectedEdges] = useState<string[]>([]);
  const file = useRef<HTMLInputElement>(null);
  const update = (next: Station) => {
    setStation(next);
    setResult("");
    setTrace([]);
  };
  const widget = station.components.find((w) => w.id === selected);
  const node = station.workflow.nodes.find((n) => n.id === nodeId);
  const patchWidget = (patch: Partial<Widget>) =>
    update({
      ...station,
      components: station.components.map((w) =>
        w.id === selected ? { ...w, ...patch } : w,
      ),
    });
  const patchNode = (patch: Partial<WorkflowNode>) =>
    update({
      ...station,
      workflow: {
        ...station.workflow,
        nodes: station.workflow.nodes.map((n) =>
          n.id === nodeId ? { ...n, ...patch } : n,
        ),
      },
    });
  const run = () => {
    try {
      const output = simulate(station, scan);
      setResult(output.result);
      setTrace(output.trace);
      setMessage("Simulation complete. No hardware commands were sent.");
    } catch (error) {
      setResult("");
      setTrace([]);
      setMessage(String(error));
    }
  };
  const runtime: Runtime = {
    scan,
    setScan,
    run,
    result,
    preview: tab !== "operator",
  };
  const move = (offset: number) => {
    const components = [...station.components];
    const i = components.findIndex((w) => w.id === selected);
    const target = i + offset;
    if (target < 0 || target >= components.length) return;
    [components[i], components[target]] = [components[target], components[i]];
    update({ ...station, components });
  };
  const save = async () => {
    try {
      if (await saveStationFile(serializeStation(station)))
        setMessage("Validated station exported.");
    } catch (error) {
      setMessage(`Export blocked: ${String(error)}`);
    }
  };
  const importText = async (text: string) => {
    const next = parseStation(text);
    if (
      !(await confirmAction(
        "Replace this station with the imported file? Unsaved edits will be lost.",
      ))
    )
      return;
    update(next);
    select(next.components[0].id);
    selectNode(next.workflow.nodes[0].id);
    setMessage("Imported and validated station version 1.");
  };
  const load = async (f: File) => {
    try {
      if (f.size > 1_000_000)
        throw new Error("Station files must be smaller than 1 MB.");
      await importText(await f.text());
    } catch (error) {
      setMessage(`Import rejected; current station retained. ${String(error)}`);
    }
  };
  const chooseImport = async () => {
    if (!isTauri()) {
      file.current?.click();
      return;
    }
    try {
      const text = await openStationFile();
      if (text !== null) await importText(text);
    } catch (error) {
      setMessage(`Import rejected; current station retained. ${String(error)}`);
    }
  };
  const [flowNodes, setFlowNodes] = useState<Node[]>([]);
  useEffect(() => {
    setFlowNodes((previous) =>
      station.workflow.nodes.map((n) => ({
        ...previous.find((p) => p.id === n.id),
        id: n.id,
        deletable: n.kind !== "scan",
        position: n.position,
        data: {
          label: `${n.kind.toUpperCase()} · ${n.label}${n.kind === "decision" ? `\nEquals: ${n.value}` : ""}`,
        },
        className: trace.includes(n.id) ? "visited" : "",
        selected: n.id === nodeId,
      })),
    );
  }, [station.workflow.nodes, nodeId, trace]);
  const onNodesChange = (changes: NodeChange[]) => {
    setFlowNodes((previous) => applyNodeChanges(changes, previous));
    const mutations = changes.filter(
      (c) => c.type === "position" || c.type === "remove",
    );
    if (!mutations.length) return;
    const updated = applyNodeChanges(mutations, flowNodes);
    update({
      ...station,
      workflow: {
        ...station.workflow,
        nodes: station.workflow.nodes
          .filter((n) => updated.some((u) => u.id === n.id))
          .map((n) => ({
            ...n,
            position: updated.find((u) => u.id === n.id)!.position,
          })),
        edges: station.workflow.edges.filter(
          (e) =>
            updated.some((n) => n.id === e.source) &&
            updated.some((n) => n.id === e.target),
        ),
      },
    });
  };
  const connect = (connection: Connection) => {
    if (!connection.source || !connection.target) return;
    update({
      ...station,
      workflow: {
        ...station.workflow,
        edges: [
          ...station.workflow.edges,
          {
            id: crypto.randomUUID(),
            source: connection.source,
            target: connection.target,
            branch,
          },
        ],
      },
    });
    setMessage(
      "Connection added. Export or simulation validates workflow structure.",
    );
  };
  return (
    <div className="app">
      <header>
        <div>
          <div className="eyebrow">PROSPERO / STATION STUDIO</div>
          <h1>Build a better station.</h1>
          <p>Desktop milestone · local design & deterministic simulation</p>
        </div>
        <div className="toolbar">
          <button onClick={() => void chooseImport()}>Import JSON</button>
          <button className="primary" onClick={save}>
            Export JSON
          </button>
          <input
            ref={file}
            type="file"
            accept=".json,application/json"
            hidden
            onChange={(e) => {
              const f = e.target.files?.[0];
              if (f) void load(f);
              e.target.value = "";
            }}
          />
        </div>
      </header>
      <div className="station-bar">
        <label>
          Station name
          <input
            value={station.name}
            maxLength={100}
            onChange={(e) => update({ ...station, name: e.target.value })}
          />
        </label>
        <span className="badge">SCHEMA v1 · STACK LAYOUT</span>
      </div>
      <nav aria-label="Studio views">
        {(["layout", "workflow", "operator"] as const).map((t) => (
          <button
            key={t}
            aria-pressed={tab === t}
            className={tab === t ? "active" : ""}
            onClick={() => setTab(t)}
          >
            {t === "layout"
              ? "01 · Station layout"
              : t === "workflow"
                ? "02 · Workflow"
                : "03 · Operator preview"}
          </button>
        ))}
      </nav>
      <div className="message" role="status">
        {message}
      </div>
      {tab === "layout" && (
        <main className="layout-grid">
          <aside className="panel">
            <h2>Components</h2>
            <p className="muted">Add to the vertical stack.</p>
            {componentKinds.map((kind) => (
              <button
                className="palette"
                key={kind}
                disabled={station.components.length >= 30}
                onClick={() => {
                  const id = crypto.randomUUID();
                  update({
                    ...station,
                    components: [
                      ...station.components,
                      {
                        id,
                        kind,
                        label: registry[kind].name,
                        ...registry[kind].defaults,
                      },
                    ],
                  });
                  select(id);
                }}
              >
                + {registry[kind].name}
              </button>
            ))}
          </aside>
          <section className="panel canvas">
            <div className="section-label">
              STATION CANVAS <span>24 px bezel clearance · 48 px targets</span>
            </div>
            <div className="component-stack">
              {station.components.map((w) => (
                <div
                  key={w.id}
                  className={`editable-widget ${selected === w.id ? "selected" : ""}`}
                >
                  <button
                    className="select-widget"
                    aria-pressed={selected === w.id}
                    onClick={() => select(w.id)}
                  >
                    Select {registry[w.kind].name}
                  </button>
                  <div className="component-content">
                    {registry[w.kind].render(w, runtime)}
                  </div>
                </div>
              ))}
            </div>
          </section>
          <aside className="panel">
            <h2>Properties</h2>
            {widget && (
              <>
                <p className="muted">{registry[widget.kind].name}</p>
                <label>
                  Label
                  <input
                    value={widget.label}
                    maxLength={200}
                    onChange={(e) => patchWidget({ label: e.target.value })}
                  />
                </label>
                {registry[widget.kind].properties.includes("disabled") && (
                  <label className="check">
                    <input
                      type="checkbox"
                      checked={widget.disabled}
                      onChange={(e) =>
                        patchWidget({ disabled: e.target.checked })
                      }
                    />
                    Disabled
                  </label>
                )}
                {registry[widget.kind].properties.includes("confirm") && (
                  <label className="check">
                    <input
                      type="checkbox"
                      checked={widget.confirm}
                      onChange={(e) =>
                        patchWidget({ confirm: e.target.checked })
                      }
                    />
                    Require confirmation
                  </label>
                )}
                <div className="row">
                  <button
                    disabled={station.components[0].id === selected}
                    onClick={() => move(-1)}
                  >
                    Move up
                  </button>
                  <button
                    disabled={station.components.at(-1)?.id === selected}
                    onClick={() => move(1)}
                  >
                    Move down
                  </button>
                </div>
                <button
                  className="danger"
                  disabled={station.components.length === 1}
                  onClick={async () => {
                    if (
                      await confirmAction(
                        `Remove “${widget.label}” from the station?`,
                      )
                    ) {
                      const components = station.components.filter(
                        (w) => w.id !== selected,
                      );
                      update({ ...station, components });
                      select(components[0].id);
                    }
                  }}
                >
                  Remove component
                </button>
              </>
            )}
          </aside>
        </main>
      )}
      {tab === "workflow" && (
        <main className="workflow-grid">
          <section className="panel flow">
            <div className="section-label">
              WORKFLOW GRAPH{" "}
              <span>
                Drag nodes · connect handles · select edges and press Delete
              </span>
            </div>
            <ReactFlow<Node, Edge>
              nodes={flowNodes}
              edges={station.workflow.edges.map((e) => ({
                ...e,
                label: e.branch,
                selected: selectedEdges.includes(e.id),
                markerEnd: { type: MarkerType.ArrowClosed },
              }))}
              onEdgesChange={(changes) => {
                const edges: Edge[] = station.workflow.edges.map((e) => ({
                  ...e,
                  selected: selectedEdges.includes(e.id),
                }));
                setSelectedEdges(
                  applyEdgeChanges(changes, edges)
                    .filter((e) => e.selected)
                    .map((e) => e.id),
                );
              }}
              onNodesChange={onNodesChange}
              onEdgesDelete={(edges) =>
                update({
                  ...station,
                  workflow: {
                    ...station.workflow,
                    edges: station.workflow.edges.filter(
                      (e) => !edges.some((d) => d.id === e.id),
                    ),
                  },
                })
              }
              onNodeClick={(_, n) => selectNode(n.id)}
              onConnect={connect}
              fitView
              minZoom={0.3}
              colorMode="dark"
              deleteKeyCode="Delete"
            >
              <Background />
              <Controls />
            </ReactFlow>
          </section>
          <aside className="panel">
            <h2>Workflow properties</h2>
            <p className="muted">
              One scan entry. Decisions compare the scan exactly. Results end
              execution.
            </p>
            <label>
              New connection branch
              <select
                value={branch}
                onChange={(e) => setBranch(e.target.value as typeof branch)}
              >
                <option>next</option>
                <option>pass</option>
                <option>fail</option>
              </select>
            </label>
            {node && (
              <>
                <label>
                  Node label
                  <input
                    value={node.label}
                    maxLength={100}
                    onChange={(e) => patchNode({ label: e.target.value })}
                  />
                </label>
                {node.kind !== "scan" && (
                  <label>
                    {node.kind === "decision"
                      ? "Expected scan (exact match)"
                      : "Result message"}
                    <input
                      value={node.value}
                      maxLength={200}
                      onChange={(e) => patchNode({ value: e.target.value })}
                    />
                  </label>
                )}
              </>
            )}
            <h3>Add node</h3>
            <div className="row">
              {(["decision", "result"] as const).map((kind) => (
                <button
                  key={kind}
                  disabled={station.workflow.nodes.length >= 50}
                  onClick={() => {
                    const id = crypto.randomUUID();
                    update({
                      ...station,
                      workflow: {
                        ...station.workflow,
                        nodes: [
                          ...station.workflow.nodes,
                          {
                            id,
                            kind,
                            label:
                              kind === "decision" ? "Check part" : "Result",
                            value: "",
                            position: { x: 200, y: 300 },
                          },
                        ],
                      },
                    });
                    selectNode(id);
                  }}
                >
                  {kind}
                </button>
              ))}
            </div>
            <p className="muted">
              Invalid or incomplete graphs cannot export or simulate. Cycles and
              disconnected nodes are rejected.
            </p>
          </aside>
        </main>
      )}
      {tab === "operator" && (
        <main className="operator-grid">
          <section className="panel">
            <div className="section-label">
              OPERATOR PREVIEW <span>{station.name}</span>
            </div>
            <StationView components={station.components} runtime={runtime} />
          </section>
          <aside className="panel">
            <h2>Simulation console</h2>
            <p className="muted">
              Local simulation only. No Python backend or equipment is
              connected.
            </p>
            <label>
              Simulated scan
              <input
                value={scan}
                onChange={(e) => setScan(e.target.value)}
                placeholder="PART-001"
              />
            </label>
            <button className="primary" onClick={run}>
              Run workflow
            </button>
            <button
              onClick={() => {
                setScan("");
                setResult("");
                setTrace([]);
              }}
            >
              Reset simulation
            </button>
            <h3>Execution trace</h3>
            {trace.length ? (
              <ol>
                {trace.map((id) => (
                  <li key={id}>
                    {station.workflow.nodes.find((n) => n.id === id)?.label}
                  </li>
                ))}
              </ol>
            ) : (
              <p className="muted">Run to see each visited step.</p>
            )}
            <output>{result}</output>
          </aside>
        </main>
      )}
      <footer>
        Prospero MES · First migration milestone · Your work stays in this
        session until exported.
      </footer>
    </div>
  );
}
