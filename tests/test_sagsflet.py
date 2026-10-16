#!/usr/bin/env python3
"""Tester én skriver pr. fil: skriveret pr. fag, forslag og fletning, og git-revisionsstyring af byg-sager/.

Kør:  python3 tests/test_sagsflet.py
"""
import json
import os
import pathlib
import shutil
import subprocess
import sys
import tempfile

ROD = pathlib.Path(__file__).resolve().parent.parent
HOOKS = ROD / "plugins" / "byg-kontrol" / "hooks"
GATE = HOOKS / "kontrol_gate.py"
sys.path.insert(0, str(HOOKS))
import sagsflet  # noqa: E402
import sagsgit  # noqa: E402

FEJL = []

GRAENSEFLADER = """# Grænseflader
## Register
| ID | Fra | Til | Hvad | Ejer |
|---|---|---|---|---|
| G-01 | vvs | el | Strøm til varmepumpe | el |
| G-02 | vvs | murer | Gennemføring i ydervæg | murer |

## Noter
Fri tekst.
"""
KORT = """# Ejendomskort – test
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


def tjek(navn: str, ok: bool, info="") -> None:
    print(("OK   " if ok else "FEJL ") + navn + ("" if ok else f"  → {info}"))
    if not ok:
        FEJL.append(navn)


def kald(hændelse: str, data: dict, env: dict):
    r = subprocess.run([sys.executable, str(GATE), hændelse], input=json.dumps(data), text=True,
                       capture_output=True, env=env, timeout=60)
    assert r.returncode == 0, r.stderr
    return json.loads(r.stdout) if r.stdout.strip() else None


def afvist(r) -> bool:
    return bool(r) and r.get("hookSpecificOutput", {}).get("permissionDecision") == "deny"


def transkript(prompt: str) -> str:
    fd, sti = tempfile.mkstemp(suffix=".jsonl")
    with os.fdopen(fd, "w", encoding="utf-8") as fh:
        fh.write(json.dumps({"message": {"role": "user", "content": prompt}}) + "\n")
        fh.write(json.dumps({"message": {"role": "assistant", "content": [{"type": "text", "text": "ok"}]}}))
    return sti


def git(rod: pathlib.Path, *args) -> str:
    return subprocess.run(["git", "-C", str(rod), *args], capture_output=True, text=True).stdout


def test_flet_enhed(tmp: pathlib.Path) -> None:
    sm = tmp / "enhed" / "byg-sager" / "2026-10-01-x"
    (sm / "forslag").mkdir(parents=True)
    (sm / "graenseflader.md").write_text(GRAENSEFLADER, encoding="utf-8")
    f = sm / "forslag" / "vvs-01__graenseflader.md"
    sagsflet.gem_basis(f, sm)
    f.write_text("# Forslag\n## Register\n| ID | Fra | Til | Hvad | Ejer |\n|---|---|---|---|---|\n"
                 "| G-02 | vvs | murer | Gennemføring Ø110 i ydervæg | murer |\n| G-03 | vvs | ventilation | Afkast | vent |\n",
                 encoding="utf-8")
    r = sagsflet.flet(f, sm, "2026-10-01-x/vvs/01")
    t = (sm / "graenseflader.md").read_text(encoding="utf-8")
    tjek("flet: ændret og ny række", r["ok"] and r["aendret"] == ["G-02"] and r["nye"] == ["G-03"], r)
    tjek("flet: ny række sidst i afsnittets tabel, resten urørt",
         t.index("G-03") > t.index("G-02") and t.index("G-03") < t.index("## Noter") and "Fri tekst." in t
         and "Strøm til varmepumpe" in t, t)
    tjek("flet: forslaget flyttes til flettet/ og logges",
         not f.exists() and (sm / "forslag" / "flettet" / f.name).exists() and (sm / "forslag" / "flettelog.md").exists())

    # Konflikt: projektlederen har ændret G-01, efter forslaget blev skrevet
    f2 = sm / "forslag" / "el-02__graenseflader.md"
    sagsflet.gem_basis(f2, sm)
    (sm / "graenseflader.md").write_text(t.replace("Strøm til varmepumpe", "Strøm 3x16 A til varmepumpe"), encoding="utf-8")
    f2.write_text("## Register\n| ID | Fra | Til | Hvad | Ejer |\n|---|---|---|---|---|\n"
                  "| G-01 | vvs | el | Strøm 1x10 A | el |\n", encoding="utf-8")
    før = (sm / "graenseflader.md").read_text(encoding="utf-8")
    r = sagsflet.flet(f2, sm, "x/el/02")
    tjek("flet: konflikt skriver intet", not r["ok"] and r["konflikter"] == ["G-01"]
         and (sm / "graenseflader.md").read_text(encoding="utf-8") == før and f2.exists(), r)
    r = sagsflet.flet(f2, sm, "x/el/02", tving=True)
    tjek("flet: --tving tilsidesætter konflikten", r["ok"] and "1x10 A" in (sm / "graenseflader.md").read_text(encoding="utf-8"), r)

    # Samme ændring begge steder er ikke en konflikt
    f3 = sm / "forslag" / "murer-01__graenseflader.md"
    sagsflet.gem_basis(f3, sm)
    linje = "| G-02 | vvs | murer | Kerneboring | murer |"
    g = (sm / "graenseflader.md").read_text(encoding="utf-8").split("\n")
    g = [linje if l.startswith("| G-02") else l for l in g]
    (sm / "graenseflader.md").write_text("\n".join(g), encoding="utf-8")
    f3.write_text("## Register\n| ID | Fra | Til | Hvad | Ejer |\n|---|---|---|---|---|\n" + linje + "\n", encoding="utf-8")
    r = sagsflet.flet(f3, sm)
    tjek("flet: identisk ændring begge steder er ingen konflikt", r["ok"], r)

    # Ejeren af en snitflade ændres kun af projektlederen
    f7 = sm / "forslag" / "el-03__graenseflader.md"
    f7.write_text("## Register\n| ID | Fra | Til | Hvad | Ejer |\n|---|---|---|---|---|\n| G-01 | vvs | el | Strøm 1x10 A | vvs |\n",
                  encoding="utf-8")
    r = sagsflet.flet(f7, sm)
    tjek("flet: forslag må ikke ændre ejeren", not r["ok"] and "ejeren" in r["besked"], r)

    # Ukendt afsnit og forkert kolonnetal
    f4 = sm / "forslag" / "vvs-02__graenseflader.md"
    f4.write_text("## Andet\n| ID | A |\n|---|---|\n| G-09 | x |\n", encoding="utf-8")
    r = sagsflet.flet(f4, sm)
    tjek("flet: ukendt afsnit afvises", not r["ok"] and "Andet" in r["besked"], r)

    # Ejendomskort: ændret værdi flyttes til Erstattede oplysninger
    (sm.parent / "ejendomme").mkdir()
    (sm.parent / "ejendomme" / "test.md").write_text(KORT, encoding="utf-8")
    (sm / "projektgrundlag.md").write_text("# PG\n**Ejendom:** byg-sager/ejendomme/test.md\n", encoding="utf-8")
    f5 = sm / "forslag" / "vvs-03__ejendomskort.md"
    sagsflet.gem_basis(f5, sm)
    f5.write_text("## VVS og varme\n| ID | Emne | Værdi | Dato | Kilde |\n|---|---|---|---|---|\n"
                  "| E-VVS-01 | Varmekilde | Luft/vand-varmepumpe | 2026-10-01 | F |\n", encoding="utf-8")
    r = sagsflet.flet(f5, sm, "x/vvs/03")
    k = (sm.parent / "ejendomme" / "test.md").read_text(encoding="utf-8")
    tjek("flet: ejendomskort findes via projektgrundlaget, gammel værdi bevares",
         r["ok"] and "| E-VVS-01 | Oliefyr |" in k and "Luft/vand-varmepumpe" in k, (r, k))

    # Samme oplysning rettet igen: historikrækken med samme ID må ikke forveksles med den levende række
    f5b = sm / "forslag" / "vvs-05__ejendomskort.md"
    sagsflet.gem_basis(f5b, sm)
    f5b.write_text("## VVS og varme\n| ID | Emne | Værdi | Dato | Kilde |\n|---|---|---|---|---|\n"
                   "| E-VVS-01 | Varmekilde | Jordvarme | 2026-10-05 | D |\n", encoding="utf-8")
    r = sagsflet.flet(f5b, sm, "x/vvs/05")
    k = (sm.parent / "ejendomme" / "test.md").read_text(encoding="utf-8")
    tjek("flet: anden rettelse af samme ID i ejendomskortet",
         r["ok"] and "| E-VVS-01 | Varmekilde | Jordvarme |" in k and "| E-VVS-01 | Oliefyr |" in k
         and "| E-VVS-01 | Luft/vand-varmepumpe |" in k, (r, k))

    # Genereret ejendomskort (fra BIM-modellen) rettes aldrig her
    (sm.parent / "ejendomme" / "test.md").write_text("<!-- GENERERET fra model.yaml -->\n" + KORT, encoding="utf-8")
    f6 = sm / "forslag" / "vvs-04__ejendomskort.md"
    f6.write_text("## VVS og varme\n| ID | Emne | Værdi | Dato | Kilde |\n|---|---|---|---|---|\n| E-VVS-02 | x | y | z | B |\n",
                  encoding="utf-8")
    r = sagsflet.flet(f6, sm)
    tjek("flet: genereret ejendomskort afvises", not r["ok"] and "bim.py flet" in r["besked"], r)


def test_git_laas(tmp: pathlib.Path) -> None:
    rod = tmp / "laas" / "byg-sager"
    (rod / "s").mkdir(parents=True)
    (rod / "s" / "a.md").write_text("a\n", encoding="utf-8")
    tjek("git: første commit", bool(sagsgit.commit(rod, "første")))
    (rod / ".git" / "index.lock").write_text("", encoding="utf-8")
    (rod / "s" / "a.md").write_text("b\n", encoding="utf-8")
    gammelt, sagsgit.BUDGET_SEK = sagsgit.BUDGET_SEK, 3
    try:
        sagsgit.commit(rod, "anden")
        tjek("git: fremmed index.lock giver en fejl inden for budgettet", False, "ingen fejl")
    except sagsgit.GitFejl:
        tjek("git: fremmed index.lock giver en fejl inden for budgettet", True)
    finally:
        sagsgit.BUDGET_SEK = gammelt
    (rod / ".git" / "index.lock").unlink()
    tjek("git: næste commit tager ændringen med", bool(sagsgit.commit(rod, "tredje"))
         and "b" in git(rod, "show", "HEAD:s/a.md"))


def test_hook(tmp: pathlib.Path) -> None:
    env = dict(os.environ, CLAUDE_PLUGIN_DATA=str(tmp / "data"))
    cwd = tmp / "projekt"
    bs = cwd / "byg-sager"
    sm = bs / "2026-10-02-bad"
    (sm / "fagnotater").mkdir(parents=True)
    (bs / "ejendomme").mkdir()
    (sm / "graenseflader.md").write_text(GRAENSEFLADER, encoding="utf-8")
    (sm / "projektgrundlag.md").write_text("# PG\n", encoding="utf-8")
    S = {"session_id": "s1", "cwd": str(cwd)}
    VVS = {**S, "agent_type": "byg-vvs:vvs-mester", "agent_id": "a1"}

    def skriv(data, sti):
        return kald("beskyt", {**data, "tool_name": "Write", "tool_input": {"file_path": str(sti)}}, env)

    tjek("skriveret: fagagent må skrive sit eget notat", not afvist(skriv(VVS, sm / "fagnotater" / "vvs.md")))
    tjek("skriveret: fagagent må skrive sit bilag", not afvist(skriv(VVS, sm / "fagnotater" / "vvs-bilag.md")))
    tjek("skriveret: fagagent må ikke skrive et andet fags notat", afvist(skriv(VVS, sm / "fagnotater" / "el.md")))
    tjek("skriveret: fagagent må ikke skrive projektgrundlaget", afvist(skriv(VVS, sm / "projektgrundlag.md")))
    tjek("skriveret: fagagent må ikke skrive grænsefladeregistret", afvist(skriv(VVS, sm / "graenseflader.md")))
    tjek("skriveret: fagagent må ikke skrive ejendomskortet", afvist(skriv(VVS, bs / "ejendomme" / "x.md")))
    tjek("skriveret: forslag med ukendt mål afvises", afvist(skriv(VVS, sm / "forslag" / "vvs-01__budget.md")))
    tjek("skriveret: forslag til et andet fags navn afvises", afvist(skriv(VVS, sm / "forslag" / "el-01__graenseflader.md")))
    tjek("skriveret: '..' i stien snyder ikke", afvist(skriv(VVS, sm / "bilag" / "vvs" / ".." / ".." / "status.md")))
    tjek("skriveret: forslag uden igangværende leverance afvises",
         afvist(skriv(VVS, sm / "forslag" / "vvs-09__graenseflader.md")))
    tjek("skriveret: hovedtråden må skrive alt", not afvist(skriv(S, sm / "projektgrundlag.md")))
    tjek("skriveret: projektleder som hovedagent må skrive alt",
         not afvist(skriv({**S, "agent_type": "byg:projektleder"}, sm / "graenseflader.md")))
    tjek("skriveret: filer uden for byg-sager påvirkes ikke", not afvist(skriv(VVS, tmp / "hukommelse" / "MEMORY.md")))
    STAT = {**S, "agent_type": "byg-statik:statiker"}
    tjek("skriveret: statiker må skrive fem/", not afvist(skriv(STAT, sm / "fem" / "fem.yaml")))
    BIM = {**S, "agent_type": "byg-bim:bim-modelloer"}
    tjek("skriveret: bim må oprette hovedmodellen", not afvist(skriv(BIM, sm / "bim" / "model.yaml")))
    (sm / "bim").mkdir()
    (sm / "bim" / "model.yaml").write_text("x: 1\n", encoding="utf-8")
    tjek("skriveret: bim må ikke rette en eksisterende hovedmodel", afvist(skriv(BIM, sm / "bim" / "model.yaml")))
    tjek("skriveret: bim må skrive forslag", not afvist(skriv(BIM, sm / "bim" / "forslag" / "bim-02.yaml")))

    # Fuldt forløb: fagkald → forslag → aflevering → afvist → rettelse → godkendt → flettet og committet
    L = "2026-10-02-bad/vvs/01"
    kald("pretool", {**S, "tool_input": {"subagent_type": "byg-vvs:vvs-mester", "prompt": f"LEVERANCE: {L}\nopgave"}}, env)
    notat = sm / "fagnotater" / "vvs.md"
    notat.write_text("# Fagnotat – vvs\nLøsning: A\n", encoding="utf-8")
    forslag = sm / "forslag" / "vvs-01__graenseflader.md"
    tjek("skriveret: fagagent må skrive sit forslag", not afvist(skriv(VVS, forslag)))
    tjek("forslag: basis gemt ved første skrivning", (sm / "forslag" / ".basis" / forslag.name).exists())
    forslag.write_text("## Register\n| ID | Fra | Til | Hvad | Ejer |\n|---|---|---|---|---|\n"
                       "| G-03 | vvs | ventilation | Emhætte og erstatningsluft | ventilation |\n", encoding="utf-8")
    stop_fag = {**S, "agent_type": "byg-vvs:vvs-mester", "agent_transcript_path": transkript(f"LEVERANCE: {L}")}
    kald("subagentstop", stop_fag, env)
    tjek("git: byg-sager er et git-repo efter første aflevering", (bs / ".git").is_dir() and (bs / ".gitignore").is_file())
    tjek("git: fagaflevering committet med leverance-ID", f"{L}: fagaflevering" in git(bs, "log", "--format=%s"))
    tjek("git: fagaflevering committer kun fagets filer",
         "fagnotater/vvs.md" in git(bs, "ls-files") and "projektgrundlag.md" not in git(bs, "ls-files"),
         git(bs, "ls-files"))

    def dom(udfald):
        fund = [] if udfald == "godkendt" else [{"id": "F1", "klasse": "væsentlig", "status": "nyt", "krav": "k",
                                                  "kilde": "s", "evidens": "e", "handling": "h"}]
        blok = {"leverance_id": L, "fag": "vvs", "dom": udfald, "fund": fund, "sagsmappe": str(sm)}
        return "ok\n```json\n" + json.dumps(blok, ensure_ascii=False) + "\n```"

    KON = {**S, "tool_input": {"subagent_type": "byg-kontrol:vvs-kontrol", "prompt": f"LEVERANCE: {L}"}}
    kald("pretool", KON, env)
    kald("subagentstop", {**S, "agent_type": "byg-kontrol:vvs-kontrol", "last_assistant_message": dom("afvist")}, env)
    tjek("afvist: forslaget flettes ikke", forslag.exists() and "G-03" not in (sm / "graenseflader.md").read_text(encoding="utf-8"))
    tjek("git: dommen committet", f"{L}: dom afvist" in git(bs, "log", "--format=%s"))

    kald("pretool", {**S, "tool_input": {"subagent_type": "byg-vvs:vvs-mester", "prompt": f"LEVERANCE: {L}\nret F1"}}, env)
    notat.write_text("# Fagnotat – vvs\nLøsning: B (rettet efter F1)\n", encoding="utf-8")
    kald("subagentstop", stop_fag, env)
    diff = sm / "kvalitet" / "2026-10-02-bad__vvs__01__aendringer.diff"
    tjek("diff: ændringer siden den kontrollerede version til forsøg 2",
         diff.exists() and "-Løsning: A" in diff.read_text(encoding="utf-8") and "+Løsning: B" in diff.read_text(encoding="utf-8"))

    # Projektlederen opdaterer registret imens (en anden række) – ingen konflikt
    g = (sm / "graenseflader.md").read_text(encoding="utf-8").replace("Gennemføring i ydervæg", "Gennemføring Ø110")
    (sm / "graenseflader.md").write_text(g, encoding="utf-8")
    kald("pretool", KON, env)
    kald("subagentstop", {**S, "agent_type": "byg-kontrol:vvs-kontrol", "last_assistant_message": dom("godkendt")}, env)
    g = (sm / "graenseflader.md").read_text(encoding="utf-8")
    tjek("godkendt: forslaget flettes ind, projektlederens ændring bevares",
         "Emhætte og erstatningsluft" in g and "Gennemføring Ø110" in g and not forslag.exists(), g)
    tjek("git: dom og fletning committet", "dom godkendt (runde 1, forsøg 2), 1 forslag flettet" in git(bs, "log", "--format=%s"),
         git(bs, "log", "--format=%s"))
    tjek("stop: ingen konflikter at rapportere", kald("stop", S, env) is None)
    tjek("git: hovedtrådens ændringer committes ved Stop",
         "projektgrundlag.md" in git(bs, "ls-files") and git(bs, "status", "--porcelain").strip() == "",
         git(bs, "status", "--porcelain"))

    # Konflikt ved godkendelse → Stop blokerer med vejledning; løst konflikt → Stop er tilfreds
    L2 = "2026-10-02-bad/vvs/02"
    kald("pretool", {**S, "tool_input": {"subagent_type": "byg-vvs:vvs-mester", "prompt": f"LEVERANCE: {L2}\nopgave"}}, env)
    f2 = sm / "forslag" / "vvs-02__graenseflader.md"
    skriv(VVS, f2)
    f2.write_text("## Register\n| ID | Fra | Til | Hvad | Ejer |\n|---|---|---|---|---|\n| G-01 | vvs | el | 1x10 A | el |\n",
                  encoding="utf-8")
    kald("subagentstop", {**S, "agent_type": "byg-vvs:vvs-mester", "agent_transcript_path": transkript(f"LEVERANCE: {L2}")}, env)
    (sm / "graenseflader.md").write_text((sm / "graenseflader.md").read_text(encoding="utf-8")
                                         .replace("Strøm til varmepumpe", "Strøm 3x16 A"), encoding="utf-8")
    kald("pretool", {**S, "tool_input": {"subagent_type": "byg-kontrol:vvs-kontrol", "prompt": f"LEVERANCE: {L2}"}}, env)
    blok = {"leverance_id": L2, "fag": "vvs", "dom": "godkendt", "fund": [], "sagsmappe": str(sm)}
    kald("subagentstop", {**S, "agent_type": "byg-kontrol:vvs-kontrol",
                          "last_assistant_message": "```json\n" + json.dumps(blok) + "\n```"}, env)
    r = kald("stop", S, env)
    tjek("konflikt: Stop blokerer med vejledning", bool(r) and r.get("decision") == "block" and "G-01" in r.get("reason", ""), r)
    m = subprocess.run([sys.executable, str(GATE), "flet", str(f2), "--tving"], capture_output=True, text=True, env=env)
    tjek("manuel flet --tving", m.returncode == 0 and "1x10 A" in (sm / "graenseflader.md").read_text(encoding="utf-8"), m.stdout)
    tjek("konflikt løst: Stop er tilfreds", kald("stop", S, env) is None)

    # Basis gemmes, når fagkaldet starter: en ændring, der lander, før fagagenten skriver forslaget, giver konflikt
    L4 = "2026-10-02-bad/vvs/04"
    kald("pretool", {**S, "tool_input": {"subagent_type": "byg-vvs:vvs-mester", "prompt": f"LEVERANCE: {L4}\nopgave"}}, env)
    tjek("basis: gemt ved fagkaldets start", (sm / "forslag" / ".basis" / "vvs-04__graenseflader.md").exists())
    (sm / "graenseflader.md").write_text((sm / "graenseflader.md").read_text(encoding="utf-8")
                                         .replace("Emhætte og erstatningsluft", "Emhætte 600 m³/h"), encoding="utf-8")
    f4 = sm / "forslag" / "vvs-04__graenseflader.md"
    tjek("skriveret: forslag til igangværende leverance tilladt", not afvist(skriv(VVS, f4)))
    f4.write_text("## Register\n| ID | Fra | Til | Hvad | Ejer |\n|---|---|---|---|---|\n"
                  "| G-03 | vvs | ventilation | Emhætte 400 m³/h | ventilation |\n", encoding="utf-8")
    kald("subagentstop", {**S, "agent_type": "byg-vvs:vvs-mester", "agent_transcript_path": transkript(f"LEVERANCE: {L4}")}, env)
    kald("pretool", {**S, "tool_input": {"subagent_type": "byg-kontrol:vvs-kontrol", "prompt": f"LEVERANCE: {L4}"}}, env)
    blok = {"leverance_id": L4, "fag": "vvs", "dom": "godkendt", "fund": [], "sagsmappe": str(sm)}
    kald("subagentstop", {**S, "agent_type": "byg-kontrol:vvs-kontrol",
                          "last_assistant_message": "```json\n" + json.dumps(blok) + "\n```"}, env)
    tjek("basis: ændring mellem fagkald og forslag giver konflikt, ikke overskrivning",
         "600 m³/h" in (sm / "graenseflader.md").read_text(encoding="utf-8") and f4.exists())
    f4.unlink()
    kald("stop", S, env)

    # BIM: hovedmodellen (ændret via bim.py) kommer med i fagafleveringens commit
    L5 = "2026-10-02-bad/bim/01"
    kald("pretool", {**S, "tool_input": {"subagent_type": "byg-bim:bim-modelloer", "prompt": f"LEVERANCE: {L5}"}}, env)
    (sm / "bim" / "model.yaml").write_text("x: 2\n", encoding="utf-8")
    kald("subagentstop", {**S, "agent_type": "byg-bim:bim-modelloer", "agent_transcript_path": transkript(f"LEVERANCE: {L5}")}, env)
    sidste = git(bs, "log", "-1", "--name-only", "--format=%s")
    tjek("git: BIM-hovedmodellen med i fagafleveringen", f"{L5}: fagaflevering" in sidste and "bim/model.yaml" in sidste, sidste)

    # BYG_GIT=0 slår revisionsstyringen fra
    tmp2 = tmp / "uden-git" / "byg-sager" / "2026-10-03-y"
    (tmp2 / "fagnotater").mkdir(parents=True)
    env2 = dict(env, BYG_GIT="0", CLAUDE_PLUGIN_DATA=str(tmp / "data2"))
    S2 = {"session_id": "s2", "cwd": str(tmp / "uden-git")}
    L3 = "2026-10-03-y/vvs/01"
    kald("pretool", {**S2, "tool_input": {"subagent_type": "byg-vvs:vvs-mester", "prompt": f"LEVERANCE: {L3}"}}, env2)
    kald("subagentstop", {**S2, "agent_type": "byg-vvs:vvs-mester", "agent_transcript_path": transkript(f"LEVERANCE: {L3}")}, env2)
    tjek("BYG_GIT=0: intet git-repo", not (tmp / "uden-git" / "byg-sager" / ".git").exists())

    # Hooken er fail-safe og skjuler fejl – loggen må ikke have nogen
    fejl = [l for d in ("data", "data2") for l in (tmp / d / "kontrol" / "log.jsonl").read_text(encoding="utf-8").splitlines()
            if json.loads(l).get("haendelse") in ("hookfejl", "git_fejl", "flet_fejl", "diff_fejl", "domfil_fejl")]
    tjek("ingen skjulte hookfejl i loggen", not fejl, fejl)


def main() -> int:
    if not shutil.which("git"):
        print("git findes ikke – springer over")
        return 0
    with tempfile.TemporaryDirectory() as t:
        tmp = pathlib.Path(t)
        test_flet_enhed(tmp)
        test_git_laas(tmp)
        test_hook(tmp)
    print("\nALLE TESTS BESTÅET" if not FEJL else f"\n{len(FEJL)} FEJL")
    return 1 if FEJL else 0


if __name__ == "__main__":
    sys.exit(main())
