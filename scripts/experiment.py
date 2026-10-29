#!/usr/bin/env python3
"""Forsøgslog og benchmark for forbedringer af fag-plugins (bruges af CI-agenten `ci-improvement`).

Brug:
  python3 scripts/experiment.py status [--trade electrical]        benchmark, åbne forsøg, forslag og udestående huller
  python3 scripts/experiment.py list [--trade electrical] [--category videnbase] [--status afsluttet]
  python3 scripts/experiment.py show F-001
  python3 scripts/experiment.py search <ord> [<ord> ...]   er en idé eller en opgave afprøvet før?
  python3 scripts/experiment.py new --trade electrical[,plumbing] --category K --hypothesis "…" [--change "…"] [--tasks EL-012,…]
                               [--proposal]
  python3 scripts/experiment.py start F-007                gør et forslag til et åbent forsøg (noterer rev_foer)
  python3 scripts/experiment.py measure F-001 (--before | --after) <resultatfil> [<resultatfil> ...] [--rev REV]
  python3 scripts/experiment.py assess F-001               beslutningsreglen på de gemte målinger
  python3 scripts/experiment.py close F-001 --decision keep|discard|undecided --learning "…"
                               [--rationale "…"] [--rev-after REV] [--pr "#7"]
  python3 scripts/experiment.py benchmark [--trade electrical]
  python3 scripts/experiment.py check                      format, og at ingen holdout-ID'er står i loggen

--decision keep|discard|undecided gemmes som behold|forkast|uafklaret i loggen.

Loggen (`exam/experiments.json`) og benchmarket (`exam/benchmark.json`) ligger i repoet. De rummer kun
sammendrag pr. gruppe (sæt × opgavefil). Holdout-opgaver gemmes kun som antal og en hash af ID-listen, så
loggen aldrig peger på enkelte holdout-opgaver. Resultatfilerne bag målingerne ligger lokalt og ignoreres af git.
"""
import argparse
import datetime
import hashlib
import json
import pathlib
import re
import subprocess
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import exam  # noqa: E402

ROOT = exam.ROOT
LOG_FILE = exam.EXAM_DIR / "experiments.json"
BENCHMARK_FILE = exam.EXAM_DIR / "benchmark.json"
CATEGORIES = {
    "videnbase": "ny eller ændret tekst i references/ eller SKILL.md",
    "prompt": "ændret agentprompt (agents/*.md)",
    "model": "model eller effort",
    "rettemaske": "rettet facit eller kriterium i udviklingssættet (ændrer prøven, ikke pluginet)",
    "opgaver": "nye eller omskrevne opgaver",
    "vaerktoej": "eksamensværktøjet eller måleopsætningen",
    "nulmaaling": "måling uden ændring, fx nyt sæt eller ny model som udgangspunkt",
}
# Categories where a before/after comparison of the plugin arm decides the outcome.
PLUGIN_CATEGORIES = {"videnbase", "prompt", "model"}
STATUSES = ["forslag", "aaben", "afsluttet"]
DECISIONS = {"behold", "forkast", "uafklaret"}
# CLI choice (English) → stored decision (Danish).
DECISION_CHOICES = {"keep": "behold", "discard": "forkast", "undecided": "uafklaret"}
NOISE_TASKS = 2         # one run moves about ±2 free-text tasks per set
PRICE_TOLERANCE = 0.10  # cost per passed task may rise at most 10 % without a quality gain
HOLDOUT_BUDGET = 8      # holdout measurements per trade before new holdout tasks should be written


# ---------- storage ----------

def load_log() -> dict:
    return json.loads(LOG_FILE.read_text(encoding="utf-8")) if LOG_FILE.exists() else {"forsoeg": []}


def load_benchmark() -> dict:
    return json.loads(BENCHMARK_FILE.read_text(encoding="utf-8")) if BENCHMARK_FILE.exists() else {"fag": {}}


def save(path: pathlib.Path, data: dict) -> None:
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def find(log: dict, eid: str) -> dict:
    for e in log["forsoeg"]:
        if e["id"] == eid:
            return e
    raise SystemExit(f"Intet forsøg med id {eid}")


