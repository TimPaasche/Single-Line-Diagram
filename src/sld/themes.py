"""Darstellungs-Themes. Die Symbole folgen immer DIN EN 60617; Themes ändern nur den Stil."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Theme:
    name: str
    line_color: str = "black"
    text_color: str = "black"
    background: str = "white"
    line_width: float = 0.35  # mm
    bus_width: float = 1.0  # mm
    font_family: str = "DejaVu Sans"
    band_fills: tuple[str, ...] = ()
    band_line: str | None = None
    band_text: str = "#555555"
    frame: bool = False
    title_block: bool = False
    title_in_header: bool = True
    margin: float = 10.0  # mm


THEMES: dict[str, Theme] = {
    "din": Theme(
        name="din",
        band_line="#8a8a8a",
        frame=True,
        title_block=True,
        title_in_header=False,
        margin=15.0,
    ),
    "simple": Theme(
        name="simple",
        line_color="#1f2937",
        text_color="#111827",
        line_width=0.3,
        bus_width=1.1,
        band_fills=("#e8f1fb", "#fdf1e1", "#e9f6e7", "#f4e9f7", "#f1f1f1"),
        band_text="#374151",
    ),
}


def get_theme(name: str) -> Theme:
    try:
        return THEMES[name]
    except KeyError:
        raise ValueError(f"Unbekanntes Theme '{name}'. Verfügbar: {', '.join(THEMES)}") from None
