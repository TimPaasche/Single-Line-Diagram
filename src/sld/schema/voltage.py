"""Spannungsebenen: Ableitung und Konsistenzprüfung.

Elemente ohne Transformator/Wechselrichter dazwischen bilden ein Segment mit
genau einer Spannungsebene. Transformatoren verbinden zwei AC-Segmente gemäß
ihrem Spannungsverhältnis, Wechselrichter trennen AC (oben) von DC (unten).
"""

from __future__ import annotations

from typing import Optional

from sld.schema.issues import Issue, error
from sld.schema.topology import Topology
from sld.util import DC, Level, fmt_kv, fmt_level, same_voltage


class _UnionFind:
    def __init__(self) -> None:
        self.p: dict[str, str] = {}

    def find(self, x: str) -> str:
        self.p.setdefault(x, x)
        while self.p[x] != x:
            self.p[x] = self.p[self.p[x]]
            x = self.p[x]
        return x

    def union(self, a: str, b: str) -> None:
        self.p[self.find(a)] = self.find(b)


def _is_boundary(c) -> bool:
    return c.is_transformer or c.is_inverter or c.is_grounding


def analyze_voltages(topo: Topology) -> tuple[dict[str, Optional[Level]], list[Issue]]:
    els = topo.elements
    issues: list[Issue] = []
    uf = _UnionFind()
    for e, c in els.items():
        if not _is_boundary(c):
            uf.find(e)
    for e, nbrs in topo.adjacency.items():
        if _is_boundary(els[e]):
            continue
        for n in nbrs:
            if not _is_boundary(els[n]):
                uf.union(e, n)

    value: dict[str, Level] = {}
    source: dict[str, str] = {}
    has_dc: set[str] = set()
    for e, c in els.items():
        if _is_boundary(c):
            continue
        seg = uf.find(e)
        if c.is_dc_device():
            has_dc.add(seg)
        v = c.explicit_voltage()
        if v is None:
            continue
        if seg not in value:
            value[seg], source[seg] = v, e
        elif not same_voltage(float(value[seg]), v):
            issues.append(
                error(
                    "E007",
                    f"Spannungswechsel ohne Transformator: '{source[seg]}' hat {fmt_kv(float(value[seg]))}, "
                    f"'{e}' hat {fmt_kv(v)}, beide liegen auf derselben Ebene",
                    node_id=e,
                )
            )

    def seg_of(e: str) -> Optional[str]:
        return None if _is_boundary(els[e]) else uf.find(e)

    # DC-Seite der Wechselrichter
    for e, c in els.items():
        if c.is_inverter:
            for ch in topo.children.get(e, []):
                s = seg_of(ch)
                if s is not None and s not in value:
                    value[s] = DC
    for s in has_dc:
        value.setdefault(s, DC)

    # Transformatoren: Seiten aus dem Spannungsverhältnis ableiten und prüfen
    checked: set[str] = set()
    changed = True
    while changed:
        changed = False
        for e, c in els.items():
            if not c.is_transformer or e in checked:
                continue
            ratio = c.voltages()
            segs = list(dict.fromkeys(s for n in topo.neighbors(e) if (s := seg_of(n)) is not None and not els[n].is_grounding))
            if ratio is None or len(segs) != 2:
                continue
            known = [value.get(s) for s in segs]
            if any(k == DC for k in known):
                issues.append(error("E008", "Transformator ist an eine DC-Ebene angeschlossen", node_id=e))
                checked.add(e)
                continue
            if known[0] is not None and known[1] is not None:
                a, b = float(known[0]), float(known[1])
                ok = (same_voltage(a, ratio[0]) and same_voltage(b, ratio[1])) or (
                    same_voltage(a, ratio[1]) and same_voltage(b, ratio[0])
                )
                if not ok:
                    issues.append(
                        error(
                            "E008",
                            f"Spannungsverhältnis {fmt_num_ratio(ratio)} passt nicht zu den angeschlossenen Ebenen "
                            f"{fmt_kv(a)} und {fmt_kv(b)}",
                            node_id=e,
                        )
                    )
                checked.add(e)
            elif known[0] is not None or known[1] is not None:
                i_known = 0 if known[0] is not None else 1
                k = float(known[i_known])  # type: ignore[arg-type]
                if same_voltage(k, ratio[0]):
                    other = ratio[1]
                elif same_voltage(k, ratio[1]):
                    other = ratio[0]
                else:
                    issues.append(
                        error(
                            "E008",
                            f"Spannungsverhältnis {fmt_num_ratio(ratio)} passt nicht zur angeschlossenen Ebene {fmt_kv(k)}",
                            node_id=e,
                        )
                    )
                    checked.add(e)
                    continue
                value[segs[1 - i_known]] = other
                checked.add(e)
                changed = True

    levels: dict[str, Optional[Level]] = {}
    for e in els:
        s = seg_of(e)
        levels[e] = value.get(s) if s is not None else None
    return levels, issues


def fmt_num_ratio(ratio: tuple[float, float]) -> str:
    return f"{fmt_level(ratio[0]).removesuffix(' kV')}/{fmt_level(ratio[1])}"
