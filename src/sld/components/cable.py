from typing import Optional

from pydantic import Field

from sld.components.base import Component, DrawContext, Kind
from sld.components.registry import register
from sld.util import fmt_num


class ConductorBase(Component):
    """Gemeinsame Felder für Kabel und Freileitung (nicht registriert)."""

    kind = Kind.SERIES
    ref_letter = "W"
    size = (6.0, 12.0)

    length_m: Optional[float] = Field(None, gt=0, description="Länge in m")
    cross_section_mm2: Optional[float] = Field(None, gt=0, description="Leiterquerschnitt in mm²")
    conductors: Optional[str] = Field(None, description="Aderzahl-Präfix, z. B. '3×1×' oder '4×'")
    designation: Optional[str] = Field(None, description="Typbezeichnung, z. B. NA2XS2Y")

    def data_lines(self) -> list[str]:
        out = []
        spec = " ".join(
            part
            for part in (
                self.designation,
                f"{self.conductors or ''}{fmt_num(self.cross_section_mm2)} mm²" if self.cross_section_mm2 else None,
            )
            if part
        )
        if spec:
            out.append(spec)
        if self.length_m:
            out.append(f"{fmt_num(self.length_m / 1000)} km" if self.length_m >= 1000 else f"{fmt_num(self.length_m)} m")
        return out


@register("cable")
class Cable(ConductorBase):
    """Kabel (Leitung mit Mantelkennzeichnung)."""

    title = "Kabel"

    def draw(self, pen, ctx: DrawContext) -> None:
        pen.line((0, -6), (0, 6))
        pen.ellipse(0, 0, 2.2, 1.1)
