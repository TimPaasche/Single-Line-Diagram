"""Basisklasse aller Komponenten.

Eine Komponente ist gleichzeitig ihr pydantic-Parametermodell und ihre
Symboldefinition. Neue Komponenten werden mit ``@register("name")`` angemeldet.
"""

from dataclasses import dataclass
from enum import Enum
from typing import TYPE_CHECKING, ClassVar, Literal, Optional

from pydantic import Field

from sld.schema.base import NodeBase

if TYPE_CHECKING:  # nur für Typprüfung, kein Laufzeitimport (Schichtentrennung)
    from sld.render.pen import Pen
    from sld.themes import Theme


class Kind(str, Enum):
    SOURCE = "source"  # Einspeisung, nur unterer Anschluss (Netz)
    BUS = "bus"  # Sammelschiene, beliebig viele Abgänge
    SERIES = "series"  # Zweipol in Reihe (oben/unten), darf in "via" stehen
    TERMINAL = "terminal"  # Endgerät, nur oberer Anschluss


@dataclass
class DrawContext:
    theme: "Theme"
    span: Optional[tuple[float, float]] = None  # Sammelschienen: x-Bereich lokal zur Mitte


class Component(NodeBase):
    # Metadaten (ClassVars, keine Konfigurationsfelder)
    type_name: ClassVar[str] = ""
    kind: ClassVar[Kind] = Kind.SERIES
    title: ClassVar[str] = ""  # deutscher Anzeigename
    ref_letter: ClassVar[str] = "X"  # Kennbuchstabe für automatische IDs (DIN EN 81346)
    size: ClassVar[tuple[float, float]] = (8.0, 10.0)  # Breite, Höhe in mm
    max_connections: ClassVar[Optional[int]] = None  # None = Vorgabe nach kind
    is_transformer: ClassVar[bool] = False
    is_inverter: ClassVar[bool] = False
    is_grounding: ClassVar[bool] = False

    # -- Topologie / Prüfung -------------------------------------------------
    def connection_limit(self) -> Optional[int]:
        if self.max_connections is not None:
            return self.max_connections
        return {Kind.TERMINAL: 1, Kind.SERIES: 2}.get(self.kind)

    def is_open(self) -> bool:
        return False

    def is_dc_device(self) -> bool:
        """True, wenn das Gerät auf der DC-Seite arbeitet (PV-Generator, DC-Speicher)."""
        return False

    def explicit_voltage(self) -> Optional[float]:
        return None

    def generation_kva(self, behind_inverter: bool = False) -> float:
        """Einspeiseleistung auf der AC-Seite (für die Trafo-Auslastungswarnung)."""
        return 0.0

    # -- Darstellung ---------------------------------------------------------
    def symbol_size(self) -> tuple[float, float]:
        return self.size

    def data_lines(self) -> list[str]:
        """Technische Daten als kurze Beschriftungszeilen."""
        return []

    def draw(self, pen: "Pen", ctx: DrawContext) -> None:
        raise NotImplementedError(f"{type(self).__name__}.draw fehlt")


class SwitchingDevice(Component):
    """Gemeinsame Basis für Schaltgeräte mit Schaltzustand."""

    kind = Kind.SERIES
    size = (7.0, 12.0)
    ref_letter = "Q"

    state: Literal["open", "closed"] = Field("closed", description="Schaltzustand: open | closed")
    rating_a: Optional[float] = Field(None, gt=0, description="Bemessungsstrom in A")

    def is_open(self) -> bool:
        return self.state == "open"

    def data_lines(self) -> list[str]:
        from sld.util import fmt_num

        out = []
        if self.rating_a:
            out.append(f"{fmt_num(self.rating_a)} A")
        if self.is_open():
            out.append("offen")
        return out
