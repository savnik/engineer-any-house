#!/usr/bin/env python3
"""Tester byg-kontrols hook (kontrol_gate.py) med simulerede Claude Code-hændelser.

Kør:  python3 tests/test_kontrol_gate.py
"""
import json
import os
import pathlib
import subprocess
import sys
import tempfile

ROD = pathlib.Path(__file__).resolve().parent.parent
GATE = ROD / "plugins" / "byg-kontrol" / "hooks" / "kontrol_gate.py"
FEJL = []
REG = json.loads((GATE.parent / "fagregister.json").read_text(encoding="utf-8"))
MAKS = int(REG.get("maks_forsoeg", 3))
MAKS_RUNDER = int(REG.get("maks_runder", 3))


FAGAGENTER = ("vvs-mester", "el-installatoer", "murermester", "ventilationsekspert", "malermester", "toemrermester")


def kald_raa(hændelse: str, data: dict, env: dict) -> dict | None:
    r = subprocess.run([sys.executable, str(GATE), hændelse], input=json.dumps(data), text=True,
                       capture_output=True, env=env, timeout=30)
    assert r.returncode == 0, r.stderr
    return json.loads(r.stdout) if r.stdout.strip() else None


def transkript(prompt: str, svar: str = "Notat skrevet.", handback: str | None = None) -> str:
    fd, sti = tempfile.mkstemp(suffix=".jsonl")
    linjer = [{"message": {"role": "user", "content": prompt}},
              {"message": {"role": "assistant", "content": [{"type": "text", "text": svar}]}}]
    if handback is not None:
        linjer.append({"message": {"role": "assistant", "content": [
            {"type": "tool_use", "name": "SubagentHandback", "input": {"report": handback}}]}})
    with os.fdopen(fd, "w", encoding="utf-8") as fh:
        fh.write("\n".join(json.dumps(x, ensure_ascii=False) for x in linjer))
    return sti


def kald(hændelse: str, data: dict, env: dict) -> dict | None:
    """Som kald_raa, men et tilladt fagkald afleveres straks (SubagentStop for fagagenten)."""
    r = kald_raa(hændelse, data, env)
    ti = data.get("tool_input") or {}
    at = str(ti.get("subagent_type") or "")
    if hændelse == "pretool" and r is None and at.split(":")[-1] in FAGAGENTER:
        kald_raa("subagentstop", {**{k: v for k, v in data.items() if k != "tool_input"}, "agent_type": at,
                                  "agent_transcript_path": transkript(str(ti.get("prompt") or ""))}, env)
    return r


def dom(lev, udfald, fund, sagsmappe=None):
    blok = {"leverance_id": lev, "fag": "vvs", "dom": udfald, "fund": fund, "sagsmappe": sagsmappe}
    return "Kort vurdering.\n```json\n" + json.dumps(blok, ensure_ascii=False) + "\n```"


def forvent(navn, resultat, slags):
    if slags == "tilladt":
        ok = resultat is None
    elif slags == "afvist":
        ok = bool(resultat) and resultat.get("hookSpecificOutput", {}).get("permissionDecision") == "deny"
    elif slags == "blokeret":
        ok = bool(resultat) and resultat.get("decision") == "block"
    else:
        ok = False
    print(("OK   " if ok else "FEJL ") + navn + ("" if ok else f"  → {resultat}"))
    if not ok:
        FEJL.append(navn)


