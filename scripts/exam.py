#!/usr/bin/env python3
"""Eksamenslaget: opgaver bygget på de officielle læringsmål, som fagagenterne testes mod.

Brug:
  python3 scripts/exam.py tjek [fag ...]            format og dækning (alle læringsmål i rollen har opgaver i begge sæt)
  python3 scripts/exam.py vis <fag> [--facit]       eksamenssættet og dækningskortet som markdown
  python3 scripts/exam.py koer <fag> [--arm plugin|basis|begge] [--saet udvikling|holdout|alle --udgivelse]
                                     [--id EL-001,...] [--kun-fejlede] [--gentag 1] [--gentag-fri 3]
                                     [--parallel 3] [--model M] [--bedoemmer sonnet] [--web]
                                     [--med-hukommelse] [--plugin-rev REV] [--uden-basis]
  python3 scripts/exam.py rapport <resultatfil> [<resultatfil> ...]
  python3 scripts/exam.py rebedoem <resultatfil> [--kun-fri]   ret gemte svar igen efter nyt facit/kriterier

Armene: 'basis' er modellen uden plugin, 'plugin' er fagagenten med sin videnbase (plugin-kopi uden
afhængigheder som i eval_fag.py og som standard uden agentens lokale hukommelse – med --med-hukommelse
måles plugin + hukommelse). Begge kører headless i en tom mappe uden brugerens plugins og uden internet
(medmindre --web). Standard er kun plugin-armen: basis afhænger ikke af videnbasen, så rapporten genbruger det nyeste
basis-svar pr. opgave. Holdout-sættet bruges kun til måling – aldrig som grundlag for ny tekst i videnbasen – og
kræver --udgivelse. --kun-fejlede kører kun de udviklingsopgaver, plugin-armen ikke bestod sidst.
Resultater gemmes i eksamen/<fag>/results/ (ignoreres af git). 'koer' kræver login og koster tokens.
"""
import argparse
import concurrent.futures
import datetime
import hashlib
import json
import pathlib
import re
import shutil
import subprocess
import sys
import tempfile
import threading

ROOT = pathlib.Path(__file__).resolve().parent.parent
EXAM_DIR = ROOT / "eksamen"
TYPES = {"valg", "tal", "fri"}
SETS = {"udvikling", "holdout"}
LEVELS = {"svend", "mester"}
ROLES = {"i", "uden"}

ANSWER_INSTRUCTIONS = {
    "valg": "Afslut med én linje i formatet `SVAR: <bogstav>`.",
    "tal": "Vis kort beregningen, og afslut med én linje i formatet `SVAR: <tal> <enhed>`.",
    "fri": "Svar fagligt og konkret, højst ca. 300 ord.",
}
EXAM_PREAMBLE = (
    "Dette er en skriftlig eksamensopgave. Besvar den, som du ville gøre det over for en censor, og ud fra "
    "gældende danske regler. Du har ikke adgang til internettet. Stil ikke opklarende spørgsmål – antag det "
    "mest almindelige, og skriv antagelsen."
)
GRADER_PROMPT = """Du er censor ved en dansk fagprøve. Bedøm besvarelsen strengt efter kriterierne og intet andet.

OPGAVE:
{question}

KRITERIER FOR BESTÅET (alle skal være opfyldt):
{criteria}

IKKE BESTÅET, hvis noget af dette gælder:
{fail_if}

BESVARELSE:
<<<
{answer}
>>>

Bedøm det faglige indhold. Henvisninger i parentes i et kriterium (paragraffer, normer, afsnit) er censorens kilde og skal ikke citeres i besvarelsen, medmindre kriteriet udtrykkeligt kræver en henvisning. Et fagligt korrekt svar, der siger det samme med andre ord, opfylder kriteriet. Et forsigtigt forbehold er ikke en fejl.

Tag stilling til hvert kriterium med én linje (`K1: ja|nej – kort begrundelse`). Afslut med præcis én linje: `DOM: BESTÅET` eller `DOM: IKKE BESTÅET`."""


# ---------- loading and validation ----------

def load_trade(trade: str) -> tuple[dict, list[dict]]:
    d = EXAM_DIR / trade
    goals = json.loads((d / "laeringsmaal.json").read_text(encoding="utf-8"))
    # Tasks may be split across opgaver*.json (one writer per file); they are validated as one set.
    tasks = []
    for f in sorted(d.glob("opgaver*.json")):
        tasks += json.loads(f.read_text(encoding="utf-8"))["opgaver"]
    return goals, tasks


def all_trades() -> list[str]:
    return sorted(p.name for p in EXAM_DIR.iterdir() if (p / "laeringsmaal.json").is_file()) if EXAM_DIR.is_dir() else []


