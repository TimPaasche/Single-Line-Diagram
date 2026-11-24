from typing import Optional

from pydantic import Field

from sld.components.base import Component, DrawContext, Kind
from sld.components.registry import register
from sld.util import fmt_num


@register("load")
class Load(Component):
    """Verbraucher / Last (Pfeil)."""

    kind = Kind.TERMINAL
    title = "Verbraucher"
    ref_letter = "E"
    size = (6.0, 10.0)

    kw: Optional[float] = Field(None, gt=0, description="Wirkleistung in kW")
    cos_phi: Optional[float] = Field(None, gt=0, le=1, description="Leistungsfaktor")

    def data_lines(self) -> list[str]:
        out = []
        if self.kw:
            out.append(f"{fmt_num(self.kw)} kW")
        if self.cos_phi:
            out.append(f"cos φ = {fmt_num(self.cos_phi)}")
        return out

    def draw(self, pen, ctx: DrawContext) -> None:
        pen.line((0, -5), (0, 1))
        pen.polygon([(-2, 1), (2, 1), (0, 5)], fill="fg")
