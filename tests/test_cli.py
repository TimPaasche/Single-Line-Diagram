import json
import sys
import textwrap

from sld.cli import json_schema, main
from sld.components import components, unregister

from conftest import EXAMPLE_FILES, EXAMPLES


def test_validate_ok(capsys):
    assert main(["validate", str(EXAMPLE_FILES[0])]) == 0
    assert "gültig (0 Fehler, 0 Warnungen)" in capsys.readouterr().out


def test_validate_reports_errors_with_line(tmp_path, capsys):
    p = tmp_path / "bad.yaml"
    p.write_text("nodes:\n  - {id: n, type: grid, voltage_kv: 20}\n  - {id: x, type: load}\nconnections:\n  - {from: n, to: y}\n", encoding="utf-8")
    assert main(["validate", str(p)]) == 1
    err = capsys.readouterr().err
    assert "bad.yaml:5: FEHLER [E002]" in err
    assert "bad.yaml:3: FEHLER [E003] Knoten 'x'" in err


def test_strict_turns_warnings_into_errors(tmp_path):
    p = tmp_path / "w.yaml"
    p.write_text(
        "nodes:\n  - {id: n, type: grid, voltage_kv: 0.4}\n  - {id: b, type: battery, kwh: 1, kw: 1}\n"
        "connections:\n  - {from: n, to: b}\n",
        encoding="utf-8",
    )
    assert main(["validate", str(p)]) == 0
    assert main(["validate", "--strict", str(p)]) == 1


def test_render_formats_and_theme(tmp_path, capsys):
    for fmt in ("svg", "png", "pdf"):
        out = tmp_path / f"plan.{fmt}"
        assert main(["render", str(EXAMPLE_FILES[1]), "-o", str(out), "--theme", "simple"]) == 0
        assert out.exists()
    out = tmp_path / "ohne_endung"
    assert main(["render", str(EXAMPLE_FILES[1]), "-o", str(out), "--format", "pdf"]) == 0
    assert (tmp_path / "ohne_endung.pdf").exists()
    assert main(["render", str(EXAMPLE_FILES[1]), "-o", str(tmp_path / "x.svg"), "--format", "png"]) == 2


def test_list_components(capsys):
    assert main(["list-components", "-v"]) == 0
    out = capsys.readouterr().out
    for name in ("grid", "busbar", "transformer", "pv_array", "inverter", "battery", "ev_charger", "cable"):
        assert name in out
    assert "*kwp" in out


def test_schema_export(tmp_path):
    out = tmp_path / "s.json"
    assert main(["schema", "-o", str(out)]) == 0
    schema = json.loads(out.read_text(encoding="utf-8"))
    text = json.dumps(schema)
    for name in components():
        assert f'"const": "{name}"' in text
    assert "templates" in schema["properties"] and "$schema" in schema["properties"]


def test_committed_schema_is_up_to_date():
    committed = json.loads((EXAMPLES.parent / "sld.schema.json").read_text(encoding="utf-8"))
    assert committed == json_schema(), "sld.schema.json neu erzeugen: sld schema -o sld.schema.json"


def test_plugin_component_without_core_change(tmp_path, monkeypatch, capsys):
    mod = tmp_path / "my_heatpump.py"
    mod.write_text(
        textwrap.dedent(
            '''
            from pydantic import Field
            from sld.components import Component, Kind, register

            @register("heat_pump")
            class HeatPump(Component):
                """Wärmepumpe."""
                kind = Kind.TERMINAL
                title = "Wärmepumpe"
                size = (10.0, 10.0)
                kw: float = Field(gt=0)

                def data_lines(self):
                    return [f"{self.kw:g} kW"]

                def draw(self, pen, ctx):
                    pen.circle(0, 0, 5)
                    pen.text(0, 0, "WP", size=6)
            '''
        ),
        encoding="utf-8",
    )
    cfg = tmp_path / "a.yaml"
    cfg.write_text(
        "nodes:\n  - {id: n, type: grid, voltage_kv: 0.4}\n  - {id: wp, type: heat_pump, kw: 9}\n"
        "connections:\n  - {from: n, to: wp, via: [{type: fuse}]}\n",
        encoding="utf-8",
    )
    monkeypatch.syspath_prepend(str(tmp_path))
    try:
        assert main(["--plugin", "my_heatpump", "render", str(cfg), "-o", str(tmp_path / "a.svg")]) == 0
        assert (tmp_path / "a.svg").exists()
    finally:
        unregister("heat_pump")
        sys.modules.pop("my_heatpump", None)
