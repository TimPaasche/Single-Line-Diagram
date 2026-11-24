from typing import Optional

from pydantic import Field

from sld.components.base import Component, DrawContext, Kind
from sld.components.registry import register
from sld.util import fmt_num


@register("grounding")
class Grounding(Component):
    """Erdung (DIN EN 60617-2)."""

    kind = Kind.TERMINAL
    title = "Erdung"
    ref_letter = "PE"
    size = (8.0, 8.0)
    is_grounding = True

    system: Optional[str] = Field(None, description="Netzsystem / Erdungsart, z. B. TN-C-S")
    resistance_ohm: Optional[float] = Field(None, gt=0, description="Erdungswiderstand in Ohm")

    def data_lines(self) -> list[str]:
        out = []
        if self.system:
            out.append(self.system)
        if self.resistance_ohm:
            out.append(f"RE = {fmt_num(self.resistance_ohm)} Ω")
        return out

    def draw(self, pen, ctx: DrawContext) -> None:
        pen.line((0, -4), (0, 0.5))
        for y, w in ((0.5, 3.5), (2.0, 2.3), (3.5, 1.1)):
            pen.line((-w, y), (w, y))
