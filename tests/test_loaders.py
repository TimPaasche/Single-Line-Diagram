import json

import pytest

import sld
from sld.io import load_raw
from sld.schema import ConfigError

from conftest import EXAMPLES, parse


def test_all_three_formats_give_identical_model():
    models = [sld.load(EXAMPLES / f"02_pv_speicher_ms.{ext}") for ext in ("yaml", "json", "toml")]
    dumps = [m.model_dump() for m in models]
    assert dumps[0] == dumps[1] == dumps[2]
    # auch die automatisch vergebenen IDs sind identisch
    assert [n.id for n, _ in models[0].elements()] == [n.id for n, _ in models[2].elements()]


def test_format_detection_by_suffix(tmp_path, basic_yaml):
    p = tmp_path / "anlage.yml"
    p.write_text(basic_yaml, encoding="utf-8")
    assert len(sld.load(p).nodes) == 6
    bad = tmp_path / "anlage.xml"
    bad.write_text("<x/>", encoding="utf-8")
    with pytest.raises(ConfigError, match="Unbekanntes Dateiformat"):
        sld.load(bad)


def test_schema_key_is_ignored(tmp_path, basic_yaml):
    data = parse(basic_yaml).model_dump(by_alias=True)
    data["$schema"] = "./sld.schema.json"
    p = tmp_path / "a.json"
    p.write_text(json.dumps(data), encoding="utf-8")
    assert sld.load(p).nodes[0].id == "netz"


def test_yaml_syntax_error_has_line():
    with pytest.raises(ConfigError) as exc:
        parse("nodes:\n  - {id: a, type: grid\n  - x: [")
    assert exc.value.issues[0].line is not None


def test_json_syntax_error_has_line(tmp_path):
    p = tmp_path / "x.json"
    p.write_text('{\n "nodes": [\n  {"id": "a",,}\n ]\n}', encoding="utf-8")
    with pytest.raises(ConfigError) as exc:
        sld.load(p)
    assert exc.value.issues[0].line == 3


def test_schema_error_reports_line_and_node_id():
    text = """\
nodes:
  - id: netz
    type: grid
    voltage_kv: 20
  - id: pv1
    type: pv_array
    kwp: viel
"""
    with pytest.raises(ConfigError) as exc:
        parse(text)
    issue = exc.value.issues[0]
    assert issue.node_id == "pv1"
    assert issue.line == 7
    assert "kwp" in issue.message


def test_unknown_type_lists_available():
    with pytest.raises(ConfigError, match="Unbekannter Komponententyp 'solar'.*pv_array"):
        parse("nodes:\n  - {id: x, type: solar}\n")


def test_unknown_field_is_rejected():
    with pytest.raises(ConfigError, match="Unbekanntes Feld"):
        parse("nodes:\n  - {id: n, type: grid, voltage_kv: 20, voltag: 1}\n")


def test_toml_line_mapping_for_nodes():
    _, source = load_raw(EXAMPLES / "02_pv_speicher_ms.toml")
    assert source.line_for(("nodes", 0)) == 9  # Zeile mit id = "netz"


def test_auto_ids_follow_reference_letters(basic_yaml):
    d = parse(basic_yaml)
    vias = [v.id for c in d.connections for v in c.via]
    assert vias == ["Q1", "F1"]
    assert all(v.auto_id for c in d.connections for v in c.via)
