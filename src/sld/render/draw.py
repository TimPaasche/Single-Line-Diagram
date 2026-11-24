"""Zeichnet ein fertiges Layout über die Renderer-Schnittstelle (backend-unabhängig)."""

from __future__ import annotations

from sld.components import DrawContext
from sld.layout.model import Layout
from sld.render.base import Renderer
from sld.render.pen import Pen
from sld.themes import Theme

JUNCTION_R = 0.75
DASH_DOT = (6.0, 1.5, 1.0, 1.5)


def _rect(box) -> list[tuple[float, float]]:
    return [(box.x0, box.y0), (box.x1, box.y0), (box.x1, box.y1), (box.x0, box.y1)]


class _Scaled(Renderer):
    """Leitet Primitive verkleinert/verschoben an einen anderen Renderer weiter."""

    def __init__(self, inner: Renderer, scale: float, offset: tuple[float, float]):
        self.inner, self.s, (self.ox, self.oy) = inner, scale, offset
        self.formats = inner.formats

    def _p(self, pts):
        return [(self.ox + self.s * x, self.oy + self.s * y) for x, y in pts]

    def begin(self, width, height, background):  # pragma: no cover - wird nie aufgerufen
        self.inner.begin(width, height, background)

    def polyline(self, pts, *, color, width, dash=None):
        self.inner.polyline(
            self._p(pts), color=color, width=width * self.s, dash=[d * self.s for d in dash] if dash else None
        )

    def polygon(self, pts, *, fill, edge, width):
        self.inner.polygon(self._p(pts), fill=fill, edge=edge, width=width * self.s)

    def circle(self, cx, cy, r, *, fill, edge, width):
        (x, y), = self._p([(cx, cy)])
        self.inner.circle(x, y, r * self.s, fill=fill, edge=edge, width=width * self.s)

    def text(self, x, y, s, *, size, color, family, bold=False, ha="left", va="center"):
        (px, py), = self._p([(x, y)])
        self.inner.text(px, py, s, size=size * self.s, color=color, family=family, bold=bold, ha=ha, va=va)

    def save(self, path, fmt, dpi=200):  # pragma: no cover - wird nie aufgerufen
        self.inner.save(path, fmt, dpi)


def draw_layout(layout: Layout, theme: Theme, page: Renderer) -> None:
    page.begin(layout.width, layout.height, theme.background)
    identity = layout.content_scale == 1.0 and layout.content_offset == (0.0, 0.0)
    r = page if identity else _Scaled(page, layout.content_scale, layout.content_offset)
    text = dict(color=theme.text_color, family=theme.font_family)

    # Spannungsebenen
    for i, band in enumerate(layout.bands):
        if theme.band_fills:
            fill = theme.band_fills[i % len(theme.band_fills)]
            r.polygon([(band.x0, band.y0), (band.x1, band.y0), (band.x1, band.y1), (band.x0, band.y1)], fill=fill, edge=None, width=0)
        if theme.band_line and i > 0:
            for a, b in band.segments:
                r.polyline([(a, band.y0), (b, band.y0)], color=theme.band_line, width=0.18, dash=DASH_DOT)

    for wire in layout.wires:
        r.polyline(wire.points, color=theme.line_color, width=theme.line_width)

    for s in layout.symbols.values():
        pen = Pen(r, theme, s.cx, s.cy, s.rot)
        span = (s.span[0] - s.cx, s.span[1] - s.cx) if s.span else None
        s.node.draw(pen, DrawContext(theme=theme, span=span))

    for x, y in layout.junctions:
        r.circle(x, y, JUNCTION_R, fill=theme.line_color, edge=None, width=0)

    for lab in layout.labels:
        color = theme.band_text if lab.kind == "band" else theme.text_color
        for ln in lab.lines:
            r.text(ln.x, ln.y, ln.text, size=ln.size, bold=ln.bold, ha=ln.ha, va="center", color=color, family=theme.font_family)

    if layout.table:
        t = layout.table
        thin = theme.line_width * 0.6
        for y in t.row_y:
            r.polyline([(t.col_x[0], y), (t.col_x[-1], y)], color=theme.line_color, width=thin)
        for x in t.col_x:
            r.polyline([(x, t.row_y[0]), (x, t.row_y[-1])], color=theme.line_color, width=thin)
        if t.title:
            r.text(t.title.x, t.title.y, t.title.text, size=t.title.size, bold=True, **text)
        for c in t.cells:
            r.text(c.x, c.y, c.text, size=c.size, bold=c.bold, ha=c.ha, **text)

    r = page  # Rahmen und Schriftfeld immer in Blattkoordinaten
    if layout.frame:
        r.polygon(_rect(layout.frame), fill=None, edge=theme.line_color, width=0.7)

    if layout.title_block:
        tb = layout.title_block
        r.polygon(_rect(tb.box), fill=theme.background, edge=theme.line_color, width=0.5)
        for cell in tb.cells:
            b = cell.box
            r.polygon(_rect(b), fill=None, edge=theme.line_color, width=0.25)
            r.text(b.x0 + 1.0, b.y0 + 1.6, cell.caption, size=4.5, color="#666666", family=theme.font_family)
            if cell.value:
                r.text(b.x0 + 1.5, (b.y0 + b.y1) / 2 + 1.0, cell.value, size=cell.value_size, bold=cell.bold, **text)