def next_id(log: dict) -> str:
    return f"F-{max([int(e['id'][2:]) for e in log['forsoeg']] or [0]) + 1:03d}"


def git_rev() -> str:
    r = subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=ROOT, capture_output=True, text=True)
    return r.stdout.strip()


def plugins_dirty() -> bool:
    r = subprocess.run(["git", "status", "--porcelain", "plugins"], cwd=ROOT, capture_output=True, text=True)
    return bool(r.stdout.strip())


def today() -> str:
    return datetime.date.today().isoformat()


# ---------- measurement ----------

def task_files(trade: str) -> dict[str, str]:
    """Task id -> the task file it lives in (opgaver-a, opgaver-c, …). Files are separate sets, e.g. AK in -c."""
    out = {}
    for f in sorted((exam.EXAM_DIR / trade).glob("tasks*.json")):
        for t in json.loads(f.read_text(encoding="utf-8"))["opgaver"]:
            out[t["id"]] = f.stem
    return out


def id_hash(ids: list[str]) -> str:
    return hashlib.sha256(",".join(sorted(ids)).encode()).hexdigest()[:12]


def summarize(files: list[pathlib.Path]) -> dict[str, dict]:
    """Per trade: groups '<sæt>/<opgavefil>' -> arm -> counts, cost and time.

    When several files hold the same task and arm, the newest file wins (file names start with a timestamp),
    as in exam.latest_basis. Repeats within a file are decided by majority, as in the report."""
    per_trade: dict[str, dict[tuple[str, str], list[dict]]] = {}
    revs: dict[str, set[str]] = {}
    for f in sorted(files, key=lambda p: p.name):
        d = json.loads(f.read_text(encoding="utf-8"))
        latest = per_trade.setdefault(d["fag"], {})
        fresh: dict[tuple[str, str], list[dict]] = {}
        for r in exam.valid_rows(f):
            fresh.setdefault((r["id"], r["arm"]), []).append(r)
        latest.update(fresh)
        if any(arm == "plugin" for _, arm in fresh):
            revs.setdefault(d["fag"], set()).add(d.get("plugin_rev") or "arbejdstræ")
    out = {}
    for trade, latest in per_trade.items():
        where = task_files(trade)
        groups: dict[str, dict] = {}
        for (tid, arm), rows in sorted(latest.items()):
            g = groups.setdefault(f"{rows[0]['saet']}/{where.get(tid, 'ukendt')}", {}).setdefault(
                arm, {"ids": [], "failed": [], "cost": 0.0, "secs": [], "toks": []})
            g["ids"].append(tid)
            if sum(r["bestaaet"] for r in rows) * 2 <= len(rows):
                g["failed"].append(tid)
            # Mean per task, so repeats (--repeat-free) do not make an arm look more expensive.
            g["cost"] += sum(r.get("pris_usd") or 0 for r in rows) / len(rows)
            g["secs"] += [r["sek"] for r in rows if r.get("sek") is not None]
            g["toks"] += [r["tokens_ud"] for r in rows if r.get("tokens_ud") is not None]
        summary = {}
        for name, arms in sorted(groups.items()):
            summary[name] = {}
            for arm, g in sorted(arms.items()):
                n, ok = len(g["ids"]), len(g["ids"]) - len(g["failed"])
                s = {"n": n, "bestaaet": ok, "opgaver_hash": id_hash(g["ids"]), "pris_usd": round(g["cost"], 3),
                     "pris_pr_bestaaet": round(g["cost"] / ok, 4) if ok else None,
                     "sek_pr_opgave": round(sum(g["secs"]) / len(g["secs"]), 1) if g["secs"] else None,
                     "tokens_ud_pr_opgave": round(sum(g["toks"]) / len(g["toks"])) if g["toks"] else None}
                if name.startswith("udvikling/"):
                    s["fejlede"] = sorted(g["failed"])  # holdout task ids are never stored
                summary[name][arm] = s
        out[trade] = {"rev": ",".join(sorted(revs.get(trade, set()))) or "–", "dato": today(),
                      "filer": sorted(f.name for f in files if json.loads(f.read_text(encoding="utf-8"))["fag"] == trade),
                      "grupper": summary}
    return out


