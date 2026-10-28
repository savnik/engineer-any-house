#!/usr/bin/env python3
"""Opretter et nyt fag i Engineer Any House: fag-plugin, modsvarende kontrolagent og kontrolfil – og registrerer faget.

Brug:     python3 scripts/nyt_fag.py <fag-id> "<Fagnavn>" <agentnavn> [--farve green]
Eksempel: python3 scripts/nyt_fag.py kloak "Kloakmester" kloakmester --farve orange

Registrerer i: .claude-plugin/marketplace.json, byg-team (dependencies), byg-kontrol/hooks/fagregister.json,
projektlederens fagtabel og kvalitetskontrollens agentpar. Kører derefter sync_protokol.py.
"""
import argparse
import datetime
import json
import pathlib
import re
import subprocess
import sys

ROD = pathlib.Path(__file__).resolve().parent.parent
SKAB = ROD / "skabelon"
FARVER = {"red", "blue", "green", "yellow", "purple", "orange", "pink", "cyan"}
NAVN_RE = re.compile(r"^[a-z][a-z0-9-]{1,30}$")


def erstat(tekst: str, v: dict) -> str:
    for k, x in v.items():
        tekst = tekst.replace("{{%s}}" % k, x)
    return tekst


def kopier(kilde: pathlib.Path, maal: pathlib.Path, v: dict) -> None:
    for f in sorted(kilde.rglob("*")):
        if f.is_dir():
            continue
        rel = str(f.relative_to(kilde)).replace("__SLUG__", v["SLUG"]).replace("__AGENT__", v["AGENT"])
        ud = maal / rel
        ud.parent.mkdir(parents=True, exist_ok=True)
        ud.write_text(erstat(f.read_text(encoding="utf-8"), v), encoding="utf-8")


def gem_json(fil: pathlib.Path, data) -> None:
    fil.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def indsaet_raekke(fil: pathlib.Path, header: str, raekke: str, foer: str | None = None) -> bool:
    linjer = fil.read_text(encoding="utf-8").split("\n")
    i = next((n for n, l in enumerate(linjer) if l.startswith(header)), None)
    if i is None:
        return False
    j = i + 2
    while j < len(linjer) and linjer[j].startswith("|"):
        if foer and linjer[j].startswith(foer):
            break
        j += 1
    linjer.insert(j, raekke)
    fil.write_text("\n".join(linjer), encoding="utf-8")
    return True


def main() -> int:
    ap = argparse.ArgumentParser(description="Opret et nyt fag med kontrolagent.")
    ap.add_argument("fag_id")
    ap.add_argument("fagnavn")
    ap.add_argument("agent")
    ap.add_argument("--farve", default="green")
    a = ap.parse_args()

    if not NAVN_RE.match(a.fag_id) or not NAVN_RE.match(a.agent):
        sys.exit("fag-id og agentnavn: små bogstaver, tal og bindestreg (2–31 tegn), fx 'kloak' og 'kloakmester'.")
    if a.farve not in FARVER:
        sys.exit(f"Farve skal være en af: {', '.join(sorted(FARVER))}")
    plugin = f"byg-{a.fag_id}"
    reg_fil = ROD / "plugins" / "byg-kontrol" / "hooks" / "fagregister.json"
    reg = json.loads(reg_fil.read_text(encoding="utf-8"))
    eksisterende = {p.stem for p in ROD.glob("plugins/*/agents/*.md")}
    if a.fag_id in reg["fag"] or a.fag_id == "projekt":
        sys.exit(f"Faget '{a.fag_id}' findes allerede.")
    if a.agent in eksisterende or f"{a.fag_id}-kontrol" in eksisterende:
        sys.exit("Agentnavnet eller kontrolagentens navn findes allerede.")
    if (ROD / "plugins" / plugin).exists():
        sys.exit(f"plugins/{plugin} findes allerede.")

    v = {"SLUG": a.fag_id, "AGENT": a.agent, "FAGNAVN": a.fagnavn, "PLUGIN": plugin,
         "FARVE": a.farve, "DATO": datetime.date.today().isoformat()}
    kopier(SKAB / "fag-plugin", ROD / "plugins" / plugin, v)
    kopier(SKAB / "kontrol" / "agents", ROD / "plugins" / "byg-kontrol" / "agents", v)
    fagfil = ROD / "plugins" / "byg-kontrol" / "skills" / "kontrol-viden" / "references" / "fag" / f"{a.fag_id}.md"
    fagfil.write_text(erstat((SKAB / "kontrol" / "fag.md").read_text(encoding="utf-8"), v), encoding="utf-8")

    reg["fag"][a.fag_id] = {"agent": a.agent, "kontrol": f"{a.fag_id}-kontrol"}
    gem_json(reg_fil, reg)
    mp_fil = ROD / ".claude-plugin" / "marketplace.json"
    mp = json.loads(mp_fil.read_text(encoding="utf-8"))
    mp["plugins"].append({"name": plugin, "source": f"./plugins/{plugin}",
                          "description": f"{a.fagnavn}: TODO – kort beskrivelse."})
    gem_json(mp_fil, mp)
    team_fil = ROD / "plugins" / "byg-team" / ".claude-plugin" / "plugin.json"
    team = json.loads(team_fil.read_text(encoding="utf-8"))
    if plugin not in team["dependencies"]:
        team["dependencies"].append(plugin)
    gem_json(team_fil, team)

    ok1 = indsaet_raekke(ROD / "plugins" / "byg" / "skills" / "projektleder" / "SKILL.md", "| Fag-id | Agent |",
                         f"| {a.fag_id} | `{a.agent}` | TODO: typiske opgaver |")
    ok2 = indsaet_raekke(ROD / "plugins" / "byg-kontrol" / "skills" / "kvalitetskontrol" / "SKILL.md",
                         "| Fag | Fagagent | Kontrolagent |", f"| {a.fag_id} | `{a.agent}` | `{a.fag_id}-kontrol` |",
                         foer="| projekt |")
    kv = ROD / "plugins" / "byg-kontrol" / "skills" / "kontrol-viden" / "SKILL.md"
    t = kv.read_text(encoding="utf-8")
    kv.write_text(t.replace(", `projekt`.", f", `{a.fag_id}`, `projekt`.", 1), encoding="utf-8")
    subprocess.run([sys.executable, str(ROD / "scripts" / "sync_protokol.py")], check=True)

    print(f"\nOprettet plugins/{plugin}, kontrolagent {a.fag_id}-kontrol og kontrolfil fag/{a.fag_id}.md.")
    if not (ok1 and ok2):
        print("Bemærk: en fagtabel blev ikke fundet – tilføj faget manuelt i projektleder- og kvalitetskontrol-skillen.")
    print("Næste skridt: udfyld alle TODO (fagagent, videnbase med V/T-status, kontrolpunkter, fejlkatalog, eval),"
          " opdatér README og koordinering.md, og kør: python3 scripts/valider.py --claude")
    return 0


if __name__ == "__main__":
    sys.exit(main())
