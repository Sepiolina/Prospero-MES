"""prospero.components.pdf_viewer — PDFViewer / PDFViewerProps"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from nicegui import ui

from prospero.core.base import StateMixin
from prospero.themes import ThemeColors


@dataclass
class PDFViewerProps:
    """Configuration for a `PDFViewer`.

    ``source``: path under /static (or any URL NiceGUI can serve).
    ``height``: any valid CSS height value, e.g. "100%" or "600px".
    ``page_from`` / ``page_to``: inclusive 1-indexed page range to
        display for the current Work Instruction (WI). Leave both
        `None` to show the full document.
    """

    source: str
    height: str = "100%"
    page_from: Optional[int] = None
    page_to: Optional[int] = None


class PDFViewer(StateMixin, ui.element):
    _PDFJS_CDN = "https://cdnjs.cloudflare.com/ajax/libs/pdf.js/3.11.174/pdf.min.js"

    def __init__(self, props: PDFViewerProps, classes: str = "") -> None:
        super().__init__("div")
        self._init_state(enabled=True)
        self.classes(f"{classes} bg-[var(--p-panel)] rounded-lg overflow-auto")
        self.style(f"height: {props.height};")

        container_id = f"pdf-container-{self.id}"
        self._props["id"] = container_id

        ui.add_head_html(f'<script src="{self._PDFJS_CDN}"></script>', shared=True)

        page_from = props.page_from or 1
        page_to = props.page_to or page_from

        with self:
            ui.spinner(size="2em").classes("m-auto").style(
                f"color: {ThemeColors.ACCENT};"
            )
        ui.run_javascript(
            f"""
            (function renderPdf(retries) {{
                const container = document.getElementById('{container_id}');
                if (!container) return;
                if (typeof pdfjsLib === 'undefined') {{
                    if (retries > 0) setTimeout(() => renderPdf(retries - 1), 200);
                    return;
                }}
                pdfjsLib.GlobalWorkerOptions.workerSrc =
                    'https://cdnjs.cloudflare.com/ajax/libs/pdf.js/3.11.174/pdf.worker.min.js';
                pdfjsLib.getDocument('{props.source}').promise.then(function(pdf) {{
                    container.innerHTML = '';
                    const from = {page_from};
                    const to = Math.min({page_to}, pdf.numPages);
                    for (let p = from; p <= to; p++) {{
                        pdf.getPage(p).then(function(page) {{
                            const viewport = page.getViewport({{scale: 1.4}});
                            const canvas = document.createElement('canvas');
                            canvas.style.display = 'block';
                            canvas.style.margin = '0 auto 12px auto';
                            canvas.width = viewport.width;
                            canvas.height = viewport.height;
                            container.appendChild(canvas);
                            page.render({{
                                canvasContext: canvas.getContext('2d'),
                                viewport: viewport
                            }});
                        }});
                    }}
                }}).catch(function(err) {{
                    container.innerHTML =
                        '<p style="color:{ThemeColors.NEGATIVE};padding:1rem;">' +
                        'Unable to load work instruction PDF.</p>';
                }});
            }})(25);
            """
        )
