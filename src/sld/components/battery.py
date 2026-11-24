from typing import Literal, Optional

from pydantic import Field

from sld.components._draw import battery_cells, inverter_box
from sld.components.base import Component, DrawContext, Kind
from sld.components.registry import register
from sld.util import fmt_num


@register("battery")
class Battery(Component):
    """Batteriespeicher, AC- oder DC-gekoppelt, optional mit integriertem Batteriewechselrichter."""

    kind = Kind.TERMINAL
    title = "Batteriespeicher"
    ref_letter = "G"
    size = (10.0, 12.0)

    kwh: float = Field(gt=0, description="Nutzbare Kapazität in kWh")
    kw: float = Field(gt=0, description="Lade-/Entladeleistung in kW")
    coupling: Literal["ac", "dc"] = Field("ac", description="Kopplung: ac | dc")
    inverter_kva: Optional[float] = Field(
        None, gt=0, description="Integrierter Batteriewechselrichter in kVA (wird mitgezeichnet)"
    )

    def is_dc_device(self) -> bool:
        return self.coupling == "dc" and self.inverter_kva is None

    def generation_kva(self, behind_inverter: bool = False) -> float:
        if self.inverter_kva:
            return self.inverter_kva
        return 0.0 if behind_inverter else self.kw

    def symbol_size(self) -> tuple[float, float]:
        return (10.0, 26.0) if self.inverter_kva else self.size

    def data_lines(self) -> list[str]:
        out = [f"{fmt_num(self.kwh)} kWh / {fmt_num(self.kw)} kW", f"{self.coupling.upper()}-gekoppelt"]
        if self.inverter_kva:
            out.append(f"BWR {fmt_num(self.inverter_kva)} kVA")
        return out

    def draw(self, pen, ctx: DrawContext) -> None:
        if self.inverter_kva:
            pen.line((0, -13), (0, -10))
            inverter_box(pen, -5)
            pen.line((0, 0), (0, 4))
            battery_cells(pen, 7)
        else:
            pen.line((0, -6), (0, -3))
            battery_cells(pen, 0)
