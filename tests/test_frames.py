#!/usr/bin/env python3
"""Tests the format check of the frame files (scripts/check_frames.py).

Run:  python3 tests/test_frames.py
"""
import pathlib
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
from check_frames import HEADER, check  # noqa: E402

FAILURES = []


def expect(name, ok, out=""):
    print(("OK   " if ok else "FEJL ") + name + ("" if ok else f"\n{out}"))
    if not ok:
        FAILURES.append(name)


def make_file(*rows):
    return HEADER + "\n|---|---|---|---|---|---|\n" + "\n".join(rows) + "\n"


def main() -> int:
    v = "| R-MUR-01 | a | b | c | d | V 2026-10-24 – kilde |"
    t = "| R-MUR-02 | a | b | c | d | T – kilde skal verificeres |"
    m = "| R-MUR-03 | a | P – mangler | P – mangler | d | P – mangler |"
    p = "| R-MUR-04 | a | b | c | d | P – murermester, 2026-11-02 |"

    errors, counts = check({"a.md": make_file(v, t, m, p)})
    expect("gyldige V, T, P og P – mangler", not errors and counts == {"V": 1, "T": 1, "P": 1, "P-mangler": 1}, errors)

    errors, _ = check({"a.md": make_file(m)})
    expect("fil med kun pladsholdere er gyldig", not errors, errors)

    errors, _ = check({"a.md": make_file("| R-MUR-01 | a | b | c | d | V – kilde |")})
    expect("V uden dato afvises", any("dato" in f for f in errors), errors)

    errors, _ = check({"a.md": make_file("| R-MUR-01 | a | b | c | d | P – almindelig praksis |")})
    expect("P uden rolle og dato afvises", any("fagrolle" in f for f in errors), errors)

    errors, _ = check({"a.md": make_file("| R-MUR-01 | a | b | c | d | se producenten |")})
    expect("ukendt status afvises", any("skal starte med" in f for f in errors), errors)

    errors, _ = check({"a.md": make_file(v), "b.md": make_file(v)})
    expect("dublet-ID afvises", any("findes også" in f for f in errors), errors)

    errors, _ = check({"a.md": make_file("| R-MUR-01 | a | b | c | V 2026-10-24 |")})
    expect("forkert antal celler afvises", any("celler" in f for f in errors), errors)

    errors, _ = check({"a.md": make_file(v)}, {"agent.md": "se R-MUR-01 og R-MUR-09"})
    expect("henvisning til ukendt ID afvises", any("R-MUR-09" in f for f in errors) and len(errors) == 1, errors)

    errors, _ = check({"a.md": "| R-MUR-01 | a | b | c | d | V 2026-10-24 |\n"})
    expect("manglende tabelhoved afvises", any("tabelhovedet" in f for f in errors), errors)

    r = subprocess.run([sys.executable, str(ROOT / "scripts" / "check_frames.py")], capture_output=True, text=True)
    expect("repoets rammefiler er gyldige", r.returncode == 0, r.stdout)

    print(f"\n{len(FAILURES)} fejl")
    return 1 if FAILURES else 0


if __name__ == "__main__":
    sys.exit(main())