def totals(groups: dict, arm: str, prefix: str = "") -> dict:
    sel = [a[arm] for name, a in groups.items() if arm in a and name.startswith(prefix)]
    n, ok, cost = sum(s["n"] for s in sel), sum(s["bestaaet"] for s in sel), sum(s["pris_usd"] for s in sel)
    return {"n": n, "bestaaet": ok, "pris_usd": cost, "pris_pr_bestaaet": cost / ok if ok else None}


# ---------- decision rule ----------

def assess(category: str, measurements: dict) -> tuple[str, list[str]]:
    """Suggested decision and the reasons, per the rule in exam/README.md ("Forbedringsforsøg").

    behold:    the plugin arm passes at least NOISE_TASKS more of the same tasks, holdout was measured,
               no group falls by NOISE_TASKS or more, and cost per passed task rises at most PRICE_TOLERANCE;
               or quality holds and cost per passed task falls by more than PRICE_TOLERANCE.
    forkast:   a group falls by NOISE_TASKS or more, or cost rises without a gain.
    uafklaret: within noise, holdout missing, or before and after were not measured on the same tasks."""
    if category not in PLUGIN_CATEGORIES:
        return "manuel", [f"kategorien '{category}' afgøres ikke af plugin før/efter – begrund beslutningen"]
    notes, gain, harm, unclear, holdout_seen = [], 0, False, False, False
    cost_before = cost_after = passed_before = passed_after = 0.0
    for trade, m in sorted(measurements.items()):
        before, after = (m.get("foer") or {}).get("grupper"), (m.get("efter") or {}).get("grupper")
        if not before or not after:
            notes.append(f"{trade}: mangler måling {'før' if not before else 'efter'}")
            unclear = True
            continue
        for g in sorted(set(before) | set(after)):
            b, a = before.get(g, {}).get("plugin"), after.get(g, {}).get("plugin")
            if not b or not a:
                notes.append(f"{trade} {g}: kun målt {'efter' if a else 'før'} – indgår ikke")
                continue
            if b["opgaver_hash"] != a["opgaver_hash"]:
                notes.append(f"{trade} {g}: ikke de samme opgaver før og efter ({b['n']} mod {a['n']}) – indgår ikke")
                unclear = True
                continue
            d = a["bestaaet"] - b["bestaaet"]
            holdout_seen |= g.startswith("holdout/")
            gain += d
            harm |= d <= -NOISE_TASKS
            cost_before, cost_after = cost_before + b["pris_usd"], cost_after + a["pris_usd"]
            passed_before, passed_after = passed_before + b["bestaaet"], passed_after + a["bestaaet"]
            flag = "  ← fald ud over støj" if d <= -NOISE_TASKS else ""
            notes.append(f"{trade} {g}: {b['bestaaet']}/{b['n']} → {a['bestaaet']}/{a['n']} ({d:+d}){flag}")
    if not passed_before or not passed_after:
        return "uafklaret", notes + ["ingen sammenlignelige målinger"]
    ppb, ppa = cost_before / passed_before, cost_after / passed_after
    change = ppa / ppb - 1
    notes.append(f"i alt {gain:+d} beståede · pris pr. bestået {ppb:.3f} → {ppa:.3f} $ ({100 * change:+.0f} %)")
    if harm:
        return "forkast", notes + [f"mindst én gruppe faldt {NOISE_TASKS} eller flere opgaver"]
    if unclear:
        return "uafklaret", notes + ["mål før og efter på de samme opgaver"]
    if not holdout_seen:
        return "uafklaret", notes + ["holdout er ikke målt før og efter (--set holdout --release --plugin-rev)"]
    if gain >= NOISE_TASKS and change <= PRICE_TOLERANCE:
        return "behold", notes + ["bedre ud over støj, og prisen pr. bestået holder"]
    if gain >= NOISE_TASKS:
        return "uafklaret", notes + [f"bedre, men pris pr. bestået steg over {round(100 * PRICE_TOLERANCE)} % – vurder"]
    if gain > -NOISE_TASKS and change < -PRICE_TOLERANCE:
        return "behold", notes + ["samme kvalitet, og prisen pr. bestået faldt"]
    if change > PRICE_TOLERANCE:
        return "forkast", notes + ["ingen gevinst, og prisen pr. bestået steg"]
    return "uafklaret", notes + ["inden for støj – gentag med --repeat-free 3, eller forkast"]


