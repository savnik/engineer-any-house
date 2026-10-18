#!/usr/bin/env python3
"""Måler byg-agenternes token- og tidsforbrug ud fra Claude Codes lokale transskripter.

Brug:  python3 scripts/forbrug.py [projektmappe] [--siden ÅÅÅÅ-MM-DD] [--til ÅÅÅÅ-MM-DD]
       projektmappe: ~/.claude/projects/<kodet arbejdsmappe> (standard: den aktuelle arbejdsmappe)
       --til er eksklusiv: før/efter en udgivelse sammenlignes med --til <dato> og --siden <dato>.

Viser:
- vægtet forbrug pr. del (hovedtråd, fagagenter, kontrolagenter, øvrige)
- hovedtrådens kontekst pr. kald (median og maks.)
- andel af fag- og kontroltokens i forsøg 2–3 (retur)
- gentagne sidehentninger og statuskald i hovedtråden
- svarlængde: slutsvar (hovedtrådens svar til brugeren, subagenternes rapport) og tekst mellem værktøjskald

Vægtning i forhold til almindelige input-tokens: cache-læsning 0,1 ×, cache-skrivning 1,25 × og output 5 ×.
Scriptet læser kun lokale filer og skriver ingenting. Output kan indeholde sag-id'er; læg det ikke i repoet.
"""
import collections
import json
import os
import pathlib
import re
import statistics
import sys

VAEGT = {"input_tokens": 1.0, "cache_read_input_tokens": 0.1, "cache_creation_input_tokens": 1.25, "output_tokens": 5.0}
KONTEKST = ("input_tokens", "cache_creation_input_tokens", "cache_read_input_tokens")
FORSOEG_RE = re.compile(r"Fors(?:ø|o)g:\s*(\d)")
LEV_RE = re.compile(r"LEVERANCE:\s*(\S+)")
MAAL_TXT = "hovedtråd og fagagenter under ca. 800, kontrolagenter under ca. 1.500"


def laes(sti: pathlib.Path) -> dict:
    """Usage pr. API-kald (max pr. besked-id, fordi streaming gentager beskeden), første prompt og værktøjskald."""
    pr_besked, foerste, vaerktoej, start = {}, "", [], None
    tekst = {}                        # besked-id -> [tegn, har værktøjskald]; streaming deler en besked i flere linjer
    slutsvar, sidste = [], None       # sidste besked-id uden værktøjskald før en brugerbesked eller slut
    for linje in sti.open(encoding="utf-8"):
        try:
            o = json.loads(linje)
        except Exception:
            continue
        start = start or o.get("timestamp")
        msg = o.get("message") or {}
        if not foerste and o.get("type") == "user":
            c = msg.get("content")
            foerste = c if isinstance(c, str) else " ".join(x.get("text", "") for x in c or [] if isinstance(x, dict))
        if o.get("type") == "user" and not o.get("isMeta"):
            c = msg.get("content")
            if isinstance(c, str) or any(isinstance(x, dict) and x.get("type") == "text" for x in c or []):
                if sidste and tekst[sidste][0]:
                    slutsvar.append(tekst[sidste][0])
                sidste = None
        if o.get("type") != "assistant":
            continue
        t = tekst.setdefault(msg.get("id"), [0, False])
        for c in msg.get("content") or []:
            if isinstance(c, dict) and c.get("type") == "tool_use":
                vaerktoej.append((c.get("name"), c.get("input") or {}))
                t[1] = True
            elif isinstance(c, dict) and c.get("type") == "text":
                t[0] += len(c.get("text", ""))
        sidste = None if t[1] else msg.get("id")
        u = pr_besked.setdefault(msg.get("id"), collections.Counter())
        for k in VAEGT:
            u[k] = max(u[k], int((msg.get("usage") or {}).get(k) or 0))
    if sidste and tekst[sidste][0]:
        slutsvar.append(tekst[sidste][0])
    mellem = sum(n for n, _ in tekst.values()) - sum(slutsvar)   # al anden tekst: mellemsvar undervejs
    return {"kald": list(pr_besked.values()), "foerste": foerste, "vaerktoej": vaerktoej, "start": start or "",
            "slutsvar": slutsvar, "mellemtekst": mellem}


def vaegtet(kald) -> float:
    return sum(u[k] * v for u in kald for k, v in VAEGT.items())


