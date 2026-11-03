import { isTauri } from "@tauri-apps/api/core";
import { confirm, open, save } from "@tauri-apps/plugin-dialog";
import { readTextFile, writeTextFile } from "@tauri-apps/plugin-fs";
export async function confirmAction(message: string): Promise<boolean> {
  return isTauri()
    ? confirm(message, { title: "Prospero Station Studio", kind: "warning" })
    : window.confirm(message);
}
export async function openStationFile(): Promise<string | null> {
  const path = await open({
    multiple: false,
    filters: [{ name: "Station JSON", extensions: ["json"] }],
  });
  if (!path) return null;
  const text = await readTextFile(path);
  if (new TextEncoder().encode(text).length > 1_000_000)
    throw new Error("Station files must be smaller than 1 MB.");
  return text;
}
export async function saveStationFile(text: string): Promise<boolean> {
  if (isTauri()) {
    const path = await save({
      defaultPath: "station.v1.json",
      filters: [{ name: "Station JSON", extensions: ["json"] }],
    });
    if (!path) return false;
    await writeTextFile(path, text);
  } else {
    const url = URL.createObjectURL(
      new Blob([text], { type: "application/json" }),
    );
    const link = document.createElement("a");
    link.href = url;
    link.download = "station.v1.json";
    link.click();
    setTimeout(() => URL.revokeObjectURL(url), 1000);
  }
  return true;
}
export { isTauri };
