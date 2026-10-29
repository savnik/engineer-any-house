#!/usr/bin/env python3
"""Kontrol-armen: måler, hvad den uafhængige kvalitetskontrol tilfører fagagenten på eksamenssættet.

Brug:  python3 scripts/review_ab.py koer <fag> [--id EL-001,...] [--parallel 3] [--kontrolmodel opus]
                                      [--genbrug <resultatfil fra exam.py koer>] [--max-turns 12]
       python3 scripts/review_ab.py rapport <resultatfil>

For hver udviklingsopgave:
  1. fagagenten svarer (plugin-armen fra exam.py) og svaret rettes efter facit,
  2. fagets kontrolagent (byg-kontrol) dømmer svaret uden at kende facit,
  3. afviser kontrollen med blokerende fund, får fagagenten fundene ordret og retter én gang (som forsøg 2 i
     kontrol-loopet), og det rettede svar rettes igen efter facit.

Rapporten krydser kontrollens dom med facit:
  fanget            forkert svar, afvist          → rettet / ikke rettet efter returen
  overset           forkert svar, godkendt
  falsk afvisning   rigtigt svar, afvist          → bevaret / skadet efter returen
  godkendt korrekt  rigtigt svar, godkendt
Og den samlede gevinst: bestået før og efter kontrol, netto (rettet − skadet), pris pr. bestået opgave i hver arm.

Baggrund: forskningen i multi-agent-systemer (Google/MIT 2025, Apple 2026) viser, at ekstra agenter kun betaler sig,
når de fanger fejl, som den enkelte agent ikke selv fanger, og at gevinsten falder, jo bedre den enkelte agent er.
Eksamen målte hidtil kun fagagenten. Denne arm måler kontrollens præcision, recall og nettoværdi.

Kun udviklingssættet bruges. Kontrolagenten kører med kun læseværktøjer på en kopi af byg-kontrol uden hooks og
uden internet. Resultater gemmes i eksamen/<fag>/results/kontrol/ (ignoreres af git og indgår ikke i exam.py's
rapporter). Kræver login og koster tokens: ca. 2–3 gange plugin-armen.
"""
import argparse
import concurrent.futures
import datetime
import json
import pathlib
import shutil
import sys
import tempfile
import threading

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import exam  # noqa: E402

ROOT = exam.ROOT
REGISTRY = ROOT / "plugins" / "byg-kontrol" / "hooks" / "fagregister.json"
BLOCKING = {"kritisk", "væsentlig", "vaesentlig"}

KONTROL_PROMPT = """LEVERANCE: eksamen/{fag}/{id}
KONTROLNIVEAU: {niveau}
FORSØG: 1

Dette er en kontrol af en skriftlig besvarelse, ikke en sag: der er ingen sagsmappe, ingen tidligere domme og intet
internet. Bestillingen er opgaven, og leverancen er fagagentens besvarelse – begge står nedenfor. Kontrollér
besvarelsen fagligt efter din kontrolprotokol og din kontrolviden (læs dit fags kontrolfil først). Efterprøv tal,
grænseværdier og regler mod din kontrolviden. Afvis kun med blokerende fund (kritisk eller væsentlig), når
besvarelsen er fagligt forkert eller mangler noget, opgaven kræver – ikke for formuleringer eller manglende
kildehenvisninger. Afslut med JSON-dommen (felterne dom og fund er nok; blokerende fund skal have paastand,
krav, kilde og handling).

OPGAVE:
<<<
{opgave}
>>>

BESVARELSE FRA FAGAGENTEN:
<<<
{svar}
>>>"""

RETUR_PROMPT = """{opgave}

Din tidligere besvarelse:
<<<
{svar}
>>>

Den uafhængige kvalitetskontrol har afvist besvarelsen med disse blokerende fund:
{fund}

Tjek hvert fund mod din videnbase. Ret kun det, fundene vedrører, og kun hvis du er enig. Er du uenig i et fund,
så behold din besvarelse på det punkt og skriv kort hvorfor. Aflevér hele besvarelsen igen i samme format som
opgaven kræver."""


# ---------- parsing ----------

def parse_dom(text: str) -> dict | None:
    """The last JSON object in the answer that has a 'dom' field (the control agent ends with it)."""
    text = text or ""
    dec = json.JSONDecoder()
    pos = text.rfind("{")
    while pos >= 0:
        try:
            obj, _ = dec.raw_decode(text[pos:])
            if isinstance(obj, dict) and "dom" in obj:
                return obj
        except json.JSONDecodeError:
            pass
        pos = text.rfind("{", 0, pos)
    return None


