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

        for forsoeg in (1, 2, 3):
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

        forvent("4. fagforsøg afvises (maks. 3)", kald("pretool", {**S, "tool_input": {"subagent_type": FAG, "prompt": f"LEVERANCE: {L}"}}, env), "afvist")
        forvent("stop blokeres uden RCA", kald("stop", S, env), "blokeret")
        (sag / "kvalitet" / "RCA-2026-09-25-bad__vvs__01.md").write_text("# RCA\n", encoding="utf-8")
        forvent("stop tilladt når RCA findes", kald("stop", S, env), "tilladt")
        domfiler = sorted(p.name for p in (sag / "kvalitet").glob("*.json"))
        ok = len(domfiler) == 3
        print(("OK   " if ok else "FEJL ") + f"domme logget i sagsmappen ({len(domfiler)})")
        if not ok:
            FEJL.append("domfiler")

        forvent("gentaget dom efter stop ignoreres",
                kald("subagentstop", {**S, "agent_type": KON, "last_assistant_message": dom(L, "afvist", blok_fund, "byg-sager/2026-09-25-bad")}, env), "tilladt")
        ok = len(list((sag / "kvalitet").glob("*.json"))) == 3
        print(("OK   " if ok else "FEJL ") + "gentaget dom efter stop giver ingen ny domfil")
        if not ok:
            FEJL.append("gentaget domfil")

        # Ny runde efter RCA: kræver RCA-fil med "Forbedring implementeret: ja"; højst 3 runder
        rca1 = sag / "kvalitet" / "RCA-2026-09-25-bad__vvs__01.md"
        forvent("ny runde afvises uden implementeret forbedring",
                kald("pretool", {**S, "tool_input": {"subagent_type": FAG, "prompt": f"LEVERANCE: {L}"}}, env), "afvist")
        rca1.write_text("# RCA\n**Forbedring implementeret:** ja\n", encoding="utf-8")
        forvent("ny runde afvises uden 5 Why-kæde",
                kald("pretool", {**S, "tool_input": {"subagent_type": FAG, "prompt": f"LEVERANCE: {L}"}}, env), "afvist")
        HV = "".join(f"{i}. Hvorfor x{i}? → y{i}\n" for i in range(1, 6)) + "**Grundårsag:** z\n"
        rca1.write_text("# RCA\n## 3. 5 Why\n" + HV + "## 6. Forbedring af fagagenten\n**Forbedring implementeret:** ja\n", encoding="utf-8")
        for r in (2, 3):
            forvent(f"runde {r} starter med nyt fagkald",
                    kald("pretool", {**S, "tool_input": {"subagent_type": FAG, "prompt": f"LEVERANCE: {L}"}}, env), "tilladt")
            for forsoeg in (1, 2, 3):
                if forsoeg > 1:
                    kald("pretool", {**S, "tool_input": {"subagent_type": FAG, "prompt": f"LEVERANCE: {L}"}}, env)
                kald("pretool", {**S, "tool_input": {"subagent_type": KON, "prompt": f"LEVERANCE: {L}"}}, env)
                kald("subagentstop", {**S, "agent_type": KON,
                                      "last_assistant_message": dom(L, "afvist", blok_fund, "byg-sager/2026-09-25-bad")}, env)
            ok = (sag / "kvalitet" / f"2026-09-25-bad__vvs__01__runde-{r}__forsoeg-3.json").exists()
            print(("OK   " if ok else "FEJL ") + f"domfil for runde {r} har rundenummer")
            if not ok:
                FEJL.append(f"domfil runde {r}")
            forvent(f"4. forsøg i runde {r} afvises",
                    kald("pretool", {**S, "tool_input": {"subagent_type": FAG, "prompt": f"LEVERANCE: {L}"}}, env), "afvist")
            forvent(f"stop blokeres uden RCA for runde {r}", kald("stop", S, env), "blokeret")
            (sag / "kvalitet" / f"RCA-2026-09-25-bad__vvs__01__runde-{r}.md").write_text(
                "# RCA\n" + HV + "Forbedring implementeret: ja\n", encoding="utf-8")
            forvent(f"stop tilladt med RCA for runde {r}", kald("stop", S, env), "tilladt")
        r = kald("pretool", {**S, "tool_input": {"subagent_type": FAG, "prompt": f"LEVERANCE: {L}"}}, env)
        ok = bool(r) and "brugerens beslutning" in r["hookSpecificOutput"]["permissionDecisionReason"]
        print(("OK   " if ok else "FEJL ") + "efter 3 runder: ny runde afvises og eskaleres til brugeren")
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
        for n in (1, 2, 3):
            kald("pretool", {**P, "tool_input": {"subagent_type": "byg-kontrol:projekt-kontrol", "prompt": "LEVERANCE: sag/projekt/01\nFASE: 1"}}, env)
            kald("subagentstop", {**P, "agent_type": "byg-kontrol:projekt-kontrol",
                                  "last_assistant_message": dom("sag/projekt/01", "afvist", blok_fund).replace('"vvs"', '"projekt"')}, env)
        forvent("projektkontrol: 4. forsøg afvises", kald("pretool", {**P, "tool_input": {"subagent_type": "byg-kontrol:projekt-kontrol", "prompt": "LEVERANCE: sag/projekt/01\nFASE: 1"}}, env), "afvist")
        (sag / "kvalitet" / "RCA-sag__projekt__01.md").write_text(HV + "Forbedring implementeret: ja\n", encoding="utf-8")
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
        forvent("fase 3 med godkendt designgrundlag tilladt",
                kald("pretool", {**P, "tool_input": {"subagent_type": PK, "prompt": f"LEVERANCE: sag/projekt/05\nFASE: 3\nDESIGNGRUNDLAG: {L3}, {L2}"}}, env), "tilladt")

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

    print(f"\n{'ALLE TESTS BESTÅET' if not FEJL else f'{len(FEJL)} FEJL'}")
    return 1 if FEJL else 0


if __name__ == "__main__":
    sys.exit(main())
