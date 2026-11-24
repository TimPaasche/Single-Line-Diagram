"""Graphstruktur: Elementketten, Spannbaum ab den Netzanschlüssen, Ringe/Kupplungen."""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field
from typing import Iterator, Optional

from sld.components import Component, Kind


@dataclass
class Chain:
    """Eine Verbindung als Elementkette: [from, via..., to]."""

    index: int
    ids: list[str]
    open: bool  # enthält ein offenes Schaltgerät
    allow_loop: bool

    @property
    def ends(self) -> tuple[str, str]:
        return self.ids[0], self.ids[-1]


@dataclass
class Topology:
    elements: dict[str, Component]
    chains: list[Chain]
    roots: list[str]
    parent: dict[str, Optional[str]] = field(default_factory=dict)
    children: dict[str, list[str]] = field(default_factory=dict)
    ties: list[Chain] = field(default_factory=list)  # Ring schließende Verbindungen (Kupplungen)
    loops: list[Chain] = field(default_factory=list)  # davon unbeabsichtigt (geschlossen, ohne allow_loop)
    unreachable: list[str] = field(default_factory=list)
    adjacency: dict[str, list[str]] = field(default_factory=dict)

    def neighbors(self, eid: str) -> list[str]:
        return self.adjacency.get(eid, [])

    def subtree(self, eid: str) -> Iterator[str]:
        stack = [eid]
        while stack:
            cur = stack.pop()
            yield cur
            stack.extend(reversed(self.children.get(cur, [])))

    def ancestors(self, eid: str) -> list[str]:
        out = []
        cur = self.parent.get(eid)
        while cur is not None:
            out.append(cur)
            cur = self.parent.get(cur)
        return out

    def in_tree(self, eid: str) -> bool:
        return eid in self.parent


def build_topology(diagram) -> Topology:
    elements = diagram.element_map()
    chains: list[Chain] = []
    for i, conn in enumerate(diagram.connections):
        if conn.from_ not in elements or conn.to not in elements or conn.from_ == conn.to:
            continue  # wird von der Validierung gemeldet
        ids = [conn.from_] + [v.id for v in conn.via] + [conn.to]
        is_open = any(elements[e].is_open() for e in ids)
        chains.append(Chain(i, ids, is_open, conn.allow_loop))

    adjacency: dict[str, list[str]] = {e: [] for e in elements}
    by_node: dict[str, list[Chain]] = {e: [] for e in elements}
    for ch in chains:
        for a, b in zip(ch.ids, ch.ids[1:]):
            adjacency[a].append(b)
            adjacency[b].append(a)
        by_node[ch.ids[0]].append(ch)
        by_node[ch.ids[-1]].append(ch)

    roots = [n.id for n in diagram.nodes if n.kind == Kind.SOURCE]
    topo = Topology(elements=elements, chains=chains, roots=roots, adjacency=adjacency)
    parent, children = topo.parent, topo.children
    seq: dict[str, int] = {}
    order_key: dict[str, Optional[int]] = {}
    used: set[int] = set()
    queue: deque[str] = deque()
    for r in roots:
        parent[r] = None
        children[r] = []
        queue.append(r)

    def attach(ch: Chain, start: str) -> None:
        ids = ch.ids if ch.ids[0] == start else list(reversed(ch.ids))
        if ids[-1] in parent:
            topo.ties.append(ch)
            if not ch.open and not ch.allow_loop:
                topo.loops.append(ch)
            return
        order = next((elements[e].order for e in ids[1:] if elements[e].order is not None), None)
        prev = start
        for e in ids[1:]:
            parent[e] = prev
            children.setdefault(prev, []).append(e)
            children.setdefault(e, [])
            seq[e] = len(seq)
            order_key[e] = order
            prev = e
        queue.append(ids[-1])

    pending: list[tuple[Chain, str]] = []
    while True:
        while queue:
            u = queue.popleft()
            for ch in by_node[u]:
                if ch.index in used:
                    continue
                if ch.open or ch.allow_loop:
                    pending.append((ch, u))  # offene Verbindungen erst zum Schluss
                    continue
                used.add(ch.index)
                attach(ch, u)
        progressed = False
        for ch, u in pending:
            if ch.index in used:
                continue
            used.add(ch.index)
            attach(ch, u)
            progressed = True
        pending = []
        if not progressed and not queue:
            break

    big = 10**9
    for kids in children.values():
        kids.sort(key=lambda e: (order_key.get(e) if order_key.get(e) is not None else big, seq.get(e, 0)))

    in_ties = {e for ch in topo.ties for e in ch.ids[1:-1]}
    topo.unreachable = [e for e in elements if e not in parent and e not in in_ties]
    return topo
