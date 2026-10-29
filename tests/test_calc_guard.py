#!/usr/bin/env python3
"""Tests calc_guard.py: structural-engineer and structural-review may only run statik.py and fem.py via Bash.

Run:  python3 tests/test_calc_guard.py
"""
import json
import pathlib
import subprocess
import sys

HOOK = pathlib.Path(__file__).resolve().parent.parent / "plugins" / "byg-review" / "hooks" / "calc_guard.py"
TOOL = "/x/plugins/byg-structural/skills/structural-knowledge/scripts/statik.py"
FEM = "/x/plugins/byg-structural/skills/structural-knowledge/scripts/fem.py"


def call(agent, cmd):
    inp = {"agent_type": agent, "tool_name": "Bash", "tool_input": {"command": cmd}}
    out = subprocess.run([sys.executable, str(HOOK)], input=json.dumps(inp), capture_output=True, text=True).stdout
    return "deny" if '"deny"' in out else "allow"


CASES = [
    ("byg-review:structural-review", f"python3 {TOOL} calc '2*3'", "allow"),
    ("byg:structural-engineer", f"python3 '{TOOL}' beam --span 3.6 --material S235 --profile HEB160 --g 8", "allow"),
    ("structural-review", "python3 -c 'print(2*3)'", "deny"),
    ("structural-review", f"python3 {TOOL} calc 1 ; rm -rf /tmp/x", "deny"),
    ("structural-review", f"python3 {TOOL} calc 1 > /tmp/ud.txt", "deny"),
    ("structural-review", "python3 /tmp/statik.py calc 1", "deny"),
    ("structural-engineer", "bc -l", "deny"),
    ("structural-engineer", f"python3 {TOOL} calc \"$(cat /etc/passwd)\"", "deny"),
    ("structural-engineer", f"python3 {FEM} calc /sag/fem/fem.yaml", "allow"),
    ("structural-engineer", f"python3 {FEM} view /sag/fem/fem.yaml", "allow"),
    ("structural-review", f"python3 {FEM} calc /sag/fem/fem.yaml --no-files --set elementer.B1.profil=HEB180", "allow"),
    ("structural-review", f"python3 {FEM} test", "allow"),
    ("structural-review", f"python3 {FEM} result /sag/fem/fem.yaml --element B1", "allow"),
    ("structural-engineer", f"python3 {FEM} result /sag/fem/fem.yaml", "allow"),
    ("structural-review", f"python3 {FEM} calc /sag/fem/fem.yaml", "deny"),
    ("structural-review", f"python3 {FEM} calc /sag/fem/fem.yaml --ingen-filer", "deny"),
    ("structural-review", f"python3 {FEM} view /sag/fem/fem.yaml", "deny"),
    ("structural-review", f"python3 {FEM} draw /sag/fem/fem.yaml M", "deny"),
    ("structural-engineer", "python3 /tmp/fem.py calc x.yaml", "deny"),
    ("byg-masonry:mason", "ls -la", "allow"),
    ("", "ls", "allow"),
]


def main():
    errors = 0
    for agent, cmd, expected in CASES:
        r = call(agent, cmd)
        ok = r == expected
        errors += not ok
        print(f"{'OK  ' if ok else 'FEJL'} {agent or '(hovedtråd)'}: {cmd[:70]} → {r}")
    print("\nALLE TESTS BESTÅET" if not errors else f"\n{errors} FEJL")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
