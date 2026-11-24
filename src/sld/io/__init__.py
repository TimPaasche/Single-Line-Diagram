"""Loader für YAML, JSON und TOML. Alle liefern dasselbe Modell.

Das Format wird an der Dateiendung erkannt. Weitere Formate lassen sich mit
``register_loader(".ext", funktion)`` ergänzen.
"""

from __future__ import annotations

from pathlib import Path
from typing import Callable

from sld.io.json_loader import load_json
from sld.io.toml_loader import load_toml
from sld.io.yaml_loader import load_yaml
from sld.schema import ConfigError, DiagramBase, SourceMap, parse_diagram
from sld.schema.issues import error

LoaderFn = Callable[[str, "str | None"], "tuple[object, SourceMap]"]

LOADERS: dict[str, LoaderFn] = {
    ".yaml": load_yaml,
    ".yml": load_yaml,
    ".json": load_json,
    ".toml": load_toml,
}


def register_loader(suffix: str, fn: LoaderFn) -> None:
    LOADERS[suffix.lower()] = fn


def load_raw(path: str | Path) -> tuple[object, SourceMap]:
    path = Path(path)
    loader = LOADERS.get(path.suffix.lower())
    if loader is None:
        raise ConfigError(
            [error("E000", f"Unbekanntes Dateiformat '{path.suffix}' (unterstützt: {', '.join(sorted(LOADERS))})", filename=str(path))]
        )
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise ConfigError([error("E000", f"Datei nicht lesbar: {exc.strerror or exc}", filename=str(path))]) from None
    return loader(text, str(path))


def loads(text: str, fmt: str, filename: str | None = None) -> DiagramBase:
    """Parst Text im Format ``yaml`` | ``json`` | ``toml``."""
    loader = LOADERS[f".{fmt.lower().lstrip('.')}"]
    data, source = loader(text, filename)
    return parse_diagram(data, source)


def load(path: str | Path) -> DiagramBase:
    """Lädt und validiert eine Konfigurationsdatei strukturell (Schema)."""
    data, source = load_raw(path)
    return parse_diagram(data, source)


__all__ = ["LOADERS", "load", "load_raw", "loads", "register_loader"]
