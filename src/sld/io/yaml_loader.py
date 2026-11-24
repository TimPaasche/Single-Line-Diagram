"""YAML-Loader mit exakten Zeilennummern."""

from __future__ import annotations

import yaml

from sld.schema.issues import ConfigError, SourceMap, error


def _walk(node: yaml.Node, path: tuple, lines: dict[tuple, int]) -> None:
    lines.setdefault(path, node.start_mark.line + 1)
    if isinstance(node, yaml.MappingNode):
        for key, value in node.value:
            if isinstance(key, yaml.ScalarNode):
                sub = path + (key.value,)
                lines[sub] = key.start_mark.line + 1
                _walk(value, sub, lines)
    elif isinstance(node, yaml.SequenceNode):
        for i, item in enumerate(node.value):
            _walk(item, path + (i,), lines)


def load_yaml(text: str, filename: str | None = None) -> tuple[object, SourceMap]:
    source = SourceMap(filename=filename)
    try:
        loader = yaml.SafeLoader(text)
        try:
            node = loader.get_single_node()
            data = loader.construct_document(node) if node is not None else None
        finally:
            loader.dispose()
    except yaml.YAMLError as exc:
        mark = getattr(exc, "problem_mark", None)
        line = mark.line + 1 if mark is not None else None
        raise ConfigError([error("E000", f"YAML-Syntaxfehler: {getattr(exc, 'problem', exc)}", line=line, filename=filename)]) from None
    if node is not None:
        _walk(node, (), source.lines)
    return data, source
