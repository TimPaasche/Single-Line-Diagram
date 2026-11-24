from typing import Optional

from pydantic import Field

from sld.components._draw import rotating_machine
from sld.components.base import Component, DrawContext, Kind
from sld.components.registry import register
from sld.util import fmt_num


@register("generator")
class Generator(Component):
    """Synchron-/Asynchrongenerator (z. B. BHKW, Notstrom, Wind)."""

    kind = Kind.TERMINAL
    title = "Generator"
    ref_letter = "G"
    size = (10.0, 10.0)

    kva: float = Field(gt=0, description="Bemessungsleistung in kVA")
    gen_type: Optional[str] = Field(None, description="Art, z. B. BHKW, Diesel, Wind")

    def generation_kva(self, behind_inverter: bool = False) -> float:
        return self.kva

    def data_lines(self) -> list[str]:
        out = [f"{fmt_num(self.kva)} kVA"]
        if self.gen_type:
            out.append(self.gen_type)
        return out

    def draw(self, pen, ctx: DrawContext) -> None:
        rotating_machine(pen, "G")
