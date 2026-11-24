"""Zeilenzuordnung für Formate ohne Positionsinfo im Parser (JSON, TOML).

Sucht die Knoten- und Verbindungseinträge der Reihe nach im Quelltext.
Das ist eine Heuristik: Sie findet die Zeile, in der die ID bzw. das
'from' einer Verbindung steht.
"""

from __future__ import annotations

import re

from sld.schema.issues import SourceMap


def _find(lines: list[str], pattern: re.Pattern, start: int) -> int | None:
    for i in range(start, len(lines)):
        if pattern.search(lines[i]):
            return i
    return None


def scan(text: str, data: object, source: SourceMap) -> None:
    if not isinstance(data, dict):
        return
    lines = text.splitlines()
    for top in data:
        pat = re.compile(rf'^\s*(\[\[?\s*)?"?{re.escape(str(top))}"?\s*(\]\]?|[:=])')
        hit = _find(lines, pat, 0)
        if hit is not None:
            source.lines[(top,)] = hit + 1
    cursor = 0
    for i, node in enumerate(data.get("nodes") or []):
        if isinstance(node, dict) and isinstance(node.get("id"), str):
            pat = re.compile(rf'"?id"?\s*[:=]\s*["\']{re.escape(node["id"])}["\']')
            hit = _find(lines, pat, cursor)
            if hit is not None:
                source.lines[("nodes", i)] = hit + 1
                cursor = hit + 1
    cursor = 0
    for i, conn in enumerate(data.get("connections") or []):
        if isinstance(conn, dict) and isinstance(conn.get("from"), str):
            pat = re.compile(rf'"?from"?\s*[:=]\s*["\']{re.escape(conn["from"])}["\']')
            hit = _find(lines, pat, cursor)
            if hit is not None:
                source.lines[("connections", i)] = hit + 1
                cursor = hit + 1
