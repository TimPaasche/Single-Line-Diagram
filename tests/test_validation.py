import sld
from sld.schema import analyze_voltages, build_topology

from conftest import EXAMPLE_FILES, codes, parse


def errors(issues):
    return [i for i in issues if i.is_error]


def test_examples_are_valid():
    for f in EXAMPLE_FILES:
        issues = sld.validate(sld.load(f))
        assert not errors(issues), (f, [str(i) for i in issues])


def test_basic_is_valid(basic_yaml):
    assert sld.validate(parse(basic_yaml)) == []


def test_duplicate_ids_with_line():
    d = parse(
        "nodes:\n  - {id: a, type: grid, voltage_kv: 1}\n  - {id: a, type: busbar}\n"
        "connections:\n  - {from: a, to: a}\n"
    )
    issues = sld.validate(d)
    dup = [i for i in issues if i.code == "E001"][0]
    assert dup.node_id == "a" and dup.line == 3
    assert "E011" in codes(issues)


def test_unknown_reference_and_loose_node(basic_yaml):
    d = parse(basic_yaml + "  - {from: ns, to: gibtsnicht}\n")
    issues = sld.validate(d)
    e2 = [i for i in issues if i.code == "E002"][0]
    assert "gibtsnicht" in e2.message and e2.line == 14
    d = parse(basic_yaml.replace("connections:", "  - {id: lose, type: load}\nconnections:"))
    issues = sld.validate(d)
    assert [i.node_id for i in issues if i.code == "E003"] == ["lose"]


def test_no_grid():
    d = parse("nodes:\n  - {id: b, type: busbar}\n  - {id: l, type: load}\nconnections:\n  - {from: b, to: l}\n")
    assert "E004" in codes(sld.validate(d))


def test_unreachable_island(basic_yaml):
    extra = basic_yaml.replace(
        "connections:", "  - {id: b2, type: busbar}\n  - {id: l2, type: load}\nconnections:"
    ) + "  - {from: b2, to: l2}\n"
    issues = sld.validate(parse(extra))
    assert sorted(i.node_id for i in issues if i.code == "E005") == ["b2", "l2"]


def test_voltage_change_without_transformer(basic_yaml):
    d = parse(basic_yaml.replace("- {from: ms, to: t1}", "- {from: ms, to: ns}\n  - {from: ms, to: t1}"))
    issues = sld.validate(d)
    assert "E007" in codes(issues)


def test_transformer_ratio_mismatch(basic_yaml):
    d = parse(basic_yaml.replace('"20/0.4 kV"', '"10/0.4 kV"'))
    assert "E008" in codes(sld.validate(d))


def test_unintended_loop_and_open_coupling(basic_yaml):
    loop = basic_yaml + "  - {from: ms, to: ns, via: [{type: transformer, rating_kva: 100, ratio: 20/0.4}]}\n"
    issues = sld.validate(parse(loop))
    assert "E006" in codes(issues)
    opened = loop.replace("rating_kva: 100, ratio: 20/0.4}", "rating_kva: 100, ratio: 20/0.4}, {type: switch_disconnector, state: open}")
    assert "E006" not in codes(sld.validate(parse(opened)))
    allowed = loop.replace("- {from: ms, to: ns,", "- {allow_loop: true, from: ms, to: ns,")
    assert "E006" not in codes(sld.validate(parse(allowed)))


def test_terminal_with_two_connections(basic_yaml):
    d = parse(basic_yaml + "  - {from: ns, to: pv1}\n")
    assert "E009" in codes(sld.validate(d))


def test_non_series_component_in_via(basic_yaml):
    d = parse(basic_yaml.replace("via: [{type: fuse}]", "via: [{type: load}]"))
    assert "E010" in codes(sld.validate(d))


def test_warning_transformer_smaller_than_generation(basic_yaml):
    d = parse(basic_yaml.replace("kva: 100}", "kva: 700}"))
    issues = sld.validate(d)
    assert codes(issues) == ["W101"] and issues[0].node_id == "t1"
    assert not issues[0].is_error


def test_warning_battery_without_inverter(basic_yaml):
    text = basic_yaml.replace("connections:", "  - {id: bat, type: battery, kwh: 10, kw: 5}\nconnections:") + "  - {from: ns, to: bat}\n"
    issues = sld.validate(parse(text))
    assert codes(issues) == ["W102"]
    with_inv = text.replace("kw: 5}", "kw: 5, inverter_kva: 5}")
    assert sld.validate(parse(with_inv)) == []


def test_dc_battery_needs_hybrid_inverter(basic_yaml):
    text = basic_yaml.replace("connections:", "  - {id: bat, type: battery, kwh: 10, kw: 5, coupling: dc}\nconnections:") + "  - {from: wr1, to: bat}\n"
    assert codes(sld.validate(parse(text))) == ["W104"]
    hybrid = text.replace("kva: 100}", "kva: 100, inverter_type: hybrid}")
    assert sld.validate(parse(hybrid)) == []


def test_voltage_levels_are_inferred():
    d = sld.load(EXAMPLE_FILES[2])  # Park: nsp_b ohne Spannungsangabe
    levels, issues = analyze_voltages(build_topology(d))
    assert not issues
    assert levels["nsp_b"] == 0.63
    assert levels["a1.pv"] == "DC"
    assert levels["T1"] is None  # Trafo ist Grenze zwischen Ebenen


def test_open_coupling_is_tie_not_tree_edge():
    d = sld.load(EXAMPLE_FILES[2])
    topo = build_topology(d)
    assert [t.ends for t in topo.ties] == [("nsp_a", "nsp_b")]
    assert topo.loops == []
