"""Visibility groups per trade (IfcGroup): default, spec globs and validation."""
import pathlib
import sys

import pytest
import yaml

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
import ifcopenshell.util.element as ue  # noqa: E402
from bimlib.build import build  # noqa: E402
from bimlib.spec import SpecError, load  # noqa: E402

EXAMPLE = pathlib.Path(__file__).resolve().parents[2] / "assets" / "example" / "model.yaml"


def _spec(tmp_path, extra=""):
    s = tmp_path / "model.yaml"
    s.write_text(EXAMPLE.read_text(encoding="utf-8") + extra, encoding="utf-8")
    return load(s)


def test_each_element_in_exactly_one_top_group(tmp_path):
    f, _, sv = build(_spec(tmp_path), tmp_path / "out" / "m.ifc")
    top = [g for g in f.by_type("IfcGroup", include_subtypes=False) if not g.HasAssignments]
    all_ids = {e.id() for e in f.by_type("IfcElement") if not e.is_a("IfcFeatureElement")}
    counts = {}
    for g in top:
        for m in ue.get_grouped_by(g, is_recursive=True):
            if m.id() in all_ids:
                counts[m.id()] = counts.get(m.id(), 0) + 1
    assert set(counts) == all_ids and max(counts.values()) == 1
    assert sv["grupper"]


def test_spec_glob_wins_over_default(tmp_path):
    wid = yaml.safe_load(EXAMPLE.read_text(encoding="utf-8"))["vaegge"][0]["id"]
    extra = f"grupper:\n  - {{id: X-TEST, navn: Testgruppe, omfatter: ['{wid}']}}\n"
    f, _, _ = build(_spec(tmp_path, extra), tmp_path / "out" / "m.ifc")
    g = [g for g in f.by_type("IfcGroup") if g.Name == "Testgruppe"]
    assert g and len(ue.get_grouped_by(g[0])) >= 1


def test_unknown_parent_group_is_spec_error(tmp_path):
    with pytest.raises(SpecError):
        _spec(tmp_path, "grupper:\n  - {id: X, navn: X, under: FINDES-IKKE}\n")
