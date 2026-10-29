#!/usr/bin/env python3
"""byg-kontrol: håndhæver det uafhængige kvalitetskontrol-loop (plugin-hook til Claude Code/Cowork).

Fra hooks/hooks.json:  python3 review_gate.py pretool | protect | subagentstop | prompt | stop | precompact | after_compact
                       (hook-input på stdin)
Manuelt:               python3 review_gate.py status
                       python3 review_gate.py reset <leverance-id>
                       python3 review_gate.py merge <sagsmappe>/forslag/<fag>-<nr>__<mål>.md [--dry-run] [--force]
                       (uden CLAUDE_PLUGIN_DATA findes pluginets datamappe under ~/.claude/plugins/data/)

Regler
- Kald af byg-fagagenter og kontrolagenter skal have linjen "LEVERANCE: <id>" i prompten.
- Et fagkald sætter leverancen til "fagkald_igang". Når fagagenten afleverer (SubagentStop), bliver den
  "afventer_kontrol". Et nyt fagkald, mens status er "fagkald_igang" (fx efter et afbrudt kald), er et
  genforsøg og tæller ikke som nyt forsøg. En ny fagversion kræver først en kontroldom.
- Godkendte leverancer beskyttes: kontrolkaldets linje "Leverance: <sti>" huskes. Write/Edit på den sti
  afvises for subagenter og giver en advarsel i hovedtråden (brug nyt leverance-ID).
- Domme findes også i hand-back-rapporter (tool_use-input i agentens transkript).
- Kontrolagentens slutbesked skal indeholde en gyldig JSON-dom (faelles/kontrolprotokol.md, afsnit 5).
  "afklar_med_bruger" (valgfri) er en liste af spørgsmål til brugeren; den blokerer ikke og tælles i dommen.
- Kontrolkaldets "Leverance: <sti>" skal findes på disken (relativ sti regnes fra cwd), ellers afvises kaldet.
  Ugyldig dom → kontrolagenten sendes tilbage én gang for at rette den.
- Højst "maks_forsoeg" (2) forsøg pr. runde. Sidste afviste dom → "stoppet": eskalering til brugeren
  (brug med åbne fund som antagelser, ny runde eller nyt leverance-ID). Stop blokerer én gang for eskaleringen.
- Ny runde (højst "maks_runder", 2) kræver brugerens egen besked "Ny runde <leverance-id>" (UserPromptSubmit)
  og derefter RCA-filen for runden med en 5 Why-kæde (mindst fem nummererede "Hvorfor"-linjer og en
  "Grundårsag") og linjen "Forbedring implementeret: ja". Efter sidste runde: kun under et nyt leverance-ID.
- Stop-hooken forhindrer (én gang pr. stop) afslutning, mens sessionens leverancer mangler kontrol,
  er afvist eller ikke er eskaleret til brugeren.
- Kontrolniveau fuld: et kontrolkald med "KONTROLNIVEAU: fuld" kræver model "opus" i Agent-kaldet
  (kontrolagenterne kører ellers på sonnet).
- Stikprøvekontrol: et fagkald med "KONTROLNIVEAU: stikprøve" (kun spørgsmål uden FASE og kun fag uden for
  "stikproeve.aldrig_fag") udtages deterministisk ud fra leverance-ID'et med andelen "stikproeve.andel". Udtaget →
  normal kontrol. Ikke udtaget → status "ikke_udtaget" ved aflevering: Stop blokerer ikke, og et kontrolkald
  afvises med besked om at markere svaret som ikke kvalitetskontrolleret.
- Værktøjskontrol (fagregister "vaerktoejskontrol", i dag bim): et fagkald med "KONTROLNIVEAU: værktøj" godkendes
  uden kontrolagent, når hjælpeagentens sammenligning ender med "resultat": "ok" og "tjek": {"fejl": 0,
  "sporbarhed": 0} (bim.py check). Ellers kaldes kontrolagenten som normalt. Godkendelsen gemmes som en dom
  med "godkendt_af": "vaerktoej".
- Workflows (PreToolUse Workflow): i byg-sager afvises Workflow-værktøjet, medmindre brugerens seneste besked
  indeholder ordet "workflow".
- Kontrolkald med et ukendt ID behandles som gennemgang af eksternt materiale (uden loop).
- Hjælpeagenter (fagregister: "hjaelpere", fx bim-sammenligner): et hjælpekald kræver LEVERANCE og en afleveret
  fagversion ("afventer_kontrol" eller "sammenlignet") og sætter "under_sammenligning"; ved aflevering bliver den
  "sammenlignet". Et fagkald efter en sammenligning er en rettelse: det bruger ikke af kontrolforsøgene. Højst
  "maks_sammenligninger" (standard 3) sammenligninger pr. leverance. Kontrollen kan kaldes efter sammenligningen.
- Opslagsagenter (fagregister: "opslag", fx bim-opslag) er hverken fag- eller hjælpeagenter: de svarer på rene
  spørgsmål til en eksisterende model, kaldes uden LEVERANCE og gates ikke. De kan ikke skrive (validate.py).
- Fase-gate: projektkontrol af en planleverance i fase 3 eller senere ("FASE: 3" i prompten) kræver
  "DESIGNGRUNDLAG: <id>, <id> …" med fagleverancer, der alle er godkendt (design freeze).
- Manuel gate G2 (løsningsgodkendelse): kun brugeren kan åbne den ved selv at skrive
  "Godkend G2 <sag-id>" (UserPromptSubmit). Godkendelsen gemmes med de fagleverancer, der er godkendt i
  sagen på det tidspunkt. Fase 3 (projektkontrol med FASE ≥ 3 og fagkald med FASE ≥ 3) kræver godkendelsen,
  og DESIGNGRUNDLAG skal være en delmængde af det godkendte design.
- Fund-fastlåsning: i forsøg 2 og 3 skal et nyt kritisk eller væsentligt fund have
  "nyt_grundlag": "regression" | "aendret_tekst" | "kritisk_sikkerhed" (kun klasse kritisk).
- Kontekstbudget (UserPromptSubmit): har sessionen byg-leverancer, og er hovedtrådens kontekst over
  KONTEKST_GRAENSE tokens, får brugeren og projektlederen én påmindelse pr. KONTEKST_TRIN om at afslutte
  opgaven og fortsætte i en ny session med /byg:status <sag-id>. Hvert svar læser hele tråden igen.
- Sikker compact: PreCompact giver resuméet instruktioner om, hvad der skal bevares ordret (leverance-ID'er,
  blokerende fund, ulogførte brugerbeslutninger, næste skridt). SessionStart med source "compact" genindlæser
  sagens status.md (højst STATUS_MAKS_TEGN tegn) og sessionens åbne leverancer fra tilstanden, så tråden
  fortsætter som efter /byg:status. Sagen findes via sessionens leverancer, ellers sagsmappen i cwd.
- Én skriver pr. fil (fagregister: "skriv_alle", "skriv", "skriv_ny"): i byg-sager/ må en fagagent kun skrive
  sine egne filer – fagnotater/<fag>*.md, bilag/<fag>/, forslag/<fag>-<nr>__<mål>.md og fagets egne mapper (bim/forslag,
  fem/ …). Alt andet i sagsmappen og ejendomskortet ejes af projektlederen; Write/Edit afvises for subagenter.
- Forslag (case_merge.py): fagagentens rækker til graenseflader/risici/kontrolplan/ejendomskort. Basis (målfilerne) gemmes, når
  fagkaldet starter; forslaget skal hedde efter en igangværende leverance og flettes ind, når leverancen godkendes. Konflikter vises af Stop-hooken.
- Revisionsstyring (case_git.py): byg-sager/ er et lokalt git-repo. Hooken committer fagaflevering (fagets stier),
  dom og fletning (kvalitet/, forslag/ og målfiler) og hovedtrådens ændringer ved Stop. Ved en ny fagversion efter en
  dom skrives diffen siden den kontrollerede version til kvalitet/<leverance>__aendringer.diff (forsøg 2–3 og rettelser).
Fail-safe: uventede fejl blokerer aldrig – de logges i <data>/kontrol/log.jsonl.
"""
import hashlib
import json
import os
import pathlib
import re
import sys
import time
import traceback
from fnmatch import fnmatch

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import case_merge  # noqa: E402
import case_git  # noqa: E402

REG = json.loads((HERE / "fagregister.json").read_text(encoding="utf-8"))
# Temporary question folders live outside byg-sager/ (permanent data): ~/byg-tmp/<date>-<topic>/
TMP_NAME = "byg-tmp"


def tmp_root() -> pathlib.Path:
    return pathlib.Path(os.environ.get("BYG_TMP") or pathlib.Path.home() / TMP_NAME)
