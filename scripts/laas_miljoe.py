#!/usr/bin/env python3
"""Låser plugin-værktøjernes Python-miljøer: requirements*.in (direkte afhængigheder) → requirements*.txt (alle
pakker fastlåst, også de transitive, for alle platforme og Python >= 3.11).

  python3 scripts/laas_miljoe.py             Lås efter en ændring i en .in-fil (beholder de øvrige låste versioner)
  python3 scripts/laas_miljoe.py --opgrader  Løft alle transitive pakker til nyeste tilladte version
  python3 scripts/laas_miljoe.py --check     Uden netværk: findes låsen, og har den præcis .in-filens versioner?

Kræver uv (https://docs.astral.sh/uv/) – kun til at låse; brugerne kan installere med både uv og pip.
Kør derefter `bim.py opsaet` / `fem.py opsaet` og testene, før du committer.
"""
import pathlib
import re
import shutil
import subprocess
import sys

ROD = pathlib.Path(__file__).resolve().parent.parent
PYTHON = "3.11"  # = MIN_PYTHON i faelles/miljoe.py
LAASE = [
    "plugins/byg-bim/skills/bim-viden/scripts/requirements.in",
    "plugins/byg-bim/skills/bim-viden/scripts/requirements-test.in",
    "plugins/byg-statik/skills/statik-viden/scripts/requirements-fem.in",
]
PIN = re.compile(r"^([A-Za-z0-9._-]+)==([^\s;]+)")


def norm(navn: str) -> str:
    return re.sub(r"[-_.]+", "-", navn).lower()


def direkte(ind: pathlib.Path) -> dict[str, str]:
    """Pins in a .in file, following -r includes."""
    pins = {}
    for linje in ind.read_text(encoding="utf-8").splitlines():
        linje = linje.split("#", 1)[0].strip()
        if linje.startswith("-r "):
            pins.update(direkte(ind.parent / linje[3:].strip()))
        elif m := PIN.match(linje):
            pins[norm(m[1])] = m[2]
        elif linje:
            raise SystemExit(f"{ind.relative_to(ROD)}: '{linje}' – direkte afhængigheder skal fastlåses med ==")
    return pins


def laaste(txt: pathlib.Path) -> dict[str, set[str]]:
    pins: dict[str, set[str]] = {}
    for linje in txt.read_text(encoding="utf-8").splitlines():
        if m := PIN.match(linje):
            pins.setdefault(norm(m[1]), set()).add(m[2])
    return pins


def check() -> int:
    fejl = []
    for rel in LAASE:
        ind = ROD / rel
        txt = ind.with_suffix(".txt")
        if not txt.exists():
            fejl.append(f"{txt.relative_to(ROD)} mangler")
            continue
        l = laaste(txt)
        for navn, v in direkte(ind).items():
            if l.get(navn) != {v}:
                fejl.append(f"{txt.relative_to(ROD)}: {navn}=={v} i .in, men {sorted(l.get(navn, [])) or 'mangler'} i låsen")
    for f in fejl:
        print(f)
    if fejl:
        print("Kør: python3 scripts/laas_miljoe.py")
    return 1 if fejl else 0


def main() -> int:
    if "--check" in sys.argv:
        return check()
    uv = shutil.which("uv")
    if not uv:
        print("uv mangler: https://docs.astral.sh/uv/getting-started/installation/", file=sys.stderr)
        return 2
    for rel in LAASE:
        ind = ROD / rel
        cmd = [uv, "pip", "compile", "-q", "--universal", "--python-version", PYTHON,
               "--custom-compile-command", "python3 scripts/laas_miljoe.py", ind.name, "-o", ind.with_suffix(".txt").name]
        if "--opgrader" in sys.argv:
            cmd.append("--upgrade")
        r = subprocess.run(cmd, cwd=ind.parent)
        if r.returncode:
            return r.returncode
        print(f"Låst: {ind.with_suffix('.txt').relative_to(ROD)}")
    return check()


if __name__ == "__main__":
    sys.exit(main())
