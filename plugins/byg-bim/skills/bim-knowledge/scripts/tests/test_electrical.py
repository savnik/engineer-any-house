"""Electrical installation in the example house: circuits, cables, panel parts, panel export and the diagram."""
import importlib.util
import pathlib
import sys

import pytest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
import ifcopenshell.util.element as ue  # noqa: E402
from bimlib.build import build  # noqa: E402
from bimlib.panel import panel_data, route_length  # noqa: E402
from bimlib.spec import SpecError, load  # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parents[6]
EXAMPLE = pathlib.Path(__file__).resolve().parents[2] / "assets" / "example" / "model.yaml"
EL_SCRIPTS = ROOT / "plugins" / "byg-electrical" / "skills" / "electrical-knowledge" / "scripts"
SCHEMATIC = EL_SCRIPTS.parent / "assets" / "schematic-example-house.svg"


def _spec(tmp_path, replace=()):
    text = EXAMPLE.read_text(encoding="utf-8")
    for old, new in replace:
        assert old in text
        text = text.replace(old, new, 1)
    s = tmp_path / "model.yaml"
    s.write_text(text, encoding="utf-8")
    return load(s)


def _diagram():
    sys.path.insert(0, str(EL_SCRIPTS))
    spec = importlib.util.spec_from_file_location("diagram", EL_SCRIPTS / "diagram.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture(scope="module")
def house(tmp_path_factory):
    tmp = tmp_path_factory.mktemp("hus")
    f, _, sv = build(load(EXAMPLE), tmp / "hus.ifc")
    return f, sv


def test_groups_are_circuits_under_el(house):
    f, sv = house
    assert not sv["fejl"]
    circuits = f.by_type("IfcDistributionCircuit")
    assert len(circuits) == 10
    for c in circuits:
        parent = c.Decomposes[0].RelatingObject
        assert parent.is_a() == "IfcDistributionSystem" and parent.Name == "El-forsyning"
        el = ue.get_pset(c, "Byg_El")
        assert el["kurve"] == "B" and el["sikring"] in (10, 13, 16)
    ev = next(c for c in circuits if c.Name == "Elbillader")
    assert ue.get_pset(ev, "Byg_El")["rcd"] == "RCD3"
    assert ue.get_pset(ev, "Pset_DistributionSystemCommon")["Reference"] == "10"


def test_cables_have_length(house):
    f, _ = house
    cables = f.by_type("IfcCableSegment")
    assert cables
    for c in cables:
        assert ue.get_pset(c, "Qto_CableSegmentBaseQuantities")["Length"] > 0


def test_panel_parts_aggregated(house):
    f, _ = house
    board = next(e for e in f.by_type("IfcElectricDistributionBoard") if e.Tag == "TAVLE")
    parts = {p.Tag: p for r in board.IsDecomposedBy for p in r.RelatedObjects}
    assert {"ELMAALER", "HA", "SPD", "RCD1", "RCD2", "RCD3"} <= set(parts)
    assert parts["RCD3"].is_a("IfcProtectiveDevice")
    assert parts["ELMAALER"].is_a("IfcFlowMeter")
    assert sum(p.is_a("IfcProtectiveDevice") for p in parts.values()) >= 10 + 4  # breakers, HA, SPD, RCDs
    assert ue.get_pset(parts["RCD3"], "Byg_El")["type"] == "B-EV"


def test_ip44_in_utility_room(house):
    f, _ = house
    tagged = {e.Tag: ue.get_pset(e, "Pset_ElectricalDeviceCommon") or {} for e in f.by_type("IfcElement")}
    for tag in ("L-K02-1", "A-K02", "S-K02-1", "S-K02-VM"):
        assert tagged[tag].get("IP_Code") == "IP44"


def test_route_length_follows_branches():
    trunk = [[0, 0, 0], [4000, 0, 0]]
    branch = [[2000, 0, 0], [2000, 3000, 0]]
    longest, total = route_length([trunk, branch], [0, 0, 0])
    assert longest == pytest.approx(5000) and total == pytest.approx(7000)


def test_panel_export_passes_el_check():
    _diagram()
    from el import check_panel
    data = panel_data(load(EXAMPLE))
    assert [g["nr"] for g in data["grupper"]] == list(range(1, 11))
    assert all(g["laengde"] > 0 for g in data["grupper"])
    assert data["tavle"]["stikledning"]["laengde"] > 0
    res = check_panel(data)
    assert not [x for x in res["fund"] if x["alvor"] == "advarsel"]


def test_schematic_asset_is_current(tmp_path):
    d = _diagram()
    from el import check_panel
    data = panel_data(load(EXAMPLE))
    svg = d.render(data, check_panel(data), "Tavlediagram – eksempelhuset", "bim.py panel · eksempelmodel",
                   "2026-10-31", "A")
    assert svg == SCHEMATIC.read_text(encoding="utf-8"), "kør bim.py panel + diagram.py og opdatér assets-SVG'en"


@pytest.mark.parametrize("old,new,needle", [
    ("{id: GR2, navn: Stik stue og spisestue, art: el, under: EL,",
     "{id: GR2, navn: Stik stue og spisestue, art: el, under: NOPE,", "GR2.under"),
    ("system: EL, del_af: TAVLE, el: {in: 63", "system: EL, del_af: NOPE, el: {in: 63", "HA.del_af"),
    ("nr: 9, sikring: 10, kurve: B", "nr: 9, sikring: 10, kurve: Z", ".kurve"),
    ("nr: 1, sikring: 13, kurve: B, icn: 10000, fase: L1,", "nr: 1, sikring: 13, kurve: B, icn: 10000, fase: L4,",
     ".fase"),
])
def test_bad_electrical_spec(tmp_path, old, new, needle):
    with pytest.raises(SpecError) as e:
        _spec(tmp_path, [(old, new)])
    assert any(needle in x for x in e.value.errors)
