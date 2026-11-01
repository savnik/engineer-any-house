"""bim.py elplan: § 57 outlet count per room, kitchen circuits and switch type per lysgruppe."""
import pathlib
import sys

import pytest
import yaml

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
from bimlib.build import build  # noqa: E402
from bimlib.elplan import elplan, required, room_kind, switch_type  # noqa: E402
from bimlib.spec import SpecError, load  # noqa: E402

EXAMPLE = pathlib.Path(__file__).resolve().parents[2] / "assets" / "example" / "model.yaml"


def _el(id_, art, p, **kw):
    return {"id": id_, "etage": "S", "art": art, "punkt": p, **kw}


EL = [
    # Stue (S.01): two lysgrupper on one kroneafbryder + a correspondence group, 2 outlets
    _el("S01-L1", "lampe", [2000, 2000, 2400], lysgruppe="S01-A"),
    _el("S01-L2", "lampe", [3000, 2000, 2400], lysgruppe="S01-B", dimmer=True),
    _el("S01-AF1", "afbryder", [1000, 1000, 1050], lysgruppe=["S01-A", "S01-B"]),
    _el("S01-L3", "lampe", [2500, 3000, 2400], lysgruppe="S01-C"),
    _el("S01-AF2", "afbryder", [1000, 1200, 1050], lysgruppe="S01-C"),
    _el("S01-AF3", "afbryder", [4000, 1200, 1050], lysgruppe="S01-C"),
    _el("S01-AF4", "afbryder", [4000, 3000, 1050], lysgruppe="S01-C"),
    _el("S01-S1", "stikkontakt", [1500, 1000, 300]),
    _el("S01-S2", "stikkontakt", [3500, 1000, 300]),
    _el("S01-D1", "data", [3600, 1000, 300]),
    # Køkken (S.02): 3 outlets, but all on one circuit; a lamp without lysgruppe
    _el("S02-S1", "stikkontakt", [2000, 6000, 1100], kreds="K3"),
    _el("S02-S2", "stikkontakt", [2500, 6000, 1100], kreds="K3"),
    _el("S02-S3", "stikkontakt", [3000, 6000, 1100], kreds="K3"),
    _el("S02-L1", "lampe", [2500, 6000, 2400]),
]


@pytest.fixture(scope="module")
def run(tmp_path_factory):
    d = tmp_path_factory.mktemp("elplan")
    spec = yaml.safe_load(EXAMPLE.read_text(encoding="utf-8"))
    spec["installationer"] += EL
    (d / "model.yaml").write_text(yaml.safe_dump(spec, allow_unicode=True, sort_keys=False), encoding="utf-8")
    ifc = d / "m.ifc"
    build(load(d / "model.yaml"), ifc)
    return ifc, d


def test_report_counts_rules_and_switch_types(run, capsys):
    ifc, d = run
    rc = elplan(ifc, d / "elplan.md")
    out = capsys.readouterr().out
    md = (d / "elplan.md").read_text(encoding="utf-8")
    assert rc == 1  # shortfalls exist
    assert "lysgruppe S01-A: kroneafbryder" in out
    assert "lysgruppe S01-B: kroneafbryder · dæmpbar" in out
    assert "lysgruppe S01-C: korrespondance + 1 krydsafbryder" in out
    assert "§ 57, stk. 2 kræver ≥ 2" in out  # kitchen on one circuit
    assert "S02-L1 i S.02: lampe uden lysgruppe" in out
    assert "| S01-D1 | Data/tv |" in md  # data is listed but not counted as a 250 V outlet
    stue = next(line for line in md.splitlines() if line.startswith("| S.01 |"))
    assert "| 2 |" in stue
    assert "K.01" in md and "Fyrrum" in md


def test_rules():
    assert required("rum", 4.0)[0] == 1 and required("rum", 4.01)[0] == 2
    assert required("rum", 60)[0] == 10
    assert required("koekken", 6)[0] == 3
    assert required("bad", 12)[0] == 1 and required("undtaget", 40)[0] == 0
    assert room_kind("Grovkøkken") == "rum" and room_kind("Køkken-alrum") == "koekken"
    assert room_kind("Carport") == "undtaget" and room_kind("Badeværelse") == "bad"
    assert switch_type(1, False) == "1-polet afbryder" and switch_type(2, False) == "korrespondance"
    assert switch_type(4, False) == "korrespondance + 2 krydsafbrydere"


def test_spec_rejects_multiple_groups_on_lamp(tmp_path):
    spec = yaml.safe_load(EXAMPLE.read_text(encoding="utf-8"))
    spec["installationer"].append(_el("X", "lampe", [2000, 2000, 2400], lysgruppe=["A", "B"]))
    (tmp_path / "model.yaml").write_text(yaml.safe_dump(spec, allow_unicode=True), encoding="utf-8")
    with pytest.raises(SpecError, match="lysgruppe"):
        load(tmp_path / "model.yaml")
