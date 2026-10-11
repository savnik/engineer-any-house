#!/usr/bin/env python3
"""PreToolUse (Bash): bim-sammenligner må kun køre læsende bim.py-kommandoer.

Tilladt: [BIM=<sti>; ] python3 <…/bim.py | "$BIM"> sammenlign|gitter|linjer|tegn|vis|find|info|skala|afkod tjek …
Alt andet (flere kommandoer, omdirigering, rm/mv/cp, redigering) afvises. Andre agenter påvirkes ikke.
Fail-safe: en uventet fejl blokerer ikke.
"""
import json
import re
import shlex
import sys

TILLADT = {"sammenlign", "gitter", "linjer", "tegn", "vis", "find", "info", "skala", "afkod"}
AGENT = "bim-sammenligner"


def afvis(grund: str) -> None:
    print(json.dumps({"hookSpecificOutput": {"hookEventName": "PreToolUse", "permissionDecision": "deny",
                                             "permissionDecisionReason": grund}}, ensure_ascii=False))


def tjek(cmd: str) -> str | None:
    """None = tilladt; ellers grunden til afvisning."""
    c = cmd.strip()
    m = re.match(r'^BIM=("[^"]+"|\'[^\']+\'|\S+)\s*(;|&&)\s*', c)
    if m:
        c = c[m.end():]
    if re.search(r"[;&|<>`]|\$\(", c):
        return "kun én bim.py-kommando uden ;, &&, |, omdirigering eller kommandosubstitution"
    try:
        dele = shlex.split(c)
    except ValueError:
        return "kommandoen kan ikke fortolkes"
    if len(dele) < 3 or dele[0] not in ("python3", "python") or not (dele[1].endswith("bim.py") or dele[1] == "$BIM"):
        return "kun python3 <…/bim.py> <kommando>"
    if dele[2] not in TILLADT:
        return f"kommandoen '{dele[2]}' er ikke læsende – tilladt: {', '.join(sorted(TILLADT))}"
    if dele[2] == "afkod" and (len(dele) < 4 or dele[3] != "tjek"):
        return "kun 'afkod tjek'"
    return None


def main() -> int:
    try:
        inp = json.loads(sys.stdin.read() or "{}")
        at = str(inp.get("agent_type") or "")
        if at.rsplit(":", 1)[-1] != AGENT:
            return 0
        grund = tjek(str((inp.get("tool_input") or {}).get("command") or ""))
        if grund:
            afvis(f"bim-sammenligner er skrivebeskyttet: {grund}. Du retter aldrig selv – beskriv afvigelsen i dit svar.")
    except Exception:
        return 0
    return 0


if __name__ == "__main__":
    sys.exit(main())
