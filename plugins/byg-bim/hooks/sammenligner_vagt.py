#!/usr/bin/env python3
"""PreToolUse (Bash): bim-sammenligner og bim-opslag må kun køre læsende bim.py-kommandoer.

Tilladt: [BIM=<sti>; ] python3 <…/bim.py | "$BIM"> <kommando> …, hvor kommandoen står i agentens liste i TILLADT
(sammenligneren: også 'afkod tjek' og 'tjek --ud <…/bim/sammenligning/…>').
Alt andet (flere kommandoer, omdirigering, rm/mv/cp, redigering) afvises. Andre agenter påvirkes ikke.
Fail-safe: en uventet fejl blokerer ikke.
"""
import json
import re
import shlex
import sys

TILLADT = {
    "bim-sammenligner": {"sammenlign", "gitter", "linjer", "tegn", "vis", "find", "info", "skala", "maal", "afkod", "tjek"},
    "bim-opslag": {"info", "find", "vis", "maal"},
}
SVAR = {
    "bim-sammenligner": "Du retter aldrig selv – beskriv afvigelsen i dit svar.",
    "bim-opslag": "Du slår kun op – ændringer i modellen laver bim-modelloer.",
}


def afvis(grund: str) -> None:
    print(json.dumps({"hookSpecificOutput": {"hookEventName": "PreToolUse", "permissionDecision": "deny",
                                             "permissionDecisionReason": grund}}, ensure_ascii=False))


def tjek(cmd: str, agent: str = "bim-sammenligner") -> str | None:
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
    if dele[2] not in TILLADT[agent]:
        return f"kommandoen '{dele[2]}' er ikke tilladt – tilladt: {', '.join(sorted(TILLADT[agent]))}"
    if dele[2] == "afkod" and (len(dele) < 4 or dele[3] != "tjek"):
        return "kun 'afkod tjek'"
    if dele[2] == "tjek":
        ud = dele[dele.index("--ud") + 1] if "--ud" in dele[:-1] else ""
        if "/bim/sammenligning/" not in ud.replace("\\", "/") + "/":
            return "'tjek' kun med --ud under <sagsmappe>/bim/sammenligning/"
        if "--tegn" in dele:
            return "'tjek' uden --tegn (brug 'tegn' til tegninger)"
    return None


def main() -> int:
    try:
        inp = json.loads(sys.stdin.read() or "{}")
        agent = str(inp.get("agent_type") or "").rsplit(":", 1)[-1]
        if agent not in TILLADT:
            return 0
        grund = tjek(str((inp.get("tool_input") or {}).get("command") or ""), agent)
        if grund:
            afvis(f"{agent} er skrivebeskyttet: {grund}. {SVAR[agent]}")
    except Exception:
        return 0
    return 0


if __name__ == "__main__":
    sys.exit(main())
