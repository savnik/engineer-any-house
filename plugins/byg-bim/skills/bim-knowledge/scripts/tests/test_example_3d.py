"""The example house for the 3D demo: skylights, system colours and export with transparent elevations."""
import json
import pathlib
import struct
import sys

import pytest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
from bimlib.build import build  # noqa: E402
from bimlib.export import export_glb  # noqa: E402
from bimlib.spec import SpecError, load  # noqa: E402

EXAMPLE = pathlib.Path(__file__).resolve().parents[2] / "assets" / "example" / "model.yaml"


def _spec(tmp_path, replace=()):
    text = EXAMPLE.read_text(encoding="utf-8")
    for old, new in replace:
        assert old in text
        text = text.replace(old, new)
    s = tmp_path / "model.yaml"
    s.write_text(text, encoding="utf-8")
    return load(s)


@pytest.fixture(scope="module")
def house(tmp_path_factory):
    tmp = tmp_path_factory.mktemp("hus")
    f, _, sv = build(_spec(tmp), tmp / "hus.ifc")
    return f, sv, tmp / "hus.ifc"


def test_skylight_sits_in_roof_face(house):
    f, sv, _ = house
    assert not sv["fejl"]
    ov = [w for w in f.by_type("IfcWindow") if w.Tag.startswith("T-OV")]
    assert sorted(w.Tag for w in ov) == ["T-OV1", "T-OV2", "T-OV3", "T-OV4"]
    for w in ov:  # each roof window fills an opening cut in a roof slab
        opening = w.FillsVoids[0].RelatingOpeningElement
        assert opening.VoidsElements[0].RelatingBuildingElement.Tag.startswith("TAG1.side")


def test_skylight_outside_roof_face_is_error(tmp_path):
    spec = _spec(tmp_path, [("{id: T-OV1, tag: TAG1, type: OV1, punkt: [2500, 2600]}",
                             "{id: T-OV1, tag: TAG1, type: OV1, punkt: [2500, 9600]}")])
    _, _, sv = build(spec, tmp_path / "m.ifc")
    assert any("T-OV1" in e and "tagflade" in e for e in sv["fejl"])


def test_rafters_in_roof(house):
    f, sv, _ = house
    roof = f.by_type("IfcRoof")[0]
    parts = [d for r in roof.IsDecomposedBy for d in r.RelatedObjects]
    rafters = [d for d in parts if d.is_a("IfcMember")]
    assert {m.PredefinedType for m in rafters} == {"RAFTER", "COLLAR", "BRACE"}
    tags = {m.Tag for m in rafters}
    assert {"TAG1.side1.S01", "TAG1.side2.S01", "TAG1.H01"} <= tags
    # trimmers: two per hole – two roof windows per face, plus the chimney on side1
    assert sum(".V" in t for t in tags if t.startswith("TAG1.side1")) == 6
    assert sum(".V" in t for t in tags if t.startswith("TAG1.side2")) == 4
    assert all(m.ContainedInStructure == () for m in rafters)  # aggregated in the roof, not contained in the storey


def test_wind_braces_under_rafters(house):
    f, _, _ = house
    braces = [m for m in f.by_type("IfcMember") if m.PredefinedType == "BRACE"]
    assert sorted(m.Tag for m in braces) == ["TAG1.side1.W01", "TAG1.side1.W02", "TAG1.side2.W01", "TAG1.side2.W02"]
    for m in braces:  # unbroken from wall plate to ridge at 45°: slope length 4250 / cos 45° times √2
        qto = next(r.RelatingPropertyDefinition for r in m.IsDefinedBy
                   if r.RelatingPropertyDefinition.is_a("IfcElementQuantity"))
        assert qto.Quantities[0].LengthValue == pytest.approx(8500, abs=150)


def test_wind_braces_validated(tmp_path):
    with pytest.raises(SpecError, match="spaer.vindbaand"):
        _spec(tmp_path, [("vindbaand: {b: 100, t: 25}", "vindbaand: {b: 100, h: 25}")])


def test_rafters_validated(tmp_path):
    with pytest.raises(SpecError, match="spaer.afstand"):
        _spec(tmp_path, [("spaer: {afstand: 900,", "spaer: {afstand: -1,")])


def test_system_colour_overrides_kind(house):
    f, _, _ = house
    seg = next(p for p in f.by_type("IfcPipeSegment") if (p.Tag or "").startswith("R-CV-R"))
    item = seg.Representation.Representations[0].Items[0]
    style = next(s for s in item.StyledByItem[0].Styles if s.is_a("IfcSurfaceStyle"))
    rgb = next(s for s in style.Styles if s.is_a("IfcSurfaceStyleShading")).SurfaceColour
    assert (round(rgb.Red * 255), round(rgb.Green * 255), round(rgb.Blue * 255)) == (130, 40, 160)


def test_system_colour_validated(tmp_path):
    with pytest.raises(SpecError):
        _spec(tmp_path, [("farve: [130, 40, 160]", "farve: [130, 40, 300]")])


def _glb_json(p):
    data = p.read_bytes()
    return json.loads(data[20:20 + struct.unpack_from("<I", data, 12)[0]])


def test_export_transparent_elevations(house, tmp_path):
    _, _, ifc = house
    out = tmp_path / "hus.glb"
    assert export_glb(ifc, out, transparent=("*-YV.1", "*-YV.4"), alpha=0.2) == 0
    doc = _glb_json(out)
    blend = {i for i, m in enumerate(doc["materials"]) if m.get("name", "").endswith("-transparent")}
    assert blend and all(doc["materials"][i]["pbrMetallicRoughness"]["baseColorFactor"][3] <= 0.2 for i in blend)
    used = {p["material"] for m in doc["meshes"] for p in m["primitives"]}
    assert used - blend  # the shared originals stay in use for everything else
    assert export_glb(ifc, tmp_path / "x.glb", transparent=("FINDES-IKKE",)) == 1
