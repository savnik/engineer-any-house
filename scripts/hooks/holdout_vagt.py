#!/usr/bin/env python3
"""PreToolUse for CI-agenten (ci-forbedring): agenten må aldrig se holdout-opgaver eller facit direkte.

Opgavefilerne (eksamen/<fag>/opgaver*.json) og resultatfilerne (eksamen/<fag>/results/) rummer begge sæt. Agenten
læser dem kun gennem scripts, der filtrerer holdout fra:
- `exam.py vis <fag> --saet udvikling [--facit]`, `exam.py koer|rapport|rebedoem|tjek` (rapporten skjuler holdout-ID'er)
- `forsoeg.py …` (loggen rummer kun holdout som antal og hash)
Afvist: Read/Edit/Write af filerne, Grep med indhold i eksamen/, og Bash-kommandoer, der nævner filerne eller søger
rekursivt uden en sti uden for eksamen/. Rettelser i opgavefilerne uddelegeres (se agentens instruks).
Fail-safe: en uventet fejl blokerer ikke.
"""
import json
import pathlib
import re
import shlex
import sys

PROTECTED_RE = re.compile(r"eksamen/[^/\s'\"]+/(opgaver[^/\s'\"]*\.json|results\b)")
SAFE_SEARCH_ROOTS = ("plugins", "faelles", "scripts", "skabelon", "tests", "versionsnoter")
SCRIPT_RE = re.compile(r"^python3?\s+(\S*/)?scripts/(exam|forsoeg)\.py\s+(\S+)(.*)$", re.DOTALL)


def deny(reason: str) -> None:
    print(json.dumps({"hookSpecificOutput": {"hookEventName": "PreToolUse", "permissionDecision": "deny",
                                             "permissionDecisionReason": reason}}, ensure_ascii=False))


def check_bash(cmd: str) -> str | None:
    c = cmd.strip()
    m = SCRIPT_RE.match(c)
    if m:
        script, sub, rest = m.group(2), m.group(3), m.group(4)
        if script == "exam" and sub == "vis" and "--saet udvikling" not in rest:
            return "brug `exam.py vis <fag> --saet udvikling` – holdout må du ikke se"
        if re.search(r"[;&`>]|\$\(", c) or re.search(r"\|(?!\s*(head|tail|grep)\b)", c):
            return "kør scriptet alene (højst med | head, | tail eller | grep), uden kædede kommandoer"
        return None
    if PROTECTED_RE.search(c):
        return "opgave- og resultatfilerne læses kun gennem exam.py og forsoeg.py"
    try:
        words = shlex.split(c)
    except ValueError:
        words = c.split()
    recursive = any(w in ("rg", "ag") for w in words) or (
        "grep" in words and any(re.fullmatch(r"-\w*[rR]\w*", w) or w.startswith("--recursive") for w in words))
    if recursive:
        if "eksamen" in c and not re.search(r"--exclude-dir=['\"]?eksamen|!eksamen", c):
            return "søg ikke i eksamen/ – brug exam.py og forsoeg.py"
        paths = [w for w in words if not w.startswith("-") and "/" in w or w in SAFE_SEARCH_ROOTS]
        if not re.search(r"--exclude-dir=['\"]?eksamen|!eksamen", c) and not any(
                p.strip("./").split("/")[0] in SAFE_SEARCH_ROOTS for p in paths):
            return "rekursiv søgning skal have en sti uden for eksamen/ (fx plugins/) eller --exclude-dir=eksamen"
    return None


def check(tool: str, inp: dict, cwd: str = "") -> str | None:
    """None = allowed; otherwise the reason for denying."""
    if tool in ("Read", "Edit", "Write", "NotebookEdit", "MultiEdit"):
        if PROTECTED_RE.search(str(inp.get("file_path") or inp.get("notebook_path") or "")):
            return ("opgave- og resultatfilerne rummer holdout – brug `exam.py vis <fag> --saet udvikling --facit`, "
                    "`exam.py rapport` og `forsoeg.py`; rettelser i opgavefilerne uddelegeres")
    if tool == "Grep":
        path = str(inp.get("path") or "")
        if PROTECTED_RE.search(path):
            return "søg ikke i opgave- og resultatfilerne"
        root = pathlib.Path(cwd or ".")
        target = (root / path).resolve() if path else root.resolve()
        exam_dir = (root / "eksamen").resolve()
        covers = target == exam_dir or exam_dir.is_relative_to(target) or target.is_relative_to(exam_dir)
        glob = str(inp.get("glob") or "") + str(inp.get("type") or "")
        if covers and inp.get("output_mode") == "content" and (not glob or "json" in glob):
            return "Grep med indhold må ikke ramme eksamen/ – angiv en sti (fx plugins/) eller en glob uden json"
    if tool == "Bash":
        return check_bash(str(inp.get("command") or ""))
    return None


def main() -> int:
    try:
        inp = json.loads(sys.stdin.read() or "{}")
        reason = check(str(inp.get("tool_name") or ""), inp.get("tool_input") or {}, str(inp.get("cwd") or ""))
        if reason:
            deny(f"Holdout-vagt: {reason}.")
    except Exception:
        return 0
    return 0


if __name__ == "__main__":
    sys.exit(main())
