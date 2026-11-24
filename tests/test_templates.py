import pytest

from sld.schema import ConfigError

from conftest import parse

BASE = """\
templates:
  feeder:
    params: {kwp: null, kva: 100}
    entry: wr
    nodes:
      - {id: wr, type: inverter, kva: "${kva}", label: "WR ${id}"}
      - {id: pv, type: pv_array, kwp: "${kwp}"}
    connections:
      - {from: wr, to: pv, via: [{type: cable, id: k, length_m: 30}]}
nodes:
  - {id: netz, type: grid, voltage_kv: 0.4}
  - {id: bus, type: busbar}
  - {id: f1, template: feeder, params: {kwp: 50}, order: 2}
  - {id: f2, template: feeder, params: {kwp: 80, kva: 70}}
connections:
  - {from: netz, to: bus}
  - {from: bus, to: f1, via: [{type: fuse}]}
  - {from: bus, to: f2}
"""


def test_instances_are_expanded_with_prefix_and_params():
    d = parse(BASE)
    ids = [n.id for n in d.nodes]
    assert ids == ["netz", "bus", "f1.wr", "f1.pv", "f2.wr", "f2.pv"]
    m = d.element_map()
    assert m["f1.wr"].kva == 100  # Vorgabewert
    assert m["f2.wr"].kva == 70
    assert m["f2.pv"].kwp == 80
    assert m["f1.wr"].label == "WR f1"
    assert m["f1.wr"].order == 2  # order der Instanz landet am Eintrittsknoten
    assert "f1.k" in m and "f2.k" in m


def test_connections_to_instance_go_to_entry():
    d = parse(BASE)
    targets = [(c.from_, c.to) for c in d.connections]
    assert ("bus", "f1.wr") in targets
    assert ("f1.wr", "f1.pv") in targets


def test_missing_required_param():
    with pytest.raises(ConfigError, match="Pflichtparameter fehlen: kwp") as exc:
        parse(BASE.replace("params: {kwp: 50}, ", ""))
    assert exc.value.issues[0].line == 13


def test_unknown_template_and_param():
    with pytest.raises(ConfigError, match="Unbekanntes Template 'nope'"):
        parse(BASE.replace("template: feeder, params: {kwp: 50}", "template: nope"))
    with pytest.raises(ConfigError, match="Unbekannte Template-Parameter: foo"):
        parse(BASE.replace("params: {kwp: 50}", "params: {kwp: 50, foo: 1}"))


def test_type_error_in_expanded_node_points_to_instance():
    with pytest.raises(ConfigError) as exc:
        parse(BASE.replace("kwp: 80", "kwp: abc"))
    issue = exc.value.issues[0]
    assert issue.node_id == "f2.pv"
    assert issue.line == 14