def validate(trade: str) -> tuple[list[str], list[str]]:
    errors: list[str] = []
    warnings: list[str] = []
    try:
        goals, tasks = load_trade(trade)
    except Exception as e:  # noqa: BLE001 – report any load error as a validation error
        return [f"{trade}: kan ikke indlæses ({e})"], []
    for key in ("fag", "plugin", "agent", "kilder", "maal"):
        if key not in goals:
            errors.append(f"{trade}/laeringsmaal.json: mangler '{key}'")
    plugin_dir = ROOT / "plugins" / goals.get("plugin", "")
    if not (plugin_dir / "agents" / f"{goals.get('agent')}.md").is_file():
        errors.append(f"{trade}: agenten {goals.get('plugin')}:{goals.get('agent')} findes ikke")
    source_ids = {s.get("id") for s in goals.get("kilder", [])}
    for s in goals.get("kilder", []):
        for key in ("id", "titel", "url", "laest"):
            if not s.get(key):
                errors.append(f"{trade}: kilde {s.get('id', '?')} mangler '{key}'")
    goal_by_id: dict[str, dict] = {}
    for g in goals.get("maal", []):
        gid = g.get("id", "?")
        if gid in goal_by_id:
            errors.append(f"{trade}: læringsmål {gid} er dubleret")
        goal_by_id[gid] = g
        for key in ("kilde", "tekst", "rolle"):
            if not g.get(key):
                errors.append(f"{trade}: læringsmål {gid} mangler '{key}'")
        if g.get("kilde", "").split()[0:1] and g["kilde"].split()[0] not in source_ids:
            errors.append(f"{trade}: læringsmål {gid} henviser til ukendt kilde '{g['kilde'].split()[0]}'")
        if g.get("rolle") not in ROLES:
            errors.append(f"{trade}: læringsmål {gid} har ugyldig rolle '{g.get('rolle')}'")
        if g.get("rolle") == "uden" and not g.get("begrundelse"):
            errors.append(f"{trade}: læringsmål {gid} er uden for rollen uden begrundelse")
    seen: set[str] = set()
    coverage: dict[str, set[str]] = {gid: set() for gid in goal_by_id}
    for t in tasks:
        tid = t.get("id", "?")
        where = f"{trade}/{tid}"
        if tid in seen:
            errors.append(f"{where}: dubleret id")
        seen.add(tid)
        for key in ("maal", "saet", "type", "niveau", "spoergsmaal", "kilde", "status"):
            if not t.get(key):
                errors.append(f"{where}: mangler '{key}'")
        if t.get("type") not in TYPES:
            errors.append(f"{where}: ugyldig type '{t.get('type')}'")
        if t.get("saet") not in SETS:
            errors.append(f"{where}: ugyldigt sæt '{t.get('saet')}'")
        if t.get("niveau") not in LEVELS:
            errors.append(f"{where}: ugyldigt niveau '{t.get('niveau')}'")
        for gid in t.get("maal", []):
            if gid not in goal_by_id:
                errors.append(f"{where}: ukendt læringsmål '{gid}'")
            else:
                coverage[gid].add(t.get("saet", ""))
                if goal_by_id[gid].get("rolle") == "uden":
                    warnings.append(f"{where}: tester {gid}, som er uden for rollen")
        if t.get("type") == "valg":
            options = t.get("valgmuligheder") or {}
            if len(options) < 3:
                errors.append(f"{where}: valg kræver mindst 3 valgmuligheder")
            if t.get("facit") not in options:
                errors.append(f"{where}: facit '{t.get('facit')}' er ikke en valgmulighed")
        elif t.get("type") == "tal":
            f = t.get("facit")
            if not isinstance(f, dict) or not isinstance(f.get("vaerdi"), (int, float)):
                errors.append(f"{where}: tal kræver facit {{vaerdi, enhed, tolerance_pct}}")
            elif not isinstance(f.get("tolerance_pct", 0), (int, float)):
                errors.append(f"{where}: tolerance_pct skal være et tal")
        elif t.get("type") == "fri":
            if not t.get("kriterier"):
                errors.append(f"{where}: fri kræver 'kriterier'")
        if not str(t.get("status", "")).startswith(("V", "T")):
            errors.append(f"{where}: status skal begynde med V eller T")
        elif str(t.get("status")).startswith("T"):
            warnings.append(f"{where}: facit er ikke verificeret (T)")
    choices = [t for t in tasks if t.get("type") == "valg" and t.get("facit") in (t.get("valgmuligheder") or {})]
    if len(choices) >= 10:
        longest = sum(1 for t in choices
                      if len(t["valgmuligheder"][t["facit"]]) == max(len(v) for v in t["valgmuligheder"].values()))
        if longest / len(choices) > 0.4:
            warnings.append(f"{trade}: facit er den længste valgmulighed i {longest} af {len(choices)} valgopgaver – "
                            "afbalancér længden, så længden ikke afslører svaret")
    for gid, g in goal_by_id.items():
        if g.get("rolle") != "i":
            continue
        missing = SETS - coverage[gid]
        if missing:
            errors.append(f"{trade}: læringsmål {gid} har ingen opgave i {', '.join(sorted(missing))}")
    return errors, warnings


