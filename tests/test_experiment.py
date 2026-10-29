#!/usr/bin/env python3
"""Tests the improvement log (scripts/experiment.py) and the CI agent's holdout guard (scripts/hooks/holdout_guard.py).

Kør:  python3 tests/test_experiment.py
"""
import json
import pathlib
import subprocess
import sys
import tempfile

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "scripts" / "hooks"))
import experiment  # noqa: E402
import holdout_guard  # noqa: E402

FAILURES = []


def expect(name, ok, detail=""):
    print(("OK   " if ok else "FEJL ") + name + ("" if ok else f"  {detail}"))
    if not ok:
        FAILURES.append(name)


def group(n, ok, cost=None, ids=None):
    ids = ids or [f"X-{i:03d}" for i in range(n)]
    cost = n * 0.07 if cost is None else cost
    return {"plugin": {"n": n, "bestaaet": ok, "opgaver_hash": experiment.id_hash(ids), "pris_usd": cost}}


def measurement(groups):
    return {"rev": "abc", "dato": "2026-10-18", "filer": [], "grupper": groups}


def test_assess():
    def run(before, after, category="videnbase"):
        return experiment.assess(category, {"el": {"foer": measurement(before), "efter": measurement(after)}})[0]

    base = {"udvikling/opgaver-a": group(30, 24), "holdout/opgaver-a": group(15, 12)}
    expect("bedre ud over støj → behold",
           run(base, {"udvikling/opgaver-a": group(30, 28), "holdout/opgaver-a": group(15, 12)}) == "behold")
    expect("inden for støj → uafklaret",
           run(base, {"udvikling/opgaver-a": group(30, 25), "holdout/opgaver-a": group(15, 12)}) == "uafklaret")
    expect("holdout falder 2 → forkast",
           run(base, {"udvikling/opgaver-a": group(30, 29), "holdout/opgaver-a": group(15, 10)}) == "forkast")
    expect("uden holdout → uafklaret",
           run({"udvikling/opgaver-a": group(30, 24)}, {"udvikling/opgaver-a": group(30, 29)}) == "uafklaret")
    expect("ikke samme opgaver → uafklaret",
           run(base, {"udvikling/opgaver-a": group(29, 28), "holdout/opgaver-a": group(15, 12)}) == "uafklaret")
    expect("samme kvalitet, meget billigere → behold",
           run(base, {"udvikling/opgaver-a": group(30, 24, cost=1.5), "holdout/opgaver-a": group(15, 12, cost=0.7)})
           == "behold")
    expect("ingen gevinst, dyrere → forkast",
           run(base, {"udvikling/opgaver-a": group(30, 24, cost=3.0), "holdout/opgaver-a": group(15, 12, cost=1.5)})
           == "forkast")
    expect("rettemaske afgøres manuelt", run(base, base, "rettemaske") == "manuel")


def test_summarize():
    with tempfile.TemporaryDirectory() as tmp:
        tmp = pathlib.Path(tmp)
        _, tasks = experiment.exam.load_trade("el")
        dev = [t for t in tasks if t["saet"] == "udvikling"][:3]
        held = [t for t in tasks if t["saet"] == "holdout"][:2]

        def row(t, arm, ok, note=""):
            return {"id": t["id"], "arm": arm, "saet": t["saet"], "type": t["type"], "niveau": t["niveau"],
                    "maal": t["maal"], "bestaaet": ok, "pris_usd": 0.1, "sek": 10.0, "note": note}
        old = tmp / "20261001-000000-plugin.json"
        new = tmp / "20261002-000000-plugin.json"
        old.write_text(json.dumps({"fag": "el", "plugin_rev": "aaa", "resultater":
                                   [row(t, "plugin", False) for t in dev + held]}))
        new.write_text(json.dumps({"fag": "el", "plugin_rev": "bbb", "resultater":
                                   [row(dev[0], "plugin", True), row(dev[0], "plugin", True),
                                    row(dev[1], "plugin", True, "kørselsfejl: grænse")]}))
        s = experiment.summarize([old, new])["el"]
        g = s["grupper"]
        dev_group = next(k for k in g if k.startswith("udvikling/"))
        expect("nyeste fil vinder pr. opgave", g[dev_group]["plugin"]["bestaaet"] == 1, g)
        expect("kørselsfejl tæller ikke", dev[1]["id"] in g[dev_group]["plugin"]["fejlede"])
        expect("holdout gemmer ingen ID'er",
               all("fejlede" not in a for k, arms in g.items() if k.startswith("holdout/") for a in arms.values()))
        expect("rev fra plugin-filerne", s["rev"] == "aaa,bbb", s["rev"])
        expect("gentagelser gør ikke opgaven dyrere", abs(g[dev_group]["plugin"]["pris_usd"] - 0.3) < 1e-9,
               g[dev_group]["plugin"]["pris_usd"])