def blocking_findings(dom: dict | None) -> list[dict]:
    if not dom:
        return []
    return [f for f in dom.get("fund") or [] if isinstance(f, dict)
            and str(f.get("klasse", "")).lower() in BLOCKING and str(f.get("status", "nyt")).lower() != "lukket"]


def classify(correct_before: bool, rejected: bool, correct_after: bool | None) -> str:
    if not rejected:
        return "godkendt_korrekt" if correct_before else "overset"
    if correct_before:
        return "falsk_afvisning_bevaret" if correct_after else "falsk_afvisning_skadet"
    return "fanget_rettet" if correct_after else "fanget_ikke_rettet"


def format_findings(fund: list[dict]) -> str:
    keys = ("id", "klasse", "sted", "paastand", "krav", "kilde", "handling")
    return "\n".join("- " + " · ".join(f"{k}: {f[k]}" for k in keys if f.get(k)) for f in fund)


# ---------- running ----------

def control_agent(trade_plugin: str) -> str:
    reg = json.loads(REGISTRY.read_text(encoding="utf-8"))
    for fag_id, entry in reg["fag"].items():
        if trade_plugin == f"byg-{fag_id}":
            return entry["kontrol"]
    raise SystemExit(f"Ingen kontrolagent for {trade_plugin} i fagregister.json")


def prepare_control(tmp: pathlib.Path) -> pathlib.Path:
    """byg-kontrol without hooks: the hooks guard real cases (LEVERANCE state, Stop) and would interfere here."""
    dst = exam.prepare_plugin("byg-kontrol", tmp)
    shutil.rmtree(dst / "hooks", ignore_errors=True)
    return dst


def run_one(task: dict, args, tmp: pathlib.Path, plugin_dir: pathlib.Path, agent: str,
            kontrol_dir: pathlib.Path, kontrol_agent: str, reused: dict | None) -> dict:
    work = pathlib.Path(tempfile.mkdtemp(prefix="kontrol-", dir=tmp))
    if reused:
        first = {k: reused.get(k) for k in ("svar", "bestaaet", "note", "pris_usd", "sek")}
        first["genbrugt"] = True
    else:
        first = exam.answer_task(task, "plugin", args, tmp, plugin_dir, agent)
    row = {"id": task["id"], "type": task["type"], "niveau": task["niveau"],
           "foer": {k: first.get(k) for k in ("bestaaet", "note", "pris_usd", "sek", "genbrugt") if k in first},
           "svar_foer": first.get("svar", "")}
    if first.get("fejl") or not first.get("svar"):
        row.update(fejl=True, note="kørselsfejl i fagagentens svar")
        return row

    extra = ["--tools", "Read,Glob,Grep", "--max-turns", str(args.max_turns_kontrol),
             "--plugin-dir", str(kontrol_dir), "--add-dir", str(kontrol_dir), "--agent", kontrol_agent]
    if args.kontrolmodel:
        extra += ["--model", args.kontrolmodel]
    prompt = KONTROL_PROMPT.format(fag=args.fag, id=task["id"], niveau=args.niveau,
                                   opgave=exam.build_prompt(task), svar=first["svar"])
    k = exam.run_claude(prompt, work, extra, args.timeout)
    ktext = k.get("result") or ""
    dom = parse_dom(ktext)
    row["kontrol"] = {"pris_usd": k.get("total_cost_usd") or 0, "sek": round((k.get("duration_ms") or 0) / 1000, 1),
                      "ture": k.get("num_turns")}
    if k.get("is_error") or dom is None:
        row.update(fejl=True, note="kørselsfejl eller ingen dom fra kontrollen: "
                   + (k.get("fejl") or ktext[-160:]))
        return row
    fund = blocking_findings(dom)
    rejected = bool(fund)
    row["kontrol"].update(dom=dom.get("dom"), afvist=rejected, blokerende=len(fund),
                          fund=[{x: f.get(x) for x in ("id", "klasse", "paastand", "krav", "kilde")} for f in fund])

    after = None
    if rejected:
        retry = RETUR_PROMPT.format(opgave=exam.build_prompt(task), svar=first["svar"], fund=format_findings(fund))
        r = exam.run_claude(retry, work, exam.arm_args("plugin", args, plugin_dir, agent), args.timeout)
        rtext = r.get("result") or ""
        if r.get("is_error") or not rtext:
            row.update(fejl=True, note="kørselsfejl i rettelsen")
            return row
        g = exam.grade(task, rtext, work, args)
        after = g["bestaaet"] and not g.get("fejl")
        row["efter"] = {"bestaaet": after, "note": g.get("note"),
                        "pris_usd": (r.get("total_cost_usd") or 0) + g.get("pris_bedoemmelse", 0),
                        "sek": round((r.get("duration_ms") or 0) / 1000, 1)}
        row["svar_efter"] = rtext
    row["kategori"] = classify(bool(first["bestaaet"]), rejected, after)
    row["bestaaet_efter_kontrol"] = after if rejected else bool(first["bestaaet"])
    return row


