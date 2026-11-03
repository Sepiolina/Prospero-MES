import { beforeEach, describe, expect, it, vi } from "vitest";
const native = vi.hoisted(() => ({
  enabled: true,
  confirm: vi.fn(),
  open: vi.fn(),
  save: vi.fn(),
  read: vi.fn(),
  write: vi.fn(),
}));
vi.mock("@tauri-apps/api/core", () => ({ isTauri: () => native.enabled }));
vi.mock("@tauri-apps/plugin-dialog", () => ({
  confirm: native.confirm,
  open: native.open,
  save: native.save,
}));
vi.mock("@tauri-apps/plugin-fs", () => ({
  readTextFile: native.read,
  writeTextFile: native.write,
}));
import { confirmAction, openStationFile, saveStationFile } from "./files";
beforeEach(() => {
  vi.clearAllMocks();
  native.enabled = true;
});
describe("native file boundary", () => {
  it("reads only the selected file and handles cancellation", async () => {
    native.open.mockResolvedValue(null);
    expect(await openStationFile()).toBeNull();
    expect(native.read).not.toHaveBeenCalled();
    native.open.mockResolvedValue("/selected/station.json");
    native.read.mockResolvedValue("{}");
    expect(await openStationFile()).toBe("{}");
    expect(native.read).toHaveBeenCalledWith("/selected/station.json");
  });
  it("writes only after a save selection", async () => {
    native.save.mockResolvedValue(null);
    expect(await saveStationFile("{}")).toBe(false);
    expect(native.write).not.toHaveBeenCalled();
    native.save.mockResolvedValue("/selected/new.json");
    expect(await saveStationFile("{}")).toBe(true);
    expect(native.write).toHaveBeenCalledWith("/selected/new.json", "{}");
  });
  it("uses native confirmation and propagates denied confirmation", async () => {
    native.confirm.mockResolvedValue(false);
    expect(await confirmAction("Replace?")).toBe(false);
    expect(native.confirm).toHaveBeenCalledWith(
      "Replace?",
      expect.objectContaining({ kind: "warning" }),
    );
  });
  it("rejects oversized native files", async () => {
    native.open.mockResolvedValue("/selected/large.json");
    native.read.mockResolvedValue("a".repeat(1_000_001));
    await expect(openStationFile()).rejects.toThrow(/1 MB/);
  });
  it("propagates native filesystem failures", async () => {
    native.save.mockResolvedValue("/selected/new.json");
    native.write.mockRejectedValue(new Error("Denied"));
    await expect(saveStationFile("{}")).rejects.toThrow("Denied");
  });
});