# ---------- rendering ----------

def render(trade: str, with_key: bool) -> str:
    goals, tasks = load_trade(trade)
    out = [f"# Eksamenssæt – {trade}", ""]
    out += ["## Kilder", "", "| ID | Kilde | Læst |", "|---|---|---|"]
    out += [f"| {s['id']} | [{s['titel']}]({s['url']}) | {s['laest']} |" for s in goals["kilder"]]
    out += ["", "## Dækningskort", "", "| Mål | Niveau | Læringsmål | Rolle | Opgaver |", "|---|---|---|---|---|"]
    by_goal: dict[str, list[str]] = {}
    for t in tasks:
        for gid in t["maal"]:
            by_goal.setdefault(gid, []).append(t["id"] + ("ᴴ" if t["saet"] == "holdout" else ""))
    for g in goals["maal"]:
        role = "i" if g["rolle"] == "i" else f"uden – {g.get('begrundelse', '')}"
        out.append(f"| {g['id']} | {g.get('niveau', '')} | {g['tekst']} | {role} | {', '.join(by_goal.get(g['id'], [])) or '–'} |")
    out += ["", "ᴴ = holdout (kun til måling).", "", "## Opgaver", ""]
    for t in tasks:
        out.append(f"### {t['id']} · {t['type']} · {t['niveau']} · {t['saet']} · mål {', '.join(t['maal'])}")
        out += ["", t["spoergsmaal"], ""]
        for k, v in (t.get("valgmuligheder") or {}).items():
            out.append(f"- **{k}** {v}")
        if with_key:
            out += ["", f"**Facit:** {format_key(t)}"]
            if t.get("kriterier"):
                out += ["", "Kriterier:"] + [f"- {c}" for c in t["kriterier"]]
            if t.get("fail_hvis"):
                out += ["", "Ikke bestået hvis:"] + [f"- {c}" for c in t["fail_hvis"]]
            if t.get("begrundelse"):
                out += ["", f"**Begrundelse:** {t['begrundelse']}"]
            out += ["", f"**Kilde:** {t['kilde']} · **Status:** {t['status']}"]
        out.append("")
    return "\n".join(out)


def format_key(t: dict) -> str:
    f = t.get("facit")
    if t["type"] == "valg":
        return str(f)
    if t["type"] == "tal":
        return f"{f['vaerdi']} {f.get('enhed', '')} (±{f.get('tolerance_pct', 0)} %)"
    return "efter kriterierne"


# ---------- grading ----------

# Claude Code returns these as an ordinary result text when the account limit is hit.
LIMIT_RE = re.compile(r"hit your (session|usage|weekly) limit|rate.?limit|overloaded", re.IGNORECASE)

ANSWER_RE = re.compile(r"^\W*SVAR\W*:\s*(.+?)\s*$", re.IGNORECASE | re.MULTILINE)


def extract_answer(text: str) -> str | None:
    matches = ANSWER_RE.findall(text or "")
    return matches[-1].strip("*`_ ") if matches else None


def parse_number(s: str) -> float | None:
    """Reads the first number in s; accepts Danish (1.234,5) and English (1,234.5 / 1234.5) notation."""
    m = re.search(r"[-−]?\d[\d.,  ]*", s or "")
    if not m:
        return None
    raw = m.group(0).replace("−", "-").replace(" ", "").replace(" ", "").rstrip(".,")
    if "," in raw and "." in raw:
        raw = raw.replace(".", "").replace(",", ".") if raw.rfind(",") > raw.rfind(".") else raw.replace(",", "")
    elif "," in raw:
        raw = raw.replace(",", ".") if not re.fullmatch(r"-?\d{1,3}(,\d{3})+", raw) else raw.replace(",", "")
    elif re.fullmatch(r"-?\d{1,3}(\.\d{3})+", raw):
        raw = raw.replace(".", "")
    try:
        return float(raw)
    except ValueError:
        return None


def grade_choice(task: dict, text: str) -> tuple[bool, str]:
    ans = extract_answer(text)
    if ans is None:
        return False, "ingen SVAR-linje"
    letter = re.match(r"([A-Za-z])\b", ans)
    got = letter.group(1).upper() if letter else ans[:1].upper()
    return got == str(task["facit"]).upper(), f"svarede {got}, facit {task['facit']}"


