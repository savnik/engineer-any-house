#!/usr/bin/env python3
"""byg-kontrol: håndhæver det uafhængige kvalitetskontrol-loop (plugin-hook til Claude Code/Cowork).

Fra hooks/hooks.json:  python3 kontrol_gate.py pretool | beskyt | subagentstop | prompt | stop   (hook-input på stdin)
Manuelt:               python3 kontrol_gate.py status
                       python3 kontrol_gate.py nulstil <leverance-id>
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
  Ugyldig dom → kontrolagenten sendes tilbage én gang for at rette den.
- Højst 3 forsøg pr. runde. Tredje afviste dom → "stoppet": root cause-analyse af, hvorfor fagagenten
  ikke leverede korrekt i første forsøg, og implementeret forbedring af fagagenten.
- Ny runde (højst 3 runder): et nyt fagkald under samme leverance-ID starter runde n+1 med forsøg 1,
  når RCA-filen for runden findes med en 5 Why-kæde (mindst fem nummererede "Hvorfor"-linjer og en
  "Grundårsag") og linjen "Forbedring implementeret: ja".
  Efter sidste runde: eskalering til brugeren, og leverancen kan kun genoptages under et nyt leverance-ID.
- Stop-hooken forhindrer (én gang pr. stop) afslutning, mens sessionens leverancer mangler kontrol,
  er afvist eller mangler RCA.
- Kontrolkald med et ukendt ID behandles som gennemgang af eksternt materiale (uden loop).
- Hjælpeagenter (fagregister: "hjaelpere", fx bim-sammenligner): et hjælpekald kræver LEVERANCE og en afleveret
  fagversion ("afventer_kontrol" eller "sammenlignet") og sætter "under_sammenligning"; ved aflevering bliver den
  "sammenlignet". Et fagkald efter en sammenligning er en rettelse: det bruger ikke af kontrolforsøgene. Højst
  "maks_sammenligninger" (standard 3) sammenligninger pr. leverance. Kontrollen kan kaldes efter sammenligningen.
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
Fail-safe: uventede fejl blokerer aldrig – de logges i <data>/kontrol/log.jsonl.
"""
import json
import os
import pathlib
import re
import sys
import time
import traceback

HER = pathlib.Path(__file__).resolve().parent
REG = json.loads((HER / "fagregister.json").read_text(encoding="utf-8"))
MAKS = int(REG.get("maks_forsoeg", 3))
MAKS_RUNDER = int(REG.get("maks_runder", 3))
MAKS_SAMMEN = int(REG.get("maks_sammenligninger", 3))
RESULTAT_RE = re.compile(r'"resultat"\s*:\s*"(ok|ret)"', re.IGNORECASE)
FORBEDRING_RE = re.compile(r"forbedring\s+implementeret\W{0,6}ja\b", re.IGNORECASE)
HVORFOR_RE = re.compile(r"^\s*\d+\.\s.*\bhvorfor\b", re.IGNORECASE | re.MULTILINE)
GRUNDAARSAG_RE = re.compile(r"grundårsag", re.IGNORECASE)
LEV_RE = re.compile(r"LEVERANCE\s*:\s*([^\s`'\"<>]+)", re.IGNORECASE)
STI_RE = re.compile(r"^\s*Leverance\s*:\s*(\S+\.md)\b", re.IGNORECASE | re.MULTILINE)
IGANG_MAKS_SEK = 90 * 60
FASE_RE = re.compile(r"^\s*FASE\s*:\s*(\d)", re.IGNORECASE | re.MULTILINE)
DESIGN_RE = re.compile(r"^\s*DESIGNGRUNDLAG\s*:\s*(.+)$", re.IGNORECASE | re.MULTILINE)
GODKEND_G2_RE = re.compile(r"\bgodkend(?:er|t)?\s+G2\s+([A-Za-z0-9ÆØÅæøå._-]+)", re.IGNORECASE)
NYT_GRUNDLAG = {"regression", "aendret_tekst", "kritisk_sikkerhed"}
BLOKERENDE = {"kritisk", "væsentlig"}
STATUSSER = {"nyt", "aabent", "åbent", "lukket", "bestridt"}
KONTEKST_GRAENSE = 200_000
KONTEKST_TRIN = 100_000


# ---------- hjælpere ----------
def nu() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%S")


def datamappe() -> pathlib.Path:
    rod = os.environ.get("CLAUDE_PLUGIN_DATA")
    if not rod:
        # Manuelle kommandoer (status/nulstil) køres uden CLAUDE_PLUGIN_DATA: brug pluginets
        # egen datamappe, hvis den findes (nyeste tilstand vinder), før standardmappen oprettes.
        fundne = sorted((pathlib.Path.home() / ".claude" / "plugins" / "data").glob("*/kontrol/tilstand.json"),
                        key=lambda f: f.stat().st_mtime, reverse=True)
        if fundne:
            return fundne[0].parent
        rod = str(pathlib.Path.home() / ".claude" / "byg-kontrol-data")
    p = pathlib.Path(rod) / "kontrol"
    p.mkdir(parents=True, exist_ok=True)
    return p


class Laas:
    def __init__(self, d: pathlib.Path):
        self.sti = d / ".laas"
        self.fh = None

    def __enter__(self):
        self.fh = open(self.sti, "a+")
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


