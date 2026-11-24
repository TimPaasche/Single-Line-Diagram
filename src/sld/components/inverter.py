from typing import Literal

from pydantic import Field

from sld.components._draw import inverter_box
from sld.components.base import Component, DrawContext, Kind
from sld.components.registry import register
from sld.util import fmt_num

_TYPES = {"string": "String-WR", "central": "Zentral-WR", "hybrid": "Hybrid-WR"}


@register("inverter")
class Inverter(Component):
    """Wechselrichter: AC-Seite oben (Netz), DC-Seite unten (PV / DC-Speicher)."""

    kind = Kind.SERIES
    title = "Wechselrichter"
    ref_letter = "T"
    size = (10.0, 14.0)
    max_connections = 99  # ein AC-Anschluss, beliebig viele DC-Eingänge
    is_inverter = True

    kva: float = Field(gt=0, description="Bemessungsleistung je Gerät in kVA")
    inverter_type: Literal["string", "central", "hybrid"] = Field(
        "string", description="Bauart: string | central (zentral) | hybrid"
    )
    count: int = Field(1, ge=1, description="Anzahl gleicher Geräte (als ein Symbol dargestellt)")

    def generation_kva(self, behind_inverter: bool = False) -> float:
        return self.kva * self.count

    def data_lines(self) -> list[str]:
        power = f"{fmt_num(self.kva)} kVA" if self.count == 1 else f"{self.count} × {fmt_num(self.kva)} kVA"
        return [power, _TYPES[self.inverter_type]]

    def draw(self, pen, ctx: DrawContext) -> None:
        pen.line((0, -7), (0, -5))
        pen.line((0, 5), (0, 7))
        inverter_box(pen, 0)
