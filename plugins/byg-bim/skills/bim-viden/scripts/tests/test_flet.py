"""Hovedmodel og forslag: bim.py forslag/flet (kør i bim-miljøet: python -m pytest scripts/tests)."""
import pathlib
import shutil
import sys

import yaml

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
from bimlib.flet import flet, opret  # noqa: E402
from bimlib.spec import indlaes  # noqa: E402

EKSEMPEL = pathlib.Path(__file__).resolve().parents[2] / "assets" / "eksempel" / "model.yaml"


def _hoved(tmp_path):
    h = tmp_path / "model.yaml"
    shutil.copy(EKSEMPEL, h)
    return h


def _forslag(h, navn, tekst):
    assert opret(h, navn) == 0
    f = h.parent / "forslag" / f"{navn}.yaml"
    f.write_text(f.read_text(encoding="utf-8") + tekst, encoding="utf-8")
    return f


def test_flet_giver_samme_model_som_forslaget(tmp_path):
    h = _hoved(tmp_path)
    f = _forslag(h, "rad", "vaegge:\n  - {id: S-IV2, usikkerhed: null, kilde: B}\n"
                           "  - {id: S-IV3, etage: S, type: IV-let, punkter: [[5000, 6000], [9700, 6000]]}\n"
                           "nedrives: [K-IV1]\n")
    forventet = indlaes(f)
    linjer_foer = h.read_text(encoding="utf-8").splitlines()
    assert flet(f) == 0
    efter = indlaes(h)
    forventet.pop("_sti"), efter.pop("_sti")
    assert efter == forventet
    # kun de berørte linjer er ændret (+ én flettelinje i hovedet)
    linjer_efter = h.read_text(encoding="utf-8").splitlines()
    assert len(set(linjer_efter) - set(linjer_foer)) == 4
    assert not f.exists() and (tmp_path / "historik" / "flettelog.md").exists()


def test_proev_skriver_intet(tmp_path):
    h = _hoved(tmp_path)
    foer = h.read_bytes()
    f = _forslag(h, "p", "vaegge:\n  - {id: S-IV2, kilde: B}\n")
    assert flet(f, proev=True) == 0
    assert h.read_bytes() == foer and f.exists()


def test_konflikt_paa_samme_element_stopper(tmp_path):
    h = _hoved(tmp_path)
    a = _forslag(h, "a", "vaegge:\n  - {id: S-IV2, usikkerhed: 5}\n")
    b = _forslag(h, "b", "vaegge:\n  - {id: S-IV2, usikkerhed: 9}\n")
    c = _forslag(h, "c", "vaegge:\n  - {id: S-IV1, kilde: B}\n")
    assert flet(a) == 0
    foer = h.read_bytes()
    assert flet(b) == 1 and h.read_bytes() == foer
    assert flet(c) == 0
    d = yaml.safe_load(h.read_text(encoding="utf-8"))
    iv = {e["id"]: e for e in d["vaegge"]}
    assert iv["S-IV2"]["usikkerhed"] == 5 and iv["S-IV1"]["kilde"] == "B"


def test_slet_med_haengende_henvisning_stopper(tmp_path):
    h = _hoved(tmp_path)
    foer = h.read_bytes()
    f = _forslag(h, "s", "slet: [S-IV2]\n")      # S-D2 sidder i S-IV2
    assert flet(f) == 1 and h.read_bytes() == foer
