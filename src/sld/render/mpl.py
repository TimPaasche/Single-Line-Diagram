"""matplotlib-Backend (SVG, PNG, PDF). 1 Dateneinheit = 1 mm auf dem Blatt."""

from __future__ import annotations

from functools import lru_cache
from typing import Optional, Sequence

import matplotlib
from matplotlib.figure import Figure
from matplotlib.font_manager import FontProperties
from matplotlib.lines import Line2D
from matplotlib.patches import Circle, Polygon
from matplotlib.textpath import TextToPath

from sld.layout.metrics import LINE_SPACING, MM_PER_PT
from sld.render.base import Point, Renderer

PT_PER_MM = 1.0 / MM_PER_PT


class MatplotlibMetrics:
    """Exakte Textbreiten über die Fontmetriken von matplotlib."""

    def __init__(self, family: str):
        self.family = family
        self._ttp = TextToPath()

    @lru_cache(maxsize=4096)
    def width(self, text: str, size: float, bold: bool = False) -> float:
        if not text:
            return 0.0
        prop = FontProperties(family=self.family, size=size, weight="bold" if bold else "normal")
        w, _, _ = self._ttp.get_text_width_height_descent(text, prop, ismath=False)
        return w * MM_PER_PT

    def line_height(self, size: float) -> float:
        return size * MM_PER_PT * LINE_SPACING


class MatplotlibRenderer(Renderer):
    formats = ("svg", "png", "pdf")

    def __init__(self) -> None:
        self.fig: Optional[Figure] = None

    def begin(self, width: float, height: float, background: str) -> None:
        self.fig = Figure(figsize=(width / 25.4, height / 25.4))
        self.fig.patch.set_facecolor(background)
        ax = self.fig.add_axes((0, 0, 1, 1))
        ax.set_xlim(0, width)
        ax.set_ylim(height, 0)
        ax.set_axis_off()
        self.ax = ax

    def polyline(self, pts: Sequence[Point], *, color: str, width: float, dash: Optional[Sequence[float]] = None) -> None:
        xs, ys = zip(*pts)
        lw = width * PT_PER_MM
        line = Line2D(xs, ys, color=color, linewidth=lw, solid_capstyle="projecting", solid_joinstyle="miter")
        if dash:
            # matplotlib skaliert Strichmuster mit der Linienbreite -> zurückrechnen
            line.set_dashes([d * PT_PER_MM / lw for d in dash])
            line.set_dash_capstyle("butt")
        self.ax.add_line(line)

    def polygon(self, pts: Sequence[Point], *, fill: Optional[str], edge: Optional[str], width: float) -> None:
        self.ax.add_patch(
            Polygon(
                list(pts),
                closed=True,
                facecolor=fill or "none",
                edgecolor=edge or "none",
                linewidth=width * PT_PER_MM if edge else 0,
                joinstyle="miter",
            )
        )

    def circle(self, cx: float, cy: float, r: float, *, fill: Optional[str], edge: Optional[str], width: float) -> None:
        self.ax.add_patch(
            Circle((cx, cy), r, facecolor=fill or "none", edgecolor=edge or "none", linewidth=width * PT_PER_MM if edge else 0)
        )

    def text(self, x, y, s, *, size, color, family, bold=False, ha="left", va="center") -> None:
        self.ax.text(
            x, y, s, fontsize=size, color=color, family=family,
            fontweight="bold" if bold else "normal", ha=ha, va=va, parse_math=False,
        )  # fmt: skip

    def save(self, path: str, fmt: str, dpi: int = 200) -> None:
        if fmt not in self.formats:
            raise ValueError(f"Format '{fmt}' nicht unterstützt (möglich: {', '.join(self.formats)})")
        metadata = {"svg": {"Date": None}, "pdf": {"CreationDate": None}}.get(fmt)
        with matplotlib.rc_context({"svg.hashsalt": "sld"}):
            self.fig.savefig(path, format=fmt, dpi=dpi, facecolor=self.fig.get_facecolor(), metadata=metadata)

    def text_metrics(self, family: str) -> MatplotlibMetrics:
        return MatplotlibMetrics(family)
