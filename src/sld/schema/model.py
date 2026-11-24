"""Datenmodell des Schaltplans.

Das Knotenmodell ist eine diskriminierte Union über alle registrierten
Komponenten und wird dynamisch aus der Registry gebaut. Eine neue Komponente
braucht deshalb keine Änderung in diesem Modul.
"""

from dataclasses import dataclass, field
from typing import Annotated, Any, Iterator, Literal, Optional, Union

from pydantic import BaseModel, ConfigDict, Field, PrivateAttr, ValidationError, create_model

from sld.components import Component, Kind, components, registry_version
from sld.schema.issues import ConfigError, Issue, SourceMap, error
from sld.schema.templates import Origins, TemplateDef, TemplateInstance, expand_templates


class DiagramMeta(BaseModel):
    model_config = ConfigDict(extra="forbid")
    title: str = Field("", description="Plantitel")
    subtitle: str = ""
    project: str = Field("", description="Projekt (Schriftfeld)")
    author: str = Field("", description="Bearbeiter (Schriftfeld)")
    date: str = Field("", description="Datum (Schriftfeld)")
    revision: str = Field("", description="Revisionsstand (Schriftfeld)")
    theme: Literal["din", "simple"] = Field("din", description="Darstellungsstil")
    bom: bool = Field(False, description="Stückliste (Betriebsmittelliste) neben dem Plan ausgeben")
    label_detail: Literal["full", "short", "id"] = Field(
        "full", description="Umfang der Beschriftung am Symbol: full | short | id (nur Name bzw. ID)"
    )
    show_ids: bool = Field(False, description="IDs (Kennzeichen) am Symbol und in der Stückliste anzeigen")
    label_width_mm: float = Field(
        32.0, ge=0, description="Maximale Breite der Beschriftung in mm, längere Texte werden umbrochen (0 = kein Umbruch)"
    )
    paper: Literal["auto", "A5", "A4", "A3", "none"] = Field(
        "auto",
        description="Blattformat: auto (kleinstes passendes aus A5/A4/A3) | A5 | A4 | A3 | none (Blatt so groß wie der Plan)",
    )
    orientation: Literal["auto", "landscape", "portrait"] = Field(
        "auto", description="Ausrichtung des Blatts: auto | landscape (quer) | portrait (hoch)"
    )


class ConnectionBase(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)
    from_: str = Field(alias="from", description="ID des Startknotens (oder einer Template-Instanz)")
    to: str = Field(description="ID des Zielknotens (oder einer Template-Instanz)")
    allow_loop: bool = Field(False, description="Diese Verbindung darf bewusst einen Ring schließen")


@dataclass
class Locator:
    """Ordnet Issues einer Zeile in der Quelldatei zu."""

    source: Optional[SourceMap] = None
    origins: Origins = field(default_factory=Origins)
    node_paths: dict[str, tuple] = field(default_factory=dict)

    def resolve(self, issue: Issue) -> Issue:
        if self.source is None:
            return issue
        issue.filename = issue.filename or self.source.filename
        if issue.line is None:
            path = issue.path or self.node_paths.get(issue.node_id or "")
            if path is not None:
                issue.line = self.source.line_for(self.origins.map(path))
        return issue


class DiagramBase(BaseModel):
    model_config = ConfigDict(extra="forbid")
    diagram: DiagramMeta = Field(default_factory=DiagramMeta)

    _locator: Locator = PrivateAttr(default_factory=Locator)

    def elements(self) -> Iterator[tuple[Component, tuple]]:
        """Alle Knoten inkl. via-Elemente mit ihrem Pfad im Dokument."""
        for i, n in enumerate(self.nodes):  # type: ignore[attr-defined]
            yield n, ("nodes", i)
        for i, c in enumerate(self.connections):  # type: ignore[attr-defined]
            for k, v in enumerate(c.via):
                yield v, ("connections", i, "via", k)

    def element_map(self) -> dict[str, Component]:
        out: dict[str, Component] = {}
        for n, _ in self.elements():
            if n.id is not None:
                out.setdefault(n.id, n)
        return out

    def resolve(self, issues: list[Issue]) -> list[Issue]:
        return [self._locator.resolve(i) for i in issues]


_cache: dict[int, tuple[type, type, type]] = {}


