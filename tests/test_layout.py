import pytest

import sld
from sld.layout import HeuristicMetrics, compute_layout
from sld.render.mpl import MatplotlibMetrics
from sld.themes import THEMES

from conftest import EXAMPLE_FILES, parse

METRICS = {"heuristic": HeuristicMetrics(), "matplotlib": MatplotlibMetrics("DejaVu Sans")}


@pytest.mark.parametrize("metrics", METRICS.values(), ids=METRICS.keys())
@pytest.mark.parametrize("theme", THEMES.values(), ids=THEMES.keys())
@pytest.mark.parametrize("path", EXAMPLE_FILES, ids=lambda p: p.stem)
def test_no_bounding_box_overlaps(path, theme, metrics):
    layout = compute_layout(sld.load(path), metrics=metrics, theme=theme)
    assert layout.overlaps() == []
    assert [w for w in layout.warnings if w.code != "W301"] == []  # W301 = verkleinert
    for _, _, box in layout.boxes():
        assert 0 <= box.x0 and box.x1 <= layout.width and 0 <= box.y0 and box.y1 <= layout.height


def test_heuristic_metrics_are_not_narrower_than_real_font():
    real, est = METRICS["matplotlib"], METRICS["heuristic"]
    for text in ["NA2XS2Y 3×1×150 mm²", "Übergabestation", "1000 kWh / 500 kW", "WWW mmm", "iiil"]:
        for bold in (False, True):
            assert est.width(text, 7, bold) >= real.width(text, 7, bold) * 0.98, text


def test_grid_on_top_and_consumers_below(basic_yaml):
    layout = compute_layout(parse(basic_yaml))
    s = layout.symbols
    assert s["netz"].cy < s["ms"].cy < s["t1"].cy < s["ns"].cy < s["wr1"].cy < s["pv1"].cy
    assert s["ns"].span is not None and s["ns"].box.width > s["ns"].box.height  # Schiene waagerecht
    assert s["wr1"].cx == pytest.approx(s["pv1"].cx)  # Abgänge senkrecht


def test_busbars_of_same_level_are_aligned():
    layout = compute_layout(sld.load(EXAMPLE_FILES[2]))
    assert layout.symbols["nsp_a"].cy == pytest.approx(layout.symbols["nsp_b"].cy)
    names = [b.name for b in layout.bands]
    assert names == ["20 kV", "0,63 kV", "DC"]
    assert all(a.y1 == pytest.approx(b.y0) for a, b in zip(layout.bands, layout.bands[1:]))


def test_open_coupling_drawn_between_buses():
    layout = compute_layout(sld.load(EXAMPLE_FILES[2]))
    qk, a, b = layout.symbols["QK"], layout.symbols["nsp_a"], layout.symbols["nsp_b"]
    assert qk.rot == 90
    assert a.span[1] < qk.cx < b.span[0]
    assert qk.cy > a.cy


def test_order_hint_controls_feeder_sequence(basic_yaml):
    text = basic_yaml.replace("connections:", "  - {id: l1, type: load}\n  - {id: l2, type: load, order: -1}\nconnections:")
    text += "  - {from: ns, to: l1}\n  - {from: ns, to: l2}\n"
    s = compute_layout(parse(text)).symbols
    assert s["l2"].cx < s["F1"].cx < s["l1"].cx


def test_manual_position_moves_subtree(basic_yaml):
    auto = compute_layout(parse(basic_yaml)).symbols
    moved = compute_layout(parse(basic_yaml.replace("kva: 100}", "kva: 100, pos: {x: 150, y: 120}}"))).symbols
    dx = moved["wr1"].cx - auto["wr1"].cx
    assert dx > 0
    assert moved["pv1"].cx - auto["pv1"].cx == pytest.approx(dx)  # Teilbaum folgt
    assert moved["pv1"].cy - moved["wr1"].cy == pytest.approx(auto["pv1"].cy - auto["wr1"].cy)


def test_second_grid_feeds_bus_from_top():
    text = """\
nodes:
  - {id: n1, type: grid, voltage_kv: 20}
  - {id: n2, type: grid, voltage_kv: 20, label: Reserve}
  - {id: bus, type: busbar}
  - {id: l, type: load, kw: 10}
connections:
  - {from: n1, to: bus, via: [{type: circuit_breaker}, {type: meter}, {type: cable}]}
  - {from: n2, to: bus, via: [{type: circuit_breaker, state: open}]}
  - {from: bus, to: l}
"""
    d = parse(text)
    assert sld.validate(d) == []
    layout = compute_layout(d)
    s = layout.symbols
    assert s["n2"].cy == pytest.approx(s["n1"].cy)
    assert s["n2"].cy < s["Q2"].cy < s["bus"].cy
    assert s["bus"].span[1] >= s["n2"].cx
    assert layout.overlaps() == []


def test_many_feeders_and_long_labels_do_not_overlap():
    feeders = "\n".join(
        f"  - {{id: f{i}, type: load, kw: {i + 1}, label: 'Abgang Nummer {i} mit langer Bezeichnung'}}" for i in range(12)
    )
    conns = "\n".join(f"  - {{from: bus, to: f{i}, via: [{{type: fuse, rating_a: 63}}, {{type: cable, length_m: 1500}}]}}" for i in range(12))
    text = f"nodes:\n  - {{id: n, type: grid, voltage_kv: 0.4}}\n  - {{id: bus, type: busbar}}\n{feeders}\nconnections:\n  - {{from: n, to: bus}}\n{conns}\n"
    layout = compute_layout(parse(text))
    assert layout.overlaps() == []


def test_layout_is_deterministic():
    d = sld.load(EXAMPLE_FILES[2])
    a, b = compute_layout(d), compute_layout(d)
    assert [(s.id, s.cx, s.cy) for s in a.symbols.values()] == [(s.id, s.cx, s.cy) for s in b.symbols.values()]