def grade_number(task: dict, text: str) -> tuple[bool, str]:
    ans = extract_answer(text)
    if ans is None:
        return False, "ingen SVAR-linje"
    value = parse_number(ans)
    if value is None:
        return False, f"intet tal i '{ans}'"
    f = task["facit"]
    target = float(f["vaerdi"])
    tol = abs(target) * float(f.get("tolerance_pct", 0)) / 100
    ok = abs(value - target) <= max(tol, 1e-9)
    return ok, f"svarede {value:g}, facit {target:g} {f.get('enhed', '')} ±{f.get('tolerance_pct', 0)} %"


def grade_verdict(text: str) -> tuple[bool, str]:
    m = re.findall(r"DOM:\s*(IKKE BESTÅET|BESTÅET)", text or "", re.IGNORECASE)
    if not m:
        return False, "bedømmeren gav ingen dom"
    return m[-1].upper() == "BESTÅET", m[-1].upper()


# ---------- running ----------

def run_claude(prompt: str, cwd: pathlib.Path, extra: list[str], timeout: int) -> dict:
    cmd = ["claude", "-p", prompt, "--output-format", "json", "--setting-sources", "local",
           "--permission-mode", "dontAsk", "--no-session-persistence", *extra]
    try:
        r = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, timeout=timeout)
    except subprocess.TimeoutExpired:
        return {"is_error": True, "result": "", "fejl": f"timeout efter {timeout} s"}
    try:
        return json.loads(r.stdout)
    except json.JSONDecodeError:
        return {"is_error": True, "result": "", "fejl": (r.stderr or r.stdout)[-500:]}


MEMORY_RE = re.compile(r"^memory:.*\n", re.MULTILINE)


def strip_memory(agent_file: pathlib.Path) -> bool:
    """Removes 'memory:' from the agent's frontmatter, so the user's local agent memory is not loaded."""
    text = agent_file.read_text(encoding="utf-8")
    end = text.find("\n---", 4)
    if not text.startswith("---\n") or end < 0:
        return False
    head, n = MEMORY_RE.subn("", text[:end + 1])
    if n:
        agent_file.write_text(head + text[end + 1:], encoding="utf-8")
    return bool(n)


def prepare_plugin(plugin: str, tmp: pathlib.Path, keep_memory: bool = False, rev: str = "") -> pathlib.Path:
    """Copy of the plugin without dependencies, so it loads without byg-kontrol (same as eval_fag.py).

    By default the agents' 'memory: user' is removed: the exam then measures the plugin alone, not the
    plugin plus the local agent memory (which may hold experience from the user's own cases)."""
    dst = tmp / plugin
    if rev:
        # The plugin as it was at a git revision, so knowledge-base versions can be compared on equal terms.
        export = tmp / f"rev-{rev}"
        export.mkdir()
        archive = subprocess.run(["git", "-C", str(ROOT), "archive", rev, f"plugins/{plugin}"],
                                 capture_output=True, check=True).stdout
        subprocess.run(["tar", "-x", "-C", str(export)], input=archive, check=True)
        shutil.copytree(export / "plugins" / plugin, dst, ignore=shutil.ignore_patterns("__pycache__", "results", "evals"))
    else:
        shutil.copytree(ROOT / "plugins" / plugin, dst, ignore=shutil.ignore_patterns("__pycache__", "results", "evals"))
    manifest = dst / ".claude-plugin" / "plugin.json"
    m = json.loads(manifest.read_text(encoding="utf-8"))
    m.pop("dependencies", None)
    manifest.write_text(json.dumps(m, ensure_ascii=False, indent=2), encoding="utf-8")
    if not keep_memory:
        for agent_file in (dst / "agents").glob("*.md"):
            strip_memory(agent_file)
    return dst


def shuffled_options(task: dict) -> tuple[dict, str]:
    """Options in a stable, id-seeded order relabelled A, B, C ... and the relabelled key.

    Authors tend to put the key in the same position; shuffling at run time removes that cue."""
    items = sorted(task["valgmuligheder"].items(),
                   key=lambda kv: hashlib.sha256(f"{task['id']}:{kv[0]}".encode()).hexdigest())
    labels = [chr(ord("A") + i) for i in range(len(items))]
    key = next(lbl for lbl, (orig, _) in zip(labels, items) if orig == task["facit"])
    return {lbl: text for lbl, (_, text) in zip(labels, items)}, key


def build_prompt(task: dict) -> str:
    parts = [EXAM_PREAMBLE, "", task["spoergsmaal"]]
    if task["type"] == "valg":
        options, _ = shuffled_options(task)
        parts += [""] + [f"{k}) {v}" for k, v in options.items()]
    parts += ["", ANSWER_INSTRUCTIONS[task["type"]]]
    return "\n".join(parts)