# ---------- commands ----------

def line(e: dict) -> str:
    dec = f" → {e['beslutning']}" if e.get("beslutning") else ""
    return f"{e['id']} [{e['status']}{dec}] {','.join(e['fag'])} · {e['kategori']} · {e['hypotese']}"


def holdout_uses(log: dict, trade: str) -> int:
    return sum(1 for e in log["forsoeg"] for side in (e.get("maalinger", {}).get(trade) or {}).values()
               if any(g.startswith("holdout/") for g in side.get("grupper", {})))


def print_benchmark(bench: dict, trades: list[str]) -> None:
    for trade in trades:
        b = bench["fag"].get(trade)
        if not b:
            print(f"\n## {trade}: intet benchmark endnu")
            continue
        print(f"\n## {trade} (senest opdateret {b['opdateret']} af {b['forsoeg']})\n")
        print(f"{'Gruppe':22} {'plugin':>14} {'basis':>14} {'pris/bestået':>13} {'sek':>6}  kilde")
        for g, arms in sorted(b["grupper"].items()):
            p, bs = arms.get("plugin"), arms.get("basis")
            cell = lambda s: f"{s['bestaaet']}/{s['n']} ({100 * s['bestaaet'] / s['n']:.0f} %)" if s else "–"
            ppb = f"{p['pris_pr_bestaaet']:.3f} $" if p and p.get("pris_pr_bestaaet") else "–"
            sek = f"{p['sek_pr_opgave']}" if p and p.get("sek_pr_opgave") else "–"
            print(f"{g:22} {cell(p):>14} {cell(bs):>14} {ppb:>13} {sek:>6}  {b.get('kilder', {}).get(g, '')}")


def cmd_status(args) -> int:
    log, bench = load_log(), load_benchmark()
    trades = [args.trade] if args.trade else sorted(set(bench["fag"]) | set(exam.all_trades()))
    print("# Status for forbedringsarbejdet")
    print_benchmark(bench, trades)
    tried: dict[str, list[str]] = {}
    for e in log["forsoeg"]:
        for t in e.get("opgaver", []):
            tried.setdefault(t, []).append(f"{e['id']} " + (e["beslutning"] if e.get("beslutning") else
                                                             "foreslået" if e["status"] == "forslag" else "åbent"))
    for trade in trades:
        b = bench["fag"].get(trade)
        if not b:
            continue
        gaps = sorted({t for arms in b["grupper"].values() for t in (arms.get("plugin") or {}).get("fejlede", [])})
        print(f"\nUdestående huller i udviklingssættet ({trade}): "
              + (", ".join(f"{t} ({', '.join(tried[t])})" if t in tried else t for t in gaps) or "ingen"))
        uses = holdout_uses(log, trade)
        print(f"Holdout målt {uses} {'gang' if uses == 1 else 'gange'}" + (f" – over budgettet på {HOLDOUT_BUDGET}: skriv nye holdout-opgaver"
                                               if uses > HOLDOUT_BUDGET else ""))
    for status in ("aaben", "forslag"):
        sel = [e for e in log["forsoeg"] if e["status"] == status and (not args.trade or args.trade in e["fag"])]
        print(f"\n## {'Åbne forsøg' if status == 'aaben' else 'Forslag'}\n")
        print("\n".join(f"- {line(e)}" for e in sel) or "- ingen")
    return 0


