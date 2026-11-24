"""Renderer-Schnittstelle. Koordinaten in mm, Ursprung oben links, y nach unten."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Optional, Sequence

from sld.layout.metrics import HeuristicMetrics, TextMetrics

Point = tuple[float, float]


class Renderer(ABC):
    """Zeichen-Backend. Bekommt nur Primitive. Layout und Symbolgeometrie kommen von außen."""

    formats: tuple[str, ...] = ()

    @abstractmethod
    def begin(self, width: float, height: float, background: str) -> None: ...

    @abstractmethod
    def polyline(
        self,
        pts: Sequence[Point],
        *,
        color: str,
        width: float,
        dash: Optional[Sequence[float]] = None,
    ) -> None: ...

    @abstractmethod
    def polygon(
        self, pts: Sequence[Point], *, fill: Optional[str], edge: Optional[str], width: float
    ) -> None: ...

    @abstractmethod
    def circle(
        self, cx: float, cy: float, r: float, *, fill: Optional[str], edge: Optional[str], width: float
    ) -> None: ...

    @abstractmethod
    def text(
        self,
        x: float,
        y: float,
        s: str,
        *,
        size: float,
        color: str,
        family: str,
        bold: bool = False,
        ha: str = "left",
        va: str = "center",
    ) -> None: ...

    @abstractmethod
    def save(self, path: str, fmt: str, dpi: int = 200) -> None: ...

    def text_metrics(self, family: str) -> TextMetrics:
        """Textvermessung für das Layout. Backends können exakte Metriken liefern."""
        return HeuristicMetrics()
