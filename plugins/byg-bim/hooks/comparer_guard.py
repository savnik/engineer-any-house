#!/usr/bin/env python3
"""PreToolUse (Bash): bim-sammenligner and bim-opslag may only run read-only bim.py commands.

Allowed: [BIM=<path>; ] python3 <…/bim.py | "$BIM"> <command> …, where the command is in the agent's list in ALLOWED
(the comparer: also 'afkod tjek' and 'tjek --ud <…/bim/sammenligning/…>').
Everything else (several commands, redirection, rm/mv/cp, editing) is denied. Other agents are not affected.
Fail-safe: an unexpected error does not block.
"""
import json
import re
import shlex
import sys

ALLOWED = {
    "bim-sammenligner": {"sammenlign", "gitter", "linjer", "tegn", "vis", "find", "info", "skala", "maal", "afkod", "tjek"},
    "bim-opslag": {"info", "find", "vis", "maal"},
}
REPLY = {
    "bim-sammenligner": "Du retter aldrig selv – beskriv afvigelsen i dit svar.",
    "bim-opslag": "Du slår kun op – ændringer i modellen laver bim-modelloer.",
}


def deny(reason: str) -> None:
    print(json.dumps({"hookSpecificOutput": {"hookEventName": "PreToolUse", "permissionDecision": "deny",
                                             "permissionDecisionReason": reason}}, ensure_ascii=False))


def check(cmd: str, agent: str = "bim-sammenligner") -> str | None:
    """None = allowed; otherwise the reason for denial."""
    c = cmd.strip()
    m = re.match(r'^BIM=("[^"]+"|\'[^\']+\'|\S+)\s*(;|&&)\s*', c)
    if m:
        c = c[m.end():]
    if re.search(r"[;&|<>`]|\$\(", c):
        return "kun én bim.py-kommando uden ;, &&, |, omdirigering eller kommandosubstitution"
    try:
        parts = shlex.split(c)
    except ValueError:
        return "kommandoen kan ikke fortolkes"
    if len(parts) < 3 or parts[0] not in ("python3", "python") or not (parts[1].endswith("bim.py") or parts[1] == "$BIM"):
        return "kun python3 <…/bim.py> <kommando>"
    if parts[2] not in ALLOWED[agent]:
        return f"kommandoen '{parts[2]}' er ikke tilladt – tilladt: {', '.join(sorted(ALLOWED[agent]))}"
    if parts[2] == "afkod" and (len(parts) < 4 or parts[3] != "tjek"):
        return "kun 'afkod tjek'"
    if parts[2] == "tjek":
        out = parts[parts.index("--ud") + 1] if "--ud" in parts[:-1] else ""
        if "/bim/sammenligning/" not in out.replace("\\", "/") + "/":
            return "'tjek' kun med --ud under <sagsmappe>/bim/sammenligning/"
        if "--tegn" in parts:
            return "'tjek' uden --tegn (brug 'tegn' til tegninger)"
    return None


def main() -> int:
    try:
        inp = json.loads(sys.stdin.read() or "{}")
        agent = str(inp.get("agent_type") or "").rsplit(":", 1)[-1]
        if agent not in ALLOWED:
            return 0
        reason = check(str((inp.get("tool_input") or {}).get("command") or ""), agent)
        if reason:
            deny(f"{agent} er skrivebeskyttet: {reason}. {REPLY[agent]}")
    except Exception:
        return 0
    return 0


if __name__ == "__main__":
    sys.exit(main())
