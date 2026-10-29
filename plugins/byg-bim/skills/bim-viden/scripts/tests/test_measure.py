"""bim.py maal: mål af vægge, rum, afstande og etager fra eksempelmodellen (mm)."""
import pathlib
import re
import sys

import pytest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
from bimlib.build import byg  # noqa: E402
from bimlib.measure import maal  # noqa: E402
from bimlib.spec import indlaes  # noqa: E402

EKSEMPEL = pathlib.Path(__file__).resolve().parents[2] / "assets" / "eksempel" / "model.yaml"


@pytest.fixture(scope="module")
def ifc(tmp_path_factory):
    d = tmp_path_factory.mktemp("maal")
    ud = d / "m.ifc"
    byg(indlaes(EKSEMPEL), ud)
    return ud


def _kør(capsys, *args, **kw):
    rc = maal(*args, **kw)
    return rc, capsys.readouterr().out


def test_kaeldervaeg_maal_aabninger_og_kilde(ifc, capsys):
    rc, ud = _kør(capsys, ifc, "K-YV.1")
    assert rc == 0
    assert "længde (største) 10000 · tykkelse 300 · højde 2400" in ud
    assert "underkant kote -2400" in ud
    assert "(inderside)" in ud and "(yderside)" in ud
    assert "K-V1 (Window): fra væggens start 1500 · bredde 800 · brystning 1500 · højde 500" in ud
    assert "Kilde=D" in ud and "Kældertegning 1937" in ud


def test_indervaeg_har_ingen_inder_og_yderside(ifc, capsys):
    rc, ud = _kør(capsys, ifc, "k-iv1")  # store/små bogstaver er ligegyldige
    assert rc == 0
    assert "tykkelse 128" in ud and "inderside" not in ud
    assert "K-D1 (Door)" in ud


def test_rum_efter_navn_og_id(ifc, capsys):
    for noegle in ("Fyrrum", "K.01"):
        rc, ud = _kør(capsys, ifc, rum=noegle)
        assert rc == 0
        assert "indvendigt 7900 × 4636 (rektangulært)" in ud
        assert "gulvareal 36.62 m²" in ud


def test_afstand_mellem_to_vaegge(ifc, capsys):
    rc, ud = _kør(capsys, ifc, "K-YV.1", "K-YV.3")
    assert rc == 0
    assert "vandret fri afstand 7900" in ud
    assert ud.count("kilde:") == 2


def test_etage_tabel(ifc, capsys):
    rc, ud = _kør(capsys, ifc, etage_navn="kælder")
    assert rc == 0
    assert ud.startswith("Kælder: 5 vægge")
    assert re.search(r"K-YV\.2 \| Kælderydervæg beton 300 \| 8200 \| 300 \| 2400 \| D", ud)
    assert "K.01 Fyrrum" in ud


def test_ukendt_element_og_rum_der_ikke_er_rum(ifc, capsys):
    assert _kør(capsys, ifc, "FINDES-IKKE")[0] == 1
    assert _kør(capsys, ifc, rum="K-YV.1")[0] == 1
    assert _kør(capsys, ifc)[0] == 2


def test_spec_bygges_foer_maaling(capsys):
    rc, ud = _kør(capsys, EKSEMPEL, "S-IV2")
    assert rc == 0
    assert "tykkelse 96" in ud and "Kilde=M" in ud
