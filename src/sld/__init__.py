"""sld – konfigurierbarer Einlinienschaltplan-Generator.

Schichten: schema (Modell/Validierung) -> io (Loader) -> components (Registry)
-> layout (Geometrie) -> render (Backends). matplotlib wird erst beim Rendern geladen.
"""

from __future__ import annotations

__version__ = "0.1.0"

from sld.io import load, loads
from sld.schema import ConfigError, Issue, validate

__all__ = ["ConfigError", "Issue", "__version__", "load", "loads", "render_file", "validate"]


def render_file(
    config: str,
    output: str,
    fmt: str | None = None,
    theme: str | None = None,
    paper: str | None = None,
    orientation: str | None = None,
):
    """Lädt, validiert und rendert eine Konfiguration. Gibt (Layout, Issues) zurück."""
    from sld.render import render

    diagram = load(config)
    issues = validate(diagram)
    errors = [i for i in issues if i.is_error]
    if errors:
        raise ConfigError(errors)
    layout = render(diagram, output, fmt=fmt, theme=theme, paper=paper, orientation=orientation)
    return layout, issues + layout.warnings
