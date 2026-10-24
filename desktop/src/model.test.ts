import { describe, expect, it } from "vitest";
import {
  example,
  parseStation,
  serializeStation,
  simulate,
  type Station,
} from "./model";
const copy = () => structuredClone(example);
describe("versioned station document", () => {
  it("round trips the complete design without losing workflow positions or properties", () => {
    const s = copy();
    s.components[3].confirm = true;
    s.workflow.nodes[1].position.x = 777;
    expect(parseStation(serializeStation(s))).toEqual(s);
  });
  it.each([
    "not json",
    "null",
    "{}",
    JSON.stringify({ ...example, schemaVersion: 2 }),
    JSON.stringify({ ...example, unknown: true }),
  ])("rejects invalid or unsupported input: %s", (text) =>
    expect(() => parseStation(text)).toThrow(),
  );
  it("rejects unknown components and duplicate IDs", () => {
    const s = copy();
    s.components[1].id = s.components[0].id;
    expect(() => serializeStation(s)).toThrow(/Duplicate component/);
    (s.components[0] as { kind: string }).kind = "html";
    expect(() => serializeStation(s)).toThrow();
  });
  it("rejects dangling edges, missing branches and duplicate branch connections", () => {
    let s = copy();
    s.workflow.edges[0].target = "missing";
    expect(() => serializeStation(s)).toThrow(/missing node/);
    s = copy();
    s.workflow.edges.pop();
    expect(() => serializeStation(s)).toThrow(/pass and fail/);
    s = copy();
    s.workflow.edges.push({ ...s.workflow.edges[1], id: "duplicate-branch" });
    expect(() => serializeStation(s)).toThrow(/pass and fail/);
  });
  it("rejects cycles and unreachable nodes", () => {
    const s = copy();
    s.workflow.edges[1].target = "check";
    expect(() => serializeStation(s)).toThrow(/cycles/);
    const disconnected = copy();
    disconnected.workflow.nodes.push({
      id: "orphan",
      kind: "result",
      label: "Unused",
      value: "",
      position: { x: 0, y: 0 },
    });
    expect(() => serializeStation(disconnected)).toThrow(/reachable/);
  });
  it("requires exactly one scan entry and bounded document size", () => {
    const s = copy();
    s.workflow.nodes[0].kind = "result";
    expect(() => serializeStation(s)).toThrow(/exactly one/);
    expect(() =>
      parseStation(
        JSON.stringify({
          ...example,
          components: Array.from({ length: 31 }, (_, i) => ({
            ...example.components[0],
            id: String(i),
          })),
        }),
      ),
    ).toThrow();
  });
});
describe("deterministic workflow simulation", () => {
  it("follows the pass path for the exact expected scan", () =>
    expect(simulate(example, "PART-001")).toEqual({
      trace: ["scan", "check", "pass"],
      result: "PASS · Part accepted",
    }));
  it.each(["PART-002", "part-001", " PART-001"])(
    "follows the fail path for %s",
    (scan) =>
      expect(simulate(example, scan)).toEqual({
        trace: ["scan", "check", "fail"],
        result: "FAIL · Incorrect part",
      }),
  );
  it("honors edited decisions and supports chained decisions", () => {
    const s = copy();
    s.workflow.nodes[1].value = "NEW";
    s.workflow.nodes.push({
      id: "check2",
      kind: "decision",
      label: "Second check",
      value: "NEW",
      position: { x: 0, y: 0 },
    });
    s.workflow.edges[1].target = "check2";
    s.workflow.edges.push(
      { id: "2-pass", source: "check2", target: "pass", branch: "pass" },
      { id: "2-fail", source: "check2", target: "fail", branch: "fail" },
    );
    expect(simulate(s, "NEW").trace).toEqual([
      "scan",
      "check",
      "check2",
      "pass",
    ]);
    expect(simulate(s, "PART-001").result).toContain("FAIL");
  });
  it("rejects empty scans and invalid graphs before execution", () => {
    expect(() => simulate(example, "  ")).toThrow(/Enter a scan/);
    const s: Station = copy();
    s.workflow.edges = [];
    expect(() => simulate(s, "PART-001")).toThrow();
  });
});
