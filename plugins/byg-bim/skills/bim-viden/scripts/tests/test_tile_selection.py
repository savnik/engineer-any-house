"""Tile selection in bim.py sammenlign: empty and unchanged tiles are skipped (run in the bim env)."""
import pathlib
import sys

from PIL import Image, ImageDraw

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
from bimlib.compare import _tiles, _tile_selection  # noqa: E402

W, H = 1520, 760  # two tiles: r1c1 (left) and r1c2 (right)


def _image(strokes):
    im = Image.new("RGB", (W, H), "white")
    dr = ImageDraw.Draw(im)
    for s in strokes:
        dr.line(s, fill="black", width=4)
    return im


def _select(tmp_path, orig, new, old, rows=()):
    tiles = _tiles(orig, new, new, tmp_path / "fliser", "V1", 0, 0)
    return {v["flise"]: v for v in _tile_selection(tiles, orig, new, old, list(rows), 0, 0)}


def test_first_round_skips_only_empty_tiles(tmp_path):
    left = [(100, 100, 600, 100), (100, 100, 100, 600)]
    v = _select(tmp_path, _image(left), _image(left), None)
    assert v["r1c1"]["gennemgaa"] and v["r1c1"]["grund"] == "første runde"
    assert not v["r1c2"]["gennemgaa"] and v["r1c2"]["grund"] == "tom"


def test_only_changed_tile_reviewed_next_round(tmp_path):
    walls = [(100, 100, 600, 100), (900, 100, 1400, 100)]
    orig = _image(walls)
    old = _image(walls)
    new = _image([(100, 100, 600, 100), (900, 140, 1400, 140)])  # right wall moved
    v = _select(tmp_path, orig, new, old)
    assert not v["r1c1"]["gennemgaa"] and v["r1c1"]["grund"] == "uændret"
    assert v["r1c2"]["gennemgaa"] and v["r1c2"]["grund"] == "model ændret"


def test_auto_finding_keeps_tile(tmp_path):
    walls = [(100, 100, 600, 100), (900, 100, 1400, 100)]
    im = _image(walls)
    rows = [{"status": "AFVIGER", "px": [[300, 120]]}, {"status": "OK", "px": [[1000, 120]]}]
    v = _select(tmp_path, im, im, im, rows)
    assert v["r1c1"]["gennemgaa"] and v["r1c1"]["fund"] == ["A1"]
    assert not v["r1c2"]["gennemgaa"]


def test_other_size_cannot_be_compared(tmp_path):
    im = _image([(100, 100, 600, 100)])
    v = _select(tmp_path, im, im, im.resize((W // 2, H // 2)))
    assert v["r1c1"]["gennemgaa"] and v["r1c1"]["grund"] == "forrige model kan ikke sammenlignes"
