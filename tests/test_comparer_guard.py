#!/usr/bin/env python3
"""Tests comparer_guard.py: bim-comparer and bim-lookup may only run read-only bim.py commands.

Run:  python3 tests/test_comparer_guard.py
"""
import pathlib
import sys

ROD = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROD / "plugins" / "byg-bim" / "hooks"))
import comparer_guard as v  # noqa: E402

ERRORS = []


def expect(name, cmd, allowed, agent="bim-comparer"):
    ok = (v.check(cmd, agent) is None) == allowed
    print(("OK   " if ok else "FEJL ") + name + ("" if ok else f"  → {v.check(cmd, agent)}"))
    if not ok:
        ERRORS.append(name)


def main() -> int:
    s = "byg-cases/x/bim/comparison/K1-r1"
    expect("compare tilladt", f'python3 "$BIM" compare m.ifc a.yaml --out {s}', True)
    expect("check med --out under comparison tilladt", f'python3 "$BIM" check m.ifc --out {s}/tjek --model-note n.md', True)
    expect("check uden --out afvises", 'python3 "$BIM" check m.ifc', False)
    expect("check med --out uden for comparison afvises", 'python3 "$BIM" check m.ifc --out byg-cases/x/bim/out', False)
    expect("check med --draw afvises", f'python3 "$BIM" check m.ifc --out {s} --draw', False)
    expect("build afvises", 'python3 "$BIM" build model.yaml', False)
    expect("merge afvises", 'python3 "$BIM" merge proposals/bim-1.yaml', False)
    expect("kædede kommandoer afvises", f'python3 "$BIM" check m.ifc --out {s}; rm -rf x', False)
    expect("decode check tilladt", 'python3 "$BIM" decode check a.yaml', True)
    expect("decode template afvises", 'python3 "$BIM" decode template', False)
    expect("gammel dansk kommando afvises", 'python3 "$BIM" sammenlign m.ifc a.yaml', False)
    expect("sammenligner: measure tilladt", 'python3 "$BIM" measure out/m.ifc K-YV.1 K-YV.3', True)
    o = "bim-lookup"
    expect("opslag: measure tilladt", 'python3 "$BIM" measure out/m.ifc --space Fyrrum', True, o)
    expect("opslag: show/find/info tilladt", 'python3 ~/x/bim.py show ud/m.ifc K-IV1', True, o)
    expect("opslag: BIM-præfiks tilladt", 'BIM=~/x/bim.py; python3 "$BIM" info ud/m.ifc', True, o)
    expect("opslag: build afvises", 'python3 "$BIM" build model.yaml', False, o)
    expect("opslag: draw afvises", 'python3 "$BIM" draw ud/m.ifc', False, o)
    expect("opslag: check afvises", f'python3 "$BIM" check m.ifc --out {s}', False, o)
    expect("opslag: omdirigering afvises", 'python3 "$BIM" info m.ifc > x.txt', False, o)
    print(f"\n{len(ERRORS)} fejl")
    return 1 if ERRORS else 0


if __name__ == "__main__":
    sys.exit(main())