def arm_args(arm: str, args, plugin_dir: pathlib.Path | None, agent: str) -> list[str]:
    tools = "Read,Glob,Grep,Skill" + (",WebSearch,WebFetch" if args.web else "")
    extra = ["--tools", tools, "--max-turns", str(args.max_turns)]
    if args.model:
        extra += ["--model", args.model]
    if arm == "plugin":
        # --add-dir is required: in dontAsk mode Read/Grep outside the working directory are denied, so without it
        # the agent cannot open its own knowledge base. It grants the plugin copy only, not the repo (and its keys).
        extra += ["--plugin-dir", str(plugin_dir), "--add-dir", str(plugin_dir), "--agent", agent]
    return extra


def answer_task(task: dict, arm: str, args, tmp: pathlib.Path, plugin_dir: pathlib.Path | None,
                agent: str) -> dict:
    work = pathlib.Path(tempfile.mkdtemp(prefix="opgave-", dir=tmp))
    extra = arm_args(arm, args, plugin_dir, agent)
    res = run_claude(build_prompt(task), work, extra, args.timeout)
    text = res.get("result", "") or ""
    usage = res.get("usage") or {}
    entry = {"id": task["id"], "arm": arm, "type": task["type"], "saet": task["saet"], "niveau": task["niveau"],
             "maal": task["maal"], "svar": text, "pris_usd": res.get("total_cost_usd", 0.0),
             "ture": res.get("num_turns"), "sek": round((res.get("duration_ms") or 0) / 1000, 1),
             "tokens_ind": sum(usage.get(k) or 0 for k in
                               ("input_tokens", "cache_read_input_tokens", "cache_creation_input_tokens")),
             "tokens_ud": usage.get("output_tokens") or 0}
    if res.get("is_error") or not text or (len(text) < 300 and LIMIT_RE.search(text)):
        reason = res.get("fejl") or (text.strip()[:120] if text else res.get("subtype") or "tomt svar")
        entry.update(bestaaet=False, fejl=True, note=f"kørselsfejl: {reason}")
        return entry
    entry.update(grade(task, text, work, args))
    entry["pris_usd"] = (entry["pris_usd"] or 0) + entry.pop("pris_bedoemmelse", 0)
    return entry


def grade(task: dict, text: str, work: pathlib.Path, args) -> dict:
    """Grades one answer: choice and number deterministically, free text by an LLM examiner."""
    if task["type"] == "valg":
        _, key = shuffled_options(task)
        ok, note = grade_choice({**task, "facit": key}, text)
        return {"bestaaet": ok, "note": f"{note} (blandet rækkefølge; facit er {task['facit']} i opgavefilen)"}
    if task["type"] == "tal":
        ok, note = grade_number(task, text)
        return {"bestaaet": ok, "note": note}
    grader = GRADER_PROMPT.format(
        question=task["spoergsmaal"],
        criteria="\n".join(f"K{i}. {c}" for i, c in enumerate(task["kriterier"], 1)),
        fail_if="\n".join(f"- {c}" for c in task.get("fail_hvis", [])) or "- (ingen)",
        answer=text)
    g = run_claude(grader, work, ["--tools", "", "--max-turns", "1", "--model", args.bedoemmer], args.timeout)
    if g.get("is_error") or LIMIT_RE.search((g.get("result") or "")[:300]) and "DOM:" not in (g.get("result") or ""):
        return {"bestaaet": False, "fejl": True, "note": "kørselsfejl i bedømmelsen: "
                + (g.get("fejl") or (g.get("result") or "")[:120]), "pris_bedoemmelse": g.get("total_cost_usd") or 0}
    ok, note = grade_verdict(g.get("result", ""))
    return {"bestaaet": ok, "note": note, "bedoemmelse": g.get("result", ""),
            "pris_bedoemmelse": g.get("total_cost_usd") or 0}


