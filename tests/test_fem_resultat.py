#!/usr/bin/env python3
"""Tests `fem.py resultat`: lookup in the saved fem.json without recalculating, refused when stale.

Kør:  python3 tests/test_fem_resultat.py   (kræver statik-miljøet: fem.py opsaet)
"""
import pathlib
import subprocess
import sys
import tempfile

ROD = pathlib.Path(__file__).resolve().parent.parent
FEM = ROD / "plugins" / "byg-statik" / "skills" / "statik-viden" / "scripts" / "fem.py"
VPY = pathlib.Path.home() / ".local" / "share" / "byg-statik" / "venv" / "bin" / "python"
FEJL = []


def fem(*args):
    r = subprocess.run([sys.executable, str(FEM), *map(str, args)], capture_output=True, text=True)
    return r.returncode, r.stdout + r.stderr


def forvent(navn, ok, ud=""):
    print(("OK   " if ok else "FEJL ") + navn + ("" if ok else f"\n{ud}"))
    if not ok:
        FEJL.append(navn)


def main() -> int:
    if not VPY.exists():
        print("SPRUNGET OVER: statik-miljøet mangler (fem.py opsaet)")
        return 0
    with tempfile.TemporaryDirectory() as tmp:
        spec = pathlib.Path(tmp) / "fem.yaml"
        spec.write_text(fem("skabelon")[1], encoding="utf-8")

        rc, ud = fem("resultat", spec)
        forvent("uden gemt resultat: afvist (rc 1), statikeren skal regne", rc == 1 and "ikke regnet" in ud, ud)

        fem("regn", spec)
        rc, ud = fem("resultat", spec)
        forvent("opslag: reaktioner, M, δ og L/δ", rc == 0 and "A: Rz 25,9" in ud and "(L/423, krav L/400: OK)" in ud, ud)
        forvent("opslag: kilde med spec-sha og OVERSLAG", "ingen ny beregning" in ud and "OVERSLAG" in ud, ud)

        rc, ud = fem("resultat", spec, "--kombi", "SLS-karakteristisk", "--element", "b1")
        forvent("--kombi og --element filtrerer (store/små bogstaver ligegyldige)",
                rc == 0 and ud.count("ligevægt") == 1 and "B1 HEB160" in ud, ud)
        rc, ud = fem("resultat", spec, "--element", "X9")
        forvent("ukendt element: rc 2 med kendte navne", rc == 2 and "kendte: B1" in ud, ud)
        rc, ud = fem("resultat", spec, "--kombi", "FINDES-IKKE")
        forvent("ukendt kombination: rc 2", rc == 2 and "ukendt kombination" in ud, ud)

        spec.write_text(spec.read_text(encoding="utf-8").replace("HEB160", "HEB180"), encoding="utf-8")
        rc, ud = fem("resultat", spec)
        forvent("fem.yaml ændret efter regn: FORÆLDET, ingen tal", rc == 1 and "FORÆLDET" in ud and "Rz" not in ud, ud)

        fem("regn", spec, "--saet", "elementer.B1.profil=HEB200")
        rc, ud = fem("resultat", spec)
        forvent("resultat regnet med --saet: afvist", rc == 1 and "ændrede input" in ud and "Rz" not in ud, ud)
    print("\nALLE TESTS BESTÅET" if not FEJL else f"\n{len(FEJL)} FEJL")
    return 1 if FEJL else 0


if __name__ == "__main__":
    sys.exit(main())
