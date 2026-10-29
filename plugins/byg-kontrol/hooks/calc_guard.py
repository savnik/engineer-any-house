#!/usr/bin/env python3
"""PreToolUse (Bash): a trade with a calculation tool may only use Bash to run that tool.

The trade register names the tool per trade (`"regnevaerktoej": "statik.py"` or a list). For the trade's agent and
review agent only this is allowed:  python3 <…/skills/<trade>-viden/scripts/<tool>> <command> [arguments]
If a tool writes files, `"kontrol_skrivefri"` limits the review agent to the commands that do not
(e.g. `{"fem.py": {"regn": "--ingen-filer", "test": ""}}`: regn only with --ingen-filer).
Everything else (several commands, pipes, redirection, command substitution, other programs) is denied.
The review agent thus stays without write access, and every number comes from the tool.
Other agents are unaffected. Fail-safe: an unexpected error never blocks.
"""
import json
import pathlib
import re
import shlex
import sys

REGISTER = pathlib.Path(__file__).resolve().parent / "fagregister.json"


def deny(reason: str) -> None:
    print(json.dumps({"hookSpecificOutput": {"hookEventName": "PreToolUse", "permissionDecision": "deny",
                                             "permissionDecisionReason": reason}}, ensure_ascii=False))


def tools_for(agent: str, reg: dict) -> tuple[str, list, dict] | None:
    """(trade, tools, write-free rules) if the agent is the trade agent or review agent of a trade with a calculation tool."""
    for trade, v in reg.get("fag", {}).items():
        if v.get("regnevaerktoej") and agent in (v.get("agent"), v.get("kontrol")):
            tool = v["regnevaerktoej"]
            rules = v.get("kontrol_skrivefri", {}) if agent == v.get("kontrol") else {}
            return trade, [tool] if isinstance(tool, str) else list(tool), rules
    return None


def check(cmd: str, trade: str, tools: list, write_free: dict | None = None) -> str | None:
    """None = allowed; otherwise the reason for denial."""
    if re.search(r"[;&|<>`\n]|\$\(", cmd):
        return "kun én kommando uden ;, &&, |, omdirigering eller kommandosubstitution"
    try:
        parts = shlex.split(cmd.strip())
    except ValueError:
        return "kommandoen kan ikke fortolkes"
    names = " eller ".join(tools)
    if len(parts) < 3 or parts[0] not in ("python3", "python"):
        return f"kun python3 <…/{names}> <kommando>"
    path = parts[1].replace("\\", "/")
    tool = next((v for v in tools if path.endswith(f"/skills/{trade}-viden/scripts/{v}")), None)
    if not tool:
        return f"kun fagets egne regneværktøjer (…/skills/{trade}-viden/scripts/{names})"
    rules = (write_free or {}).get(tool)
    if rules is not None:
        if parts[2] not in rules:
            return f"kontrollen må kun køre {tool} {', '.join(rules)} (de andre kommandoer skriver filer)"
        if rules[parts[2]] and rules[parts[2]] not in parts[3:]:
            return f"kontrollen skal køre {tool} {parts[2]} med {rules[parts[2]]} (ingen filer)"
    return None


def main() -> int:
    try:
        inp = json.loads(sys.stdin.read() or "{}")
        agent = str(inp.get("agent_type") or "").rsplit(":", 1)[-1]
        if not agent:
            return 0
        reg = json.loads(REGISTER.read_text(encoding="utf-8"))
        hit = tools_for(agent, reg)
        if not hit:
            return 0
        reason = check(str((inp.get("tool_input") or {}).get("command") or ""), *hit)
        if reason:
            deny(f"{agent} må kun bruge Bash til regneværktøjet: {reason}. Al regning – også summer og "
                 f"enhedsomregning – sker med værktøjet (fx kommandoen 'regn').")
    except Exception:
        return 0
    return 0


if __name__ == "__main__":
    sys.exit(main())