def cmd_list(args) -> int:
    for e in load_log()["forsoeg"]:
        if (not args.trade or args.trade in e["fag"]) and (not args.category or e["kategori"] == args.category) \
                and (not args.status or e["status"] == args.status):
            print(line(e))
    return 0


def cmd_show(args) -> int:
    e = find(load_log(), args.id)
    print(line(e))
    for k in ("dato", "aendring", "opgaver", "rev_foer", "rev_efter", "pr", "laering", "begrundelse"):
        if e.get(k):
            print(f"  {k}: {', '.join(e[k]) if isinstance(e[k], list) else e[k]}")
    for trade, m in (e.get("maalinger") or {}).items():
        for side in ("foer", "efter"):
            if side in m:
                s = m[side]
                print(f"  {trade} {side} (plugin {s['rev']}, {s['dato']}):")
                for g, arms in s["grupper"].items():
                    p = arms.get("plugin") or {}
                    cost = f"{p['pris_pr_bestaaet']:.3f} $/bestået" if p.get("pris_pr_bestaaet") else ""
                    extra = ", ".join(x for x in (
                        cost,
                        f"{p['sek_pr_opgave']} s/opgave" if p.get("sek_pr_opgave") else "",
                        f"{p['tokens_ud_pr_opgave']} tokens_ud/opgave" if p.get("tokens_ud_pr_opgave") else "") if x)
                    print("    " + g + ": " + " · ".join(f"{arm} {a['bestaaet']}/{a['n']}" for arm, a in arms.items())
                          + (f" ({extra})" if extra else ""))
    if e.get("maalinger"):
        suggestion, notes = assess(e["kategori"], e["maalinger"])
        print(f"  vurdering: {suggestion}")
        print("\n".join(f"    {n}" for n in notes))
    return 0


def cmd_search(args) -> int:
    words = [w.lower() for w in args.words]
    hits = [e for e in load_log()["forsoeg"] if all(w in json.dumps(
        {k: e.get(k) for k in ("hypotese", "aendring", "laering", "begrundelse", "opgaver", "fag", "kategori")},
        ensure_ascii=False).lower() for w in words)]
    print("\n".join(line(e) + (f"\n  læring: {e['laering']}" if e.get("laering") else "") for e in hits)
          or "Ikke afprøvet før.")
    return 0


def cmd_new(args) -> int:
    log = load_log()
    trades = [t for t in args.trade.split(",") if t]
    unknown = [t for t in trades if t not in exam.all_trades() and t != "alle"]
    if unknown:
        raise SystemExit(f"Ukendt fag: {', '.join(unknown)}")
    if args.category not in CATEGORIES:
        raise SystemExit(f"Ukendt kategori – brug en af: {', '.join(CATEGORIES)}")
    tasks = [t for t in args.tasks.split(",") if t]
    holdout = holdout_ids()
    if set(tasks) & holdout:
        raise SystemExit("Et forsøg må aldrig sigte på holdout-opgaver – kun udviklingsopgaver.")
    e = {"id": next_id(log), "dato": today(), "fag": trades, "kategori": args.category,
         "hypotese": args.hypothesis, "aendring": args.change, "opgaver": tasks,
         "status": "forslag" if args.proposal else "aaben", "beslutning": None, "maalinger": {}}
    if not args.proposal:
        e["rev_foer"] = git_rev()
        if plugins_dirty():
            print("ADVARSEL: plugins/ har ucommittede ændringer – rev_foer svarer ikke til det, der måles.")
    log["forsoeg"].append(e)
    save(LOG_FILE, log)
    print(f"Oprettet {e['id']}: {e['hypotese']}" + (f" (før = {e['rev_foer']})" if "rev_foer" in e else ""))
    return 0


def cmd_start(args) -> int:
    log = load_log()
    e = find(log, args.id)
    if e["status"] != "forslag":
        raise SystemExit(f"{e['id']} er ikke et forslag (status {e['status']})")
    e.update(status="aaben", dato=today(), rev_foer=git_rev())
    save(LOG_FILE, log)
    print(f"{e['id']} er åbent (før = {e['rev_foer']})")
    return 0