def cmd_regrade(args) -> int:
    """Grades stored answers again against the current tasks (new key, criteria or grader) without new answers."""
    src = pathlib.Path(args.fil)
    d = json.loads(src.read_text(encoding="utf-8"))
    _, tasks = load_trade(d["fag"])
    by_id = {t["id"]: t for t in tasks}
    jobs = [r for r in d["resultater"] if r["id"] in by_id and r["svar"]
            and (not args.kun_fri or by_id[r["id"]]["type"] == "fri")]
    with tempfile.TemporaryDirectory(prefix="rebedoem-") as tmpname:
        work = pathlib.Path(tmpname)
        with concurrent.futures.ThreadPoolExecutor(max_workers=args.parallel) as pool:
            futures = {pool.submit(grade, by_id[r["id"]], r["svar"], work, args): r for r in jobs}
            for fut in concurrent.futures.as_completed(futures):
                r, g = futures[fut], fut.result()
                changed = "ÆNDRET " if g["bestaaet"] != r["bestaaet"] else ""
                r.pop("fejl", None)
                r["pris_usd"] = (r.get("pris_usd") or 0) + g.pop("pris_bedoemmelse", 0)
                r.update(g)
                print(f"  {changed}{'OK ' if r['bestaaet'] else 'NEJ'} {r['arm']:6} {r['id']:8} {r['note']}")
    d["rebedoemt"] = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
    out = src.with_name(src.stem + "-rebedoemt.json")
    out.write_text(json.dumps(d, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\nGemt: {out}\n")
    print(report([out]))
    return 0


def cmd_run(args) -> int:
    errors, _ = validate(args.fag)
    if errors:
        print("\n".join(f"FEJL  {e}" for e in errors))
        return 1
    if not shutil.which("claude"):
        print("claude CLI ikke fundet")
        return 1
    if args.saet != "udvikling" and not args.udgivelse:
        print("Holdout-sættet køres kun ved udgivelse eller en større ændring af videnbasen – tilføj --udgivelse.")
        return 1
    goals, tasks = load_trade(args.fag)
    if args.saet != "alle":
        tasks = [t for t in tasks if t["saet"] == args.saet]
    if args.id:
        wanted = set(args.id.split(","))
        tasks = [t for t in tasks if t["id"] in wanted]
    if args.kun_fejlede:
        failed = latest_failed_plugin(args.fag)
        tasks = [t for t in tasks if t["id"] in failed and t["saet"] == "udvikling"]
        print(f"Kun de {len(tasks)} udviklingsopgaver, plugin-armen ikke bestod sidst")
    arms = ["basis", "plugin"] if args.arm == "begge" else [args.arm]
    agent = f"{goals['plugin']}:{goals['agent']}"
    jobs = []
    for t in tasks:
        repeats = max(args.gentag, args.gentag_fri if t["type"] == "fri" else 0)
        jobs += [(t, arm) for _ in range(repeats) for arm in arms]
    print(f"{args.fag}: {len(tasks)} opgaver × {len(arms)} arm(e) = {len(jobs)} kørsler")
    lock = threading.Lock()
    results = []
    with tempfile.TemporaryDirectory(prefix="eksamen-") as tmpname:
        tmp = pathlib.Path(tmpname)
        plugin_dir = (prepare_plugin(goals["plugin"], tmp, args.med_hukommelse, args.plugin_rev)
                      if "plugin" in arms else None)
        kb_bytes = knowledge_base_bytes(plugin_dir) if plugin_dir else 0
        with concurrent.futures.ThreadPoolExecutor(max_workers=args.parallel) as pool:
            futures = [pool.submit(answer_task, t, arm, args, tmp, plugin_dir, agent) for t, arm in jobs]
            for fut in concurrent.futures.as_completed(futures):
                r = fut.result()
                with lock:
                    results.append(r)
                    print(f"  {'OK ' if r['bestaaet'] else 'NEJ'} {r['arm']:6} {r['id']:8} {r['note']}")
    stamp = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
    out_dir = EXAM_DIR / args.fag / "results"
    out_dir.mkdir(exist_ok=True)
    out = out_dir / f"{stamp}-{args.arm}-{args.saet}{'-' + args.plugin_rev if args.plugin_rev else ''}.json"
    out.write_text(json.dumps({"fag": args.fag, "tid": stamp, "model": args.model or "agentens",
                               "web": args.web, "hukommelse": args.med_hukommelse, "plugin_rev": args.plugin_rev or "arbejdstræ",
                               "videnbase_bytes": kb_bytes, "resultater": results}, ensure_ascii=False, indent=2),
                   encoding="utf-8")
    print(f"\nGemt: {out.relative_to(ROOT)}\n")
    extra, sources = ([], set())
    if arms == ["plugin"] and not args.uden_basis:
        extra, sources = latest_basis(args.fag, {t["id"] for t in tasks}, exclude=out)
    print(report([out], extra, sources))
    return 0


def result_files(trade: str, exclude: pathlib.Path | None = None) -> list[pathlib.Path]:
    """Valid result files, oldest first (files in folders marked 'ugyldig' and regraded copies are skipped)."""
    files = sorted((EXAM_DIR / trade / "results").glob("*.json"))
    return [f for f in files if f != exclude and "rebedoemt" not in f.name]


def valid_rows(f: pathlib.Path) -> list[dict]:
    rows = json.loads(f.read_text(encoding="utf-8"))["resultater"]
    return [r for r in rows if not (r.get("fejl") or str(r.get("note", "")).startswith("kørselsfejl"))]


def latest_basis(trade: str, ids: set[str], exclude: pathlib.Path | None = None) -> tuple[list[dict], set[str]]:
    """The newest basis answer per task. The basis arm does not depend on the knowledge base, so it is reused
    instead of being paid for again on every plugin run."""
    latest: dict[str, tuple[dict, str]] = {}
    for f in result_files(trade, exclude):
        for r in valid_rows(f):
            if r["arm"] == "basis" and r["id"] in ids:
                latest[r["id"]] = (r, f.name)
    return [r for r, _ in latest.values()], {name for _, name in latest.values()}


def latest_failed_plugin(trade: str) -> set[str]:
    latest: dict[str, bool] = {}
    for f in result_files(trade):
        for r in valid_rows(f):
            if r["arm"] == "plugin":
                latest[r["id"]] = r["bestaaet"]
    return {tid for tid, ok in latest.items() if not ok}


def knowledge_base_bytes(plugin_dir: pathlib.Path) -> int:
    """Size of what the agent can load: its prompt and the knowledge base (skills' references and SKILL.md)."""
    files = list(plugin_dir.glob("agents/*.md")) + list(plugin_dir.glob("skills/*/SKILL.md")) \
        + list(plugin_dir.glob("skills/*/references/*.md"))
    return sum(f.stat().st_size for f in files)


# ---------- reporting ----------

def pct(ok: int, n: int) -> str:
    return f"{ok}/{n} ({100 * ok / n:.0f} %)" if n else "–"


def report(files: list[pathlib.Path], extra_rows: list[dict] | None = None,
           reused_basis: set[str] | None = None) -> str:
    rows = list(extra_rows or [])
    trade = None
    kb_sizes: dict[str, int] = {}
    reused_basis = reused_basis or set()
    for f in files:
        d = json.loads(f.read_text(encoding="utf-8"))
        trade = d["fag"]
        rows += d["resultater"]
        if d.get("videnbase_bytes"):
            kb_sizes[d.get("plugin_rev", "arbejdstræ")] = d["videnbase_bytes"]
    arms = sorted({r["arm"] for r in rows})
    # Older result files only carry the note; treat those as run errors too.
    errors = [r for r in rows if r.get("fejl") or str(r.get("note", "")).startswith("kørselsfejl")]
    rows = [r for r in rows if r not in errors]
    out = [f"# Eksamensresultat – {trade}", ""]
    header = "| Del | " + " | ".join(arms) + " |"
    out += [header, "|---|" + "---|" * len(arms)]
    groups = [("I alt", lambda r: True)]
    groups += [(f"Sæt: {s}", lambda r, s=s: r["saet"] == s) for s in sorted(SETS)]
    groups += [(f"Type: {t}", lambda r, t=t: r["type"] == t) for t in sorted(TYPES)]
    groups += [(f"Niveau: {lv}", lambda r, lv=lv: r["niveau"] == lv) for lv in sorted(LEVELS)]
    for name, pred in groups:
        cells = []
        for arm in arms:
            sel = [r for r in rows if r["arm"] == arm and pred(r)]
            cells.append(pct(sum(r["bestaaet"] for r in sel), len(sel)))
        if any(c != "–" for c in cells):
            out.append(f"| {name} | " + " | ".join(cells) + " |")
    def per_arm(fn) -> list[str]:
        cells = []
        for arm in arms:
            sel = [r for r in rows if r["arm"] == arm]
            cells.append(fn(sel) if sel else "–")
        return cells

    def mean(sel, key, digits=1):
        vals = [r[key] for r in sel if r.get(key) is not None]
        return f"{sum(vals) / len(vals):.{digits}f}" if vals else "–"

    out.append("| Pris (USD) | " + " | ".join(per_arm(lambda s: f"{sum(r.get('pris_usd') or 0 for r in s):.2f}")) + " |")
    out.append("| Pris pr. bestået (USD) | " + " | ".join(per_arm(
        lambda s: f"{sum(r.get('pris_usd') or 0 for r in s) / sum(r['bestaaet'] for r in s):.3f}"
        if any(r["bestaaet"] for r in s) else "–")) + " |")
    out.append("| Tid pr. opgave (s) | " + " | ".join(per_arm(lambda s: mean(s, "sek"))) + " |")
    out.append("| Ture pr. opgave | " + " | ".join(per_arm(lambda s: mean(s, "ture"))) + " |")
    out.append("| Input-tokens pr. opgave | " + " | ".join(per_arm(lambda s: mean(s, "tokens_ind", 0))) + " |")
    if kb_sizes:
        out += ["", "Videnbasens størrelse (references + agentprompt): "
                + ", ".join(f"{rev}: {size / 1024:.1f} KB" for rev, size in kb_sizes.items())]
    if reused_basis:
        out += ["", f"Basis er genbrugt fra: {', '.join(sorted(reused_basis))}"]
    if errors:
        out += ["", f"**{len(errors)} kørselsfejl er ikke talt med** (fx ramt kontogrænse). Kør dem igen med "
                "`koer --id " + ",".join(sorted({r['id'] for r in errors})) + "`:", ""]
        out += [f"- {r['id']} ({r['arm']}): {r['note']}" for r in errors]

    by_task: dict[str, dict[str, list[bool]]] = {}
    goals_of: dict[str, list[str]] = {}
    for r in rows:
        by_task.setdefault(r["id"], {}).setdefault(r["arm"], []).append(r["bestaaet"])
        goals_of[r["id"]] = r["maal"]

    def passed(tid: str, arm: str) -> bool | None:
        v = by_task[tid].get(arm)
        return None if v is None else sum(v) * 2 > len(v)

    set_of = {r["id"]: r["saet"] for r in rows}
    failed_plugin = sorted(t for t in by_task if passed(t, "plugin") is False)
    regressions = sorted(t for t in failed_plugin if passed(t, "basis"))
    gains = sorted(t for t in by_task if passed(t, "plugin") and passed(t, "basis") is False)
    if "plugin" in arms:
        gaps = [t for t in failed_plugin if set_of[t] == "udvikling"]
        held = [t for t in failed_plugin if set_of[t] == "holdout"]
        out += ["", "## Huller (plugin ikke bestået) – kandidater til videnbasen, kun fra udviklingssættet", ""]
        out += [f"- {t} (mål {', '.join(goals_of[t])})" for t in gaps] or ["- ingen"]
        if held:
            out += ["", f"{len(held)} holdout-opgaver er ikke bestået. De vises ikke, fordi holdout aldrig må være "
                    "grundlag for videnbasen."]
    if {"basis", "plugin"} <= set(arms):
        out += ["", "## Regressioner (basis bestået, plugin ikke) – videnbasen vildleder", ""]
        out += [f"- {t} ({set_of[t]})" for t in regressions] or ["- ingen"]
        out += ["", "## Gevinst (plugin bestået, basis ikke)", ""]
        out += [f"- {t}" for t in gains] or ["- ingen"]
    return "\n".join(out)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("tjek")
    p.add_argument("fag", nargs="*")
    p = sub.add_parser("vis")
    p.add_argument("fag")
    p.add_argument("--facit", action="store_true")
    p = sub.add_parser("koer")
    p.add_argument("fag")
    p.add_argument("--arm", choices=["basis", "plugin", "begge"], default="plugin")
    p.add_argument("--saet", choices=["udvikling", "holdout", "alle"], default="udvikling")
    p.add_argument("--id", default="")
    p.add_argument("--parallel", type=int, default=4)
    p.add_argument("--model", default="")
    p.add_argument("--bedoemmer", default="sonnet")
    p.add_argument("--gentag", type=int, default=1)
    p.add_argument("--max-turns", type=int, default=12)
    p.add_argument("--timeout", type=int, default=600)
    p.add_argument("--web", action="store_true")
    p.add_argument("--gentag-fri", type=int, default=0, help="ekstra gentagelser kun af fri-opgaverne (støj)")
    p.add_argument("--kun-fejlede", action="store_true", help="kun udviklingsopgaver, plugin-armen ikke bestod sidst")
    p.add_argument("--udgivelse", action="store_true", help="kræves for at køre holdout-sættet")
    p.add_argument("--uden-basis", action="store_true", help="rapportér plugin-armen uden genbrugt basis")
    p.add_argument("--plugin-rev", default="", help="kør pluginet, som det var i en git-revision (fx før en ændring)")
    p.add_argument("--med-hukommelse", action="store_true",
                   help="indlæs fagagentens lokale hukommelse (~/.claude/agent-memory) i plugin-armen")
    p = sub.add_parser("rapport")
    p.add_argument("filer", nargs="+")
    p = sub.add_parser("rebedoem")
    p.add_argument("fil")
    p.add_argument("--kun-fri", action="store_true")
    p.add_argument("--parallel", type=int, default=4)
    p.add_argument("--bedoemmer", default="sonnet")
    p.add_argument("--timeout", type=int, default=600)
    args = ap.parse_args()

    if args.cmd == "tjek":
        trades = args.fag or all_trades()
        failed = False
        for trade in trades:
            errors, warnings = validate(trade)
            try:
                goals, tasks = load_trade(trade)
            except Exception:  # noqa: BLE001 – already reported by validate()
                goals, tasks = {}, []
            for w in warnings:
                print(f"ADVARSEL  {w}")
            for e in errors:
                print(f"FEJL      {e}")
            in_role = sum(1 for g in goals.get("maal", []) if g.get("rolle") == "i")
            print(f"{trade}: {len(goals.get('maal', []))} læringsmål ({in_role} i rollen) · {len(tasks)} opgaver · "
                  f"{len(errors)} fejl · {len(warnings)} advarsler")
            failed |= bool(errors)
        return 1 if failed else 0
    if args.cmd == "vis":
        print(render(args.fag, args.facit))
        return 0
    if args.cmd == "koer":
        return cmd_run(args)
    if args.cmd == "rebedoem":
        return cmd_regrade(args)
    print(report([pathlib.Path(f) for f in args.filer]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
