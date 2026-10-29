"""Ejendomskortet genereres fra hovedmodellens fakta: (bim.py opsaet --test, derefter i bim-miljøet: python -m pytest scripts/tests)."""
import pathlib
import shutil
import sys

import pytest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
from bimlib.property_card import generer, importer  # noqa: E402
from bimlib.merge import flet, opret  # noqa: E402
from bimlib.spec import SpecFejl, indlaes  # noqa: E402

EKSEMPEL = pathlib.Path(__file__).resolve().parents[2] / "assets" / "eksempel" / "model.yaml"
KORT = """# Ejendomskort – testvej 1
**Opdateret:** 2026-10-16
En oplysning uden dato er ikke kontrolleret.

## Fælles (alle fag)
| ID | Emne | Værdi | Dato | Kilde |
|---|---|---|---|---|
| E-F-01 | Opført | 1952 | 2026-09-01 | BBR |
| E-F-02 | Kælder | ja, 2,10 m | 2026-09-02 | B |

## Åbne spørgsmål
| ID | Spørgsmål | Hvem afklarer | Sag |
|---|---|---|---|
| Å-1 | Hvor er stophanen? | bygherren | v2 |

## Erstattede oplysninger
| ID | Tidligere værdi | Erstattet (dato) | Grund |
|---|---|---|---|
| E-F-02 | 2,00 m | 2026-10-01 | målt |
| E-F-02 | 1,90 m | 2026-10-02 | målt igen |
"""


def _opsæt(tmp_path):
    (tmp_path / "bim").mkdir()
    h = tmp_path / "bim" / "model.yaml"
    shutil.copy(EKSEMPEL, h)
    k = tmp_path / "kort.md"
    k.write_text(KORT, encoding="utf-8")
    return h, k


def test_import_flet_og_generer_giver_samme_kort(tmp_path):
    h, k = _opsæt(tmp_path)
    assert importer(h, k) == 0
    assert flet(h.parent / "forslag" / "ejendomskort-import.yaml") == 0
    ny = k.read_text(encoding="utf-8")
    assert ny.startswith("<!-- GENERERET") and ny.split("\n", 1)[1] == KORT
    fakta = {f["id"]: f for f in indlaes(h)["fakta"]}
    assert fakta["E-F-02@2"]["tidligere"] == "2,00 m" and fakta["E-F-02@3"]["afsnit"] == "erstattede_oplysninger"
    assert generer(h, tjek=True) == 0


def test_rettelse_via_forslag_slaar_igennem_i_kortet(tmp_path):
    h, k = _opsæt(tmp_path)
    importer(h, k)
    flet(h.parent / "forslag" / "ejendomskort-import.yaml")
    assert opret(h, "kaelder") == 0
    f = h.parent / "forslag" / "kaelder.yaml"
    f.write_text(f.read_text(encoding="utf-8")
                 + "fakta:\n  - {id: E-F-02, vaerdi: 'ja, 2,15 m'}\n"
                   "  - {id: E-F-03, afsnit: faelles, emne: Tag, vaerdi: tegl, dato: '2026-10-16', kilde: F}\n"
                 "slet: [Å-1]\n", encoding="utf-8")
    assert flet(f) == 0
    ny = k.read_text(encoding="utf-8")
    assert "| E-F-02 | Kælder | ja, 2,15 m |" in ny and "| E-F-03 | Tag | tegl |" in ny and "Å-1" not in ny


def test_haandrettet_kort_opdages(tmp_path):
    h, k = _opsæt(tmp_path)
    importer(h, k)
    flet(h.parent / "forslag" / "ejendomskort-import.yaml")
    k.write_text(k.read_text(encoding="utf-8").replace("1952", "1953"), encoding="utf-8")
    assert generer(h, tjek=True) == 1


def test_dublet_id_og_ukendt_afsnit_afvises(tmp_path):
    h, k = _opsæt(tmp_path)
    importer(h, k)
    flet(h.parent / "forslag" / "ejendomskort-import.yaml")
    t = h.read_text(encoding="utf-8")
    h.write_text(t + "  - {id: E-F-01, afsnit: faelles}\n  - {id: E-X, afsnit: findes_ikke}\n", encoding="utf-8")
    with pytest.raises(SpecFejl) as e:
        indlaes(h)
    assert any("to gange" in x for x in e.value.fejl) and any("ukendt afsnit" in x for x in e.value.fejl)
