"""Launch with ``python -m prospero.builder`` from the repository root."""

import argparse

from dotenv import load_dotenv

load_dotenv()

from nicegui import ui  # noqa: E402

from prospero.themes import setup_theme  # noqa: E402
from .editor import ScreenEditor  # noqa: E402


@ui.page("/")
async def editor_page() -> None:
    setup_theme(dark=True)
    await ScreenEditor().build()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Prospero visual screen editor")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8081)
    args = parser.parse_args()
    ui.run(
        host=args.host,
        port=args.port,
        title="Prospero · Screen studio",
        reload=False,
        show=False,
    )
