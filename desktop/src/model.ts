import { z } from "zod";
const id = z.string().min(1).max(100);
export const componentKinds = [
  "heading",
  "instruction",
  "scan",
  "button",
  "status",
] as const;
export const widgetSchema = z
  .object({
    id,
    kind: z.enum(componentKinds),
    label: z.string().min(1).max(200),
    disabled: z.boolean(),
    confirm: z.boolean(),
  })
  .strict();
const nodeSchema = z
  .object({
    id,
    kind: z.enum(["scan", "decision", "result"]),
    label: z.string().min(1).max(100),
    position: z
      .object({ x: z.number().finite(), y: z.number().finite() })
      .strict(),
    value: z.string().max(200),
  })
  .strict();
const edgeSchema = z
  .object({
    id,
    source: id,
    target: id,
    branch: z.enum(["next", "pass", "fail"]),
  })
  .strict();
export const stationSchema = z
  .object({
    schemaVersion: z.literal(1),
    name: z.string().min(1).max(100),
    layout: z.literal("stack"),
    components: z.array(widgetSchema).min(1).max(30),
    workflow: z
      .object({
        nodes: z.array(nodeSchema).min(1).max(50),
        edges: z.array(edgeSchema).max(100),
      })
      .strict(),
  })
  .strict()
  .superRefine((s, ctx) => {
    const issue = (message: string) =>
      ctx.addIssue({ code: "custom", message });
    for (const [label, items] of [
      ["component", s.components],
      ["node", s.workflow.nodes],
      ["edge", s.workflow.edges],
    ] as const) {
      if (new Set(items.map((x) => x.id)).size !== items.length)
        issue(`Duplicate ${label} IDs`);
    }
    const nodes = new Map(s.workflow.nodes.map((n) => [n.id, n]));
    if (s.workflow.nodes.filter((n) => n.kind === "scan").length !== 1)
      issue("Workflow requires exactly one scan entry");
    for (const e of s.workflow.edges) {
      if (!nodes.has(e.source) || !nodes.has(e.target))
        issue(`Edge ${e.id} references a missing node`);
      if (e.source === e.target) issue("Self loops are not supported");
    }
    for (const n of s.workflow.nodes) {
      const outgoing = s.workflow.edges.filter((e) => e.source === n.id);
      const branches = outgoing
        .map((e) => e.branch)
        .sort()
        .join(",");
      if (n.kind === "scan" && branches !== "next")
        issue(`Scan ${n.id} needs one next edge`);
      if (n.kind === "decision" && branches !== "fail,pass")
        issue(`Decision ${n.id} needs pass and fail edges`);
      if (n.kind === "result" && outgoing.length)
        issue(`Result ${n.id} must be terminal`);
    }
    const visited = new Set<string>();
    const active = new Set<string>();
    const visit = (key: string) => {
      if (active.has(key)) {
        issue("Workflow cycles are not supported");
        return;
      }
      if (visited.has(key)) return;
      visited.add(key);
      active.add(key);
      for (const e of s.workflow.edges.filter((e) => e.source === key))
        visit(e.target);
      active.delete(key);
    };
    const entry = s.workflow.nodes.find((n) => n.kind === "scan");
    if (entry) visit(entry.id);
    if (visited.size !== nodes.size)
      issue("Every node must be reachable from the scan entry");
  });
export type Station = z.infer<typeof stationSchema>;
export type Widget = z.infer<typeof widgetSchema>;
export type WorkflowNode = Station["workflow"]["nodes"][number];
export function parseStation(text: string): Station {
  return stationSchema.parse(JSON.parse(text));
}
export function serializeStation(station: Station): string {
  return JSON.stringify(stationSchema.parse(station), null, 2);
}
export function simulate(
  station: Station,
  scan: string,
): { trace: string[]; result: string } {
  const valid = stationSchema.parse(station);
  if (!scan.trim()) throw new Error("Enter a scan value before running.");
  const trace: string[] = [];
  let node = valid.workflow.nodes.find((n) => n.kind === "scan")!;
  for (let step = 0; step <= valid.workflow.nodes.length; step++) {
    trace.push(node.id);
    if (node.kind === "result")
      return { trace, result: node.value || node.label };
    const branch =
      node.kind === "decision"
        ? scan === node.value
          ? "pass"
          : "fail"
        : "next";
    const edge = valid.workflow.edges.find(
      (e) => e.source === node.id && e.branch === branch,
    )!;
    node = valid.workflow.nodes.find((n) => n.id === edge.target)!;
  }
  throw new Error("Workflow did not terminate");
}
export const example: Station = {
  schemaVersion: 1,
  name: "Assembly · scan verification",
  layout: "stack",
  components: [
    {
      id: "title",
      kind: "heading",
      label: "Verify the assembly",
      disabled: false,
      confirm: false,
    },
    {
      id: "help",
      kind: "instruction",
      label: "Scan the part barcode. Expected part: PART-001.",
      disabled: false,
      confirm: false,
    },
    {
      id: "scan-input",
      kind: "scan",
      label: "Part barcode",
      disabled: false,
      confirm: false,
    },
    {
      id: "run",
      kind: "button",
      label: "Verify part",
      disabled: false,
      confirm: false,
    },
    {
      id: "feedback",
      kind: "status",
      label: "Ready for scan",
      disabled: false,
      confirm: false,
    },
  ],
  workflow: {
    nodes: [
      {
        id: "scan",
        kind: "scan",
        label: "Scan part",
        position: { x: 60, y: 100 },
        value: "",
      },
      {
        id: "check",
        kind: "decision",
        label: "Part matches?",
        position: { x: 310, y: 100 },
        value: "PART-001",
      },
      {
        id: "pass",
        kind: "result",
        label: "Accepted",
        position: { x: 570, y: 20 },
        value: "PASS · Part accepted",
      },
      {
        id: "fail",
        kind: "result",
        label: "Rejected",
        position: { x: 570, y: 200 },
        value: "FAIL · Incorrect part",
      },
    ],
    edges: [
      { id: "scan-check", source: "scan", target: "check", branch: "next" },
      { id: "check-pass", source: "check", target: "pass", branch: "pass" },
      { id: "check-fail", source: "check", target: "fail", branch: "fail" },
    ],
  },
};
