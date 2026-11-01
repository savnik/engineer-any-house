#!/usr/bin/env python3
"""Eksamenslaget: opgaver bygget på de officielle læringsmål, som fagagenterne testes mod.

Brug:
  python3 scripts/exam.py check [fag ...]           format og dækning (alle læringsmål i rollen har opgaver i begge sæt)
  python3 scripts/exam.py show <fag> [--answer-key] [--set development]   sættet og dækningskortet som markdown
  python3 scripts/exam.py run <fag> [--arm plugin|base|both] [--set development|holdout|regression|all --release]
                                    [--id EL-001,...] [--only-failed] [--repeat 1] [--repeat-free 3]
                                    [--parallel 3] [--model M] [--grader sonnet] [--web]
                                    [--with-memory] [--plugin-rev REV] [--no-base] [--calc-tool]
  python3 scripts/exam.py answers <fag> [--id EL-001,...] [--arm plugin|base] [--file FIL]
                                    seneste svar, bedømmelse og værktøjskald (kun udvikling)
  python3 scripts/exam.py report <resultatfil> [<resultatfil> ...]
  python3 scripts/exam.py regrade <resultatfil> [--only-free]   ret gemte svar igen efter nyt facit/kriterier

Armene: 'basis' (--arm base) er modellen uden plugin, 'plugin' er fagagenten med sin videnbase (plugin-kopi uden
afhængigheder som i eval_trade.py og som standard uden agentens lokale hukommelse – med --with-memory
måles plugin + hukommelse). Begge kører headless i en tom mappe uden brugerens plugins og uden internet
(medmindre --web). Standard er kun plugin-armen: basis afhænger ikke af videnbasen, så rapporten genbruger det nyeste
basis-svar pr. opgave. Holdout-sættet bruges kun til måling – aldrig som grundlag for ny tekst i videnbasen – og
kræver --release. Efter et holdout-skifte (holdout_filer i learning-goals.json) er tidligere holdout-opgaver
sættet 'regression': skjult som holdout, men kun et regressionsværn. --only-failed kører kun de
udviklingsopgaver, plugin-armen ikke bestod sidst.
--calc-tool giver plugin-armen Bash, låst af scripts/hooks/exam_calc_guard.py til fagets regneværktøj
(trade-registry 'regnevaerktoej'), og Write til en .json-inputfil i opgavemappen. Uden flaget har ingen arm Bash.
Resultater gemmes i exam/<fag>/results/ (ignoreres af git). 'run' kræver login og koster tokens.
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
EXAM_DIR = ROOT / "exam"
TYPES = {"valg", "tal", "fri", "case"}
PART_TYPES = {"valg", "tal", "fri"}
CASE_PASS_SHARE = 0.6  # like the written trade exams: about 60 of 100 points to pass
SETS = {"udvikling", "holdout", "regression"}
STORED_SETS = {"udvikling", "holdout"}  # the values written in the task files
# Never shown to the CI agent. 'regression' holds former holdout tasks: still hidden, but run only to catch
# regressions, because they no longer count as an independent measure (see holdout_files).
HIDDEN_SETS = {"holdout", "regression"}
# CLI choice (English) ↔ stored data value (Danish).
CLI_VALUES = {"development": "udvikling", "all": "alle", "base": "basis", "both": "begge"}
LEVELS = {"svend", "mester"}
ROLES = {"i", "uden"}

ANSWER_INSTRUCTIONS = {
    "valg": "Afslut med én linje i formatet `ANSWER: <bogstav>`.",
    "tal": "Vis kort beregningen, og afslut med én linje i formatet `ANSWER: <tal> <enhed>`.",
    "fri": "Svar fagligt og konkret, højst ca. 300 ord.",
    "case": "Besvar hver del under overskriften 'Del <bogstav>'. Afslut regnedele med én linje "
            "`ANSWER <bogstav>: <tal> <enhed>` og valgdele med `ANSWER <bogstav>: <bogstav for svaret>`. "
            "Skøn- og rådgivningsdele besvares fagligt og konkret med højst ca. 200 ord pr. del.",
}
EXAM_PREAMBLE = (
    "Dette er en skriftlig eksamensopgave. Besvar den, som du ville gøre det over for en censor, og ud fra "
    "gældende danske regler. Du har ikke adgang til internettet. Stil ikke opklarende spørgsmål – antag det "
    "mest almindelige, og skriv antagelsen."
)
GRADER_PROMPT = """Du er censor ved en dansk fagprøve. Bedøm besvarelsen strengt efter kriterierne og intet andet.

TASK:
{question}

KRITERIER FOR BESTÅET (alle skal være opfyldt):
{criteria}

IKKE BESTÅET, hvis noget af dette gælder:
{fail_if}

RESPONSE:
<<<
{answer}
>>>

Bedøm det faglige indhold. Henvisninger i parentes i et kriterium (paragraffer, normer, afsnit) er censorens kilde og skal ikke citeres i besvarelsen, medmindre kriteriet udtrykkeligt kræver en henvisning. Et fagligt korrekt svar, der siger det samme med andre ord, opfylder kriteriet. Et forsigtigt forbehold er ikke en fejl.

Tag stilling til hvert kriterium med én linje (`K1: ja|nej – kort begrundelse`). Afslut med præcis én linje: `VERDICT: BESTÅET` eller `VERDICT: IKKE BESTÅET`."""


CASE_GRADER_PROMPT = """Du er censor ved en dansk mesterprøve. Bedøm kun de nævnte dele af besvarelsen strengt efter deres kriterier.

Bedøm det faglige indhold. Henvisninger i parentes i et kriterium er censorens kilde og skal ikke citeres, medmindre kriteriet udtrykkeligt kræver en henvisning. Et fagligt korrekt svar med andre ord opfylder kriteriet.

CASE:
{question}

{parts}

RESPONSE:
<<<
{answer}
>>>

