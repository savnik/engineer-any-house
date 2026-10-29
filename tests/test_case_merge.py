#!/usr/bin/env python3
"""Tests one writer per file: write permission per trade, proposals and merging, and git version control of byg-cases/.

Run:  python3 tests/test_case_merge.py
"""
import json
import os
import pathlib
import shutil
import subprocess
import sys
import tempfile

ROOT = pathlib.Path(__file__).resolve().parent.parent
HOOKS = ROOT / "plugins" / "byg-review" / "hooks"
GATE = HOOKS / "review_gate.py"
sys.path.insert(0, str(HOOKS))
import case_merge  # noqa: E402
import case_git  # noqa: E402

ERRORS = []

INTERFACES = """# Grænseflader
## Register
| ID | Fra | Til | Hvad | Ejer |
|---|---|---|---|---|
| G-01 | vvs | el | Strøm til varmepumpe | el |
| G-02 | vvs | murer | Gennemføring i ydervæg | murer |

## Noter
Fri tekst.
"""
CARD = """# Ejendomskort – test
## Fælles (alle fag)
| ID | Emne | Værdi | Dato | Kilde |
|---|---|---|---|---|
| E-F-01 | Opførelsesår | 1970 | 2026-01-01 | D BBR |

## VVS og varme
| ID | Emne | Værdi | Dato | Kilde |
|---|---|---|---|---|
| E-VVS-01 | Varmekilde | Oliefyr | 2026-01-01 | B |

## Erstattede oplysninger
| ID | Tidligere værdi | Erstattet (dato) | Grund |
|---|---|---|---|
"""


def check(name: str, ok: bool, info="") -> None:
    print(("OK   " if ok else "FEJL ") + name + ("" if ok else f"  → {info}"))
    if not ok:
        ERRORS.append(name)


def call(event: str, data: dict, env: dict):
    r = subprocess.run([sys.executable, str(GATE), event], input=json.dumps(data), text=True,
                       capture_output=True, env=env, timeout=60)
    assert r.returncode == 0, r.stderr
    return json.loads(r.stdout) if r.stdout.strip() else None


def denied(r) -> bool:
    return bool(r) and r.get("hookSpecificOutput", {}).get("permissionDecision") == "deny"


def transcript(prompt: str) -> str:
    fd, path = tempfile.mkstemp(suffix=".jsonl")
    with os.fdopen(fd, "w", encoding="utf-8") as fh:
        fh.write(json.dumps({"message": {"role": "user", "content": prompt}}) + "\n")
        fh.write(json.dumps({"message": {"role": "assistant", "content": [{"type": "text", "text": "ok"}]}}))
    return path


def git(root: pathlib.Path, *args) -> str:
    return subprocess.run(["git", "-C", str(root), *args], capture_output=True, text=True).stdout


