"""Eksempelhuset til 3D-demoen: ovenlys, systemfarver og eksport med gennemsigtige facader."""
import json
import pathlib
import struct
import sys

import pytest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
from bimlib.byg import byg  # noqa: E402
from bimlib.export import export_glb  # noqa: E402
from bimlib.spec import SpecFejl, indlaes  # noqa: E402

EKSEMPEL = pathlib.Path(__file__).resolve().parents[2] / "assets" / "eksempel" / "model.yaml"


def _spec(tmp_path, erstat=()):
    tekst = EKSEMPEL.read_text(encoding="utf-8")
    for gammel, ny in erstat:
        assert gammel in tekst
        tekst = tekst.replace(gammel, ny)
    s = tmp_path / "model.yaml"
    s.write_text(tekst, encoding="utf-8")
    return indlaes(s)


@pytest.fixture(scope="module")
def hus(tmp_path_factory):
    tmp = tmp_path_factory.mktemp("hus")
    f, _, sv = byg(_spec(tmp), tmp / "hus.ifc")
    return f, sv, tmp / "hus.ifc"


def test_ovenlys_sidder_i_tagfladen(hus):
    f, sv, _ = hus
    assert not sv["fejl"]
    ov = [w for w in f.by_type("IfcWindow") if w.Tag.startswith("T-OV")]
    assert sorted(w.Tag for w in ov) == ["T-OV1", "T-OV2", "T-OV3", "T-OV4"]
    for w in ov:  # each roof window fills an opening cut in a roof slab
        aab = w.FillsVoids[0].RelatingOpeningElement
        assert aab.VoidsElements[0].RelatingBuildingElement.Tag.startswith("TAG1.side")


def test_ovenlys_uden_for_tagfladen_er_fejl(tmp_path):
    spec = _spec(tmp_path, [("{id: T-OV1, tag: TAG1, type: OV1, punkt: [2500, 2600]}",
                             "{id: T-OV1, tag: TAG1, type: OV1, punkt: [2500, 9600]}")])
    _, _, sv = byg(spec, tmp_path / "m.ifc")
    assert any("T-OV1" in e and "tagflade" in e for e in sv["fejl"])


def test_systemfarve_overstyrer_art(hus):
    f, _, _ = hus
    seg = next(p for p in f.by_type("IfcPipeSegment") if (p.Tag or "").startswith("R-CV-R"))
    item = seg.Representation.Representations[0].Items[0]
    stil = next(s for s in item.StyledByItem[0].Styles if s.is_a("IfcSurfaceStyle"))
    rgb = next(s for s in stil.Styles if s.is_a("IfcSurfaceStyleShading")).SurfaceColour
    assert (round(rgb.Red * 255), round(rgb.Green * 255), round(rgb.Blue * 255)) == (130, 40, 160)


def test_systemfarve_valideres(tmp_path):
    with pytest.raises(SpecFejl):
        _spec(tmp_path, [("farve: [130, 40, 160]", "farve: [130, 40, 300]")])


def _glb_json(p):
    data = p.read_bytes()
    return json.loads(data[20:20 + struct.unpack_from("<I", data, 12)[0]])


def test_eksport_gennemsigtige_facader(hus, tmp_path):
    _, _, ifc = hus
    ud = tmp_path / "hus.glb"
    assert export_glb(ifc, ud, transparent=("*-YV.1", "*-YV.4"), alpha=0.2) == 0
    doc = _glb_json(ud)
    blend = {i for i, m in enumerate(doc["materials"]) if m.get("name", "").endswith("-transparent")}
    assert blend and all(doc["materials"][i]["pbrMetallicRoughness"]["baseColorFactor"][3] <= 0.2 for i in blend)
    brugt = {p["material"] for m in doc["meshes"] for p in m["primitives"]}
    assert brugt - blend  # the shared originals stay in use for everything else
    assert export_glb(ifc, tmp_path / "x.glb", transparent=("FINDES-IKKE",)) == 1
