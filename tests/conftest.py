from pathlib import Path

import pytest

import sld

ROOT = Path(__file__).resolve().parent.parent
EXAMPLES = ROOT / "examples"
EXAMPLE_FILES = sorted(EXAMPLES.glob("*.yaml"))


def parse(yaml_text: str):
    return sld.loads(yaml_text, "yaml", "test.yaml")


def codes(issues) -> list[str]:
    return [i.code for i in issues]


@pytest.fixture
def basic_yaml() -> str:
    return """\
nodes:
  - {id: netz, type: grid, voltage_kv: 20}
  - {id: ms, type: busbar, voltage_kv: 20}
  - {id: t1, type: transformer, rating_kva: 630, ratio: "20/0.4 kV"}
  - {id: ns, type: busbar, voltage_kv: 0.4}
  - {id: wr1, type: inverter, kva: 100}
  - {id: pv1, type: pv_array, kwp: 100}
connections:
  - {from: netz, to: ms, via: [{type: circuit_breaker}]}
  - {from: ms, to: t1}
  - {from: t1, to: ns}
  - {from: ns, to: wr1, via: [{type: fuse}]}
  - {from: wr1, to: pv1}
"""
