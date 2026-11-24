"""Kleine Hilfsfunktionen (Zahlenformatierung im deutschen Stil)."""

from __future__ import annotations

from typing import Union

Level = Union[float, str]
"""Spannungsebene: Nennspannung in kV oder ``"DC"``."""

DC = "DC"


def fmt_num(value: float, max_decimals: int = 3) -> str:
    """Formatiert eine Zahl mit Dezimalkomma und ohne überflüssige Nullen."""
    if float(value).is_integer():
        text = str(int(value))
    else:
        text = f"{value:.{max_decimals}f}".rstrip("0").rstrip(".")
    return text.replace(".", ",")


def fmt_kv(kv: float) -> str:
    return f"{fmt_num(kv)} kV"


def fmt_level(level: Level) -> str:
    return DC if level == DC else fmt_kv(float(level))


def same_voltage(a: float, b: float, rel_tol: float = 0.01) -> bool:
    return abs(a - b) <= rel_tol * max(abs(a), abs(b))
