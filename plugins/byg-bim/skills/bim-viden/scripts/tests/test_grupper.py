"""Synlighedsgrupper pr. fag (IfcGroup): standard, spec-globs og validering."""
import pathlib
import sys

import pytest
import yaml

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
import ifcopenshell.util.element as ue  # noqa: E402
from bimlib.byg import byg  # noqa: E402
from bimlib.spec import SpecFejl, indlaes  # noqa: E402

EKSEMPEL = pathlib.Path(__file__).resolve().parents[2] / "assets" / "eksempel" / "model.yaml"


def _spec(tmp_path, ekstra=""):
    s = tmp_path / "model.yaml"
    s.write_text(EKSEMPEL.read_text(encoding="utf-8") + ekstra, encoding="utf-8")
    return indlaes(s)


def test_hvert_element_i_praecis_en_topgruppe(tmp_path):
    f, _, sv = byg(_spec(tmp_path), tmp_path / "ud" / "m.ifc")
    top = [g for g in f.by_type("IfcGroup", include_subtypes=False) if not g.HasAssignments]
    alle = {e.id() for e in f.by_type("IfcElement") if not e.is_a("IfcFeatureElement")}
    taelling = {}
    for g in top:
        for m in ue.get_grouped_by(g, is_recursive=True):
            if m.id() in alle:
                taelling[m.id()] = taelling.get(m.id(), 0) + 1
    assert set(taelling) == alle and max(taelling.values()) == 1
    assert sv["grupper"]


def test_spec_glob_vinder_over_standard(tmp_path):
    vid = yaml.safe_load(EKSEMPEL.read_text(encoding="utf-8"))["vaegge"][0]["id"]
    ekstra = f"grupper:\n  - {{id: X-TEST, navn: Testgruppe, omfatter: ['{vid}']}}\n"
    f, _, _ = byg(_spec(tmp_path, ekstra), tmp_path / "ud" / "m.ifc")
    g = [g for g in f.by_type("IfcGroup") if g.Name == "Testgruppe"]
    assert g and len(ue.get_grouped_by(g[0])) >= 1


def test_ukendt_overgruppe_er_specfejl(tmp_path):
    with pytest.raises(SpecFejl):
        _spec(tmp_path, "grupper:\n  - {id: X, navn: X, under: FINDES-IKKE}\n")
