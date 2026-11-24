from sld.components.base import DrawContext, SwitchingDevice
from sld.components.circuit_breaker import draw_contact
from sld.components.registry import register


@register("switch_disconnector")
class SwitchDisconnector(SwitchingDevice):
    """Lasttrennschalter (Trennstrich und Lastschalt-Kreis am Festkontakt)."""

    title = "Lasttrennschalter"
    ref_letter = "Q"

    def draw(self, pen, ctx: DrawContext) -> None:
        draw_contact(pen, closed=not self.is_open())
        pen.line((-1.3, -2), (1.3, -2))
        pen.circle(0, -2.8, 0.7, fill="bg")
