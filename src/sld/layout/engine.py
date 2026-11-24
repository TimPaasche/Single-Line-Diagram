"""Automatisches Layout.

Ablauf:
1. Spannbaum ab den Netzanschlüssen (Netz oben, Erzeuger/Verbraucher unten).
2. Teilbaum-Breiten bottom-up inkl. Beschriftungen bestimmen. Geschwister liegen
   nebeneinander, ohne dass sich ihre Hüllintervalle überlappen. Damit können sich
   Labels konstruktionsbedingt nicht überschneiden.
3. Vertikale Lage top-down. Sammelschienen gleicher Spannungsebene werden auf
   eine Höhe gebracht (Spannungsebenen als Bänder).
4. Layout-Hinweise anwenden (``order`` wirkt schon in der Topologie, ``pos`` hier).
5. Kupplungen (Ring schließende Verbindungen) führen, Leitungen, Labels,
   Kollisionsprüfung, Bänder, Stückliste, Schriftfeld.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from typing import Iterator, Optional

from sld.components import Component, Kind
from sld.layout.metrics import HeuristicMetrics, TextMetrics
from sld.layout.model import (
    Band,
    Box,
    Layout,
    PlacedLabel,
    PlacedSymbol,
    Point,
    Table,
    TextLine,
    TitleBlock,
    TitleBlockCell,
    Wire,
)
from sld.schema.issues import Issue, warning
from sld.schema.topology import Chain, build_topology
from sld.schema.voltage import analyze_voltages
from sld.themes import Theme, get_theme
from sld.util import fmt_level

# Schriftgrößen in pt
NAME_SIZE = 7.0
DATA_SIZE = 6.5
BAND_SIZE = 7.5
TITLE_SIZE = 13.0
SUBTITLE_SIZE = 8.0
TABLE_SIZE = 6.0

# Maximale Spaltenbreiten der Stückliste in mm (Umbruch)
TABLE_NAME_W = 35.0
TABLE_TEXT_W = 40.0
TABLE_DATA_W = 55.0

# Blattformate (Breite x Höhe hochkant) in mm, kleinstes zuerst
PAPER_SIZES = {"A5": (148.0, 210.0), "A4": (210.0, 297.0), "A3": (297.0, 420.0)}
FRAME_LEFT = 20.0  # Heftrand (DIN EN ISO 5457)
FRAME_OTHER = 10.0
FRAME_PAD = 5.0
TB_GAP = 4.0

# Abstände in mm
GAP_WIRE = 5.0
GAP_BUS_CHILD = 7.0
SIBLING_GAP = 6.0
ROOT_GAP = 16.0
BUS_OVERHANG = 6.0
BUS_MIN = 24.0
LABEL_GAP = 1.8
TIE_MARGIN = 3.0
TIE_WIRE = 4.0
TIE_DROP = 10.0
BUS_EXT = 4.0

LabelSpec = list[tuple[str, float, bool]]  # (Text, Größe, fett)


class _N:
    """Arbeitsknoten des Layouts."""

    def __init__(self, eid: str, comp: Optional[Component]):
        self.id = eid
        self.comp = comp
        self.w, self.h = comp.symbol_size() if comp is not None else (0.0, 0.0)
        self.children: list[_N] = []
        self.parent: Optional[_N] = None
        self.lines: LabelSpec = []
        self.lw = self.lh = 0.0
        self.gaps: dict[int, float] = {}
        self.offsets: list[float] = []
        self.own_left = self.own_right = self.sub_left = self.sub_right = 0.0
        self.extra_right = 0.0
        self.bar = (0.0, 0.0)
        self.label_side = "left"
        self.tie_left = self.tie_right = False
        self.x = self.cy = self.slot_bottom = 0.0
        self.junction_y: Optional[float] = None
        self.span: Optional[tuple[float, float]] = None

    @property
    def is_bus(self) -> bool:
        return self.comp is not None and self.comp.kind == Kind.BUS

    @property
    def top(self) -> float:
        return self.cy if self.is_bus else self.cy - self.h / 2

    @property
    def bottom(self) -> float:
        return self.cy if self.is_bus else self.cy + self.h / 2

    def walk(self) -> Iterator["_N"]:
        stack = [self]
        while stack:
            cur = stack.pop()
            yield cur
            stack.extend(reversed(cur.children))


@dataclass
class _Tie:
    chain: Chain
    a: _N
    b: _N
    vias: list[_N]
    mode: str = "fallback"  # adjacent | feeder | fallback
    ca: Optional[_N] = None
    cb: Optional[_N] = None


@dataclass
class _LabelReq:
    owner: str
    kind: str
    lines: LabelSpec
    width: float
    height: float
    candidates: list[tuple[float, float, str]] = field(default_factory=list)  # (x0, top, ha)


class LayoutEngine:
    def __init__(
        self,
        diagram,
        metrics: Optional[TextMetrics] = None,
        theme: Optional[Theme] = None,
        paper: Optional[str] = None,
        orientation: Optional[str] = None,
    ):
        self.d = diagram
        self.m: TextMetrics = metrics or HeuristicMetrics()
        meta = diagram.diagram
        self.theme = theme or get_theme(meta.theme)
        self.detail = meta.label_detail
        self.show_ids = meta.show_ids
        self.label_width = meta.label_width_mm
        self.paper = paper or meta.paper
        self.orientation = orientation or meta.orientation
        self.warnings: list[Issue] = []

    # ------------------------------------------------------------------ Text
    def _label_spec(self, comp: Component) -> LabelSpec:
        lines: LabelSpec = []
        if self.show_ids and comp.id:
            lines.append((comp.id, NAME_SIZE, True))
        if comp.name:
            lines.append((comp.name, NAME_SIZE, True))
        if self.detail != "id":
            if comp.label:
                lines.append((comp.label, DATA_SIZE, False))
            data = comp.data_lines()
            if self.detail == "short":
                data = data[:1]
            lines += [(t, DATA_SIZE, False) for t in data]
        return self._wrap_spec(lines, self.label_width)

    def _wrap(self, text: str, size: float, bold: bool, max_w: float) -> list[str]:
        """Bricht Text an Leerzeichen (und expliziten Zeilenumbrüchen) auf max_w mm um."""
        out: list[str] = []
        for para in str(text).split("\n"):
            if max_w <= 0:
                out.append(para)
                continue
            cur = ""
            for word in para.split():
                cand = f"{cur} {word}" if cur else word
                if cur and self.m.width(cand, size, bold) > max_w:
                    out.append(cur)
                    cur = word
                else:
                    cur = cand
            out.append(cur)
        return out

    def _wrap_spec(self, spec: LabelSpec, max_w: float) -> LabelSpec:
        return [(part, size, bold) for text, size, bold in spec for part in self._wrap(text, size, bold, max_w)]

    def _measure_spec(self, spec: LabelSpec) -> tuple[float, float]:
        if not spec:
            return 0.0, 0.0
        w = max(self.m.width(t, s, b) for t, s, b in spec)
        h = sum(self.m.line_height(s) for _, s, _ in spec)
        return w, h

    def _make_label(self, owner: str, kind: str, spec: LabelSpec, x0: float, top: float, ha: str = "left") -> PlacedLabel:
        w, _ = self._measure_spec(spec)
        lines, y = [], top
        for text, size, bold in spec:
            lh = self.m.line_height(size)
            x = x0 if ha == "left" else x0 + w / 2
            lines.append(TextLine(text, x, y + lh / 2, size, bold, ha))
            y += lh
        return PlacedLabel(owner, kind, lines, Box(x0, top, x0 + w, y))

    def _new_node(self, eid: str) -> _N:
        n = _N(eid, self.topo.elements[eid])
        n.lines = self._label_spec(n.comp)
        n.lw, n.lh = self._measure_spec(n.lines)
        return n

    # ------------------------------------------------------------------ Baum
    def _build(self, eid: str, parent: _N) -> _N:
        n = self._new_node(eid)
        n.parent = parent
        self.nodes[eid] = n
        for c in self.topo.children.get(eid, []):
            n.children.append(self._build(c, n))
        return n

    def _path_up(self, n: _N) -> list[_N]:
        out = [n]
        while out[-1].parent is not None:
            out.append(out[-1].parent)
        return out

    def _plan_ties(self) -> list[_Tie]:
        ties = []
        for ch in self.topo.ties:
            a, b = (self.nodes.get(e) for e in ch.ends)
            if a is None or b is None:
                continue
            vias = [self._new_node(v) for v in ch.ids[1:-1]]
            tie = _Tie(ch, a, b, vias)
            ties.append(tie)
            src = next((x for x in (a, b) if x.comp.kind == Kind.SOURCE and not x.children), None)
            other = b if src is a else a
            if src is not None and other.is_bus:
                if src is b:
                    tie.a, tie.b, tie.vias = b, a, list(reversed(vias))
                tie.mode = "feeder"
                src.extra_right = max((v.w / 2 + LABEL_GAP + v.lw for v in vias), default=0.0)
                continue
            if a.is_bus and b.is_bus:
                pa, pb = self._path_up(a), self._path_up(b)
                ids_a = {id(x) for x in pa}
                lca = next(x for x in pb if id(x) in ids_a)
                if lca is not a and lca is not b:
                    ca = pa[[id(x) for x in pa].index(id(lca)) - 1]
                    cb = pb[[id(x) for x in pb].index(id(lca)) - 1]
                    ia, ib = lca.children.index(ca), lca.children.index(cb)
                    if abs(ia - ib) == 1:
                        if ia > ib:
                            a, b, ca, cb, vias = b, a, cb, ca, list(reversed(vias))
                        run = sum(max(v.h, v.lw) + TIE_WIRE for v in vias)
                        gap = 2 * TIE_MARGIN + 2 * TIE_WIRE + run
                        k = max(ia, ib)
                        lca.gaps[k] = max(lca.gaps.get(k, SIBLING_GAP), gap)
                        tie.a, tie.b, tie.ca, tie.cb, tie.vias, tie.mode = a, b, ca, cb, vias, "adjacent"
                        a.tie_right = True
                        b.tie_left = True
                        continue
            self.warnings.append(
                warning(
                    "W107",
                    f"Kupplung '{ch.ends[0]}' <-> '{ch.ends[1]}' wird unterhalb des Plans geführt "
                    "und kann andere Leitungen kreuzen",
                    path=("connections", ch.index),
                )
            )
        for n in self.nodes.values():
            if n.is_bus and n.tie_left and not n.tie_right:
                n.label_side = "right"
        return ties

    # ------------------------------------------------------------- Horizontal
    def _measure(self, n: _N) -> None:
        for c in n.children:
            self._measure(c)
        if n.comp is not None and not n.is_bus:
            n.own_left = n.w / 2
            n.own_right = max(n.w / 2 + (LABEL_GAP + n.lw if n.lw else 0.0), n.extra_right)
        offs: list[float] = []
        for i, c in enumerate(n.children):
            if i == 0:
                offs.append(0.0)
            else:
                gap = n.gaps.get(i, ROOT_GAP if n.comp is None else SIBLING_GAP)
                offs.append(offs[-1] + n.children[i - 1].sub_right + gap + c.sub_left)
        if offs:
            anchor = (offs[0] + offs[-1]) / 2
            n.offsets = [o - anchor for o in offs]
        if n.is_bus:
            if n.offsets:
                left, right = n.offsets[0] - BUS_OVERHANG, n.offsets[-1] + BUS_OVERHANG
            else:
                left, right = -BUS_MIN / 2, BUS_MIN / 2
            if right - left < BUS_MIN:
                pad = (BUS_MIN - (right - left)) / 2
                left, right = left - pad, right + pad
            n.bar = (left, right)
            lab = LABEL_GAP + n.lw if n.lw else 0.0
            n.own_left = -left + (lab if n.label_side == "left" else 0.0)
            n.own_right = right + (lab if n.label_side == "right" else 0.0)
        n.sub_left = max([n.own_left] + [-o + c.sub_left for o, c in zip(n.offsets, n.children)])
        n.sub_right = max([n.own_right] + [o + c.sub_right for o, c in zip(n.offsets, n.children)])

    def _place(self, n: _N, x: float) -> None:
        n.x = x
        for o, c in zip(n.offsets, n.children):
            self._place(c, x + o)

    # --------------------------------------------------------------- Vertikal
    def _assign_y(self, n: _N, ytop: float) -> None:
        if n.is_bus:
            half = max(1.0, n.lh / 2)
            n.cy = ytop + half
            n.slot_bottom = n.cy + half
            child_top = n.cy + max(GAP_BUS_CHILD, half + 2.5)
        else:
            slot = max(n.h, n.lh)
            n.cy = ytop + slot / 2
            n.slot_bottom = ytop + slot
            if len(n.children) > 1:
                n.junction_y = n.slot_bottom + GAP_WIRE * 0.6
                child_top = n.junction_y + GAP_WIRE
            else:
                child_top = n.slot_bottom + GAP_WIRE
        for c in n.children:
            self._assign_y(c, child_top)

    @staticmethod
    def _shift(n: _N, dx: float, dy: float) -> None:
        for d in n.walk():
            d.x += dx
            d.cy += dy
            d.slot_bottom += dy
            if d.junction_y is not None:
                d.junction_y += dy

    def _align_buses(self) -> None:
        groups: dict[tuple, list[_N]] = defaultdict(list)
        for n in self.nodes.values():
            lvl = self.levels.get(n.id)
            if not n.is_bus or lvl is None:
                continue
            depth = sum(
                1
                for a in self._path_up(n)[1:]
                if a.is_bus and self.levels.get(a.id) == lvl
            )
            key = (round(lvl, 6) if isinstance(lvl, float) else lvl, depth)
            groups[key].append(n)
        for _ in range(50):
            changed = False
            for members in groups.values():
                target = max(m.cy for m in members)
                for m in members:
                    if m.cy < target - 1e-6:
                        self._shift(m, 0.0, target - m.cy)
                        changed = True
            if not changed:
                break

    def _apply_positions(self) -> None:
        for n in list(self.root.walk()):
            pos = n.comp.pos if n.comp is not None else None
            if pos is not None:
                self._shift(n, pos.x - n.x, pos.y - n.cy)

    # -------------------------------------------------------------- Geometrie
    @staticmethod
    def _ortho(a: Point, b: Point) -> Wire:
        if abs(a[0] - b[0]) < 1e-6:
            return Wire([a, b])
        mid = (a[1] + b[1]) / 2
        return Wire([a, (a[0], mid), (b[0], mid), b])

    def _node_label_req(self, n: _N) -> _LabelReq:
        req = _LabelReq(n.id, "node", n.lines, n.lw, n.lh)
        top = n.cy - n.lh / 2
        req.candidates = [
            (n.x + n.w / 2 + LABEL_GAP, top, "left"),
            (n.x - n.w / 2 - LABEL_GAP - n.lw, top, "left"),
            (n.x + n.w / 2 + LABEL_GAP, n.cy + n.h / 2 + 1.0, "left"),
            (n.x + n.w / 2 + LABEL_GAP, n.cy - n.h / 2 - 1.0 - n.lh, "left"),
        ]
        return req

    def _bus_label_req(self, n: _N) -> _LabelReq:
        x0, x1 = n.span  # type: ignore[misc]
        top = n.cy - n.lh / 2
        left = (x0 - LABEL_GAP - n.lw, top, "left")
        right = (x1 + LABEL_GAP, top, "left")
        above = (x0, n.cy - 1.5 - n.lh, "left")
        req = _LabelReq(n.id, "bus", n.lines, n.lw, n.lh)
        req.candidates = [left, right, above] if n.label_side == "left" else [right, left, above]
        return req

    def _horizontal_vias(
        self, vias: list[_N], x_from: float, x_to: float, y: float, symbols: dict, reqs: list, wires: list
    ) -> None:
        """Legt via-Elemente waagerecht zwischen x_from und x_to auf Höhe y."""
        slots = [max(v.h, v.lw) + TIE_WIRE for v in vias]
        total = sum(slots)
        x = (x_from + x_to) / 2 - total / 2
        cursor = x_from
        for v, s in zip(vias, slots):
            v.x, v.cy = x + s / 2, y
            symbols[v.id] = PlacedSymbol(v.id, v.comp, v.x, y, v.w, v.h, rot=90)
            wires.append(Wire([(cursor, y), (v.x - v.h / 2, y)]))
            cursor = v.x + v.h / 2
            req = _LabelReq(v.id, "node", v.lines, v.lw, v.lh)
            req.candidates = [
                (v.x - v.lw / 2, y - v.w / 2 - 1.0 - v.lh, "center"),
                (v.x - v.lw / 2, y + v.w / 2 + 1.0, "center"),
            ]
            reqs.append(req)
            x += s
        wires.append(Wire([(cursor, y), (x_to, y)]))

    def _vertical_vias(
        self, vias: list[_N], x: float, y_from: float, symbols: dict, reqs: list, wires: list
    ) -> float:
        """Stapelt via-Elemente senkrecht ab y_from. Gibt das untere Ende zurück."""
        cursor = y_from
        for v in vias:
            slot = max(v.h, v.lh)
            top = cursor + GAP_WIRE
            v.x, v.cy = x, top + slot / 2
            symbols[v.id] = PlacedSymbol(v.id, v.comp, x, v.cy, v.w, v.h)
            wires.append(Wire([(x, cursor), (x, v.cy - v.h / 2)]))
            cursor = v.cy + v.h / 2
            reqs.append(self._node_label_req(v))
        return cursor

    def _geometry(self, ties: list[_Tie]):
        symbols: dict[str, PlacedSymbol] = {}
        reqs: list[_LabelReq] = []
        wires: list[Wire] = []
        junctions: list[Point] = []
        tree = [n for n in self.root.walk() if n.comp is not None]

        # Kupplungen zwischen benachbarten Teilbäumen: Beinchen festlegen
        ext_left: dict[str, float] = {}
        ext_right: dict[str, float] = {}
        for t in ties:
            if t.mode == "adjacent":
                ext_right[t.a.id] = t.ca.x + t.ca.sub_right + TIE_MARGIN
                ext_left[t.b.id] = t.cb.x - t.cb.sub_left - TIE_MARGIN

        for n in tree:
            if n.is_bus:
                xs = [c.x for c in n.children] + [n.x]
                x0 = min(n.x + n.bar[0], min(xs) - BUS_OVERHANG)
                x1 = max(n.x + n.bar[1], max(xs) + BUS_OVERHANG)
                x0 = ext_left.get(n.id, x0)
                x1 = ext_right.get(n.id, x1)
                n.span = (x0, x1)

        # Einspeise-Kupplungen (zweites Netz auf Sammelschiene)
        for t in ties:
            if t.mode != "feeder":
                continue
            src, bus = t.a, t.b
            bottom = self._vertical_vias(t.vias, src.x, src.bottom, symbols, reqs, wires)
            x0, x1 = bus.span  # type: ignore[misc]
            if bottom + GAP_WIRE <= bus.cy and not (x0 <= src.x <= x1):
                wires.append(Wire([(src.x, bottom), (src.x, bus.cy)]))
                bus.span = (min(x0, src.x), max(x1, src.x))
            else:
                end = x1 + BUS_EXT if src.x >= (x0 + x1) / 2 else x0 - BUS_EXT
                y = max(bottom + GAP_WIRE, bus.cy + GAP_BUS_CHILD / 2)
                wires.append(Wire([(src.x, bottom), (src.x, y), (end, y), (end, bus.cy)]))
                bus.span = (min(x0, end), max(x1, end))

        for n in tree:
            symbols[n.id] = PlacedSymbol(n.id, n.comp, n.x, n.cy, n.w, n.h, span=n.span if n.is_bus else None)

        # Leitungen im Baum
        for n in tree:
            p = n.parent
            if p is None or p.comp is None:
                continue
            if p.is_bus:
                wires.append(Wire([(n.x, p.cy), (n.x, n.top)]))
            elif len(p.children) == 1:
                wires.append(self._ortho((p.x, p.bottom), (n.x, n.top)))
        for p in tree:
            if p.is_bus or len(p.children) < 2:
                continue
            jy = p.junction_y if p.junction_y is not None else p.bottom + GAP_WIRE
            xs = [c.x for c in p.children]
            lo, hi = min(xs + [p.x]), max(xs + [p.x])
            wires.append(Wire([(p.x, p.bottom), (p.x, jy)]))
            wires.append(Wire([(lo, jy), (hi, jy)]))
            for c in p.children:
                wires.append(Wire([(c.x, jy), (c.x, c.top)]))
            for x in sorted(set(xs + [p.x])):
                count = (abs(x - p.x) < 1e-6) + sum(abs(x - cx) < 1e-6 for cx in xs) + (x > lo + 1e-6) + (x < hi - 1e-6)
                if count >= 3:
                    junctions.append((x, jy))

        # Kupplungen zwischen Sammelschienen
        content_bottom = max((n.slot_bottom for n in tree), default=0.0)
        for t in ties:
            if t.mode == "adjacent":
                leg_a, leg_b = ext_right[t.a.id], ext_left[t.b.id]
                drop = max([TIE_DROP] + [v.lh + v.w / 2 + 4.0 for v in t.vias])
                y = max(t.a.cy, t.b.cy) + drop
                wires.append(Wire([(leg_a, t.a.cy), (leg_a, y)]))
                wires.append(Wire([(leg_b, y), (leg_b, t.b.cy)]))
                self._horizontal_vias(t.vias, leg_a, leg_b, y, symbols, reqs, wires)
            elif t.mode == "fallback":
                a, b = (t.a, t.b) if t.a.x <= t.b.x else (t.b, t.a)
                vias = t.vias if a is t.a else list(reversed(t.vias))
                pa = self._tie_anchor(a, toward_right=True)
                pb = self._tie_anchor(b, toward_right=False)
                drop = max([TIE_DROP] + [v.lh + v.w / 2 + 4.0 for v in vias])
                y = content_bottom + drop
                content_bottom = y + max([v.w / 2 + v.lh for v in vias] + [0.0]) + 2.0
                wires.append(Wire([pa, (pa[0], y)]))
                wires.append(Wire([(pb[0], y), pb]))
                self._horizontal_vias(vias, pa[0], pb[0], y, symbols, reqs, wires)
                for n, p in ((a, pa), (b, pb)):
                    if n.is_bus:
                        x0, x1 = n.span  # type: ignore[misc]
                        n.span = (min(x0, p[0]), max(x1, p[0]))
                        symbols[n.id].span = n.span

        # Beschriftungen
        for n in tree:
            if n.is_bus and n.lines:
                reqs.append(self._bus_label_req(n))
            elif n.lines and not n.is_bus:
                reqs.append(self._node_label_req(n))
        labels = self._resolve_labels(reqs, symbols)
        return symbols, labels, wires, junctions

    def _tie_anchor(self, n: _N, toward_right: bool) -> Point:
        if n.is_bus:
            x0, x1 = n.span  # type: ignore[misc]
            return (x1 + BUS_EXT, n.cy) if toward_right else (x0 - BUS_EXT, n.cy)
        return (n.x, n.bottom)

    def _resolve_labels(self, reqs: list[_LabelReq], symbols: dict[str, PlacedSymbol]) -> list[PlacedLabel]:
        fixed = [s.box for s in symbols.values()]
        placed: list[PlacedLabel] = []
        for req in reqs:
            chosen = None
            for x0, top, ha in req.candidates:
                lab = self._make_label(req.owner, req.kind, req.lines, x0, top, ha)
                if not any(lab.box.overlaps(b) for b in fixed) and not any(lab.box.overlaps(p.box) for p in placed):
                    chosen = lab
                    break
            if chosen is None:
                x0, top, ha = req.candidates[0]
                chosen = self._make_label(req.owner, req.kind, req.lines, x0, top, ha)
                self.warnings.append(warning("W201", "Beschriftung überlappt mit anderen Elementen", node_id=req.owner))
            placed.append(chosen)
        syms = list(symbols.values())
        for i, s in enumerate(syms):
            for o in syms[i + 1 :]:
                if s.box.overlaps(o.box):
                    self.warnings.append(warning("W202", f"Symbol überlappt mit '{o.id}' (manuelle Position prüfen)", node_id=s.id))
        return placed

    # ----------------------------------------------------- Bänder und Blatt
    def _bands(self, symbols: dict[str, PlacedSymbol], labels: list[PlacedLabel], content: Box) -> list[Band]:
        label_box = {lab.owner: lab.box for lab in labels if lab.kind in ("node", "bus")}
        ranges: dict = {}
        for eid, s in symbols.items():
            lvl = self.levels.get(eid)
            if lvl is None:
                continue
            box = s.box.union(label_box[eid]) if eid in label_box else s.box
            key = round(lvl, 6) if isinstance(lvl, float) else lvl
            lo, hi = ranges.get(key, (box.y0, box.y1))
            ranges[key] = (min(lo, box.y0), max(hi, box.y1))
        bands = [Band(fmt_level(k), lo, hi, content.x0, content.x1) for k, (lo, hi) in ranges.items()]
        bands.sort(key=lambda b: (b.y0 + b.y1) / 2)
        for prev, nxt in zip(bands, bands[1:]):
            boundary = (prev.y1 + nxt.y0) / 2
            prev.y1 = nxt.y0 = boundary
        if bands:
            bands[0].y0 = content.y0 - 4.0
            bands[-1].y1 = content.y1 + 4.0
        return bands

    def _table(self, x: float, y: float) -> Table:
        pad = 2.0
        header = (["Kennz."] if self.show_ids else []) + ["Name", "Typ", "Bezeichnung", "Technische Daten"]
        max_w = ([0.0] if self.show_ids else []) + [TABLE_NAME_W, 0.0, TABLE_TEXT_W, TABLE_DATA_W]
        rows: list[list[str]] = [header]
        for eid, comp in self.topo.elements.items():
            data = comp.data_lines() + ([comp.note] if comp.note else [])
            row = [comp.name or "", comp.title or comp.type_name, comp.label or "", "; ".join(data)]
            rows.append(([eid] if self.show_ids else []) + row)
        ni = 1 if self.show_ids else 0
        if not any(r[ni] for r in rows[1:]):  # Namensspalte ohne Inhalt weglassen
            header, max_w = header[:ni] + header[ni + 1 :], max_w[:ni] + max_w[ni + 1 :]
            rows = [r[:ni] + r[ni + 1 :] for r in rows]
        wrapped = [
            [self._wrap(text, TABLE_SIZE, j == 0, mw) if text else [""] for text, mw in zip(row, max_w)]
            for j, row in enumerate(rows)
        ]
        widths = [
            max(self.m.width(ln, TABLE_SIZE, bold=(j == 0)) for j, r in enumerate(wrapped) for ln in r[i]) + 2 * pad
            for i in range(len(header))
        ]
        title_size = 7.5
        title_h = self.m.line_height(title_size) + 1.0
        lh = self.m.line_height(TABLE_SIZE)
        col_x = [x]
        for w in widths:
            col_x.append(col_x[-1] + w)
        row_y = [y + title_h]
        for r in wrapped:
            row_y.append(row_y[-1] + max(len(c) for c in r) * lh + 1.6)
        cells = [
            TextLine(ln, col_x[i] + pad, row_y[j] + 0.8 + (k + 0.5) * lh, TABLE_SIZE, bold=(j == 0))
            for j, row in enumerate(wrapped)
            for i, lines in enumerate(row)
            for k, ln in enumerate(lines)
            if ln
        ]
        title = TextLine("Betriebsmittelliste", x, y + title_h / 2 - 0.5, title_size, bold=True)
        return Table(Box(x, y, col_x[-1], row_y[-1]), col_x, row_y, cells, title)

    def _title_block(self, x1: float, y0: float, max_width: Optional[float] = None) -> TitleBlock:
        meta = self.d.diagram
        width = max(140.0, self.m.width(meta.title, 9.0, True) + 10.0)
        if max_width is not None:
            width = min(width, max_width)
        rows = [11.0, 6.5, 6.5, 6.5]
        x0 = x1 - width
        split = x0 + width * 0.66
        ys = [y0]
        for h in rows:
            ys.append(ys[-1] + h)
        cells = [TitleBlockCell(Box(x0, ys[0], x1, ys[1]), "Titel", meta.title, 9.0, True)]
        pairs = [
            (("Projekt", meta.project), ("Datum", meta.date)),
            (("Bearbeiter", meta.author), ("Revision", meta.revision)),
            (("Zeichnungsart", "Einlinienschaltplan (Symbole DIN EN 60617)"), ("Blatt", "1 / 1")),
        ]
        for r, (left, right) in enumerate(pairs, start=1):
            cells.append(TitleBlockCell(Box(x0, ys[r], split, ys[r + 1]), *left))
            cells.append(TitleBlockCell(Box(split, ys[r], x1, ys[r + 1]), *right))
        return TitleBlock(Box(x0, y0, x1, ys[-1]), cells)

    # ------------------------------------------------------------------- Run
    def run(self) -> Layout:
        self.topo = build_topology(self.d)
        self.levels, _ = analyze_voltages(self.topo)
        self.nodes: dict[str, _N] = {}
        self.root = _N("__root__", None)
        for r in self.topo.roots:
            child = self._build(r, self.root)
            self.root.children.append(child)
        ties = self._plan_ties()
        self._measure(self.root)
        for c in self.root.children:
            self._assign_y(c, 0.0)
        self._align_buses()
        if self.root.children:
            start = -min(o - c.sub_left for o, c in zip(self.root.offsets, self.root.children))
            self._place(self.root, start)
        self._apply_positions()

        symbols, labels, wires, junctions = self._geometry(ties)

        pts = [p for w in wires for p in w.points]
        boxes = [s.box for s in symbols.values()] + [lab.box for lab in labels]
        if pts:
            boxes.append(Box.around(pts))
        content = boxes[0] if boxes else Box(0, 0, 50, 30)
        for b in boxes[1:]:
            content = content.union(b)

        bands = self._bands(symbols, labels, content)
        band_labels = [self._make_label(f"band:{b.name}", "band", [(b.name, BAND_SIZE, True)], 0, 0) for b in bands]
        band_col = max((lab.box.width for lab in band_labels), default=-6.0) + 6.0

        theme, meta = self.theme, self.d.diagram
        header: list[PlacedLabel] = []
        header_h = 0.0
        if theme.title_in_header and (meta.title or meta.subtitle):
            spec = [(meta.title, TITLE_SIZE, True)] if meta.title else []
            if meta.subtitle:
                spec.append((meta.subtitle, SUBTITLE_SIZE, False))
            header.append(self._make_label("title", "title", spec, 0.0, 0.0))
            header_h = header[0].box.height + 6.0

        # Zeichnung in lokalen Koordinaten, Ursprung (0, 0)
        dx = band_col - content.x0
        dy = header_h - content.y0 + 4.0
        for s in symbols.values():
            s.translate(dx, dy)
        for lab in labels:
            lab.translate(dx, dy)
        for w in wires:
            w.translate(dx, dy)
        junctions = [(x + dx, y + dy) for x, y in junctions]
        content = content.shifted(dx, dy)
        for b, lab in zip(bands, band_labels):
            b.translate(0, dy)
            b.x0, b.x1 = 0.0, content.x1 + 4.0
            lab.translate(b.x0 + 2.0, b.y0 + 2.0)
        obstacles = [s.box for s in symbols.values()] + [lab.box for lab in labels]
        for b in bands[1:]:
            b.segments = _free_segments(b.x0, b.x1, b.y0, obstacles)
        labels += band_labels + header

        right = content.x1 + 4.0
        bottom = content.y1 + 4.0
        table = None
        if meta.bom:
            # Stückliste rechts oder unter dem Plan, je nachdem was besser aufs Blatt passt
            beside = self._table(right + 10.0, content.y0 - 4.0)
            below = self._table(content.x0, bottom + 8.0)
            size_beside = (beside.box.x1, max(bottom, beside.box.y1))
            size_below = (max(right, below.box.x1), below.box.y1)
            table, (right, bottom) = beside, size_beside
            if self.paper != "none" and self._paper_rank(*size_below) < self._paper_rank(*size_beside):
                table, (right, bottom) = below, size_below

        layout = Layout(
            width=0.0,
            height=0.0,
            symbols=symbols,
            labels=labels,
            wires=wires,
            junctions=junctions,
            bands=bands,
            table=table,
            warnings=self.warnings,
        )
        if self.paper == "none":
            self._compose_free(layout, right, bottom)
        else:
            self._compose_paper(layout, right, bottom)
        return layout

    # ------------------------------------------------------------ Blattaufbau
    def _compose_free(self, layout: Layout, w: float, h: float) -> None:
        """Blatt wächst mit dem Plan (kein Normformat)."""
        theme = self.theme
        margin = theme.margin
        layout.translate_content(margin, margin)
        right, bottom = w + margin, h + margin
        if theme.title_block:
            tb = self._title_block(0, 0)
            x1 = max(right, margin + tb.box.width)
            layout.title_block = self._title_block(x1, bottom + 8.0)
            layout.width = x1 + margin
            layout.height = layout.title_block.box.y1 + margin
        else:
            layout.width, layout.height = right + margin, bottom + margin
        if theme.frame:
            layout.frame = Box(5.0, 5.0, layout.width - 5.0, layout.height - 5.0)

    def _page_areas(self, pw: float, ph: float) -> tuple[Optional[Box], Box, Optional[TitleBlock]]:
        """Rahmen, Zeichenfläche und Schriftfeld für ein Blatt der Größe pw x ph."""
        theme = self.theme
        if theme.frame:
            frame: Optional[Box] = Box(FRAME_LEFT, FRAME_OTHER, pw - FRAME_OTHER, ph - FRAME_OTHER)
            area = Box(frame.x0 + FRAME_PAD, frame.y0 + FRAME_PAD, frame.x1 - FRAME_PAD, frame.y1 - FRAME_PAD)
        else:
            frame = None
            m = theme.margin
            area = Box(m, m, pw - m, ph - m)
        tb = None
        if theme.title_block:
            outer = frame or area
            probe = self._title_block(0, 0, outer.width)
            tb = self._title_block(outer.x1, outer.y1 - probe.box.height, outer.width)
            area = Box(area.x0, area.y0, area.x1, min(area.y1, tb.box.y0 - TB_GAP))
        return frame, area, tb

    def _paper_rank(self, w: float, h: float) -> tuple[float, float]:
        """Sortierschlüssel: kleiner = besser (erst Verkleinerung, dann Blattgröße)."""
        name, _, pw, ph, *_, scale = self._choose_paper(w, h)
        return (-round(scale, 4), pw * ph)

    def _choose_paper(self, w: float, h: float):
        sizes = list(PAPER_SIZES) if self.paper == "auto" else [self.paper]
        if self.orientation == "auto":
            orients = ["landscape", "portrait"] if w >= h else ["portrait", "landscape"]
        else:
            orients = [self.orientation]

        candidates = []
        for name in sizes:
            short, long_ = PAPER_SIZES[name]
            for o in orients:
                pw, ph = (long_, short) if o == "landscape" else (short, long_)
                frame, area, tb = self._page_areas(pw, ph)
                scale = min(1.0, area.width / w if w > 0 else 1.0, area.height / h if h > 0 else 1.0)
                candidates.append((name, o, pw, ph, frame, area, tb, scale))
        fitting = [c for c in candidates if c[7] >= 1.0 - 1e-9]
        if fitting:
            return fitting[0]
        return max((c for c in candidates if c[0] == sizes[-1]), key=lambda c: c[7])

    def _compose_paper(self, layout: Layout, w: float, h: float) -> None:
        """Wählt das kleinste passende Normformat (A5/A4/A3) samt Ausrichtung."""
        name, o, pw, ph, frame, area, tb, scale = self._choose_paper(w, h)
        label = f"{name} {'quer' if o == 'landscape' else 'hoch'}"
        if scale < 1.0 - 1e-9:
            self.warnings.append(
                warning("W301", f"Plan passt nicht unverkleinert auf {label} und wird auf {scale:.0%} verkleinert")
            )
        else:
            scale = 1.0
        ox = area.x0 + (area.width - w * scale) / 2
        oy = area.y0 + (area.height - h * scale) / 2
        if scale == 1.0:
            layout.translate_content(ox, oy)
        else:
            layout.content_scale = scale
            layout.content_offset = (ox, oy)
        layout.width, layout.height = pw, ph
        layout.frame = frame
        layout.title_block = tb
        layout.paper = label


def _free_segments(x0: float, x1: float, y: float, boxes: list[Box], pad: float = 1.5) -> list[tuple[float, float]]:
    """Teile der Linie y in [x0, x1], die keine Box schneiden."""
    blocked = sorted((b.x0 - pad, b.x1 + pad) for b in boxes if b.y0 - pad < y < b.y1 + pad)
    out, cur = [], x0
    for a, b in blocked:
        if a > cur:
            out.append((cur, min(a, x1)))
        cur = max(cur, b)
    if cur < x1:
        out.append((cur, x1))
    return [(a, b) for a, b in out if b - a > 2.0]


def compute_layout(
    diagram,
    metrics: Optional[TextMetrics] = None,
    theme: Optional[Theme] = None,
    paper: Optional[str] = None,
    orientation: Optional[str] = None,
) -> Layout:
    """Berechnet das Layout eines (validierten) Schaltplans.

    ``paper``/``orientation`` überschreiben die Angaben aus ``diagram``.
    """
    return LayoutEngine(diagram, metrics, theme, paper, orientation).run()