# ---------- report ----------

def summarize(rows: list[dict]) -> dict:
    ok = [r for r in rows if not r.get("fejl")]
    cats: dict[str, int] = {}
    for r in ok:
        cats[r["kategori"]] = cats.get(r["kategori"], 0) + 1
    before = sum(1 for r in ok if r["foer"]["bestaaet"])
    after = sum(1 for r in ok if r["bestaaet_efter_kontrol"])
    caught = cats.get("fanget_rettet", 0) + cats.get("fanget_ikke_rettet", 0)
    false_rej = cats.get("falsk_afvisning_bevaret", 0) + cats.get("falsk_afvisning_skadet", 0)
    wrong = len(ok) - before
    cost_plugin = sum(r["foer"].get("pris_usd") or 0 for r in ok if not r["foer"].get("genbrugt"))
    cost_extra = sum((r.get("kontrol") or {}).get("pris_usd", 0) + (r.get("efter") or {}).get("pris_usd", 0)
                     for r in ok)
    reused = any(r["foer"].get("genbrugt") for r in ok)
    return {
        "n": len(ok), "koerselsfejl": len(rows) - len(ok), "kategorier": cats,
        "bestaaet_foer": before, "bestaaet_efter": after,
        "netto": cats.get("fanget_rettet", 0) - cats.get("falsk_afvisning_skadet", 0),
        "afvisningsrate": round((caught + false_rej) / len(ok), 3) if ok else None,
        "praecision": round(caught / (caught + false_rej), 3) if caught + false_rej else None,
        "recall": round(caught / wrong, 3) if wrong else None,
        "pris_plugin_usd": None if reused else round(cost_plugin, 3),
        "pris_kontrol_og_retur_usd": round(cost_extra, 3),
        "pris_pr_bestaaet_plugin": None if reused or not before else round(cost_plugin / before, 4),
        "pris_pr_bestaaet_med_kontrol": None if reused or not after else round((cost_plugin + cost_extra) / after, 4),
    }


def report(path: pathlib.Path) -> str:
    d = json.loads(path.read_text(encoding="utf-8"))
    s = d.get("sammendrag") or summarize(d["resultater"])
    c = s["kategorier"]
    pct = lambda v: "–" if v is None else f"{v * 100:.0f} %"  # noqa: E731
    lines = [
        f"# Kontrol-arm · {d['fag']} · {d['tid']} · kontrol: {d['kontrolagent']} ({d.get('kontrolmodel') or 'agentens model'})",
        "",
        f"Opgaver: {s['n']} (kørselsfejl: {s['koerselsfejl']})",
        f"Bestået: {s['bestaaet_foer']} uden kontrol → {s['bestaaet_efter']} med kontrol (netto {s['netto']:+d})",
        "",
        "| Kontrollens dom | Antal |",
        "|---|---:|",
        f"| Forkert svar, afvist og rettet | {c.get('fanget_rettet', 0)} |",
        f"| Forkert svar, afvist, ikke rettet | {c.get('fanget_ikke_rettet', 0)} |",
        f"| Forkert svar, godkendt (overset) | {c.get('overset', 0)} |",
        f"| Rigtigt svar, afvist, stadig rigtigt efter retur | {c.get('falsk_afvisning_bevaret', 0)} |",
        f"| Rigtigt svar, afvist, forkert efter retur (skadet) | {c.get('falsk_afvisning_skadet', 0)} |",
        f"| Rigtigt svar, godkendt | {c.get('godkendt_korrekt', 0)} |",
        "",
        f"Afvisningsrate {pct(s['afvisningsrate'])} · præcision {pct(s['praecision'])} (afvisninger der ramte en reel fejl)"
        f" · recall {pct(s['recall'])} (forkerte svar, kontrollen fangede)",
    ]
    if s["pris_plugin_usd"] is not None:
        lines.append(f"Pris: plugin {s['pris_plugin_usd']} $ + kontrol og retur {s['pris_kontrol_og_retur_usd']} $ · "
                     f"pr. bestået {s['pris_pr_bestaaet_plugin']} $ → {s['pris_pr_bestaaet_med_kontrol']} $")
    else:
        lines.append(f"Pris for kontrol og retur: {s['pris_kontrol_og_retur_usd']} $ (fagagentens svar genbrugt)")
    lines += ["", "Beslutningsstøtte: kontrollen betaler sig på eksamen, hvis netto er mindst +2 (én kørsels støj er ±2), "
              "og præcisionen er høj nok til, at returerne ikke koster mere, end de redder. Lav præcision betyder "
              "returer for intet i rigtige sager, også når netto er 0."]
    return "\n".join(lines)


