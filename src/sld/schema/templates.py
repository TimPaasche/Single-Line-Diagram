"""Templates / Makros: wiederverwendbare Teilschaltungen mit Parametern.

Definition::

    templates:
      pv_feeder:
        params: {kwp: null, kva: 100}     # null = Pflichtparameter
        entry: wr                         # Knoten, an den von außen angeschlossen wird
        nodes:
          - {id: wr, type: inverter, kva: "${kva}"}
          - {id: pv, type: pv_array, kwp: "${kwp}"}
        connections:
          - {from: wr, to: pv}

Instanz (in ``nodes``)::

    - {id: f1, template: pv_feeder, params: {kwp: 250}}

Interne Knoten heißen danach ``f1.wr``, ``f1.pv``. Verbindungen zu ``f1``
landen am Eintrittsknoten. ``${id}`` ist immer die Instanz-ID.
"""

from __future__ import annotations

import copy
import re
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, Field, ValidationError

from sld.schema.base import Position
from sld.schema.issues import ConfigError, Issue, error

_PLACEHOLDER = re.compile(r"\$\{(\w+)\}")


class TemplateDef(BaseModel):
    model_config = ConfigDict(extra="forbid")
    description: Optional[str] = None
    params: dict[str, Any] = Field(default_factory=dict, description="Parameter mit Vorgabewert (null = Pflicht)")
    entry: Optional[str] = Field(None, description="Lokale ID des Eintrittsknotens (Vorgabe: erster Knoten)")
    nodes: list[dict[str, Any]] = Field(min_length=1)
    connections: list[dict[str, Any]] = Field(default_factory=list)