def test_merge_unit(tmp: pathlib.Path) -> None:
    case_dir = tmp / "enhed" / "byg-cases" / "2026-10-01-x"
    (case_dir / "proposals").mkdir(parents=True)
    (case_dir / "interfaces.md").write_text(INTERFACES, encoding="utf-8")
    f = case_dir / "proposals" / "plumbing-01__interfaces.md"
    case_merge.save_base(f, case_dir)
    f.write_text("# Forslag\n## Register\n| ID | Fra | Til | Hvad | Ejer |\n|---|---|---|---|---|\n"
                 "| G-02 | vvs | murer | Gennemføring Ø110 i ydervæg | murer |\n| G-03 | vvs | ventilation | Afkast | vent |\n",
                 encoding="utf-8")
    r = case_merge.merge(f, case_dir, "2026-10-01-x/plumbing/01")
    t = (case_dir / "interfaces.md").read_text(encoding="utf-8")
    check("flet: ændret og ny række", r["ok"] and r["aendret"] == ["G-02"] and r["nye"] == ["G-03"], r)
    check("flet: ny række sidst i afsnittets tabel, resten urørt",
         t.index("G-03") > t.index("G-02") and t.index("G-03") < t.index("## Noter") and "Fri tekst." in t
         and "Strøm til varmepumpe" in t, t)
    check("flet: forslaget flyttes til flettet/ og logges",
         not f.exists() and (case_dir / "proposals" / "merged" / f.name).exists() and (case_dir / "proposals" / "merge-log.md").exists())

    # Conflict: the project manager changed G-01 after the proposal was written
    f2 = case_dir / "proposals" / "electrical-02__interfaces.md"
    case_merge.save_base(f2, case_dir)
    (case_dir / "interfaces.md").write_text(t.replace("Strøm til varmepumpe", "Strøm 3x16 A til varmepumpe"), encoding="utf-8")
    f2.write_text("## Register\n| ID | Fra | Til | Hvad | Ejer |\n|---|---|---|---|---|\n"
                  "| G-01 | vvs | el | Strøm 1x10 A | el |\n", encoding="utf-8")
    before = (case_dir / "interfaces.md").read_text(encoding="utf-8")
    r = case_merge.merge(f2, case_dir, "x/electrical/02")
    check("flet: konflikt skriver intet", not r["ok"] and r["konflikter"] == ["G-01"]
         and (case_dir / "interfaces.md").read_text(encoding="utf-8") == before and f2.exists(), r)
    r = case_merge.merge(f2, case_dir, "x/electrical/02", force=True)
    check("flet: --force tilsidesætter konflikten", r["ok"] and "1x10 A" in (case_dir / "interfaces.md").read_text(encoding="utf-8"), r)

    # The same change in both places is not a conflict
    f3 = case_dir / "proposals" / "masonry-01__interfaces.md"
    case_merge.save_base(f3, case_dir)
    line = "| G-02 | vvs | murer | Kerneboring | murer |"
    g = (case_dir / "interfaces.md").read_text(encoding="utf-8").split("\n")
    g = [line if l.startswith("| G-02") else l for l in g]
    (case_dir / "interfaces.md").write_text("\n".join(g), encoding="utf-8")
    f3.write_text("## Register\n| ID | Fra | Til | Hvad | Ejer |\n|---|---|---|---|---|\n" + line + "\n", encoding="utf-8")
    r = case_merge.merge(f3, case_dir)
    check("flet: identisk ændring begge steder er ingen konflikt", r["ok"], r)

    # Only the project manager changes the owner of an interface
    f7 = case_dir / "proposals" / "electrical-03__interfaces.md"
    f7.write_text("## Register\n| ID | Fra | Til | Hvad | Ejer |\n|---|---|---|---|---|\n| G-01 | vvs | el | Strøm 1x10 A | vvs |\n",
                  encoding="utf-8")
    r = case_merge.merge(f7, case_dir)
    check("flet: forslag må ikke ændre ejeren", not r["ok"] and "ejeren" in r["besked"], r)

    # Unknown section and wrong column count
    f4 = case_dir / "proposals" / "plumbing-02__interfaces.md"
    f4.write_text("## Andet\n| ID | A |\n|---|---|\n| G-09 | x |\n", encoding="utf-8")
    r = case_merge.merge(f4, case_dir)
    check("flet: ukendt afsnit afvises", not r["ok"] and "Andet" in r["besked"], r)

    # Property card: a changed value is moved to Erstattede oplysninger
    (case_dir.parent / "properties").mkdir()
    (case_dir.parent / "properties" / "test.md").write_text(CARD, encoding="utf-8")
    (case_dir / "project-basis.md").write_text("# PG\n**Ejendom:** byg-cases/properties/test.md\n", encoding="utf-8")
    f5 = case_dir / "proposals" / "plumbing-03__property-card.md"
    case_merge.save_base(f5, case_dir)
    f5.write_text("## VVS og varme\n| ID | Emne | Værdi | Dato | Kilde |\n|---|---|---|---|---|\n"
                  "| E-VVS-01 | Varmekilde | Luft/vand-varmepumpe | 2026-10-01 | F |\n", encoding="utf-8")
    r = case_merge.merge(f5, case_dir, "x/plumbing/03")
    k = (case_dir.parent / "properties" / "test.md").read_text(encoding="utf-8")
    check("flet: ejendomskort findes via projektgrundlaget, gammel værdi bevares",
         r["ok"] and "| E-VVS-01 | Oliefyr |" in k and "Luft/vand-varmepumpe" in k, (r, k))

    # Same item corrected again: the history row with the same ID must not be mistaken for the live row
    f5b = case_dir / "proposals" / "plumbing-05__property-card.md"
    case_merge.save_base(f5b, case_dir)
    f5b.write_text("## VVS og varme\n| ID | Emne | Værdi | Dato | Kilde |\n|---|---|---|---|---|\n"
                   "| E-VVS-01 | Varmekilde | Jordvarme | 2026-10-05 | D |\n", encoding="utf-8")
    r = case_merge.merge(f5b, case_dir, "x/plumbing/05")
    k = (case_dir.parent / "properties" / "test.md").read_text(encoding="utf-8")
    check("flet: anden rettelse af samme ID i ejendomskortet",
         r["ok"] and "| E-VVS-01 | Varmekilde | Jordvarme |" in k and "| E-VVS-01 | Oliefyr |" in k
         and "| E-VVS-01 | Luft/vand-varmepumpe |" in k, (r, k))

    # A generated property card (from the BIM model) is never edited here
    (case_dir.parent / "properties" / "test.md").write_text("<!-- GENERATED fra model.yaml -->\n" + CARD, encoding="utf-8")
    f6 = case_dir / "proposals" / "plumbing-04__property-card.md"
    f6.write_text("## VVS og varme\n| ID | Emne | Værdi | Dato | Kilde |\n|---|---|---|---|---|\n| E-VVS-02 | x | y | z | B |\n",
                  encoding="utf-8")
    r = case_merge.merge(f6, case_dir)
    check("flet: genereret ejendomskort afvises", not r["ok"] and "bim.py merge" in r["besked"], r)


