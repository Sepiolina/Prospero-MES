"""Optional browser regression check; requires Playwright and a running editor."""

import argparse
import asyncio
import json
from pathlib import Path

from playwright.async_api import async_playwright, expect


async def main(url, browser_path, artifacts):
    artifacts.mkdir(parents=True, exist_ok=True)
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            executable_path=browser_path, headless=True, args=["--no-sandbox"]
        )
        context = await browser.new_context(viewport={"width": 1600, "height": 1100})
        page = await context.new_page()
        errors = []
        page.on("pageerror", lambda e: errors.append(str(e)))
        await page.goto(url)
        await expect(page.get_by_text("10 components", exact=True)).to_be_visible()
        await page.locator(".builder-palette-item").filter(has_text="Text").click()
        await expect(page.get_by_text("11 components", exact=True)).to_be_visible()
        inspector = page.locator(".builder-inspector")
        await inspector.get_by_label("Component name", exact=True).fill("Station note")
        await inspector.get_by_label("Text", exact=True).fill("Safety check complete")
        await inspector.get_by_role("button", name="Apply properties").click()
        await expect(
            page.locator(".builder-canvas").get_by_text(
                "Safety check complete", exact=True
            )
        ).to_be_visible()
        note_id = await page.locator(".builder-node.is-selected").get_attribute(
            "data-node-id"
        )
        await page.get_by_role("button", name="Undo", exact=True).click()
        await expect(
            page.locator(".builder-canvas").get_by_text(
                "Safety check complete", exact=True
            )
        ).to_have_count(0)
        await page.get_by_role("button", name="Redo", exact=True).click()
        await expect(
            page.locator(".builder-canvas").get_by_text(
                "Safety check complete", exact=True
            )
        ).to_be_visible()
        await page.locator(".builder-palette-item").filter(has_text="Row").click()
        await expect(page.get_by_text("12 components", exact=True)).to_be_visible()
        row_id = await page.locator(".builder-node.is-selected").get_attribute(
            "data-node-id"
        )
        await inspector.get_by_label("Component name", exact=True).fill("Actions row")
        await inspector.get_by_role("button", name="Apply properties").click()
        await expect(
            page.locator(f'[data-node-id="{row_id}"] > .builder-node-label')
        ).to_contain_text("Actions row")
        target = page.locator(
            f'[data-node-id="{row_id}"] > .builder-layout > .builder-dropzone'
        )
        await target.evaluate('(e) => e.scrollIntoView({block: "center"})')
        await (
            page.locator(".builder-palette-item")
            .filter(has_text="Button")
            .drag_to(target)
        )
        await expect(page.get_by_text("13 components", exact=True)).to_be_visible()
        await expect(
            page.locator(f'[data-node-id="{row_id}"] .builder-node')
        ).to_have_count(1)
        await target.evaluate('(e) => e.scrollIntoView({block: "center"})')
        await page.locator(f'[data-node-id="{note_id}"] > .builder-node-label').drag_to(
            target
        )
        await expect(
            page.locator(f'[data-node-id="{row_id}"] [data-node-id="{note_id}"]')
        ).to_have_count(1)
        await page.get_by_role("button", name="Duplicate component", exact=True).click()
        await expect(page.get_by_text("14 components", exact=True)).to_be_visible()
        await page.get_by_role("button", name="Delete component", exact=True).click()
        await expect(page.get_by_text("13 components", exact=True)).to_be_visible()
        async with page.expect_download() as info:
            await page.get_by_role("button", name="Export JSON").click()
        download = await info.value
        await download.save_as(artifacts / "browser-export.json")
        data = json.loads(Path(artifacts / "browser-export.json").read_text())
        row = next(n for n in data["root"]["children"] if n["id"] == row_id)
        assert [n["kind"] for n in row["children"]] == ["button", "text"]
        await page.get_by_role("button", name="Save draft").click()
        await expect(
            page.locator(".builder-header").get_by_text(
                "Draft saved in this browser", exact=True
            )
        ).to_be_visible()
        await page.reload()
        await expect(page.get_by_text("13 components", exact=True)).to_be_visible()
        await expect(
            page.locator(f'[data-node-id="{row_id}"] [data-node-id="{note_id}"]')
        ).to_have_count(1)
        await page.get_by_role("button", name="Preview", exact=True).click()
        await (
            page.locator(".builder-canvas")
            .get_by_label("Serial number", exact=True)
            .fill("SN-001")
        )
        assert (
            await page.locator(".builder-canvas")
            .get_by_label("Serial number", exact=True)
            .input_value()
            == "SN-001"
        )
        assert await page.locator(".builder-canvas button:disabled").count() == 2
        await page.screenshot(path=artifacts / "editor-preview.png", full_page=True)
        await page.get_by_role("button", name="Edit", exact=True).click()
        await page.get_by_role("button", name="Screen menu", exact=True).click()
        await page.get_by_text("New blank screen", exact=True).click()
        await page.get_by_role("button", name="Open screen", exact=True).click()
        await expect(page.get_by_text("1 component", exact=True)).to_be_visible()
        await page.get_by_role("button", name="Screen menu", exact=True).click()
        await page.get_by_text("Import JSON", exact=True).click()
        await page.locator('input[type="file"]').set_input_files(
            artifacts / "browser-export.json"
        )
        await page.get_by_role("button", name="Open screen", exact=True).click()
        await expect(page.get_by_text("13 components", exact=True)).to_be_visible()
        await page.get_by_role("button", name="Screen menu", exact=True).click()
        await page.get_by_text("Import JSON", exact=True).click()
        await page.locator('input[type="file"]').set_input_files(
            {
                "name": "invalid.json",
                "mimeType": "application/json",
                "buffer": b'{"version":2}',
            }
        )
        await expect(
            page.get_by_text("Invalid screen file:", exact=False)
        ).to_be_visible()
        await expect(page.get_by_text("13 components", exact=True)).to_be_visible()
        await page.get_by_role("button", name="Cancel", exact=True).click()
        await page.screenshot(path=artifacts / "editor-verified.png", full_page=True)
        fresh = await browser.new_context()
        other = await fresh.new_page()
        await other.goto(url)
        await expect(other.get_by_text("10 components", exact=True)).to_be_visible()
        assert not errors, errors
        print(
            "PASS: click-add, properties, undo/redo, native palette drag, nested move, duplicate/delete, JSON export/import, local save/reload, interactive preview, client isolation; no browser errors."
        )
        await browser.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--url", default="http://127.0.0.1:8081")
    parser.add_argument(
        "--browser", default=None, help="Optional Chromium executable path"
    )
    parser.add_argument("--artifacts", type=Path, default=Path("work/builder-browser"))
    args = parser.parse_args()
    asyncio.run(main(args.url, args.browser, args.artifacts))