MAX_ATTEMPTS = int(REG.get("maks_forsoeg", 3))
MAX_ROUNDS = int(REG.get("maks_runder", 3))
MAX_COMPARISONS = int(REG.get("maks_sammenligninger", 3))
SAMPLE = REG.get("stikproeve") or {}
SAMPLE_SHARE = float(SAMPLE.get("andel", 1.0))
SAMPLE_NEVER = set(SAMPLE.get("aldrig_fag") or [])
RESULT_RE = re.compile(r'"resultat"\s*:\s*"(ok|ret)"', re.IGNORECASE)
IMPROVEMENT_RE = re.compile(r"forbedring\s+implementeret\W{0,6}ja\b", re.IGNORECASE)
WHY_RE = re.compile(r"^\s*\d+\.\s.*\bhvorfor\b", re.IGNORECASE | re.MULTILINE)
ROOT_CAUSE_RE = re.compile(r"grundårsag", re.IGNORECASE)
DELIVERABLE_RE = re.compile(r"LEVERANCE\s*:\s*([^\s`'\"<>]+)", re.IGNORECASE)
PATH_RE = re.compile(r"^\s*Leverance\s*:\s*(\S+\.md)\b", re.IGNORECASE | re.MULTILINE)
IN_PROGRESS_MAX_SEC = 90 * 60
PHASE_RE = re.compile(r"^\s*FASE\s*:\s*(\d)", re.IGNORECASE | re.MULTILINE)
DESIGN_RE = re.compile(r"^\s*DESIGNGRUNDLAG\s*:\s*(.+)$", re.IGNORECASE | re.MULTILINE)
NEW_ROUND_RE = re.compile(r"\bny\s+runde\s+([^\s`'\"<>]+)", re.IGNORECASE)
WORKFLOW_RE = re.compile(r"\bworkflow", re.IGNORECASE)
LEVEL_FULL_RE = re.compile(r"KONTROLNIVEAU\s*:\s*fuld", re.IGNORECASE)
LEVEL_TOOL_RE = re.compile(r"KONTROLNIVEAU\s*:\s*v(?:æ|ae)rkt(?:ø|oe)j", re.IGNORECASE)
CHECK_RE = re.compile(r'"tjek"\s*:\s*(\{[^{}]*\})')
LEVEL_SAMPLE_RE = re.compile(r"KONTROLNIVEAU\s*:\s*stikpr(?:ø|oe)ve", re.IGNORECASE)
APPROVE_G2_RE = re.compile(r"\bgodkend(?:er|t)?\s+G2\s+([A-Za-z0-9ÆØÅæøå._-]+)", re.IGNORECASE)
NEW_BASIS = {"regression", "aendret_tekst", "kritisk_sikkerhed"}
BLOCKING = {"kritisk", "væsentlig"}
STATUSES = {"nyt", "aabent", "åbent", "lukket", "bestridt"}
CONTEXT_LIMIT = 200_000
CONTEXT_STEP = 100_000
STATUS_MAX_CHARS = 12_000


# ---------- helpers ----------
def now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%S")


def data_dir() -> pathlib.Path:
    root = os.environ.get("CLAUDE_PLUGIN_DATA")
    if not root:
        # Manual commands (status/reset) run without CLAUDE_PLUGIN_DATA: use the plugin's
        # own data folder if it exists (newest state wins) before the default folder is created.
        found = sorted((pathlib.Path.home() / ".claude" / "plugins" / "data").glob("*/kontrol/tilstand.json"),
                        key=lambda f: f.stat().st_mtime, reverse=True)
        if found:
            return found[0].parent
        root = str(pathlib.Path.home() / ".claude" / "byg-kontrol-data")
    p = pathlib.Path(root) / "kontrol"
    p.mkdir(parents=True, exist_ok=True)
    return p


class Lock:
    def __init__(self, d: pathlib.Path):
        self.path = d / ".laas"
        self.fh = None

    def __enter__(self):
        self.fh = open(self.path, "a+")
        try:
            import fcntl
            fcntl.flock(self.fh, fcntl.LOCK_EX)
        except Exception:
            pass
        return self

    def __exit__(self, *_):
        try:
            import fcntl
            fcntl.flock(self.fh, fcntl.LOCK_UN)
        except Exception:
            pass
        self.fh.close()


