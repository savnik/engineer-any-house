#!/usr/bin/env python3
"""Structure check of Engineer Any House.

Usage: python3 scripts/validate.py [--claude]   (--claude also runs `claude plugin validate` on all plugins and the marketplace)
Checks: JSON, marketplace and dependencies, frontmatter and unique names (also for the combined package), tools of
trade and review agents, trade register, ${CLAUDE_PLUGIN_ROOT} paths, evals, protocols in sync, version notes, no bin/,
hook tests, the exam layer, the experiment log, the frame files, data separation, shared environment module and locked
environments in sync, and hooks/bootstrap scripts using only the standard library.
"""
import ast
import json
import pathlib
import re
import shutil
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
PLUGINS = ROOT / "plugins"
ERRORS: list[str] = []
WARNINGS: list[str] = []
GRADER_TYPES = {"regex", "tool_order", "tool_used", "file_exists", "llm", "baseline"}


def frontmatter(path: pathlib.Path) -> dict | None:
    t = path.read_text(encoding="utf-8")
    if not t.startswith("---\n"):
        return None
    end = t.find("\n---", 4)
    if end < 0:
        return None
    fm, key = {}, None
    for line in t[4:end].split("\n"):
        m = re.match(r"^([A-Za-z_-]+):\s*(.*)$", line)
        if m:
            key = m.group(1)
            fm[key] = m.group(2).strip()
        elif key and line.startswith((" ", "\t")):
            fm[key] = (fm[key] + " " + line.strip()).strip()
    return fm


# Runs with the system python3 before any venv exists: standard library and sibling modules only.
# bim.py/fem.py: only module-level imports (their libraries are imported after switching into the venv).
STDLIB_ONLY = ["plugins/*/hooks/*.py", "scripts/hooks/*.py", "shared/environment.py",
              "plugins/*/skills/*/scripts/environment.py", "plugins/*/skills/*/scripts/statik.py",
              "plugins/*/skills/*/scripts/el.py"]
STDLIB_ONLY_TOP = ["plugins/*/skills/*/scripts/bim.py", "plugins/*/skills/*/scripts/fem.py"]


def non_stdlib(path: pathlib.Path, top_only: bool) -> list[str]:
    """Imported top-level modules that are neither standard library nor a sibling .py file."""
    tree = ast.parse(path.read_text(encoding="utf-8"))
    nodes = tree.body if top_only else ast.walk(tree)
    names = set()
    for n in nodes:
        if isinstance(n, ast.Import):
            names.update(a.name.split(".")[0] for a in n.names)
        elif isinstance(n, ast.ImportFrom) and n.level == 0 and n.module:
            names.add(n.module.split(".")[0])
    return sorted(m for m in names
                  if m not in sys.stdlib_module_names and m != "__future__" and not (path.parent / f"{m}.py").exists())


def read_json(path: pathlib.Path):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception as e:
        ERRORS.append(f"Ugyldig JSON: {path.relative_to(ROOT)} ({e})")
        return None


