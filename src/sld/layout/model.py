"""Ergebnis des Layouts: rein geometrische Beschreibung, unabhängig vom Backend.

Einheiten: mm. Ursprung oben links, y wächst nach unten.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from sld.components import Component
from sld.schema.issues import Issue

Point = tuple[float, float]


@dataclass
class Box:
    x0: float
    y0: float
    x1: float
    y1: float

    @property
    def width(self) -> float:
        return self.x1 - self.x0

    @property
    def height(self) -> float:
        return self.y1 - self.y0

    def overlaps(self, other: "Box", eps: float = 0.05) -> bool:
        return (
            self.x0 < other.x1 - eps
            and other.x0 < self.x1 - eps
            and self.y0 < other.y1 - eps
            and other.y0 < self.y1 - eps
        )

    def shifted(self, dx: float, dy: float) -> "Box":
        return Box(self.x0 + dx, self.y0 + dy, self.x1 + dx, self.y1 + dy)

    def union(self, other: "Box") -> "Box":
        return Box(min(self.x0, other.x0), min(self.y0, other.y0), max(self.x1, other.x1), max(self.y1, other.y1))

    @staticmethod
    def around(points: list[Point]) -> "Box":
        xs, ys = [p[0] for p in points], [p[1] for p in points]
        return Box(min(xs), min(ys), max(xs), max(ys))


@dataclass
class TextLine:
    text: str
    x: float
    y: float  # Mitte der Zeile
    size: float
    bold: bool = False
    ha: str = "left"


@dataclass
class PlacedLabel:
    owner: str
    kind: str  # node | bus | band | title | table
    lines: list[TextLine]
    box: Box

    def translate(self, dx: float, dy: float) -> None:
        for ln in self.lines:
            ln.x += dx
            ln.y += dy
        self.box = self.box.shifted(dx, dy)


@dataclass
class PlacedSymbol:
    id: str
    node: Component
    cx: float
    cy: float
    w: float
    h: float
    rot: int = 0
    span: Optional[tuple[float, float]] = None  # Sammelschiene: absolute x-Grenzen

    @property
    def box(self) -> Box:
        if self.span is not None:
            half = max(self.h, 1.0) / 2
            return Box(self.span[0], self.cy - half, self.span[1], self.cy + half)
        w, h = (self.h, self.w) if self.rot == 90 else (self.w, self.h)
        return Box(self.cx - w / 2, self.cy - h / 2, self.cx + w / 2, self.cy + h / 2)

    def translate(self, dx: float, dy: float) -> None:
        self.cx += dx
        self.cy += dy
        if self.span:
            self.span = (self.span[0] + dx, self.span[1] + dx)


@dataclass
class Wire:
    points: list[Point]

    def translate(self, dx: float, dy: float) -> None:
        self.points = [(x + dx, y + dy) for x, y in self.points]


@dataclass
class Band:
    name: str
    y0: float
    y1: float
    x0: float
    x1: float
    segments: list[tuple[float, float]] = field(default_factory=list)  # sichtbare Teile der Oberkante

    def translate(self, dx: float, dy: float) -> None:
        self.x0 += dx
        self.x1 += dx
        self.y0 += dy
        self.y1 += dy
        self.segments = [(a + dx, b + dx) for a, b in self.segments]


@dataclass
class Table:
    """Stückliste: Raster + Texte (Texte als Labels, damit Backends nichts messen müssen)."""

    box: Box
    col_x: list[float]  # linke Kanten der Spalten + rechte Außenkante
    row_y: list[float]  # obere Kanten der Zeilen + untere Außenkante
    cells: list[TextLine] = field(default_factory=list)
    title: Optional[TextLine] = None

    def translate(self, dx: float, dy: float) -> None:
        self.box = self.box.shifted(dx, dy)
        self.col_x = [x + dx for x in self.col_x]
        self.row_y = [y + dy for y in self.row_y]
        for ln in self.cells + ([self.title] if self.title else []):
            ln.x += dx
            ln.y += dy


@dataclass
class TitleBlockCell:
    box: Box
    caption: str
    value: str
    value_size: float = 6.5
    bold: bool = False


@dataclass
class TitleBlock:
    box: Box
    cells: list[TitleBlockCell]


@dataclass
class Layout:
    """Fertiges Blatt.

    Plan-Inhalt (Symbole, Leitungen, Labels, Bänder, Stückliste) liegt in Inhaltskoordinaten;
    Blattkoordinate = content_offset + content_scale * Inhaltskoordinate. Rahmen und Schriftfeld
    liegen immer in Blattkoordinaten. Ohne Verkleinerung ist die Abbildung die Identität.
    """

    width: float
    height: float
    symbols: dict[str, PlacedSymbol]
    labels: list[PlacedLabel]
    wires: list[Wire]
    junctions: list[Point]
    bands: list[Band]
    table: Optional[Table] = None
    title_block: Optional[TitleBlock] = None
    frame: Optional[Box] = None
    warnings: list[Issue] = field(default_factory=list)
    content_scale: float = 1.0
    content_offset: Point = (0.0, 0.0)
    paper: Optional[str] = None  # z. B. "A4 quer", None = freies Format

    def translate_content(self, dx: float, dy: float) -> None:
        for s in self.symbols.values():
            s.translate(dx, dy)
        for lab in self.labels:
            lab.translate(dx, dy)
        for w in self.wires:
            w.translate(dx, dy)
        for b in self.bands:
            b.translate(dx, dy)
        self.junctions = [(x + dx, y + dy) for x, y in self.junctions]
        if self.table:
            self.table.translate(dx, dy)

    def to_page(self, box: Box) -> Box:
        s, (ox, oy) = self.content_scale, self.content_offset
        return Box(ox + s * box.x0, oy + s * box.y0, ox + s * box.x1, oy + s * box.y1)

    def boxes(self) -> list[tuple[str, str, Box]]:
        """Alle Bounding-Boxen (Blattkoordinaten), die sich nicht überlappen dürfen: (Besitzer, Art, Box)."""
        out = [(s.id, "symbol", self.to_page(s.box)) for s in self.symbols.values()]
        out += [(lab.owner, lab.kind, self.to_page(lab.box)) for lab in self.labels]
        if self.table:
            out.append(("bom", "table", self.to_page(self.table.box)))
        if self.title_block:
            out.append(("title_block", "title_block", self.title_block.box))
        return out

    def overlaps(self) -> list[tuple[str, str]]:
        boxes = self.boxes()
        found = []
        for i, (oa, ka, ba) in enumerate(boxes):
            for ob, kb, bb in boxes[i + 1 :]:
                if ba.overlaps(bb):
                    found.append((f"{ka}:{oa}", f"{kb}:{ob}"))
        return found