def _build() -> tuple[type, type, type]:
    version = registry_version()
    if version in _cache:
        return _cache[version]
    comps = tuple(components().values())
    if not comps:
        raise RuntimeError("Keine Komponenten registriert")
    node_union: Any = Annotated[Union[comps], Field(discriminator="type")] if len(comps) > 1 else comps[0]  # type: ignore[valid-type]
    connection = create_model(
        "Connection",
        __base__=ConnectionBase,
        via=(list[node_union], Field(default_factory=list, description="Elemente in Reihe auf der Verbindung (von from nach to)")),
    )
    diagram = create_model(
        "Diagram",
        __base__=DiagramBase,
        nodes=(list[node_union], Field(description="Knoten des Schaltplans")),
        connections=(list[connection], Field(default_factory=list, description="Verbindungen (Graph-Kanten)")),
    )
    file_model = create_model(
        "DiagramFile",
        __base__=diagram,
        templates=(dict[str, TemplateDef], Field(default_factory=dict, description="Wiederverwendbare Teilschaltungen")),
        nodes=(list[Union[node_union, TemplateInstance]], Field(description="Knoten oder Template-Instanzen")),
    )
    _cache.clear()
    _cache[version] = (diagram, connection, file_model)
    return _cache[version]


def diagram_model() -> type[DiagramBase]:
    return _build()[0]


def file_model() -> type[BaseModel]:
    """Modell inkl. Templates, nur für den JSON-Schema-Export."""
    return _build()[2]


# -- Parsen -----------------------------------------------------------------

_MSG_DE = {
    "missing": "Pflichtfeld fehlt",
    "extra_forbidden": "Unbekanntes Feld",
    "union_tag_not_found": "Feld 'type' fehlt",
}


def _convert_errors(exc: ValidationError, data: dict) -> list[Issue]:
    names = set(components())
    out = []
    for e in exc.errors():
        loc = list(e["loc"])
        # Diskriminator-Segment (z. B. 'pv_array') aus dem Pfad entfernen
        loc = [p for i, p in enumerate(loc) if not (isinstance(p, str) and p in names and i > 0 and isinstance(loc[i - 1], int))]
        node_id = None
        try:
            if loc[0] == "nodes":
                node_id = data["nodes"][loc[1]].get("id")
            elif loc[0] == "connections" and len(loc) > 3 and loc[2] == "via":
                node_id = data["connections"][loc[1]]["via"][loc[3]].get("id")
        except (KeyError, IndexError, TypeError, AttributeError):
            pass
        kind = e["type"]
        if kind == "union_tag_invalid":
            tag = e.get("ctx", {}).get("tag")
            msg = f"Unbekannter Komponententyp '{tag}'. Verfügbar: {', '.join(sorted(names))}"
        else:
            msg = _MSG_DE.get(kind, e["msg"])
        field_path = ".".join(str(p) for p in loc[2:] if not isinstance(p, int)) if loc and loc[0] == "nodes" else ""
        where = f"Feld '{field_path}': " if field_path else ("" if node_id else f"{'.'.join(map(str, loc))}: ")
        out.append(error("E000", f"{where}{msg}", node_id=node_id, path=tuple(loc)))
    return out


def _assign_auto_ids(diagram: DiagramBase) -> None:
    used = {n.id for n, _ in diagram.elements() if n.id}
    counters: dict[str, int] = {}
    for conn in diagram.connections:  # type: ignore[attr-defined]
        for v in conn.via:
            if v.id:
                continue
            letter = v.ref_letter
            n = counters.get(letter, 0)
            while True:
                n += 1
                candidate = f"{letter}{n}"
                if candidate not in used:
                    break
            counters[letter] = n
            used.add(candidate)
            v.id = candidate
            v._auto_id = True


def parse_diagram(raw: Any, source: Optional[SourceMap] = None) -> DiagramBase:
    """Validiert ein Rohdokument (dict) und liefert das Modell. Wirft ConfigError."""
    locator = Locator(source=source)
    if not isinstance(raw, dict):
        raise ConfigError([locator.resolve(error("E000", "Die Konfiguration muss ein Mapping/Objekt sein"))])
    raw = {k: v for k, v in raw.items() if k != "$schema"}
    try:
        data, origins = expand_templates(raw)
    except ConfigError as exc:
        raise ConfigError([locator.resolve(i) for i in exc.issues]) from None
    locator.origins = origins

    issues: list[Issue] = []
    for i, n in enumerate(data.get("nodes") or [] if isinstance(data.get("nodes"), list) else []):
        if isinstance(n, dict) and not n.get("id"):
            issues.append(error("E000", "Knoten ohne 'id'", path=("nodes", i)))
    try:
        model = diagram_model().model_validate(data)
    except ValidationError as exc:
        issues += _convert_errors(exc, data)
        model = None
    if issues or model is None:
        raise ConfigError([locator.resolve(i) for i in issues])

    _assign_auto_ids(model)
    locator.node_paths = {}
    for n, path in model.elements():
        locator.node_paths.setdefault(n.id, path)
    model._locator = locator
    return model


def is_series(node: Component) -> bool:
    return node.kind == Kind.SERIES
