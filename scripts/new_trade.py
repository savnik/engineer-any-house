#!/usr/bin/env python3
"""Creates a new trade in Engineer Any House: trade plugin, matching review agent and review file – and registers the trade.

Usage:   python3 scripts/new_trade.py <fag-id> "<Fagnavn>" <agentnavn> [--color green]
Example: python3 scripts/new_trade.py kloak "Kloakmester" kloakmester --color orange

Registers in: .claude-plugin/marketplace.json, byg-team (dependencies), byg-review/hooks/trade-registry.json,
the project manager's trade table and the quality review's agent pairs. Then runs sync_protocol.py.
"""
import argparse
import datetime
import json
import pathlib
import re
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
TEMPLATES = ROOT / "template"
COLORS = {"red", "blue", "green", "yellow", "purple", "orange", "pink", "cyan"}
NAME_RE = re.compile(r"^[a-z][a-z0-9-]{1,30}$")


def replace_vars(text: str, v: dict) -> str:
    for k, x in v.items():
        text = text.replace("{{%s}}" % k, x)
    return text


def copy_template(src: pathlib.Path, dst: pathlib.Path, v: dict) -> None:
    for f in sorted(src.rglob("*")):
        if f.is_dir():
            continue
        rel = str(f.relative_to(src)).replace("__SLUG__", v["SLUG"]).replace("__AGENT__", v["AGENT"])
        out = dst / rel
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(replace_vars(f.read_text(encoding="utf-8"), v), encoding="utf-8")


def save_json(path: pathlib.Path, data) -> None:
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def insert_row(path: pathlib.Path, header: str, row: str, before: str | None = None) -> bool:
    lines = path.read_text(encoding="utf-8").split("\n")
    i = next((n for n, line in enumerate(lines) if line.startswith(header)), None)
    if i is None:
        return False
    j = i + 2
    while j < len(lines) and lines[j].startswith("|"):
        if before and lines[j].startswith(before):
            break
        j += 1
    lines.insert(j, row)
    path.write_text("\n".join(lines), encoding="utf-8")
    return True


def main() -> int:
    ap = argparse.ArgumentParser(description="Opret et nyt fag med kontrolagent.")
    ap.add_argument("fag_id")
    ap.add_argument("fagnavn")
    ap.add_argument("agent")
    ap.add_argument("--color", default="green")
    a = ap.parse_args()

    if not NAME_RE.match(a.fag_id) or not NAME_RE.match(a.agent):
        sys.exit("fag-id og agentnavn: små bogstaver, tal og bindestreg (2–31 tegn), fx 'kloak' og 'kloakmester'.")
    if a.color not in COLORS:
        sys.exit(f"Farve skal være en af: {', '.join(sorted(COLORS))}")
    plugin = f"byg-{a.fag_id}"
    reg_path = ROOT / "plugins" / "byg-review" / "hooks" / "trade-registry.json"
    reg = json.loads(reg_path.read_text(encoding="utf-8"))
    existing = {p.stem for p in ROOT.glob("plugins/*/agents/*.md")}
    if a.fag_id in reg["fag"] or a.fag_id == "project":
        sys.exit(f"Faget '{a.fag_id}' findes allerede.")
    if a.agent in existing or f"{a.fag_id}-review" in existing:
        sys.exit("Agentnavnet eller kontrolagentens navn findes allerede.")
    if (ROOT / "plugins" / plugin).exists():
        sys.exit(f"plugins/{plugin} findes allerede.")

    v = {"SLUG": a.fag_id, "AGENT": a.agent, "TRADE_NAME": a.fagnavn, "PLUGIN": plugin,
         "COLOR": a.color, "DATE": datetime.date.today().isoformat()}
    copy_template(TEMPLATES / "trade-plugin", ROOT / "plugins" / plugin, v)
    copy_template(TEMPLATES / "review" / "agents", ROOT / "plugins" / "byg-review" / "agents", v)
    trade_file = ROOT / "plugins" / "byg-review" / "skills" / "review-knowledge" / "references" / "trades" / f"{a.fag_id}.md"
    trade_file.write_text(replace_vars((TEMPLATES / "review" / "trade.md").read_text(encoding="utf-8"), v), encoding="utf-8")

    reg["fag"][a.fag_id] = {"agent": a.agent, "kontrol": f"{a.fag_id}-review"}
    save_json(reg_path, reg)
    mp_path = ROOT / ".claude-plugin" / "marketplace.json"
    mp = json.loads(mp_path.read_text(encoding="utf-8"))
    mp["plugins"].append({"name": plugin, "source": f"./plugins/{plugin}",
                          "description": f"{a.fagnavn}: TODO – kort beskrivelse."})
    save_json(mp_path, mp)
    team_path = ROOT / "plugins" / "byg-team" / ".claude-plugin" / "plugin.json"
    team = json.loads(team_path.read_text(encoding="utf-8"))
    if plugin not in team["dependencies"]:
        team["dependencies"].append(plugin)
    save_json(team_path, team)

    ok1 = insert_row(ROOT / "plugins" / "byg" / "skills" / "project-manager" / "SKILL.md", "| Fag-id | Agent |",
                         f"| {a.fag_id} | `{a.agent}` | TODO: typiske opgaver |")
    ok2 = insert_row(ROOT / "plugins" / "byg-review" / "skills" / "quality-review" / "SKILL.md",
                         "| Fag | Fagagent | Kontrolagent |", f"| {a.fag_id} | `{a.agent}` | `{a.fag_id}-review` |",
                         before="| project |")
    kv = ROOT / "plugins" / "byg-review" / "skills" / "review-knowledge" / "SKILL.md"
    t = kv.read_text(encoding="utf-8")
    kv.write_text(t.replace(", `project`.", f", `{a.fag_id}`, `project`.", 1), encoding="utf-8")
    subprocess.run([sys.executable, str(ROOT / "scripts" / "sync_protocol.py")], check=True)

    print(f"\nOprettet plugins/{plugin}, kontrolagent {a.fag_id}-review og kontrolfil trades/{a.fag_id}.md.")
    if not (ok1 and ok2):
        print("Bemærk: en fagtabel blev ikke fundet – tilføj faget manuelt i skillene project-manager og quality-review.")
    print("Næste skridt: udfyld alle TODO (fagagent, videnbase med V/T-status, kontrolpunkter, fejlkatalog, eval),"
          " opdatér README.md, README.da.md og coordination.md, og kør: python3 scripts/validate.py --claude")
    return 0


if __name__ == "__main__":
    sys.exit(main())
