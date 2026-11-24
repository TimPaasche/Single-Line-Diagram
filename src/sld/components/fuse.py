from typing import Optional

from pydantic import Field

from sld.components.base import DrawContext, SwitchingDevice
from sld.components.registry import register


@register("fuse")
class Fuse(SwitchingDevice):
    """Sicherung (Rechteck mit durchgehender Linie). state: open = Einsatz gezogen."""

    title = "Sicherung"
    ref_letter = "F"
    size = (5.0, 12.0)

    fuse_type: Optional[str] = Field(None, description="Bauart / Betriebsklasse, z. B. 'NH2 gG'")

    def data_lines(self) -> list[str]:
        out = super().data_lines()
        if self.fuse_type:
            out.insert(0, self.fuse_type)
        return out

    def draw(self, pen, ctx: DrawContext) -> None:
        pen.rect(-1.5, -4.5, 3, 9)
        if self.is_open():
            pen.line((0, -6), (0, -4.5))
            pen.line((0, 4.5), (0, 6))
        else:
            pen.line((0, -6), (0, 6))
