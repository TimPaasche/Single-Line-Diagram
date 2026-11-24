from sld.components.base import DrawContext
from sld.components.cable import ConductorBase
from sld.components.registry import register


@register("line")
class OverheadLine(ConductorBase):
    """Freileitung (Leitung mit Mastsymbol)."""

    title = "Freileitung"

    def draw(self, pen, ctx: DrawContext) -> None:
        pen.line((0, -6), (0, 6))
        pen.line((-2.6, -1.2), (2.6, -1.2))
        pen.circle(-2.6, -0.5, 0.45)
        pen.circle(2.6, -0.5, 0.45)