For hver del: én linje pr. kriterium (`<del>K1: ja|nej – kort begrundelse`) og derefter præcis én linje `VERDICT <del>: BESTÅET` eller `VERDICT <del>: IKKE BESTÅET`. En del er kun bestået, hvis alle dens kriterier er opfyldt og intet af dens 'ikke bestået'-forhold gælder."""


# ---------- loading and validation ----------

def holdout_files(goals: dict) -> set[str] | None:
    """The task files whose holdout tasks form the trade's current holdout set ('holdout_filer' in
    learning-goals.json). None means no switch has been made: every holdout task counts as holdout.

    After a switch, holdout tasks in the other files belong to the set 'regression': they stay hidden, but they
    are no longer an independent measure and do not count against the holdout budget."""
    files = goals.get("holdout_filer")
    return set(files) if files else None


def load_trade(trade: str, stored: bool = False) -> tuple[dict, list[dict]]:
    """Goals and tasks. Each task's 'saet' is its current set; stored=True keeps the value in the task file."""
    d = EXAM_DIR / trade
    goals = json.loads((d / "learning-goals.json").read_text(encoding="utf-8"))
    active = None if stored else holdout_files(goals)
    # Tasks may be split across tasks*.json (one writer per file); they are validated as one set.
    tasks = []
    for f in sorted(d.glob("tasks*.json")):
        for t in json.loads(f.read_text(encoding="utf-8"))["opgaver"]:
            if active is not None and t.get("saet") == "holdout" and f.name not in active:
                t["saet"] = "regression"
            tasks.append(t)
    return goals, tasks


_SETS_CACHE: dict[tuple[str, str], dict[str, str]] = {}


def current_sets(trade: str) -> dict[str, str]:
    """Task id -> current set, or {} when the trade cannot be loaded."""
    key = (str(EXAM_DIR), trade)
    if key not in _SETS_CACHE:
        try:
            _SETS_CACHE[key] = {t["id"]: t["saet"] for t in load_trade(trade)[1]}
        except (OSError, ValueError, KeyError):
            _SETS_CACHE[key] = {}
    return _SETS_CACHE[key]


def result_rows(d: dict) -> list[dict]:
    """The rows of a result file with each task's current set. Rows written before a holdout switch say
    'holdout' for tasks that are now in 'regression'."""
    sets = current_sets(d.get("fag", ""))
    return [{**r, "saet": sets.get(r["id"], r["saet"])} for r in d["resultater"]]


def all_trades() -> list[str]:
    return sorted(p.name for p in EXAM_DIR.iterdir() if (p / "learning-goals.json").is_file()) if EXAM_DIR.is_dir() else []


def validate(trade: str) -> tuple[list[str], list[str]]:
    errors: list[str] = []
    warnings: list[str] = []
    try:
        goals, tasks = load_trade(trade, stored=True)
    except Exception as e:  # noqa: BLE001 – report any load error as a validation error
        return [f"{trade}: kan ikke indlæses ({e})"], []
    active = holdout_files(goals)
    if active is not None:
        d = EXAM_DIR / trade
        for name in sorted(active):
            f = d / name
            if not f.is_file() or not name.startswith("tasks"):
                errors.append(f"{trade}/learning-goals.json: holdout_filer nævner {name}, som ikke er en opgavefil")
            elif not any(t.get("saet") == "holdout" for t in json.loads(f.read_text(encoding="utf-8"))["opgaver"]):
                errors.append(f"{trade}/learning-goals.json: {name} i holdout_filer har ingen holdout-opgaver")
    for key in ("fag", "plugin", "agent", "kilder", "maal"):
        if key not in goals:
            errors.append(f"{trade}/learning-goals.json: mangler '{key}'")
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
        if t.get("saet") not in STORED_SETS:
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
        if t.get("type") == "case":
            parts = t.get("dele") or []
            if len(parts) < 2:
                errors.append(f"{where}: case kræver mindst 2 dele")
            labels = [d.get("del") for d in parts]
            if len(set(labels)) != len(labels) or not all(isinstance(x, str) and re.fullmatch(r"[a-h]", x)
                                                            for x in labels):
                errors.append(f"{where}: case-delene skal have unikke bogstaver a–h i 'del'")
            for d in parts:
                if d.get("type") not in PART_TYPES:
                    errors.append(f"{where}/{d.get('del')}: ugyldig deltype '{d.get('type')}'")
                elif not d.get("spoergsmaal"):
                    errors.append(f"{where}/{d.get('del')}: mangler 'spoergsmaal'")
                else:
                    errors += validate_answer_spec(d, f"{where}/{d.get('del')}")
        elif t.get("type") in PART_TYPES:
            errors += validate_answer_spec(t, where)
        if not str(t.get("status", "")).startswith(("V", "T")):
            errors.append(f"{where}: status skal begynde med V eller T")
        elif str(t.get("status")).startswith("T"):
            warnings.append(f"{where}: facit er ikke verificeret (T)")
    items = tasks + [d for t in tasks if t.get("type") == "case" for d in (t.get("dele") or [])]
    for t in tasks:
        if t.get("type") == "case":
            warnings += [f"{trade}/{t.get('id')}: {w}" for w in case_leaks(t)]
    choices = [t for t in items if t.get("type") == "valg" and t.get("facit") in (t.get("valgmuligheder") or {})]
    if len(choices) >= 10:
        longest = sum(1 for t in choices
                      if len(t["valgmuligheder"][t["facit"]]) == max(len(v) for v in t["valgmuligheder"].values()))
        if longest / len(choices) > 0.4:
            warnings.append(f"{trade}: facit er den længste valgmulighed i {longest} af {len(choices)} valgopgaver – "
                            "afbalancér længden, så længden ikke afslører svaret")
    for gid, g in goal_by_id.items():
        if g.get("rolle") != "i":
            continue
        missing = STORED_SETS - coverage[gid]
        if missing:
            errors.append(f"{trade}: læringsmål {gid} har ingen opgave i {', '.join(sorted(missing))}")
    return errors, warnings


