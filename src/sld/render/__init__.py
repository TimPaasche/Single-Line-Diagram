"""Rendering: Layout berechnen und über ein Backend zeichnen.

Das matplotlib-Backend wird erst bei Bedarf importiert.
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from sld.layout import Layout, compute_layout
from sld.render.base import Renderer
from sld.render.draw import draw_layout
from sld.themes import get_theme

FORMATS = ("svg", "png", "pdf")


def default_renderer() -> Renderer:
    from sld.render.mpl import MatplotlibRenderer

    return MatplotlibRenderer()


def render(
    diagram,
    output: str | Path,
    fmt: Optional[str] = None,
    theme: Optional[str] = None,
    renderer: Optional[Renderer] = None,
    dpi: int = 200,
    paper: Optional[str] = None,
    orientation: Optional[str] = None,
) -> Layout:
    """Zeichnet den Schaltplan nach ``output``. Format aus ``fmt`` oder der Dateiendung.

    ``paper`` (auto/A5/A4/A3/none) und ``orientation`` (auto/landscape/portrait)
    überschreiben die Angaben aus ``diagram``.
    """
    output = Path(output)
    fmt = (fmt or output.suffix.lstrip(".") or "svg").lower()
    renderer = renderer or default_renderer()
    if fmt not in renderer.formats:
        raise ValueError(f"Unbekanntes Ausgabeformat '{fmt}' (möglich: {', '.join(renderer.formats)})")
    th = get_theme(theme or diagram.diagram.theme)
    layout = compute_layout(
        diagram, metrics=renderer.text_metrics(th.font_family), theme=th, paper=paper, orientation=orientation
    )
    draw_layout(layout, th, renderer)
    renderer.save(str(output), fmt, dpi=dpi)
    return layout


__all__ = ["FORMATS", "Renderer", "default_renderer", "draw_layout", "render"]
