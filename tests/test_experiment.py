#!/usr/bin/env python3
"""Tests the improvement log (scripts/experiment.py) and the CI agent's holdout guard (scripts/hooks/holdout_guard.py).

Run:  python3 tests/test_experiment.py
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
        return experiment.assess(category, {"electrical": {"foer": measurement(before), "efter": measurement(after)}})[0]

    base = {"udvikling/tasks-a": group(30, 24), "holdout/tasks-d": group(15, 12)}
    expect("bedre ud over støj → behold",
           run(base, {"udvikling/tasks-a": group(30, 28), "holdout/tasks-d": group(15, 12)}) == "behold")
    expect("inden for støj → uafklaret",
           run(base, {"udvikling/tasks-a": group(30, 25), "holdout/tasks-d": group(15, 12)}) == "uafklaret")
    expect("holdout falder 2 → forkast",
           run(base, {"udvikling/tasks-a": group(30, 29), "holdout/tasks-d": group(15, 10)}) == "forkast")
    expect("uden holdout → uafklaret",
           run({"udvikling/tasks-a": group(30, 24)}, {"udvikling/tasks-a": group(30, 29)}) == "uafklaret")
    expect("ikke samme opgaver → uafklaret",
           run(base, {"udvikling/tasks-a": group(29, 28), "holdout/tasks-d": group(15, 12)}) == "uafklaret")
    expect("samme kvalitet, meget billigere → behold",
           run(base, {"udvikling/tasks-a": group(30, 24, cost=1.5), "holdout/tasks-d": group(15, 12, cost=0.7)})
           == "behold")
    expect("ingen gevinst, dyrere → forkast",
           run(base, {"udvikling/tasks-a": group(30, 24, cost=3.0), "holdout/tasks-d": group(15, 12, cost=1.5)})
           == "forkast")
    expect("rettemaske afgøres manuelt", run(base, base, "rettemaske") == "manuel")


def test_summarize():
    with tempfile.TemporaryDirectory() as tmp:
        tmp = pathlib.Path(tmp)
        _, tasks = experiment.exam.load_trade("electrical")
        dev = [t for t in tasks if t["saet"] == "udvikling"][:3]
        held = [t for t in tasks if t["saet"] == "holdout"][:2]

        def row(t, arm, ok, note=""):
            return {"id": t["id"], "arm": arm, "saet": t["saet"], "type": t["type"], "niveau": t["niveau"],
                    "maal": t["maal"], "bestaaet": ok, "pris_usd": 0.1, "sek": 10.0, "note": note}
        old = tmp / "20261001-000000-plugin.json"
        new = tmp / "20261002-000000-plugin.json"
        old.write_text(json.dumps({"fag": "electrical", "plugin_rev": "aaa", "resultater":
                                   [row(t, "plugin", False) for t in dev + held]}))
        new.write_text(json.dumps({"fag": "electrical", "plugin_rev": "bbb", "resultater":
                                   [{**row(dev[0], "plugin", True), "afviste_kald": 1},
                                    {**row(dev[0], "plugin", True), "afviste_kald": 0},
                                    row(dev[1], "plugin", True, "kørselsfejl: grænse")]}))
        s = experiment.summarize([old, new])["electrical"]
        g = s["grupper"]
        dev_group = next(k for k in g if k.startswith("udvikling/"))
        expect("nyeste fil vinder pr. opgave", g[dev_group]["plugin"]["bestaaet"] == 1, g)
        expect("kørselsfejl tæller ikke", dev[1]["id"] in g[dev_group]["plugin"]["fejlede"])
        expect("holdout gemmer ingen ID'er",
               all("fejlede" not in a for k, arms in g.items() if k.startswith("holdout/") for a in arms.values()))
        expect("rev fra plugin-filerne", s["rev"] == "aaa,bbb", s["rev"])
        expect("gentagelser gør ikke opgaven dyrere", abs(g[dev_group]["plugin"]["pris_usd"] - 0.3) < 1e-9,
               g[dev_group]["plugin"]["pris_usd"])
        expect("afviste kald kun fra rækker, der tæller dem",
               g[dev_group]["plugin"].get("afviste_kald_pr_opgave") == 0.5, g[dev_group]["plugin"])


def test_validate():
    holdout = experiment.holdout_ids()
    some = sorted(holdout)[0]
    log = {"forsoeg": [{"id": "F-001", "dato": "2026-10-18", "fag": ["electrical"], "kategori": "videnbase",
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
    expect("Read af opgavefil afvises", deny("Read", {"file_path": f"{root}/exam/electrical/tasks-a.json"}))
    expect("Read af resultatfil afvises", deny("Read", {"file_path": f"{root}/exam/plumbing/results/x.json"}))
    expect("Edit af opgavefil afvises", deny("Edit", {"file_path": f"{root}/exam/electrical/tasks-c.json"}))
    expect("Read af forsøgslog tilladt", not deny("Read", {"file_path": f"{root}/exam/experiments.json"}))
    expect("Read af læringsmål tilladt", not deny("Read", {"file_path": f"{root}/exam/electrical/learning-goals.json"}))
    expect("Read af videnbase tilladt", not deny("Read", {"file_path": f"{root}/plugins/byg-electrical/agents/x.md"}))
    expect("Grep med indhold i hele repoet afvises", deny("Grep", {"pattern": "x", "output_mode": "content"}))
    expect("Grep med filnavne tilladt", not deny("Grep", {"pattern": "x"}))
    expect("Grep i plugins tilladt", not deny("Grep", {"pattern": "x", "path": "plugins", "output_mode": "content"}))
    expect("Grep i exam med md-glob tilladt",
           not deny("Grep", {"pattern": "x", "path": "exam", "output_mode": "content", "glob": "*.md"}))
    expect("show uden --set development afvises",
           deny("Bash", {"command": "python3 scripts/exam.py show electrical --answer-key"}))
    expect("show --set holdout afvises",
           deny("Bash", {"command": "python3 scripts/exam.py show electrical --set holdout --answer-key"}))
    expect("show --set development tilladt",
           not deny("Bash", {"command": "python3 scripts/exam.py show electrical --set development --answer-key"}))
    expect("show --set=development tilladt",
           not deny("Bash", {"command": "python3 scripts/exam.py show electrical --set=development"}))
    expect("run tilladt", not deny("Bash", {"command": "python3 scripts/exam.py run electrical --only-failed"}))
    expect("experiment.py tilladt", not deny("Bash", {"command": "python3 scripts/experiment.py status"}))
    expect("script kædet med anden kommando afvises",
           deny("Bash", {"command": "python3 scripts/experiment.py status; cat exam/electrical/tasks-a.json"}))
    expect("cat af opgavefil afvises", deny("Bash", {"command": "cat exam/electrical/tasks-b.json"}))
    expect("git show af opgavefil afvises", deny("Bash", {"command": "git show HEAD:exam/plumbing/tasks-a.json"}))
    expect("rekursiv grep i roden afvises", deny("Bash", {"command": "grep -rn BEK ."}))
    expect("rekursiv grep i plugins tilladt", not deny("Bash", {"command": "grep -rn BEK plugins/byg-electrical"}))
    expect("rg med exam udeladt tilladt", not deny("Bash", {"command": "rg BEK --glob '!exam'"}))
    expect("git status tilladt", not deny("Bash", {"command": "git status"}))


def test_holdout_switch():
    """After a switch only the active holdout files count as holdout: for the budget, the rule and the benchmark."""
    original = experiment.exam.EXAM_DIR
    try:
        with tempfile.TemporaryDirectory() as tmp:
            experiment.exam.EXAM_DIR = pathlib.Path(tmp)
            d = experiment.exam.EXAM_DIR / "electrical"
            d.mkdir()
            goals = {"fag": "electrical", "maal": [], "holdout_filer": ["tasks-d.json"]}
            (d / "learning-goals.json").write_text(json.dumps(goals), encoding="utf-8")
            expect("aktiv holdout-fil tæller", experiment.is_holdout_group("electrical", "holdout/tasks-d"))
            expect("gammel holdout-fil tæller ikke", not experiment.is_holdout_group("electrical", "holdout/tasks-a"))
            expect("regression tæller ikke", not experiment.is_holdout_group("electrical", "regression/tasks-a"))
            old = measurement({"udvikling/tasks-a": group(30, 24), "holdout/tasks-a": group(15, 12)})
            log = {"forsoeg": [{"maalinger": {"electrical": {"foer": old, "efter": old}}}]}
            expect("budgettet tæller ikke gamle holdout-målinger", experiment.holdout_uses(log, "electrical") == 0)
            log["forsoeg"][0]["maalinger"]["electrical"]["efter"] = measurement({"holdout/tasks-d": group(6, 5)})
            expect("budgettet tæller nye holdout-målinger", experiment.holdout_uses(log, "electrical") == 1)
            verdict, notes = experiment.assess("videnbase", {"electrical": {
                "foer": old, "efter": measurement({"udvikling/tasks-a": group(30, 28), "holdout/tasks-a": group(15, 12)})}})
            expect("gammel holdout opfylder ikke holdout-kravet", verdict == "uafklaret" and "holdout" in notes[-1], notes)
            bench = {"fag": {"electrical": {"grupper": {"holdout/tasks-a": group(15, 12), "holdout/tasks-d": group(6, 5),
                                                        "udvikling/tasks-a": group(30, 24)},
                                            "kilder": {"holdout/tasks-a": "F-007 @ x"}}}}
            moved = experiment.retire_holdout(bench, "electrical")
            b = bench["fag"]["electrical"]
            expect("benchmark: gammel holdout bliver regression", moved == ["holdout/tasks-a → regression/tasks-a"]
                   and "regression/tasks-a" in b["grupper"] and "holdout/tasks-d" in b["grupper"]
                   and b["kilder"] == {"regression/tasks-a": "F-007 @ x"}, str(b))
    finally:
        experiment.exam.EXAM_DIR = original
        experiment._ACTIVE_HOLDOUT.clear()
        experiment.exam._SETS_CACHE.clear()


def test_answers_hide_holdout():
    held = sorted(t for t in experiment.holdout_ids() if t.startswith("EL-"))[0]
    r = subprocess.run([sys.executable, str(ROOT / "scripts" / "exam.py"), "answers", "electrical", "--id", held],
                       capture_output=True, text=True)
    expect("exam.py answers viser aldrig holdout", r.returncode == 1 and "Holdout" in r.stdout, r.stdout[:200])


def main() -> int:
    for t in (test_assess, test_summarize, test_validate, test_guard, test_holdout_switch, test_answers_hide_holdout):
        t()
    print(f"\n{len(FAILURES)} fejl")
    return 1 if FAILURES else 0


if __name__ == "__main__":
    sys.exit(main())