def indlaes(d: pathlib.Path) -> dict:
    f = d / "tilstand.json"
    if f.exists():
        try:
            return json.loads(f.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {"version": 1, "leverancer": {}}


def gem(d: pathlib.Path, s: dict) -> None:
    f = d / "tilstand.json"
    tmp = f.with_suffix(".tmp")
    tmp.write_text(json.dumps(s, ensure_ascii=False, indent=2), encoding="utf-8")
    os.replace(tmp, f)


def log(d: pathlib.Path, **kw) -> None:
    kw["tid"] = nu()
    with open(d / "log.jsonl", "a", encoding="utf-8") as fh:
        fh.write(json.dumps(kw, ensure_ascii=False) + "\n")


def sikkert(lev: str) -> str:
    return re.sub(r"[^A-Za-z0-9ÆØÅæøå._-]+", "__", lev)


def del_navn(navn: str) -> tuple[str, str]:
    navn = (navn or "").strip()
    if ":" in navn:
        pre, base = navn.rsplit(":", 1)
        return pre, base
    return "", navn


def klassificer(base: str) -> tuple:
    for fag, v in REG["fag"].items():
        if base == v["agent"]:
            return "fag", fag
        if base == v["kontrol"]:
            return "kontrol", fag
        if base in v.get("hjaelpere", []):
            return "hjaelper", fag
    if base == REG["projekt_kontrol"]:
        return "kontrol", "projekt"
    return None, None


def kontrolnavn(fag: str, fag_prefix: str) -> str:
    base = REG["projekt_kontrol"] if fag == "projekt" else REG["fag"][fag]["kontrol"]
    if not fag_prefix:
        return base
    pre = fag_prefix if fag_prefix == REG["samlet_plugin"] else REG["kontrol_plugin"]
    return f"{pre}:{base}"


def afvis_kald(grund: str) -> None:
    print(json.dumps({"hookSpecificOutput": {"hookEventName": "PreToolUse",
                                             "permissionDecision": "deny",
                                             "permissionDecisionReason": grund}}, ensure_ascii=False))


def bloker(grund: str) -> None:
    print(json.dumps({"decision": "block", "reason": grund}, ensure_ascii=False))


def runde(e: dict) -> int:
    return int(e.get("runde") or 1)


def rca_navn(lev: str, r: int) -> str:
    return f"RCA-{sikkert(lev)}.md" if r <= 1 else f"RCA-{sikkert(lev)}__runde-{r}.md"


def sag_af(lev: str) -> str:
    return lev.split("/", 1)[0]


def g2_mangler(s: dict, sag: str, ids: list) -> str | None:
    g2 = (s.get("gates") or {}).get(sag, {}).get("G2")
    if not g2:
        return (f"Manuel gate G2 mangler for sagen {sag}: detailplanlægning (fase 3) må først starte, når brugeren har "
                f"godkendt løsningen. Præsentér løsningen (loesningspraesentation.md, se projektlederens faser-og-gates.md), "
                f"og bed brugeren selv skrive: 'Godkend G2 {sag}'. Claude kan ikke give denne godkendelse.")
    ukendte = [i for i in ids if i not in (g2.get("design") or [])]
    if ukendte:
        return (f"Designgrundlaget er ændret efter brugerens G2-godkendelse ({g2.get('tid')}): {', '.join(ukendte)} "
                f"indgik ikke i det godkendte design. Præsentér ændringen, og bed brugeren skrive 'Godkend G2 {sag}' igen.")
    return None


def naeste_skridt(lev: str, e: dict) -> str:
    st = e.get("status")
    r = runde(e)
    if st == "afvist":
        hvem = e.get("fag_agent") or "projektlederen (egen leverance)"
        return (f"Afvist (runde {r}/{MAKS_RUNDER}, forsøg {e.get('forsoeg')}/{MAKS}): send de blokerende fund (ikke de mindre) "
                f"retur til {hvem} med 'LEVERANCE: {lev}', og kald derefter {e.get('kontrol_agent')} igen i forgrunden.")
    if st in ("stoppet", "rca_udfoert"):
        if r < MAKS_RUNDER:
            return (f"Stoppet efter {MAKS} afviste forsøg i runde {r}/{MAKS_RUNDER}: skriv root cause-analysen til "
                    f"<sagsmappe>/kvalitet/{rca_navn(lev, r)} – hvorfor kunne fagagenten ikke levere korrekt i første forsøg? "
                    f"Implementér læringen som forbedring af fagagenten (agentens hukommelse og repoet), skriv linjen "
                    f"'Forbedring implementeret: ja' i RCA'en, og start runde {r + 1} med et nyt fagkald under samme "
                    f"leverance-ID (højst {MAKS} nye forsøg) – se skill 'kvalitetskontrol'.")
        return (f"Stoppet efter {MAKS_RUNDER} runder à {MAKS} forsøg: skriv root cause-analysen til "
                f"<sagsmappe>/kvalitet/{rca_navn(lev, r)}, implementér læringen i fagagenten, eskalér til brugeren, "
                f"og fortsæt kun efter brugerens beslutning under et nyt leverance-ID.")
    if st == "godkendt":
        return f"Godkendt: ændringer kræver et nyt leverance-ID (fx '{lev}-r2')."
    return ""


# ---------- PreToolUse ----------
def pretool(inp: dict, d: pathlib.Path) -> None:
    ti = inp.get("tool_input") or {}
    st = str(ti.get("subagent_type") or "")
    pre, base = del_navn(st)
    art, fag = klassificer(base)
    if not art:
        return
    m = LEV_RE.search(str(ti.get("prompt") or ""))
    if not m and art == "hjaelper":
        return afvis_kald(f"byg-kvalitetskontrol: {base} kræver 'LEVERANCE: <id>' for den fagleverance, der skal "
                          "sammenlignes – se skill 'tegningsimport'.")
    if not m:
        if art == "fag":
            afvis_kald(f"byg-kvalitetskontrol: fagkald uden leverance-ID. Tilføj linjen 'LEVERANCE: <sag-id>/{fag}/<nr>' "
                       f"i prompten (fx 'LEVERANCE: {time.strftime('%Y-%m-%d')}-<emne>/{fag}/01'). Leverancen skal bagefter "
                       f"kontrolleres af {kontrolnavn(fag, pre)} – se skill 'kvalitetskontrol'.")
        else:
            afvis_kald("byg-kvalitetskontrol: kontrolkald uden leverance-ID. Brug samme 'LEVERANCE: <id>' som fagleverancen "
                       "(eller 'LEVERANCE: ekstern/<emne>' ved gennemgang af eksternt materiale).")
        return
    lev = m.group(1).rstrip(".,;:)")
    sid = str(inp.get("session_id") or "")
    with Laas(d):
        s = indlaes(d)
        L = s["leverancer"]
        e = L.get(lev)
        if art == "hjaelper":
            return hjaelperkald(d, s, e, lev, fag, st, sid)
        if art == "fag":
            fm = FASE_RE.search(str(ti.get("prompt") or ""))
            if fm and int(fm.group(1)) >= 3:
                grund = g2_mangler(s, sag_af(lev), [])
                if grund:
                    return afvis_kald(grund)
            if e:
                if e.get("fag") != fag:
                    return afvis_kald(f"Leverance-ID {lev} tilhører faget '{e.get('fag')}'. Brug et nyt ID til {fag}.")
                status = e.get("status")
                if status == "fagkald_igang":
                    e.update(session_id=sid, opdateret=nu())
                    gem(d, s)
                    log(d, haendelse="fagkald_gentaget", leverance=lev, forsoeg=e.get("forsoeg"), agent=st)
                    return
                if status == "under_sammenligning":
                    return afvis_kald(f"Leverance {lev} er ved at blive sammenlignet. Vent på sammenligningens resultat, "
                                      f"og send afvigelserne retur med 'LEVERANCE: {lev}'.")
                if status in ("afventer_kontrol", "under_kontrol"):
                    hj = REG["fag"].get(fag, {}).get("hjaelpere")
                    ekstra = (f" (Eller sammenlign først med {', '.join(hj)} – se skill 'tegningsimport'.)"
                              if hj and status == "afventer_kontrol" else "")
                    return afvis_kald(f"Leverance {lev} (forsøg {e.get('forsoeg')}/{MAKS}) er ikke kontrolleret endnu. "
                                      f"Kald {e.get('kontrol_agent')} med 'LEVERANCE: {lev}' og stien til fagnotatet først."
                                      + ekstra)
                if status == "sammenlignet":
                    e["rettelser"] = int(e.get("rettelser", 0)) + 1
                    e.update(status="fagkald_igang", session_id=sid, opdateret=nu())
                    gem(d, s)
                    log(d, haendelse="rettelse_efter_sammenligning", leverance=lev, rettelse=e["rettelser"], agent=st)
                    return
                if status == "godkendt":
                    return afvis_kald(naeste_skridt(lev, e))
                if status in ("stoppet", "rca_udfoert"):
                    grund = ny_runde_blokeret(inp, e, lev)
                    if grund:
                        return afvis_kald(grund)
                    start_ny_runde(d, e, lev)
                elif int(e.get("forsoeg", 0)) >= MAKS:
                    e["status"] = "stoppet"
                    gem(d, s)
                    return afvis_kald(naeste_skridt(lev, e))
                else:
                    e["forsoeg"] = int(e.get("forsoeg", 0)) + 1
            else:
                e = L[lev] = {"fag": fag, "type": "fag", "forsoeg": 1, "fag_agent": st,
                              "kontrol_agent": kontrolnavn(fag, pre), "oprettet": nu(), "domme": []}
            e.update(status="fagkald_igang", session_id=sid, opdateret=nu())
            gem(d, s)
            log(d, haendelse="fagkald", leverance=lev, runde=runde(e), forsoeg=e["forsoeg"], agent=st)
            return
        # kontrolkald
        if fag == "projekt":
            if e and e.get("type") != "projekt":
                return afvis_kald(f"Leverance {lev} er en {e.get('fag')}-leverance og kontrolleres af {e.get('kontrol_agent')}.")
            prompt = str(ti.get("prompt") or "")
            fm = FASE_RE.search(prompt)
            if not fm:
                return afvis_kald("Projektkontrol kræver linjen 'FASE: <0-4>' i prompten (0 afklaring, 1 dispositionsforslag, "
                                  "2 design, 3 integration/plan, 4 udførelse) – se skill 'kvalitetskontrol', afsnit 3.")
            fase = int(fm.group(1))
            if fase >= 3:
                dm = DESIGN_RE.search(prompt)
                ids = [x.strip().rstrip(".,;") for x in re.split(r"[,\s]+", dm.group(1)) if x.strip()] if dm else []
                if not ids:
                    return afvis_kald("Fase-gate: en planleverance i fase 3+ kræver linjen 'DESIGNGRUNDLAG: <leverance-id>, …' "
                                      "med de godkendte fagnotater, planen bygger på (design freeze).")
                mangler = [f"{i} ({(L.get(i) or {}).get('status', 'ukendt')})" for i in ids
                           if (L.get(i) or {}).get("status") != "godkendt"]
                if mangler:
                    return afvis_kald("Fase-gate: designgrundlaget er ikke frosset – disse fagleverancer er ikke godkendt: "
                                      + ", ".join(mangler) + ". Planlæg (tidsplan, budget, montage) først, når designet er godkendt.")
                grund = g2_mangler(s, sag_af(lev), ids)
                if grund:
                    return afvis_kald(grund)
            if not e:
                e = L[lev] = {"fag": "projekt", "type": "projekt", "forsoeg": 0, "kontrol_agent": st,
                              "oprettet": nu(), "domme": []}
            e["fase"] = fase
            if e.get("status") == "godkendt":
                return afvis_kald(naeste_skridt(lev, e))
            if e.get("status") in ("stoppet", "rca_udfoert"):
                grund = ny_runde_blokeret(inp, e, lev)
                if grund:
                    return afvis_kald(grund)
                start_ny_runde(d, e, lev)
            elif e.get("status") != "under_kontrol":
                if int(e.get("forsoeg", 0)) >= MAKS:
                    e["status"] = "stoppet"
                    gem(d, s)
                    return afvis_kald(naeste_skridt(lev, e))
                e["forsoeg"] = int(e.get("forsoeg", 0)) + 1
        elif e is None:
            e = L[lev] = {"fag": fag, "type": "ekstern", "forsoeg": 1, "kontrol_agent": st,
                          "oprettet": nu(), "domme": []}
        else:
            if e.get("fag") != fag:
                return afvis_kald(f"Forkert kontrolagent: {lev} er en {e.get('fag')}-leverance og skal kontrolleres af "
                                  f"{e.get('kontrol_agent')}.")
            if e.get("type") == "ekstern":
                if e.get("status") != "under_kontrol":
                    e["forsoeg"] = int(e.get("forsoeg", 0)) + 1
            elif e.get("status") not in ("fagkald_igang", "afventer_kontrol", "under_kontrol", "sammenlignet"):
                return afvis_kald(f"Leverance {lev} har status '{e.get('status')}' – der er ingen ny fagversion at "
                                  f"kontrollere. {naeste_skridt(lev, e)}")
        sm = STI_RE.search(str(ti.get("prompt") or ""))
        if sm and e.get("type") != "ekstern":
            e["sti"] = str(pathlib.Path(sm.group(1)).expanduser())
        e.update(status="under_kontrol", session_id=sid, opdateret=nu())
        gem(d, s)
        log(d, haendelse="kontrolkald", leverance=lev, runde=runde(e), forsoeg=e.get("forsoeg"), agent=st, type=e.get("type"))


# ---------- SubagentStop ----------
def find_dom(msg: str):
    if not msg:
        return None, ["Kontrolagenten har ingen slutbesked."]
    for blok in reversed(re.findall(r"```(?:json)?\s*(\{.*?\})\s*```", msg, re.S)):
        try:
            d = json.loads(blok)
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


def normklasse(k) -> str:
    k = str(k or "").strip().lower()
    return {"vaesentlig": "væsentlig", "vasentlig": "væsentlig"}.get(k, k)


def valider(dom: dict) -> list:
    fejl = []
    if not str(dom.get("leverance_id") or "").strip():
        fejl.append("leverance_id mangler.")
    dv = str(dom.get("dom") or "").strip().lower()
    if dv not in ("godkendt", "afvist"):
        fejl.append("dom skal være 'godkendt' eller 'afvist'.")
    fund = dom.get("fund")
    if not isinstance(fund, list):
        fejl.append("fund skal være en liste (tom liste er tilladt).")
        fund = []
    aabne = []
    for i, f in enumerate(fund):
        if not isinstance(f, dict):
            fejl.append(f"fund nr. {i + 1} er ikke et objekt.")
            continue
        fid = str(f.get("id") or f"#{i + 1}")
        kl = normklasse(f.get("klasse"))
        st = str(f.get("status") or "").strip().lower()
        if kl not in ("kritisk", "væsentlig", "mindre"):
            fejl.append(f"{fid}: klasse skal være kritisk, væsentlig eller mindre.")
        if st not in STATUSSER:
            fejl.append(f"{fid}: status skal være nyt, aabent, lukket eller bestridt.")
        if kl in BLOKERENDE and st != "lukket":
            mangler = [k for k in ("krav", "kilde", "evidens") if not str(f.get(k) or "").strip()]
            if mangler:
                fejl.append(f"{fid} ({kl}): mangler {', '.join(mangler)} – blokerende fund kræver krav, kilde og evidens.")
            aabne.append(fid)
    if dv == "godkendt" and aabne:
        fejl.append(f"dom 'godkendt' er ikke tilladt med åbne blokerende fund: {', '.join(aabne)}.")
    if dv == "afvist" and not aabne:
        fejl.append("dom 'afvist' kræver mindst ét åbent kritisk eller væsentligt fund.")
    dom["dom"] = dv
    return fejl


def taelling(dom: dict) -> dict:
    t = {"kritisk": 0, "væsentlig": 0, "mindre": 0}
    for f in dom.get("fund") or []:
        if isinstance(f, dict) and str(f.get("status") or "").lower() != "lukket":
            kl = normklasse(f.get("klasse"))
            if kl in t:
                t[kl] += 1
    return t


def sagsmappe_sti(inp: dict, e: dict):
    sm = e.get("sagsmappe")
    if not sm or str(sm).lower() in ("null", "none"):
        return None
    p = pathlib.Path(str(sm)).expanduser()
    if not p.is_absolute():
        p = pathlib.Path(str(inp.get("cwd") or os.getcwd())) / p
    return p if p.is_dir() else None


def _tekst(indhold) -> str:
    if isinstance(indhold, str):
        return indhold
    dele = []
    for b in indhold or []:
        if not isinstance(b, dict):
            continue
        if b.get("type") == "text":
            dele.append(b.get("text", ""))
        elif b.get("type") == "tool_use":
            # Hand-back og lignende: dommen kan ligge i værktøjskaldets input
            for v in (b.get("input") or {}).values():
                if isinstance(v, str):
                    dele.append(v)
        elif b.get("type") == "tool_result":
            dele.append(_tekst(b.get("content")))
    return "\n".join(dele)


def laes_transkript(sti, antal: int = 3) -> str:
    """Tekst fra de sidste assistent-beskeder (inkl. tool_use-input), nyeste sidst."""
    try:
        linjer = pathlib.Path(sti).read_text(encoding="utf-8").splitlines()
        fundne = []
        for linje in reversed(linjer):
            obj = json.loads(linje)
            msg = obj.get("message") or {}
            if msg.get("role") == "assistant":
                fundne.append(_tekst(msg.get("content")))
                if len(fundne) >= antal:
                    break
        return "\n".join(reversed(fundne))
    except Exception:
        return ""


def foerste_prompt(sti) -> str:
    """Første brugerbesked i agentens transkript (prompten fra orkestratoren)."""
    try:
        for linje in pathlib.Path(sti).read_text(encoding="utf-8").splitlines():
            obj = json.loads(linje)
            msg = obj.get("message") or {}
            if msg.get("role") == "user":
                return _tekst(msg.get("content"))
    except Exception:
        pass
    return ""


def fagaflevering(inp: dict, d: pathlib.Path, fag: str, at: str) -> None:
    m = LEV_RE.search(foerste_prompt(inp.get("agent_transcript_path")) or "")
    with Laas(d):
        s = indlaes(d)
        kandidater = []
        if m:
            kandidater = [m.group(1).rstrip(".,;:)")]
        else:
            sid = str(inp.get("session_id") or "")
            kandidater = [lev for lev, e in s["leverancer"].items()
                          if e.get("fag") == fag and e.get("status") == "fagkald_igang" and e.get("session_id") == sid]
            if len(kandidater) != 1:
                log(d, haendelse="fagaflevering_uklar", agent=at, kandidater=kandidater)
                return
        for lev in kandidater:
            e = s["leverancer"].get(lev)
            if e and e.get("fag") == fag and e.get("status") == "fagkald_igang":
                e.update(status="afventer_kontrol", opdateret=nu())
                gem(d, s)
                log(d, haendelse="fagaflevering", leverance=lev, forsoeg=e.get("forsoeg"), agent=at)


def hjaelperkald(d, s, e, lev, fag, st, sid) -> None:
    """Sammenligning (eller anden hjælper) af en afleveret fagversion – før den formelle kontrol."""
    if not e or e.get("fag") != fag:
        return afvis_kald(f"Leverance {lev} findes ikke for faget '{fag}'. Kald først fagagenten med 'LEVERANCE: {lev}'.")
    status = e.get("status")
    if status == "under_sammenligning":
        e.update(session_id=sid, opdateret=nu())
        gem(d, s)
        log(d, haendelse="sammenligning_gentaget", leverance=lev, agent=st)
        return
    if status not in ("afventer_kontrol", "sammenlignet"):
        return afvis_kald(f"Leverance {lev} har status '{status}'. Sammenligning kræver en afleveret fagversion "
                          f"(fagagenten skal have afleveret, og kontrollen må ikke være gået i gang).")
    if int(e.get("sammenligninger", 0)) >= MAKS_SAMMEN:
        return afvis_kald(f"Højst {MAKS_SAMMEN} sammenligninger pr. leverance ({lev}). Send leverancen til "
                          f"{e.get('kontrol_agent')} med de resterende afvigelser beskrevet i notatet, eller eskalér til brugeren.")
    e["sammenligninger"] = int(e.get("sammenligninger", 0)) + 1
    e.update(status="under_sammenligning", session_id=sid, opdateret=nu(), hjaelper_agent=st)
    gem(d, s)
    log(d, haendelse="sammenligning", leverance=lev, nr=e["sammenligninger"], agent=st)


def hjaelperaflevering(inp: dict, d: pathlib.Path, fag: str, at: str) -> None:
    m = LEV_RE.search(foerste_prompt(inp.get("agent_transcript_path")) or "")
    if not m:
        log(d, haendelse="hjaelperaflevering_uden_leverance", agent=at)
        return
    lev = m.group(1).rstrip(".,;:)")
    tekst = (inp.get("last_assistant_message") or "") + "\n" + laes_transkript(inp.get("agent_transcript_path"), 1)
    r = RESULTAT_RE.findall(tekst)
    with Laas(d):
        s = indlaes(d)
        e = s["leverancer"].get(lev)
        if e and e.get("fag") == fag and e.get("status") == "under_sammenligning":
            e.update(status="sammenlignet", opdateret=nu(), sammenligning_resultat=(r[-1].lower() if r else None))
            gem(d, s)
            log(d, haendelse="sammenligning_afleveret", leverance=lev, nr=e.get("sammenligninger"),
                resultat=e.get("sammenligning_resultat"), agent=at)


def subagentstop(inp: dict, d: pathlib.Path) -> None:
    at = str(inp.get("agent_type") or "")
    _, base = del_navn(at)
    art, fag = klassificer(base)
    if art == "fag":
        return fagaflevering(inp, d, fag, at)
    if art == "hjaelper":
        return hjaelperaflevering(inp, d, fag, at)
    if art != "kontrol":
        return
    msg = inp.get("last_assistant_message") or ""
    dom, fejl = find_dom(msg)
    if fejl:
        dom2, fejl2 = find_dom(laes_transkript(inp.get("agent_transcript_path")))
        if not fejl2:
            dom, fejl = dom2, fejl2
    if not fejl:
        fejl = valider(dom)
    with Laas(d):
        s = indlaes(d)
        L = s["leverancer"]
        e = None
        if not fejl:
            lev = str(dom.get("leverance_id")).strip()
            e = L.get(lev)
            if e is None:
                fejl = [f"leverance_id '{lev}' matcher ikke en registreret leverance – brug præcis ID'et fra prompten."]
            elif e.get("fag") != fag:
                fejl = [f"leverance_id '{lev}' tilhører faget '{e.get('fag')}', ikke '{fag}'."]
            else:
                # Gentaget eller forældet dom (fx fra en genoptaget kontrolagent) registreres ikke
                forældet = None
                if e.get("status") != "under_kontrol":
                    forældet = f"status er '{e.get('status')}', ikke 'under_kontrol'"
                elif str(dom.get("forsoeg") or "").strip().isdigit() and int(dom["forsoeg"]) != int(e.get("forsoeg", 0)):
                    forældet = f"dommen gælder forsøg {dom['forsoeg']}, men leverancen er i forsøg {e.get('forsoeg')}"
                if forældet:
                    log(d, haendelse="forældet_dom", leverance=lev, agent=at, grund=forældet)
                    return
                if int(e.get("forsoeg", 1)) > 1 and e.get("type") != "ekstern":
                    for f in dom.get("fund") or []:
                        kl = normklasse(f.get("klasse"))
                        if str(f.get("status") or "").lower() == "nyt" and kl in BLOKERENDE:
                            ng = str(f.get("nyt_grundlag") or "").strip().lower()
                            if ng not in NYT_GRUNDLAG or (ng == "kritisk_sikkerhed" and kl != "kritisk"):
                                fejl.append(f"{f.get('id')}: nyt {kl} fund i forsøg {e.get('forsoeg')} kræver \"nyt_grundlag\": "
                                            "\"regression\" eller \"aendret_tekst\" (eller \"kritisk_sikkerhed\" for kritiske fund). "
                                            "Blev det overset i forsøg 1, så nedgradér det til 'mindre' og skriv det under kontrolsvigt "
                                            "(fund-fastlåsning, kontrolprotokol afsnit 4).")
        if fejl:
            log(d, haendelse="ugyldig_dom", agent=at, fejl=fejl, gentaget=bool(inp.get("stop_hook_active")))
            if not inp.get("stop_hook_active"):
                bloker("Ugyldig kontroldom – ret den, før du afslutter:\n- " + "\n- ".join(fejl) +
                       "\nAfslut med præcis én JSON-blok efter skemaet i kontrolprotokollen (afsnit 5).")
            return
        e.setdefault("domme", []).append({"runde": runde(e), "forsoeg": e.get("forsoeg"), "dom": dom["dom"],
                                          "aabne_fund": taelling(dom), "tid": nu()})
        if e.get("type") == "ekstern":
            e["status"] = "vurderet_ekstern"
        elif dom["dom"] == "godkendt":
            e["status"] = "godkendt"
        else:
            e["status"] = "stoppet" if int(e.get("forsoeg", 1)) >= MAKS else "afvist"
        if dom.get("sagsmappe"):
            e["sagsmappe"] = dom.get("sagsmappe")
        e["opdateret"] = nu()
        gem(d, s)
    log(d, haendelse="dom", leverance=lev, dom=dom["dom"], status=e["status"], runde=runde(e), forsoeg=e.get("forsoeg"))
    try:
        sm = sagsmappe_sti(inp, e)
        if sm:
            kv = sm / "kvalitet"
            kv.mkdir(exist_ok=True)
            rdel = f"__runde-{runde(e)}" if runde(e) > 1 else ""
            (kv / f"{sikkert(lev)}{rdel}__forsoeg-{e.get('forsoeg')}.json").write_text(
                json.dumps(dom, ensure_ascii=False, indent=2), encoding="utf-8")
    except Exception:
        log(d, haendelse="domfil_fejl", fejl=traceback.format_exc()[-400:])


# ---------- Stop ----------
def rca_fil(inp: dict, e: dict, lev: str):
    navn = rca_navn(lev, runde(e))
    sm = sagsmappe_sti(inp, e)
    if sm and (sm / "kvalitet" / navn).exists():
        return sm / "kvalitet" / navn
    cwd = pathlib.Path(str(inp.get("cwd") or os.getcwd()))
    return next(iter(cwd.glob(f"byg-sager/*/kvalitet/{navn}")), None)


def rca_findes(inp: dict, e: dict, lev: str) -> bool:
    return rca_fil(inp, e, lev) is not None


def ny_runde_blokeret(inp: dict, e: dict, lev: str):
    """Grund til at en ny runde ikke må starte – eller None, hvis den må."""
    r = runde(e)
    if r >= MAKS_RUNDER:
        return naeste_skridt(lev, e)
    f = rca_fil(inp, e, lev)
    if f is None:
        return (f"Runde {r + 1} kræver først root cause-analysen for runde {r}. " + naeste_skridt(lev, e))
    try:
        tekst = f.read_text(encoding="utf-8")
    except Exception:
        tekst = ""
    if len(HVORFOR_RE.findall(tekst)) < 5 or not GRUNDAARSAG_RE.search(tekst):
        return (f"{f.name} mangler en 5 Why-kæde: mindst fem nummererede 'Hvorfor'-linjer (hvert svar besvarer det "
                f"foregående, med evidens) og en linje med 'Grundårsag' (skabelonens afsnit 3), før runde {r + 1} starter.")
    if not FORBEDRING_RE.search(tekst):
        return (f"{f.name} mangler linjen 'Forbedring implementeret: ja'. Implementér læringen som forbedring af "
                f"fagagenten (agentens hukommelse og repoet), notér hvad der er ændret, og skriv linjen i RCA'en, før "
                f"runde {r + 1} starter.")
    return None


def start_ny_runde(d: pathlib.Path, e: dict, lev: str) -> None:
    e["runde"] = runde(e) + 1
    e["forsoeg"] = 1
    log(d, haendelse="ny_runde", leverance=lev, runde=e["runde"])


def alder_sek(e: dict) -> float:
    try:
        return time.time() - time.mktime(time.strptime(str(e.get("opdateret")), "%Y-%m-%dT%H:%M:%S"))
    except Exception:
        return 0


def beskyt(inp: dict, d: pathlib.Path) -> None:
    """PreToolUse Write/Edit: beskyt filer, der hører til godkendte leverancer."""
    ti = inp.get("tool_input") or {}
    fil = ti.get("file_path") or ti.get("notebook_path")
    if not fil:
        return
    fil = str(pathlib.Path(str(fil)).expanduser())
    s = indlaes(d)
    for lev, e in s["leverancer"].items():
        if e.get("status") == "godkendt" and e.get("sti") and e["sti"] == fil:
            grund = (f"{fil} er leverancen {lev}, som er godkendt af kvalitetskontrollen. Ret den ikke direkte: "
                     f"skriv afvigelsen i dit eget notat og bed projektlederen om en ændring under nyt leverance-ID "
                     f"(fx '{lev}-r2') via aendringer.md.")
            if inp.get("agent_type") or inp.get("agent_id"):
                log(d, haendelse="beskyttet_fil_afvist", leverance=lev, fil=fil, agent=inp.get("agent_type"))
                return afvis_kald(grund)
            log(d, haendelse="beskyttet_fil_advarsel", leverance=lev, fil=fil)
            print(json.dumps({"systemMessage": "byg-kontrol: " + grund,
                              "hookSpecificOutput": {"hookEventName": "PreToolUse", "additionalContext": grund}},
                             ensure_ascii=False))
            return


def kontekst_tokens(sti) -> int:
    """Hovedtrådens kontekst (input + cache) i det seneste svar, læst bagfra i transkriptets sidste 2 MB."""
    try:
        with open(sti, "rb") as fh:
            fh.seek(0, os.SEEK_END)
            start = max(0, fh.tell() - 2_000_000)
            fh.seek(start)
            linjer = fh.read().split(b"\n")
        for linje in reversed(linjer[1:] if start else linjer):
            if b'"usage"' not in linje:
                continue
            try:
                obj = json.loads(linje)
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


def kontekst_paamindelse(inp: dict, s: dict) -> tuple[str, str] | None:
    """(til brugeren, til modellen), når en byg-sessions hovedtråd har passeret næste kontekstgrænse."""
    sid = str(inp.get("session_id") or "")
    sager = sorted({sag_af(lev) for lev, e in s["leverancer"].items() if sid and e.get("session_id") == sid})
    if not sager:
        return None
    n = kontekst_tokens(inp.get("transcript_path"))
    if n < KONTEKST_GRAENSE:
        return None
    trin = 1 + (n - KONTEKST_GRAENSE) // KONTEKST_TRIN
    advaret = s.setdefault("kontekst", {})
    if int(advaret.get(sid, 0)) >= trin:
        return None
    advaret[sid] = trin
    sag = sager[0] if len(sager) == 1 else "<sag-id>"
    k = f"{n // 1000}k"
    til_bruger = (f"byg: Samtalen fylder nu ca. {k} tokens, og hvert svar læser det hele igen. Når den igangværende "
                  f"opgave er færdig, så fortsæt i en ny session med /byg:status {sag} – sagsmappen husker resten.")
    til_model = (f"Kontekstbudget: hovedtråden er ca. {k} tokens, og hvert svar læser det hele igen. Afslut den igangværende "
                 f"opgave, opdatér status.md (næste skridt, åbne punkter, leverancer), og foreslå brugeren at fortsætte i en "
                 f"ny session med /byg:status {sag}. Lav ikke research og læs ikke store filer i denne tråd; send det til en "
                 f"subagent (projektleder-skill, 'Effektivitet').")
    return til_bruger, til_model


def brugerprompt(inp: dict, d: pathlib.Path) -> None:
    """UserPromptSubmit: brugerens egen godkendelse af G2 ('Godkend G2 <sag-id>') og påmindelse om kontekstbudget."""
    tekst = str(inp.get("prompt") or "")
    fundne = [m.group(1).rstrip(".,;:)") for m in GODKEND_G2_RE.finditer(tekst)]
    beskeder = []
    with Laas(d):
        s = indlaes(d)
        paamindelse = kontekst_paamindelse(inp, s)
        for sag in fundne:
            design = sorted(lev for lev, e in s["leverancer"].items()
                            if sag_af(lev) == sag and e.get("type") == "fag" and e.get("status") == "godkendt")
            s.setdefault("gates", {}).setdefault(sag, {})["G2"] = {
                "tid": nu(), "design": design, "session_id": str(inp.get("session_id") or ""), "tekst": tekst[:300]}
            log(d, haendelse="gate_G2_godkendt", sag=sag, design=design)
            beskeder.append(f"G2 (løsningsgodkendelse) for {sag} er registreret som godkendt af brugeren med "
                            f"{len(design)} godkendte fagleverancer: {', '.join(design) or 'ingen'}. "
                            "Skriv godkendelsen i beslutningsloggen, og start fase 3.")
        if fundne or paamindelse:
            gem(d, s)
    if paamindelse:
        log(d, haendelse="kontekst_paamindelse", session_id=str(inp.get("session_id") or ""))
        beskeder.append(paamindelse[1])
    if not beskeder:
        return
    ud = {"hookSpecificOutput": {"hookEventName": "UserPromptSubmit", "additionalContext": " ".join(beskeder)}}
    if paamindelse:
        ud["systemMessage"] = paamindelse[0]
    print(json.dumps(ud, ensure_ascii=False))


def stop(inp: dict, d: pathlib.Path) -> None:
    if inp.get("stop_hook_active"):
        return
    sid = str(inp.get("session_id") or "")
    punkter, aendret = [], False
    with Laas(d):
        s = indlaes(d)
        for lev, e in s["leverancer"].items():
            if e.get("session_id") != sid:
                continue
            status, typ = e.get("status"), e.get("type")
            if typ == "ekstern":
                if status == "under_kontrol":
                    punkter.append(f"{lev}: kontrolagentens gyldige dom mangler → kald {e.get('kontrol_agent')} igen.")
                continue
            if status == "fagkald_igang":
                if alder_sek(e) > IGANG_MAKS_SEK:
                    punkter.append(f"{lev}: fagkaldet har ikke afleveret i over {IGANG_MAKS_SEK // 60} min. Er agenten "
                                   f"afbrudt, så kald {e.get('fag_agent')} igen med 'LEVERANCE: {lev}' (tæller ikke som nyt forsøg).")
                continue
            if status == "afventer_kontrol":
                punkter.append(f"{lev}: afventer kontrol → kald {e.get('kontrol_agent')} med 'LEVERANCE: {lev}'.")
            elif status == "under_sammenligning":
                punkter.append(f"{lev}: sammenligningens resultat mangler → kald {e.get('hjaelper_agent')} igen.")
            elif status == "sammenlignet":
                punkter.append(f"{lev}: sammenlignet ({e.get('sammenligning_resultat') or '?'}) → send afvigelserne retur til "
                               f"{e.get('fag_agent')}, eller kald {e.get('kontrol_agent')}, hvis der ikke er flere at rette.")
            elif status == "under_kontrol":
                punkter.append(f"{lev}: gyldig kontroldom mangler → kald {e.get('kontrol_agent')} igen.")
            elif status == "afvist":
                punkter.append(f"{lev}: {naeste_skridt(lev, e)} Kræver fundene brugerens beslutning, så stop og spørg brugeren.")
            elif status == "stoppet":
                if rca_findes(inp, e, lev):
                    e["status"] = "rca_udfoert"
                    aendret = True
                else:
                    punkter.append(f"{lev}: {naeste_skridt(lev, e)}")
        if aendret:
            gem(d, s)
    if punkter:
        bloker("Kvalitetskontrollen er ikke afsluttet for denne sessions leverancer:\n- " + "\n- ".join(punkter))


# ---------- manuelle kommandoer ----------
def manuel(cmd: str, args: list) -> int:
    d = datamappe()
    with Laas(d):
        s = indlaes(d)
        if cmd == "status":
            if not s["leverancer"]:
                print("Ingen registrerede leverancer.")
            for lev, e in sorted(s["leverancer"].items()):
                print(f"{lev:45} {e.get('fag', ''):12} {e.get('status', ''):18} "
                      f"runde {runde(e)}/{MAKS_RUNDER} forsøg {e.get('forsoeg')}/{MAKS}")
            for sag, g in sorted((s.get("gates") or {}).items()):
                if g.get("G2"):
                    print(f"GATE G2 {sag}: godkendt af bruger {g['G2'].get('tid')} ({len(g['G2'].get('design') or [])} fagleverancer)")
            return 0
        if cmd == "nulstil" and args:
            fjernet = s["leverancer"].pop(args[0], None)
            gem(d, s)
            log(d, haendelse="nulstillet", leverance=args[0])
            print("Nulstillet." if fjernet else "Ukendt leverance-ID.")
            return 0
    print(__doc__)
    return 1


def main() -> int:
    cmd = sys.argv[1] if len(sys.argv) > 1 else ""
    if cmd in ("status", "nulstil", "hjaelp"):
        return manuel(cmd, sys.argv[2:])
    try:
        raw = sys.stdin.read()
        inp = json.loads(raw) if raw.strip() else {}
        handler = {"pretool": pretool, "subagentstop": subagentstop, "stop": stop, "beskyt": beskyt,
                   "prompt": brugerprompt}.get(cmd)
        if handler:
            handler(inp, datamappe())
    except Exception:
        try:
            log(datamappe(), haendelse="hookfejl", kommando=cmd, fejl=traceback.format_exc()[-800:])
        except Exception:
            pass
    return 0


if __name__ == "__main__":
    sys.exit(main())
