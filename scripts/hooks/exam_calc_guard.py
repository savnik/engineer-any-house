#!/usr/bin/env python3
"""PreToolUse hook for the exam's calculation-tool arm (`exam.py run --calc-tool`).

The exam runs headless in dontAsk mode, so Bash and Write are denied unless a hook allows them. This hook allows:
- Bash: exactly one call of the trade's own calculation tool (same rule as byg-review's calc_guard.check).
- Write: a .json file inside the task's working directory (the panel file for e.g. `el.py panel`).
Everything else is denied. Unlike calc_guard, this hook fails closed: in the exam it is the only lock.

Usage (written into the plugin copy's hooks/hooks.json by exam.py):
  python3 exam_calc_guard.py <trade> <tool> [<tool> ...]
"""
import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "plugins" / "byg-review" / "hooks"))

from calc_guard import check  # noqa: E402


def decision(allow: bool, reason: str) -> str:
    return json.dumps({"hookSpecificOutput": {"hookEventName": "PreToolUse",
                                              "permissionDecision": "allow" if allow else "deny",
                                              "permissionDecisionReason": reason}}, ensure_ascii=False)


def judge(inp: dict, trade: str, tools: list[str]) -> tuple[bool, str]:
    tool = inp.get("tool_name")
    args = inp.get("tool_input") or {}
    if tool == "Bash":
        reason = check(str(args.get("command") or ""), trade, tools)
        if reason:
            return False, f"Bash kun til regneværktøjet: {reason}"
        return True, "fagets regneværktøj"
    if tool == "Write":
        cwd = pathlib.Path(str(inp.get("cwd") or "")).resolve()
        target = pathlib.Path(str(args.get("file_path") or ""))
        target = (target if target.is_absolute() else cwd / target).resolve()
        if str(inp.get("cwd") or "") and target.suffix == ".json" and target.is_relative_to(cwd):
            return True, "inputfil til regneværktøjet i opgavemappen"
        return False, "Write kun til en .json-inputfil i opgavemappen"
    return False, f"{tool} er ikke tilladt i regneværktøjsarmen"


def main() -> int:
    if len(sys.argv) < 3:
        print(decision(False, "exam_calc_guard mangler fag og værktøj"))
        return 0
    try:
        allow, reason = judge(json.loads(sys.stdin.read() or "{}"), sys.argv[1], sys.argv[2:])
    except Exception as exc:  # fail closed
        allow, reason = False, f"vagten fejlede: {exc}"
    print(decision(allow, reason))
    return 0


if __name__ == "__main__":
    sys.exit(main())
