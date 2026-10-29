#!/usr/bin/env python3
"""Tests the byg-kontrol hook (review_gate.py) with simulated Claude Code events.

Run:  python3 tests/test_review_gate.py
"""
import json
import os
import pathlib
import subprocess
import sys
import tempfile

ROOT = pathlib.Path(__file__).resolve().parent.parent
GATE = ROOT / "plugins" / "byg-kontrol" / "hooks" / "review_gate.py"
ERRORS = []
REG = json.loads((GATE.parent / "fagregister.json").read_text(encoding="utf-8"))
MAX_ATTEMPTS = int(REG.get("maks_forsoeg", 3))
MAX_ROUNDS = int(REG.get("maks_runder", 3))


TRADE_AGENTS = ("vvs-mester", "el-installatoer", "murermester", "ventilationsekspert", "malermester", "toemrermester")


def call_raw(event: str, data: dict, env: dict) -> dict | None:
    r = subprocess.run([sys.executable, str(GATE), event], input=json.dumps(data), text=True,
                       capture_output=True, env=env, timeout=30)
    assert r.returncode == 0, r.stderr
    return json.loads(r.stdout) if r.stdout.strip() else None


def transcript(prompt: str, reply: str = "Notat skrevet.", handback: str | None = None) -> str:
    fd, path = tempfile.mkstemp(suffix=".jsonl")
    lines = [{"message": {"role": "user", "content": prompt}},
              {"message": {"role": "assistant", "content": [{"type": "text", "text": reply}]}}]
    if handback is not None:
        lines.append({"message": {"role": "assistant", "content": [
            {"type": "tool_use", "name": "SubagentHandback", "input": {"report": handback}}]}})
    with os.fdopen(fd, "w", encoding="utf-8") as fh:
        fh.write("\n".join(json.dumps(x, ensure_ascii=False) for x in lines))
    return path


def call(event: str, data: dict, env: dict) -> dict | None:
    """Like call_raw, but an allowed trade call is handed off at once (SubagentStop for the trade agent)."""
    r = call_raw(event, data, env)
    tool_input = data.get("tool_input") or {}
    agent_name = str(tool_input.get("subagent_type") or "")
    if event == "pretool" and r is None and agent_name.split(":")[-1] in TRADE_AGENTS:
        call_raw("subagentstop", {**{k: v for k, v in data.items() if k != "tool_input"}, "agent_type": agent_name,
                                  "agent_transcript_path": transcript(str(tool_input.get("prompt") or ""))}, env)
    return r


def verdict(deliv, outcome, findings, case_dir=None):
    chunk = {"leverance_id": deliv, "fag": "vvs", "dom": outcome, "fund": findings, "sagsmappe": case_dir}
    return "Kort vurdering.\n```json\n" + json.dumps(chunk, ensure_ascii=False) + "\n```"


def expect(name, result, kind):
    if kind == "tilladt":
        ok = result is None
    elif kind == "afvist":
        ok = bool(result) and result.get("hookSpecificOutput", {}).get("permissionDecision") == "deny"
    elif kind == "blokeret":
        ok = bool(result) and result.get("decision") == "block"
    else:
        ok = False
    print(("OK   " if ok else "FEJL ") + name + ("" if ok else f"  → {result}"))
    if not ok:
        ERRORS.append(name)