# ---------- rendering ----------

def number_forms(value: float) -> set[str]:
    """Ways a number may be written in Danish or English text (e.g. 0,4 / 0.4; 1.500 / 1500)."""
    forms = set()
    for digits in (0, 1, 2, 3):
        s = f"{value:.{digits}f}"
        if float(s) == round(value, digits) and abs(float(s) - value) < 1e-9:
            forms |= {s, s.replace(".", ",")}
    whole = f"{value:,.0f}" if float(value).is_integer() else ""
    if whole and abs(value) >= 1000:
        forms |= {whole.replace(",", "."), whole.replace(",", " ")}
    return {f for f in forms if len(f.replace(",", "").replace(".", "")) >= 2}


def case_leaks(task: dict) -> list[str]:
    """Later parts are shown together with earlier ones; flag text that repeats an earlier part's key."""
    leaks = []
    parts = task.get("dele") or []
    for i, d in enumerate(parts):
        later = " ".join(x.get("spoergsmaal", "") + " " + " ".join((x.get("valgmuligheder") or {}).values())
                         for x in parts[i + 1:])
        if not later:
            continue
        if d.get("type") == "tal" and isinstance((d.get("facit") or {}).get("vaerdi"), (int, float)):
            for form in number_forms(float(d["facit"]["vaerdi"])):
                if re.search(rf"(?<![\d,.]){re.escape(form)}(?![\d])", later):
                    leaks.append(f"del {d.get('del')}: facit {form} står i en senere del")
                    break
        if d.get("type") == "valg" and d.get("facit") in (d.get("valgmuligheder") or {}):
            key = d["valgmuligheder"][d["facit"]].lower()
            words = re.findall(r"\w{4,}", key)
            for n in range(min(len(words), 4), 2, -1):
                hit = next((" ".join(words[j:j + n]) for j in range(len(words) - n + 1)
                            if " ".join(words[j:j + n]) in " ".join(re.findall(r"\w{4,}", later.lower()))), None)
                if hit:
                    leaks.append(f"del {d.get('del')}: facit ('{hit}') går igen i en senere del")
                    break
    return leaks


def validate_answer_spec(t: dict, where: str) -> list[str]:
    """Checks the key of one choice, number or free-text item (a task or a case part)."""
    errors = []
    if t["type"] == "valg":
        options = t.get("valgmuligheder") or {}
        if len(options) < 3:
            errors.append(f"{where}: valg kræver mindst 3 valgmuligheder")
        if t.get("facit") not in options:
            errors.append(f"{where}: facit '{t.get('facit')}' er ikke en valgmulighed")
    elif t["type"] == "tal":
        f = t.get("facit")
        if not isinstance(f, dict) or not isinstance(f.get("vaerdi"), (int, float)):
            errors.append(f"{where}: tal kræver facit {{vaerdi, enhed, tolerance_pct}}")
        elif not isinstance(f.get("tolerance_pct", 0), (int, float)):
            errors.append(f"{where}: tolerance_pct skal være et tal")
    elif t["type"] == "fri" and not t.get("kriterier"):
        errors.append(f"{where}: fri kræver 'kriterier'")
    return errors


def render(trade: str, with_key: bool, only_set: str = "") -> str:
    goals, tasks = load_trade(trade)
    if only_set:
        tasks = [t for t in tasks if t["saet"] == only_set]
    out = [f"# Eksamenssæt – {trade}", ""]
    out += ["## Kilder", "", "| ID | Kilde | Læst |", "|---|---|---|"]
    out += [f"| {s['id']} | [{s['titel']}]({s['url']}) | {s['laest']} |" for s in goals["kilder"]]
    out += ["", "## Dækningskort", "", "| Mål | Niveau | Læringsmål | Rolle | Opgaver |", "|---|---|---|---|---|"]
    by_goal: dict[str, list[str]] = {}
    for t in tasks:
        for gid in t["maal"]:
            by_goal.setdefault(gid, []).append(t["id"] + ("ᴴ" if t["saet"] in HIDDEN_SETS else ""))
    for g in goals["maal"]:
        role = "i" if g["rolle"] == "i" else f"uden – {g.get('begrundelse', '')}"
        out.append(f"| {g['id']} | {g.get('niveau', '')} | {g['tekst']} | {role} | {', '.join(by_goal.get(g['id'], [])) or '–'} |")
    out += ["", "ᴴ = holdout eller regression (kun til måling).", "", "## Opgaver", ""]
    for t in tasks:
        out.append(f"### {t['id']} · {t['type']} · {t['niveau']} · {t['saet']} · mål {', '.join(t['maal'])}")
        out += ["", t["spoergsmaal"], ""]
        for k, v in (t.get("valgmuligheder") or {}).items():
            out.append(f"- **{k}** {v}")
        for d in t.get("dele") or []:
            out += ["", f"**Del {d['del']}** ({d['type']}): {d['spoergsmaal']}"]
            out += [f"  - **{k}** {v}" for k, v in (d.get("valgmuligheder") or {}).items()]
            if with_key:
                out.append(f"  - Facit: {format_key(d)}")
                out += [f"  - Kriterium: {c}" for c in d.get("kriterier", [])]
                out += [f"  - Ikke bestået hvis: {c}" for c in d.get("fail_hvis", [])]
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
    if t["type"] == "case":
        return f"bestået ved mindst {round(100 * t.get('bestaa_andel', CASE_PASS_SHARE))} % af delene"
    return "efter kriterierne"


# ---------- grading ----------

# Claude Code returns these as an ordinary result text when the account limit is hit.
LIMIT_RE = re.compile(r"hit your (session|usage|weekly) limit|rate.?limit|overloaded", re.IGNORECASE)

