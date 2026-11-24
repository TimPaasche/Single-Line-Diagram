"""Anzeigenamen, Textumbruch und Blattformate."""

import pytest

from sld.layout import HeuristicMetrics, compute_layout

from conftest import parse

M = HeuristicMetrics()


def _texts(layout, owner):
    return [ln.text for lab in layout.labels if lab.owner == owner for ln in lab.lines]


def test_ids_hidden_by_default_and_name_shown(basic_yaml):
    text = basic_yaml.replace("{id: wr1, type: inverter,", "{id: wr1, name: Wechselrichter 1, type: inverter,")
    layout = compute_layout(parse(text))
    assert _texts(layout, "wr1")[0] == "Wechselrichter 1"
    assert "pv1" not in _texts(layout, "pv1")
    assert "F1" not in _texts(layout, "F1")


def test_show_ids_puts_id_before_name(basic_yaml):
    text = "diagram: {show_ids: true}\n" + basic_yaml.replace("{id: wr1, type: inverter,", "{id: wr1, name: WR, type: inverter,")
    layout = compute_layout(parse(text))
    assert _texts(layout, "wr1")[:2] == ["wr1", "WR"]
    assert _texts(layout, "pv1")[0] == "pv1"


def test_long_labels_are_wrapped(basic_yaml):
    long = "Wechselrichter für die Dachfläche Süd mit sehr langer Beschreibung"
    text = "diagram: {label_width_mm: 30}\n" + basic_yaml.replace("kva: 100}", f"kva: 100, label: '{long}'}}")
    layout = compute_layout(parse(text), metrics=M)
    lab = next(lab for lab in layout.labels if lab.owner == "wr1")
    assert len(lab.lines) > 3
    assert lab.box.width <= 30.0 + 1e-6
    assert " ".join(ln.text for ln in lab.lines).find(long) >= 0

    unwrapped = compute_layout(parse(text.replace("label_width_mm: 30", "label_width_mm: 0")), metrics=M)
    assert next(lab for lab in unwrapped.labels if lab.owner == "wr1").box.width > 60


def test_small_plan_gets_smallest_paper(basic_yaml):
    layout = compute_layout(parse(basic_yaml))
    assert layout.paper is not None and layout.paper.startswith("A5")
    assert layout.content_scale == 1.0


@pytest.mark.parametrize(
    "paper, orientation, size",
    [("A4", "landscape", (297, 210)), ("A4", "portrait", (210, 297)), ("A3", "landscape", (420, 297))],
)
def test_fixed_paper_and_orientation(basic_yaml, paper, orientation, size):
    layout = compute_layout(parse(basic_yaml), paper=paper, orientation=orientation)
    assert (layout.width, layout.height) == size
    for _, _, box in layout.boxes():
        assert 0 <= box.x0 and box.x1 <= layout.width and 0 <= box.y0 and box.y1 <= layout.height
    assert layout.overlaps() == []


def test_free_format_grows_with_plan(basic_yaml):
    layout = compute_layout(parse("diagram: {paper: none}\n" + basic_yaml))
    assert layout.paper is None
    assert (layout.width, layout.height) not in {(148, 210), (210, 148), (210, 297), (297, 210)}


def test_too_large_plan_is_scaled_onto_a3():
    loads = "\n".join(f"  - {{id: l{i}, type: load, kw: {i + 1}}}" for i in range(40))
    conns = "\n".join(f"  - {{from: bus, to: l{i}}}" for i in range(40))
    text = f"nodes:\n  - {{id: n, type: grid, voltage_kv: 0.4}}\n  - {{id: bus, type: busbar}}\n{loads}\nconnections:\n  - {{from: n, to: bus}}\n{conns}\n"
    layout = compute_layout(parse(text))
    assert layout.paper == "A3 quer"
    assert layout.content_scale < 1.0
    assert [w.code for w in layout.warnings] == ["W301"]
    for _, _, box in layout.boxes():
        assert 0 <= box.x0 and box.x1 <= layout.width and 0 <= box.y0 and box.y1 <= layout.height
    assert layout.overlaps() == []