def main() -> int:
    run_claude = "--claude" in sys.argv
    for f in ROOT.rglob("*.json"):
        if not {"dist", "results", "node_modules"} & set(f.relative_to(ROOT).parts):
            read_json(f)

    plugin_dirs = sorted(p for p in PLUGINS.iterdir() if p.is_dir())
    names = {}
    for p in plugin_dirs:
        man = p / ".claude-plugin" / "plugin.json"
        if not man.exists():
            ERRORS.append(f"Mangler manifest: {p.relative_to(ROOT)}")
            continue
        d = read_json(man) or {}
        names[p.name] = d
        if d.get("name") != p.name:
            ERRORS.append(f"{p.name}: plugin.json name '{d.get('name')}' matcher ikke mappenavnet")
        if (p / "bin").exists():
            ERRORS.append(f"{p.name}: bin/ er ikke tilladt (Cowork)")

    mp = read_json(ROOT / ".claude-plugin" / "marketplace.json") or {"plugins": []}
    mp_names = {e["name"] for e in mp["plugins"]}
    for e in mp["plugins"]:
        src = ROOT / e["source"]
        if not (src / ".claude-plugin" / "plugin.json").exists():
            ERRORS.append(f"marketplace: kilde findes ikke for {e['name']} ({e['source']})")
    for n in names:
        if n not in mp_names:
            ERRORS.append(f"marketplace: plugin {n} er ikke registreret")
    for n, d in names.items():
        for dep in d.get("dependencies", []):
            if dep not in names:
                ERRORS.append(f"{n}: ukendt afhængighed {dep}")
    team = names.get("byg-team", {})
    missing = set(names) - {"byg-team"} - set(team.get("dependencies", []))
    if missing:
        ERRORS.append(f"byg-team mangler afhængigheder: {', '.join(sorted(missing))}")

    agents, skills = {}, {}
    for p in plugin_dirs:
        for a in sorted(p.glob("agents/*.md")):
            fm = frontmatter(a)
            rel = a.relative_to(ROOT)
            if not fm:
                ERRORS.append(f"{rel}: mangler frontmatter")
                continue
            for k in ("name", "description", "tools", "model"):
                if not fm.get(k):
                    ERRORS.append(f"{rel}: mangler '{k}'")
            if fm.get("name") != a.stem:
                ERRORS.append(f"{rel}: name '{fm.get('name')}' matcher ikke filnavnet")
            if a.stem in agents:
                ERRORS.append(f"Agentnavn '{a.stem}' findes i både {agents[a.stem]} og {p.name} (konflikt i samlet pakke)")
            agents[a.stem] = p.name
            tools = {t.strip() for t in fm.get("tools", "").split(",")}
            if p.name == "byg-review":
                calc_reviewers = {v["kontrol"] for v in (read_json(PLUGINS / "byg-review" / "hooks" / "trade-registry.json")
                                                or {"fag": {}})["fag"].values() if v.get("regnevaerktoej")}
                forbidden = {"Write", "Edit", "MultiEdit", "Agent", "NotebookEdit"} | (set() if a.stem in calc_reviewers else {"Bash"})
                if tools & forbidden:
                    ERRORS.append(f"{rel}: kontrolagenter må kun have læse- og søgeværktøjer"
                                " (Bash kun i fag med regneværktøj, låst af hooks/calc_guard.py)")
                if "memory" in fm:
                    ERRORS.append(f"{rel}: kontrolagenter må ikke have memory (giver Write/Edit)")
                # Default model sonnet; REVIEW-LEVEL: full is called with model "opus" (enforced by review_gate.py)
                if fm.get("model") not in ("sonnet", "opus"):
                    WARNINGS.append(f"{rel}: kontrolagenten skal køre på sonnet (let) eller opus")
                if not str(fm.get("maxTurns") or "").isdigit():
                    WARNINGS.append(f"{rel}: kontrolagenten mangler maxTurns (tokenbudget)")
            elif p.name != "byg":
                if "Agent" in tools:
                    ERRORS.append(f"{rel}: fagagenter må ikke have Agent-værktøjet (de kalder ikke selv kontrollen)")
                helper_names = {h for v in (read_json(PLUGINS / "byg-review" / "hooks" / "trade-registry.json") or {"fag": {}})["fag"].values()
                      for h in v.get("hjaelpere", []) + v.get("opslag", [])}
                if a.stem not in helper_names and "SHARED-PROTOCOL:START" not in a.read_text(encoding="utf-8"):
                    ERRORS.append(f"{rel}: mangler SHARED-PROTOCOL-markører")
        for s in sorted(p.glob("skills/*/SKILL.md")):
            fm = frontmatter(s) or {}
            rel = s.relative_to(ROOT)
            if fm.get("name") != s.parent.name:
                ERRORS.append(f"{rel}: name '{fm.get('name')}' matcher ikke mappenavnet")
            if not fm.get("description"):
                ERRORS.append(f"{rel}: mangler description")
            if s.parent.name in skills:
                ERRORS.append(f"Skill '{s.parent.name}' findes i både {skills[s.parent.name]} og {p.name} (konflikt i samlet pakke)")
            skills[s.parent.name] = p.name

    reg = read_json(PLUGINS / "byg-review" / "hooks" / "trade-registry.json") or {"fag": {}}
    review_agents = {a.stem for a in (PLUGINS / "byg-review" / "agents").glob("*.md")}
    registered = {v["kontrol"] for v in reg["fag"].values()} | {reg.get("projekt_kontrol")}
    for trade, v in reg["fag"].items():
        if v["agent"] not in agents:
            ERRORS.append(f"trade-registry: fagagent '{v['agent']}' ({trade}) findes ikke")
        if v["kontrol"] not in review_agents:
            ERRORS.append(f"trade-registry: kontrolagent '{v['kontrol']}' ({trade}) findes ikke i byg-review")
        if not (PLUGINS / "byg-review" / "skills" / "review-knowledge" / "references" / "trades" / f"{trade}.md").exists():
            ERRORS.append(f"review-knowledge mangler fagfil for '{trade}'")
    for k in review_agents - registered:
        ERRORS.append(f"Kontrolagent '{k}' er ikke registreret i trade-registry.json")
    helpers = {h for v in reg["fag"].values() for h in v.get("hjaelpere", [])}
    lookups = {h for v in reg["fag"].values() for h in v.get("opslag", [])}
    for h in sorted(helpers - set(agents)):
        ERRORS.append(f"trade-registry: hjælpeagent '{h}' findes ikke")
    for h in sorted(lookups - set(agents)):
        ERRORS.append(f"trade-registry: opslagsagent '{h}' findes ikke")
    for h in sorted(lookups & helpers):
        ERRORS.append(f"trade-registry: '{h}' er både hjælpe- og opslagsagent")
    for n, plugin in agents.items():
        if plugin.startswith("byg-") and plugin not in ("byg-review", "byg-team") and n not in {v["agent"] for v in reg["fag"].values()} \
                and n not in helpers | lookups:
            ERRORS.append(f"Fagagent '{n}' ({plugin}) har ingen modsvarende kontrolagent i trade-registry.json")
        if n in helpers | lookups and agents[n] not in ("byg-review",):
            fm = frontmatter(next(PLUGINS.glob(f"*/agents/{n}.md"))) or {}
            if {t.strip() for t in fm.get("tools", "").split(",")} & {"Write", "Edit", "MultiEdit", "Agent", "NotebookEdit"} \
                    or "memory" in fm:
                ERRORS.append(f"Hjælpeagent '{n}' må ikke kunne skrive (ingen Write/Edit/Agent/memory) – den retter aldrig selv")

    path_re = re.compile(r"\$\{CLAUDE_PLUGIN_ROOT\}/([^\s`'\"()]+)")
    for p in plugin_dirs:
        for md in p.rglob("*.md"):
            if "evals" in md.relative_to(p).parts:
                continue
            text = md.read_text(encoding="utf-8")
            for m in path_re.finditer(text):
                path = m.group(1).rstrip(".,;:")
                if "<" in path or "*" in path:
                    continue
                if not (p / path).exists():
                    ERRORS.append(f"{md.relative_to(ROOT)}: stien ${{CLAUDE_PLUGIN_ROOT}}/{path} findes ikke i {p.name}")
            if "TODO" in text:
                WARNINGS.append(f"{md.relative_to(ROOT)}: indeholder TODO")

    for case in sorted(PLUGINS.glob("*/evals/*/")):
        if case.name == "results":
            continue
        prompt = case / "prompt.md"
        if not prompt.exists():
            ERRORS.append(f"{case.relative_to(ROOT)}: mangler prompt.md")
            continue
        graders = sorted((case / "graders").glob("*.md"))
        if not graders:
            ERRORS.append(f"{case.relative_to(ROOT)}: ingen graders")
        for g in graders:
            fm = frontmatter(g) or {}
            kind = fm.get("type")
            if kind not in GRADER_TYPES:
                ERRORS.append(f"{g.relative_to(ROOT)}: ugyldig type '{kind}'")
            if kind == "tool_used" and not fm.get("tool"):
                ERRORS.append(f"{g.relative_to(ROOT)}: tool_used kræver 'tool'")
            if kind == "tool_order" and not ("before" in fm and "after" in fm):
                ERRORS.append(f"{g.relative_to(ROOT)}: tool_order kræver 'before' og 'after'")

    r = subprocess.run([sys.executable, str(ROOT / "scripts" / "sync_protocol.py"), "--check"], capture_output=True, text=True)
    if r.returncode:
        ERRORS.append("Protokoller ude af synk – kør scripts/sync_protocol.py\n" + r.stdout)
    r = subprocess.run([sys.executable, str(ROOT / "scripts" / "sync_environment.py"), "--check"], capture_output=True, text=True)
    if r.returncode:
        ERRORS.append("Det fælles miljømodul er ude af synk – kør scripts/sync_environment.py\n" + r.stdout)
    r = subprocess.run([sys.executable, str(ROOT / "scripts" / "lock_environment.py"), "--check"], capture_output=True, text=True)
    if r.returncode:
        ERRORS.append("Låste miljøer passer ikke til requirements*.in – kør scripts/lock_environment.py\n" + r.stdout)
    for patterns, top_only in ((STDLIB_ONLY, False), (STDLIB_ONLY_TOP, True)):
        for path in sorted({f for m in patterns for f in ROOT.glob(m)}):
            if foreign := non_stdlib(path, top_only):
                ERRORS.append(f"{path.relative_to(ROOT)}: importerer {', '.join(foreign)} – hooks og opstartsscripts må kun "
                            "bruge standardbiblioteket (ARCHITECTURE.md, Python-miljøer)")
    r = subprocess.run([sys.executable, str(ROOT / "scripts" / "release.py"), "--check"], capture_output=True, text=True)
    if r.returncode:
        ERRORS.append("Versionsnoter er ugyldige (release-notes/README.md):\n" + r.stdout)
    r = subprocess.run([sys.executable, str(ROOT / "tests" / "test_review_gate.py")], capture_output=True, text=True)
    if r.returncode:
        ERRORS.append("Hook-tests fejlede:\n" + r.stdout[-2000:])
    r = subprocess.run([sys.executable, str(ROOT / "tests" / "test_case_merge.py")], capture_output=True, text=True)
    if r.returncode:
        ERRORS.append("Tests af skriveret, forslag og sagernes git fejlede:\n" + r.stdout[-2000:])
    r = subprocess.run([sys.executable, str(ROOT / "tests" / "test_calc_guard.py")], capture_output=True, text=True)
    if r.returncode:
        ERRORS.append("Tests af regnevagten fejlede:\n" + r.stdout[-2000:])
    r = subprocess.run([sys.executable, str(ROOT / "tests" / "test_el.py")], capture_output=True, text=True)
    if r.returncode:
        ERRORS.append("Tests af el-regneværktøjet (el.py) fejlede:\n" + r.stdout[-2000:])
    for v in sorted([*PLUGINS.glob("*/skills/*-knowledge/scripts/statik.py"), *PLUGINS.glob("*/skills/*-knowledge/scripts/el.py")]):
        r = subprocess.run([sys.executable, str(v), "test"], capture_output=True, text=True)
        if r.returncode:
            ERRORS.append(f"Selvtest af {v.relative_to(ROOT)} fejlede:\n" + r.stdout[-2000:])
    r = subprocess.run([sys.executable, str(ROOT / "tests" / "test_exam.py")], capture_output=True, text=True)
    if r.returncode:
        ERRORS.append("Eksamenslaget (format, dækning af læringsmål eller rettelogik) fejlede:\n" + r.stdout[-2000:])
    r = subprocess.run([sys.executable, str(ROOT / "tests" / "test_experiment.py")], capture_output=True, text=True)
    if r.returncode:
        ERRORS.append("Forsøgsloggen, beslutningsreglen eller holdout-vagten fejlede:\n" + r.stdout[-2000:])
    r = subprocess.run([sys.executable, str(ROOT / "tests" / "test_comparer_guard.py")], capture_output=True, text=True)
    if r.returncode:
        ERRORS.append("Sammenligner-vagten (bim-sammenlignerens tilladte kommandoer) fejlede:\n" + r.stdout[-2000:])
    r = subprocess.run([sys.executable, str(ROOT / "tests" / "test_review_ab.py")], capture_output=True, text=True)
    if r.returncode:
        ERRORS.append("Kontrol-armen (parsing af domme eller opgørelse) fejlede:\n" + r.stdout[-2000:])
    r = subprocess.run([sys.executable, str(ROOT / "tests" / "test_frames.py")], capture_output=True, text=True)
    if r.returncode:
        ERRORS.append("Rammefilerne (references/frames.md: format, status eller ID'er) fejlede:\n" + r.stdout[-2000:])
    r = subprocess.run([sys.executable, str(ROOT / "scripts" / "check_data.py")], capture_output=True, text=True)
    if r.returncode:
        ERRORS.append("Dataseparation – sagsdata eller hemmeligheder i repoet:\n" + r.stdout[-2000:])
    r = subprocess.run([sys.executable, str(ROOT / "tests" / "test_check_data.py")], capture_output=True, text=True)
    if r.returncode:
        ERRORS.append("Tests af dataseparationen fejlede:\n" + r.stdout[-2000:])

    if run_claude:
        if not shutil.which("claude"):
            WARNINGS.append("claude CLI ikke fundet – springer 'claude plugin validate' over")
        else:
            for p in plugin_dirs + [ROOT]:
                r = subprocess.run(["claude", "plugin", "validate", str(p)], capture_output=True, text=True)
                if r.returncode or "Validation passed" not in r.stdout:
                    ERRORS.append(f"claude plugin validate {p.relative_to(ROOT) if p != ROOT else '.'}:\n{r.stdout[-800:]}{r.stderr[-400:]}")

    for a in WARNINGS:
        print(f"ADVARSEL  {a}")
    for f in ERRORS:
        print(f"FEJL      {f}")
    print(f"\n{len(names)} plugins · {len(agents)} agenter · {len(skills)} skills · {len(ERRORS)} fejl · {len(WARNINGS)} advarsler")
    return 1 if ERRORS else 0


if __name__ == "__main__":
    sys.exit(main())