def main() -> int:
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    siden = sys.argv[sys.argv.index("--siden") + 1] if "--siden" in sys.argv else ""
    til = sys.argv[sys.argv.index("--til") + 1] if "--til" in sys.argv else ""
    args = [a for a in args if a not in (siden, til)]
    mappe = pathlib.Path(args[0]).expanduser() if args else \
        pathlib.Path.home() / ".claude" / "projects" / re.sub(r"[^A-Za-z0-9]", "-", os.getcwd())
    if not mappe.is_dir():
        print(f"Findes ikke: {mappe}")
        return 1

    dele = collections.defaultdict(list)          # del -> liste af kørsler
    hovedkontekst, statuskald, hentninger = [], 0, collections.Counter()
    retur = collections.defaultdict(lambda: [0.0, 0.0])  # del -> [forsøg 1, forsøg 2–3]
    leverancer = collections.defaultdict(float)
    for hoved in sorted(mappe.glob("*.jsonl")):
        h = laes(hoved)
        if not h["kald"] or h["start"][:10] < siden or (til and h["start"][:10] >= til):
            continue
        subs = []
        for sub in sorted((mappe / hoved.stem / "subagents").glob("*.jsonl")):
            meta = sub.with_suffix(".meta.json")
            typ = json.loads(meta.read_text(encoding="utf-8")).get("agentType", "") if meta.exists() else ""
            subs.append((typ, sub))
        if not any(typ.startswith("byg") for typ, _ in subs):
            continue  # kun sessioner, hvor byg-agenterne er brugt
        dele["hovedtråd"].append(h)
        hovedkontekst += [sum(u[k] for k in KONTEKST) for u in h["kald"]]
        statuskald += sum(1 for n, i in h["vaerktoej"] if n == "Bash" and "kontrol_gate.py" in str(i.get("command"))
                          and " status" in str(i.get("command")))
        for typ, sub in subs:
            r = laes(sub)
            if not r["kald"]:
                continue
            del_ = "kontrolagenter" if "-kontrol" in typ else "fagagenter" if typ.startswith("byg") else "øvrige"
            dele[del_].append(r)
            hentninger.update(i.get("url") for n, i in r["vaerktoej"] if n == "WebFetch")
            if del_ in ("fagagenter", "kontrolagenter"):
                m = FORSOEG_RE.search(r["foerste"])
                retur[del_][1 if m and int(m.group(1)) > 1 else 0] += vaegtet(r["kald"])
                lev = LEV_RE.search(r["foerste"])
                if lev:
                    leverancer[lev.group(1)] += vaegtet(r["kald"])

    total = sum(vaegtet(r["kald"]) for liste in dele.values() for r in liste)
    if not total:
        print("Ingen sessioner i perioden.")
        return 0
    print(f"Mappe: {mappe}" + (f" · siden {siden}" if siden else "") + (f" · før {til}" if til else ""))
    print(f"Sessioner: {len(dele['hovedtråd'])} · vægtet forbrug i alt: {total / 1e6:.1f}M\n")
    print(f"{'Del':16} {'kørsler':>7} {'vægtet':>9} {'andel':>6}")
    for del_ in ("hovedtråd", "fagagenter", "kontrolagenter", "øvrige"):
        v = sum(vaegtet(r["kald"]) for r in dele[del_])
        print(f"{del_:16} {len(dele[del_]):7} {v / 1e6:8.1f}M {100 * v / total:5.0f} %")
    if hovedkontekst:
        print(f"\nHovedtråd: median-kontekst {statistics.median(hovedkontekst) / 1e3:.0f}k · maks. "
              f"{max(hovedkontekst) / 1e3:.0f}k · kald over 200k: {sum(n > 200_000 for n in hovedkontekst)} af "
              f"{len(hovedkontekst)} · statuskald: {statuskald}")
    for del_, (f1, f23) in retur.items():
        if f1 + f23:
            print(f"{del_.capitalize()}: {100 * f23 / (f1 + f23):.0f} % af forbruget i forsøg 2–3 (retur)")
    if hentninger:
        n = sum(hentninger.values())
        print(f"Sidehentninger: {n}, heraf gentagne: {100 * (n - len(hentninger)) / n:.0f} %")
    print(f"\nSvarlængde i tegn (mål for median: {MAAL_TXT})")
    print(f"{'Del':16} {'slutsvar':>8} {'median':>7} {'p90':>7} {'mellemtekst/kørsel':>19}")
    for del_ in ("hovedtråd", "fagagenter", "kontrolagenter", "øvrige"):
        svar = sorted(n for r in dele[del_] for n in r["slutsvar"])
        if svar:
            mellem = sum(r["mellemtekst"] for r in dele[del_]) / len(dele[del_])
            print(f"{del_:16} {len(svar):8} {statistics.median(svar):7.0f} {svar[int(0.9 * (len(svar) - 1))]:7} {mellem:19.0f}")
    if leverancer:
        print(f"Leverancer: {len(leverancer)} · median vægtet forbrug pr. leverance: "
              f"{statistics.median(leverancer.values()) / 1e6:.2f}M")
    return 0


if __name__ == "__main__":
    sys.exit(main())
