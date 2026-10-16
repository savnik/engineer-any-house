#!/usr/bin/env python3
"""Tester regne_vagt.py: statiker og statik-kontrol må kun køre statik.py og fem.py via Bash.

Kør:  python3 tests/test_regne_vagt.py
"""
import json
import pathlib
import subprocess
import sys

HOOK = pathlib.Path(__file__).resolve().parent.parent / "plugins" / "byg-kontrol" / "hooks" / "regne_vagt.py"
VAERKTOEJ = "/x/plugins/byg-statik/skills/statik-viden/scripts/statik.py"
FEM = "/x/plugins/byg-statik/skills/statik-viden/scripts/fem.py"


def kald(agent, cmd):
    inp = {"agent_type": agent, "tool_name": "Bash", "tool_input": {"command": cmd}}
    ud = subprocess.run([sys.executable, str(HOOK)], input=json.dumps(inp), capture_output=True, text=True).stdout
    return "deny" if '"deny"' in ud else "allow"


SAGER = [
    ("byg-kontrol:statik-kontrol", f"python3 {VAERKTOEJ} regn '2*3'", "allow"),
    ("byg:statiker", f"python3 '{VAERKTOEJ}' bjaelke --spaend 3.6 --materiale S235 --profil HEB160 --g 8", "allow"),
    ("statik-kontrol", "python3 -c 'print(2*3)'", "deny"),
    ("statik-kontrol", f"python3 {VAERKTOEJ} regn 1 ; rm -rf /tmp/x", "deny"),
    ("statik-kontrol", f"python3 {VAERKTOEJ} regn 1 > /tmp/ud.txt", "deny"),
    ("statik-kontrol", "python3 /tmp/statik.py regn 1", "deny"),
    ("statiker", "bc -l", "deny"),
    ("statiker", f"python3 {VAERKTOEJ} regn \"$(cat /etc/passwd)\"", "deny"),
    ("statiker", f"python3 {FEM} regn /sag/fem/fem.yaml", "allow"),
    ("statiker", f"python3 {FEM} vis /sag/fem/fem.yaml", "allow"),
    ("statik-kontrol", f"python3 {FEM} regn /sag/fem/fem.yaml --ingen-filer --saet elementer.B1.profil=HEB180", "allow"),
    ("statik-kontrol", f"python3 {FEM} test", "allow"),
    ("statik-kontrol", f"python3 {FEM} regn /sag/fem/fem.yaml", "deny"),
    ("statik-kontrol", f"python3 {FEM} vis /sag/fem/fem.yaml", "deny"),
    ("statik-kontrol", f"python3 {FEM} tegn /sag/fem/fem.yaml M", "deny"),
    ("statiker", "python3 /tmp/fem.py regn x.yaml", "deny"),
    ("byg-murer:murermester", "ls -la", "allow"),
    ("", "ls", "allow"),
]


def main():
    fejl = 0
    for agent, cmd, forventet in SAGER:
        r = kald(agent, cmd)
        ok = r == forventet
        fejl += not ok
        print(f"{'OK  ' if ok else 'FEJL'} {agent or '(hovedtråd)'}: {cmd[:70]} → {r}")
    print("\nALLE TESTS BESTÅET" if not fejl else f"\n{fejl} FEJL")
    return 1 if fejl else 0


if __name__ == "__main__":
    sys.exit(main())
