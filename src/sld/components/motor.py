from typing import Optional

from pydantic import Field

from sld.components._draw import rotating_machine
from sld.components.base import Component, DrawContext, Kind
from sld.components.registry import register
from sld.util import fmt_num


@register("motor")
class Motor(Component):
    """Drehstrommotor."""

    kind = Kind.TERMINAL
    title = "Motor"
    ref_letter = "M"
    size = (10.0, 10.0)

    kw: float = Field(gt=0, description="Bemessungsleistung in kW")
    starter: Optional[str] = Field(None, description="Anlaufart, z. B. DOL, Stern-Dreieck, FU")

    def data_lines(self) -> list[str]:
        out = [f"{fmt_num(self.kw)} kW"]
        if self.starter:
            out.append(self.starter)
        return out

    def draw(self, pen, ctx: DrawContext) -> None:
        rotating_machine(pen, "M")