def load(d: pathlib.Path) -> dict:
    f = d / "tilstand.json"
    if f.exists():
        try:
            return json.loads(f.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {"version": 1, "leverancer": {}}


def save(d: pathlib.Path, s: dict) -> None:
    f = d / "tilstand.json"
    tmp = f.with_suffix(".tmp")
    tmp.write_text(json.dumps(s, ensure_ascii=False, indent=2), encoding="utf-8")
    os.replace(tmp, f)


def log(d: pathlib.Path, **kw) -> None:
    kw["tid"] = now()
    with open(d / "log.jsonl", "a", encoding="utf-8") as fh:
        fh.write(json.dumps(kw, ensure_ascii=False) + "\n")


def safe(deliv: str) -> str:
    return re.sub(r"[^A-Za-z0-9ÆØÅæøå._-]+", "__", deliv)


def split_name(name: str) -> tuple[str, str]:
    name = (name or "").strip()
    if ":" in name:
        pre, base = name.rsplit(":", 1)
        return pre, base
    return "", name


def classify(base: str) -> tuple:
    for trade, v in REG["fag"].items():
        if base == v["agent"]:
            return "fag", trade
        if base == v["kontrol"]:
            return "kontrol", trade
        if base in v.get("hjaelpere", []):
            return "hjaelper", trade
    if base == REG["projekt_kontrol"]:
        return "kontrol", "projekt"
    return None, None


def review_name(trade: str, trade_prefix: str) -> str:
    base = REG["projekt_kontrol"] if trade == "projekt" else REG["fag"][trade]["kontrol"]
    if not trade_prefix:
        return base
    pre = trade_prefix if trade_prefix == REG["samlet_plugin"] else REG["kontrol_plugin"]
    return f"{pre}:{base}"


def deny_call(reason: str) -> None:
    print(json.dumps({"hookSpecificOutput": {"hookEventName": "PreToolUse",
                                             "permissionDecision": "deny",
                                             "permissionDecisionReason": reason}}, ensure_ascii=False))


def block(reason: str) -> None:
    print(json.dumps({"decision": "block", "reason": reason}, ensure_ascii=False))


def sampled(deliv: str) -> bool:
    """Deterministic sample: the same deliverable ID always gives the same outcome (reproducible and verifiable)."""
    return int(hashlib.sha256(deliv.encode("utf-8")).hexdigest(), 16) % 1000 < round(SAMPLE_SHARE * 1000)


def round_no(e: dict) -> int:
    return int(e.get("runde") or 1)


def rca_name(deliv: str, r: int) -> str:
    return f"RCA-{safe(deliv)}.md" if r <= 1 else f"RCA-{safe(deliv)}__runde-{r}.md"


def case_of(deliv: str) -> str:
    return deliv.split("/", 1)[0]


def write_patterns(trade: str) -> list:
    v = REG["fag"].get(trade, {})
    return [m.format(fag=trade) for m in REG.get("skriv_alle", [])] + list(v.get("skriv", []))


def git_patterns(case_id: str, trade: str) -> list:
    """The trade's files in the case as git globs (fnmatch's '*' also covers subfolders, git's '**' does): the write paths
    plus what the trade changes with its tool via Bash ("skriv_ny", "git_ekstra", e.g. the BIM main model)."""
    v = REG["fag"].get(trade, {})
    all_patterns = write_patterns(trade) + list(v.get("skriv_ny", [])) + list(v.get("git_ekstra", []))
    return [f"{case_id}/" + (m[:-1] + "**" if m.endswith("/*") else m) for m in all_patterns]


def find_case_dir(inp: dict, e: dict, deliv: str):
    case_dir = case_dir_path(inp, e or {})
    if case_dir:
        return case_dir
    for p in (pathlib.Path(str(inp.get("cwd") or os.getcwd())) / "byg-sager" / case_of(deliv), tmp_root() / case_of(deliv)):
        if p.is_dir():
            return p
    return None


def git_commit(d: pathlib.Path, case_dir, message: str, paths=None):
    """Commit in the case's byg-sager repo; paths are relative to byg-sager/. Errors are logged and never block."""
    try:
        root = case_git.root_for(case_dir) if case_dir else None
        return case_git.commit(root, message, paths) if root else None
    except Exception:
        log(d, haendelse="git_fejl", fejl=traceback.format_exc()[-400:])
        return None


def g2_missing(s: dict, case_id: str, ids: list) -> str | None:
    g2 = (s.get("gates") or {}).get(case_id, {}).get("G2")
    if not g2:
        return (f"Manuel gate G2 mangler for sagen {case_id}: detailplanlægning (fase 3) må først starte, når brugeren har "
                f"godkendt løsningen. Præsentér løsningen (loesningspraesentation.md, se projektlederens faser-og-gates.md), "
                f"og bed brugeren selv skrive: 'Godkend G2 {case_id}'. Claude kan ikke give denne godkendelse.")
    unknown = [i for i in ids if i not in (g2.get("design") or [])]
    if unknown:
        return (f"Designgrundlaget er ændret efter brugerens G2-godkendelse ({g2.get('tid')}): {', '.join(unknown)} "
                f"indgik ikke i det godkendte design. Præsentér ændringen, og bed brugeren skrive 'Godkend G2 {case_id}' igen.")
    return None


def next_step(deliv: str, e: dict) -> str:
    st = e.get("status")
    r = round_no(e)
    if st == "afvist":
        who = e.get("fag_agent") or "projektlederen (egen leverance)"
        return (f"Afvist (runde {r}/{MAX_ROUNDS}, forsøg {e.get('forsoeg')}/{MAX_ATTEMPTS}): send de blokerende fund (ikke de mindre) "
                f"retur til {who} med 'LEVERANCE: {deliv}', og kald derefter {e.get('kontrol_agent')} igen i forgrunden.")
    if st in ("stoppet", "rca_udfoert"):
        if r < MAX_ROUNDS and e.get("ny_runde_ok") == r:
            return (f"Brugeren har bedt om runde {r + 1}: skriv root cause-analysen til "
                    f"<sagsmappe>/kvalitet/{rca_name(deliv, r)} – hvorfor kunne fagagenten ikke levere korrekt i første forsøg? "
                    f"Implementér læringen som forbedring af fagagenten (agentens hukommelse og repoet), skriv linjen "
                    f"'Forbedring implementeret: ja' i RCA'en, og start runde {r + 1} med et nyt fagkald under samme "
                    f"leverance-ID (højst {MAX_ATTEMPTS} nye forsøg) – se skill 'kvalitetskontrol'.")
        options = (f"(b) en ny runde – brugeren skriver selv 'Ny runde {deliv}' – eller (c) " if r < MAX_ROUNDS
                else "eller (c) ")
        return (f"Stoppet efter {MAX_ATTEMPTS} afviste forsøg i runde {r}/{MAX_ROUNDS}: stop og eskalér til brugeren. Vis de "
                f"åbne blokerende fund kort, og spørg, om leverancen skal (a) bruges med fundene som åbne antagelser eller "
                f"hold points, " + options + "omformuleres som en ny, mindre opgave under et nyt leverance-ID. Start ingen "
                "ny runde, og skriv ingen RCA, før brugeren har valgt.")
    if st == "godkendt":
        unchecked = ((e.get("domme") or [{}])[-1]).get("ikke_kontrolleret") or []
        scope = (f" Godkendelsen dækker ikke: {'; '.join(unchecked)}. Nævn det, når leverancen bruges." if unchecked else "")
        return f"Godkendt: ændringer kræver et nyt leverance-ID (fx '{deliv}-r2').{scope}"
    if st == "ikke_udtaget":
        return (f"Ikke udtaget til stikprøvekontrol: {deliv} er afleveret uden kontrol. Svar brugeren, og skriv tydeligt "
                "'Ikke kvalitetskontrolleret (stikprøve, ikke udtaget)'. Skal svaret alligevel kontrolleres, eller "
                f"ændres det, så brug et nyt leverance-ID (fx '{deliv}-r2') med KONTROLNIVEAU: let.")
    return ""


# ---------- PreToolUse ----------
def pretool(inp: dict, d: pathlib.Path) -> None:
    ti = inp.get("tool_input") or {}
    st = str(ti.get("subagent_type") or "")
    pre, base = split_name(st)
    kind, trade = classify(base)
    if not kind:
        return
    m = DELIVERABLE_RE.search(str(ti.get("prompt") or ""))
    if not m and kind == "hjaelper":
        return deny_call(f"byg-kvalitetskontrol: {base} kræver 'LEVERANCE: <id>' for den fagleverance, der skal "
                          "sammenlignes – se skill 'tegningsimport'.")
    if not m:
        if kind == "fag":
            deny_call(f"byg-kvalitetskontrol: fagkald uden leverance-ID. Tilføj linjen 'LEVERANCE: <sag-id>/{trade}/<nr>' "
                       f"i prompten (fx 'LEVERANCE: {time.strftime('%Y-%m-%d')}-<emne>/{trade}/01'). Leverancen skal bagefter "
                       f"kontrolleres af {review_name(trade, pre)} – se skill 'kvalitetskontrol'.")
        else:
            deny_call("byg-kvalitetskontrol: kontrolkald uden leverance-ID. Brug samme 'LEVERANCE: <id>' som fagleverancen "
                       "(eller 'LEVERANCE: ekstern/<emne>' ved gennemgang af eksternt materiale).")
        return
    deliv = m.group(1).rstrip(".,;:)")
    sid = str(inp.get("session_id") or "")
    with Lock(d):
        s = load(d)
        delivs = s["leverancer"]
        e = delivs.get(deliv)
        if kind == "hjaelper":
            return helper_call(d, s, e, deliv, trade, st, sid)
        if kind == "fag":
            fm = PHASE_RE.search(str(ti.get("prompt") or ""))
            if fm and int(fm.group(1)) >= 3:
                reason = g2_missing(s, case_of(deliv), [])
                if reason:
                    return deny_call(reason)
            if e:
                if e.get("fag") != trade:
                    return deny_call(f"Leverance-ID {deliv} tilhører faget '{e.get('fag')}'. Brug et nyt ID til {trade}.")
                status = e.get("status")
                if status == "fagkald_igang":
                    e.update(session_id=sid, opdateret=now())
                    save(d, s)
                    log(d, haendelse="fagkald_gentaget", leverance=deliv, forsoeg=e.get("forsoeg"), agent=st)
                    return
                if status == "under_sammenligning":
                    return deny_call(f"Leverance {deliv} er ved at blive sammenlignet. Vent på sammenligningens resultat, "
                                      f"og send afvigelserne retur med 'LEVERANCE: {deliv}'.")
                if status in ("afventer_kontrol", "under_kontrol"):
                    helpers = REG["fag"].get(trade, {}).get("hjaelpere")
                    extra = (f" (Eller sammenlign først med {', '.join(helpers)} – se skill 'tegningsimport'.)"
                              if helpers and status == "afventer_kontrol" else "")
                    return deny_call(f"Leverance {deliv} (forsøg {e.get('forsoeg')}/{MAX_ATTEMPTS}) er ikke kontrolleret endnu. "
                                      f"Kald {e.get('kontrol_agent')} med 'LEVERANCE: {deliv}' og stien til fagnotatet først."
                                      + extra)
                if status == "sammenlignet":
                    e["rettelser"] = int(e.get("rettelser", 0)) + 1
                    e.update(status="fagkald_igang", session_id=sid, opdateret=now())
                    save(d, s)
                    log(d, haendelse="rettelse_efter_sammenligning", leverance=deliv, rettelse=e["rettelser"], agent=st)
                    return
                if status in ("godkendt", "ikke_udtaget"):
                    return deny_call(next_step(deliv, e))
                if status in ("stoppet", "rca_udfoert"):
                    reason = new_round_blocked(inp, e, deliv)
                    if reason:
                        return deny_call(reason)
                    start_new_round(d, e, deliv)
                elif int(e.get("forsoeg", 0)) >= MAX_ATTEMPTS:
                    e["status"] = "stoppet"
                    save(d, s)
                    return deny_call(next_step(deliv, e))
                else:
                    e["forsoeg"] = int(e.get("forsoeg", 0)) + 1
            else:
                sample = None
                if LEVEL_SAMPLE_RE.search(str(ti.get("prompt") or "")):
                    if trade in SAMPLE_NEVER:
                        return deny_call(f"KONTROLNIVEAU: stikprøve er ikke tilladt for {trade}: brug let (eller fuld ved en "
                                          "sikkerhedsfunktion) – se skill 'kvalitetskontrol'.")
                    if fm:
                        return deny_call("KONTROLNIVEAU: stikprøve gælder kun enkeltstående fagspørgsmål uden sag (/byg:spoerg). "
                                          "Leverancer i en sag (med FASE) kontrolleres altid: brug let eller fuld.")
                    sample = "udtaget" if sampled(deliv) else "ikke_udtaget"
                tool_level = bool(LEVEL_TOOL_RE.search(str(ti.get("prompt") or "")))
                if tool_level and not REG["fag"].get(trade, {}).get("vaerktoejskontrol"):
                    return deny_call(f"KONTROLNIVEAU: værktøj findes kun for fag med deterministisk kontrol og "
                                      f"sammenligning (bim). Brug let eller fuld for {trade}.")
                e = delivs[deliv] = {"fag": trade, "type": "fag", "forsoeg": 1, "fag_agent": st,
                              "kontrol_agent": review_name(trade, pre), "oprettet": now(), "domme": []}
                if sample:
                    e["stikproeve"] = sample
                if tool_level:
                    e["kontrolniveau"] = "vaerktoej"
            e.update(status="fagkald_igang", session_id=sid, opdateret=now())
            save(d, s)
            log(d, haendelse="fagkald", leverance=deliv, runde=round_no(e), forsoeg=e["forsoeg"], agent=st)
            try:
                case_dir = find_case_dir(inp, e, deliv)
                if case_dir:
                    case_merge.save_base_for_deliverable(case_dir, deliv)
            except Exception:
                log(d, haendelse="basis_fejl", leverance=deliv, fejl=traceback.format_exc()[-400:])
            return
        # review call
        if LEVEL_FULL_RE.search(str(ti.get("prompt") or "")) and "opus" not in str(ti.get("model") or "").lower():
            return deny_call("KONTROLNIVEAU: fuld kræver Opus: gentag kontrolkaldet med model: \"opus\" i Agent-kaldet "
                              "(kontrolagenterne kører ellers på sonnet) – se skill 'kvalitetskontrol'. Er opgaven ikke "
                              "sikkerhedskritisk, så brug KONTROLNIVEAU: let.")
        if trade == "projekt":
            if e and e.get("type") != "projekt":
                return deny_call(f"Leverance {deliv} er en {e.get('fag')}-leverance og kontrolleres af {e.get('kontrol_agent')}.")
            prompt = str(ti.get("prompt") or "")
            fm = PHASE_RE.search(prompt)
            if not fm:
                return deny_call("Projektkontrol kræver linjen 'FASE: <0-4>' i prompten (0 afklaring, 1 dispositionsforslag, "
                                  "2 design, 3 integration/plan, 4 udførelse) – se skill 'kvalitetskontrol', afsnit 3.")
            phase = int(fm.group(1))
            if phase >= 3:
                dm = DESIGN_RE.search(prompt)
                ids = [x.strip().rstrip(".,;") for x in re.split(r"[,\s]+", dm.group(1)) if x.strip()] if dm else []
                if not ids:
                    return deny_call("Fase-gate: en planleverance i fase 3+ kræver linjen 'DESIGNGRUNDLAG: <leverance-id>, …' "
                                      "med de godkendte fagnotater, planen bygger på (design freeze).")
                missing = [f"{i} ({(delivs.get(i) or {}).get('status', 'ukendt')})" for i in ids
                           if (delivs.get(i) or {}).get("status") != "godkendt"]
                if missing:
                    return deny_call("Fase-gate: designgrundlaget er ikke frosset – disse fagleverancer er ikke godkendt: "
                                      + ", ".join(missing) + ". Planlæg (tidsplan, budget, montage) først, når designet er godkendt.")
                reason = g2_missing(s, case_of(deliv), ids)
                if reason:
                    return deny_call(reason)
            if not e:
                e = delivs[deliv] = {"fag": "projekt", "type": "projekt", "forsoeg": 0, "kontrol_agent": st,
                              "oprettet": now(), "domme": []}
            e["fase"] = phase
            if e.get("status") == "godkendt":
                return deny_call(next_step(deliv, e))
            if e.get("status") in ("stoppet", "rca_udfoert"):
                reason = new_round_blocked(inp, e, deliv)
                if reason:
                    return deny_call(reason)
                start_new_round(d, e, deliv)
            elif e.get("status") != "under_kontrol":
                if int(e.get("forsoeg", 0)) >= MAX_ATTEMPTS:
                    e["status"] = "stoppet"
                    save(d, s)
                    return deny_call(next_step(deliv, e))
                e["forsoeg"] = int(e.get("forsoeg", 0)) + 1
        elif e is None:
            e = delivs[deliv] = {"fag": trade, "type": "ekstern", "forsoeg": 1, "kontrol_agent": st,
                          "oprettet": now(), "domme": []}
        else:
            if e.get("fag") != trade:
                return deny_call(f"Forkert kontrolagent: {deliv} er en {e.get('fag')}-leverance og skal kontrolleres af "
                                  f"{e.get('kontrol_agent')}.")
            if e.get("type") == "ekstern":
                if e.get("status") != "under_kontrol":
                    e["forsoeg"] = int(e.get("forsoeg", 0)) + 1
            elif e.get("status") == "ikke_udtaget":
                return deny_call(next_step(deliv, e))
            elif e.get("status") not in ("fagkald_igang", "afventer_kontrol", "under_kontrol", "sammenlignet"):
                return deny_call(f"Leverance {deliv} har status '{e.get('status')}' – der er ingen ny fagversion at "
                                  f"kontrollere. {next_step(deliv, e)}")
        pm = PATH_RE.search(str(ti.get("prompt") or ""))
        if pm and e.get("type") != "ekstern":
            path = pathlib.Path(pm.group(1)).expanduser()
            if not path.is_absolute() and inp.get("cwd"):
                path = pathlib.Path(str(inp["cwd"])) / path
            if not path.is_file():
                return deny_call(f"Leverancen findes ikke på disken: {path}. Fagagenten skal skrive notatet, før det kan "
                                  "kontrolleres – tjek stien, eller send leverancen retur til fagagenten.")
            e["sti"] = os.path.normpath(str(path))
        e.update(status="under_kontrol", session_id=sid, opdateret=now())
        save(d, s)
        log(d, haendelse="kontrolkald", leverance=deliv, runde=round_no(e), forsoeg=e.get("forsoeg"), agent=st, type=e.get("type"))


# ---------- Workflow ----------
def workflow(inp: dict, d: pathlib.Path) -> None:
    """PreToolUse (Workflow): in byg-sager only when the user's latest message mentions "workflow"."""
    sid = str(inp.get("session_id") or "")
    with Lock(d):
        s = load(d)
    is_byg = "byg-sager" in str(inp.get("cwd") or "") or any(
        e.get("session_id") == sid for e in s["leverancer"].values())
    if is_byg and not (s.get("workflow_ok") or {}).get(sid):
        deny_call("byg: Workflow-værktøjet bruges kun, når brugeren selv beder om et workflow i sin besked. "
                   "'Fortsæt' betyder: genoptag den aktuelle leverance med ét fagkald. Løs opgaven i hovedtråden "
                   "eller med én agent – se projektlederens skill, afsnittet 'Tokenbudget'.")


# ---------- SubagentStop ----------
def find_verdict(msg: str):
    if not msg:
        return None, ["Kontrolagenten har ingen slutbesked."]
    for chunk in reversed(re.findall(r"```(?:json)?\s*(\{.*?\})\s*```", msg, re.S)):
        try:
            d = json.loads(chunk)
            if isinstance(d, dict) and "dom" in d:
                return d, []
        except Exception:
            continue
    dec = json.JSONDecoder()
    for m in reversed(list(re.finditer(r"\{", msg))):
        try:
            d, _ = dec.raw_decode(msg[m.start():])
            if isinstance(d, dict) and "dom" in d:
                return d, []
        except Exception:
            continue
    return None, ["Ingen JSON-dom fundet i slutbeskeden."]


def norm_class(k) -> str:
    k = str(k or "").strip().lower()
    return {"vaesentlig": "væsentlig", "vasentlig": "væsentlig"}.get(k, k)


def validate(verdict: dict) -> list:
    errors = []
    if not str(verdict.get("leverance_id") or "").strip():
        errors.append("leverance_id mangler.")
    dv = str(verdict.get("dom") or "").strip().lower()
    if dv not in ("godkendt", "afvist"):
        errors.append("dom skal være 'godkendt' eller 'afvist'.")
    findings = verdict.get("fund")
    if not isinstance(findings, list):
        errors.append("fund skal være en liste (tom liste er tilladt).")
        findings = []
    open_items = []
    for i, f in enumerate(findings):
        if not isinstance(f, dict):
            errors.append(f"fund nr. {i + 1} er ikke et objekt.")
            continue
        fid = str(f.get("id") or f"#{i + 1}")
        cls = norm_class(f.get("klasse"))
        st = str(f.get("status") or "").strip().lower()
        if cls not in ("kritisk", "væsentlig", "mindre"):
            errors.append(f"{fid}: klasse skal være kritisk, væsentlig eller mindre.")
        if st not in STATUSES:
            errors.append(f"{fid}: status skal være nyt, aabent, lukket eller bestridt.")
        if cls in BLOCKING and st != "lukket":
            missing = [k for k in ("krav", "kilde", "evidens") if not str(f.get(k) or "").strip()]
            if missing:
                errors.append(f"{fid} ({cls}): mangler {', '.join(missing)} – blokerende fund kræver krav, kilde og evidens.")
            open_items.append(fid)
    clarify = verdict.get("afklar_med_bruger", [])
    if not isinstance(clarify, list) or any(not isinstance(a, dict) or not str(a.get("spoergsmaal") or "").strip() for a in clarify):
        errors.append("afklar_med_bruger skal være en liste af objekter med 'spoergsmaal' (tom liste er tilladt).")
    unchecked = verdict.get("ikke_kontrolleret", [])
    if not isinstance(unchecked, list) or any(not isinstance(x, str) or not x.strip() for x in unchecked):
        errors.append("ikke_kontrolleret skal være en liste af korte tekster om det, der ikke er kontrolleret (tom liste er tilladt).")
    if dv == "godkendt" and open_items:
        errors.append(f"dom 'godkendt' er ikke tilladt med åbne blokerende fund: {', '.join(open_items)}.")
    if dv == "afvist" and not open_items:
        errors.append("dom 'afvist' kræver mindst ét åbent kritisk eller væsentligt fund.")
    verdict["dom"] = dv
    return errors


def count_findings(verdict: dict) -> dict:
    t = {"kritisk": 0, "væsentlig": 0, "mindre": 0}
    for f in verdict.get("fund") or []:
        if isinstance(f, dict) and str(f.get("status") or "").lower() != "lukket":
            cls = norm_class(f.get("klasse"))
            if cls in t:
                t[cls] += 1
    return t


def case_dir_path(inp: dict, e: dict):
    case_dir = e.get("sagsmappe")
    if not case_dir or str(case_dir).lower() in ("null", "none"):
        return None
    p = pathlib.Path(str(case_dir)).expanduser()
    if not p.is_absolute():
        p = pathlib.Path(str(inp.get("cwd") or os.getcwd())) / p
    return p if p.is_dir() else None


def _text(content) -> str:
    if isinstance(content, str):
        return content
    parts = []
    for b in content or []:
        if not isinstance(b, dict):
            continue
        if b.get("type") == "text":
            parts.append(b.get("text", ""))
        elif b.get("type") == "tool_use":
            # Hand-back and the like: the verdict may be in the tool call's input
            for v in (b.get("input") or {}).values():
                if isinstance(v, str):
                    parts.append(v)
        elif b.get("type") == "tool_result":
            parts.append(_text(b.get("content")))
    return "\n".join(parts)


def read_transcript(path, count: int = 3) -> str:
    """Text from the last assistant messages (incl. tool_use input), newest last."""
    try:
        lines = pathlib.Path(path).read_text(encoding="utf-8").splitlines()
        found = []
        for line in reversed(lines):
            obj = json.loads(line)
            msg = obj.get("message") or {}
            if msg.get("role") == "assistant":
                found.append(_text(msg.get("content")))
                if len(found) >= count:
                    break
        return "\n".join(reversed(found))
    except Exception:
        return ""


def first_prompt(path) -> str:
    """First user message in the agent's transcript (the prompt from the orchestrator)."""
    try:
        for line in pathlib.Path(path).read_text(encoding="utf-8").splitlines():
            obj = json.loads(line)
            msg = obj.get("message") or {}
            if msg.get("role") == "user":
                return _text(msg.get("content"))
    except Exception:
        pass
    return ""


def trade_handoff(inp: dict, d: pathlib.Path, trade: str, agent_name: str) -> None:
    m = DELIVERABLE_RE.search(first_prompt(inp.get("agent_transcript_path")) or "")
    with Lock(d):
        s = load(d)
        candidates = []
        if m:
            candidates = [m.group(1).rstrip(".,;:)")]
        else:
            sid = str(inp.get("session_id") or "")
            candidates = [deliv for deliv, e in s["leverancer"].items()
                          if e.get("fag") == trade and e.get("status") == "fagkald_igang" and e.get("session_id") == sid]
            if len(candidates) != 1:
                log(d, haendelse="fagaflevering_uklar", agent=agent_name, kandidater=candidates)
                return
        handed_off = []
        for deliv in candidates:
            e = s["leverancer"].get(deliv)
            if e and e.get("fag") == trade and e.get("status") == "fagkald_igang":
                new_status = "ikke_udtaget" if e.get("stikproeve") == "ikke_udtaget" else "afventer_kontrol"
                e.update(status=new_status, opdateret=now())
                save(d, s)
                log(d, haendelse="fagaflevering", leverance=deliv, forsoeg=e.get("forsoeg"), agent=agent_name,
                    stikproeve=e.get("stikproeve"))
                handed_off.append((deliv, find_case_dir(inp, e, deliv), f"runde {round_no(e)}, forsøg {e.get('forsoeg')}"))
    # git outside the state lock, so parallel hooks do not wait for it
    for deliv, case_dir, what in handed_off:
        sha = git_commit(d, case_dir, f"{deliv}: fagaflevering ({what})", git_patterns(case_dir.name, trade)) if case_dir else None
        if not sha:
            continue
        with Lock(d):
            s = load(d)
            e = s["leverancer"].get(deliv)
            if not e:
                continue
            e["fag_sha"] = sha
            if e.get("kontrolleret_sha"):
                write_changes(d, case_dir, deliv, e, trade)
            save(d, s)


def write_changes(d: pathlib.Path, case_dir: pathlib.Path, deliv: str, e: dict, trade: str) -> None:
    """Diff from the last reviewed trade version to the new one – the basis for review attempts 2–3."""
    try:
        text = case_git.diff(case_git.root_for(case_dir), e["kontrolleret_sha"], e["fag_sha"], git_patterns(case_dir.name, trade))
        f = case_dir / "kvalitet" / f"{safe(deliv)}__aendringer.diff"
        if text:
            f.parent.mkdir(exist_ok=True)
            f.write_text(text, encoding="utf-8")
            e["aendringer"] = str(f)
        elif f.exists():
            f.unlink()
            e.pop("aendringer", None)
    except Exception:
        log(d, haendelse="diff_fejl", leverance=deliv, fejl=traceback.format_exc()[-400:])


def merge_proposals(inp: dict, d: pathlib.Path, e: dict, deliv: str) -> list:
    """Approved trade deliverable: merge its proposals into the shared case files. Returns the changed target files."""
    case_dir = find_case_dir(inp, e, deliv)
    if not case_dir:
        return []
    targets = []
    for f in case_merge.deliverable_proposals(case_dir, deliv):
        try:
            r = case_merge.merge(f, case_dir, deliv)
        except Exception:
            log(d, haendelse="flet_fejl", leverance=deliv, forslag=f.name, fejl=traceback.format_exc()[-400:])
            continue
        log(d, haendelse="flet", leverance=deliv, forslag=f.name, ok=r["ok"], besked=r["besked"])
        if r["ok"]:
            targets.append(r["maal"])
        else:
            e.setdefault("flet_konflikter", {})[str(f)] = r["besked"]
    if not e.get("flet_konflikter"):
        case_merge.clear_base(case_dir, deliv)
    return targets


def helper_call(d, s, e, deliv, trade, st, sid) -> None:
    """Comparison (or other helper) of a handed-off trade version – before the formal review."""
    if not e or e.get("fag") != trade:
        return deny_call(f"Leverance {deliv} findes ikke for faget '{trade}'. Kald først fagagenten med 'LEVERANCE: {deliv}'.")
    status = e.get("status")
    if status == "under_sammenligning":
        e.update(session_id=sid, opdateret=now())
        save(d, s)
        log(d, haendelse="sammenligning_gentaget", leverance=deliv, agent=st)
        return
    if status not in ("afventer_kontrol", "sammenlignet"):
        return deny_call(f"Leverance {deliv} har status '{status}'. Sammenligning kræver en afleveret fagversion "
                          f"(fagagenten skal have afleveret, og kontrollen må ikke være gået i gang).")
    if int(e.get("sammenligninger", 0)) >= MAX_COMPARISONS:
        return deny_call(f"Højst {MAX_COMPARISONS} sammenligninger pr. leverance ({deliv}). Send leverancen til "
                          f"{e.get('kontrol_agent')} med de resterende afvigelser beskrevet i notatet, eller eskalér til brugeren.")
    e["sammenligninger"] = int(e.get("sammenligninger", 0)) + 1
    e.update(status="under_sammenligning", session_id=sid, opdateret=now(), hjaelper_agent=st)
    save(d, s)
    log(d, haendelse="sammenligning", leverance=deliv, nr=e["sammenligninger"], agent=st)


def helper_handoff(inp: dict, d: pathlib.Path, trade: str, agent_name: str) -> None:
    m = DELIVERABLE_RE.search(first_prompt(inp.get("agent_transcript_path")) or "")
    if not m:
        log(d, haendelse="hjaelperaflevering_uden_leverance", agent=agent_name)
        return
    deliv = m.group(1).rstrip(".,;:)")
    text = (inp.get("last_assistant_message") or "") + "\n" + read_transcript(inp.get("agent_transcript_path"), 1)
    r = RESULT_RE.findall(text)
    verdict, merged, e = None, [], None
    with Lock(d):
        s = load(d)
        e = s["leverancer"].get(deliv)
        if e and e.get("fag") == trade and e.get("status") == "under_sammenligning":
            e.update(status="sammenlignet", opdateret=now(), sammenligning_resultat=(r[-1].lower() if r else None))
            chk = None
            for chunk in CHECK_RE.findall(text)[::-1]:
                try:
                    chk = json.loads(chunk)
                    break
                except json.JSONDecodeError:
                    continue
            tool_ok = (e.get("kontrolniveau") == "vaerktoej" and e["sammenligning_resultat"] == "ok"
                            and isinstance(chk, dict) and chk.get("fejl") == 0 and chk.get("sporbarhed") == 0)
            verdict = None
            if tool_ok:
                verdict = {"leverance_id": deliv, "fag": trade, "forsoeg": e.get("forsoeg"), "dom": "godkendt",
                       "godkendt_af": "vaerktoej", "rubric_version": "vaerktoej@1",
                       "sammenligninger": e.get("sammenligninger"), "tjek": chk, "fund": []}
                e.setdefault("domme", []).append({"runde": round_no(e), "forsoeg": e.get("forsoeg"), "dom": "godkendt",
                                                  "af": "vaerktoej", "aabne_fund": {}, "tid": now()})
                e.update(status="godkendt", godkendt_af="vaerktoej")
                if e.get("fag_sha"):
                    e["kontrolleret_sha"] = e["fag_sha"]
                merged = merge_proposals(inp, d, e, deliv)
            save(d, s)
            log(d, haendelse="sammenligning_afleveret", leverance=deliv, nr=e.get("sammenligninger"),
                resultat=e.get("sammenligning_resultat"), agent=agent_name, tjek=chk, godkendt_af_vaerktoej=tool_ok)
    if verdict:
        case_dir = find_case_dir(inp, e, deliv)
        try:
            if case_dir:
                qdir = case_dir / "kvalitet"
                qdir.mkdir(exist_ok=True)
                (qdir / f"{safe(deliv)}__forsoeg-{e.get('forsoeg')}__vaerktoej.json").write_text(
                    json.dumps(verdict, ensure_ascii=False, indent=2), encoding="utf-8")
        except Exception:
            log(d, haendelse="domfil_fejl", fejl=traceback.format_exc()[-400:])
        if case_dir:
            git_commit(d, case_dir, f"{deliv}: godkendt af værktøj (sammenligning ok, tjek rent)"
                       + (f", {len(merged)} forslag flettet" if merged else ""),
                       [f"{case_dir.name}/kvalitet/**", f"{case_dir.name}/forslag/**"])


def subagentstop(inp: dict, d: pathlib.Path) -> None:
    agent_name = str(inp.get("agent_type") or "")
    _, base = split_name(agent_name)
    kind, trade = classify(base)
    if kind == "fag":
        return trade_handoff(inp, d, trade, agent_name)
    if kind == "hjaelper":
        return helper_handoff(inp, d, trade, agent_name)
    if kind != "kontrol":
        return
    msg = inp.get("last_assistant_message") or ""
    verdict, errors = find_verdict(msg)
    if errors:
        verdict2, errors2 = find_verdict(read_transcript(inp.get("agent_transcript_path")))
        if not errors2:
            verdict, errors = verdict2, errors2
    if not errors:
        errors = validate(verdict)
    with Lock(d):
        s = load(d)
        delivs = s["leverancer"]
        e = None
        if not errors:
            deliv = str(verdict.get("leverance_id")).strip()
            e = delivs.get(deliv)
            if e is None:
                errors = [f"leverance_id '{deliv}' matcher ikke en registreret leverance – brug præcis ID'et fra prompten."]
            elif e.get("fag") != trade:
                errors = [f"leverance_id '{deliv}' tilhører faget '{e.get('fag')}', ikke '{trade}'."]
            else:
                # A repeated or stale verdict (e.g. from a resumed review agent) is not recorded
                stale = None
                if e.get("status") != "under_kontrol":
                    stale = f"status er '{e.get('status')}', ikke 'under_kontrol'"
                elif str(verdict.get("forsoeg") or "").strip().isdigit() and int(verdict["forsoeg"]) != int(e.get("forsoeg", 0)):
                    stale = f"dommen gælder forsøg {verdict['forsoeg']}, men leverancen er i forsøg {e.get('forsoeg')}"
                if stale:
                    log(d, haendelse="forældet_dom", leverance=deliv, agent=agent_name, grund=stale)
                    return
                if int(e.get("forsoeg", 1)) > 1 and e.get("type") != "ekstern":
                    for f in verdict.get("fund") or []:
                        cls = norm_class(f.get("klasse"))
                        if str(f.get("status") or "").lower() == "nyt" and cls in BLOCKING:
                            ng = str(f.get("nyt_grundlag") or "").strip().lower()
                            if ng not in NEW_BASIS or (ng == "kritisk_sikkerhed" and cls != "kritisk"):
                                errors.append(f"{f.get('id')}: nyt {cls} fund i forsøg {e.get('forsoeg')} kræver \"nyt_grundlag\": "
                                            "\"regression\" eller \"aendret_tekst\" (eller \"kritisk_sikkerhed\" for kritiske fund). "
                                            "Blev det overset i forsøg 1, så nedgradér det til 'mindre' og skriv det under kontrolsvigt "
                                            "(fund-fastlåsning, kontrolprotokol afsnit 4).")
        if errors:
            log(d, haendelse="ugyldig_dom", agent=agent_name, fejl=errors, gentaget=bool(inp.get("stop_hook_active")))
            if not inp.get("stop_hook_active"):
                block("Ugyldig kontroldom – ret den, før du afslutter:\n- " + "\n- ".join(errors) +
                       "\nAfslut med præcis én JSON-blok efter skemaet i kontrolprotokollen (afsnit 5).")
            return
        e.setdefault("domme", []).append({"runde": round_no(e), "forsoeg": e.get("forsoeg"), "dom": verdict["dom"],
                                          "aabne_fund": count_findings(verdict), "tid": now(),
                                          "afklar_med_bruger": len(verdict.get("afklar_med_bruger") or []),
                                          "ikke_kontrolleret": list(verdict.get("ikke_kontrolleret") or [])})
        if e.get("type") == "ekstern":
            e["status"] = "vurderet_ekstern"
        elif verdict["dom"] == "godkendt":
            e["status"] = "godkendt"
        else:
            e["status"] = "stoppet" if int(e.get("forsoeg", 1)) >= MAX_ATTEMPTS else "afvist"
        if verdict.get("sagsmappe"):
            e["sagsmappe"] = verdict.get("sagsmappe")
        if e.get("fag_sha"):
            e["kontrolleret_sha"] = e["fag_sha"]
        merged = merge_proposals(inp, d, e, deliv) if e["status"] == "godkendt" and e.get("type") == "fag" else []
        e["opdateret"] = now()
        save(d, s)
    log(d, haendelse="dom", leverance=deliv, dom=verdict["dom"], status=e["status"], runde=round_no(e), forsoeg=e.get("forsoeg"))
    try:
        case_dir = case_dir_path(inp, e)
        if case_dir:
            qdir = case_dir / "kvalitet"
            qdir.mkdir(exist_ok=True)
            round_part = f"__runde-{round_no(e)}" if round_no(e) > 1 else ""
            (qdir / f"{safe(deliv)}{round_part}__forsoeg-{e.get('forsoeg')}.json").write_text(
                json.dumps(verdict, ensure_ascii=False, indent=2), encoding="utf-8")
    except Exception:
        log(d, haendelse="domfil_fejl", fejl=traceback.format_exc()[-400:])
    case_dir = find_case_dir(inp, e, deliv)
    root = case_git.root_for(case_dir) if case_dir else None
    if root:
        paths = [f"{case_dir.name}/kvalitet/**", f"{case_dir.name}/forslag/**"]
        for m in merged:
            try:
                paths.append(pathlib.Path(m).resolve().relative_to(root.resolve()).as_posix())
            except ValueError:
                pass
        git_commit(d, case_dir, f"{deliv}: dom {verdict['dom']} (runde {round_no(e)}, forsøg {e.get('forsoeg')})"
                   + (f", {len(merged)} forslag flettet" if merged else ""), paths)


# ---------- Stop ----------
def rca_file(inp: dict, e: dict, deliv: str):
    name = rca_name(deliv, round_no(e))
    case_dir = case_dir_path(inp, e)
    if case_dir and (case_dir / "kvalitet" / name).exists():
        return case_dir / "kvalitet" / name
    cwd = pathlib.Path(str(inp.get("cwd") or os.getcwd()))
    return next(iter(cwd.glob(f"byg-sager/*/kvalitet/{name}")), None) or next(
        iter(tmp_root().glob(f"*/kvalitet/{name}")), None)


def rca_exists(inp: dict, e: dict, deliv: str) -> bool:
    return rca_file(inp, e, deliv) is not None


def new_round_blocked(inp: dict, e: dict, deliv: str):
    """Reason a new round may not start – or None if it may."""
    r = round_no(e)
    if r >= MAX_ROUNDS or e.get("ny_runde_ok") != r:
        return next_step(deliv, e)
    f = rca_file(inp, e, deliv)
    if f is None:
        return (f"Runde {r + 1} kræver først root cause-analysen for runde {r}. " + next_step(deliv, e))
    try:
        text = f.read_text(encoding="utf-8")
    except Exception:
        text = ""
    if len(WHY_RE.findall(text)) < 5 or not ROOT_CAUSE_RE.search(text):
        return (f"{f.name} mangler en 5 Why-kæde: mindst fem nummererede 'Hvorfor'-linjer (hvert svar besvarer det "
                f"foregående, med evidens) og en linje med 'Grundårsag' (skabelonens afsnit 3), før runde {r + 1} starter.")
    if not IMPROVEMENT_RE.search(text):
        return (f"{f.name} mangler linjen 'Forbedring implementeret: ja'. Implementér læringen som forbedring af "
                f"fagagenten (agentens hukommelse og repoet), notér hvad der er ændret, og skriv linjen i RCA'en, før "
                f"runde {r + 1} starter.")
    return None


def start_new_round(d: pathlib.Path, e: dict, deliv: str) -> None:
    e["runde"] = round_no(e) + 1
    e["forsoeg"] = 1
    log(d, haendelse="ny_runde", leverance=deliv, runde=e["runde"])


def age_sec(e: dict) -> float:
    try:
        return time.time() - time.mktime(time.strptime(str(e.get("opdateret")), "%Y-%m-%dT%H:%M:%S"))
    except Exception:
        return 0


def write_permission(inp: dict, fpath: str, s: dict):
    """One writer per file: in byg-sager/ (and byg-tmp/) a trade agent may only write its own files. Reason for denial
    or None."""
    _, base = split_name(str(inp.get("agent_type") or ""))
    kind, trade = classify(base)
    if kind != "fag":
        return None
    parts = pathlib.Path(fpath).parts
    hits = [i for i, d in enumerate(parts) if d in ("byg-sager", TMP_NAME)]
    if not hits:
        return None
    i = hits[-1]
    rest = parts[i + 1:]
    allowed = write_patterns(trade)
    guidance = (f"Du må kun skrive dine egne filer i sagsmappen: {', '.join(allowed)}. Skal en fælles fil ændres "
                  f"(graenseflader.md, risici.md, kontrolplan.md, ejendomskortet), så skriv et forslag: "
                  f"forslag/{trade}-<nr>__<mål>.md med de nye eller ændrede tabelrækker under samme ##-overskrift som i "
                  f"målfilen (rækker matches på ID i første kolonne). Det flettes ind, når leverancen er godkendt. Andet "
                  f"(projektgrundlag, beslutninger, status) beskriver du i notatet og rapporten – projektlederen skriver det.")
    if len(rest) < 2 or rest[0] == "ejendomme":
        return f"{fpath} ejes af projektlederen (én skriver pr. fil). " + guidance
    rel = "/".join(rest[1:])
    case_dir = pathlib.Path(*parts[:i + 2])
    if ".." in rest:
        return f"{fpath}: stier med '..' er ikke tilladt i sagsmappen. " + guidance
    if any(fnmatch(rel, m) for m in allowed):
        if rel.startswith("forslag/"):
            if case_merge.target_for(pathlib.Path(fpath), case_dir) is None:
                return (f"{rel}: ukendt mål. Forslag hedder forslag/{trade}-<nr>__<mål>.md med mål "
                        f"{', '.join(case_merge.TARGETS)} (ejendomskortet kræver '**Ejendom:** <sti>' i projektgrundlaget).")
            # The proposal must belong to an ongoing deliverable, otherwise it is never merged
            open_items = [deliv for deliv, e in s["leverancer"].items() if e.get("fag") == trade and case_of(deliv) == case_dir.name
                     and e.get("status") in ("fagkald_igang", "afventer_kontrol", "sammenlignet")]
            prefix = pathlib.Path(fpath).name.split("__", 1)[0]
            if prefix not in {case_merge.proposal_prefix(deliv) for deliv in open_items}:
                names = ", ".join(f"forslag/{case_merge.proposal_prefix(deliv)}__<mål>.md" for deliv in open_items) or "ingen"
                return (f"{rel} hører ikke til en igangværende {trade}-leverance i sagen, så det ville aldrig blive "
                        f"flettet. Brug leverancens navn: {names}.")
            case_merge.save_base(pathlib.Path(fpath), case_dir)
        return None
    if any(fnmatch(rel, m) for m in REG["fag"][trade].get("skriv_ny", [])) and not pathlib.Path(fpath).exists():
        return None
    return f"{rel} i sagen ejes ikke af {trade} (én skriver pr. fil). " + guidance


def protect(inp: dict, d: pathlib.Path) -> None:
    """PreToolUse Write/Edit: write permission per trade, and protect files that belong to approved deliverables."""
    ti = inp.get("tool_input") or {}
    fpath = ti.get("file_path") or ti.get("notebook_path")
    if not fpath:
        return
    fpath = os.path.normpath(str(pathlib.Path(str(fpath)).expanduser()))  # 'a/../b' must not bypass the write permission
    s = load(d)
    reason = write_permission(inp, fpath, s)
    if reason:
        log(d, haendelse="skriveret_afvist", fil=fpath, agent=inp.get("agent_type"))
        return deny_call(reason)
    for deliv, e in s["leverancer"].items():
        if e.get("status") == "godkendt" and e.get("sti") and e["sti"] == fpath:
            reason = (f"{fpath} er leverancen {deliv}, som er godkendt af kvalitetskontrollen. Ret den ikke direkte: "
                     f"skriv afvigelsen i dit eget notat og bed projektlederen om en ændring under nyt leverance-ID "
                     f"(fx '{deliv}-r2') via aendringer.md.")
            if inp.get("agent_type") or inp.get("agent_id"):
                log(d, haendelse="beskyttet_fil_afvist", leverance=deliv, fil=fpath, agent=inp.get("agent_type"))
                return deny_call(reason)
            log(d, haendelse="beskyttet_fil_advarsel", leverance=deliv, fil=fpath)
            print(json.dumps({"systemMessage": "byg-kontrol: " + reason,
                              "hookSpecificOutput": {"hookEventName": "PreToolUse", "additionalContext": reason}},
                             ensure_ascii=False))
            return


def context_tokens(path) -> int:
    """The main thread's context (input + cache) in the latest reply, read backwards in the last 2 MB of the transcript."""
    try:
        with open(path, "rb") as fh:
            fh.seek(0, os.SEEK_END)
            start = max(0, fh.tell() - 2_000_000)
            fh.seek(start)
            lines = fh.read().split(b"\n")
        for line in reversed(lines[1:] if start else lines):
            if b'"usage"' not in line:
                continue
            try:
                obj = json.loads(line)
            except Exception:
                continue
            msg = obj.get("message") or {}
            if msg.get("role") != "assistant" or obj.get("isSidechain"):
                continue
            u = msg.get("usage") or {}
            n = sum(int(u.get(k) or 0) for k in ("input_tokens", "cache_creation_input_tokens", "cache_read_input_tokens"))
            if n:
                return n
    except Exception:
        pass
    return 0


def context_reminder(inp: dict, s: dict) -> tuple[str, str] | None:
    """(to the user, to the model) when a byg session's main thread has passed the next context limit."""
    sid = str(inp.get("session_id") or "")
    cases = sorted({case_of(deliv) for deliv, e in s["leverancer"].items() if sid and e.get("session_id") == sid})
    if not cases:
        return None
    n = context_tokens(inp.get("transcript_path"))
    if n < CONTEXT_LIMIT:
        return None
    step = 1 + (n - CONTEXT_LIMIT) // CONTEXT_STEP
    warned = s.setdefault("kontekst", {})
    if int(warned.get(sid, 0)) >= step:
        return None
    warned[sid] = step
    case_id = cases[0] if len(cases) == 1 else "<sag-id>"
    k = f"{n // 1000}k"
    to_user = (f"byg: Samtalen fylder nu ca. {k} tokens, og hvert svar læser det hele igen. Når den igangværende "
                  f"opgave er færdig, så fortsæt i en ny session med /byg:status {case_id} – sagsmappen husker resten.")
    to_model = (f"Kontekstbudget: hovedtråden er ca. {k} tokens, og hvert svar læser det hele igen. Afslut den igangværende "
                 f"opgave, opdatér status.md (næste skridt, åbne punkter, leverancer), og foreslå brugeren at fortsætte i en "
                 f"ny session med /byg:status {case_id}. Lav ikke research og læs ikke store filer i denne tråd; send det til en "
                 f"subagent (projektleder-skill, 'Effektivitet').")
    return to_user, to_model


# ---------- compact (PreCompact and SessionStart "compact") ----------
def session_cases(inp: dict, s: dict) -> dict:
    """{case id: case_dir or None} for cases with deliverables in the session. Without deliverables: the case folder in cwd."""
    sid = str(inp.get("session_id") or "")
    cwd = pathlib.Path(str(inp.get("cwd") or os.getcwd()))
    cases = {}
    for deliv, e in s["leverancer"].items():
        if not sid or e.get("session_id") != sid or "/" not in deliv:
            continue
        case_id = case_of(deliv)
        if cases.get(case_id) is None:
            p = case_dir_path(inp, e)
            if p is None:
                for cand in (cwd / "byg-sager" / case_id, cwd / case_id, cwd, tmp_root() / case_id):
                    if cand.name == case_id and (cand / "status.md").is_file():
                        p = cand
                        break
            cases[case_id] = p
    if not cases and (cwd / "status.md").is_file() and cwd.parent.name == "byg-sager":
        cases[cwd.name] = cwd
    return cases


def open_deliverables(inp: dict, s: dict) -> list:
    sid = str(inp.get("session_id") or "")
    lines = []
    for deliv, e in sorted(s["leverancer"].items()):
        if not sid or e.get("session_id") != sid or e.get("status") in ("godkendt", "vurderet_ekstern", "rca_udfoert", "ikke_udtaget"):
            continue
        step = next_step(deliv, e)
        lines.append(f"- {deliv}: {e.get('status')} (runde {round_no(e)}/{MAX_ROUNDS}, forsøg {e.get('forsoeg')}/{MAX_ATTEMPTS})"
                      + (f" – {step}" if step else ""))
    return lines


def precompact(inp: dict, d: pathlib.Path) -> None:
    """PreCompact: stdout becomes extra instructions for the summary."""
    with Lock(d):
        s = load(d)
    cases = session_cases(inp, s)
    if not cases:
        return
    log(d, haendelse="precompact", session_id=str(inp.get("session_id") or ""), trigger=inp.get("trigger"))
    print("Dette er en byg-sag (" + ", ".join(sorted(cases)) + "). Sagsmappen er hukommelsen og genindlæses efter "
          "compact, så gengiv ikke filindhold, fagnotater eller agentrapporter. Bevar i stedet præcist: sag-id og "
          "sagsmappe; den igangværende opgave og næste konkrete skridt; alle leverance-ID'er fra samtalen med status, "
          "runde/forsøg og blokerende fund ordret (fund-ID og krav); brugerens beslutninger og svar, som endnu ikke "
          "står i beslutningslog.md eller status.md, ordret; åbne spørgsmål til brugeren; aftalte afgrænsninger og "
          "brugerens præferencer for denne opgave; stier til filer, der er ændret, men ikke kontrolleret.")


def after_compact(inp: dict, d: pathlib.Path) -> None:
    """SessionStart (source 'compact'): reload the case status and review state into the compacted thread."""
    with Lock(d):
        s = load(d)
    cases = session_cases(inp, s)
    if not cases:
        return
    parts = ["byg: Samtalen er netop compactet. Resuméet er ikke sagens hukommelse; det er sagsmappen. Før du "
            "fortsætter: følg projektlederens regler (skill 'projektleder' og 'kvalitetskontrol' – indlæs dem igen, "
            "hvis reglerne ikke står i konteksten), læs kvalitet/kontrollog.md og de seneste ca. 15 linjer af "
            "beslutningslog.md og aendringer.md for sagen, og skriv brugerbeslutninger fra resuméet, der mangler i "
            "beslutningsloggen, ind dér nu."]
    open_items = open_deliverables(inp, s)
    if open_items:
        parts.append("Åbne leverancer i denne session (byg-kontrols tilstand – den gælder frem for resuméet):\n" + "\n".join(open_items))
    for case_id, p in sorted(cases.items()):
        f = p / "status.md" if p else None
        if f and f.is_file():
            text = f.read_text(encoding="utf-8", errors="replace")
            if len(text) > STATUS_MAX_CHARS:
                text = text[:STATUS_MAX_CHARS] + f"\n[… afkortet – læs resten af {f} målrettet]"
            parts.append(f"status.md for {case_id} ({f}):\n{text}")
        else:
            parts.append(f"Sagen {case_id}: status.md blev ikke fundet – find sagsmappen under byg-sager/ og læs den.")
    log(d, haendelse="efter_compact", session_id=str(inp.get("session_id") or ""), sager=sorted(cases))
    print(json.dumps({"hookSpecificOutput": {"hookEventName": "SessionStart", "additionalContext": "\n\n".join(parts)}},
                     ensure_ascii=False))


def user_prompt(inp: dict, d: pathlib.Path) -> None:
    """UserPromptSubmit: the user's own approval of G2 ('Godkend G2 <sag-id>') and the context budget reminder."""
    text = str(inp.get("prompt") or "")
    found = [m.group(1).rstrip(".,;:)") for m in APPROVE_G2_RE.finditer(text)]
    messages = []
    with Lock(d):
        s = load(d)
        reminder = context_reminder(inp, s)
        sid = str(inp.get("session_id") or "")
        wf = bool(WORKFLOW_RE.search(text))
        changed = False
        if bool((s.get("workflow_ok") or {}).get(sid)) != wf:
            s.setdefault("workflow_ok", {})[sid] = wf
            changed = True
        for m in NEW_ROUND_RE.finditer(text):
            deliv = m.group(1).rstrip(".,;:)")
            e = s["leverancer"].get(deliv)
            if not e or e.get("status") not in ("stoppet", "rca_udfoert"):
                continue
            if round_no(e) >= MAX_ROUNDS:
                messages.append(f"{deliv} har brugt alle {MAX_ROUNDS} runder; fortsæt under et nyt leverance-ID.")
                continue
            e["ny_runde_ok"] = round_no(e)
            changed = True
            log(d, haendelse="ny_runde_godkendt", leverance=deliv, runde=round_no(e))
            messages.append(f"Brugeren har godkendt en ny runde for {deliv}. " + next_step(deliv, e))
        for case_id in found:
            design = sorted(deliv for deliv, e in s["leverancer"].items()
                            if case_of(deliv) == case_id and e.get("type") == "fag" and e.get("status") == "godkendt")
            s.setdefault("gates", {}).setdefault(case_id, {})["G2"] = {
                "tid": now(), "design": design, "session_id": str(inp.get("session_id") or ""), "tekst": text[:300]}
            log(d, haendelse="gate_G2_godkendt", sag=case_id, design=design)
            messages.append(f"G2 (løsningsgodkendelse) for {case_id} er registreret som godkendt af brugeren med "
                            f"{len(design)} godkendte fagleverancer: {', '.join(design) or 'ingen'}. "
                            "Skriv godkendelsen i beslutningsloggen, og start fase 3.")
        if found or reminder or changed:
            save(d, s)
    if reminder:
        log(d, haendelse="kontekst_paamindelse", session_id=str(inp.get("session_id") or ""))
        messages.append(reminder[1])
    if not messages:
        return
    out = {"hookSpecificOutput": {"hookEventName": "UserPromptSubmit", "additionalContext": " ".join(messages)}}
    if reminder:
        out["systemMessage"] = reminder[0]
    print(json.dumps(out, ensure_ascii=False))


def commit_main_thread(inp: dict, d: pathlib.Path, s: dict) -> None:
    """The main thread's (project manager's) changes in the session's cases are committed at every Stop."""
    roots = {}
    for p in session_cases(inp, s).values():
        root = case_git.root_for(p) if p else None
        if root:
            roots[str(root)] = p
    for p in roots.values():
        git_commit(d, p, f"hovedtråd: ændringer (session {str(inp.get('session_id') or '')[:8]})")


def stop(inp: dict, d: pathlib.Path) -> None:
    with Lock(d):
        s = load(d)
    commit_main_thread(inp, d, s)  # outside the state lock; case git has its own time budget
    if inp.get("stop_hook_active"):
        return
    sid = str(inp.get("session_id") or "")
    items, changed = [], False
    with Lock(d):
        s = load(d)
        for deliv, e in s["leverancer"].items():
            if e.get("session_id") != sid:
                continue
            for path, message in list((e.get("flet_konflikter") or {}).items()):
                if not pathlib.Path(path).exists():
                    del e["flet_konflikter"][path]
                    changed = True
                    continue
                items.append(f"{deliv}: {message}. Du ejer målfilen: afgør konflikten (ret målfilen eller forslaget), og "
                               f"flet med 'python3 {HERE / 'review_gate.py'} merge {path}' (--force tilsidesætter konflikten) "
                               f"eller i hånden – flyt så forslaget til forslag/flettet/, eller slet det, hvis det ikke skal bruges.")
            status, type_ = e.get("status"), e.get("type")
            if type_ == "ekstern":
                if status == "under_kontrol":
                    items.append(f"{deliv}: kontrolagentens gyldige dom mangler → kald {e.get('kontrol_agent')} igen.")
                continue
            if status == "fagkald_igang":
                if age_sec(e) > IN_PROGRESS_MAX_SEC:
                    items.append(f"{deliv}: fagkaldet har ikke afleveret i over {IN_PROGRESS_MAX_SEC // 60} min. Er agenten "
                                   f"afbrudt, så kald {e.get('fag_agent')} igen med 'LEVERANCE: {deliv}' (tæller ikke som nyt forsøg).")
                continue
            if status == "afventer_kontrol":
                items.append(f"{deliv}: afventer kontrol → kald {e.get('kontrol_agent')} med 'LEVERANCE: {deliv}'.")
            elif status == "under_sammenligning":
                items.append(f"{deliv}: sammenligningens resultat mangler → kald {e.get('hjaelper_agent')} igen.")
            elif status == "sammenlignet":
                items.append(f"{deliv}: sammenlignet ({e.get('sammenligning_resultat') or '?'}) → send afvigelserne retur til "
                               f"{e.get('fag_agent')}, eller kald {e.get('kontrol_agent')}, hvis der ikke er flere at rette.")
            elif status == "under_kontrol":
                items.append(f"{deliv}: gyldig kontroldom mangler → kald {e.get('kontrol_agent')} igen.")
            elif status == "afvist":
                items.append(f"{deliv}: {next_step(deliv, e)} Kræver fundene brugerens beslutning, så stop og spørg brugeren.")
            elif status == "stoppet":
                if rca_exists(inp, e, deliv):
                    e["status"] = "rca_udfoert"
                    changed = True
                elif e.get("ny_runde_ok") == round_no(e):
                    items.append(f"{deliv}: {next_step(deliv, e)}")
                elif e.get("eskaleret") != round_no(e):
                    e["eskaleret"] = round_no(e)
                    changed = True
                    items.append(f"{deliv}: {next_step(deliv, e)}")
        if changed:
            save(d, s)
    if items:
        block("Kvalitetskontrollen er ikke afsluttet for denne sessions leverancer:\n- " + "\n- ".join(items))


# ---------- manual commands ----------
def manual(cmd: str, args: list) -> int:
    d = data_dir()
    with Lock(d):
        s = load(d)
        if cmd == "status":
            if not s["leverancer"]:
                print("Ingen registrerede leverancer.")
            for deliv, e in sorted(s["leverancer"].items()):
                print(f"{deliv:45} {e.get('fag', ''):12} {e.get('status', ''):18} "
                      f"runde {round_no(e)}/{MAX_ROUNDS} forsøg {e.get('forsoeg')}/{MAX_ATTEMPTS}")
            for case_id, g in sorted((s.get("gates") or {}).items()):
                if g.get("G2"):
                    print(f"GATE G2 {case_id}: godkendt af bruger {g['G2'].get('tid')} ({len(g['G2'].get('design') or [])} fagleverancer)")
            return 0
        if cmd == "reset" and args:
            removed = s["leverancer"].pop(args[0], None)
            save(d, s)
            log(d, haendelse="nulstillet", leverance=args[0])
            print("Nulstillet." if removed else "Ukendt leverance-ID.")
            return 0
    print(__doc__)
    return 1


def manual_merge(f: pathlib.Path, args: list) -> int:
    """The project manager (or the user) merges a proposal by hand, e.g. after a conflict."""
    if not f.is_file() or f.parent.name != "forslag":
        print(f"Ikke et forslag: {f} (forventet <sagsmappe>/forslag/<fag>-<nr>__<mål>.md)")
        return 1
    case_dir = f.parent.parent
    r = case_merge.merge(f, case_dir, dry_run="--dry-run" in args, force="--force" in args)
    print(r["besked"])
    if r["ok"] and "--dry-run" not in args:
        root = case_git.root_for(case_dir)
        if root:
            case_git.commit(root, f"flet {f.name} (manuelt)")
    return 0 if r["ok"] else 1


def main() -> int:
    cmd = sys.argv[1] if len(sys.argv) > 1 else ""
    if cmd == "merge" and len(sys.argv) > 2:
        return manual_merge(pathlib.Path(sys.argv[2]).expanduser().resolve(), sys.argv[3:])
    if cmd in ("status", "reset", "help"):
        return manual(cmd, sys.argv[2:])
    try:
        raw = sys.stdin.read()
        inp = json.loads(raw) if raw.strip() else {}
        handler = {"pretool": pretool, "subagentstop": subagentstop, "stop": stop, "protect": protect,
                   "prompt": user_prompt, "workflow": workflow, "precompact": precompact, "after_compact": after_compact}.get(cmd)
        if handler:
            handler(inp, data_dir())
    except Exception:
        try:
            log(data_dir(), haendelse="hookfejl", kommando=cmd, fejl=traceback.format_exc()[-800:])
        except Exception:
            pass
    return 0


if __name__ == "__main__":
    sys.exit(main())
