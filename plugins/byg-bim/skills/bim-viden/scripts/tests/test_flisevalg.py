"""Flisevalg i bim.py sammenlign: tomme og uændrede fliser springes over (kør i bim-miljøet)."""
import pathlib
import sys

from PIL import Image, ImageDraw

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
from bimlib.sammenlign import _fliser, _flisevalg  # noqa: E402

W, H = 1520, 760  # to fliser: r1c1 (venstre) og r1c2 (højre)


def _billede(streger):
    im = Image.new("RGB", (W, H), "white")
    dr = ImageDraw.Draw(im)
    for s in streger:
        dr.line(s, fill="black", width=4)
    return im


def _valg(tmp_path, orig, ny, gammel, rows=()):
    fliser = _fliser(orig, ny, ny, tmp_path / "fliser", "V1", 0, 0)
    return {v["flise"]: v for v in _flisevalg(fliser, orig, ny, gammel, list(rows), 0, 0)}


def test_foerste_runde_springer_kun_tomme_fliser_over(tmp_path):
    venstre = [(100, 100, 600, 100), (100, 100, 100, 600)]
    v = _valg(tmp_path, _billede(venstre), _billede(venstre), None)
    assert v["r1c1"]["gennemgaa"] and v["r1c1"]["grund"] == "første runde"
    assert not v["r1c2"]["gennemgaa"] and v["r1c2"]["grund"] == "tom"


def test_kun_aendret_flise_gennemgaas_i_naeste_runde(tmp_path):
    vaegge = [(100, 100, 600, 100), (900, 100, 1400, 100)]
    orig = _billede(vaegge)
    gammel = _billede(vaegge)
    ny = _billede([(100, 100, 600, 100), (900, 140, 1400, 140)])  # højre væg flyttet
    v = _valg(tmp_path, orig, ny, gammel)
    assert not v["r1c1"]["gennemgaa"] and v["r1c1"]["grund"] == "uændret"
    assert v["r1c2"]["gennemgaa"] and v["r1c2"]["grund"] == "model ændret"


def test_auto_fund_holder_flisen_med(tmp_path):
    vaegge = [(100, 100, 600, 100), (900, 100, 1400, 100)]
    im = _billede(vaegge)
    rows = [{"status": "AFVIGER", "px": [[300, 120]]}, {"status": "OK", "px": [[1000, 120]]}]
    v = _valg(tmp_path, im, im, im, rows)
    assert v["r1c1"]["gennemgaa"] and v["r1c1"]["fund"] == ["A1"]
    assert not v["r1c2"]["gennemgaa"]


def test_anden_stoerrelse_kan_ikke_sammenlignes(tmp_path):
    im = _billede([(100, 100, 600, 100)])
    v = _valg(tmp_path, im, im, im.resize((W // 2, H // 2)))
    assert v["r1c1"]["gennemgaa"] and v["r1c1"]["grund"] == "forrige model kan ikke sammenlignes"
