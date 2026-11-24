from typing import Optional

from pydantic import Field

from sld.components.base import Component, DrawContext, Kind
from sld.components.registry import register
from sld.util import fmt_num


@register("pv_array")
class PVArray(Component):
    """PV-Generator (Modulfeld), DC-seitig an einen Wechselrichter angeschlossen."""

    kind = Kind.TERMINAL
    title = "PV-Generator"
    ref_letter = "G"
    size = (12.0, 14.0)

    kwp: float = Field(gt=0, description="Nennleistung in kWp")
    strings: Optional[int] = Field(None, ge=1, description="Anzahl Strings")
    modules: Optional[int] = Field(None, ge=1, description="Anzahl Module")

    def is_dc_device(self) -> bool:
        return True

    def generation_kva(self, behind_inverter: bool = False) -> float:
        return 0.0 if behind_inverter else self.kwp

    def data_lines(self) -> list[str]:
        out = [f"{fmt_num(self.kwp)} kWp"]
        extra = []
        if self.strings:
            extra.append(f"{self.strings} Strings")
        if self.modules:
            extra.append(f"{self.modules} Module")
        if extra:
            out.append(", ".join(extra))
        return out

    def draw(self, pen, ctx: DrawContext) -> None:
        pen.line((0, -7), (0, -5))
        pen.rect(-5, -5, 10, 10)
        pen.line((-5, 5), (5, -5))
        pen.arrow((-4.3, -1.6), (-2.4, 0.3), head=1.0)
        pen.arrow((-1.6, -4.3), (0.3, -2.4), head=1.0)
        pen.dc_sign(2.4, 2.6, 3.2)
