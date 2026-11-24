from typing import Literal, Optional

from pydantic import Field

from sld.components.base import Component, DrawContext, Kind
from sld.components.registry import register

_DIRECTION = {"import": "Bezug", "export": "Einspeisung", "bidirectional": "Bezug/Einspeisung"}


@register("meter")
class Meter(Component):
    """Elektrizitätszähler (Wattstundenzähler) mit Zählrichtung."""

    kind = Kind.SERIES
    title = "Zähler"
    ref_letter = "P"
    size = (10.0, 12.0)

    direction: Literal["import", "export", "bidirectional"] = Field(
        "bidirectional", description="Zählrichtung: import (Bezug) | export (Einspeisung) | bidirectional"
    )
    number: Optional[str] = Field(None, description="Zählernummer / Messlokation")

    def data_lines(self) -> list[str]:
        out = [_DIRECTION[self.direction]]
        if self.number:
            out.append(self.number)
        return out

    def draw(self, pen, ctx: DrawContext) -> None:
        pen.line((0, -6), (0, -4.5))
        pen.line((0, 4.5), (0, 6))
        pen.rect(-4.5, -4.5, 9, 9)
        pen.line((-4.5, -1.5), (4.5, -1.5))
        pen.text(0, 1.6, "kWh", size=5.5)
        if self.direction == "import":
            pen.arrow((0, -4.1), (0, -1.9), head=0.9)
        elif self.direction == "export":
            pen.arrow((0, -1.9), (0, -4.1), head=0.9)
        else:
            pen.arrow((-1.5, -4.1), (-1.5, -1.9), head=0.9)
            pen.arrow((1.5, -1.9), (1.5, -4.1), head=0.9)
