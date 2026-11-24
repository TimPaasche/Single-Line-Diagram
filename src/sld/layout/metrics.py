"""Textvermessung in mm. Das Layout braucht Textgrößen, ohne vom Zeichen-Backend abzuhängen."""

from __future__ import annotations

from typing import Protocol

MM_PER_PT = 25.4 / 72.0
LINE_SPACING = 1.25


class TextMetrics(Protocol):
    def width(self, text: str, size: float, bold: bool = False) -> float: ...

    def line_height(self, size: float) -> float: ...


# Zeichenbreiten von DejaVu Sans in em (gerundet). Unbekannte Zeichen nutzen DEFAULT_EM.
_EM: dict[str, float] = {}
_EM.update(dict.fromkeys("0123456789", 0.637))
_EM.update(dict.fromkeys("ijlI|'!.,:;", 0.30))
_EM.update(dict.fromkeys(" ", 0.32))
_EM.update(dict.fromkeys("frt()[]-/\\", 0.42))
_EM.update(dict.fromkeys("abcdeghknopqsuvxyzJ", 0.63))
_EM.update(dict.fromkeys("mwMW%", 1.0))
_EM.update(dict.fromkeys("ABCDEFGHKLNOPQRSTUVXYZÄÖÜ", 0.78))
_EM.update(dict.fromkeys("äöüß", 0.63))
_EM.update({"×": 0.84, "~": 0.84, "″": 0.45, "²": 0.40, "=": 0.84, "+": 0.84, "_": 0.5})
DEFAULT_EM = 0.70


class HeuristicMetrics:
    """Konservative Schätzung (eher zu breit), damit Labels sicher nicht überlappen."""

    def width(self, text: str, size: float, bold: bool = False) -> float:
        em = sum(_EM.get(ch, DEFAULT_EM) for ch in text)
        factor = 1.12 if bold else 1.0
        return em * size * MM_PER_PT * factor * 1.03

    def line_height(self, size: float) -> float:
        return size * MM_PER_PT * LINE_SPACING
