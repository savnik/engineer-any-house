"""The property card is generated from the main model's facts: (bim.py setup --test, then in the bim env: python -m pytest scripts/tests)."""
import pathlib
import shutil
import sys

import pytest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
from bimlib.property_card import generate, import_card  # noqa: E402
from bimlib.merge import merge, create  # noqa: E402
from bimlib.spec import SpecError, load  # noqa: E402

EXAMPLE = pathlib.Path(__file__).resolve().parents[2] / "assets" / "eksempel" / "model.yaml"
CARD = """# Ejendomskort – testvej 1
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


def _setup(tmp_path):
    (tmp_path / "bim").mkdir()
    h = tmp_path / "bim" / "model.yaml"
    shutil.copy(EXAMPLE, h)
    k = tmp_path / "kort.md"
    k.write_text(CARD, encoding="utf-8")
    return h, k


def test_import_merge_and_generate_give_same_card(tmp_path):
    h, k = _setup(tmp_path)
    assert import_card(h, k) == 0
    assert merge(h.parent / "forslag" / "ejendomskort-import.yaml") == 0
    new = k.read_text(encoding="utf-8")
    assert new.startswith("<!-- GENERERET") and new.split("\n", 1)[1] == CARD
    facts = {f["id"]: f for f in load(h)["fakta"]}
    assert facts["E-F-02@2"]["tidligere"] == "2,00 m" and facts["E-F-02@3"]["afsnit"] == "erstattede_oplysninger"
    assert generate(h, check=True) == 0


def test_fix_via_proposal_reaches_card(tmp_path):
    h, k = _setup(tmp_path)
    import_card(h, k)
    merge(h.parent / "forslag" / "ejendomskort-import.yaml")
    assert create(h, "kaelder") == 0
    f = h.parent / "forslag" / "kaelder.yaml"
    f.write_text(f.read_text(encoding="utf-8")
                 + "fakta:\n  - {id: E-F-02, vaerdi: 'ja, 2,15 m'}\n"
                   "  - {id: E-F-03, afsnit: faelles, emne: Tag, vaerdi: tegl, dato: '2026-10-16', kilde: F}\n"
                 "slet: [Å-1]\n", encoding="utf-8")
    assert merge(f) == 0
    new = k.read_text(encoding="utf-8")
    assert "| E-F-02 | Kælder | ja, 2,15 m |" in new and "| E-F-03 | Tag | tegl |" in new and "Å-1" not in new


def test_hand_edited_card_detected(tmp_path):
    h, k = _setup(tmp_path)
    import_card(h, k)
    merge(h.parent / "forslag" / "ejendomskort-import.yaml")
    k.write_text(k.read_text(encoding="utf-8").replace("1952", "1953"), encoding="utf-8")
    assert generate(h, check=True) == 1


def test_duplicate_id_and_unknown_section_rejected(tmp_path):
    h, k = _setup(tmp_path)
    import_card(h, k)
    merge(h.parent / "forslag" / "ejendomskort-import.yaml")
    t = h.read_text(encoding="utf-8")
    h.write_text(t + "  - {id: E-F-01, afsnit: faelles}\n  - {id: E-X, afsnit: findes_ikke}\n", encoding="utf-8")
    with pytest.raises(SpecError) as e:
        load(h)
    assert any("to gange" in x for x in e.value.errors) and any("ukendt afsnit" in x for x in e.value.errors)
