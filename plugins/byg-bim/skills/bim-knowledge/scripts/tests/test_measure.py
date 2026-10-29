"""bim.py measure: dimensions of walls, rooms, distances and storeys from the example model (mm)."""
import pathlib
import re
import sys

import pytest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
from bimlib.build import build  # noqa: E402
from bimlib.measure import measure  # noqa: E402
from bimlib.spec import load  # noqa: E402

EXAMPLE = pathlib.Path(__file__).resolve().parents[2] / "assets" / "example" / "model.yaml"


@pytest.fixture(scope="module")
def ifc(tmp_path_factory):
    d = tmp_path_factory.mktemp("maal")
    out = d / "m.ifc"
    build(load(EXAMPLE), out)
    return out


def _run(capsys, *args, **kw):
    rc = measure(*args, **kw)
    return rc, capsys.readouterr().out


def test_basement_wall_dims_openings_and_source(ifc, capsys):
    rc, out = _run(capsys, ifc, "K-YV.1")
    assert rc == 0
    assert "længde (største) 10000 · tykkelse 300 · højde 2400" in out
    assert "underkant kote -2400" in out
    assert "(inderside)" in out and "(yderside)" in out
    assert "K-V1 (Window): fra væggens start 1500 · bredde 800 · brystning 1500 · højde 500" in out
    assert "Kilde=D" in out and "Kældertegning 1937" in out


def test_interior_wall_has_no_inner_outer_side(ifc, capsys):
    rc, out = _run(capsys, ifc, "k-iv1")  # case does not matter
    assert rc == 0
    assert "tykkelse 128" in out and "inderside" not in out
    assert "K-D1 (Door)" in out


def test_room_by_name_and_id(ifc, capsys):
    for key in ("Fyrrum", "K.01"):
        rc, out = _run(capsys, ifc, room=key)
        assert rc == 0
        assert "indvendigt 7900 × 4636 (rektangulært)" in out
        assert "gulvareal 36.62 m²" in out


def test_distance_between_two_walls(ifc, capsys):
    rc, out = _run(capsys, ifc, "K-YV.1", "K-YV.3")
    assert rc == 0
    assert "vandret fri afstand 7900" in out
    assert out.count("kilde:") == 2


def test_storey_table(ifc, capsys):
    rc, out = _run(capsys, ifc, storey_name="kælder")
    assert rc == 0
    assert out.startswith("Kælder: 5 vægge")
    assert re.search(r"K-YV\.2 \| Kælderydervæg beton 300 \| 8200 \| 300 \| 2400 \| D", out)
    assert "K.01 Fyrrum" in out


def test_unknown_element_and_room_that_is_not_room(ifc, capsys):
    assert _run(capsys, ifc, "FINDES-IKKE")[0] == 1
    assert _run(capsys, ifc, room="K-YV.1")[0] == 1
    assert _run(capsys, ifc)[0] == 2


def test_spec_built_before_measuring(capsys):
    rc, out = _run(capsys, EXAMPLE, "S-IV2")
    assert rc == 0
    assert "tykkelse 96" in out and "Kilde=M" in out