ANSWER_RE = re.compile(r"^\W*ANSWER\W*:\s*(.+?)\s*$", re.IGNORECASE | re.MULTILINE)


def extract_answer(text: str, part: str = "") -> str | None:
    if part:
        pattern = re.compile(rf"^\W*ANSWER\s*{re.escape(part)}\W*:\s*(.+?)\s*$", re.IGNORECASE | re.MULTILINE)
        matches = pattern.findall(text or "")
    else:
        matches = [m for m in ANSWER_RE.findall(text or "") if not re.match(r"[a-h]\W*:", m, re.IGNORECASE)]
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


def grade_choice(task: dict, text: str, part: str = "") -> tuple[bool, str]:
    ans = extract_answer(text, part)
    if ans is None:
        return False, "ingen ANSWER-linje"
    letter = re.match(r"([A-Za-z])\b", ans)
    got = letter.group(1).upper() if letter else ans[:1].upper()
    return got == str(task["facit"]).upper(), f"svarede {got}, facit {task['facit']}"


def grade_number(task: dict, text: str, part: str = "") -> tuple[bool, str]:
    ans = extract_answer(text, part)
    if ans is None:
        return False, "ingen ANSWER-linje"
    value = parse_number(ans)
    if value is None:
        return False, f"intet tal i '{ans}'"
    f = task["facit"]
    target = float(f["vaerdi"])
    tol = abs(target) * float(f.get("tolerance_pct", 0)) / 100
    ok = abs(value - target) <= max(tol, 1e-9)
    return ok, f"svarede {value:g}, facit {target:g} {f.get('enhed', '')} ±{f.get('tolerance_pct', 0)} %"


def grade_verdict(text: str) -> tuple[bool, str]:
    m = re.findall(r"VERDICT:\s*(IKKE BESTÅET|BESTÅET)", text or "", re.IGNORECASE)
    if not m:
        return False, "bedømmeren gav ingen dom"
    return m[-1].upper() == "BESTÅET", m[-1].upper()


# ---------- running ----------

def run_claude(prompt: str, cwd: pathlib.Path, extra: list[str], timeout: int, stream: bool = False) -> dict:
    """One headless run. stream=True reads the event stream, so the tool calls can be counted (parse_stream)."""
    fmt = ["--output-format", "stream-json", "--verbose"] if stream else ["--output-format", "json"]
    cmd = ["claude", "-p", prompt, *fmt, "--setting-sources", "local",
           "--permission-mode", "dontAsk", "--no-session-persistence", *extra]
    try:
        r = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, timeout=timeout)
    except subprocess.TimeoutExpired:
        return {"is_error": True, "result": "", "fejl": f"timeout efter {timeout} s"}
    if stream:
        return parse_stream(r.stdout, r.stderr)
    try:
        return json.loads(r.stdout)
    except json.JSONDecodeError:
        return {"is_error": True, "result": "", "fejl": (r.stderr or r.stdout)[-500:]}


REJECTED_TEXT = 400  # characters kept of a denied or failed call's command and error text


def tool_target(name: str, inp: dict) -> str:
    """What a tool call acted on: the Bash command, the file path or the search pattern."""
    for key in ("command", "file_path", "pattern", "url", "query"):
        if inp.get(key):
            return str(inp[key])
    return ""


def result_text(block: dict) -> str:
    """The text of a tool_result block (a string or a list of text parts)."""
    content = block.get("content")
    if isinstance(content, list):
        return " ".join(str(c.get("text") or "") for c in content if isinstance(c, dict))
    return str(content or "")


def parse_stream(stdout: str, stderr: str = "") -> dict:
    """The final result event of a stream-json run, plus the tool calls per tool, the Bash commands and the
    tool calls that were denied or failed (tool, command or path, error text)."""
    result, calls, commands, rejected, uses = None, {}, [], [], {}
    for raw in stdout.splitlines():
        try:
            ev = json.loads(raw)
        except json.JSONDecodeError:
            continue
        if not isinstance(ev, dict):
            continue
        content = (ev.get("message") or {}).get("content") if ev.get("type") in ("assistant", "user") else None
        for block in content if isinstance(content, list) else []:
            if block.get("type") == "tool_use":
                name = block.get("name") or "?"
                inp = block.get("input") or {}
                calls[name] = calls.get(name, 0) + 1
                uses[block.get("id")] = (name, tool_target(name, inp))
                if name == "Bash":
                    commands.append(str(inp.get("command") or ""))
            elif block.get("type") == "tool_result" and block.get("is_error"):
                name, target = uses.get(block.get("tool_use_id"), ("?", ""))
                rejected.append({"vaerktoej": name, "kald": target[:REJECTED_TEXT],
                                 "fejl": result_text(block).strip()[:REJECTED_TEXT]})
        if ev.get("type") == "result":
            result = ev
    if result is None:
        return {"is_error": True, "result": "", "fejl": (stderr or stdout)[-500:]}
    return {**result, "vaerktoejskald": calls, "bash_kommandoer": commands, "afviste_kald": len(rejected),
            "afviste": rejected}


def count_calc_calls(commands: list[str], tools: list[str]) -> int:
    """Bash commands that run one of the trade's calculation tools (e.g. el.py)."""
    names = [pathlib.Path(t).name for t in tools]
    return sum(1 for c in commands if any(re.search(rf"(?<![\w.-]){re.escape(n)}\b", c) for n in names))


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
    """Copy of the plugin without dependencies, so it loads without byg-review (same as eval_trade.py).

    By default the agents' 'memory: user' is removed: the exam then measures the plugin alone, not the
    plugin plus the local agent memory (which may hold experience from the user's own cases)."""
    dst = tmp / plugin
    if rev:
        # The plugin as it was at a git revision, so knowledge-base versions can be compared on equal terms.
        export = tmp / f"rev-{rev.replace('/', '-')}"  # branch names like origin/main hold a slash
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


