"""TOML-Loader (tomllib ab Python 3.11, sonst tomli)."""

from __future__ import annotations

import re
import sys

from sld.io._textscan import scan
from sld.schema.issues import ConfigError, SourceMap, error

if sys.version_info >= (3, 11):
    import tomllib
else:  # pragma: no cover
    import tomli as tomllib


def load_toml(text: str, filename: str | None = None) -> tuple[object, SourceMap]:
    try:
        data = tomllib.loads(text)
    except tomllib.TOMLDecodeError as exc:
        line = getattr(exc, "lineno", None)
        if line is None:
            m = re.search(r"line (\d+)", str(exc))
            line = int(m.group(1)) if m else None
        raise ConfigError([error("E000", f"TOML-Syntaxfehler: {exc}", line=line, filename=filename)]) from None
    source = SourceMap(filename=filename)
    scan(text, data, source)
    return data, source
