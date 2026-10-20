#!/usr/bin/env python3
"""Strukturtjek af byg-eksperter.

Brug: python3 scripts/valider.py [--claude]   (--claude kører også `claude plugin validate` på alle plugins og marketplacet)
Tjekker: JSON, marketplace og afhængigheder, frontmatter og unikke navne (også til den samlede pakke), værktøjer for
fag- og kontrolagenter, fagregister, ${CLAUDE_PLUGIN_ROOT}-stier, evals, protokoller i synk, versionsnoter, ingen bin/,
hook-tests, eksamenslaget, forsøgsloggen og dataseparation.
"""
import json
import pathlib
import re
import shutil
import subprocess
import sys

ROD = pathlib.Path(__file__).resolve().parent.parent
PLUGINS = ROD / "plugins"
FEJL: list[str] = []
ADV: list[str] = []
GRADERTYPER = {"regex", "tool_order", "tool_used", "file_exists", "llm", "baseline"}


def frontmatter(fil: pathlib.Path) -> dict | None:
    t = fil.read_text(encoding="utf-8")
    if not t.startswith("---\n"):
        return None
    slut = t.find("\n---", 4)
    if slut < 0:
        return None
    fm, noegle = {}, None
    for linje in t[4:slut].split("\n"):
        m = re.match(r"^([A-Za-z_-]+):\s*(.*)$", linje)
        if m:
            noegle = m.group(1)
            fm[noegle] = m.group(2).strip()
        elif noegle and linje.startswith((" ", "\t")):
            fm[noegle] = (fm[noegle] + " " + linje.strip()).strip()
    return fm


def laes_json(fil: pathlib.Path):
    try:
        return json.loads(fil.read_text(encoding="utf-8"))
    except Exception as e:
        FEJL.append(f"Ugyldig JSON: {fil.relative_to(ROD)} ({e})")
        return None


