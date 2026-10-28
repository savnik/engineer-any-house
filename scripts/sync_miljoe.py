#!/usr/bin/env python3
"""Kopierer det fælles miljømodul (faelles/miljoe.py) ind i de plugins, der har deres eget Python-miljø.

Én kilde til sandhed: faelles/miljoe.py. Plugins installeres hver for sig og kan ikke importere på tværs,
så hvert værktøj har sin egen kopi (miljoe.py ved siden af bim.py og fem.py).

Kør efter hver ændring i faelles/miljoe.py:  python3 scripts/sync_miljoe.py [--check]
--staged tjekker indholdet i git-indekset (det, der committes); bruges af scripts/hooks/pre-commit.
"""
import pathlib
import subprocess
import sys

ROD = pathlib.Path(__file__).resolve().parent.parent
KILDE = "faelles/miljoe.py"
KOPIER = [
    "plugins/byg-bim/skills/bim-viden/scripts/miljoe.py",
    "plugins/byg-statik/skills/statik-viden/scripts/miljoe.py",
]
HOVED = "# GENERERET af scripts/sync_miljoe.py fra faelles/miljoe.py – redigér kilden, ikke denne kopi.\n"


def staged(rel: str) -> str | None:
    """Return the staged (index) text of a repo-relative path, or None if it is not in the index."""
    r = subprocess.run(["git", "-C", str(ROD), "show", f":{rel}"], capture_output=True)
    return r.stdout.decode("utf-8") if r.returncode == 0 else None


def main() -> int:
    if "--staged" in sys.argv:
        kilde = staged(KILDE)
        if kilde is None:
            return 0
        laes = staged
    else:
        kilde = (ROD / KILDE).read_text(encoding="utf-8")

        def laes(rel: str) -> str | None:
            p = ROD / rel
            return p.read_text(encoding="utf-8") if p.exists() else None
    forventet = HOVED + kilde
    check = "--check" in sys.argv or "--staged" in sys.argv
    afvigelser = 0
    for rel in KOPIER:
        if laes(rel) == forventet:
            continue
        if check:
            print(f"Ude af synk: {rel}")
            afvigelser += 1
        else:
            (ROD / rel).write_text(forventet, encoding="utf-8")
            print(f"Opdateret: {rel}")
    return 1 if afvigelser else 0


if __name__ == "__main__":
    sys.exit(main())
