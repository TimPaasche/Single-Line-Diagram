"""Fehler- und Warnungsobjekte mit Quellbezug (Datei, Zeile, Knoten-ID)."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal, Optional

Path = tuple  # z. B. ("nodes", 3, "kwp")


@dataclass
class Issue:
    level: Literal["error", "warning"]
    code: str
    message: str
    node_id: Optional[str] = None
    path: Optional[Path] = None
    line: Optional[int] = None
    filename: Optional[str] = None

    @property
    def is_error(self) -> bool:
        return self.level == "error"

    def format(self) -> str:
        loc = self.filename or "<config>"
        if self.line is not None:
            loc += f":{self.line}"
        kind = "FEHLER" if self.is_error else "WARNUNG"
        who = f"Knoten '{self.node_id}': " if self.node_id else ""
        return f"{loc}: {kind} [{self.code}] {who}{self.message}"

    def __str__(self) -> str:
        return self.format()


def error(code: str, message: str, **kw) -> Issue:
    return Issue("error", code, message, **kw)


def warning(code: str, message: str, **kw) -> Issue:
    return Issue("warning", code, message, **kw)


@dataclass
class ConfigError(Exception):
    """Konfiguration ungültig. Enthält alle gefundenen Probleme."""

    issues: list[Issue] = field(default_factory=list)

    def __post_init__(self) -> None:
        super().__init__(self.__str__())

    def __str__(self) -> str:
        return "\n".join(i.format() for i in self.issues)


@dataclass
class SourceMap:
    """Zuordnung Datenpfad -> Zeilennummer (1-basiert) in der Quelldatei."""

    filename: Optional[str] = None
    lines: dict[tuple, int] = field(default_factory=dict)

    def line_for(self, path: Optional[Path]) -> Optional[int]:
        if path is None:
            return None
        p = tuple(path)
        while True:
            if p in self.lines:
                return self.lines[p]
            if not p:
                return None
            p = p[:-1]