REGISTRY = ROOT / "plugins" / "byg-review" / "hooks" / "trade-registry.json"
EXAM_CALC_GUARD = ROOT / "scripts" / "hooks" / "exam_calc_guard.py"


def calc_tools(trade: str) -> list[str]:
    """The trade's calculation tools from the trade registry ('regnevaerktoej'), or [] if it has none."""
    entry = json.loads(REGISTRY.read_text(encoding="utf-8")).get("fag", {}).get(trade, {})
    tool = entry.get("regnevaerktoej") or []
    return [tool] if isinstance(tool, str) else list(tool)


def install_calc_guard(plugin_dir: pathlib.Path, trade: str, tools: list[str]) -> None:
    """Adds a PreToolUse hook to the plugin copy that allows Bash only for the trade's calculation tool.

    The plugin copy has no byg-review dependency, so byg-review's calc_guard is not loaded; this hook takes its place
    and fails closed. It is added to the copy only, never to the plugin in the repo."""
    hooks_file = plugin_dir / "hooks" / "hooks.json"
    hooks = json.loads(hooks_file.read_text(encoding="utf-8")) if hooks_file.exists() else {"hooks": {}}
    command = " ".join(["python3", f'"{EXAM_CALC_GUARD}"', trade, *tools])
    hooks.setdefault("hooks", {}).setdefault("PreToolUse", []).append(
        {"matcher": "Bash|Write", "hooks": [{"type": "command", "command": command, "timeout": 10}]})
    hooks_file.parent.mkdir(exist_ok=True)
    hooks_file.write_text(json.dumps(hooks, ensure_ascii=False, indent=2), encoding="utf-8")


def shuffled_options(task: dict, seed: str = "") -> tuple[dict, str]:
    """Options in a stable, id-seeded order relabelled A, B, C ... and the relabelled key.

    Authors tend to put the key in the same position; shuffling at run time removes that cue."""
    seed = seed or task["id"]
    items = sorted(task["valgmuligheder"].items(),
                   key=lambda kv: hashlib.sha256(f"{seed}:{kv[0]}".encode()).hexdigest())
    labels = [chr(ord("A") + i) for i in range(len(items))]
    key = next(lbl for lbl, (orig, _) in zip(labels, items) if orig == task["facit"])
    return {lbl: text for lbl, (_, text) in zip(labels, items)}, key


def build_prompt(task: dict) -> str:
    parts = [EXAM_PREAMBLE, "", task["spoergsmaal"]]
    if task["type"] == "valg":
        options, _ = shuffled_options(task)
        parts += [""] + [f"{k}) {v}" for k, v in options.items()]
    for d in task.get("dele") or []:
        parts += ["", f"Del {d['del']}) {d['spoergsmaal']}"]
        if d["type"] == "valg":
            options, _ = shuffled_options(d, f"{task['id']}/{d['del']}")
            parts += [f"   {k}) {v}" for k, v in options.items()]
    parts += ["", ANSWER_INSTRUCTIONS[task["type"]]]
    return "\n".join(parts)


def arm_args(arm: str, args, plugin_dir: pathlib.Path | None, agent: str) -> list[str]:
    tools = "Read,Glob,Grep,Skill" + (",WebSearch,WebFetch" if args.web else "")
    if arm == "plugin" and getattr(args, "calc_tool", False):
        tools += ",Bash,Write"
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
    res = run_claude(build_prompt(task), work, extra, args.timeout, stream=True)
    text = res.get("result", "") or ""
    usage = res.get("usage") or {}
    calls = res.get("vaerktoejskald") or {}
    entry = {"id": task["id"], "arm": arm, "type": task["type"], "saet": task["saet"], "niveau": task["niveau"],
             "maal": task["maal"], "svar": text, "pris_usd": res.get("total_cost_usd", 0.0),
             "ture": res.get("num_turns"), "sek": round((res.get("duration_ms") or 0) / 1000, 1),
             "tokens_ind": sum(usage.get(k) or 0 for k in
                               ("input_tokens", "cache_read_input_tokens", "cache_creation_input_tokens")),
             "tokens_ud": usage.get("output_tokens") or 0,
             "vaerktoejskald": calls,
             "regnekald": count_calc_calls(res.get("bash_kommandoer") or [], calc_tools(getattr(args, "fag", ""))),
             "afviste_kald": res.get("afviste_kald", 0),
             "afviste": res.get("afviste") or []}
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
    if task["type"] == "case":
        return grade_case(task, text, work, args)
    grader = GRADER_PROMPT.format(
        question=task["spoergsmaal"],
        criteria="\n".join(f"K{i}. {c}" for i, c in enumerate(task["kriterier"], 1)),
        fail_if="\n".join(f"- {c}" for c in task.get("fail_hvis", [])) or "- (ingen)",
        answer=text)
    g = run_claude(grader, work, ["--tools", "", "--max-turns", "1", "--model", args.grader], args.timeout)
    if g.get("is_error") or LIMIT_RE.search((g.get("result") or "")[:300]) and "VERDICT:" not in (g.get("result") or ""):
        return {"bestaaet": False, "fejl": True, "note": "kørselsfejl i bedømmelsen: "
                + (g.get("fejl") or (g.get("result") or "")[:120]), "pris_bedoemmelse": g.get("total_cost_usd") or 0}
    ok, note = grade_verdict(g.get("result", ""))
    return {"bestaaet": ok, "note": note, "bedoemmelse": g.get("result", ""),
            "pris_bedoemmelse": g.get("total_cost_usd") or 0}


