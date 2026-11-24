import pytest

import sld
from sld.render import render
from sld.render.base import Renderer

from conftest import EXAMPLE_FILES


@pytest.mark.parametrize("fmt", ["svg", "png", "pdf"])
@pytest.mark.parametrize("path", EXAMPLE_FILES, ids=lambda p: p.stem)
def test_render_smoke(tmp_path, path, fmt):
    out = tmp_path / f"plan.{fmt}"
    layout, issues = sld.render_file(str(path), str(out))
    assert out.stat().st_size > 1000
    assert not [i for i in issues if i.is_error]
    head = out.read_bytes()[:8]
    assert {"svg": b"<?xml", "png": b"\x89PNG", "pdf": b"%PDF"}[fmt] in head


def test_svg_is_deterministic(tmp_path):
    d = sld.load(EXAMPLE_FILES[1])
    render(d, tmp_path / "a.svg")
    render(d, tmp_path / "b.svg")
    assert (tmp_path / "a.svg").read_bytes() == (tmp_path / "b.svg").read_bytes()


class RecordingRenderer(Renderer):
    """Beispiel für ein alternatives Backend: protokolliert nur die Primitive."""

    formats = ("log",)

    def __init__(self):
        self.calls = []

    def begin(self, width, height, background):
        self.calls.append(("begin", width, height))

    def polyline(self, pts, *, color, width, dash=None):
        self.calls.append(("line", tuple(pts)))

    def polygon(self, pts, *, fill, edge, width):
        self.calls.append(("polygon", tuple(pts)))

    def circle(self, cx, cy, r, *, fill, edge, width):
        self.calls.append(("circle", cx, cy, r))

    def text(self, x, y, s, **kw):
        self.calls.append(("text", s))

    def save(self, path, fmt, dpi=200):
        self.calls.append(("save", path))


def test_custom_backend_receives_primitives(tmp_path):
    rec = RecordingRenderer()
    render(sld.load(EXAMPLE_FILES[1]), tmp_path / "x.log", renderer=rec)
    kinds = {c[0] for c in rec.calls}
    assert {"begin", "line", "polygon", "circle", "text", "save"} <= kinds
    assert ("text", "500 kWp") in rec.calls


def test_unknown_format_rejected(tmp_path):
    with pytest.raises(ValueError, match="Ausgabeformat"):
        render(sld.load(EXAMPLE_FILES[0]), tmp_path / "x.bmp")