def cmd_measure(args) -> int:
    log = load_log()
    e = find(log, args.id)
    if e["status"] == "afsluttet":
        raise SystemExit(f"{e['id']} er afsluttet")
    side = "foer" if args.before else "efter"
    files = [pathlib.Path(f) for f in args.files]
    missing = [str(f) for f in files if not f.is_file()]
    if missing:
        raise SystemExit(f"Findes ikke: {', '.join(missing)}")
    for trade, s in summarize(files).items():
        if args.rev:
            s["rev"] = args.rev
        e.setdefault("maalinger", {}).setdefault(trade, {})[side] = s
        print(f"{e['id']} {trade} {side}: plugin {s['rev']} · "
              + " · ".join(f"{g} " + "/".join(f"{arm} {a['bestaaet']}/{a['n']}" for arm, a in arms.items())
                           for g, arms in s["grupper"].items()))
    save(LOG_FILE, log)
    return 0


def cmd_assess(args) -> int:
    e = find(load_log(), args.id)
    suggestion, notes = assess(e["kategori"], e.get("maalinger") or {})
    print("\n".join(notes))
    print(f"\nForslag til beslutning: {suggestion}")
    return 0


def update_benchmark(bench: dict, e: dict) -> list[str]:
    """Replace the benchmark's groups with the experiment's 'efter' (or only) measurement, group by group."""
    changed = []
    for trade, m in (e.get("maalinger") or {}).items():
        s = m.get("efter") or m.get("foer")
        if not s:
            continue
        b = bench["fag"].setdefault(trade, {"grupper": {}})
        b["grupper"].update(s["grupper"])
        b.setdefault("kilder", {}).update({g: f"{e['id']} @ {s['rev']}" for g in s["grupper"]})
        b.update(opdateret=e["slut"], forsoeg=e["id"])
        changed.append(trade)
    return changed


def cmd_close(args) -> int:
    log, bench = load_log(), load_benchmark()
    e = find(log, args.id)
    if e["status"] == "afsluttet":
        raise SystemExit(f"{e['id']} er allerede afsluttet")
    suggestion, notes = assess(e["kategori"], e.get("maalinger") or {})
    if suggestion not in ("manuel", args.decision) and not args.rationale:
        print("\n".join(notes))
        raise SystemExit(f"Reglen foreslår '{suggestion}'. Vælger du '{args.decision}', skal det begrundes "
                         "med --rationale.")
    if suggestion == "manuel" and not args.rationale:
        raise SystemExit(f"Kategorien '{e['kategori']}' kræver --rationale.")
    e.update(status="afsluttet", beslutning=args.decision, laering=args.learning, slut=today(),
             vurdering=suggestion)
    for k, v in (("begrundelse", args.rationale), ("rev_efter", args.rev_after), ("pr", args.pr)):
        if v:
            e[k] = v
    msg = f"{e['id']} afsluttet: {args.decision}"
    if args.decision == "behold":
        changed = update_benchmark(bench, e)
        save(BENCHMARK_FILE, bench)
        msg += f" · benchmark opdateret for {', '.join(changed) or 'ingen fag (ingen målinger)'}"
    save(LOG_FILE, log)
    print(msg)
    return 0


def cmd_benchmark(args) -> int:
    bench = load_benchmark()
    print_benchmark(bench, [args.trade] if args.trade else sorted(bench["fag"]))
    return 0


# ---------- validation ----------

def holdout_ids() -> set[str]:
    out = set()
    for trade in exam.all_trades():
        out |= {t["id"] for t in exam.load_trade(trade)[1] if t["saet"] == "holdout"}
    return out


