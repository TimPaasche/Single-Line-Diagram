"""Komponentenbibliothek.

Jedes Modul in diesem Paket (außer ``_*``, ``base``, ``registry``) wird beim
Import automatisch geladen. Externe Pakete können Komponenten über die
Entry-Point-Gruppe ``sld.components`` oder ``sld --plugin modul`` beisteuern.
"""

import importlib
import pkgutil
from importlib.metadata import entry_points

from sld.components.base import Component, DrawContext, Kind, SwitchingDevice
from sld.components.registry import components, get_component, register, registry_version, unregister

__all__ = [
    "Component",
    "DrawContext",
    "Kind",
    "SwitchingDevice",
    "components",
    "get_component",
    "load_plugin",
    "register",
    "registry_version",
    "unregister",
]

_CORE = {"base", "registry"}


def _discover() -> None:
    for info in pkgutil.iter_modules(__path__):
        if info.name.startswith("_") or info.name in _CORE:
            continue
        importlib.import_module(f"{__name__}.{info.name}")
    for ep in entry_points(group="sld.components"):
        ep.load()


def load_plugin(module: str) -> None:
    """Importiert ein Modul, das Komponenten per ``@register`` anmeldet."""
    importlib.import_module(module)


_discover()
