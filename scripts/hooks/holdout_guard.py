#!/usr/bin/env python3
"""PreToolUse for the CI agent (ci-improvement): the agent must never see holdout tasks or answer keys directly.

The task files (exam/<trade>/tasks*.json) and the result files (exam/<trade>/results/) hold both sets. The
agent reads them only through scripts that filter holdout out:
- `exam.py show <fag> --set development [--answer-key]`, `exam.py run|report|regrade|check` (the report hides holdout IDs)
- `experiment.py …` (the log holds holdout only as a count and a hash)
Denied: Read/Edit/Write of the files, Grep with content in exam/, and Bash commands that name the files or search
recursively without a path outside exam/. Edits to the task files are delegated (see the agent's instructions).
Fail-safe: an unexpected error does not block.
"""
import json
import pathlib
import re
import shlex
import sys

PROTECTED_RE = re.compile(r"exam/[^/\s'\"]+/(tasks[^/\s'\"]*\.json|results\b)")
SAFE_SEARCH_ROOTS = ("plugins", "shared", "scripts", "template", "tests", "release-notes")
SCRIPT_RE = re.compile(r"^python3?\s+(\S*/)?scripts/(exam|experiment)\.py\s+(\S+)(.*)$", re.DOTALL)


def deny(reason: str) -> None:
    print(json.dumps({"hookSpecificOutput": {"hookEventName": "PreToolUse", "permissionDecision": "deny",
                                             "permissionDecisionReason": reason}}, ensure_ascii=False))


def check_bash(cmd: str) -> str | None:
    c = cmd.strip()
    m = SCRIPT_RE.match(c)
    if m:
        script, sub, rest = m.group(2), m.group(3), m.group(4)
        if script == "exam" and sub == "show" and not re.search(r"--set[\s=]development\b", rest):
            return "brug `exam.py show <fag> --set development` – holdout må du ikke se"
        if re.search(r"[;&`>]|\$\(", c) or re.search(r"\|(?!\s*(head|tail|grep)\b)", c):
            return "kør scriptet alene (højst med | head, | tail eller | grep), uden kædede kommandoer"
        return None
    if PROTECTED_RE.search(c):
        return "opgave- og resultatfilerne læses kun gennem exam.py og experiment.py"
    try:
        words = shlex.split(c)
    except ValueError:
        words = c.split()
    recursive = any(w in ("rg", "ag") for w in words) or (
        "grep" in words and any(re.fullmatch(r"-\w*[rR]\w*", w) or w.startswith("--recursive") for w in words))
    if recursive:
        if "exam" in c and not re.search(r"--exclude-dir=['\"]?exam|!exam", c):
            return "søg ikke i exam/ – brug exam.py og experiment.py"
        paths = [w for w in words if not w.startswith("-") and "/" in w or w in SAFE_SEARCH_ROOTS]
        if not re.search(r"--exclude-dir=['\"]?exam|!exam", c) and not any(
                p.strip("./").split("/")[0] in SAFE_SEARCH_ROOTS for p in paths):
            return "rekursiv søgning skal have en sti uden for exam/ (fx plugins/) eller --exclude-dir=exam"
    return None


def check(tool: str, inp: dict, cwd: str = "") -> str | None:
    """None = allowed; otherwise the reason for denying."""
    if tool in ("Read", "Edit", "Write", "NotebookEdit", "MultiEdit"):
        if PROTECTED_RE.search(str(inp.get("file_path") or inp.get("notebook_path") or "")):
            return ("opgave- og resultatfilerne rummer holdout – brug `exam.py show <fag> --set development --answer-key`, "
                    "`exam.py report` og `experiment.py`; rettelser i opgavefilerne uddelegeres")
    if tool == "Grep":
        path = str(inp.get("path") or "")
        if PROTECTED_RE.search(path):
            return "søg ikke i opgave- og resultatfilerne"
        root = pathlib.Path(cwd or ".")
        target = (root / path).resolve() if path else root.resolve()
        exam_dir = (root / "exam").resolve()
        covers = target == exam_dir or exam_dir.is_relative_to(target) or target.is_relative_to(exam_dir)
        glob = str(inp.get("glob") or "") + str(inp.get("type") or "")
        if covers and inp.get("output_mode") == "content" and (not glob or "json" in glob):
            return "Grep med indhold må ikke ramme exam/ – angiv en sti (fx plugins/) eller en glob uden json"
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
