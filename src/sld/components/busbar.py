from typing import Optional

from pydantic import Field

from sld.components.base import Component, DrawContext, Kind
from sld.components.registry import register
from sld.util import fmt_kv


@register("busbar")
class Busbar(Component):
    """Sammelschiene einer Spannungsebene (waagerecht, Abgänge senkrecht)."""

    kind = Kind.BUS
    title = "Sammelschiene"
    ref_letter = "W"
    size = (24.0, 1.0)

    voltage_kv: Optional[float] = Field(None, gt=0, description="Nennspannung in kV (sonst aus Nachbarn abgeleitet)")

    def explicit_voltage(self) -> Optional[float]:
        return self.voltage_kv

    def data_lines(self) -> list[str]:
        return [fmt_kv(self.voltage_kv)] if self.voltage_kv else []

    def draw(self, pen, ctx: DrawContext) -> None:
        x0, x1 = ctx.span or (-self.size[0] / 2, self.size[0] / 2)
        pen.line((x0, 0), (x1, 0), width=ctx.theme.bus_width)