def test_git_lock(tmp: pathlib.Path) -> None:
    root = tmp / "lock" / "byg-cases"
    (root / "s").mkdir(parents=True)
    (root / "s" / "a.md").write_text("a\n", encoding="utf-8")
    check("git: første commit", bool(case_git.commit(root, "første")))
    (root / ".git" / "index.lock").write_text("", encoding="utf-8")
    (root / "s" / "a.md").write_text("b\n", encoding="utf-8")
    old, case_git.BUDGET_SEC = case_git.BUDGET_SEC, 3
    try:
        case_git.commit(root, "anden")
        check("git: fremmed index.lock giver en fejl inden for budgettet", False, "ingen fejl")
    except case_git.GitError:
        check("git: fremmed index.lock giver en fejl inden for budgettet", True)
    finally:
        case_git.BUDGET_SEC = old
    (root / ".git" / "index.lock").unlink()
    check("git: næste commit tager ændringen med", bool(case_git.commit(root, "tredje"))
         and "b" in git(root, "show", "HEAD:s/a.md"))


def test_hook(tmp: pathlib.Path) -> None:
    env = dict(os.environ, CLAUDE_PLUGIN_DATA=str(tmp / "data"))
    cwd = tmp / "projekt"
    bs = cwd / "byg-cases"
    case_dir = bs / "2026-10-02-bad"
    (case_dir / "trade-notes").mkdir(parents=True)
    (bs / "properties").mkdir()
    (case_dir / "interfaces.md").write_text(INTERFACES, encoding="utf-8")
    (case_dir / "project-basis.md").write_text("# PG\n", encoding="utf-8")
    S = {"session_id": "s1", "cwd": str(cwd)}
    VVS = {**S, "agent_type": "byg-plumbing:plumber", "agent_id": "a1"}

    def write(data, path):
        return call("protect", {**data, "tool_name": "Write", "tool_input": {"file_path": str(path)}}, env)

    check("skriveret: fagagent må skrive sit eget notat", not denied(write(VVS, case_dir / "trade-notes" / "plumbing.md")))
    check("skriveret: fagagent må skrive sit bilag", not denied(write(VVS, case_dir / "trade-notes" / "plumbing-bilag.md")))
    check("skriveret: fagagent må ikke skrive et andet fags notat", denied(write(VVS, case_dir / "trade-notes" / "electrical.md")))
    check("skriveret: fagagent må ikke skrive projektgrundlaget", denied(write(VVS, case_dir / "project-basis.md")))
    check("skriveret: fagagent må ikke skrive grænsefladeregistret", denied(write(VVS, case_dir / "interfaces.md")))
    check("skriveret: fagagent må ikke skrive ejendomskortet", denied(write(VVS, bs / "properties" / "x.md")))
    check("skriveret: forslag med ukendt mål afvises", denied(write(VVS, case_dir / "proposals" / "plumbing-01__budget.md")))
    check("skriveret: forslag til et andet fags navn afvises", denied(write(VVS, case_dir / "proposals" / "electrical-01__interfaces.md")))
    check("skriveret: '..' i stien snyder ikke", denied(write(VVS, case_dir / "attachments" / "plumbing" / ".." / ".." / "status.md")))
    check("skriveret: forslag uden igangværende leverance afvises",
         denied(write(VVS, case_dir / "proposals" / "plumbing-09__interfaces.md")))
    check("skriveret: hovedtråden må skrive alt", not denied(write(S, case_dir / "project-basis.md")))
    check("skriveret: projektleder som hovedagent må skrive alt",
         not denied(write({**S, "agent_type": "byg:project-manager"}, case_dir / "interfaces.md")))
    check("skriveret: filer uden for byg-cases påvirkes ikke", not denied(write(VVS, tmp / "hukommelse" / "MEMORY.md")))
    STAT = {**S, "agent_type": "byg-structural:structural-engineer"}
    check("skriveret: statiker må skrive fem/", not denied(write(STAT, case_dir / "fem" / "fem.yaml")))
    BIM = {**S, "agent_type": "byg-bim:bim-modeller"}
    check("skriveret: bim må oprette hovedmodellen", not denied(write(BIM, case_dir / "bim" / "model.yaml")))
    (case_dir / "bim").mkdir()
    (case_dir / "bim" / "model.yaml").write_text("x: 1\n", encoding="utf-8")
    check("skriveret: bim må ikke rette en eksisterende hovedmodel", denied(write(BIM, case_dir / "bim" / "model.yaml")))
    check("skriveret: bim må skrive forslag", not denied(write(BIM, case_dir / "bim" / "proposals" / "bim-02.yaml")))

    # Full flow: trade call → proposal → handoff → rejected → correction → approved → merged and committed
    L = "2026-10-02-bad/plumbing/01"
    call("pretool", {**S, "tool_input": {"subagent_type": "byg-plumbing:plumber", "prompt": f"DELIVERABLE: {L}\nopgave"}}, env)
    note = case_dir / "trade-notes" / "plumbing.md"
    note.write_text("# Fagnotat – vvs\nLøsning: A\n", encoding="utf-8")
    proposal = case_dir / "proposals" / "plumbing-01__interfaces.md"
    check("skriveret: fagagent må skrive sit forslag", not denied(write(VVS, proposal)))
    check("forslag: basis gemt ved første skrivning", (case_dir / "proposals" / ".base" / proposal.name).exists())
    proposal.write_text("## Register\n| ID | Fra | Til | Hvad | Ejer |\n|---|---|---|---|---|\n"
                       "| G-03 | vvs | ventilation | Emhætte og erstatningsluft | ventilation |\n", encoding="utf-8")
    stop_trade = {**S, "agent_type": "byg-plumbing:plumber", "agent_transcript_path": transcript(f"DELIVERABLE: {L}")}
    call("subagentstop", stop_trade, env)
    check("git: byg-cases er et git-repo efter første aflevering", (bs / ".git").is_dir() and (bs / ".gitignore").is_file())
    check("git: fagaflevering committet med leverance-ID", f"{L}: fagaflevering" in git(bs, "log", "--format=%s"))
    check("git: fagaflevering committer kun fagets filer",
         "trade-notes/plumbing.md" in git(bs, "ls-files") and "project-basis.md" not in git(bs, "ls-files"),
         git(bs, "ls-files"))

    def verdict(outcome):
        findings = [] if outcome == "godkendt" else [{"id": "F1", "klasse": "væsentlig", "status": "nyt", "krav": "k",
                                                  "kilde": "s", "evidens": "e", "handling": "h"}]
        chunk = {"leverance_id": L, "fag": "plumbing", "dom": outcome, "fund": findings, "sagsmappe": str(case_dir)}
        return "ok\n```json\n" + json.dumps(chunk, ensure_ascii=False) + "\n```"

    REVIEW = {**S, "tool_input": {"subagent_type": "byg-review:plumbing-review", "prompt": f"DELIVERABLE: {L}"}}
    call("pretool", REVIEW, env)
    call("subagentstop", {**S, "agent_type": "byg-review:plumbing-review", "last_assistant_message": verdict("afvist")}, env)
    check("afvist: forslaget flettes ikke", proposal.exists() and "G-03" not in (case_dir / "interfaces.md").read_text(encoding="utf-8"))
    check("git: dommen committet", f"{L}: dom afvist" in git(bs, "log", "--format=%s"))

    call("pretool", {**S, "tool_input": {"subagent_type": "byg-plumbing:plumber", "prompt": f"DELIVERABLE: {L}\nret F1"}}, env)
    note.write_text("# Fagnotat – vvs\nLøsning: B (rettet efter F1)\n", encoding="utf-8")
    call("subagentstop", stop_trade, env)
    diff = case_dir / "quality" / "2026-10-02-bad__plumbing__01__changes.diff"
    check("diff: ændringer siden den kontrollerede version til forsøg 2",
         diff.exists() and "-Løsning: A" in diff.read_text(encoding="utf-8") and "+Løsning: B" in diff.read_text(encoding="utf-8"))

    # The project manager updates the register meanwhile (another row) – no conflict
    g = (case_dir / "interfaces.md").read_text(encoding="utf-8").replace("Gennemføring i ydervæg", "Gennemføring Ø110")
    (case_dir / "interfaces.md").write_text(g, encoding="utf-8")
    call("pretool", REVIEW, env)
    call("subagentstop", {**S, "agent_type": "byg-review:plumbing-review", "last_assistant_message": verdict("godkendt")}, env)
    g = (case_dir / "interfaces.md").read_text(encoding="utf-8")
    check("godkendt: forslaget flettes ind, projektlederens ændring bevares",
         "Emhætte og erstatningsluft" in g and "Gennemføring Ø110" in g and not proposal.exists(), g)
    check("git: dom og fletning committet", "dom godkendt (runde 1, forsøg 2), 1 forslag flettet" in git(bs, "log", "--format=%s"),
         git(bs, "log", "--format=%s"))
    check("stop: ingen konflikter at rapportere", call("stop", S, env) is None)
    check("git: hovedtrådens ændringer committes ved Stop",
         "project-basis.md" in git(bs, "ls-files") and git(bs, "status", "--porcelain").strip() == "",
         git(bs, "status", "--porcelain"))

    # Conflict on approval → Stop blocks with guidance; resolved conflict → Stop is satisfied
    L2 = "2026-10-02-bad/plumbing/02"
    call("pretool", {**S, "tool_input": {"subagent_type": "byg-plumbing:plumber", "prompt": f"DELIVERABLE: {L2}\nopgave"}}, env)
    f2 = case_dir / "proposals" / "plumbing-02__interfaces.md"
    write(VVS, f2)
    f2.write_text("## Register\n| ID | Fra | Til | Hvad | Ejer |\n|---|---|---|---|---|\n| G-01 | vvs | el | 1x10 A | el |\n",
                  encoding="utf-8")
    call("subagentstop", {**S, "agent_type": "byg-plumbing:plumber", "agent_transcript_path": transcript(f"DELIVERABLE: {L2}")}, env)
    (case_dir / "interfaces.md").write_text((case_dir / "interfaces.md").read_text(encoding="utf-8")
                                         .replace("Strøm til varmepumpe", "Strøm 3x16 A"), encoding="utf-8")
    call("pretool", {**S, "tool_input": {"subagent_type": "byg-review:plumbing-review", "prompt": f"DELIVERABLE: {L2}"}}, env)
    chunk = {"leverance_id": L2, "fag": "plumbing", "dom": "godkendt", "fund": [], "sagsmappe": str(case_dir)}
    call("subagentstop", {**S, "agent_type": "byg-review:plumbing-review",
                          "last_assistant_message": "```json\n" + json.dumps(chunk) + "\n```"}, env)
    r = call("stop", S, env)
    check("konflikt: Stop blokerer med vejledning", bool(r) and r.get("decision") == "block" and "G-01" in r.get("reason", ""), r)
    m = subprocess.run([sys.executable, str(GATE), "merge", str(f2), "--force"], capture_output=True, text=True, env=env)
    check("manuel merge --force", m.returncode == 0 and "1x10 A" in (case_dir / "interfaces.md").read_text(encoding="utf-8"), m.stdout)
    check("konflikt løst: Stop er tilfreds", call("stop", S, env) is None)

    # The base is saved when the trade call starts: a change landing before the trade agent writes the proposal gives a conflict
    L4 = "2026-10-02-bad/plumbing/04"
    call("pretool", {**S, "tool_input": {"subagent_type": "byg-plumbing:plumber", "prompt": f"DELIVERABLE: {L4}\nopgave"}}, env)
    check("basis: gemt ved fagkaldets start", (case_dir / "proposals" / ".base" / "plumbing-04__interfaces.md").exists())
    (case_dir / "interfaces.md").write_text((case_dir / "interfaces.md").read_text(encoding="utf-8")
                                         .replace("Emhætte og erstatningsluft", "Emhætte 600 m³/h"), encoding="utf-8")
    f4 = case_dir / "proposals" / "plumbing-04__interfaces.md"
    check("skriveret: forslag til igangværende leverance tilladt", not denied(write(VVS, f4)))
    f4.write_text("## Register\n| ID | Fra | Til | Hvad | Ejer |\n|---|---|---|---|---|\n"
                  "| G-03 | vvs | ventilation | Emhætte 400 m³/h | ventilation |\n", encoding="utf-8")
    call("subagentstop", {**S, "agent_type": "byg-plumbing:plumber", "agent_transcript_path": transcript(f"DELIVERABLE: {L4}")}, env)
    call("pretool", {**S, "tool_input": {"subagent_type": "byg-review:plumbing-review", "prompt": f"DELIVERABLE: {L4}"}}, env)
    chunk = {"leverance_id": L4, "fag": "plumbing", "dom": "godkendt", "fund": [], "sagsmappe": str(case_dir)}
    call("subagentstop", {**S, "agent_type": "byg-review:plumbing-review",
                          "last_assistant_message": "```json\n" + json.dumps(chunk) + "\n```"}, env)
    check("basis: ændring mellem fagkald og forslag giver konflikt, ikke overskrivning",
         "600 m³/h" in (case_dir / "interfaces.md").read_text(encoding="utf-8") and f4.exists())
    f4.unlink()
    call("stop", S, env)

    # BIM: the main model (changed via bim.py) is included in the trade handoff commit
    L5 = "2026-10-02-bad/bim/01"
    call("pretool", {**S, "tool_input": {"subagent_type": "byg-bim:bim-modeller", "prompt": f"DELIVERABLE: {L5}"}}, env)
    (case_dir / "bim" / "model.yaml").write_text("x: 2\n", encoding="utf-8")
    call("subagentstop", {**S, "agent_type": "byg-bim:bim-modeller", "agent_transcript_path": transcript(f"DELIVERABLE: {L5}")}, env)
    last = git(bs, "log", "-1", "--name-only", "--format=%s")
    check("git: BIM-hovedmodellen med i fagafleveringen", f"{L5}: fagaflevering" in last and "bim/model.yaml" in last, last)

    # BYG_GIT=0 disables version control
    tmp2 = tmp / "uden-git" / "byg-cases" / "2026-10-03-y"
    (tmp2 / "trade-notes").mkdir(parents=True)
    env2 = dict(env, BYG_GIT="0", CLAUDE_PLUGIN_DATA=str(tmp / "data2"))
    S2 = {"session_id": "s2", "cwd": str(tmp / "uden-git")}
    L3 = "2026-10-03-y/plumbing/01"
    call("pretool", {**S2, "tool_input": {"subagent_type": "byg-plumbing:plumber", "prompt": f"DELIVERABLE: {L3}"}}, env2)
    call("subagentstop", {**S2, "agent_type": "byg-plumbing:plumber", "agent_transcript_path": transcript(f"DELIVERABLE: {L3}")}, env2)
    check("BYG_GIT=0: intet git-repo", not (tmp / "uden-git" / "byg-cases" / ".git").exists())

    # The hook is fail-safe and hides errors – the log must have none
    errors = [l for d in ("data", "data2") for l in (tmp / d / "review" / "log.jsonl").read_text(encoding="utf-8").splitlines()
            if json.loads(l).get("haendelse") in ("hookfejl", "git_fejl", "flet_fejl", "diff_fejl", "domfil_fejl")]
    check("ingen skjulte hookfejl i loggen", not errors, errors)


def main() -> int:
    if not shutil.which("git"):
        print("git findes ikke – springer over")
        return 0
    with tempfile.TemporaryDirectory() as t:
        tmp = pathlib.Path(t)
        test_merge_unit(tmp)
        test_git_lock(tmp)
        test_hook(tmp)
    print("\nALLE TESTS BESTÅET" if not ERRORS else f"\n{len(ERRORS)} FEJL")
    return 1 if ERRORS else 0


if __name__ == "__main__":
    sys.exit(main())