def main() -> int:
    kør_claude = "--claude" in sys.argv
    for f in ROD.rglob("*.json"):
        if not {"dist", "results", "node_modules"} & set(f.relative_to(ROD).parts):
            laes_json(f)

    plugin_dirs = sorted(p for p in PLUGINS.iterdir() if p.is_dir())
    navne = {}
    for p in plugin_dirs:
        man = p / ".claude-plugin" / "plugin.json"
        if not man.exists():
            FEJL.append(f"Mangler manifest: {p.relative_to(ROD)}")
            continue
        d = laes_json(man) or {}
        navne[p.name] = d
        if d.get("name") != p.name:
            FEJL.append(f"{p.name}: plugin.json name '{d.get('name')}' matcher ikke mappenavnet")
        if (p / "bin").exists():
            FEJL.append(f"{p.name}: bin/ er ikke tilladt (Cowork)")

    mp = laes_json(ROD / ".claude-plugin" / "marketplace.json") or {"plugins": []}
    mp_navne = {e["name"] for e in mp["plugins"]}
    for e in mp["plugins"]:
        src = ROD / e["source"]
        if not (src / ".claude-plugin" / "plugin.json").exists():
            FEJL.append(f"marketplace: kilde findes ikke for {e['name']} ({e['source']})")
    for n in navne:
        if n not in mp_navne:
            FEJL.append(f"marketplace: plugin {n} er ikke registreret")
    for n, d in navne.items():
        for dep in d.get("dependencies", []):
            if dep not in navne:
                FEJL.append(f"{n}: ukendt afhængighed {dep}")
    team = navne.get("byg-team", {})
    mangler = set(navne) - {"byg-team"} - set(team.get("dependencies", []))
    if mangler:
        FEJL.append(f"byg-team mangler afhængigheder: {', '.join(sorted(mangler))}")

    agenter, skills = {}, {}
    for p in plugin_dirs:
        for a in sorted(p.glob("agents/*.md")):
            fm = frontmatter(a)
            rel = a.relative_to(ROD)
            if not fm:
                FEJL.append(f"{rel}: mangler frontmatter")
                continue
            for k in ("name", "description", "tools", "model"):
                if not fm.get(k):
                    FEJL.append(f"{rel}: mangler '{k}'")
            if fm.get("name") != a.stem:
                FEJL.append(f"{rel}: name '{fm.get('name')}' matcher ikke filnavnet")
            if a.stem in agenter:
                FEJL.append(f"Agentnavn '{a.stem}' findes i både {agenter[a.stem]} og {p.name} (konflikt i samlet pakke)")
            agenter[a.stem] = p.name
            tools = {t.strip() for t in fm.get("tools", "").split(",")}
            if p.name == "byg-kontrol":
                regne = {v["kontrol"] for v in (laes_json(PLUGINS / "byg-kontrol" / "hooks" / "fagregister.json")
                                                or {"fag": {}})["fag"].values() if v.get("regnevaerktoej")}
                forbudt = {"Write", "Edit", "MultiEdit", "Agent", "NotebookEdit"} | (set() if a.stem in regne else {"Bash"})
                if tools & forbudt:
                    FEJL.append(f"{rel}: kontrolagenter må kun have læse- og søgeværktøjer"
                                " (Bash kun i fag med regneværktøj, låst af hooks/regne_vagt.py)")
                if "memory" in fm:
                    FEJL.append(f"{rel}: kontrolagenter må ikke have memory (giver Write/Edit)")
                # Standardmodel sonnet; KONTROLNIVEAU: fuld kaldes med model "opus" (håndhæves af kontrol_gate.py)
                if fm.get("model") not in ("sonnet", "opus"):
                    ADV.append(f"{rel}: kontrolagenten skal køre på sonnet (let) eller opus")
                if not str(fm.get("maxTurns") or "").isdigit():
                    ADV.append(f"{rel}: kontrolagenten mangler maxTurns (tokenbudget)")
            elif p.name != "byg":
                if "Agent" in tools:
                    FEJL.append(f"{rel}: fagagenter må ikke have Agent-værktøjet (de kalder ikke selv kontrollen)")
                hj = {h for v in (laes_json(PLUGINS / "byg-kontrol" / "hooks" / "fagregister.json") or {"fag": {}})["fag"].values()
                      for h in v.get("hjaelpere", [])}
                if a.stem not in hj and "FÆLLES-PROTOKOL:START" not in a.read_text(encoding="utf-8"):
                    FEJL.append(f"{rel}: mangler FÆLLES-PROTOKOL-markører")
        for s in sorted(p.glob("skills/*/SKILL.md")):
            fm = frontmatter(s) or {}
            rel = s.relative_to(ROD)
            if fm.get("name") != s.parent.name:
                FEJL.append(f"{rel}: name '{fm.get('name')}' matcher ikke mappenavnet")
            if not fm.get("description"):
                FEJL.append(f"{rel}: mangler description")
            if s.parent.name in skills:
                FEJL.append(f"Skill '{s.parent.name}' findes i både {skills[s.parent.name]} og {p.name} (konflikt i samlet pakke)")
            skills[s.parent.name] = p.name

    reg = laes_json(PLUGINS / "byg-kontrol" / "hooks" / "fagregister.json") or {"fag": {}}
    kontrol_agenter = {a.stem for a in (PLUGINS / "byg-kontrol" / "agents").glob("*.md")}
    registrerede = {v["kontrol"] for v in reg["fag"].values()} | {reg.get("projekt_kontrol")}
    for fag, v in reg["fag"].items():
        if v["agent"] not in agenter:
            FEJL.append(f"fagregister: fagagent '{v['agent']}' ({fag}) findes ikke")
        if v["kontrol"] not in kontrol_agenter:
            FEJL.append(f"fagregister: kontrolagent '{v['kontrol']}' ({fag}) findes ikke i byg-kontrol")
        if not (PLUGINS / "byg-kontrol" / "skills" / "kontrol-viden" / "references" / "fag" / f"{fag}.md").exists():
            FEJL.append(f"kontrol-viden mangler fagfil for '{fag}'")
    for k in kontrol_agenter - registrerede:
        FEJL.append(f"Kontrolagent '{k}' er ikke registreret i fagregister.json")
    hjaelpere = {h for v in reg["fag"].values() for h in v.get("hjaelpere", [])}
    for h in sorted(hjaelpere - set(agenter)):
        FEJL.append(f"fagregister: hjælpeagent '{h}' findes ikke")
    for n, pl in agenter.items():
        if pl.startswith("byg-") and pl not in ("byg-kontrol", "byg-team") and n not in {v["agent"] for v in reg["fag"].values()} \
                and n not in hjaelpere:
            FEJL.append(f"Fagagent '{n}' ({pl}) har ingen modsvarende kontrolagent i fagregister.json")
        if n in hjaelpere and agenter[n] not in ("byg-kontrol",):
            fm = frontmatter(next(PLUGINS.glob(f"*/agents/{n}.md"))) or {}
            if {t.strip() for t in fm.get("tools", "").split(",")} & {"Write", "Edit", "MultiEdit", "Agent", "NotebookEdit"} \
                    or "memory" in fm:
                FEJL.append(f"Hjælpeagent '{n}' må ikke kunne skrive (ingen Write/Edit/Agent/memory) – den retter aldrig selv")

    sti_re = re.compile(r"\$\{CLAUDE_PLUGIN_ROOT\}/([^\s`'\"()]+)")
    for p in plugin_dirs:
        for md in p.rglob("*.md"):
            if "evals" in md.relative_to(p).parts:
                continue
            tekst = md.read_text(encoding="utf-8")
            for m in sti_re.finditer(tekst):
                sti = m.group(1).rstrip(".,;:")
                if "<" in sti or "*" in sti:
                    continue
                if not (p / sti).exists():
                    FEJL.append(f"{md.relative_to(ROD)}: stien ${{CLAUDE_PLUGIN_ROOT}}/{sti} findes ikke i {p.name}")
            if "TODO" in tekst:
                ADV.append(f"{md.relative_to(ROD)}: indeholder TODO")

    for case in sorted(PLUGINS.glob("*/evals/*/")):
        if case.name == "results":
            continue
        prompt = case / "prompt.md"
        if not prompt.exists():
            FEJL.append(f"{case.relative_to(ROD)}: mangler prompt.md")
            continue
        graders = sorted((case / "graders").glob("*.md"))
        if not graders:
            FEJL.append(f"{case.relative_to(ROD)}: ingen graders")
        for g in graders:
            fm = frontmatter(g) or {}
            typ = fm.get("type")
            if typ not in GRADERTYPER:
                FEJL.append(f"{g.relative_to(ROD)}: ugyldig type '{typ}'")
            if typ == "tool_used" and not fm.get("tool"):
                FEJL.append(f"{g.relative_to(ROD)}: tool_used kræver 'tool'")
            if typ == "tool_order" and not ("before" in fm and "after" in fm):
                FEJL.append(f"{g.relative_to(ROD)}: tool_order kræver 'before' og 'after'")

    r = subprocess.run([sys.executable, str(ROD / "scripts" / "sync_protokol.py"), "--check"], capture_output=True, text=True)
    if r.returncode:
        FEJL.append("Protokoller ude af synk – kør scripts/sync_protokol.py\n" + r.stdout)
    r = subprocess.run([sys.executable, str(ROD / "scripts" / "udgiv.py"), "--check"], capture_output=True, text=True)
    if r.returncode:
        FEJL.append("Versionsnoter er ugyldige (versionsnoter/README.md):\n" + r.stdout)
    r = subprocess.run([sys.executable, str(ROD / "tests" / "test_kontrol_gate.py")], capture_output=True, text=True)
    if r.returncode:
        FEJL.append("Hook-tests fejlede:\n" + r.stdout[-2000:])
    r = subprocess.run([sys.executable, str(ROD / "tests" / "test_sagsflet.py")], capture_output=True, text=True)
    if r.returncode:
        FEJL.append("Tests af skriveret, forslag og sagernes git fejlede:\n" + r.stdout[-2000:])
    r = subprocess.run([sys.executable, str(ROD / "tests" / "test_regne_vagt.py")], capture_output=True, text=True)
    if r.returncode:
        FEJL.append("Tests af regnevagten fejlede:\n" + r.stdout[-2000:])
    for v in sorted(PLUGINS.glob("*/skills/*-viden/scripts/statik.py")):
        r = subprocess.run([sys.executable, str(v), "test"], capture_output=True, text=True)
        if r.returncode:
            FEJL.append(f"Selvtest af {v.relative_to(ROD)} fejlede:\n" + r.stdout[-2000:])
    r = subprocess.run([sys.executable, str(ROD / "tests" / "test_exam.py")], capture_output=True, text=True)
    if r.returncode:
        FEJL.append("Eksamenslaget (format, dækning af læringsmål eller rettelogik) fejlede:\n" + r.stdout[-2000:])
    r = subprocess.run([sys.executable, str(ROD / "tests" / "test_forsoeg.py")], capture_output=True, text=True)
    if r.returncode:
        FEJL.append("Forsøgsloggen, beslutningsreglen eller holdout-vagten fejlede:\n" + r.stdout[-2000:])
    r = subprocess.run([sys.executable, str(ROD / "tests" / "test_kontrol_ab.py")], capture_output=True, text=True)
    if r.returncode:
        FEJL.append("Kontrol-armen (parsing af domme eller opgørelse) fejlede:\n" + r.stdout[-2000:])
    r = subprocess.run([sys.executable, str(ROD / "scripts" / "tjek_data.py")], capture_output=True, text=True)
    if r.returncode:
        FEJL.append("Dataseparation – sagsdata eller hemmeligheder i repoet:\n" + r.stdout[-2000:])
    r = subprocess.run([sys.executable, str(ROD / "tests" / "test_tjek_data.py")], capture_output=True, text=True)
    if r.returncode:
        FEJL.append("Tests af dataseparationen fejlede:\n" + r.stdout[-2000:])

    if kør_claude:
        if not shutil.which("claude"):
            ADV.append("claude CLI ikke fundet – springer 'claude plugin validate' over")
        else:
            for p in plugin_dirs + [ROD]:
                r = subprocess.run(["claude", "plugin", "validate", str(p)], capture_output=True, text=True)
                if r.returncode or "Validation passed" not in r.stdout:
                    FEJL.append(f"claude plugin validate {p.relative_to(ROD) if p != ROD else '.'}:\n{r.stdout[-800:]}{r.stderr[-400:]}")

    for a in ADV:
        print(f"ADVARSEL  {a}")
    for f in FEJL:
        print(f"FEJL      {f}")
    print(f"\n{len(navne)} plugins · {len(agenter)} agenter · {len(skills)} skills · {len(FEJL)} fejl · {len(ADV)} advarsler")
    return 1 if FEJL else 0


if __name__ == "__main__":
    sys.exit(main())