class TemplateInstance(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: str = Field(min_length=1, description="Instanz-ID, Präfix der internen Knoten")
    template: str = Field(description="Name des Templates")
    params: dict[str, Any] = Field(default_factory=dict)
    order: Optional[int] = None
    pos: Optional[Position] = None


class Origins:
    """Bildet Pfade im expandierten Dokument auf Pfade im Originaldokument ab."""

    def __init__(self) -> None:
        # Index im expandierten Dokument -> (Originalpfad, Unterpfad übernehmen?)
        self.nodes: list[tuple[tuple, bool]] = []
        self.connections: list[tuple[tuple, bool]] = []

    def map(self, path: tuple) -> tuple:
        if len(path) >= 2 and path[0] in ("nodes", "connections") and isinstance(path[1], int):
            table = self.nodes if path[0] == "nodes" else self.connections
            if path[1] < len(table):
                base, keep = table[path[1]]
                return base + tuple(path[2:]) if keep else base
        return tuple(path)


def _substitute(obj: Any, params: dict[str, Any], missing: set[str]) -> Any:
    if isinstance(obj, dict):
        return {k: _substitute(v, params, missing) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_substitute(v, params, missing) for v in obj]
    if isinstance(obj, str):
        full = _PLACEHOLDER.fullmatch(obj)
        if full:
            name = full.group(1)
            if name not in params:
                missing.add(name)
                return obj
            return params[name]

        def repl(m: re.Match) -> str:
            if m.group(1) not in params:
                missing.add(m.group(1))
                return m.group(0)
            return str(params[m.group(1)])

        return _PLACEHOLDER.sub(repl, obj)
    return obj


def _pydantic_issues(exc: ValidationError, base: tuple, what: str) -> list[Issue]:
    return [
        error("E012", f"{what}: {'.'.join(map(str, e['loc']))}: {e['msg']}", path=base + tuple(e["loc"]))
        for e in exc.errors()
    ]


def expand_templates(raw: dict) -> tuple[dict, Origins]:
    """Löst alle Template-Instanzen auf. Wirft ConfigError bei Fehlern."""
    origins = Origins()
    issues: list[Issue] = []
    raw_templates = raw.get("templates") or {}
    nodes_in = raw.get("nodes")
    conns_in = raw.get("connections")

    if not isinstance(raw_templates, dict):
        raise ConfigError([error("E012", "'templates' muss ein Mapping Name -> Definition sein", path=("templates",))])

    templates: dict[str, TemplateDef] = {}
    for name, body in raw_templates.items():
        try:
            templates[name] = TemplateDef.model_validate(body)
        except ValidationError as exc:
            issues += _pydantic_issues(exc, ("templates", name), f"Template '{name}'")

    out = {k: v for k, v in raw.items() if k != "templates"}
    if not isinstance(nodes_in, list) or (conns_in is not None and not isinstance(conns_in, list)):
        # Strukturfehler meldet anschließend pydantic mit Pfad
        if issues:
            raise ConfigError(issues)
        if isinstance(conns_in, list):
            origins.connections = [(("connections", i), True) for i in range(len(conns_in))]
        return out, origins

    new_nodes: list[Any] = []
    new_conns: list[Any] = []
    entry_of: dict[str, str] = {}

    for j, node in enumerate(nodes_in):
        if not (isinstance(node, dict) and "template" in node):
            new_nodes.append(node)
            origins.nodes.append((("nodes", j), True))
            continue
        path = ("nodes", j)
        try:
            inst = TemplateInstance.model_validate(node)
        except ValidationError as exc:
            issues += _pydantic_issues(exc, path, "Template-Instanz")
            continue
        tpl = templates.get(inst.template)
        if tpl is None:
            avail = ", ".join(templates) or "keine definiert"
            issues.append(error("E012", f"Unbekanntes Template '{inst.template}' (verfügbar: {avail})", node_id=inst.id, path=path))
            continue
        unknown = set(inst.params) - set(tpl.params)
        if unknown:
            issues.append(
                error("E012", f"Unbekannte Template-Parameter: {', '.join(sorted(unknown))}", node_id=inst.id, path=path + ("params",))
            )
        params = {**tpl.params, **inst.params, "id": inst.id}
        required = [k for k, v in params.items() if v is None]
        if required:
            issues.append(
                error("E012", f"Pflichtparameter fehlen: {', '.join(required)}", node_id=inst.id, path=path)
            )
            continue

        missing: set[str] = set()
        body_nodes = _substitute(copy.deepcopy(tpl.nodes), params, missing)
        body_conns = _substitute(copy.deepcopy(tpl.connections), params, missing)
        if missing:
            issues.append(
                error("E012", f"Platzhalter ohne Parameter im Template '{inst.template}': {', '.join(sorted(missing))}", node_id=inst.id, path=path)
            )
            continue

        local_ids = []
        for n in body_nodes:
            if not isinstance(n, dict) or "id" not in n:
                issues.append(error("E012", f"Template '{inst.template}': jeder Knoten braucht eine 'id'", node_id=inst.id, path=path))
                break
            if "template" in n:
                issues.append(error("E012", "Verschachtelte Templates werden nicht unterstützt", node_id=inst.id, path=path))
                break
            local_ids.append(str(n["id"]))
        else:
            entry = tpl.entry or local_ids[0]
            if entry not in local_ids:
                issues.append(error("E012", f"Template '{inst.template}': entry '{entry}' ist kein Knoten des Templates", node_id=inst.id, path=path))
                continue
            prefix = f"{inst.id}."
            local = set(local_ids)

            def rename(ref: Any) -> Any:
                return prefix + ref if isinstance(ref, str) and ref in local else ref

            for n in body_nodes:
                n["id"] = prefix + str(n["id"])
                if n["id"] == prefix + entry:
                    if inst.order is not None:
                        n["order"] = inst.order
                    if inst.pos is not None:
                        n["pos"] = inst.pos.model_dump()
                new_nodes.append(n)
                origins.nodes.append((path, False))
            for c in body_conns:
                if isinstance(c, dict):
                    c["from"], c["to"] = rename(c.get("from")), rename(c.get("to"))
                    for v in c.get("via") or []:
                        if isinstance(v, dict) and isinstance(v.get("id"), str):
                            v["id"] = prefix + v["id"]
                new_conns.append(c)
                origins.connections.append((path, False))
            entry_of[inst.id] = prefix + entry

    if issues:
        raise ConfigError(issues)

    top_conns: list[Any] = []
    top_origins: list[tuple[tuple, bool]] = []
    for i, c in enumerate(conns_in or []):
        top_conns.append(c)
        top_origins.append((("connections", i), True))
    # Instanz-IDs in Verbindungen auf den Eintrittsknoten umlenken
    for c in top_conns + new_conns:
        if isinstance(c, dict):
            for key in ("from", "to"):
                if c.get(key) in entry_of:
                    c[key] = entry_of[c[key]]

    out["nodes"] = new_nodes
    if conns_in is not None or new_conns:
        out["connections"] = top_conns + new_conns
    origins.connections = top_origins + origins.connections
    return out, origins
