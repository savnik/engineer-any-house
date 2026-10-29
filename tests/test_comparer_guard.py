#!/usr/bin/env python3
"""Tester comparer_guard.py: bim-sammenligneren og bim-opslag må kun køre læsende bim.py-kommandoer.

Kør:  python3 tests/test_comparer_guard.py
"""
import pathlib
import sys

ROD = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROD / "plugins" / "byg-bim" / "hooks"))
import comparer_guard as v  # noqa: E402

FEJL = []


def forvent(navn, cmd, tilladt, agent="bim-sammenligner"):
    ok = (v.tjek(cmd, agent) is None) == tilladt
    print(("OK   " if ok else "FEJL ") + navn + ("" if ok else f"  → {v.tjek(cmd, agent)}"))
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
    forvent("sammenligner: maal tilladt", 'python3 "$BIM" maal ud/m.ifc K-YV.1 K-YV.3', True)
    o = "bim-opslag"
    forvent("opslag: maal tilladt", 'python3 "$BIM" maal ud/m.ifc --rum Fyrrum', True, o)
    forvent("opslag: vis/find/info tilladt", 'python3 ~/x/bim.py vis ud/m.ifc K-IV1', True, o)
    forvent("opslag: BIM-præfiks tilladt", 'BIM=~/x/bim.py; python3 "$BIM" info ud/m.ifc', True, o)
    forvent("opslag: byg afvises", 'python3 "$BIM" byg model.yaml', False, o)
    forvent("opslag: tegn afvises", 'python3 "$BIM" tegn ud/m.ifc', False, o)
    forvent("opslag: tjek afvises", f'python3 "$BIM" tjek m.ifc --ud {s}', False, o)
    forvent("opslag: omdirigering afvises", 'python3 "$BIM" info m.ifc > x.txt', False, o)
    print(f"\n{len(FEJL)} fejl")
    return 1 if FEJL else 0


if __name__ == "__main__":
    sys.exit(main())