def main() -> int:
    with tempfile.TemporaryDirectory() as tmp:
        env = dict(os.environ, CLAUDE_PLUGIN_DATA=str(pathlib.Path(tmp) / "data"))
        cwd = pathlib.Path(tmp) / "projekt"
        sag = cwd / "byg-sager" / "2026-09-25-bad"
        sag.mkdir(parents=True)
        S = {"session_id": "s1", "cwd": str(cwd)}
        L = "2026-09-25-bad/vvs/01"
        FAG = "byg-vvs:vvs-mester"
        KON = "byg-kontrol:vvs-kontrol"
        blok_fund = [{"id": "F1", "klasse": "væsentlig", "status": "aabent", "krav": "DS 439:2024 tæthedsprøvning",
                      "kilde": "ds.dk", "evidens": "Notatet nævner ingen tæthedsprøvning", "handling": "Tilføj hold point"}]

        forvent("fagkald uden leverance-ID afvises", kald("pretool", {**S, "tool_input": {"subagent_type": FAG, "prompt": "Vurdér"}}, env), "afvist")
        forvent("andre agenter påvirkes ikke", kald("pretool", {**S, "tool_input": {"subagent_type": "Explore", "prompt": "x"}}, env), "tilladt")
        forvent("fagkald forsøg 1 tilladt", kald("pretool", {**S, "tool_input": {"subagent_type": FAG, "prompt": f"LEVERANCE: {L}\nVurdér"}}, env), "tilladt")
        forvent("nyt fagkald før kontrol afvises", kald("pretool", {**S, "tool_input": {"subagent_type": FAG, "prompt": f"LEVERANCE: {L}"}}, env), "afvist")
        forvent("forkert kontrolagent afvises", kald("pretool", {**S, "tool_input": {"subagent_type": "byg-kontrol:el-kontrol", "prompt": f"LEVERANCE: {L}"}}, env), "afvist")
        forvent("stop blokeres, mens leverance afventer kontrol", kald("stop", S, env), "blokeret")
        forvent("stop tilladt ved stop_hook_active", kald("stop", {**S, "stop_hook_active": True}, env), "tilladt")

        for forsoeg in range(1, MAKS + 1):
            if forsoeg > 1:
                forvent(f"fagkald forsøg {forsoeg} tilladt efter afvisning",
                        kald("pretool", {**S, "tool_input": {"subagent_type": FAG, "prompt": f"LEVERANCE: {L}"}}, env), "tilladt")
            forvent(f"kontrolkald forsøg {forsoeg} tilladt",
                    kald("pretool", {**S, "tool_input": {"subagent_type": KON, "prompt": f"LEVERANCE: {L}"}}, env), "tilladt")
            if forsoeg == 1:
                ugyldig = dom(L, "godkendt", [{"id": "F1", "klasse": "kritisk", "status": "nyt", "krav": "x"}])
                forvent("ugyldig dom sendes retur", kald("subagentstop", {**S, "agent_type": KON, "last_assistant_message": ugyldig}, env), "blokeret")
            forvent(f"gyldig afvisning forsøg {forsoeg} registreres",
                    kald("subagentstop", {**S, "agent_type": KON, "stop_hook_active": forsoeg == 1,
                                          "last_assistant_message": dom(L, "afvist", blok_fund, "byg-sager/2026-09-25-bad")}, env), "tilladt")

        forvent(f"fagforsøg {MAKS + 1} afvises (maks. {MAKS})", kald("pretool", {**S, "tool_input": {"subagent_type": FAG, "prompt": f"LEVERANCE: {L}"}}, env), "afvist")
        r = kald("stop", S, env)
        forvent("stop blokeres én gang for eskalering til brugeren", r, "blokeret")
        ok = bool(r) and "Ny runde" in r.get("reason", "") and "RCA" in r.get("reason", "")
        print(("OK   " if ok else "FEJL ") + "eskaleringen tilbyder brugeren en ny runde")
        if not ok:
            FEJL.append("eskaleringstekst")
        forvent("stop tilladt efter eskalering (ingen RCA krævet)", kald("stop", S, env), "tilladt")
        forvent("ny runde afvises uden brugerens 'Ny runde'",
                kald("pretool", {**S, "tool_input": {"subagent_type": FAG, "prompt": f"LEVERANCE: {L}"}}, env), "afvist")
        r = kald_raa("prompt", {**S, "prompt": f"Ny runde {L}"}, env)
        ok = bool(r) and "root cause" in r["hookSpecificOutput"]["additionalContext"]
        print(("OK   " if ok else "FEJL ") + "brugerens 'Ny runde' registreres og beder om RCA")
        if not ok:
            FEJL.append(f"ny runde-prompt: {r}")
        forvent("stop blokeres uden RCA, når brugeren har bedt om ny runde", kald("stop", S, env), "blokeret")
        (sag / "kvalitet" / "RCA-2026-09-25-bad__vvs__01.md").write_text("# RCA\n", encoding="utf-8")
        forvent("stop tilladt når RCA findes", kald("stop", S, env), "tilladt")
        domfiler = sorted(p.name for p in (sag / "kvalitet").glob("*.json"))
        ok = len(domfiler) == MAKS
        print(("OK   " if ok else "FEJL ") + f"domme logget i sagsmappen ({len(domfiler)})")
        if not ok:
            FEJL.append("domfiler")

        forvent("gentaget dom efter stop ignoreres",
                kald("subagentstop", {**S, "agent_type": KON, "last_assistant_message": dom(L, "afvist", blok_fund, "byg-sager/2026-09-25-bad")}, env), "tilladt")
        ok = len(list((sag / "kvalitet").glob("*.json"))) == MAKS
        print(("OK   " if ok else "FEJL ") + "gentaget dom efter stop giver ingen ny domfil")
        if not ok:
            FEJL.append("gentaget domfil")

        # Ny runde efter brugerens "Ny runde" og RCA med "Forbedring implementeret: ja"; højst MAKS_RUNDER runder
        rca1 = sag / "kvalitet" / "RCA-2026-09-25-bad__vvs__01.md"
        forvent("ny runde afvises uden implementeret forbedring",
                kald("pretool", {**S, "tool_input": {"subagent_type": FAG, "prompt": f"LEVERANCE: {L}"}}, env), "afvist")
        rca1.write_text("# RCA\n**Forbedring implementeret:** ja\n", encoding="utf-8")
        forvent("ny runde afvises uden 5 Why-kæde",
                kald("pretool", {**S, "tool_input": {"subagent_type": FAG, "prompt": f"LEVERANCE: {L}"}}, env), "afvist")
        HV = "".join(f"{i}. Hvorfor x{i}? → y{i}\n" for i in range(1, 6)) + "**Grundårsag:** z\n"
        rca1.write_text("# RCA\n## 3. 5 Why\n" + HV + "## 6. Forbedring af fagagenten\n**Forbedring implementeret:** ja\n", encoding="utf-8")
        for r in range(2, MAKS_RUNDER + 1):
            if r > 2:
                kald_raa("prompt", {**S, "prompt": f"ny runde {L}"}, env)
            forvent(f"runde {r} starter med nyt fagkald",
                    kald("pretool", {**S, "tool_input": {"subagent_type": FAG, "prompt": f"LEVERANCE: {L}"}}, env), "tilladt")
            for forsoeg in range(1, MAKS + 1):
                if forsoeg > 1:
                    kald("pretool", {**S, "tool_input": {"subagent_type": FAG, "prompt": f"LEVERANCE: {L}"}}, env)
                kald("pretool", {**S, "tool_input": {"subagent_type": KON, "prompt": f"LEVERANCE: {L}"}}, env)
                kald("subagentstop", {**S, "agent_type": KON,
                                      "last_assistant_message": dom(L, "afvist", blok_fund, "byg-sager/2026-09-25-bad")}, env)
            ok = (sag / "kvalitet" / f"2026-09-25-bad__vvs__01__runde-{r}__forsoeg-{MAKS}.json").exists()
            print(("OK   " if ok else "FEJL ") + f"domfil for runde {r} har rundenummer")
            if not ok:
                FEJL.append(f"domfil runde {r}")
            forvent(f"forsøg {MAKS + 1} i runde {r} afvises",
                    kald("pretool", {**S, "tool_input": {"subagent_type": FAG, "prompt": f"LEVERANCE: {L}"}}, env), "afvist")
            forvent(f"stop blokeres for eskalering i runde {r}", kald("stop", S, env), "blokeret")
            (sag / "kvalitet" / f"RCA-2026-09-25-bad__vvs__01__runde-{r}.md").write_text(
                "# RCA\n" + HV + "Forbedring implementeret: ja\n", encoding="utf-8")
            forvent(f"stop tilladt med RCA for runde {r}", kald("stop", S, env), "tilladt")
        r = kald("pretool", {**S, "tool_input": {"subagent_type": FAG, "prompt": f"LEVERANCE: {L}"}}, env)
        ok = bool(r) and "nyt leverance-ID" in r["hookSpecificOutput"]["permissionDecisionReason"]
        print(("OK   " if ok else "FEJL ") + f"efter {MAKS_RUNDER} runder: ny runde afvises og eskaleres til brugeren")
        if not ok:
            FEJL.append(f"runde 4: {r}")

        # Gentaget dom fra en genoptaget kontrolagent må ikke tælle som næste forsøg
        L3 = "2026-09-25-bad/vvs/03"
        kald("pretool", {**S, "tool_input": {"subagent_type": FAG, "prompt": f"LEVERANCE: {L3}"}}, env)
        kald("pretool", {**S, "tool_input": {"subagent_type": KON, "prompt": f"LEVERANCE: {L3}"}}, env)
        gammel = dom(L3, "afvist", blok_fund, "byg-sager/2026-09-25-bad").replace('"dom":', '"forsoeg": 1, "dom":')
        kald("subagentstop", {**S, "agent_type": KON, "last_assistant_message": gammel}, env)
        kald("pretool", {**S, "tool_input": {"subagent_type": FAG, "prompt": f"LEVERANCE: {L3}"}}, env)
        kald("subagentstop", {**S, "agent_type": KON, "last_assistant_message": gammel}, env)
        forvent("gentaget dom før kontrolkald registreres ikke",
                kald("pretool", {**S, "tool_input": {"subagent_type": FAG, "prompt": f"LEVERANCE: {L3}"}}, env), "afvist")
        kald("pretool", {**S, "tool_input": {"subagent_type": KON, "prompt": f"LEVERANCE: {L3}"}}, env)
        kald("subagentstop", {**S, "agent_type": KON, "last_assistant_message": gammel}, env)
        forvent("dom med forkert forsøgsnummer registreres ikke",
                kald("pretool", {**S, "tool_input": {"subagent_type": FAG, "prompt": f"LEVERANCE: {L3}"}}, env), "afvist")
        ok = not (sag / "kvalitet" / "2026-09-25-bad__vvs__03__forsoeg-2.json").exists()
        print(("OK   " if ok else "FEJL ") + "ingen domfil for forsøg 2 ved forældet dom")
        if not ok:
            FEJL.append("forældet domfil")
        ny = dom(L3, "godkendt", [], "byg-sager/2026-09-25-bad").replace('"dom":', '"forsoeg": 2, "dom":')
        kald("subagentstop", {**S, "agent_type": KON, "last_assistant_message": ny}, env)
        ok = (sag / "kvalitet" / "2026-09-25-bad__vvs__03__forsoeg-2.json").exists()
        print(("OK   " if ok else "FEJL ") + "dom med rigtigt forsøgsnummer registreres")
        if not ok:
            FEJL.append("aktuel dom")

        L2 = "2026-09-25-bad/vvs/02"
        kald("pretool", {**S, "tool_input": {"subagent_type": FAG, "prompt": f"LEVERANCE: {L2}"}}, env)
        kald("pretool", {**S, "tool_input": {"subagent_type": KON, "prompt": f"LEVERANCE: {L2}"}}, env)
        forvent("godkendt dom registreres", kald("subagentstop", {**S, "agent_type": KON, "last_assistant_message": dom(L2, "godkendt", [])}, env), "tilladt")
        forvent("ændring af godkendt leverance kræver nyt ID", kald("pretool", {**S, "tool_input": {"subagent_type": FAG, "prompt": f"LEVERANCE: {L2}"}}, env), "afvist")

        forvent("ekstern gennemgang tilladt", kald("pretool", {**S, "tool_input": {"subagent_type": KON, "prompt": "LEVERANCE: ekstern/tilbud-vvs"}}, env), "tilladt")
        kald("subagentstop", {**S, "agent_type": KON, "last_assistant_message": dom("ekstern/tilbud-vvs", "afvist", blok_fund)}, env)
        forvent("ekstern afvisning blokerer ikke stop", kald("stop", S, env), "tilladt")

        SAM = {"session_id": "s2", "cwd": str(cwd)}
        forvent("samlet plugin: fagkald tilladt", kald("pretool", {**SAM, "tool_input": {"subagent_type": "byg:el-installatoer", "prompt": "LEVERANCE: x/el/01"}}, env), "tilladt")
        r = kald("stop", SAM, env)
        ok = bool(r) and "byg:el-kontrol" in r.get("reason", "")
        print(("OK   " if ok else "FEJL ") + "samlet plugin peger på byg:el-kontrol")
        if not ok:
            FEJL.append("samlet navn")

        P = {"session_id": "s3", "cwd": str(cwd)}
        for n in range(1, MAKS + 1):
            kald("pretool", {**P, "tool_input": {"subagent_type": "byg-kontrol:projekt-kontrol", "prompt": "LEVERANCE: sag/projekt/01\nFASE: 1"}}, env)
            kald("subagentstop", {**P, "agent_type": "byg-kontrol:projekt-kontrol",
                                  "last_assistant_message": dom("sag/projekt/01", "afvist", blok_fund).replace('"vvs"', '"projekt"')}, env)
        forvent(f"projektkontrol: forsøg {MAKS + 1} afvises", kald("pretool", {**P, "tool_input": {"subagent_type": "byg-kontrol:projekt-kontrol", "prompt": "LEVERANCE: sag/projekt/01\nFASE: 1"}}, env), "afvist")
        (sag / "kvalitet" / "RCA-sag__projekt__01.md").write_text(HV + "Forbedring implementeret: ja\n", encoding="utf-8")
        forvent("projektkontrol: runde 2 afvises uden brugerens 'Ny runde'",
                kald("pretool", {**P, "tool_input": {"subagent_type": "byg-kontrol:projekt-kontrol", "prompt": "LEVERANCE: sag/projekt/01\nFASE: 1"}}, env), "afvist")
        kald_raa("prompt", {**P, "prompt": "Ny runde sag/projekt/01"}, env)
        forvent("projektkontrol: runde 2 starter efter RCA med forbedring",
                kald("pretool", {**P, "tool_input": {"subagent_type": "byg-kontrol:projekt-kontrol", "prompt": "LEVERANCE: sag/projekt/01\nFASE: 1"}}, env), "tilladt")

        # Fase-gate: planleverance i fase 3 kræver godkendt designgrundlag
        PK = "byg-kontrol:projekt-kontrol"
        forvent("projektkontrol uden FASE afvises",
                kald("pretool", {**P, "tool_input": {"subagent_type": PK, "prompt": "LEVERANCE: sag/projekt/05"}}, env), "afvist")
        forvent("fase 3 uden DESIGNGRUNDLAG afvises",
                kald("pretool", {**P, "tool_input": {"subagent_type": PK, "prompt": "LEVERANCE: sag/projekt/05\nFASE: 3"}}, env), "afvist")
        forvent("fase 3 med ikke-godkendt designgrundlag afvises",
                kald("pretool", {**P, "tool_input": {"subagent_type": PK, "prompt": f"LEVERANCE: sag/projekt/05\nFASE: 3\nDESIGNGRUNDLAG: {L3}, {L}"}}, env), "afvist")
        LP = "2026-09-25-bad/projekt/05"
        forvent("fase 3 uden brugerens G2-godkendelse afvises",
                kald("pretool", {**P, "tool_input": {"subagent_type": PK, "prompt": f"LEVERANCE: {LP}\nFASE: 3\nDESIGNGRUNDLAG: {L3}, {L2}"}}, env), "afvist")
        forvent("fagkald i fase 3 uden G2 afvises",
                kald("pretool", {**P, "tool_input": {"subagent_type": FAG, "prompt": "LEVERANCE: 2026-09-25-bad/vvs/09\nFASE: 3"}}, env), "afvist")
        r = kald("prompt", {**P, "prompt": "Det ser fint ud. Godkend G2 2026-09-25-bad"}, env)
        ok = bool(r) and "G2" in r.get("hookSpecificOutput", {}).get("additionalContext", "")
        print(("OK   " if ok else "FEJL ") + "brugerens 'Godkend G2 <sag>' registreres")
        if not ok:
            FEJL.append(f"G2 prompt: {r}")
        forvent("fase 3 med G2 og godkendt designgrundlag tilladt",
                kald("pretool", {**P, "tool_input": {"subagent_type": PK, "prompt": f"LEVERANCE: {LP}\nFASE: 3\nDESIGNGRUNDLAG: {L3}, {L2}"}}, env), "tilladt")
        forvent("designgrundlag uden for det G2-godkendte design afvises",
                kald("pretool", {**P, "tool_input": {"subagent_type": PK, "prompt": f"LEVERANCE: 2026-09-25-bad/projekt/06\nFASE: 3\nDESIGNGRUNDLAG: {L3}, 2026-09-25-bad/vvs/07"}}, env), "afvist")
        forvent("almindelig brugerprompt påvirkes ikke", kald("prompt", {**P, "prompt": "Hvad koster det?"}, env), "tilladt")

        # Kontekstbudget: påmindelse, når en byg-sessions hovedtråd passerer 200k og derefter hver 100k
        def hovedtraad(n: int) -> str:
            fd, sti = tempfile.mkstemp(suffix=".jsonl")
            linjer = [{"type": "user", "message": {"role": "user", "content": "x"}},
                      {"type": "assistant", "message": {"role": "assistant", "content": [{"type": "text", "text": "y"}],
                       "usage": {"input_tokens": 5, "cache_creation_input_tokens": 995, "cache_read_input_tokens": n - 1000}}},
                      {"type": "assistant", "isSidechain": True, "message": {"role": "assistant", "content": [],
                       "usage": {"input_tokens": 5, "cache_read_input_tokens": 10}}}]
            with os.fdopen(fd, "w", encoding="utf-8") as fh:
                fh.write("\n".join(json.dumps(x) for x in linjer))
            return sti

        def paamindet(r) -> bool:
            return bool(r) and "ny session" in r.get("systemMessage", "") and \
                "Kontekstbudget" in r.get("hookSpecificOutput", {}).get("additionalContext", "")

        for navn, sid, n, forventet in [
                ("kontekst under 200k giver ingen påmindelse", "s3", 150_000, False),
                ("kontekst over 200k giver påmindelse", "s3", 250_000, True),
                ("samme trin giver ikke påmindelse igen", "s3", 280_000, False),
                ("næste trin (300k+) giver ny påmindelse", "s3", 320_000, True),
                ("session uden byg-leverancer påvirkes ikke", "s9", 500_000, False)]:
            r = kald("prompt", {"session_id": sid, "cwd": str(cwd), "prompt": "Næste spørgsmål",
                                "transcript_path": hovedtraad(n)}, env)
            ok = paamindet(r) == forventet
            print(("OK   " if ok else "FEJL ") + navn)
            if not ok:
                FEJL.append(f"{navn}: {r}")

        # Sikker compact: PreCompact giver resumé-instruktioner, SessionStart(compact) genindlæser sagen
        (sag / "status.md").write_text("# Status\nFase: 2\nNæste skridt: tæthedsprøvning\n" + "x" * 20_000, encoding="utf-8")

        def compact_kald(hændelse: str, data: dict) -> str:
            r = subprocess.run([sys.executable, str(GATE), hændelse], input=json.dumps(data), text=True,
                               capture_output=True, env=env, timeout=30)
            assert r.returncode == 0, r.stderr
            return r.stdout

        for navn, ok in [
                ("precompact i byg-session beder om at bevare leverance-ID'er",
                 "leverance-ID" in compact_kald("precompact", {**S, "trigger": "auto"})),
                ("precompact uden byg-sag giver intet", compact_kald("precompact", {"session_id": "s9", "cwd": str(cwd)}) == "")]:
            print(("OK   " if ok else "FEJL ") + navn)
            if not ok:
                FEJL.append(navn)
        C = {"session_id": "s5", "cwd": str(cwd)}
        kald_raa("pretool", {**C, "tool_input": {"subagent_type": FAG, "prompt": "LEVERANCE: 2026-09-25-bad/vvs/09"}}, env)
        ud = compact_kald("efter_compact", {**C, "source": "compact"})
        ctx = json.loads(ud)["hookSpecificOutput"]["additionalContext"] if ud.strip() else ""
        for navn, ok in [
                ("efter compact genindlæses status.md", "Næste skridt: tæthedsprøvning" in ctx),
                ("efter compact afkortes en lang status.md", "afkortet" in ctx and len(ctx) < 16_000),
                ("efter compact vises åbne leverancer fra tilstanden", "2026-09-25-bad/vvs/09: fagkald_igang" in ctx),
                ("efter compact uden byg-sag giver intet",
                 compact_kald("efter_compact", {"session_id": "s9", "cwd": str(cwd), "source": "compact"}) == ""),
                ("efter compact i sagsmappen uden leverancer genindlæses status.md",
                 "tæthedsprøvning" in compact_kald("efter_compact", {"session_id": "s9", "cwd": str(sag), "source": "compact"}))]:
            print(("OK   " if ok else "FEJL ") + navn)
            if not ok:
                FEJL.append(f"{navn}: {ctx[:300]}")

        # Fund-fastlåsning: nyt blokerende fund i forsøg 2 kræver nyt_grundlag
        L4 = "2026-09-25-bad/vvs/04"
        kald("pretool", {**S, "tool_input": {"subagent_type": FAG, "prompt": f"LEVERANCE: {L4}"}}, env)
        kald("pretool", {**S, "tool_input": {"subagent_type": KON, "prompt": f"LEVERANCE: {L4}"}}, env)
        kald("subagentstop", {**S, "agent_type": KON, "last_assistant_message": dom(L4, "afvist", blok_fund, "byg-sager/2026-09-25-bad")}, env)
        kald("pretool", {**S, "tool_input": {"subagent_type": FAG, "prompt": f"LEVERANCE: {L4}"}}, env)
        kald("pretool", {**S, "tool_input": {"subagent_type": KON, "prompt": f"LEVERANCE: {L4}"}}, env)
        nytfund = [{**blok_fund[0], "id": "F9", "status": "nyt"}]
        forvent("nyt væsentligt fund i forsøg 2 uden nyt_grundlag sendes retur",
                kald("subagentstop", {**S, "agent_type": KON, "last_assistant_message": dom(L4, "afvist", nytfund)}, env), "blokeret")
        forvent("nyt væsentligt fund i forsøg 2 med nyt_grundlag=regression registreres",
                kald("subagentstop", {**S, "agent_type": KON, "stop_hook_active": True,
                                      "last_assistant_message": dom(L4, "afvist", [{**nytfund[0], "nyt_grundlag": "regression"}])}, env), "tilladt")

        # Fagkald i gang: stop blokerer ikke, genforsøg tæller ikke, aflevering giver afventer_kontrol
        G = {"session_id": "s4", "cwd": str(cwd)}
        LG = "2026-09-25-bad/vvs/07"
        forvent("fagkald (uden aflevering) tilladt", kald_raa("pretool", {**G, "tool_input": {"subagent_type": FAG, "prompt": f"LEVERANCE: {LG}"}}, env), "tilladt")
        forvent("stop blokerer ikke, mens fagkald er i gang", kald("stop", G, env), "tilladt")
        forvent("genforsøg af afbrudt fagkald tilladt", kald_raa("pretool", {**G, "tool_input": {"subagent_type": FAG, "prompt": f"LEVERANCE: {LG}"}}, env), "tilladt")
        tilst = json.loads((pathlib.Path(env["CLAUDE_PLUGIN_DATA"]) / "kontrol" / "tilstand.json").read_text(encoding="utf-8"))
        ok = tilst["leverancer"][LG]["forsoeg"] == 1
        print(("OK   " if ok else "FEJL ") + "genforsøg tæller ikke som nyt forsøg")
        if not ok:
            FEJL.append("genforsøg")
        kald_raa("subagentstop", {**G, "agent_type": FAG, "agent_transcript_path": transkript(f"LEVERANCE: {LG}\nOpgave")}, env)
        forvent("efter aflevering blokerer stop (afventer kontrol)", kald("stop", G, env), "blokeret")

        # Dom i hand-back (tool_use-input) registreres uden retur
        forvent("kontrolkald med sti til manglende notat afvises", kald("pretool", {**G, "tool_input": {"subagent_type": KON, "prompt":
                f"LEVERANCE: {LG}\nLeverance: {sag}/fagnotater/vvs-07.md"}}, env), "afvist")
        (sag / "fagnotater").mkdir(exist_ok=True)
        (sag / "fagnotater" / "vvs-07.md").write_text("# Fagnotat\n", encoding="utf-8")
        forvent("kontrolkald med sti", kald("pretool", {**G, "tool_input": {"subagent_type": KON, "prompt":
                f"LEVERANCE: {LG}\nLeverance: {sag}/fagnotater/vvs-07.md"}}, env), "tilladt")
        hb = dom(LG, "godkendt", [], "byg-sager/2026-09-25-bad")
        forvent("dom i hand-back registreres", kald("subagentstop", {**G, "agent_type": KON, "last_assistant_message": "Rapport afleveret.",
                "agent_transcript_path": transkript("x", handback=hb)}, env), "tilladt")
        tilst = json.loads((pathlib.Path(env["CLAUDE_PLUGIN_DATA"]) / "kontrol" / "tilstand.json").read_text(encoding="utf-8"))
        ok = tilst["leverancer"][LG]["status"] == "godkendt"
        print(("OK   " if ok else "FEJL ") + "hand-back-dom gav status godkendt")
        if not ok:
            FEJL.append("handback")

        # Beskyttelse af godkendt notat
        fil = str(sag / "fagnotater" / "vvs-07.md")
        forvent("subagent må ikke rette godkendt notat", kald("beskyt", {**G, "agent_type": "byg-murer:murermester",
                "tool_input": {"file_path": fil}}, env), "afvist")
        r = kald("beskyt", {**G, "tool_input": {"file_path": fil}}, env)
        ok = bool(r) and "systemMessage" in r and "hookSpecificOutput" in r and r["hookSpecificOutput"].get("permissionDecision") is None
        print(("OK   " if ok else "FEJL ") + "hovedtråden får advarsel ved godkendt notat")
        if not ok:
            FEJL.append(f"beskyt hovedtråd: {r}")
        forvent("andre filer påvirkes ikke", kald("beskyt", {**G, "agent_type": "x", "tool_input": {"file_path": str(sag / "andet.md")}}, env), "tilladt")

        # Én skriver pr. fil gælder også midlertidige spørgsmålsmapper i ~/byg-tmp/
        tmpsag = pathlib.Path(tmp) / "byg-tmp" / "2026-10-18-spoergsmaal"
        forvent("fagagent må ikke skrive fremmed fil i byg-tmp", kald("beskyt", {**G, "agent_type": "byg-vvs:vvs-mester",
                "tool_input": {"file_path": str(tmpsag / "projektgrundlag.md")}}, env), "afvist")
        forvent("fagagent må skrive eget notat i byg-tmp", kald("beskyt", {**G, "agent_type": "byg-vvs:vvs-mester",
                "tool_input": {"file_path": str(tmpsag / "fagnotater" / "vvs.md")}}, env), "tilladt")

        # Manuel status uden CLAUDE_PLUGIN_DATA skal finde pluginets datamappe under ~/.claude/plugins/data/
        hjem = pathlib.Path(tmp) / "hjem"
        pdata = hjem / ".claude" / "plugins" / "data" / "byg-kontrol-test" / "kontrol"
        pdata.mkdir(parents=True)
        (pdata / "tilstand.json").write_text(json.dumps({"leverancer": {"sag/vvs/09": {
            "fag": "vvs", "status": "godkendt", "forsoeg": 1}}}), encoding="utf-8")
        env_manuel = {k: v for k, v in os.environ.items() if k != "CLAUDE_PLUGIN_DATA"}
        env_manuel["HOME"] = str(hjem)
        r = subprocess.run([sys.executable, str(GATE), "status"], text=True, capture_output=True, env=env_manuel, timeout=30)
        ok = r.returncode == 0 and "sag/vvs/09" in r.stdout
        print(("OK   " if ok else "FEJL ") + "manuel status finder pluginets datamappe")
        if not ok:
            FEJL.append(f"manuel status: {r.stdout or r.stderr}")

        # Hjælpeagent (tegningsimport): fag → sammenligning → rettelse → sammenligning → kontrol
        B = {"session_id": "s4", "cwd": str(cwd)}
        LB = "2026-09-25-bad/bim/01"
        BF, BS, BK = "byg-bim:bim-modelloer", "byg-bim:bim-sammenligner", "byg-kontrol:bim-kontrol"

        def bim_fag(navn, forventet):
            r = kald_raa("pretool", {**B, "tool_input": {"subagent_type": BF, "prompt": f"LEVERANCE: {LB}\nByg"}}, env)
            forvent(navn, r, forventet)
            if r is None:
                kald_raa("subagentstop", {**B, "agent_type": BF, "agent_transcript_path": transkript(f"LEVERANCE: {LB}")}, env)

        def bim_sammen(navn, forventet, resultat="ret"):
            r = kald_raa("pretool", {**B, "tool_input": {"subagent_type": BS, "prompt": f"LEVERANCE: {LB}\nSammenlign"}}, env)
            forvent(navn, r, forventet)
            if r is None:
                svar = '```json\n{"resultat": "%s", "afvigelser": []}\n```' % resultat
                kald_raa("subagentstop", {**B, "agent_type": BS, "last_assistant_message": svar,
                                          "agent_transcript_path": transkript(f"LEVERANCE: {LB}", svar)}, env)

        forvent("sammenligning uden leverance-ID afvises",
                kald_raa("pretool", {**B, "tool_input": {"subagent_type": BS, "prompt": "Sammenlign"}}, env), "afvist")
        forvent("sammenligning før fagleverance afvises",
                kald_raa("pretool", {**B, "tool_input": {"subagent_type": BS, "prompt": f"LEVERANCE: {LB}"}}, env), "afvist")
        bim_fag("bim-fagkald tilladt", "tilladt")
        bim_fag("nyt bim-fagkald uden sammenligning afvises", "afvist")
        bim_sammen("sammenligning 1 tilladt", "tilladt")
        forvent("stop blokeres efter sammenligning med afvigelser", kald_raa("stop", B, env), "blokeret")
        bim_fag("rettelse efter sammenligning tilladt", "tilladt")
        bim_sammen("sammenligning 2 tilladt", "tilladt")
        bim_fag("rettelse 2 tilladt", "tilladt")
        bim_sammen("sammenligning 3 tilladt", "tilladt", resultat="ok")
        bim_fag("rettelse 3 tilladt", "tilladt")
        bim_sammen("4. sammenligning afvises (maks. 3)", "afvist")
        forvent("kontrol efter sammenligninger tilladt",
                kald_raa("pretool", {**B, "tool_input": {"subagent_type": BK, "prompt": f"LEVERANCE: {LB}"}}, env), "tilladt")
        tilst = json.loads((pathlib.Path(env["CLAUDE_PLUGIN_DATA"]) / "kontrol" / "tilstand.json").read_text(encoding="utf-8"))
        eb = tilst["leverancer"][LB]
        ok = eb.get("forsoeg") == 1 and eb.get("sammenligninger") == 3 and eb.get("rettelser") == 3
        print(("OK   " if ok else "FEJL ") + "rettelser efter sammenligning bruger ikke kontrolforsøg")
        if not ok:
            FEJL.append(f"hjælpertilstand: {eb}")

        # afklar_med_bruger: valideres, blokerer ikke
        LA = "2026-09-25-bad/vvs/20"
        A = {"session_id": "s-afk", "cwd": str(cwd)}
        kald("pretool", {**A, "tool_input": {"subagent_type": FAG, "prompt": f"LEVERANCE: {LA}"}}, env)
        kald_raa("pretool", {**A, "tool_input": {"subagent_type": KON, "prompt": f"LEVERANCE: {LA}"}}, env)
        def afk_dom(liste):
            blok = {"leverance_id": LA, "fag": "vvs", "dom": "godkendt", "fund": [], "afklar_med_bruger": liste}
            return "OK.\n```json\n" + json.dumps(blok, ensure_ascii=False) + "\n```"
        forvent("afklar_med_bruger uden spoergsmaal sendes retur", kald_raa("subagentstop", {**A, "agent_type": KON,
                "last_assistant_message": afk_dom([{"betydning": "x"}])}, env), "blokeret")
        forvent("godkendt dom med afklar_med_bruger registreres", kald_raa("subagentstop", {**A, "agent_type": KON,
                "stop_hook_active": True, "last_assistant_message": afk_dom([{"spoergsmaal": "Bliver radiatoren?",
                "betydning": "shuntens størrelse"}])}, env), "tilladt")
        tilst = json.loads((pathlib.Path(env["CLAUDE_PLUGIN_DATA"]) / "kontrol" / "tilstand.json").read_text(encoding="utf-8"))
        ea = tilst["leverancer"][LA]
        ok = ea["status"] == "godkendt" and ea["domme"][-1].get("afklar_med_bruger") == 1
        print(("OK   " if ok else "FEJL ") + "afklar_med_bruger blokerer ikke og tælles i dommen")
        if not ok:
            FEJL.append(f"afklar: {ea}")

        # KONTROLNIVEAU: fuld kræver Opus i kontrolkaldet
        LF = "2026-09-25-bad/vvs/21"
        F = {"session_id": "s-fuld", "cwd": str(cwd)}
        kald("pretool", {**F, "tool_input": {"subagent_type": FAG, "prompt": f"LEVERANCE: {LF}"}}, env)
        forvent("fuld kontrol uden model opus afvises", kald_raa("pretool", {**F, "tool_input": {
            "subagent_type": KON, "prompt": f"LEVERANCE: {LF}\nKONTROLNIVEAU: fuld"}}, env), "afvist")
        forvent("fuld kontrol med model opus tilladt", kald_raa("pretool", {**F, "tool_input": {
            "subagent_type": KON, "model": "opus", "prompt": f"LEVERANCE: {LF}\nKONTROLNIVEAU: fuld"}}, env), "tilladt")

        # Workflow i byg-sager kun, når brugerens seneste besked nævner workflow
        W = {"session_id": "s-wf", "cwd": str(cwd / "byg-sager" / "2026-09-25-bad")}
        kald_raa("prompt", {**W, "prompt": "Forsæt"}, env)
        forvent("workflow afvises efter 'Forsæt'", kald_raa("workflow", {**W, "tool_input": {}}, env), "afvist")
        kald_raa("prompt", {**W, "prompt": "Brug et workflow til at sammenligne tilbuddene"}, env)
        forvent("workflow tilladt, når brugeren beder om det", kald_raa("workflow", {**W, "tool_input": {}}, env), "tilladt")
        kald_raa("prompt", {**W, "prompt": "fortsæt"}, env)
        forvent("workflow afvises igen ved næste besked uden 'workflow'", kald_raa("workflow", {**W, "tool_input": {}}, env), "afvist")
        forvent("workflow uden for byg-sager påvirkes ikke",
                kald_raa("workflow", {"session_id": "s-andet", "cwd": str(pathlib.Path(tmp)), "tool_input": {}}, env), "tilladt")

        # Værktøjskontrol (bim): sammenligning ok + rent tjek godkender uden kontrolagent
        V = {"session_id": "s-vaerk", "cwd": str(cwd)}
        LV = "2026-09-25-bad/bim/02"
        forvent("værktøj afvises for vvs", kald_raa("pretool", {**V, "tool_input": {
            "subagent_type": FAG, "prompt": "LEVERANCE: 2026-09-25-bad/vvs/40\nKONTROLNIVEAU: værktøj"}}, env), "afvist")

        def v_fag(navn, prompt):
            r = kald_raa("pretool", {**V, "tool_input": {"subagent_type": BF, "prompt": prompt}}, env)
            forvent(navn, r, "tilladt")
            kald_raa("subagentstop", {**V, "agent_type": BF, "agent_transcript_path": transkript(prompt)}, env)

        def v_sammen(navn, resultat, tjek):
            r = kald_raa("pretool", {**V, "tool_input": {"subagent_type": BS, "prompt": f"LEVERANCE: {LV}"}}, env)
            forvent(navn, r, "tilladt")
            svar = '```json\n{"resultat": "%s", "tjek": %s, "afvigelser": []}\n```' % (resultat, json.dumps(tjek))
            kald_raa("subagentstop", {**V, "agent_type": BS, "last_assistant_message": svar,
                                      "agent_transcript_path": transkript(f"LEVERANCE: {LV}", svar)}, env)

        def v_status():
            t = json.loads((pathlib.Path(env["CLAUDE_PLUGIN_DATA"]) / "kontrol" / "tilstand.json").read_text(encoding="utf-8"))
            return t["leverancer"][LV]

        v_fag("bim-fagkald med KONTROLNIVEAU: værktøj tilladt", f"LEVERANCE: {LV}\nKONTROLNIVEAU: værktøj\nByg")
        v_sammen("værktøj: sammenligning 1 tilladt", "ok", {"fejl": 0, "advarsler": 3, "sporbarhed": 2})
        ok = v_status()["status"] == "sammenlignet"
        print(("OK   " if ok else "FEJL ") + "værktøj: ok med sporbarhedsfund godkendes ikke")
        if not ok:
            FEJL.append(f"værktøj sporbarhed: {v_status()}")
        forvent("værktøj: stop blokeres, til leverancen er godkendt", kald_raa("stop", V, env), "blokeret")
        v_fag("værktøj: rettelse tilladt", f"LEVERANCE: {LV}\nRet sporbarheden")
        v_sammen("værktøj: sammenligning 2 tilladt", "ok", {"fejl": 0, "advarsler": 3, "sporbarhed": 0})
        ev = v_status()
        ok = ev["status"] == "godkendt" and ev.get("godkendt_af") == "vaerktoej" and ev.get("forsoeg") == 1
        print(("OK   " if ok else "FEJL ") + "værktøj: ok og rent tjek godkender uden kontrolagent")
        if not ok:
            FEJL.append(f"værktøj godkendelse: {ev}")
        domfiler = list((sag / "kvalitet").glob("*bim__02*vaerktoej.json"))
        print(("OK   " if domfiler else "FEJL ") + "værktøj: godkendelsen gemmes som dom i kvalitet/")
        if not domfiler:
            FEJL.append("værktøj: ingen domfil")
        forvent("værktøj: stop tilladt efter godkendelse", kald("stop", V, env), "tilladt")
        forvent("værktøj: ny version kræver nyt ID", kald_raa("pretool", {**V, "tool_input": {
            "subagent_type": BF, "prompt": f"LEVERANCE: {LV}"}}, env), "afvist")

        # Stikprøvekontrol: kun spørgsmål uden FASE, aldrig el/statik; udfaldet er deterministisk pr. leverance-ID
        import hashlib
        stik = REG.get("stikproeve") or {}
        def udtaget(lev):
            return int(hashlib.sha256(lev.encode("utf-8")).hexdigest(), 16) % 1000 < round(float(stik.get("andel", 1)) * 1000)
        kandidater = [f"2026-10-20-spm-{i}/murer/01" for i in range(60)]
        LI = next(x for x in kandidater if not udtaget(x))
        LU = next(x for x in kandidater if udtaget(x))
        MUR, MKON = "byg-murer:murermester", "byg-kontrol:murer-kontrol"
        forvent("stikprøve afvises for el", kald_raa("pretool", {"session_id": "s-stik0", "cwd": str(cwd), "tool_input": {
            "subagent_type": "byg-el:el-installatoer", "prompt": "LEVERANCE: 2026-10-20-spm/el/01\nKONTROLNIVEAU: stikprøve"}}, env), "afvist")
        forvent("stikprøve afvises i en sag med FASE", kald_raa("pretool", {"session_id": "s-stik0", "cwd": str(cwd), "tool_input": {
            "subagent_type": MUR, "prompt": "LEVERANCE: 2026-09-25-bad/murer/31\nFASE: 1 · KONTROLNIVEAU: stikprøve"}}, env), "afvist")
        I = {"session_id": "s-stik1", "cwd": str(cwd)}
        forvent("stikprøve: fagkald tilladt", kald("pretool", {**I, "tool_input": {
            "subagent_type": MUR, "prompt": f"LEVERANCE: {LI}\nKONTROLNIVEAU: stikprøve"}}, env), "tilladt")
        tilst = json.loads((pathlib.Path(tmp) / "data" / "kontrol" / "tilstand.json").read_text(encoding="utf-8"))
        ok = tilst["leverancer"][LI]["status"] == "ikke_udtaget"
        print(("OK   " if ok else "FEJL ") + "ikke udtaget: afleveret uden kontrol")
        if not ok:
            FEJL.append(f"stikprøve status: {tilst['leverancer'][LI]}")
        forvent("ikke udtaget: kontrolkald afvises med besked", kald_raa("pretool", {**I, "tool_input": {
            "subagent_type": MKON, "prompt": f"LEVERANCE: {LI}"}}, env), "afvist")
        forvent("ikke udtaget: stop blokerer ikke", kald("stop", I, env), "tilladt")
        forvent("ikke udtaget: ny version kræver nyt ID", kald_raa("pretool", {**I, "tool_input": {
            "subagent_type": MUR, "prompt": f"LEVERANCE: {LI}"}}, env), "afvist")
        U = {"session_id": "s-stik2", "cwd": str(cwd)}
        kald("pretool", {**U, "tool_input": {"subagent_type": MUR, "prompt": f"LEVERANCE: {LU}\nKONTROLNIVEAU: stikprøve"}}, env)
        forvent("udtaget: stop blokeres, til kontrollen er kørt", kald("stop", U, env), "blokeret")
        forvent("udtaget: kontrolkald tilladt", kald_raa("pretool", {**U, "tool_input": {
            "subagent_type": MKON, "prompt": f"LEVERANCE: {LU}"}}, env), "tilladt")

    print(f"\n{'ALLE TESTS BESTÅET' if not FEJL else f'{len(FEJL)} FEJL'}")
    return 1 if FEJL else 0


if __name__ == "__main__":
    sys.exit(main())
