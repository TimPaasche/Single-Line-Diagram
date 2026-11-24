from sld.components.base import DrawContext, SwitchingDevice
from sld.components.registry import register


def draw_contact(pen, closed: bool) -> None:
    """Schließer: Festkontakt bei y=-2, Drehpunkt bei y=+3."""
    pen.line((0, -6), (0, -2))
    pen.line((0, 3), (0, 6))
    if closed:
        pen.line((0, 3), (0, -2))
    else:
        pen.line((0, 3), (-3.2, -1.4))


@register("circuit_breaker")
class CircuitBreaker(SwitchingDevice):
    """Leistungsschalter (DIN EN 60617-7: Schaltglied mit Kreuz am Festkontakt)."""

    title = "Leistungsschalter"
    ref_letter = "Q"

    def draw(self, pen, ctx: DrawContext) -> None:
        draw_contact(pen, closed=not self.is_open())
        pen.line((-1, -3), (1, -1))
        pen.line((-1, -1), (1, -3))
