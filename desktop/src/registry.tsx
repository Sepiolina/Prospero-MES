import type { ReactNode } from "react";
import { confirmAction } from "./files";
import type { Widget } from "./model";
export type Runtime = {
  scan: string;
  setScan: (value: string) => void;
  run: () => void;
  result: string;
  preview: boolean;
};
export const registry: Record<
  Widget["kind"],
  {
    name: string;
    defaults: { disabled: boolean; confirm: boolean };
    properties: readonly ("disabled" | "confirm")[];
    render: (widget: Widget, runtime: Runtime) => ReactNode;
  }
> = {
  heading: {
    name: "Heading",
    defaults: { disabled: false, confirm: false },
    properties: [],
    render: (w) => <h2>{w.label}</h2>,
  },
  instruction: {
    name: "Instruction",
    defaults: { disabled: false, confirm: false },
    properties: [],
    render: (w) => <p className="instruction">{w.label}</p>,
  },
  scan: {
    name: "Scan input",
    defaults: { disabled: false, confirm: false },
    properties: ["disabled"],
    render: (w, r) => (
      <label>
        {w.label}
        <input
          aria-label={w.label}
          placeholder="Scan or type PART-001"
          disabled={w.disabled || r.preview}
          value={r.scan}
          onChange={(e) => r.setScan(e.target.value)}
        />
      </label>
    ),
  },
  button: {
    name: "Action button",
    defaults: { disabled: false, confirm: false },
    properties: ["disabled", "confirm"],
    render: (w, r) => (
      <button
        className={w.confirm ? "danger" : "primary"}
        disabled={w.disabled || r.preview}
        onClick={async () => {
          if (!w.confirm || (await confirmAction(`Confirm “${w.label}”?`)))
            r.run();
        }}
      >
        {w.label}
      </button>
    ),
  },
  status: {
    name: "Status",
    defaults: { disabled: false, confirm: false },
    properties: [],
    render: (w, r) => (
      <div className="status" role="status">
        <span aria-hidden="true">{r.result ? "●" : "○"}</span>{" "}
        {r.result || w.label}
      </div>
    ),
  },
};
export function StationView({
  components,
  runtime,
}: {
  components: Widget[];
  runtime: Runtime;
}) {
  return (
    <div className="station-view">
      {components.map((w) => (
        <div key={w.id} className="station-widget">
          {registry[w.kind].render(w, runtime)}
        </div>
      ))}
    </div>
  );
}