def grade_case(task: dict, text: str, work: pathlib.Path, args) -> dict:
    """Each part is graded on its own; the case passes when the share of passed parts reaches bestaa_andel."""
    results: dict[str, bool] = {}
    notes = []
    for d in task["dele"]:
        if d["type"] == "valg":
            _, key = shuffled_options(d, f"{task['id']}/{d['del']}")
            results[d["del"]], note = grade_choice({**d, "facit": key}, text, d["del"])
            notes.append(f"{d['del']}: {note.split(' (')[0]}")
        elif d["type"] == "tal":
            results[d["del"]], note = grade_number(d, text, d["del"])
            notes.append(f"{d['del']}: {note}")
    free = [d for d in task["dele"] if d["type"] == "fri"]
    out = {"pris_bedoemmelse": 0}
    if free:
        parts = "\n\n".join(
            f"DEL {d['del']}: {d['spoergsmaal']}\nKRITERIER:\n"
            + "\n".join(f"{d['del']}K{i}. {c}" for i, c in enumerate(d["kriterier"], 1))
            + "\nIKKE BESTÅET, hvis:\n" + ("\n".join(f"- {c}" for c in d.get("fail_hvis", [])) or "- (ingen)")
            for d in free)
        g = run_claude(CASE_GRADER_PROMPT.format(question=task["spoergsmaal"], parts=parts, answer=text), work,
                       ["--tools", "", "--max-turns", "1", "--model", args.grader], args.timeout)
        verdict = g.get("result") or ""
        out["pris_bedoemmelse"] = g.get("total_cost_usd") or 0
        if g.get("is_error") or "VERDICT" not in verdict:
            return {**out, "bestaaet": False, "fejl": True, "note": "kørselsfejl i bedømmelsen: "
                    + (g.get("fejl") or verdict[:120])}
        out["bedoemmelse"] = verdict
        for d in free:
            m = re.findall(rf"VERDICT\s*{d['del']}\W*:\s*(IKKE BESTÅET|BESTÅET)", verdict, re.IGNORECASE)
            results[d["del"]] = bool(m) and m[-1].upper() == "BESTÅET"
            notes.append(f"{d['del']}: {m[-1].upper() if m else 'ingen dom'}")
    share = sum(results.values()) / len(task["dele"])
    passed = share >= task.get("bestaa_andel", CASE_PASS_SHARE)
    return {**out, "bestaaet": passed, "point": round(share, 3), "dele": results,
            "note": f"{sum(results.values())}/{len(task['dele'])} dele ({'; '.join(notes)})"}


def progress_line(r: dict, task: dict, prefix: str = "") -> str:
    """One progress line per answer; hidden lines (holdout, regression) hide ID and note, which can reveal the key."""
    status = "OK " if r["bestaaet"] else "NEJ"
    if task["saet"] in HIDDEN_SETS:
        return f"  {prefix}{status} {r['arm']:6} {task['saet']:10} (skjult)"
    return f"  {prefix}{status} {r['arm']:6} {r['id']:8} {r['note']}"


def cmd_regrade(args) -> int:
    """Grades stored answers again against the current tasks (new key, criteria or grader) without new answers."""
    src = pathlib.Path(args.fil)
    d = json.loads(src.read_text(encoding="utf-8"))
    _, tasks = load_trade(d["fag"])
    by_id = {t["id"]: t for t in tasks}
    jobs = [r for r in d["resultater"] if r["id"] in by_id and r["svar"]
            and (not args.only_free or by_id[r["id"]]["type"] == "fri")]
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
                print(progress_line(r, by_id[r["id"]], changed))
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
    if args.set != "udvikling" and not args.release:
        print("Holdout- og regressionssættet køres kun ved udgivelse eller en større ændring af videnbasen – "
              "tilføj --release.")
        return 1
    tools_for_run = calc_tools(args.fag) if args.calc_tool else []
    if args.calc_tool and not tools_for_run:
        print(f"--calc-tool: faget {args.fag} har intet regneværktøj i trade-registry.json")
        return 1
    goals, tasks = load_trade(args.fag)
    if args.set != "alle":
        tasks = [t for t in tasks if t["saet"] == args.set]
    if args.id:
        wanted = set(args.id.split(","))
        tasks = [t for t in tasks if t["id"] in wanted]
    if args.only_failed:
        failed = latest_failed_plugin(args.fag)
        tasks = [t for t in tasks if t["id"] in failed and t["saet"] == "udvikling"]
        print(f"Kun de {len(tasks)} udviklingsopgaver, plugin-armen ikke bestod sidst")
    arms = ["basis", "plugin"] if args.arm == "begge" else [args.arm]
    agent = f"{goals['plugin']}:{goals['agent']}"
    jobs = []
    if args.only_run_errors:
        # Re-run exactly the runs that errored in an earlier file, without printing their IDs.
        by_id = {t["id"]: t for t in tasks}
        prev = json.loads(pathlib.Path(args.only_run_errors).read_text(encoding="utf-8"))
        jobs = [(by_id[r["id"]], r["arm"]) for r in prev["resultater"]
                if r.get("fejl") and r["id"] in by_id and r["arm"] in arms]
        arms = sorted({arm for _, arm in jobs}) or arms
        print(f"Kun de {len(jobs)} kørsler, der fejlede i {pathlib.Path(args.only_run_errors).name}")
    for t in tasks if not args.only_run_errors else []:
        repeats = max(args.repeat, args.repeat_free if t["type"] == "fri" else 0)
        jobs += [(t, arm) for _ in range(repeats) for arm in arms]
    print(f"{args.fag}: {len(tasks)} opgaver × {len(arms)} arm(e) = {len(jobs)} kørsler")
    by_task = {t["id"]: t for t in tasks}
    lock = threading.Lock()
    results = []
    with tempfile.TemporaryDirectory(prefix="exam-") as tmpname:
        tmp = pathlib.Path(tmpname)
        plugin_dir = (prepare_plugin(goals["plugin"], tmp, args.with_memory, args.plugin_rev)
                      if "plugin" in arms else None)
        kb_bytes = knowledge_base_bytes(plugin_dir) if plugin_dir else 0
        if plugin_dir and args.calc_tool:
            install_calc_guard(plugin_dir, args.fag, tools_for_run)
        with concurrent.futures.ThreadPoolExecutor(max_workers=args.parallel) as pool:
            futures = [pool.submit(answer_task, t, arm, args, tmp, plugin_dir, agent) for t, arm in jobs]
            for fut in concurrent.futures.as_completed(futures):
                r = fut.result()
                with lock:
                    results.append(r)
                    print(progress_line(r, by_task[r["id"]]))
    stamp = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
    out_dir = EXAM_DIR / args.fag / "results"
    out_dir.mkdir(exist_ok=True)
    calc = "-regn" if args.calc_tool else ""
    out = out_dir / f"{stamp}-{args.arm}-{args.set}{calc}{'-' + args.plugin_rev.replace('/', '-') if args.plugin_rev else ''}.json"
    out.write_text(json.dumps({"fag": args.fag, "tid": stamp, "model": args.model or "agentens",
                               "web": args.web, "hukommelse": args.with_memory,
                               "regnevaerktoej": tools_for_run, "plugin_rev": args.plugin_rev or "arbejdstræ",
                               "videnbase_bytes": kb_bytes, "resultater": results}, ensure_ascii=False, indent=2),
                   encoding="utf-8")
    print(f"\nGemt: {out.relative_to(ROOT)}\n")
    extra, sources = ([], set())
    if arms == ["plugin"] and not args.no_base:
        extra, sources = latest_basis(args.fag, {t["id"] for t in tasks}, exclude=out)
    print(report([out], extra, sources))
    return 0