def test_validate():
    holdout = experiment.holdout_ids()
    some = sorted(holdout)[0]
    log = {"forsoeg": [{"id": "F-001", "dato": "2026-10-18", "fag": ["el"], "kategori": "videnbase",
                        "hypotese": f"lukke {some}", "status": "afsluttet", "beslutning": "behold", "laering": "x"}]}
    expect("holdout-ID i loggen afvises", any("holdout" in e for e in experiment.validate(log, {"fag": {}}, holdout)))
    log["forsoeg"][0]["hypotese"] = "lukke huller"
    expect("gyldig log", experiment.validate(log, {"fag": {}}, holdout) == [])
    log["forsoeg"][0]["laering"] = ""
    expect("afsluttet kræver læring", experiment.validate(log, {"fag": {}}, holdout) != [])
    errors = experiment.validate(experiment.load_log(), experiment.load_benchmark(), holdout)
    expect("repoets forsøgslog og benchmark er gyldige", errors == [], errors)


def test_guard():
    root = str(ROOT)
    deny = lambda tool, inp: holdout_guard.check(tool, inp, root) is not None  # noqa: E731
    expect("Read af opgavefil afvises", deny("Read", {"file_path": f"{root}/eksamen/el/opgaver-a.json"}))
    expect("Read af resultatfil afvises", deny("Read", {"file_path": f"{root}/eksamen/vvs/results/x.json"}))
    expect("Edit af opgavefil afvises", deny("Edit", {"file_path": f"{root}/eksamen/el/opgaver-c.json"}))
    expect("Read af forsøgslog tilladt", not deny("Read", {"file_path": f"{root}/eksamen/forsoeg.json"}))
    expect("Read af læringsmål tilladt", not deny("Read", {"file_path": f"{root}/eksamen/el/laeringsmaal.json"}))
    expect("Read af videnbase tilladt", not deny("Read", {"file_path": f"{root}/plugins/byg-el/agents/x.md"}))
    expect("Grep med indhold i hele repoet afvises", deny("Grep", {"pattern": "x", "output_mode": "content"}))
    expect("Grep med filnavne tilladt", not deny("Grep", {"pattern": "x"}))
    expect("Grep i plugins tilladt", not deny("Grep", {"pattern": "x", "path": "plugins", "output_mode": "content"}))
    expect("Grep i eksamen med md-glob tilladt",
           not deny("Grep", {"pattern": "x", "path": "eksamen", "output_mode": "content", "glob": "*.md"}))
    expect("vis uden --saet udvikling afvises", deny("Bash", {"command": "python3 scripts/exam.py vis el --facit"}))
    expect("vis --saet udvikling tilladt",
           not deny("Bash", {"command": "python3 scripts/exam.py vis el --saet udvikling --facit"}))
    expect("koer tilladt", not deny("Bash", {"command": "python3 scripts/exam.py koer el --kun-fejlede"}))
    expect("experiment.py tilladt", not deny("Bash", {"command": "python3 scripts/experiment.py status"}))
    expect("script kædet med anden kommando afvises",
           deny("Bash", {"command": "python3 scripts/experiment.py status; cat eksamen/el/opgaver-a.json"}))
    expect("cat af opgavefil afvises", deny("Bash", {"command": "cat eksamen/el/opgaver-b.json"}))
    expect("git show af opgavefil afvises", deny("Bash", {"command": "git show HEAD:eksamen/vvs/opgaver-a.json"}))
    expect("rekursiv grep i roden afvises", deny("Bash", {"command": "grep -rn BEK ."}))
    expect("rekursiv grep i plugins tilladt", not deny("Bash", {"command": "grep -rn BEK plugins/byg-el"}))
    expect("rg med eksamen udeladt tilladt", not deny("Bash", {"command": "rg BEK --glob '!eksamen'"}))
    expect("git status tilladt", not deny("Bash", {"command": "git status"}))


def test_answers_hide_holdout():
    held = sorted(t for t in experiment.holdout_ids() if t.startswith("EL-"))[0]
    r = subprocess.run([sys.executable, str(ROOT / "scripts" / "exam.py"), "svar", "el", "--id", held],
                       capture_output=True, text=True)
    expect("exam.py svar viser aldrig holdout", r.returncode == 1 and "Holdout" in r.stdout, r.stdout[:200])


def main() -> int:
    for t in (test_assess, test_summarize, test_validate, test_guard, test_answers_hide_holdout):
        t()
    print(f"\n{len(FAILURES)} fejl")
    return 1 if FAILURES else 0


if __name__ == "__main__":
    sys.exit(main())
