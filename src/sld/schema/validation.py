"""Fachliche Prüfung eines geparsten Schaltplans.

Fehlercodes:
  E001 doppelte ID              E002 Verbindung auf unbekannten Knoten
  E003 loser Knoten             E004 kein Netzanschlusspunkt
  E005 nicht erreichbar         E006 unbeabsichtigte Schleife
  E007 Spannungswechsel ohne Trafo
  E008 Trafo-Übersetzung passt nicht
  E009 zu viele Anschlüsse      E010 ungeeignetes via-Element
  E011 Verbindung auf sich selbst
Warnungen:
  W101 Trafo kleiner als angeschlossene Erzeugung
  W102 Batterie ohne Wechselrichter
  W103 PV-Generator ohne Wechselrichter
  W104 DC-Speicher ohne Hybrid-Wechselrichter
  W105 Kupplung zwischen Nicht-Sammelschienen
"""

from __future__ import annotations

from sld.components import Kind
from sld.schema.issues import Issue, error, warning
from sld.schema.topology import Topology, build_topology
from sld.schema.voltage import analyze_voltages
from sld.util import fmt_num


def validate(diagram, topo: Topology | None = None) -> list[Issue]:
    """Liefert alle Fehler und Warnungen (mit Zeilennummern, falls bekannt)."""
    issues: list[Issue] = []

    # -- IDs ---------------------------------------------------------------
    seen: dict[str, tuple] = {}
    for node, path in diagram.elements():
        if node.auto_id:
            continue
        if node.id in seen:
            issues.append(error("E001", f"ID ist doppelt vergeben (zuerst bei {_fmt_path(seen[node.id])})", node_id=node.id, path=path))
        else:
            seen[node.id] = path
    elements = diagram.element_map()

    # -- Verbindungen --------------------------------------------------------
    referenced: set[str] = set()
    for i, conn in enumerate(diagram.connections):
        for key, ref in (("from", conn.from_), ("to", conn.to)):
            if ref not in elements:
                issues.append(error("E002", f"Verbindung #{i + 1}: '{key}' verweist auf unbekannten Knoten '{ref}'", path=("connections", i, key)))
            referenced.add(ref)
        if conn.from_ == conn.to:
            issues.append(error("E011", f"Verbindung #{i + 1} führt von '{conn.from_}' auf sich selbst", path=("connections", i)))
        for k, v in enumerate(conn.via):
            if v.kind != Kind.SERIES:
                issues.append(
                    error(
                        "E010",
                        f"'{v.type_name}' ist kein Reihenelement und darf nicht in 'via' stehen "
                        f"(erlaubt: Schalter, Sicherung, Zähler, Kabel, Trafo, Wechselrichter …)",
                        node_id=v.id,
                        path=("connections", i, "via", k),
                    )
                )

    for i, node in enumerate(diagram.nodes):
        if node.id not in referenced:
            issues.append(error("E003", "Knoten ist mit nichts verbunden", node_id=node.id, path=("nodes", i)))

    grids = [n for n in diagram.nodes if n.kind == Kind.SOURCE]
    if not grids:
        issues.append(error("E004", "Kein Netzanschlusspunkt vorhanden (mindestens ein Knoten vom Typ 'grid' nötig)", path=("nodes",)))

    # -- Graph -------------------------------------------------------------
    topo = topo or build_topology(diagram)
    if grids:
        loose = {i.node_id for i in issues if i.code == "E003"}
        for e in topo.unreachable:
            if e not in loose:
                issues.append(error("E005", "Nicht mit einem Netzanschlusspunkt verbunden", node_id=e))
    for ch in topo.loops:
        a, b = ch.ends
        issues.append(
            error(
                "E006",
                f"Unbeabsichtigte Schleife: Verbindung '{a}' -> '{b}' schließt einen Ring. "
                "Ein offenes Schaltgerät (state: open) einfügen oder 'allow_loop: true' setzen",
                path=("connections", ch.index),
            )
        )

    for e, c in topo.elements.items():
        degree = len(topo.neighbors(e))
        limit = c.connection_limit()
        if c.is_transformer:
            windings = [n for n in topo.neighbors(e) if not topo.elements[n].is_grounding]
            if len(windings) > 2:
                issues.append(error("E009", f"Zweiwicklungstransformator mit {len(windings)} Anschlüssen (max. 2 + Erdung)", node_id=e))
        elif limit is not None and degree > limit:
            issues.append(error("E009", f"{c.title or c.type_name} hat {degree} Anschlüsse, erlaubt sind {limit}", node_id=e))

    levels, v_issues = analyze_voltages(topo)
    issues += v_issues

    # -- Warnungen -----------------------------------------------------------
    issues += _warnings(topo)
    return diagram.resolve(issues)


def _has_inverter_above(topo: Topology, e: str, kind: str | None = None) -> bool:
    for a in topo.ancestors(e):
        c = topo.elements[a]
        if c.is_inverter and (kind is None or getattr(c, "inverter_type", None) == kind):
            return True
        if c.kind == Kind.BUS or c.is_transformer:
            return False
    return False


def _warnings(topo: Topology) -> list[Issue]:
    out: list[Issue] = []
    els = topo.elements
    for e, c in els.items():
        if not topo.in_tree(e):
            continue
        t = c.type_name
        if t == "battery":
            if c.coupling == "ac" and not c.inverter_kva and not _has_inverter_above(topo, e):
                out.append(warning("W102", "Batterie ohne Wechselrichter (inverter_kva setzen oder über einen Wechselrichter anschließen)", node_id=e))
            if c.coupling == "dc" and not c.inverter_kva and not _has_inverter_above(topo, e, "hybrid"):
                out.append(warning("W104", "DC-gekoppelte Batterie ohne Hybrid-Wechselrichter", node_id=e))
        elif t == "pv_array" and not _has_inverter_above(topo, e):
            out.append(warning("W103", "PV-Generator ohne Wechselrichter", node_id=e))
        if c.is_transformer:
            gen = _generation_below(topo, e)
            if gen > c.rating_kva:
                out.append(
                    warning(
                        "W101",
                        f"Transformator ({fmt_num(c.rating_kva)} kVA) kleiner als angeschlossene Erzeugung "
                        f"({fmt_num(gen)} kVA)",
                        node_id=e,
                    )
                )
    for ch in topo.ties:
        a, b = ch.ends
        kinds = {els[a].kind, els[b].kind}
        if kinds != {Kind.BUS} and kinds != {Kind.BUS, Kind.SOURCE}:
            out.append(
                warning("W105", f"Kupplung '{a}' <-> '{b}' verbindet keine zwei Sammelschienen und wird vereinfacht gezeichnet", path=("connections", ch.index))
            )
    return out


def _generation_below(topo: Topology, start: str) -> float:
    total = 0.0
    stack = [(c, False) for c in topo.children.get(start, [])]
    while stack:
        e, behind = stack.pop()
        c = topo.elements[e]
        total += c.generation_kva(behind)
        child_behind = behind or c.is_inverter
        stack.extend((ch, child_behind) for ch in topo.children.get(e, []))
    return total


def _fmt_path(path: tuple) -> str:
    out = ""
    for p in path:
        out += f"[{p}]" if isinstance(p, int) else (f".{p}" if out else str(p))
    return out