def result_files(trade: str, exclude: pathlib.Path | None = None) -> list[pathlib.Path]:
    """Valid result files, oldest first (files in folders marked 'ugyldig' and regraded copies are skipped)."""
    files = sorted((EXAM_DIR / trade / "results").glob("*.json"))
    return [f for f in files if f != exclude and "rebedoemt" not in f.name]


def valid_rows(f: pathlib.Path) -> list[dict]:
    rows = result_rows(json.loads(f.read_text(encoding="utf-8")))
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


def latest_answers(trade: str, ids: set[str], arm: str = "plugin",
                   files: list[pathlib.Path] | None = None) -> list[dict]:
    """The newest answer per task in one arm, for the development set only (from the given files, else all)."""
    latest: dict[str, dict] = {}
    for f in files if files is not None else result_files(trade):
        for r in valid_rows(f):
            if r["arm"] == arm and r["saet"] == "udvikling" and (not ids or r["id"] in ids):
                latest[r["id"]] = r
    return [latest[t] for t in sorted(latest)]


def cmd_answers(args) -> int:
    _, tasks = load_trade(args.fag)
    hidden = {t["id"] for t in tasks if t["saet"] in HIDDEN_SETS}
    ids = {t for t in args.id.split(",") if t}
    if ids & hidden:
        print("Holdout-svar vises ikke (heller ikke regression) – holdout må aldrig være grundlag for ændringer.")
        return 1
    files = [pathlib.Path(args.file)] if args.file else None
    if not ids and not files:
        ids = latest_failed_plugin(args.fag) - hidden
    rows = latest_answers(args.fag, ids, args.arm, files)
    for r in rows:
        print(f"## {r['id']} · {r['arm']} · {'bestået' if r['bestaaet'] else 'ikke bestået'} · {r.get('note', '')}\n")
        if "vaerktoejskald" in r:
            print(f"Værktøjskald: {format_calls(r)}\n")
        for a in r.get("afviste") or []:
            print(f"- afvist eller fejlet {a.get('vaerktoej')}: `{a.get('kald')}` → {a.get('fejl')}")
        if r.get("afviste"):
            print()
        print(r.get("svar", "").strip(), "\n")
        if r.get("bedoemmelse"):
            print("**Bedømmelse:**\n" + r["bedoemmelse"].strip() + "\n")
    if not rows:
        print("Ingen svar fundet.")
    return 0


