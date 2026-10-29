#!/usr/bin/env python3
"""Locks the plugin tools' Python environments: requirements*.in (direct dependencies) → requirements*.txt (all
packages pinned, transitive ones too, for all platforms and Python >= 3.11).

  python3 scripts/lock_environment.py             Lock after a change to an .in file (keeps the other locked versions)
  python3 scripts/lock_environment.py --upgrade   Raise all transitive packages to the newest allowed version
  python3 scripts/lock_environment.py --check     Without network: does the lock exist, and does it have exactly the .in file's versions?

Requires uv (https://docs.astral.sh/uv/) – only for locking; users can install with both uv and pip.
Then run `bim.py setup` / `fem.py setup` and the tests before you commit.
"""
import pathlib
import re
import shutil
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
PYTHON = "3.11"  # = MIN_PYTHON in shared/environment.py
LOCKS = [
    "plugins/byg-bim/skills/bim-knowledge/scripts/requirements.in",
    "plugins/byg-bim/skills/bim-knowledge/scripts/requirements-test.in",
    "plugins/byg-structural/skills/structural-knowledge/scripts/requirements-fem.in",
]
PIN = re.compile(r"^([A-Za-z0-9._-]+)==([^\s;]+)")


def norm(name: str) -> str:
    return re.sub(r"[-_.]+", "-", name).lower()


def direct_pins(in_file: pathlib.Path) -> dict[str, str]:
    """Pins in a .in file, following -r includes."""
    pins = {}
    for line in in_file.read_text(encoding="utf-8").splitlines():
        line = line.split("#", 1)[0].strip()
        if line.startswith("-r "):
            pins.update(direct_pins(in_file.parent / line[3:].strip()))
        elif m := PIN.match(line):
            pins[norm(m[1])] = m[2]
        elif line:
            raise SystemExit(f"{in_file.relative_to(ROOT)}: '{line}' – direkte afhængigheder skal fastlåses med ==")
    return pins


def locked_pins(txt: pathlib.Path) -> dict[str, set[str]]:
    pins: dict[str, set[str]] = {}
    for line in txt.read_text(encoding="utf-8").splitlines():
        if m := PIN.match(line):
            pins.setdefault(norm(m[1]), set()).add(m[2])
    return pins


def check() -> int:
    errors = []
    for rel in LOCKS:
        in_file = ROOT / rel
        txt = in_file.with_suffix(".txt")
        if not txt.exists():
            errors.append(f"{txt.relative_to(ROOT)} mangler")
            continue
        locked = locked_pins(txt)
        for name, v in direct_pins(in_file).items():
            if locked.get(name) != {v}:
                errors.append(f"{txt.relative_to(ROOT)}: {name}=={v} i .in, men {sorted(locked.get(name, [])) or 'mangler'} i låsen")
    for f in errors:
        print(f)
    if errors:
        print("Kør: python3 scripts/lock_environment.py")
    return 1 if errors else 0


def main() -> int:
    if "--check" in sys.argv:
        return check()
    uv = shutil.which("uv")
    if not uv:
        print("uv mangler: https://docs.astral.sh/uv/getting-started/installation/", file=sys.stderr)
        return 2
    for rel in LOCKS:
        in_file = ROOT / rel
        cmd = [uv, "pip", "compile", "-q", "--universal", "--python-version", PYTHON,
               "--custom-compile-command", "python3 scripts/lock_environment.py", in_file.name, "-o", in_file.with_suffix(".txt").name]
        if "--upgrade" in sys.argv:
            cmd.append("--upgrade")
        r = subprocess.run(cmd, cwd=in_file.parent)
        if r.returncode:
            return r.returncode
        print(f"Låst: {in_file.with_suffix('.txt').relative_to(ROOT)}")
    return check()


if __name__ == "__main__":
    sys.exit(main())