def validate(log: dict, bench: dict, holdout: set[str]) -> list[str]:
    errors, seen = [], set()
    for e in log.get("forsoeg", []):
        eid = e.get("id", "?")
        if eid in seen:
            errors.append(f"{eid}: id findes to gange")
        seen.add(eid)
        for k in ("id", "dato", "fag", "kategori", "hypotese", "status"):
            if not e.get(k):
                errors.append(f"{eid}: mangler '{k}'")
        if e.get("kategori") not in CATEGORIES:
            errors.append(f"{eid}: ukendt kategori '{e.get('kategori')}'")
        if e.get("status") not in STATUSES:
            errors.append(f"{eid}: ukendt status '{e.get('status')}'")
        if e.get("status") == "afsluttet":
            if e.get("beslutning") not in DECISIONS:
                errors.append(f"{eid}: afsluttet uden gyldig beslutning")
            if not e.get("laering"):
                errors.append(f"{eid}: afsluttet uden læring")
        if e.get("status") == "aaben" and not e.get("rev_foer"):
            errors.append(f"{eid}: åbent forsøg uden rev_foer")
    text = json.dumps(log, ensure_ascii=False) + json.dumps(bench, ensure_ascii=False)
    mentioned = set(re.findall(r"\b[A-ZÆØÅ]+-\d{3}\b", text))
    leaked = sorted(holdout & mentioned)
    if leaked:
        errors.append(f"{len(leaked)} holdout-opgave(r) er nævnt i forsøgsloggen eller benchmarket – fjern dem")
    return errors


def cmd_check(args) -> int:
    errors = validate(load_log(), load_benchmark(), holdout_ids())
    for err in errors:
        print(f"FEJL  {err}")
    log = load_log()
    for trade in exam.all_trades():
        if holdout_uses(log, trade) > HOLDOUT_BUDGET:
            print(f"ADVARSEL  {trade}: holdout er målt {holdout_uses(log, trade)} gange (budget {HOLDOUT_BUDGET})")
    print(f"{len(log['forsoeg'])} forsøg · {len(errors)} fejl")
    return 1 if errors else 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("status")
    p.add_argument("--trade", default="")
    p = sub.add_parser("list")
    p.add_argument("--trade", default="")
    p.add_argument("--category", default="")
    p.add_argument("--status", default="")
    p = sub.add_parser("show")
    p.add_argument("id")
    p = sub.add_parser("search")
    p.add_argument("words", nargs="+")
    p = sub.add_parser("new")
    p.add_argument("--trade", required=True)
    p.add_argument("--category", required=True)
    p.add_argument("--hypothesis", required=True)
    p.add_argument("--change", default="")
    p.add_argument("--tasks", default="", help="udviklingsopgaver, forsøget sigter på")
    p.add_argument("--proposal", action="store_true", help="kun en idé til senere – ingen rev_foer endnu")
    p = sub.add_parser("start")
    p.add_argument("id")
    p = sub.add_parser("measure")
    p.add_argument("id")
    g = p.add_mutually_exclusive_group(required=True)
    g.add_argument("--before", action="store_true")
    g.add_argument("--after", action="store_true")
    p.add_argument("files", nargs="+")
    p.add_argument("--rev", default="", help="pluginets git-revision, når kørslen var på arbejdstræet")
    p = sub.add_parser("assess")
    p.add_argument("id")
    p = sub.add_parser("close")
    p.add_argument("id")
    p.add_argument("--decision", required=True, choices=sorted(DECISION_CHOICES))
    p.add_argument("--learning", required=True)
    p.add_argument("--rationale", default="")
    p.add_argument("--rev-after", default="")
    p.add_argument("--pr", default="")
    p = sub.add_parser("benchmark")
    p.add_argument("--trade", default="")
    sub.add_parser("check")
    args = ap.parse_args()
    if getattr(args, "decision", None):
        args.decision = DECISION_CHOICES[args.decision]  # English CLI choice → stored Danish value
    return {"status": cmd_status, "list": cmd_list, "show": cmd_show, "search": cmd_search, "new": cmd_new,
            "start": cmd_start, "measure": cmd_measure, "assess": cmd_assess, "close": cmd_close,
            "benchmark": cmd_benchmark, "check": cmd_check}[args.cmd](args)

if __name__ == "__main__":
    sys.exit(main())
