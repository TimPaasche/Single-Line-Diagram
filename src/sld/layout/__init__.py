"""Automatisches Layout (Geometrie), getrennt vom Zeichnen."""

from sld.layout.engine import compute_layout
from sld.layout.metrics import HeuristicMetrics, TextMetrics
from sld.layout.model import Band, Box, Layout, PlacedLabel, PlacedSymbol, Table, TextLine, TitleBlock, Wire

__all__ = [
    "Band",
    "Box",
    "HeuristicMetrics",
    "Layout",
    "PlacedLabel",
    "PlacedSymbol",
    "Table",
    "TextLine",
    "TextMetrics",
    "TitleBlock",
    "Wire",
    "compute_layout",
]
