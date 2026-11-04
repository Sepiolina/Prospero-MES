"""Optional browser checks for Screen Studio's geometry and editing workflows.

Start the editor separately, then run:
    python tests/browser_studio_quality.py --url http://127.0.0.1:8083 --browser /usr/bin/chromium

The test also starts an isolated station renderer to verify exported screens.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
from pathlib import Path
import socket
import sys

from playwright.async_api import async_playwright, expect

ROOT = Path(__file__).resolve().parents[1]

# Measure screen geometry in design pixels, independent of the editor's zoom.
SNAPSHOT = """() => {
    const root = document.querySelector('.p-rendered-screen');
    const bounds = root.getBoundingClientRect();
    const scale = bounds.width / root.offsetWidth;
    return {
      width: root.offsetWidth,
      nodes: [...root.querySelectorAll('[data-screen-id]')].map(el => {
        const r = el.getBoundingClientRect(), style = getComputedStyle(el);
        return {id: el.dataset.screenId, kind: el.dataset.screenKind,
          x: (r.x - bounds.x) / scale, y: (r.y - bounds.y) / scale,
          width: r.width / scale, height: r.height / scale,
          fontSize: style.fontSize, fontFamily: style.fontFamily,
          color: style.color, background: style.backgroundColor,
          padding: style.padding, gap: style.gap, borderRadius: style.borderRadius};
      })
    };
}"""


async def settle(page):
    await page.evaluate("document.fonts.ready")
    await page.evaluate(
        "() => new Promise(resolve => requestAnimationFrame(() => requestAnimationFrame(resolve)))"
    )


async def snapshot(page):
    await settle(page)
    return await page.evaluate(SNAPSHOT)


def assert_parity(expected, actual, context):
    assert expected["width"] == actual["width"], (
        context,
        expected["width"],
        actual["width"],
    )
    assert len(expected["nodes"]) == len(actual["nodes"]), context
    actual_by_id = {n["id"]: n for n in actual["nodes"]}
    for before in expected["nodes"]:
        after = actual_by_id[before["id"]]
        for key in ("x", "y", "width", "height"):
            assert abs(before[key] - after[key]) <= 0.25, (
                context,
                before["id"],
                key,
                before[key],
                after[key],
            )
        for key in (
            "fontSize",
            "fontFamily",
            "color",
            "background",
            "padding",
            "gap",
            "borderRadius",
        ):
            assert before[key] == after[key], (
                context,
                before["id"],
                key,
                before[key],
                after[key],
            )


def available_port():
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


def serve_runtime(screen_path, port):
    sys.path.insert(0, str(ROOT))
    from nicegui import ui
    from prospero.builder import Screen
    from prospero.builder.renderer import render_screen
    from prospero.themes import setup_theme

    @ui.page("/")
    def station():
        setup_theme(dark=True)
        ui.add_css(".nicegui-content {padding: 0; gap: 0;}")
        render_screen(Screen.from_json(screen_path.read_text()))

    ui.run(host="127.0.0.1", port=port, show=False, reload=False)


async def runtime_browser(browser, exported_path, artifacts):
    port = available_port()
    log = (artifacts / "runtime.log").open("w")
    process = await asyncio.create_subprocess_exec(
        sys.executable,
        str(Path(__file__).resolve()),
        "--serve-runtime",
        "--screen",
        str(exported_path.resolve()),
        "--port",
        str(port),
        cwd=ROOT,
        stdout=log,
        stderr=asyncio.subprocess.STDOUT,
        env={**os.environ, "ARIEL_DEV_MODE": "1"},
    )
    page = await browser.new_page(viewport={"width": 1280, "height": 1800})
    try:
        for _ in range(100):
            try:
                await page.goto(f"http://127.0.0.1:{port}", timeout=1000)
                await expect(page.locator(".p-rendered-screen")).to_be_visible()
                return process, page, log
            except Exception:
                if process.returncode is not None:
                    raise RuntimeError(
                        (artifacts / "runtime.log").read_text()
                    ) from None
                await asyncio.sleep(0.1)
        raise RuntimeError("Standalone renderer did not start")
    except BaseException:
        process.terminate()
        await process.wait()
        log.close()
        raise


async def click_node(page, node_id):
    bounds = await page.locator(f'[data-screen-id="{node_id}"]').bounding_box()
    assert bounds
    await page.mouse.click(
        bounds["x"] + bounds["width"] / 2, bounds["y"] + bounds["height"] / 2
    )


async def main(args):
    artifacts = args.artifacts.resolve()
    artifacts.mkdir(parents=True, exist_ok=True)
    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch(
            executable_path=args.browser, headless=True, args=["--no-sandbox"]
        )
        context = await browser.new_context(viewport={"width": 1600, "height": 1100})
        page = await context.new_page()
        errors = []
        page.on("pageerror", lambda error: errors.append(str(error)))
        page.on("dialog", lambda dialog: dialog.accept())
        await page.goto(args.url)
        await expect(page.locator(".studio-hit-layer")).to_be_visible()
        await expect(page.get_by_text("Unsaved changes", exact=True)).to_be_visible()
        await page.wait_for_timeout(300)
        title_id = await page.locator(
            '[data-screen-name="Station title"]'
        ).get_attribute("data-screen-id")
        await click_node(page, title_id)
        field = page.get_by_label("Text", exact=True)
        await expect(field).to_be_visible()
        await field.fill("Assembly station")
        await expect(page.locator(f'[data-screen-id="{title_id}"]')).to_have_text(
            "Assembly station"
        )
        await click_node(page, title_id)
        await page.keyboard.press("Control+z")
        await expect(page.locator(f'[data-screen-id="{title_id}"]')).to_have_text(
            "Production station"
        )
        await page.keyboard.press("Control+Shift+z")
        await expect(page.locator(f'[data-screen-id="{title_id}"]')).to_have_text(
            "Assembly station"
        )
        await page.keyboard.press("Control+s")
        await page.wait_for_function(
            "() => (localStorage.getItem('prospero.screen-builder.v1') || '').includes('Assembly station')"
        )

        async with page.expect_download() as exported:
            await page.get_by_role("button", name="Export JSON", exact=True).click()
        file = await exported.value
        screen_path = artifacts / "exported-screen.json"
        await file.save_as(screen_path)
        assert json.loads(screen_path.read_text())["version"] == 1
        process, runtime, log = await runtime_browser(browser, screen_path, artifacts)
        try:
            for width in (1280, 768, 390):
                viewport = page.get_by_label("Viewport width", exact=True)
                await viewport.fill(str(width))
                await viewport.press("Tab")
                await page.wait_for_function(
                    '(width) => document.querySelector(".p-rendered-screen").offsetWidth === width',
                    arg=width,
                )
                design = await snapshot(page)
                await page.get_by_role("button", name="Preview", exact=True).click()
                await expect(page.locator(".studio-hit-layer")).to_have_count(0)
                preview = await snapshot(page)
                assert_parity(design, preview, f"edit/preview at {width}")
                await runtime.set_viewport_size({"width": width, "height": 1800})
                rendered = await snapshot(runtime)
                assert_parity(design, rendered, f"edit/runtime at {width}")
                await page.get_by_role(
                    "button", name="Back to design", exact=True
                ).click()
                await expect(page.locator(".studio-hit-layer")).to_be_visible()

            await click_node(page, title_id)
            await field.fill("Recovered unsaved heading")
            await expect(page.locator(f'[data-screen-id="{title_id}"]')).to_have_text(
                "Recovered unsaved heading"
            )
            await page.wait_for_function(
                "() => Object.values(sessionStorage).some(value => value.includes('Recovered unsaved heading'))"
            )
            await page.reload()
            await expect(page.locator(f'[data-screen-id="{title_id}"]')).to_have_text(
                "Recovered unsaved heading"
            )
            assert not errors, errors
            await page.screenshot(path=artifacts / "studio.png", full_page=True)
            print(
                "PASS: live text editing, grouped undo/redo, save shortcut, JSON export, unsaved recovery, and geometry/style parity across design, preview, and standalone runtime at 1280/768/390px; no browser errors."
            )
        finally:
            process.terminate()
            await process.wait()
            log.close()
            await browser.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--url", default="http://127.0.0.1:8083")
    parser.add_argument("--browser", default=None)
    parser.add_argument(
        "--artifacts", type=Path, default=Path("work/studio-quality-browser")
    )
    parser.add_argument("--serve-runtime", action="store_true")
    parser.add_argument("--screen", type=Path)
    parser.add_argument("--port", type=int, default=8090)
    args = parser.parse_args()
    if args.serve_runtime:
        serve_runtime(args.screen, args.port)
    else:
        asyncio.run(main(args))
