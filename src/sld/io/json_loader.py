"""JSON-Loader."""

from __future__ import annotations

import json

from sld.io._textscan import scan
from sld.schema.issues import ConfigError, SourceMap, error


def load_json(text: str, filename: str | None = None) -> tuple[object, SourceMap]:
    try:
        data = json.loads(text)
    except json.JSONDecodeError as exc:
        raise ConfigError([error("E000", f"JSON-Syntaxfehler: {exc.msg}", line=exc.lineno, filename=filename)]) from None
    source = SourceMap(filename=filename)
    scan(text, data, source)
    return data, source
