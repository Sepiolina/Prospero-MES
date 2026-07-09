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
    _PDFJS_ = "/static/pdf.min.js"
    _PDFJS_WORKER = "/static/pdf.worker.min.js"

    def __init__(self, props: PDFViewerProps, classes: str = "") -> None:
        super().__init__("div")
        self._init_state(enabled=True)

        self.viewer_id = f"pdf-viewer-{self.id}"

        self.props(f'id="{self.viewer_id}"')
        self.classes(
            f"{classes} bg-[#f3f4f6] dark:bg-[#121212] rounded-xl overflow-hidden relative border border-gray-200 dark:border-gray-700 transition-colors duration-200"
        )
        self.style(f"height: {props.height};")

        ui.add_head_html(
            """
            <style>
                /* Native browser fullscreen safety backgrounds */
                :fullscreen { background-color: #f3f4f6 !important; }
                .dark :fullscreen { background-color: #121212 !important; }

                /* Hybrid CSS Overlay Fullscreen (guarantees fullscreen inside native desktop mode/webview) */
                .pdf-viewer-fixed-fs {
                    position: fixed !important;
                    top: 0 !important;
                    left: 0 !important;
                    width: 100vw !important;
                    height: 100vh !important;
                    max-width: 100vw !important;
                    max-height: 100vh !important;
                    z-index: 999999 !important;
                    border-radius: 0 !important;
                    border: none !important;
                    margin: 0 !important;
                }

                /* Dark Mode canvas inversion */
                .pdf-canvas-dark { filter: invert(90%) hue-rotate(180deg) brightness(95%) contrast(90%); }

                /* Cursors */
                .pdf-grab { cursor: grab; }
                .pdf-grabbing { cursor: grabbing !important; }

                /* Sleek Scrollbar */
                .pdf-hide-scrollbar::-webkit-scrollbar { width: 6px; height: 6px; }
                .pdf-hide-scrollbar::-webkit-scrollbar-track { background: transparent; }
                .pdf-hide-scrollbar::-webkit-scrollbar-thumb { background: #cbd5e1; border-radius: 4px; }
                .dark .pdf-hide-scrollbar::-webkit-scrollbar-thumb { background: #475569; }

                /* Native arrow hiding for inputs */
                .hide-arrows::-webkit-inner-spin-button, .hide-arrows::-webkit-outer-spin-button { -webkit-appearance: none; margin: 0; }
                .hide-arrows { -moz-appearance: textfield; }
            </style>
        """,
            shared=True,
        )
        ui.add_head_html(f'<script src="{self._PDFJS_}"></script>', shared=True)

        self.wrapper_id = f"pdf-wrapper-{self.id}"
        self.container_id = f"pdf-container-{self.id}"
        self.spinner_id = f"pdf-spinner-{self.id}"
        self.page_input_id = f"pdf-page-input-{self.id}"
        self.page_total_id = f"pdf-page-total-{self.id}"
        self.zoom_label_id = f"pdf-zoom-label-{self.id}"
        self.close_btn_id = f"pdf-close-btn-{self.id}"

        with self:
            self.pdf_wrapper = (
                ui.element("div")
                .props(f'id="{self.wrapper_id}"')
                .classes(
                    "w-full h-full overflow-y-auto overflow-x-auto pdf-hide-scrollbar relative pdf-grab bg-transparent"
                )
            )

            with self.pdf_wrapper:
                self.spinner = (
                    ui.spinner(size="2.5em")
                    .props(f'id="{self.spinner_id}"')
                    .classes(
                        "absolute top-1/2 left-1/2 transform -translate-x-1/2 -translate-y-1/2 z-10"
                    )
                    .style(f"color: {ThemeColors.ACCENT};")
                )

                self.pdf_container = (
                    ui.element("div")
                    .props(f'id="{self.container_id}"')
                    .classes("mx-auto w-max py-8 flex flex-col items-center")
                )

            self.close_btn = (
                ui.button(icon="close", on_click=self._js_call("exitFullscreen()"))
                .props(f'id="{self.close_btn_id}" flat round color="white"')
                .classes(
                    "absolute top-4 right-4 z-[999999] bg-black/60 hover:bg-black/90 backdrop-blur-md shadow-xl transition-all duration-200"
                )
                .style(
                    "display: none; width: 3.5rem; height: 3.5rem; font-size: 1.25rem;"
                )
                .tooltip("Exit Fullscreen (ESC)")
            )

            with ui.element("div").classes(
                "absolute bottom-5 left-1/2 transform -translate-x-1/2 "
                "px-2 py-1.5 flex items-center justify-center gap-0.5 sm:gap-1 "
                "rounded-full z-[999998] flex-nowrap w-max max-w-[95vw] overflow-x-auto pdf-hide-scrollbar "
                "bg-white/40 dark:bg-gray-800/40 backdrop-blur-[6px] border border-gray-300/30 dark:border-gray-600/40 shadow-sm opacity-60 "
                "hover:bg-white/95 dark:hover:bg-gray-800/95 hover:backdrop-blur-xl hover:shadow-xl hover:opacity-100 "
                "transition-all duration-300 ease-in-out cursor-default text-gray-700 dark:text-gray-200"
            ):
                # Zoom Controls
                ui.button(icon="remove", on_click=self._js_call("zoomOut()")).props(
                    "flat round dense size=sm color=inherit text-color=inherit"
                )
                ui.label("100%").props(f'id="{self.zoom_label_id}"').classes(
                    "w-10 text-center text-[11px] font-bold select-none"
                )
                ui.button(icon="add", on_click=self._js_call("zoomIn()")).props(
                    "flat round dense size=sm color=inherit text-color=inherit"
                )

                ui.separator().props("vertical").classes("mx-1 h-5")

                # Navigation Controls
                ui.button(
                    icon="chevron_left", on_click=self._js_call("prevPage()")
                ).props("flat round dense size=sm color=inherit text-color=inherit")

                self.page_input = (
                    ui.element("input")
                    .props(f'id="{self.page_input_id}" type="number" min="1"')
                    .classes(
                        "w-7 text-center text-[13px] font-bold bg-transparent outline-none border-none text-inherit hide-arrows p-0 m-0"
                    )
                )
                ui.label(" / 0").props(f'id="{self.page_total_id}"').classes(
                    "text-[13px] font-bold opacity-60 select-none mr-1 tracking-wider"
                )
                ui.button(
                    icon="chevron_right", on_click=self._js_call("nextPage()")
                ).props("flat round dense size=sm color=inherit text-color=inherit")

                ui.separator().props("vertical").classes("mx-1 h-5")

                # Quality of Life Controls
                ui.button(
                    icon="contrast", on_click=self._js_call("toggleDarkMode()")
                ).props(
                    "flat round dense size=sm color=inherit text-color=inherit"
                ).tooltip("Toggle Dark Mode")
                ui.button(
                    icon="fullscreen", on_click=self._js_call("toggleFullscreen()")
                ).props(
                    "flat round dense size=sm color=inherit text-color=inherit"
                ).tooltip("Toggle Fullscreen")

        self._inject_javascript(props)

    def _js_call_str(self, func: str) -> str:
        return f"window.pdfViewers['{self.id}'].{func}"

    def _js_call(self, func: str):
        return lambda: ui.run_javascript(self._js_call_str(func))

    def _inject_javascript(self, props: PDFViewerProps):
        page_from_str = str(props.page_from) if props.page_from is not None else "1"
        page_to_str = str(props.page_to) if props.page_to is not None else "null"

        ui.run_javascript(f"""
            if (!window.pdfViewers) window.pdfViewers = {{}};

            window.pdfViewers['{self.id}'] = new class {{
                constructor() {{
                    this.id = '{self.id}';
                    this.source = '{props.source}';
                    this.pageFrom = {page_from_str};
                    this.pageToConfig = {page_to_str};

                    this.scale = 1.0;
                    this.currentPage = this.pageFrom;
                    this.totalPages = 0;
                    this.isDarkMode = false;
                    this.isFullscreen = false;
                    this.pageWrappers = [];

                    this.isDragging = false;
                    this.dragStartX = 0;
                    this.dragStartY = 0;
                    this.scrollStartX = 0;
                    this.scrollStartY = 0;

                    this.init(25);
                }}

                getEl(key) {{
                    const ids = {{
                        viewer: '{self.viewer_id}',
                        wrapper: '{self.wrapper_id}',
                        container: '{self.container_id}',
                        spinner: '{self.spinner_id}',
                        pageInput: '{self.page_input_id}',
                        pageTotal: '{self.page_total_id}',
                        zoomLabel: '{self.zoom_label_id}',
                        closeBtn: '{self.close_btn_id}'
                    }};
                    return document.getElementById(ids[key]);
                }}

                init(retries) {{
                    if (typeof pdfjsLib === 'undefined') {{
                        if (retries > 0) setTimeout(() => this.init(retries - 1), 200);
                        else {{
                            const spinner = this.getEl('spinner');
                            if (spinner) spinner.style.display = 'none';
                        }}
                        return;
                    }}
                    pdfjsLib.GlobalWorkerOptions.workerSrc = '{self._PDFJS_WORKER}';
                    this.loadPDF();
                    this.setupEventListeners();
                }}

                loadPDF() {{
                    pdfjsLib.getDocument(this.source).promise.then(pdf => {{
                        const spinner = this.getEl('spinner');
                        const container = this.getEl('container');
                        if (spinner) spinner.style.display = 'none';
                        if (!container) return;

                        container.innerHTML = '';
                        this.pageWrappers = [];

                        let toPage = this.pageToConfig ? Math.min(this.pageToConfig, pdf.numPages) : pdf.numPages;
                        this.totalPages = (toPage - this.pageFrom) + 1;

                        const totalEl = this.getEl('pageTotal');
                        if (totalEl) totalEl.innerText = ` / ${{this.totalPages}}`;
                        this.updatePageInput(1);

                        const renderScale = Math.max(window.devicePixelRatio || 1, 2.5);

                        for (let p = this.pageFrom; p <= toPage; p++) {{
                            const wrapper = document.createElement('div');
                            wrapper.className = 'bg-white dark:bg-gray-200 shadow-lg mb-8 relative transition-all duration-75 select-none mx-auto';
                            wrapper.dataset.pageIndex = p - this.pageFrom + 1;

                            wrapper.addEventListener('dblclick', () => {{
                                this.scale = (this.scale === 1.0) ? 1.5 : 1.0;
                                this.applyZoom();
                            }});

                            container.appendChild(wrapper);
                            this.pageWrappers.push(wrapper);

                            pdf.getPage(p).then(page => {{
                                const viewport = page.getViewport({{scale: renderScale}});

                                const canvas = document.createElement('canvas');
                                canvas.style.display = 'block';
                                canvas.style.width = '100%';
                                canvas.style.height = '100%';
                                canvas.width = viewport.width;
                                canvas.height = viewport.height;

                                const baseWidth = viewport.width / renderScale;
                                const baseHeight = viewport.height / renderScale;
                                wrapper.baseWidth = baseWidth;
                                wrapper.baseHeight = baseHeight;

                                wrapper.style.width = `${{baseWidth}}px`;
                                wrapper.style.height = `${{baseHeight}}px`;
                                wrapper.appendChild(canvas);

                                page.render({{ canvasContext: canvas.getContext('2d'), viewport: viewport }});
                            }});
                        }}
                        this.setupIntersectionObserver();
                    }}).catch(err => {{
                        const spinner = this.getEl('spinner');
                        const container = this.getEl('container');
                        if (spinner) spinner.style.display = 'none';
                        if (container) container.innerHTML = '<p style="color:{ThemeColors.NEGATIVE};padding:1rem;">Error Loading PDF: ' + err.message + '</p>';
                    }});
                }}

                setupEventListeners() {{
                    const wrapper = this.getEl('wrapper');
                    if (!wrapper) return;

                    wrapper.addEventListener('mousedown', (e) => {{
                        if (e.target.closest('button') || e.target.closest('input')) return;
                        this.isDragging = true;
                        wrapper.classList.add('pdf-grabbing');
                        this.dragStartX = e.pageX - wrapper.offsetLeft;
                        this.dragStartY = e.pageY - wrapper.offsetTop;
                        this.scrollStartX = wrapper.scrollLeft;
                        this.scrollStartY = wrapper.scrollTop;
                    }});

                    wrapper.addEventListener('mousemove', (e) => {{
                        if (!this.isDragging) return;
                        e.preventDefault();
                        const x = e.pageX - wrapper.offsetLeft;
                        const y = e.pageY - wrapper.offsetTop;
                        wrapper.scrollLeft = this.scrollStartX - (x - this.dragStartX);
                        wrapper.scrollTop = this.scrollStartY - (y - this.dragStartY);
                    }});

                    const stopDrag = () => {{
                        this.isDragging = false;
                        wrapper.classList.remove('pdf-grabbing');
                    }};
                    wrapper.addEventListener('mouseup', stopDrag);
                    wrapper.addEventListener('mouseleave', stopDrag);

                    wrapper.addEventListener('wheel', (e) => {{
                        if (e.ctrlKey) {{
                            e.preventDefault();
                            if (e.deltaY < 0) this.zoomIn();
                            else this.zoomOut();
                        }}
                    }}, {{ passive: false }});

                    const input = this.getEl('pageInput');
                    if (input) {{
                        input.addEventListener('keydown', (e) => {{ if (e.key === 'Enter') this.goToPageFromInput(); }});
                    }}

                    document.addEventListener('fullscreenchange', () => {{
                        if (!document.fullscreenElement && this.isFullscreen) this.exitFullscreen();
                    }});
                }}

                setupIntersectionObserver() {{
                    const wrapper = this.getEl('wrapper');
                    if (!wrapper) return;
                    const observer = new IntersectionObserver((entries) => {{
                        let maxVisible = 0;
                        let maxVisiblePage = this.currentPage;
                        entries.forEach(entry => {{
                            if (entry.isIntersecting && entry.intersectionRatio > maxVisible) {{
                                maxVisible = entry.intersectionRatio;
                                maxVisiblePage = parseInt(entry.target.dataset.pageIndex);
                            }}
                        }});
                        if (maxVisible > 0) this.updatePageInput(maxVisiblePage);
                    }}, {{ root: wrapper, threshold: [0.25, 0.5, 0.75, 1.0] }});

                    this.pageWrappers.forEach(w => observer.observe(w));
                }}

                zoomIn() {{ this.scale = Math.min(this.scale + 0.15, 3.0); this.applyZoom(); }}
                zoomOut() {{ this.scale = Math.max(this.scale - 0.15, 0.4); this.applyZoom(); }}

                applyZoom() {{
                    this.pageWrappers.forEach(w => {{
                        if (w.baseWidth) {{
                            w.style.width = `${{w.baseWidth * this.scale}}px`;
                            w.style.height = `${{w.baseHeight * this.scale}}px`;
                        }}
                    }});
                    const zoomLabel = this.getEl('zoomLabel');
                    if (zoomLabel) zoomLabel.innerText = `${{Math.round(this.scale * 100)}}%`;
                }}

                prevPage() {{ this.scrollToPage(this.currentPage - 1); }}
                nextPage() {{ this.scrollToPage(this.currentPage + 1); }}

                goToPageFromInput() {{
                    const inputEl = this.getEl('pageInput');
                    if (!inputEl) return;
                    const val = parseInt(inputEl.value);
                    if (!isNaN(val)) this.scrollToPage(val);
                }}

                scrollToPage(pageIndex) {{
                    if (pageIndex < 1 || pageIndex > this.totalPages) return;
                    const el = this.pageWrappers[pageIndex - 1];
                    if (el) {{
                        const wrapper = this.getEl('wrapper');
                        const targetTop = el.offsetTop - 30;
                        wrapper.scrollTo({{top: targetTop, behavior: 'smooth'}});
                    }}
                }}

                updatePageInput(pageIndex) {{
                    this.currentPage = pageIndex;
                    const inputEl = this.getEl('pageInput');
                    if (inputEl) inputEl.value = pageIndex;
                }}

                toggleDarkMode() {{
                    this.isDarkMode = !this.isDarkMode;
                    const container = this.getEl('container');
                    if (!container) return;
                    const canvases = container.querySelectorAll('canvas');
                    canvases.forEach(c => {{
                        if (this.isDarkMode) c.classList.add('pdf-canvas-dark');
                        else c.classList.remove('pdf-canvas-dark');
                    }});
                }}

                toggleFullscreen() {{
                    if (!this.isFullscreen) this.enterFullscreen();
                    else this.exitFullscreen();
                }}

                enterFullscreen() {{
                    this.isFullscreen = true;
                    const viewer = this.getEl('viewer');
                    if (viewer) viewer.classList.add('pdf-viewer-fixed-fs');

                    const closeBtn = this.getEl('closeBtn');
                    if (closeBtn) closeBtn.style.display = 'flex';
                    if (viewer) {{
                        try {{
                            if (viewer.requestFullscreen) viewer.requestFullscreen().catch(e=>{{}});
                            else if (viewer.webkitRequestFullscreen) viewer.webkitRequestFullscreen();
                        }} catch (e) {{}}
                    }}

                    this._escListener = (e) => {{ if (e.key === 'Escape') this.exitFullscreen(); }};
                    document.addEventListener('keydown', this._escListener);
                }}

                exitFullscreen() {{
                    this.isFullscreen = false;

                    const viewer = this.getEl('viewer');
                    if (viewer) viewer.classList.remove('pdf-viewer-fixed-fs');

                    const closeBtn = this.getEl('closeBtn');
                    if (closeBtn) closeBtn.style.display = 'none';

                    try {{
                        if (document.fullscreenElement) document.exitFullscreen().catch(e=>{{}});
                        else if (document.webkitFullscreenElement) document.webkitExitFullscreen();
                    }} catch(e) {{}}
                    if (this._escListener) document.removeEventListener('keydown', this._escListener);
                }}
            }}();
        """)