def format_calls(r: dict) -> str:
    calls = r.get("vaerktoejskald") or {}
    text = ", ".join(f"{name} {n}" for name, n in sorted(calls.items())) or "ingen"
    return text + f" · regnekald {r.get('regnekald', 0)} · afvist eller fejlet {r.get('afviste_kald', 0)}"


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
        rows += result_rows(d)
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
    out.append("| Output-tokens pr. opgave | " + " | ".join(per_arm(lambda s: mean(s, "tokens_ud", 0))) + " |")
    if any("vaerktoejskald" in r for r in rows):
        # Only rows written since tool calls were counted carry the fields.
        def counted(sel):
            return [r for r in sel if "vaerktoejskald" in r]
        out.append("| Værktøjskald pr. opgave | " + " | ".join(per_arm(lambda s: (
            f"{sum(sum(r['vaerktoejskald'].values()) for r in counted(s)) / len(counted(s)):.1f}"
            if counted(s) else "–"))) + " |")
        out.append("| Regnekald pr. opgave | " + " | ".join(per_arm(
            lambda s: mean(counted(s), "regnekald") if counted(s) else "–")) + " |")
        out.append("| Kørsler med regnekald | " + " | ".join(per_arm(lambda s: (
            f"{sum(1 for r in counted(s) if r.get('regnekald'))}/{len(counted(s))}" if counted(s) else "–"))) + " |")
    if kb_sizes:
        out += ["", "Videnbasens størrelse (references + agentprompt): "
                + ", ".join(f"{rev}: {size / 1024:.1f} KB" for rev, size in kb_sizes.items())]
    if reused_basis:
        out += ["", f"Basis er genbrugt fra: {', '.join(sorted(reused_basis))}"]
    if errors:
        dev_errors = [r for r in errors if r["saet"] not in HIDDEN_SETS]
        out += ["", f"**{len(errors)} kørselsfejl er ikke talt med** (fx ramt kontogrænse)."]
        if dev_errors:
            out[-1] += " Kør udviklingsopgaverne igen med `run --id " + \
                ",".join(sorted({r['id'] for r in dev_errors})) + "`:"
        out += [""] + [f"- {r['id']} ({r['arm']}): {r['note']}" for r in dev_errors]
        if len(dev_errors) < len(errors):
            out += [f"- {len(errors) - len(dev_errors)} skjulte kørsel(er) med fejl (holdout eller regression) – "
                    "ID skjult. "
                    "Kør dem igen med `run FAG --only-run-errors FIL --set all --release`."]

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
        out += ["", "## Huller (plugin ikke bestået) – kandidater til videnbasen, kun fra udviklingssættet", ""]
        out += [f"- {t} (mål {', '.join(goals_of[t])})" for t in gaps] or ["- ingen"]
        for s in sorted(HIDDEN_SETS):
            held = [t for t in failed_plugin if set_of[t] == s]
            if held:
                out += ["", f"{len(held)} {s}-opgaver er ikke bestået. De vises ikke, fordi skjulte opgaver aldrig "
                        "må være grundlag for videnbasen."]
    if {"basis", "plugin"} <= set(arms):
        def listed(ids: list[str]) -> list[str]:
            shown = [f"- {t}" for t in ids if set_of[t] == "udvikling"]
            hidden = {s: sum(1 for t in ids if set_of[t] == s) for s in sorted(HIDDEN_SETS)}
            return (shown or (["- ingen"] if not any(hidden.values()) else [])) \
                + [f"- og {n} i {s}" for s, n in hidden.items() if n]
        out += ["", "## Regressioner (basis bestået, plugin ikke) – videnbasen vildleder", ""]
        out += listed(regressions)
        out += ["", "## Gevinst (plugin bestået, basis ikke)", ""]
        out += listed(gains)
    return "\n".join(out)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("check")
    p.add_argument("fag", nargs="*")
    p = sub.add_parser("show")
    p.add_argument("fag")
    p.add_argument("--answer-key", action="store_true")
    p.add_argument("--set", choices=["development", "holdout", "regression"], default="",
                   help="kun ét sæt (CI-agenten bruger development)")
    p = sub.add_parser("run")
    p.add_argument("fag")
    p.add_argument("--arm", choices=["base", "plugin", "both"], default="plugin")
    p.add_argument("--set", choices=["development", "holdout", "regression", "all"], default="development")
    p.add_argument("--id", default="")
    p.add_argument("--parallel", type=int, default=4)
    p.add_argument("--model", default="")
    p.add_argument("--grader", default="sonnet")
    p.add_argument("--repeat", type=int, default=1)
    p.add_argument("--max-turns", type=int, default=12)
    p.add_argument("--timeout", type=int, default=600)
    p.add_argument("--web", action="store_true")
    p.add_argument("--repeat-free", type=int, default=0, help="ekstra gentagelser kun af fri-opgaverne (støj)")
    p.add_argument("--only-failed", action="store_true", help="kun udviklingsopgaver, plugin-armen ikke bestod sidst")
    p.add_argument("--only-run-errors", metavar="FILE",
                   help="kør kun de kørsler igen, der fejlede (fx kontogrænse) i FILE")
    p.add_argument("--release", action="store_true", help="kræves for at køre holdout- og regressionssættet")
    p.add_argument("--no-base", action="store_true", help="rapportér plugin-armen uden genbrugt basis")
    p.add_argument("--plugin-rev", default="", help="kør pluginet, som det var i en git-revision (fx før en ændring)")
    p.add_argument("--with-memory", action="store_true",
                   help="indlæs fagagentens lokale hukommelse (~/.claude/agent-memory) i plugin-armen")
    p.add_argument("--calc-tool", action="store_true",
                   help="plugin-armen får Bash låst til fagets regneværktøj (måleopsætning for regneværktøjer)")
    p = sub.add_parser("answers")
    p.add_argument("fag")
    p.add_argument("--id", default="", help="standard: udviklingsopgaver, plugin-armen ikke bestod sidst")
    p.add_argument("--arm", choices=["base", "plugin"], default="plugin")
    p.add_argument("--file", default="", help="svarene i én resultatfil (fx én arm) i stedet for de nyeste")
    p = sub.add_parser("report")
    p.add_argument("filer", nargs="+")
    p = sub.add_parser("regrade")
    p.add_argument("fil")
    p.add_argument("--only-free", action="store_true")
    p.add_argument("--parallel", type=int, default=4)
    p.add_argument("--grader", default="sonnet")
    p.add_argument("--timeout", type=int, default=600)
    args = ap.parse_args()
    # English CLI choices → the Danish values stored in exam data and result files.
    if getattr(args, "set", None):
        args.set = CLI_VALUES.get(args.set, args.set)
    if getattr(args, "arm", None):
        args.arm = CLI_VALUES.get(args.arm, args.arm)

    if args.cmd == "check":
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
            per_set = ", ".join(f"{s} {n}" for s in sorted(SETS)
                                if (n := sum(1 for t in tasks if t.get("saet") == s)))
            print(f"{trade}: {len(goals.get('maal', []))} læringsmål ({in_role} i rollen) · {len(tasks)} opgaver "
                  f"({per_set}) · {len(errors)} fejl · {len(warnings)} advarsler")
            failed |= bool(errors)
        return 1 if failed else 0
    if args.cmd == "show":
        print(render(args.fag, args.answer_key, args.set))
        return 0
    if args.cmd == "run":
        return cmd_run(args)
    if args.cmd == "answers":
        return cmd_answers(args)
    if args.cmd == "regrade":
        return cmd_regrade(args)
    print(report([pathlib.Path(f) for f in args.filer]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
