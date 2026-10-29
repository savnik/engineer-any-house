#!/usr/bin/env python3
"""Tests the format check of the frame files (scripts/check_frames.py).

Kør:  python3 tests/test_frames.py
"""
import pathlib
import subprocess
import sys

ROD = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROD / "scripts"))
from check_frames import HOVED, tjek  # noqa: E402

FEJL = []


def forvent(navn, ok, ud=""):
    print(("OK   " if ok else "FEJL ") + navn + ("" if ok else f"\n{ud}"))
    if not ok:
        FEJL.append(navn)


def fil(*rækker):
    return HOVED + "\n|---|---|---|---|---|---|\n" + "\n".join(rækker) + "\n"


def main() -> int:
    v = "| R-MUR-01 | a | b | c | d | V 2026-10-24 – kilde |"
    t = "| R-MUR-02 | a | b | c | d | T – kilde skal verificeres |"
    m = "| R-MUR-03 | a | P – mangler | P – mangler | d | P – mangler |"
    p = "| R-MUR-04 | a | b | c | d | P – murermester, 2026-11-02 |"

    fejl, antal = tjek({"a.md": fil(v, t, m, p)})
    forvent("gyldige V, T, P og P – mangler", not fejl and antal == {"V": 1, "T": 1, "P": 1, "P-mangler": 1}, fejl)

    fejl, _ = tjek({"a.md": fil(m)})
    forvent("fil med kun pladsholdere er gyldig", not fejl, fejl)

    fejl, _ = tjek({"a.md": fil("| R-MUR-01 | a | b | c | d | V – kilde |")})
    forvent("V uden dato afvises", any("dato" in f for f in fejl), fejl)

    fejl, _ = tjek({"a.md": fil("| R-MUR-01 | a | b | c | d | P – almindelig praksis |")})
    forvent("P uden rolle og dato afvises", any("fagrolle" in f for f in fejl), fejl)

    fejl, _ = tjek({"a.md": fil("| R-MUR-01 | a | b | c | d | se producenten |")})
    forvent("ukendt status afvises", any("skal starte med" in f for f in fejl), fejl)

    fejl, _ = tjek({"a.md": fil(v), "b.md": fil(v)})
    forvent("dublet-ID afvises", any("findes også" in f for f in fejl), fejl)

    fejl, _ = tjek({"a.md": fil("| R-MUR-01 | a | b | c | V 2026-10-24 |")})
    forvent("forkert antal celler afvises", any("celler" in f for f in fejl), fejl)

    fejl, _ = tjek({"a.md": fil(v)}, {"agent.md": "se R-MUR-01 og R-MUR-09"})
    forvent("henvisning til ukendt ID afvises", any("R-MUR-09" in f for f in fejl) and len(fejl) == 1, fejl)

    fejl, _ = tjek({"a.md": "| R-MUR-01 | a | b | c | d | V 2026-10-24 |\n"})
    forvent("manglende tabelhoved afvises", any("tabelhovedet" in f for f in fejl), fejl)

    r = subprocess.run([sys.executable, str(ROD / "scripts" / "check_frames.py")], capture_output=True, text=True)
    forvent("repoets rammefiler er gyldige", r.returncode == 0, r.stdout)

    print(f"\n{len(FEJL)} fejl")
    return 1 if FEJL else 0


if __name__ == "__main__":
    sys.exit(main())
