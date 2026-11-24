from pydantic import Field

from sld.components.base import Component, DrawContext, Kind
from sld.components.registry import register
from sld.util import fmt_num


@register("ev_charger")
class EVCharger(Component):
    """Ladeeinrichtung für Elektrofahrzeuge (Wallbox / Ladesäule)."""

    kind = Kind.TERMINAL
    title = "Ladeeinrichtung (Wallbox)"
    ref_letter = "E"
    size = (10.0, 12.0)

    kw: float = Field(gt=0, description="Ladeleistung je Ladepunkt in kW")
    points: int = Field(1, ge=1, description="Anzahl Ladepunkte")

    def data_lines(self) -> list[str]:
        if self.points == 1:
            return [f"{fmt_num(self.kw)} kW"]
        return [f"{self.points} × {fmt_num(self.kw)} kW"]

    def draw(self, pen, ctx: DrawContext) -> None:
        pen.line((0, -6), (0, -4))
        pen.rect(-5, -4, 10, 10)
        bolt = [(1.0, -3.0), (-1.8, 1.4), (0.0, 1.4), (-1.0, 5.0), (2.0, 0.0), (0.2, 0.0), (1.4, -3.0)]
        pen.polygon(bolt, fill="fg", width=pen.lw * 0.5)
