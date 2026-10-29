#!/usr/bin/env python3
"""Copies the shared environment module (faelles/environment.py) into the plugins that have their own Python environment.

One source of truth: faelles/environment.py. Plugins are installed separately and cannot import from each other,
so each tool has its own copy (environment.py next to bim.py and fem.py).

Run after every change to faelles/environment.py:  python3 scripts/sync_environment.py [--check]
--staged checks the content in the git index (what gets committed); used by scripts/hooks/pre-commit.
"""
import pathlib
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
SOURCE = "faelles/environment.py"
COPIES = [
    "plugins/byg-bim/skills/bim-viden/scripts/environment.py",
    "plugins/byg-statik/skills/statik-viden/scripts/environment.py",
]
HEADER = "# GENERERET af scripts/sync_environment.py fra faelles/environment.py – redigér kilden, ikke denne kopi.\n"


def staged(rel: str) -> str | None:
    """Return the staged (index) text of a repo-relative path, or None if it is not in the index."""
    r = subprocess.run(["git", "-C", str(ROOT), "show", f":{rel}"], capture_output=True)
    return r.stdout.decode("utf-8") if r.returncode == 0 else None


def main() -> int:
    if "--staged" in sys.argv:
        source = staged(SOURCE)
        if source is None:
            return 0
        read = staged
    else:
        source = (ROOT / SOURCE).read_text(encoding="utf-8")

        def read(rel: str) -> str | None:
            p = ROOT / rel
            return p.read_text(encoding="utf-8") if p.exists() else None
    expected = HEADER + source
    check = "--check" in sys.argv or "--staged" in sys.argv
    mismatches = 0
    for rel in COPIES:
        if read(rel) == expected:
            continue
        if check:
            print(f"Ude af synk: {rel}")
            mismatches += 1
        else:
            (ROOT / rel).write_text(expected, encoding="utf-8")
            print(f"Opdateret: {rel}")
    return 1 if mismatches else 0


if __name__ == "__main__":
    sys.exit(main())
