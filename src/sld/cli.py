"""Kommandozeile: sld render | validate | list-components | schema."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Optional, Sequence

from sld.schema.issues import ConfigError, Issue

EXIT_OK, EXIT_INVALID, EXIT_USAGE = 0, 1, 2


def _print_issues(issues: list[Issue]) -> None:
    for i in issues:
        print(i.format(), file=sys.stderr)


def _load_and_validate(path: str, strict: bool):
    from sld.io import load
    from sld.schema import validate

    diagram = load(path)
    issues = validate(diagram)
    errors = [i for i in issues if i.is_error or strict]
    return diagram, issues, errors


def cmd_validate(args) -> int:
    _, issues, errors = _load_and_validate(args.config, args.strict)
    _print_issues(issues)
    n_err = sum(i.is_error for i in issues)
    n_warn = len(issues) - n_err
    print(f"{args.config}: {'ungültig' if errors else 'gültig'} ({n_err} Fehler, {n_warn} Warnungen)")
    return EXIT_INVALID if errors else EXIT_OK


def cmd_render(args) -> int:
    from sld.render import render

    diagram, issues, errors = _load_and_validate(args.config, args.strict)
    _print_issues(issues)
    if errors:
        print("Abbruch: Konfiguration enthält Fehler.", file=sys.stderr)
        return EXIT_INVALID
    fmt = args.format
    if args.output:
        out = Path(args.output)
        suffix = out.suffix.lstrip(".").lower()
        if fmt and suffix and suffix != fmt:
            print(f"--format {fmt} passt nicht zur Dateiendung '.{suffix}'", file=sys.stderr)
            return EXIT_USAGE
        fmt = fmt or suffix or "svg"
        if not out.suffix:
            out = out.with_suffix(f".{fmt}")
    else:
        fmt = fmt or "svg"
        out = Path(args.config).with_suffix(f".{fmt}")
    layout = render(diagram, out, fmt=fmt, theme=args.theme, dpi=args.dpi, paper=args.paper, orientation=args.orientation)
    _print_issues(layout.warnings)
    sheet = f"{layout.paper}, " if layout.paper else ""
    print(f"geschrieben: {out} ({sheet}{layout.width:.0f} × {layout.height:.0f} mm)")
    return EXIT_OK


def cmd_list(args) -> int:
    from sld.components import components

    common = {"id", "type", "name", "label", "order", "pos", "note"}
    for name, cls in components().items():
        print(f"{name:<20} {cls.kind.value:<9} {cls.title}")
        if args.verbose:
            for fname, f in cls.model_fields.items():
                if fname in common:
                    continue
                req = "*" if f.is_required() else " "
                print(f"    {req}{fname:<20} {f.description or ''}")
    if args.verbose:
        print("\n* = Pflichtfeld. Gemeinsame Felder aller Komponenten: " + ", ".join(sorted(common)))
    return EXIT_OK


def json_schema() -> dict:
    from sld.schema import file_model

    schema = file_model().model_json_schema(by_alias=True)
    schema["$schema"] = "https://json-schema.org/draft/2020-12/schema"
    schema["title"] = "sld – Einlinienschaltplan"
    schema.setdefault("properties", {})["$schema"] = {"type": "string"}
    return schema


def cmd_schema(args) -> int:
    text = json.dumps(json_schema(), indent=2, ensure_ascii=False) + "\n"
    if args.output:
        Path(args.output).write_text(text, encoding="utf-8")
        print(f"geschrieben: {args.output}")
    else:
        sys.stdout.write(text)
    return EXIT_OK


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="sld", description="Einlinienschaltplan-Generator")
    p.add_argument("--plugin", action="append", default=[], metavar="MODUL", help="Python-Modul mit zusätzlichen Komponenten laden")
    sub = p.add_subparsers(dest="command", required=True)

    r = sub.add_parser("render", help="Schaltplan zeichnen")
    r.add_argument("config", help="Konfiguration (.yaml/.yml/.json/.toml)")
    r.add_argument("-o", "--output", help="Ausgabedatei (Vorgabe: <config>.svg)")
    r.add_argument("--format", choices=["svg", "png", "pdf"])
    r.add_argument("--theme", choices=["din", "simple"], help="überschreibt diagram.theme")
    r.add_argument("--paper", choices=["auto", "A5", "A4", "A3", "none"], help="Blattformat, überschreibt diagram.paper")
    r.add_argument(
        "--orientation", choices=["auto", "landscape", "portrait"], help="Ausrichtung, überschreibt diagram.orientation"
    )
    r.add_argument("--dpi", type=int, default=200, help="Auflösung für PNG")
    r.add_argument("--strict", action="store_true", help="Warnungen wie Fehler behandeln")
    r.set_defaults(func=cmd_render)

    v = sub.add_parser("validate", help="Konfiguration prüfen")
    v.add_argument("config")
    v.add_argument("--strict", action="store_true", help="Warnungen wie Fehler behandeln")
    v.set_defaults(func=cmd_validate)

    lc = sub.add_parser("list-components", help="verfügbare Komponenten anzeigen")
    lc.add_argument("-v", "--verbose", action="store_true", help="Parameter mit anzeigen")
    lc.set_defaults(func=cmd_list)

    s = sub.add_parser("schema", help="JSON-Schema für Editoren exportieren")
    s.add_argument("-o", "--output", help="Zieldatei (Vorgabe: stdout)")
    s.set_defaults(func=cmd_schema)
    return p


def main(argv: Optional[Sequence[str]] = None) -> int:
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(errors="replace")  # type: ignore[attr-defined]
        except (AttributeError, ValueError):
            pass
    args = build_parser().parse_args(argv)
    from sld.components import load_plugin

    try:
        for mod in args.plugin:
            load_plugin(mod)
    except ImportError as exc:
        print(f"Plugin nicht ladbar: {exc}", file=sys.stderr)
        return EXIT_USAGE
    try:
        return args.func(args)
    except ConfigError as exc:
        _print_issues(exc.issues)
        return EXIT_INVALID


if __name__ == "__main__":
    sys.exit(main())