def main() -> int:
    with tempfile.TemporaryDirectory() as tmp:
        env = dict(os.environ, CLAUDE_PLUGIN_DATA=str(pathlib.Path(tmp) / "data"))
        cwd = pathlib.Path(tmp) / "projekt"
        case_dir = cwd / "byg-sager" / "2026-09-25-bad"
        case_dir.mkdir(parents=True)
        S = {"session_id": "s1", "cwd": str(cwd)}
        L = "2026-09-25-bad/vvs/01"
        FAG = "byg-vvs:vvs-mester"
        KON = "byg-kontrol:vvs-kontrol"
        chunk_findings = [{"id": "F1", "klasse": "væsentlig", "status": "aabent", "krav": "DS 439:2024 tæthedsprøvning",
                      "kilde": "ds.dk", "evidens": "Notatet nævner ingen tæthedsprøvning", "handling": "Tilføj hold point"}]

        expect("fagkald uden leverance-ID afvises", call("pretool", {**S, "tool_input": {"subagent_type": FAG, "prompt": "Vurdér"}}, env), "afvist")
        expect("andre agenter påvirkes ikke", call("pretool", {**S, "tool_input": {"subagent_type": "Explore", "prompt": "x"}}, env), "tilladt")
        expect("fagkald forsøg 1 tilladt", call("pretool", {**S, "tool_input": {"subagent_type": FAG, "prompt": f"LEVERANCE: {L}\nVurdér"}}, env), "tilladt")
        expect("nyt fagkald før kontrol afvises", call("pretool", {**S, "tool_input": {"subagent_type": FAG, "prompt": f"LEVERANCE: {L}"}}, env), "afvist")
        expect("forkert kontrolagent afvises", call("pretool", {**S, "tool_input": {"subagent_type": "byg-kontrol:el-kontrol", "prompt": f"LEVERANCE: {L}"}}, env), "afvist")
        expect("stop blokeres, mens leverance afventer kontrol", call("stop", S, env), "blokeret")
        expect("stop tilladt ved stop_hook_active", call("stop", {**S, "stop_hook_active": True}, env), "tilladt")

        for attempt in range(1, MAX_ATTEMPTS + 1):
            if attempt > 1:
                expect(f"fagkald forsøg {attempt} tilladt efter afvisning",
                        call("pretool", {**S, "tool_input": {"subagent_type": FAG, "prompt": f"LEVERANCE: {L}"}}, env), "tilladt")
            expect(f"kontrolkald forsøg {attempt} tilladt",
                    call("pretool", {**S, "tool_input": {"subagent_type": KON, "prompt": f"LEVERANCE: {L}"}}, env), "tilladt")
            if attempt == 1:
                invalid = verdict(L, "godkendt", [{"id": "F1", "klasse": "kritisk", "status": "nyt", "krav": "x"}])
                expect("ugyldig dom sendes retur", call("subagentstop", {**S, "agent_type": KON, "last_assistant_message": invalid}, env), "blokeret")
            expect(f"gyldig afvisning forsøg {attempt} registreres",
                    call("subagentstop", {**S, "agent_type": KON, "stop_hook_active": attempt == 1,
                                          "last_assistant_message": verdict(L, "afvist", chunk_findings, "byg-sager/2026-09-25-bad")}, env), "tilladt")

        expect(f"fagforsøg {MAX_ATTEMPTS + 1} afvises (maks. {MAX_ATTEMPTS})", call("pretool", {**S, "tool_input": {"subagent_type": FAG, "prompt": f"LEVERANCE: {L}"}}, env), "afvist")
        r = call("stop", S, env)
        expect("stop blokeres én gang for eskalering til brugeren", r, "blokeret")
        ok = bool(r) and "Ny runde" in r.get("reason", "") and "RCA" in r.get("reason", "")
        print(("OK   " if ok else "FEJL ") + "eskaleringen tilbyder brugeren en ny runde")
        if not ok:
            ERRORS.append("eskaleringstekst")
        expect("stop tilladt efter eskalering (ingen RCA krævet)", call("stop", S, env), "tilladt")
        expect("ny runde afvises uden brugerens 'Ny runde'",
                call("pretool", {**S, "tool_input": {"subagent_type": FAG, "prompt": f"LEVERANCE: {L}"}}, env), "afvist")
        r = call_raw("prompt", {**S, "prompt": f"Ny runde {L}"}, env)
        ok = bool(r) and "root cause" in r["hookSpecificOutput"]["additionalContext"]
        print(("OK   " if ok else "FEJL ") + "brugerens 'Ny runde' registreres og beder om RCA")
        if not ok:
            ERRORS.append(f"ny runde-prompt: {r}")
        expect("stop blokeres uden RCA, når brugeren har bedt om ny runde", call("stop", S, env), "blokeret")
        (case_dir / "kvalitet" / "RCA-2026-09-25-bad__vvs__01.md").write_text("# RCA\n", encoding="utf-8")
        expect("stop tilladt når RCA findes", call("stop", S, env), "tilladt")
        verdict_files = sorted(p.name for p in (case_dir / "kvalitet").glob("*.json"))
        ok = len(verdict_files) == MAX_ATTEMPTS
        print(("OK   " if ok else "FEJL ") + f"domme logget i sagsmappen ({len(verdict_files)})")
        if not ok:
            ERRORS.append("domfiler")

        expect("gentaget dom efter stop ignoreres",
                call("subagentstop", {**S, "agent_type": KON, "last_assistant_message": verdict(L, "afvist", chunk_findings, "byg-sager/2026-09-25-bad")}, env), "tilladt")
        ok = len(list((case_dir / "kvalitet").glob("*.json"))) == MAX_ATTEMPTS
        print(("OK   " if ok else "FEJL ") + "gentaget dom efter stop giver ingen ny domfil")
        if not ok:
            ERRORS.append("gentaget domfil")

        # New round after the user's "Ny runde" and an RCA with "Forbedring implementeret: ja"; at most MAX_ROUNDS rounds
        rca1 = case_dir / "kvalitet" / "RCA-2026-09-25-bad__vvs__01.md"
        expect("ny runde afvises uden implementeret forbedring",
                call("pretool", {**S, "tool_input": {"subagent_type": FAG, "prompt": f"LEVERANCE: {L}"}}, env), "afvist")
        rca1.write_text("# RCA\n**Forbedring implementeret:** ja\n", encoding="utf-8")
        expect("ny runde afvises uden 5 Why-kæde",
                call("pretool", {**S, "tool_input": {"subagent_type": FAG, "prompt": f"LEVERANCE: {L}"}}, env), "afvist")
        HV = "".join(f"{i}. Hvorfor x{i}? → y{i}\n" for i in range(1, 6)) + "**Grundårsag:** z\n"
        rca1.write_text("# RCA\n## 3. 5 Why\n" + HV + "## 6. Forbedring af fagagenten\n**Forbedring implementeret:** ja\n", encoding="utf-8")
        for r in range(2, MAX_ROUNDS + 1):
            if r > 2:
                call_raw("prompt", {**S, "prompt": f"ny runde {L}"}, env)
            expect(f"runde {r} starter med nyt fagkald",
                    call("pretool", {**S, "tool_input": {"subagent_type": FAG, "prompt": f"LEVERANCE: {L}"}}, env), "tilladt")
            for attempt in range(1, MAX_ATTEMPTS + 1):
                if attempt > 1:
                    call("pretool", {**S, "tool_input": {"subagent_type": FAG, "prompt": f"LEVERANCE: {L}"}}, env)
                call("pretool", {**S, "tool_input": {"subagent_type": KON, "prompt": f"LEVERANCE: {L}"}}, env)
                call("subagentstop", {**S, "agent_type": KON,
                                      "last_assistant_message": verdict(L, "afvist", chunk_findings, "byg-sager/2026-09-25-bad")}, env)
            ok = (case_dir / "kvalitet" / f"2026-09-25-bad__vvs__01__runde-{r}__forsoeg-{MAX_ATTEMPTS}.json").exists()
            print(("OK   " if ok else "FEJL ") + f"domfil for runde {r} har rundenummer")
            if not ok:
                ERRORS.append(f"domfil runde {r}")
            expect(f"forsøg {MAX_ATTEMPTS + 1} i runde {r} afvises",
                    call("pretool", {**S, "tool_input": {"subagent_type": FAG, "prompt": f"LEVERANCE: {L}"}}, env), "afvist")
            expect(f"stop blokeres for eskalering i runde {r}", call("stop", S, env), "blokeret")
            (case_dir / "kvalitet" / f"RCA-2026-09-25-bad__vvs__01__runde-{r}.md").write_text(
                "# RCA\n" + HV + "Forbedring implementeret: ja\n", encoding="utf-8")
            expect(f"stop tilladt med RCA for runde {r}", call("stop", S, env), "tilladt")
        r = call("pretool", {**S, "tool_input": {"subagent_type": FAG, "prompt": f"LEVERANCE: {L}"}}, env)
        ok = bool(r) and "nyt leverance-ID" in r["hookSpecificOutput"]["permissionDecisionReason"]
        print(("OK   " if ok else "FEJL ") + f"efter {MAX_ROUNDS} runder: ny runde afvises og eskaleres til brugeren")
        if not ok:
            ERRORS.append(f"runde 4: {r}")

        # A repeated verdict from a resumed review agent must not count as the next attempt
        L3 = "2026-09-25-bad/vvs/03"
        call("pretool", {**S, "tool_input": {"subagent_type": FAG, "prompt": f"LEVERANCE: {L3}"}}, env)
        call("pretool", {**S, "tool_input": {"subagent_type": KON, "prompt": f"LEVERANCE: {L3}"}}, env)
        old = verdict(L3, "afvist", chunk_findings, "byg-sager/2026-09-25-bad").replace('"dom":', '"forsoeg": 1, "dom":')
        call("subagentstop", {**S, "agent_type": KON, "last_assistant_message": old}, env)
        call("pretool", {**S, "tool_input": {"subagent_type": FAG, "prompt": f"LEVERANCE: {L3}"}}, env)
        call("subagentstop", {**S, "agent_type": KON, "last_assistant_message": old}, env)
        expect("gentaget dom før kontrolkald registreres ikke",
                call("pretool", {**S, "tool_input": {"subagent_type": FAG, "prompt": f"LEVERANCE: {L3}"}}, env), "afvist")
        call("pretool", {**S, "tool_input": {"subagent_type": KON, "prompt": f"LEVERANCE: {L3}"}}, env)
        call("subagentstop", {**S, "agent_type": KON, "last_assistant_message": old}, env)
        expect("dom med forkert forsøgsnummer registreres ikke",
                call("pretool", {**S, "tool_input": {"subagent_type": FAG, "prompt": f"LEVERANCE: {L3}"}}, env), "afvist")
        ok = not (case_dir / "kvalitet" / "2026-09-25-bad__vvs__03__forsoeg-2.json").exists()
        print(("OK   " if ok else "FEJL ") + "ingen domfil for forsøg 2 ved forældet dom")
        if not ok:
            ERRORS.append("forældet domfil")
        new = verdict(L3, "godkendt", [], "byg-sager/2026-09-25-bad").replace('"dom":', '"forsoeg": 2, "dom":')
        call("subagentstop", {**S, "agent_type": KON, "last_assistant_message": new}, env)
        ok = (case_dir / "kvalitet" / "2026-09-25-bad__vvs__03__forsoeg-2.json").exists()
        print(("OK   " if ok else "FEJL ") + "dom med rigtigt forsøgsnummer registreres")
        if not ok:
            ERRORS.append("aktuel dom")

        L2 = "2026-09-25-bad/vvs/02"
        call("pretool", {**S, "tool_input": {"subagent_type": FAG, "prompt": f"LEVERANCE: {L2}"}}, env)
        call("pretool", {**S, "tool_input": {"subagent_type": KON, "prompt": f"LEVERANCE: {L2}"}}, env)
        expect("godkendt dom registreres", call("subagentstop", {**S, "agent_type": KON, "last_assistant_message": verdict(L2, "godkendt", [])}, env), "tilladt")
        expect("ændring af godkendt leverance kræver nyt ID", call("pretool", {**S, "tool_input": {"subagent_type": FAG, "prompt": f"LEVERANCE: {L2}"}}, env), "afvist")

        expect("ekstern gennemgang tilladt", call("pretool", {**S, "tool_input": {"subagent_type": KON, "prompt": "LEVERANCE: ekstern/tilbud-vvs"}}, env), "tilladt")
        call("subagentstop", {**S, "agent_type": KON, "last_assistant_message": verdict("ekstern/tilbud-vvs", "afvist", chunk_findings)}, env)
        expect("ekstern afvisning blokerer ikke stop", call("stop", S, env), "tilladt")

        SAM = {"session_id": "s2", "cwd": str(cwd)}
        expect("samlet plugin: fagkald tilladt", call("pretool", {**SAM, "tool_input": {"subagent_type": "byg:el-installatoer", "prompt": "LEVERANCE: x/el/01"}}, env), "tilladt")
        r = call("stop", SAM, env)
        ok = bool(r) and "byg:el-kontrol" in r.get("reason", "")
        print(("OK   " if ok else "FEJL ") + "samlet plugin peger på byg:el-kontrol")
        if not ok:
            ERRORS.append("samlet navn")

        P = {"session_id": "s3", "cwd": str(cwd)}
        for n in range(1, MAX_ATTEMPTS + 1):
            call("pretool", {**P, "tool_input": {"subagent_type": "byg-kontrol:projekt-kontrol", "prompt": "LEVERANCE: sag/projekt/01\nFASE: 1"}}, env)
            call("subagentstop", {**P, "agent_type": "byg-kontrol:projekt-kontrol",
                                  "last_assistant_message": verdict("sag/projekt/01", "afvist", chunk_findings).replace('"vvs"', '"projekt"')}, env)
        expect(f"projektkontrol: forsøg {MAX_ATTEMPTS + 1} afvises", call("pretool", {**P, "tool_input": {"subagent_type": "byg-kontrol:projekt-kontrol", "prompt": "LEVERANCE: sag/projekt/01\nFASE: 1"}}, env), "afvist")
        (case_dir / "kvalitet" / "RCA-sag__projekt__01.md").write_text(HV + "Forbedring implementeret: ja\n", encoding="utf-8")
        expect("projektkontrol: runde 2 afvises uden brugerens 'Ny runde'",
                call("pretool", {**P, "tool_input": {"subagent_type": "byg-kontrol:projekt-kontrol", "prompt": "LEVERANCE: sag/projekt/01\nFASE: 1"}}, env), "afvist")
        call_raw("prompt", {**P, "prompt": "Ny runde sag/projekt/01"}, env)
        expect("projektkontrol: runde 2 starter efter RCA med forbedring",
                call("pretool", {**P, "tool_input": {"subagent_type": "byg-kontrol:projekt-kontrol", "prompt": "LEVERANCE: sag/projekt/01\nFASE: 1"}}, env), "tilladt")

        # Phase gate: a plan deliverable in phase 3 requires an approved design basis
        PK = "byg-kontrol:projekt-kontrol"
        expect("projektkontrol uden FASE afvises",
                call("pretool", {**P, "tool_input": {"subagent_type": PK, "prompt": "LEVERANCE: sag/projekt/05"}}, env), "afvist")
        expect("fase 3 uden DESIGNGRUNDLAG afvises",
                call("pretool", {**P, "tool_input": {"subagent_type": PK, "prompt": "LEVERANCE: sag/projekt/05\nFASE: 3"}}, env), "afvist")
        expect("fase 3 med ikke-godkendt designgrundlag afvises",
                call("pretool", {**P, "tool_input": {"subagent_type": PK, "prompt": f"LEVERANCE: sag/projekt/05\nFASE: 3\nDESIGNGRUNDLAG: {L3}, {L}"}}, env), "afvist")
        LP = "2026-09-25-bad/projekt/05"
        expect("fase 3 uden brugerens G2-godkendelse afvises",
                call("pretool", {**P, "tool_input": {"subagent_type": PK, "prompt": f"LEVERANCE: {LP}\nFASE: 3\nDESIGNGRUNDLAG: {L3}, {L2}"}}, env), "afvist")
        expect("fagkald i fase 3 uden G2 afvises",
                call("pretool", {**P, "tool_input": {"subagent_type": FAG, "prompt": "LEVERANCE: 2026-09-25-bad/vvs/09\nFASE: 3"}}, env), "afvist")
        r = call("prompt", {**P, "prompt": "Det ser fint ud. Godkend G2 2026-09-25-bad"}, env)
        ok = bool(r) and "G2" in r.get("hookSpecificOutput", {}).get("additionalContext", "")
        print(("OK   " if ok else "FEJL ") + "brugerens 'Godkend G2 <sag>' registreres")
        if not ok:
            ERRORS.append(f"G2 prompt: {r}")
        expect("fase 3 med G2 og godkendt designgrundlag tilladt",
                call("pretool", {**P, "tool_input": {"subagent_type": PK, "prompt": f"LEVERANCE: {LP}\nFASE: 3\nDESIGNGRUNDLAG: {L3}, {L2}"}}, env), "tilladt")
        expect("designgrundlag uden for det G2-godkendte design afvises",
                call("pretool", {**P, "tool_input": {"subagent_type": PK, "prompt": f"LEVERANCE: 2026-09-25-bad/projekt/06\nFASE: 3\nDESIGNGRUNDLAG: {L3}, 2026-09-25-bad/vvs/07"}}, env), "afvist")
        expect("almindelig brugerprompt påvirkes ikke", call("prompt", {**P, "prompt": "Hvad koster det?"}, env), "tilladt")

        # Context budget: reminder when a byg session's main thread passes 200k and then every 100k
        def main_thread(n: int) -> str:
            fd, path = tempfile.mkstemp(suffix=".jsonl")
            lines = [{"type": "user", "message": {"role": "user", "content": "x"}},
                      {"type": "assistant", "message": {"role": "assistant", "content": [{"type": "text", "text": "y"}],
                       "usage": {"input_tokens": 5, "cache_creation_input_tokens": 995, "cache_read_input_tokens": n - 1000}}},
                      {"type": "assistant", "isSidechain": True, "message": {"role": "assistant", "content": [],
                       "usage": {"input_tokens": 5, "cache_read_input_tokens": 10}}}]
            with os.fdopen(fd, "w", encoding="utf-8") as fh:
                fh.write("\n".join(json.dumps(x) for x in lines))
            return path

        def reminded(r) -> bool:
            return bool(r) and "ny session" in r.get("systemMessage", "") and \
                "Kontekstbudget" in r.get("hookSpecificOutput", {}).get("additionalContext", "")

        for name, sid, n, expected in [
                ("kontekst under 200k giver ingen påmindelse", "s3", 150_000, False),
                ("kontekst over 200k giver påmindelse", "s3", 250_000, True),
                ("samme trin giver ikke påmindelse igen", "s3", 280_000, False),
                ("næste trin (300k+) giver ny påmindelse", "s3", 320_000, True),
                ("session uden byg-leverancer påvirkes ikke", "s9", 500_000, False)]:
            r = call("prompt", {"session_id": sid, "cwd": str(cwd), "prompt": "Næste spørgsmål",
                                "transcript_path": main_thread(n)}, env)
            ok = reminded(r) == expected
            print(("OK   " if ok else "FEJL ") + name)
            if not ok:
                ERRORS.append(f"{name}: {r}")

        # Safe compact: PreCompact gives summary instructions, SessionStart(compact) reloads the case
        (case_dir / "status.md").write_text("# Status\nFase: 2\nNæste skridt: tæthedsprøvning\n" + "x" * 20_000, encoding="utf-8")

        def compact_call(event: str, data: dict) -> str:
            r = subprocess.run([sys.executable, str(GATE), event], input=json.dumps(data), text=True,
                               capture_output=True, env=env, timeout=30)
            assert r.returncode == 0, r.stderr
            return r.stdout

        for name, ok in [
                ("precompact i byg-session beder om at bevare leverance-ID'er",
                 "leverance-ID" in compact_call("precompact", {**S, "trigger": "auto"})),
                ("precompact uden byg-sag giver intet", compact_call("precompact", {"session_id": "s9", "cwd": str(cwd)}) == "")]:
            print(("OK   " if ok else "FEJL ") + name)
            if not ok:
                ERRORS.append(name)
        C = {"session_id": "s5", "cwd": str(cwd)}
        call_raw("pretool", {**C, "tool_input": {"subagent_type": FAG, "prompt": "LEVERANCE: 2026-09-25-bad/vvs/09"}}, env)
        out = compact_call("efter_compact", {**C, "source": "compact"})
        ctx = json.loads(out)["hookSpecificOutput"]["additionalContext"] if out.strip() else ""
        for name, ok in [
                ("efter compact genindlæses status.md", "Næste skridt: tæthedsprøvning" in ctx),
                ("efter compact afkortes en lang status.md", "afkortet" in ctx and len(ctx) < 16_000),
                ("efter compact vises åbne leverancer fra tilstanden", "2026-09-25-bad/vvs/09: fagkald_igang" in ctx),
                ("efter compact uden byg-sag giver intet",
                 compact_call("efter_compact", {"session_id": "s9", "cwd": str(cwd), "source": "compact"}) == ""),
                ("efter compact i sagsmappen uden leverancer genindlæses status.md",
                 "tæthedsprøvning" in compact_call("efter_compact", {"session_id": "s9", "cwd": str(case_dir), "source": "compact"}))]:
            print(("OK   " if ok else "FEJL ") + name)
            if not ok:
                ERRORS.append(f"{name}: {ctx[:300]}")

        # Finding lock-in: a new blocking finding in attempt 2 requires nyt_grundlag
        L4 = "2026-09-25-bad/vvs/04"
        call("pretool", {**S, "tool_input": {"subagent_type": FAG, "prompt": f"LEVERANCE: {L4}"}}, env)
        call("pretool", {**S, "tool_input": {"subagent_type": KON, "prompt": f"LEVERANCE: {L4}"}}, env)
        call("subagentstop", {**S, "agent_type": KON, "last_assistant_message": verdict(L4, "afvist", chunk_findings, "byg-sager/2026-09-25-bad")}, env)
        call("pretool", {**S, "tool_input": {"subagent_type": FAG, "prompt": f"LEVERANCE: {L4}"}}, env)
        call("pretool", {**S, "tool_input": {"subagent_type": KON, "prompt": f"LEVERANCE: {L4}"}}, env)
        new_finding = [{**chunk_findings[0], "id": "F9", "status": "nyt"}]
        expect("nyt væsentligt fund i forsøg 2 uden nyt_grundlag sendes retur",
                call("subagentstop", {**S, "agent_type": KON, "last_assistant_message": verdict(L4, "afvist", new_finding)}, env), "blokeret")
        expect("nyt væsentligt fund i forsøg 2 med nyt_grundlag=regression registreres",
                call("subagentstop", {**S, "agent_type": KON, "stop_hook_active": True,
                                      "last_assistant_message": verdict(L4, "afvist", [{**new_finding[0], "nyt_grundlag": "regression"}])}, env), "tilladt")

        # Trade call in progress: stop does not block, retry does not count, handoff gives afventer_kontrol
        G = {"session_id": "s4", "cwd": str(cwd)}
        LG = "2026-09-25-bad/vvs/07"
        expect("fagkald (uden aflevering) tilladt", call_raw("pretool", {**G, "tool_input": {"subagent_type": FAG, "prompt": f"LEVERANCE: {LG}"}}, env), "tilladt")
        expect("stop blokerer ikke, mens fagkald er i gang", call("stop", G, env), "tilladt")
        expect("genforsøg af afbrudt fagkald tilladt", call_raw("pretool", {**G, "tool_input": {"subagent_type": FAG, "prompt": f"LEVERANCE: {LG}"}}, env), "tilladt")
        state = json.loads((pathlib.Path(env["CLAUDE_PLUGIN_DATA"]) / "kontrol" / "tilstand.json").read_text(encoding="utf-8"))
        ok = state["leverancer"][LG]["forsoeg"] == 1
        print(("OK   " if ok else "FEJL ") + "genforsøg tæller ikke som nyt forsøg")
        if not ok:
            ERRORS.append("genforsøg")
        call_raw("subagentstop", {**G, "agent_type": FAG, "agent_transcript_path": transcript(f"LEVERANCE: {LG}\nOpgave")}, env)
        expect("efter aflevering blokerer stop (afventer kontrol)", call("stop", G, env), "blokeret")

        # A verdict in the hand-back (tool_use input) is registered without a return
        expect("kontrolkald med sti til manglende notat afvises", call("pretool", {**G, "tool_input": {"subagent_type": KON, "prompt":
                f"LEVERANCE: {LG}\nLeverance: {case_dir}/fagnotater/vvs-07.md"}}, env), "afvist")
        (case_dir / "fagnotater").mkdir(exist_ok=True)
        (case_dir / "fagnotater" / "vvs-07.md").write_text("# Fagnotat\n", encoding="utf-8")
        expect("kontrolkald med sti", call("pretool", {**G, "tool_input": {"subagent_type": KON, "prompt":
                f"LEVERANCE: {LG}\nLeverance: {case_dir}/fagnotater/vvs-07.md"}}, env), "tilladt")
        hb = verdict(LG, "godkendt", [], "byg-sager/2026-09-25-bad")
        expect("dom i hand-back registreres", call("subagentstop", {**G, "agent_type": KON, "last_assistant_message": "Rapport afleveret.",
                "agent_transcript_path": transcript("x", handback=hb)}, env), "tilladt")
        state = json.loads((pathlib.Path(env["CLAUDE_PLUGIN_DATA"]) / "kontrol" / "tilstand.json").read_text(encoding="utf-8"))
        ok = state["leverancer"][LG]["status"] == "godkendt"
        print(("OK   " if ok else "FEJL ") + "hand-back-dom gav status godkendt")
        if not ok:
            ERRORS.append("handback")

        # Protection of an approved note
        fpath = str(case_dir / "fagnotater" / "vvs-07.md")
        expect("subagent må ikke rette godkendt notat", call("beskyt", {**G, "agent_type": "byg-murer:murermester",
                "tool_input": {"file_path": fpath}}, env), "afvist")
        r = call("beskyt", {**G, "tool_input": {"file_path": fpath}}, env)
        ok = bool(r) and "systemMessage" in r and "hookSpecificOutput" in r and r["hookSpecificOutput"].get("permissionDecision") is None
        print(("OK   " if ok else "FEJL ") + "hovedtråden får advarsel ved godkendt notat")
        if not ok:
            ERRORS.append(f"beskyt hovedtråd: {r}")
        expect("andre filer påvirkes ikke", call("beskyt", {**G, "agent_type": "x", "tool_input": {"file_path": str(case_dir / "andet.md")}}, env), "tilladt")

        # One writer per file also applies to temporary question folders in ~/byg-tmp/
        tmp_case = pathlib.Path(tmp) / "byg-tmp" / "2026-10-18-spoergsmaal"
        expect("fagagent må ikke skrive fremmed fil i byg-tmp", call("beskyt", {**G, "agent_type": "byg-vvs:vvs-mester",
                "tool_input": {"file_path": str(tmp_case / "projektgrundlag.md")}}, env), "afvist")
        expect("fagagent må skrive eget notat i byg-tmp", call("beskyt", {**G, "agent_type": "byg-vvs:vvs-mester",
                "tool_input": {"file_path": str(tmp_case / "fagnotater" / "vvs.md")}}, env), "tilladt")

        # Manual status without CLAUDE_PLUGIN_DATA must find the plugin's data folder under ~/.claude/plugins/data/
        home = pathlib.Path(tmp) / "hjem"
        pdata = home / ".claude" / "plugins" / "data" / "byg-kontrol-test" / "kontrol"
        pdata.mkdir(parents=True)
        (pdata / "tilstand.json").write_text(json.dumps({"leverancer": {"sag/vvs/09": {
            "fag": "vvs", "status": "godkendt", "forsoeg": 1}}}), encoding="utf-8")
        env_manual = {k: v for k, v in os.environ.items() if k != "CLAUDE_PLUGIN_DATA"}
        env_manual["HOME"] = str(home)
        r = subprocess.run([sys.executable, str(GATE), "status"], text=True, capture_output=True, env=env_manual, timeout=30)
        ok = r.returncode == 0 and "sag/vvs/09" in r.stdout
        print(("OK   " if ok else "FEJL ") + "manuel status finder pluginets datamappe")
        if not ok:
            ERRORS.append(f"manuel status: {r.stdout or r.stderr}")

        # Helper agent (drawing import): trade → comparison → correction → comparison → review
        B = {"session_id": "s4", "cwd": str(cwd)}
        LB = "2026-09-25-bad/bim/01"
        BF, BS, BK = "byg-bim:bim-modelloer", "byg-bim:bim-sammenligner", "byg-kontrol:bim-kontrol"

        def bim_trade(name, expected):
            r = call_raw("pretool", {**B, "tool_input": {"subagent_type": BF, "prompt": f"LEVERANCE: {LB}\nByg"}}, env)
            expect(name, r, expected)
            if r is None:
                call_raw("subagentstop", {**B, "agent_type": BF, "agent_transcript_path": transcript(f"LEVERANCE: {LB}")}, env)

        def bim_compare(name, expected, result="ret"):
            r = call_raw("pretool", {**B, "tool_input": {"subagent_type": BS, "prompt": f"LEVERANCE: {LB}\nSammenlign"}}, env)
            expect(name, r, expected)
            if r is None:
                reply = '```json\n{"resultat": "%s", "afvigelser": []}\n```' % result
                call_raw("subagentstop", {**B, "agent_type": BS, "last_assistant_message": reply,
                                          "agent_transcript_path": transcript(f"LEVERANCE: {LB}", reply)}, env)

        expect("sammenligning uden leverance-ID afvises",
                call_raw("pretool", {**B, "tool_input": {"subagent_type": BS, "prompt": "Sammenlign"}}, env), "afvist")
        expect("sammenligning før fagleverance afvises",
                call_raw("pretool", {**B, "tool_input": {"subagent_type": BS, "prompt": f"LEVERANCE: {LB}"}}, env), "afvist")
        bim_trade("bim-fagkald tilladt", "tilladt")
        bim_trade("nyt bim-fagkald uden sammenligning afvises", "afvist")
        bim_compare("sammenligning 1 tilladt", "tilladt")
        expect("stop blokeres efter sammenligning med afvigelser", call_raw("stop", B, env), "blokeret")
        bim_trade("rettelse efter sammenligning tilladt", "tilladt")
        bim_compare("sammenligning 2 tilladt", "tilladt")
        bim_trade("rettelse 2 tilladt", "tilladt")
        bim_compare("sammenligning 3 tilladt", "tilladt", result="ok")
        bim_trade("rettelse 3 tilladt", "tilladt")
        bim_compare("4. sammenligning afvises (maks. 3)", "afvist")
        expect("kontrol efter sammenligninger tilladt",
                call_raw("pretool", {**B, "tool_input": {"subagent_type": BK, "prompt": f"LEVERANCE: {LB}"}}, env), "tilladt")
        state = json.loads((pathlib.Path(env["CLAUDE_PLUGIN_DATA"]) / "kontrol" / "tilstand.json").read_text(encoding="utf-8"))
        eb = state["leverancer"][LB]
        ok = eb.get("forsoeg") == 1 and eb.get("sammenligninger") == 3 and eb.get("rettelser") == 3
        print(("OK   " if ok else "FEJL ") + "rettelser efter sammenligning bruger ikke kontrolforsøg")
        if not ok:
            ERRORS.append(f"hjælpertilstand: {eb}")

        # afklar_med_bruger: validated, does not block
        LA = "2026-09-25-bad/vvs/20"
        A = {"session_id": "s-afk", "cwd": str(cwd)}
        call("pretool", {**A, "tool_input": {"subagent_type": FAG, "prompt": f"LEVERANCE: {LA}"}}, env)
        call_raw("pretool", {**A, "tool_input": {"subagent_type": KON, "prompt": f"LEVERANCE: {LA}"}}, env)
        def clarify_verdict(entries):
            chunk = {"leverance_id": LA, "fag": "vvs", "dom": "godkendt", "fund": [], "afklar_med_bruger": entries}
            return "OK.\n```json\n" + json.dumps(chunk, ensure_ascii=False) + "\n```"
        expect("afklar_med_bruger uden spoergsmaal sendes retur", call_raw("subagentstop", {**A, "agent_type": KON,
                "last_assistant_message": clarify_verdict([{"betydning": "x"}])}, env), "blokeret")
        expect("godkendt dom med afklar_med_bruger registreres", call_raw("subagentstop", {**A, "agent_type": KON,
                "stop_hook_active": True, "last_assistant_message": clarify_verdict([{"spoergsmaal": "Bliver radiatoren?",
                "betydning": "shuntens størrelse"}])}, env), "tilladt")
        state = json.loads((pathlib.Path(env["CLAUDE_PLUGIN_DATA"]) / "kontrol" / "tilstand.json").read_text(encoding="utf-8"))
        ea = state["leverancer"][LA]
        ok = ea["status"] == "godkendt" and ea["domme"][-1].get("afklar_med_bruger") == 1
        print(("OK   " if ok else "FEJL ") + "afklar_med_bruger blokerer ikke og tælles i dommen")
        if not ok:
            ERRORS.append(f"afklar: {ea}")

        # ikke_kontrolleret: validated, saved and mentioned when the deliverable is reused
        LI = "2026-09-25-bad/vvs/22"
        I = {"session_id": "s-ik", "cwd": str(cwd)}
        call("pretool", {**I, "tool_input": {"subagent_type": FAG, "prompt": f"LEVERANCE: {LI}"}}, env)
        call_raw("pretool", {**I, "tool_input": {"subagent_type": KON, "prompt": f"LEVERANCE: {LI}"}}, env)
        def unchecked_verdict(entries):
            chunk = {"leverance_id": LI, "fag": "vvs", "dom": "godkendt", "fund": [], "ikke_kontrolleret": entries}
            return "OK.\n```json\n" + json.dumps(chunk, ensure_ascii=False) + "\n```"
        expect("ikke_kontrolleret som tekst i stedet for liste sendes retur", call_raw("subagentstop", {**I,
                "agent_type": KON, "last_assistant_message": unchecked_verdict("bilag")}, env), "blokeret")
        expect("godkendt dom med ikke_kontrolleret registreres", call_raw("subagentstop", {**I, "agent_type": KON,
                "stop_hook_active": True, "last_assistant_message": unchecked_verdict(["bilag vvs-bilag.md, trykfald"])}, env),
                "tilladt")
        state = json.loads((pathlib.Path(env["CLAUDE_PLUGIN_DATA"]) / "kontrol" / "tilstand.json").read_text(encoding="utf-8"))
        ei = state["leverancer"][LI]
        ok = ei["status"] == "godkendt" and ei["domme"][-1].get("ikke_kontrolleret") == ["bilag vvs-bilag.md, trykfald"]
        print(("OK   " if ok else "FEJL ") + "ikke_kontrolleret gemmes i dommen")
        if not ok:
            ERRORS.append(f"ikke_kontrolleret: {ei}")
        r = call_raw("pretool", {**I, "tool_input": {"subagent_type": FAG, "prompt": f"LEVERANCE: {LI}"}}, env)
        reason = str((r or {}).get("hookSpecificOutput", {}).get("permissionDecisionReason", ""))
        ok = "dækker ikke: bilag vvs-bilag.md, trykfald" in reason
        print(("OK   " if ok else "FEJL ") + "godkendt-besked nævner det ikke kontrollerede")
        if not ok:
            ERRORS.append(f"ikke_kontrolleret-besked: {r}")

        # KONTROLNIVEAU: fuld requires Opus in the review call
        LF = "2026-09-25-bad/vvs/21"
        F = {"session_id": "s-fuld", "cwd": str(cwd)}
        call("pretool", {**F, "tool_input": {"subagent_type": FAG, "prompt": f"LEVERANCE: {LF}"}}, env)
        expect("fuld kontrol uden model opus afvises", call_raw("pretool", {**F, "tool_input": {
            "subagent_type": KON, "prompt": f"LEVERANCE: {LF}\nKONTROLNIVEAU: fuld"}}, env), "afvist")
        expect("fuld kontrol med model opus tilladt", call_raw("pretool", {**F, "tool_input": {
            "subagent_type": KON, "model": "opus", "prompt": f"LEVERANCE: {LF}\nKONTROLNIVEAU: fuld"}}, env), "tilladt")

        # Workflow in byg-sager only when the user's latest message mentions workflow
        W = {"session_id": "s-wf", "cwd": str(cwd / "byg-sager" / "2026-09-25-bad")}
        call_raw("prompt", {**W, "prompt": "Forsæt"}, env)
        expect("workflow afvises efter 'Forsæt'", call_raw("workflow", {**W, "tool_input": {}}, env), "afvist")
        call_raw("prompt", {**W, "prompt": "Brug et workflow til at sammenligne tilbuddene"}, env)
        expect("workflow tilladt, når brugeren beder om det", call_raw("workflow", {**W, "tool_input": {}}, env), "tilladt")
        call_raw("prompt", {**W, "prompt": "fortsæt"}, env)
        expect("workflow afvises igen ved næste besked uden 'workflow'", call_raw("workflow", {**W, "tool_input": {}}, env), "afvist")
        expect("workflow uden for byg-sager påvirkes ikke",
                call_raw("workflow", {"session_id": "s-andet", "cwd": str(pathlib.Path(tmp)), "tool_input": {}}, env), "tilladt")

        # Tool review (bim): comparison ok + clean check approves without a review agent
        V = {"session_id": "s-vaerk", "cwd": str(cwd)}
        LV = "2026-09-25-bad/bim/02"
        expect("værktøj afvises for vvs", call_raw("pretool", {**V, "tool_input": {
            "subagent_type": FAG, "prompt": "LEVERANCE: 2026-09-25-bad/vvs/40\nKONTROLNIVEAU: værktøj"}}, env), "afvist")

        def tool_trade(name, prompt):
            r = call_raw("pretool", {**V, "tool_input": {"subagent_type": BF, "prompt": prompt}}, env)
            expect(name, r, "tilladt")
            call_raw("subagentstop", {**V, "agent_type": BF, "agent_transcript_path": transcript(prompt)}, env)

        def tool_compare(name, result, check):
            r = call_raw("pretool", {**V, "tool_input": {"subagent_type": BS, "prompt": f"LEVERANCE: {LV}"}}, env)
            expect(name, r, "tilladt")
            reply = '```json\n{"resultat": "%s", "tjek": %s, "afvigelser": []}\n```' % (result, json.dumps(check))
            call_raw("subagentstop", {**V, "agent_type": BS, "last_assistant_message": reply,
                                      "agent_transcript_path": transcript(f"LEVERANCE: {LV}", reply)}, env)

        def tool_status():
            t = json.loads((pathlib.Path(env["CLAUDE_PLUGIN_DATA"]) / "kontrol" / "tilstand.json").read_text(encoding="utf-8"))
            return t["leverancer"][LV]

        tool_trade("bim-fagkald med KONTROLNIVEAU: værktøj tilladt", f"LEVERANCE: {LV}\nKONTROLNIVEAU: værktøj\nByg")
        tool_compare("værktøj: sammenligning 1 tilladt", "ok", {"fejl": 0, "advarsler": 3, "sporbarhed": 2})
        ok = tool_status()["status"] == "sammenlignet"
        print(("OK   " if ok else "FEJL ") + "værktøj: ok med sporbarhedsfund godkendes ikke")
        if not ok:
            ERRORS.append(f"værktøj sporbarhed: {tool_status()}")
        expect("værktøj: stop blokeres, til leverancen er godkendt", call_raw("stop", V, env), "blokeret")
        tool_trade("værktøj: rettelse tilladt", f"LEVERANCE: {LV}\nRet sporbarheden")
        tool_compare("værktøj: sammenligning 2 tilladt", "ok", {"fejl": 0, "advarsler": 3, "sporbarhed": 0})
        ev = tool_status()
        ok = ev["status"] == "godkendt" and ev.get("godkendt_af") == "vaerktoej" and ev.get("forsoeg") == 1
        print(("OK   " if ok else "FEJL ") + "værktøj: ok og rent tjek godkender uden kontrolagent")
        if not ok:
            ERRORS.append(f"værktøj godkendelse: {ev}")
        verdict_files = list((case_dir / "kvalitet").glob("*bim__02*vaerktoej.json"))
        print(("OK   " if verdict_files else "FEJL ") + "værktøj: godkendelsen gemmes som dom i kvalitet/")
        if not verdict_files:
            ERRORS.append("værktøj: ingen domfil")
        expect("værktøj: stop tilladt efter godkendelse", call("stop", V, env), "tilladt")
        expect("værktøj: ny version kræver nyt ID", call_raw("pretool", {**V, "tool_input": {
            "subagent_type": BF, "prompt": f"LEVERANCE: {LV}"}}, env), "afvist")

        # Sample review: only questions without FASE, never el/statik; the outcome is deterministic per deliverable ID
        import hashlib
        sample = REG.get("stikproeve") or {}
        def sampled(deliv):
            return int(hashlib.sha256(deliv.encode("utf-8")).hexdigest(), 16) % 1000 < round(float(sample.get("andel", 1)) * 1000)
        candidates = [f"2026-10-20-spm-{i}/murer/01" for i in range(60)]
        LI = next(x for x in candidates if not sampled(x))
        LU = next(x for x in candidates if sampled(x))
        MUR, MKON = "byg-murer:murermester", "byg-kontrol:murer-kontrol"
        expect("stikprøve afvises for el", call_raw("pretool", {"session_id": "s-stik0", "cwd": str(cwd), "tool_input": {
            "subagent_type": "byg-el:el-installatoer", "prompt": "LEVERANCE: 2026-10-20-spm/el/01\nKONTROLNIVEAU: stikprøve"}}, env), "afvist")
        expect("stikprøve afvises i en sag med FASE", call_raw("pretool", {"session_id": "s-stik0", "cwd": str(cwd), "tool_input": {
            "subagent_type": MUR, "prompt": "LEVERANCE: 2026-09-25-bad/murer/31\nFASE: 1 · KONTROLNIVEAU: stikprøve"}}, env), "afvist")
        I = {"session_id": "s-stik1", "cwd": str(cwd)}
        expect("stikprøve: fagkald tilladt", call("pretool", {**I, "tool_input": {
            "subagent_type": MUR, "prompt": f"LEVERANCE: {LI}\nKONTROLNIVEAU: stikprøve"}}, env), "tilladt")
        state = json.loads((pathlib.Path(tmp) / "data" / "kontrol" / "tilstand.json").read_text(encoding="utf-8"))
        ok = state["leverancer"][LI]["status"] == "ikke_udtaget"
        print(("OK   " if ok else "FEJL ") + "ikke udtaget: afleveret uden kontrol")
        if not ok:
            ERRORS.append(f"stikprøve status: {state['leverancer'][LI]}")
        expect("ikke udtaget: kontrolkald afvises med besked", call_raw("pretool", {**I, "tool_input": {
            "subagent_type": MKON, "prompt": f"LEVERANCE: {LI}"}}, env), "afvist")
        expect("ikke udtaget: stop blokerer ikke", call("stop", I, env), "tilladt")
        expect("ikke udtaget: ny version kræver nyt ID", call_raw("pretool", {**I, "tool_input": {
            "subagent_type": MUR, "prompt": f"LEVERANCE: {LI}"}}, env), "afvist")
        U = {"session_id": "s-stik2", "cwd": str(cwd)}
        call("pretool", {**U, "tool_input": {"subagent_type": MUR, "prompt": f"LEVERANCE: {LU}\nKONTROLNIVEAU: stikprøve"}}, env)
        expect("udtaget: stop blokeres, til kontrollen er kørt", call("stop", U, env), "blokeret")
        expect("udtaget: kontrolkald tilladt", call_raw("pretool", {**U, "tool_input": {
            "subagent_type": MKON, "prompt": f"LEVERANCE: {LU}"}}, env), "tilladt")

    print(f"\n{'ALLE TESTS BESTÅET' if not ERRORS else f'{len(ERRORS)} FEJL'}")
    return 1 if ERRORS else 0


if __name__ == "__main__":
    sys.exit(main())
