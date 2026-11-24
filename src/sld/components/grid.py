from typing import Optional

from pydantic import Field

from sld.components.base import Component, DrawContext, Kind
from sld.components.registry import register
from sld.util import fmt_kv, fmt_num


@register("grid")
class Grid(Component):
    """Netz / Netzanschlusspunkt: Einspeisung aus dem vorgelagerten Netz."""

    kind = Kind.SOURCE
    title = "Netz / Netzanschlusspunkt"
    ref_letter = "N"
    size = (16.0, 10.0)

    voltage_kv: float = Field(gt=0, description="Nennspannung in kV")
    sk_mva: Optional[float] = Field(None, gt=0, description="Kurzschlussleistung S''k in MVA")

    def explicit_voltage(self) -> Optional[float]:
        return self.voltage_kv

    def data_lines(self) -> list[str]:
        out = [fmt_kv(self.voltage_kv)]
        if self.sk_mva:
            out.append(f"S″k = {fmt_num(self.sk_mva)} MVA")
        return out

    def draw(self, pen, ctx: DrawContext) -> None:
        # Netzeinspeisung: schraffiertes Rechteck, Anschluss unten
        pen.rect(-8, -5, 16, 10)
        pen.hatch(-8, -5, 16, 10, spacing=2.2)
