#!/usr/bin/env python3
"""Tests comparer_guard.py: bim-sammenligner and bim-opslag may only run read-only bim.py commands.

Run:  python3 tests/test_comparer_guard.py
"""
import pathlib
import sys

ROD = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROD / "plugins" / "byg-bim" / "hooks"))
import comparer_guard as v  # noqa: E402

ERRORS = []


def expect(name, cmd, allowed, agent="bim-sammenligner"):
    ok = (v.check(cmd, agent) is None) == allowed
    print(("OK   " if ok else "FEJL ") + name + ("" if ok else f"  → {v.check(cmd, agent)}"))
    if not ok:
        ERRORS.append(name)


def main() -> int:
    s = "byg-sager/x/bim/sammenligning/K1-r1"
    expect("sammenlign tilladt", f'python3 "$BIM" sammenlign m.ifc a.yaml --ud {s}', True)
    expect("tjek med --ud under sammenligning tilladt", f'python3 "$BIM" tjek m.ifc --ud {s}/tjek --notat n.md', True)
    expect("tjek uden --ud afvises", 'python3 "$BIM" tjek m.ifc', False)
    expect("tjek med --ud uden for sammenligning afvises", 'python3 "$BIM" tjek m.ifc --ud byg-sager/x/bim/ud', False)
    expect("tjek med --tegn afvises", f'python3 "$BIM" tjek m.ifc --ud {s} --tegn', False)
    expect("byg afvises", 'python3 "$BIM" byg model.yaml', False)
    expect("flet afvises", 'python3 "$BIM" flet forslag/bim-1.yaml', False)
    expect("kædede kommandoer afvises", f'python3 "$BIM" tjek m.ifc --ud {s}; rm -rf x', False)
    expect("sammenligner: maal tilladt", 'python3 "$BIM" maal ud/m.ifc K-YV.1 K-YV.3', True)
    o = "bim-opslag"
    expect("opslag: maal tilladt", 'python3 "$BIM" maal ud/m.ifc --rum Fyrrum', True, o)
    expect("opslag: vis/find/info tilladt", 'python3 ~/x/bim.py vis ud/m.ifc K-IV1', True, o)
    expect("opslag: BIM-præfiks tilladt", 'BIM=~/x/bim.py; python3 "$BIM" info ud/m.ifc', True, o)
    expect("opslag: byg afvises", 'python3 "$BIM" byg model.yaml', False, o)
    expect("opslag: tegn afvises", 'python3 "$BIM" tegn ud/m.ifc', False, o)
    expect("opslag: tjek afvises", f'python3 "$BIM" tjek m.ifc --ud {s}', False, o)
    expect("opslag: omdirigering afvises", 'python3 "$BIM" info m.ifc > x.txt', False, o)
    print(f"\n{len(ERRORS)} fejl")
    return 1 if ERRORS else 0


if __name__ == "__main__":
    sys.exit(main())
