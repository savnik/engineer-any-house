#!/usr/bin/env python3
"""Tester sammenligner_vagt.py: bim-sammenligneren må kun køre læsende bim.py-kommandoer (nu også tjek med --ud).

Kør:  python3 tests/test_sammenligner_vagt.py
"""
import pathlib
import sys

ROD = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROD / "plugins" / "byg-bim" / "hooks"))
import sammenligner_vagt as v  # noqa: E402

FEJL = []


def forvent(navn, cmd, tilladt):
    ok = (v.tjek(cmd) is None) == tilladt
    print(("OK   " if ok else "FEJL ") + navn + ("" if ok else f"  → {v.tjek(cmd)}"))
    if not ok:
        FEJL.append(navn)


def main() -> int:
    s = "byg-sager/x/bim/sammenligning/K1-r1"
    forvent("sammenlign tilladt", f'python3 "$BIM" sammenlign m.ifc a.yaml --ud {s}', True)
    forvent("tjek med --ud under sammenligning tilladt", f'python3 "$BIM" tjek m.ifc --ud {s}/tjek --notat n.md', True)
    forvent("tjek uden --ud afvises", 'python3 "$BIM" tjek m.ifc', False)
    forvent("tjek med --ud uden for sammenligning afvises", 'python3 "$BIM" tjek m.ifc --ud byg-sager/x/bim/ud', False)
    forvent("tjek med --tegn afvises", f'python3 "$BIM" tjek m.ifc --ud {s} --tegn', False)
    forvent("byg afvises", 'python3 "$BIM" byg model.yaml', False)
    forvent("flet afvises", 'python3 "$BIM" flet forslag/bim-1.yaml', False)
    forvent("kædede kommandoer afvises", f'python3 "$BIM" tjek m.ifc --ud {s}; rm -rf x', False)
    print(f"\n{len(FEJL)} fejl")
    return 1 if FEJL else 0


if __name__ == "__main__":
    sys.exit(main())