# ---------- commands ----------

def cmd_run(args) -> int:
    goals, tasks = exam.load_trade(args.fag)
    tasks = [t for t in tasks if t["saet"] == "udvikling"]
    if args.id:
        wanted = set(args.id.split(","))
        tasks = [t for t in tasks if t["id"] in wanted]
    reused_rows: dict[str, dict] = {}
    if args.genbrug:
        src = json.loads(pathlib.Path(args.genbrug).read_text(encoding="utf-8"))
        for r in src["resultater"]:
            if r.get("arm") == "plugin" and r.get("svar") and not r.get("fejl") and r.get("saet") == "udvikling":
                reused_rows[r["id"]] = r
        tasks = [t for t in tasks if t["id"] in reused_rows]
    agent = f"{goals['plugin']}:{goals['agent']}"
    kontrol_agent = f"byg-kontrol:{control_agent(goals['plugin'])}"
    print(f"{args.fag}: {len(tasks)} udviklingsopgaver · fag {agent} · kontrol {kontrol_agent}", flush=True)
    rows, lock = [], threading.Lock()
    with tempfile.TemporaryDirectory(prefix="kontrol-ab-") as tmpname:
        tmp = pathlib.Path(tmpname)
        plugin_dir = exam.prepare_plugin(goals["plugin"], tmp, False, args.plugin_rev)
        kontrol_dir = prepare_control(tmp)
        with concurrent.futures.ThreadPoolExecutor(max_workers=args.parallel) as pool:
            futs = [pool.submit(run_one, t, args, tmp, plugin_dir, agent, kontrol_dir, kontrol_agent,
                                reused_rows.get(t["id"])) for t in tasks]
            for fut in concurrent.futures.as_completed(futs):
                r = fut.result()
                with lock:
                    rows.append(r)
                    print(f"  {r['id']:9} {r.get('kategori') or r.get('note')}", flush=True)
    stamp = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
    out_dir = exam.EXAM_DIR / args.fag / "results" / "kontrol"
    out_dir.mkdir(parents=True, exist_ok=True)
    out = out_dir / f"{stamp}-kontrol-udvikling.json"
    rows.sort(key=lambda r: r["id"])
    data = {"fag": args.fag, "tid": stamp, "fagagent": agent, "kontrolagent": kontrol_agent,
            "kontrolmodel": args.kontrolmodel or "", "kontrolniveau": args.niveau,
            "plugin_rev": args.plugin_rev or "arbejdstræ", "genbrug": args.genbrug or "",
            "sammendrag": summarize(rows), "resultater": rows}
    out.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\nGemt: {out.relative_to(ROOT)}\n")
    print(report(out))
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("koer")
    p.add_argument("fag")
    p.add_argument("--id", default="")
    p.add_argument("--parallel", type=int, default=3)
    p.add_argument("--model", default="", help="fagagentens model (standard: agentens egen)")
    p.add_argument("--kontrolmodel", default="", help="kontrolagentens model (standard: agentens egen; opus = 'fuld')")
    p.add_argument("--niveau", choices=["let", "fuld"], default="let")
    p.add_argument("--bedoemmer", default="sonnet")
    p.add_argument("--max-turns", type=int, default=12)
    p.add_argument("--max-turns-kontrol", type=int, default=20)
    p.add_argument("--timeout", type=int, default=900)
    p.add_argument("--plugin-rev", default="")
    p.add_argument("--genbrug", default="", help="genbrug plugin-svar fra en resultatfil fra exam.py koer")
    p = sub.add_parser("rapport")
    p.add_argument("fil")
    args = ap.parse_args()
    if args.cmd == "rapport":
        print(report(pathlib.Path(args.fil)))
        return 0
    args.web = False  # exam.arm_args reads it; the exam runs without internet
    if not shutil.which("claude"):
        print("claude CLI ikke fundet")
        return 1
    return cmd_run(args)


if __name__ == "__main__":
    sys.exit(main())
