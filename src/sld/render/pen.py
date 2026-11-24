"""Pen: lokales Symbol-Koordinatensystem -> Renderer.

Symbole zeichnen senkrecht: Mitte (0, 0), oberer Anschluss bei y = -h/2,
unterer Anschluss bei y = +h/2 (y zeigt nach unten). Bei ``rot=90`` wird das
Symbol waagerecht gelegt (oberer Anschluss links). Texte bleiben waagerecht.
"""

from __future__ import annotations

import math
from typing import Optional, Sequence

from sld.render.base import Point, Renderer
from sld.themes import Theme

FG = "fg"  # Linienfarbe
BG = "bg"  # Hintergrundfarbe


class Pen:
    def __init__(self, renderer: Renderer, theme: Theme, cx: float, cy: float, rot: int = 0):
        self.r = renderer
        self.theme = theme
        self.cx, self.cy, self.rot = cx, cy, rot

    @property
    def lw(self) -> float:
        return self.theme.line_width

    # -- Koordinaten ---------------------------------------------------------
    def pt(self, x: float, y: float) -> Point:
        if self.rot == 90:
            return (self.cx + y, self.cy - x)
        return (self.cx + x, self.cy + y)

    def _color(self, c: Optional[str]) -> Optional[str]:
        if c == FG:
            return self.theme.line_color
        if c == BG:
            return self.theme.background
        return c

    # -- Primitive -----------------------------------------------------------
    def line(self, *pts: Point, width: Optional[float] = None, dash: Optional[Sequence[float]] = None) -> None:
        self.r.polyline(
            [self.pt(*p) for p in pts],
            color=self.theme.line_color,
            width=self.lw if width is None else width,
            dash=dash,
        )

    def polygon(self, pts: Sequence[Point], fill: Optional[str] = None, width: Optional[float] = None) -> None:
        self.r.polygon(
            [self.pt(*p) for p in pts],
            fill=self._color(fill),
            edge=self.theme.line_color,
            width=self.lw if width is None else width,
        )

    def rect(self, x: float, y: float, w: float, h: float, fill: Optional[str] = None) -> None:
        self.polygon([(x, y), (x + w, y), (x + w, y + h), (x, y + h)], fill=fill)

    def circle(self, x: float, y: float, radius: float, fill: Optional[str] = None) -> None:
        px, py = self.pt(x, y)
        self.r.circle(px, py, radius, fill=self._color(fill), edge=self.theme.line_color, width=self.lw)

    def ellipse(self, x: float, y: float, rx: float, ry: float, fill: Optional[str] = None, n: int = 36) -> None:
        pts = [(x + rx * math.cos(2 * math.pi * i / n), y + ry * math.sin(2 * math.pi * i / n)) for i in range(n)]
        self.polygon(pts, fill=fill)

    def text(
        self, x: float, y: float, s: str, size: float = 7.0, bold: bool = False, ha: str = "center", va: str = "center"
    ) -> None:
        px, py = self.pt(x, y)
        self.r.text(
            px, py, s, size=size, color=self.theme.text_color, family=self.theme.font_family, bold=bold, ha=ha, va=va
        )

    # -- zusammengesetzte Grundformen ---------------------------------------
    def arrow(self, start: Point, end: Point, head: float = 1.2) -> None:
        """Linie mit gefüllter Pfeilspitze am Ende."""
        (x0, y0), (x1, y1) = start, end
        length = math.hypot(x1 - x0, y1 - y0) or 1.0
        ux, uy = (x1 - x0) / length, (y1 - y0) / length
        bx, by = x1 - ux * head, y1 - uy * head
        self.line(start, (bx, by))
        nx, ny = -uy * head * 0.45, ux * head * 0.45
        self.polygon([(x1, y1), (bx + nx, by + ny), (bx - nx, by - ny)], fill=FG, width=self.lw * 0.5)

    def sine(self, x: float, y: float, width: float, amp: float) -> None:
        """Wechselstromzeichen ~ (eine volle Periode)."""
        n = 24
        pts = [(x - width / 2 + width * i / n, y - amp * math.sin(2 * math.pi * i / n)) for i in range(n + 1)]
        self.line(*pts)

    def dc_sign(self, x: float, y: float, width: float) -> None:
        """Gleichstromzeichen: durchgezogene Linie über gestrichelter Linie."""
        self.line((x - width / 2, y - 0.5), (x + width / 2, y - 0.5))
        seg = width / 5
        for i in (0, 2, 4):
            x0 = x - width / 2 + i * seg
            self.line((x0, y + 0.5), (x0 + seg, y + 0.5))

    def hatch(self, x: float, y: float, w: float, h: float, spacing: float = 2.0) -> None:
        """45°-Schraffur innerhalb des Rechtecks (x, y, w, h)."""
        x0, y0, x1, y1 = x, y, x + w, y + h
        c = x0 + y0 + spacing
        while c < x1 + y1:
            lo, hi = max(x0, c - y1), min(x1, c - y0)
            if lo < hi:
                self.line((lo, c - lo), (hi, c - hi), width=self.lw * 0.6)
            c += spacing
