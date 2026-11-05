"""Canvas interaction layer. It never inserts layout boxes around screen nodes."""

from nicegui.element import Element


class StudioSurface(Element, component="surface.js"):
    def __init__(
        self,
        *,
        selected: str,
        width: int,
        zoom: str,
        editing: bool,
        dirty: bool = False,
    ) -> None:
        super().__init__()
        self._props.update(
            selected=selected, width=width, zoom=zoom, editing=editing, dirty=dirty
        )

    def configure(self, **props) -> None:
        self._props.update(props)
        self.update()
