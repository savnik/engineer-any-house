#!/usr/bin/env python3
"""byg-kontrol: håndhæver det uafhængige kvalitetskontrol-loop (plugin-hook til Claude Code/Cowork).

Fra hooks/hooks.json:  python3 kontrol_gate.py pretool | subagentstop | stop   (hook-input på stdin)
Manuelt:               python3 kontrol_gate.py status
                       python3 kontrol_gate.py nulstil <leverance-id>
                       (uden CLAUDE_PLUGIN_DATA findes pluginets datamappe under ~/.claude/plugins/data/)

Regler
- Kald af byg-fagagenter og kontrolagenter skal have linjen "LEVERANCE: <id>" i prompten.
- Et fagkald sætter leverancen til "afventer_kontrol". En ny fagversion kræver først en kontroldom.
- Kontrolagentens slutbesked skal indeholde en gyldig JSON-dom (faelles/kontrolprotokol.md, afsnit 5).
  Ugyldig dom → kontrolagenten sendes tilbage én gang for at rette den.
- Højst 3 forsøg pr. runde. Tredje afviste dom → "stoppet": root cause-analyse af, hvorfor fagagenten
  ikke leverede korrekt i første forsøg, og implementeret forbedring af fagagenten.
- Ny runde (højst 3 runder): et nyt fagkald under samme leverance-ID starter runde n+1 med forsøg 1,
  når RCA-filen for runden findes og indeholder linjen "Forbedring implementeret: ja".
  Efter sidste runde: eskalering til brugeren, og leverancen kan kun genoptages under et nyt leverance-ID.
- Stop-hooken forhindrer (én gang pr. stop) afslutning, mens sessionens leverancer mangler kontrol,
  er afvist eller mangler RCA.
- Kontrolkald med et ukendt ID behandles som gennemgang af eksternt materiale (uden loop).
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
FORBEDRING_RE = re.compile(r"forbedring\s+implementeret\W{0,6}ja\b", re.IGNORECASE)
LEV_RE = re.compile(r"LEVERANCE\s*:\s*([^\s`'\"<>]+)", re.IGNORECASE)
BLOKERENDE = {"kritisk", "væsentlig"}
STATUSSER = {"nyt", "aabent", "åbent", "lukket", "bestridt"}


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


def naeste_skridt(lev: str, e: dict) -> str:
    st = e.get("status")
    r = runde(e)
    if st == "afvist":
        hvem = e.get("fag_agent") or "projektlederen (egen leverance)"
        return (f"Afvist (runde {r}/{MAKS_RUNDER}, forsøg {e.get('forsoeg')}/{MAKS}): send fundene retur til {hvem} med "
                f"'LEVERANCE: {lev}' og kald derefter {e.get('kontrol_agent')} igen.")
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
        if art == "fag":
            if e:
                if e.get("fag") != fag:
                    return afvis_kald(f"Leverance-ID {lev} tilhører faget '{e.get('fag')}'. Brug et nyt ID til {fag}.")
                status = e.get("status")
                if status in ("afventer_kontrol", "under_kontrol"):
                    return afvis_kald(f"Leverance {lev} (forsøg {e.get('forsoeg')}/{MAKS}) er ikke kontrolleret endnu. "
                                      f"Kald {e.get('kontrol_agent')} med 'LEVERANCE: {lev}' og stien til fagnotatet først.")
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
            e.update(status="afventer_kontrol", session_id=sid, opdateret=nu())
            gem(d, s)
            log(d, haendelse="fagkald", leverance=lev, runde=runde(e), forsoeg=e["forsoeg"], agent=st)
            return
        # kontrolkald
        if fag == "projekt":
            if e and e.get("type") != "projekt":
                return afvis_kald(f"Leverance {lev} er en {e.get('fag')}-leverance og kontrolleres af {e.get('kontrol_agent')}.")
            if not e:
                e = L[lev] = {"fag": "projekt", "type": "projekt", "forsoeg": 0, "kontrol_agent": st,
                              "oprettet": nu(), "domme": []}
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
            elif e.get("status") not in ("afventer_kontrol", "under_kontrol"):
                return afvis_kald(f"Leverance {lev} har status '{e.get('status')}' – der er ingen ny fagversion at "
                                  f"kontrollere. {naeste_skridt(lev, e)}")
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


def laes_transkript(sti) -> str:
    try:
        linjer = pathlib.Path(sti).read_text(encoding="utf-8").splitlines()
        for linje in reversed(linjer):
            obj = json.loads(linje)
            msg = obj.get("message") or {}
            if msg.get("role") == "assistant":
                indhold = msg.get("content")
                if isinstance(indhold, str):
                    return indhold
                return "\n".join(b.get("text", "") for b in indhold or [] if isinstance(b, dict))
    except Exception:
        pass
    return ""


def subagentstop(inp: dict, d: pathlib.Path) -> None:
    at = str(inp.get("agent_type") or "")
    _, base = del_navn(at)
    art, fag = klassificer(base)
    if art != "kontrol":
        return
    msg = inp.get("last_assistant_message") or laes_transkript(inp.get("agent_transcript_path"))
    dom, fejl = find_dom(msg)
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
    if not FORBEDRING_RE.search(tekst):
        return (f"{f.name} mangler linjen 'Forbedring implementeret: ja'. Implementér læringen som forbedring af "
                f"fagagenten (agentens hukommelse og repoet), notér hvad der er ændret, og skriv linjen i RCA'en, før "
                f"runde {r + 1} starter.")
    return None


def start_ny_runde(d: pathlib.Path, e: dict, lev: str) -> None:
    e["runde"] = runde(e) + 1
    e["forsoeg"] = 1
    log(d, haendelse="ny_runde", leverance=lev, runde=e["runde"])


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
            if status == "afventer_kontrol":
                punkter.append(f"{lev}: afventer kontrol → kald {e.get('kontrol_agent')} med 'LEVERANCE: {lev}'.")
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
        handler = {"pretool": pretool, "subagentstop": subagentstop, "stop": stop}.get(cmd)
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
