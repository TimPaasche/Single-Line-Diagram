"""Gemeinsame Symbolteile (kein eigenes Bauteil, wird nicht registriert)."""


def inverter_box(pen, cy: float, s: float = 10.0) -> None:
    """Wechselrichter DIN EN 60617-6: Quadrat mit Diagonale, ~ oben links, = unten rechts."""
    h = s / 2
    pen.rect(-h, cy - h, s, s)
    pen.line((-h, cy + h), (h, cy - h))
    pen.sine(-s * 0.24, cy - s * 0.24, s * 0.32, s * 0.07)
    pen.dc_sign(s * 0.24, cy + s * 0.26, s * 0.32)


def battery_cells(pen, cy: float) -> None:
    """Akkumulator aus zwei Zellen (lange dünne Platte = Plus, kurze dicke = Minus)."""
    thick = pen.lw * 2.6
    for y in (cy - 3.0, cy + 1.2):
        pen.line((-4, y), (4, y))
        pen.line((-2, y + 1.8), (2, y + 1.8), width=thick)
    pen.line((0, cy - 1.2), (0, cy + 1.2), dash=(0.6, 0.6))


def rotating_machine(pen, letter: str) -> None:
    pen.circle(0, 0, 5)
    pen.text(0, -1.0, letter, size=9, bold=True)
    pen.sine(0, 2.4, 3.4, 0.6)
