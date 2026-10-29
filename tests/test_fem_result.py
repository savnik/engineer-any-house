#!/usr/bin/env python3
"""Tests `fem.py result`: lookup in the saved fem.json without recalculating, refused when stale.

Run:  python3 tests/test_fem_result.py   (requires the statik environment: fem.py setup)
"""
import os
import pathlib
import subprocess
import sys
import tempfile

ROOT = pathlib.Path(__file__).resolve().parent.parent
FEM = ROOT / "plugins" / "byg-structural" / "skills" / "structural-knowledge" / "scripts" / "fem.py"
VPY = pathlib.Path(os.environ.get("BYG_STATIK_VENV", pathlib.Path.home() / ".local" / "share" / "byg-structural" / "venv")) / "bin" / "python"
FAILURES = []


def run_fem(*args):
    r = subprocess.run([sys.executable, str(FEM), *map(str, args)], capture_output=True, text=True)
    return r.returncode, r.stdout + r.stderr


def expect(name, ok, out=""):
    print(("OK   " if ok else "FEJL ") + name + ("" if ok else f"\n{out}"))
    if not ok:
        FAILURES.append(name)


def main() -> int:
    if not VPY.exists():
        print("SPRUNGET OVER: statik-miljøet mangler (fem.py setup)")
        return 0
    with tempfile.TemporaryDirectory() as tmp:
        spec = pathlib.Path(tmp) / "fem.yaml"
        spec.write_text(run_fem("template")[1], encoding="utf-8")

        rc, out = run_fem("result", spec)
        expect("uden gemt resultat: afvist (rc 1), statikeren skal regne", rc == 1 and "ikke regnet" in out, out)

        run_fem("calc", spec)
        rc, out = run_fem("result", spec)
        expect("opslag: reaktioner, M, δ og L/δ", rc == 0 and "A: Rz 25,9" in out and "(L/423, krav L/400: OK)" in out, out)
        expect("opslag: kilde med spec-sha og OVERSLAG", "ingen ny beregning" in out and "OVERSLAG" in out, out)

        rc, out = run_fem("result", spec, "--combo", "SLS-karakteristisk", "--element", "b1")
        expect("--combo og --element filtrerer (store/små bogstaver ligegyldige)",
                rc == 0 and out.count("ligevægt") == 1 and "B1 HEB160" in out, out)
        rc, out = run_fem("result", spec, "--element", "X9")
        expect("ukendt element: rc 2 med kendte navne", rc == 2 and "kendte: B1" in out, out)
        rc, out = run_fem("result", spec, "--combo", "FINDES-IKKE")
        expect("ukendt kombination: rc 2", rc == 2 and "ukendt kombination" in out, out)

        spec.write_text(spec.read_text(encoding="utf-8").replace("HEB160", "HEB180"), encoding="utf-8")
        rc, out = run_fem("result", spec)
        expect("fem.yaml ændret efter regn: FORÆLDET, ingen tal", rc == 1 and "FORÆLDET" in out and "Rz" not in out, out)

        run_fem("calc", spec, "--set", "elementer.B1.profil=HEB200")
        rc, out = run_fem("result", spec)
        expect("result regnet med --set: afvist", rc == 1 and "ændrede input" in out and "Rz" not in out, out)
    print("\nALLE TESTS BESTÅET" if not FAILURES else f"\n{len(FAILURES)} FEJL")
    return 1 if FAILURES else 0


if __name__ == "__main__":
    sys.exit(main())
