from __future__ import annotations
import os
from typing import Optional

from dotenv import load_dotenv
from nicegui import ui, app

from prospero.themes import setup_theme
from stations.test import build_test_station

load_dotenv()


def _str_to_bool(value: Optional[str], default: bool = False) -> bool:
    if value is None:
        return default
    return value.strip().lower() in ("true", "1", "yes")


HOST = os.getenv("HOST", "127.0.0.1")
PORT = int(os.getenv("PORT", "8080"))

APP_RELOAD = _str_to_bool(os.getenv("APP_DEV_MODE"), default=False)

APP_NAME = os.getenv("APP_NAME", "Prospero-MES")
VERSION = os.getenv("VERSION", "v0.0.0")
FAVICON = os.getenv("FAVICON", "📊")

APP_NATIVE = _str_to_bool(os.getenv("APP_NATIVE"), default=True)
APP_SHOW = _str_to_bool(os.getenv("APP_NATIVE"), default=False)


@ui.page("/")
def index_page() -> None:
    setup_theme(dark=True)
    build_test_station()


if __name__ in {"__main__", "__mp_main__"}:
    app.add_static_files("/static", "static")
    ui.run(
        title=APP_NAME,
        favicon=FAVICON,
        reload=APP_RELOAD,
        show=APP_SHOW,
        native=APP_NATIVE,
        host=HOST,
        port=PORT,
    )
