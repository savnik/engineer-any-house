#!/usr/bin/env python3
"""PreToolUse (Bash): fag med et regneværktøj må kun bruge Bash til at køre det.

Fagregistret angiver værktøjet pr. fag (`"regnevaerktoej": "statik.py"` eller en liste). For fagets agent og
kontrolagent tillades kun:  python3 <…/skills/<fag>-viden/scripts/<værktøj>> <kommando> [argumenter]
Skriver et værktøj filer, begrænser `"kontrol_skrivefri"` kontrolagenten til de kommandoer, der ikke gør
(fx `{"fem.py": {"regn": "--ingen-filer", "test": ""}}`: regn kun med --ingen-filer).
Alt andet (flere kommandoer, rør, omdirigering, kommandosubstitution, andre programmer) afvises.
Kontrolagenten forbliver dermed uden skriveadgang, og alle tal kommer fra værktøjet.
Andre agenter påvirkes ikke. Fail-safe: en uventet fejl blokerer ikke.
"""
import json
import pathlib
import re
import shlex
import sys

REGISTER = pathlib.Path(__file__).resolve().parent / "fagregister.json"


def afvis(grund: str) -> None:
    print(json.dumps({"hookSpecificOutput": {"hookEventName": "PreToolUse", "permissionDecision": "deny",
                                             "permissionDecisionReason": grund}}, ensure_ascii=False))


def vaerktoej_for(agent: str, reg: dict) -> tuple[str, list, dict] | None:
    """(fag, værktøjer, skrivefri-regler) hvis agenten er fagagent eller kontrolagent i et fag med regneværktøj."""
    for fag, v in reg.get("fag", {}).items():
        if v.get("regnevaerktoej") and agent in (v.get("agent"), v.get("kontrol")):
            vt = v["regnevaerktoej"]
            regler = v.get("kontrol_skrivefri", {}) if agent == v.get("kontrol") else {}
            return fag, [vt] if isinstance(vt, str) else list(vt), regler
    return None


def tjek(cmd: str, fag: str, vaerktoejer: list, skrivefri: dict | None = None) -> str | None:
    """None = tilladt; ellers grunden til afvisning."""
    if re.search(r"[;&|<>`\n]|\$\(", cmd):
        return "kun én kommando uden ;, &&, |, omdirigering eller kommandosubstitution"
    try:
        dele = shlex.split(cmd.strip())
    except ValueError:
        return "kommandoen kan ikke fortolkes"
    navne = " eller ".join(vaerktoejer)
    if len(dele) < 3 or dele[0] not in ("python3", "python"):
        return f"kun python3 <…/{navne}> <kommando>"
    sti = dele[1].replace("\\", "/")
    vt = next((v for v in vaerktoejer if sti.endswith(f"/skills/{fag}-viden/scripts/{v}")), None)
    if not vt:
        return f"kun fagets egne regneværktøjer (…/skills/{fag}-viden/scripts/{navne})"
    regler = (skrivefri or {}).get(vt)
    if regler is not None:
        if dele[2] not in regler:
            return f"kontrollen må kun køre {vt} {', '.join(regler)} (de andre kommandoer skriver filer)"
        if regler[dele[2]] and regler[dele[2]] not in dele[3:]:
            return f"kontrollen skal køre {vt} {dele[2]} med {regler[dele[2]]} (ingen filer)"
    return None


def main() -> int:
    try:
        inp = json.loads(sys.stdin.read() or "{}")
        agent = str(inp.get("agent_type") or "").rsplit(":", 1)[-1]
        if not agent:
            return 0
        reg = json.loads(REGISTER.read_text(encoding="utf-8"))
        hit = vaerktoej_for(agent, reg)
        if not hit:
            return 0
        grund = tjek(str((inp.get("tool_input") or {}).get("command") or ""), *hit)
        if grund:
            afvis(f"{agent} må kun bruge Bash til regneværktøjet: {grund}. Al regning – også summer og "
                  f"enhedsomregning – sker med værktøjet (fx kommandoen 'regn').")
    except Exception:
        return 0
    return 0


if __name__ == "__main__":
    sys.exit(main())
