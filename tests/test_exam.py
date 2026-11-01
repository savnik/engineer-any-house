#!/usr/bin/env python3
"""Tests the exam layer (scripts/exam.py): answer parsing, grading and coverage validation.

Run:  python3 tests/test_exam.py
"""
import json
import pathlib
import subprocess
import sys
import tempfile

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import exam  # noqa: E402

FAILURES = []


def expect(name, ok, detail=""):
    print(("OK   " if ok else "FEJL ") + name + ("" if ok else f"  {detail}"))
    if not ok:
        FAILURES.append(name)


def test_parsing():
    expect("svar-linje findes", exam.extract_answer("bla\n**ANSWER: B**") == "B")
    expect("sidste svar-linje vinder", exam.extract_answer("ANSWER: A\n...\nANSWER: C") == "C")
    expect("ingen svar-linje", exam.extract_answer("Jeg mener B") is None)
    for raw, want in [("30 mA", 30), ("2,5 mm²", 2.5), ("1.500 W", 1500), ("1,234.5", 1234.5),
                      ("1.234,5 kWh", 1234.5), ("0.4 s", 0.4), ("−3,2 %", -3.2), ("12 345 l", 12345)]:
        got = exam.parse_number(raw)
        expect(f"tal '{raw}'", got == want, f"fik {got}")


def test_grading():
    choice = {"type": "valg", "facit": "B", "valgmuligheder": {"A": "a", "B": "b", "C": "c"}}
    expect("valg rigtigt", exam.grade_choice(choice, "ANSWER: B) 30 mA")[0])
    expect("valg forkert", not exam.grade_choice(choice, "ANSWER: A")[0])
    number = {"type": "tal", "facit": {"vaerdi": 10.0, "enhed": "A", "tolerance_pct": 5}}
    expect("tal inden for tolerance", exam.grade_number(number, "ANSWER: 10,4 A")[0])
    expect("tal uden for tolerance", not exam.grade_number(number, "ANSWER: 10,6 A")[0])
    exact = {"type": "tal", "facit": {"vaerdi": 30, "enhed": "mA"}}
    expect("tal eksakt", exam.grade_number(exact, "ANSWER: 30 mA")[0])
    expect("dom bestået", exam.grade_verdict("K1: ja\nVERDICT: BESTÅET")[0])
    expect("dom ikke bestået", not exam.grade_verdict("K1: nej\nVERDICT: IKKE BESTÅET")[0])
    expect("ingen dom", not exam.grade_verdict("K1: ja")[0])


def write_fixture(base: pathlib.Path, tasks: list[dict]):
    d = base / "electrical"
    d.mkdir(parents=True)
    goals = {
        "fag": "electrical", "plugin": "byg-electrical", "agent": "electrician",
        "kilder": [{"id": "K1", "titel": "Kilde", "url": "https://example.org", "laest": "2026-10-17"}],
        "maal": [
            {"id": "M1", "kilde": "K1 pkt. 1", "tekst": "Mål 1", "rolle": "i"},
            {"id": "M2", "kilde": "K1 pkt. 2", "tekst": "Mål 2", "rolle": "uden", "begrundelse": "industri"},
        ],
    }
    (d / "learning-goals.json").write_text(json.dumps(goals), encoding="utf-8")
    (d / "tasks.json").write_text(json.dumps({"opgaver": tasks}), encoding="utf-8")


def task(tid, set_id, **kw):
    t = {"id": tid, "maal": ["M1"], "saet": set_id, "type": "valg", "niveau": "svend", "spoergsmaal": "?",
         "valgmuligheder": {"A": "a", "B": "b", "C": "c"}, "facit": "A", "kilde": "K1", "status": "V 2026-10"}
    t.update(kw)
    return t


def test_report_skips_run_errors():
    rows = [
        {"id": "X-1", "arm": "basis", "type": "valg", "saet": "udvikling", "niveau": "svend", "maal": ["M1"], "bestaaet": True},
        {"id": "X-1", "arm": "plugin", "type": "valg", "saet": "udvikling", "niveau": "svend", "maal": ["M1"],
         "bestaaet": False, "fejl": True, "note": "kørselsfejl: You've hit your session limit"},
    ]
    with tempfile.TemporaryDirectory() as tmp:
        f = pathlib.Path(tmp) / "r.json"
        f.write_text(json.dumps({"fag": "electrical", "resultater": rows}), encoding="utf-8")
        text = exam.report([f])
    expect("kørselsfejl tæller ikke som regression", "## Regressioner" in text and "- X-1" not in text.split("## Regressioner")[1])
    expect("kørselsfejl vises", "1 kørselsfejl er ikke talt med" in text)
    expect("grænsebesked genkendes", bool(exam.LIMIT_RE.search("You've hit your session limit · resets 2:40am")))


def test_efficiency_helpers():
    original = exam.EXAM_DIR
    row = {"type": "valg", "saet": "udvikling", "niveau": "svend", "maal": ["M1"], "pris_usd": 0.1, "ture": 2}
    try:
        with tempfile.TemporaryDirectory() as tmp:
            exam.EXAM_DIR = pathlib.Path(tmp)
            res = exam.EXAM_DIR / "electrical" / "results"
            res.mkdir(parents=True)
            (res / "ugyldig").mkdir()

            def write(name, rows, folder=res):
                (folder / name).write_text(json.dumps({"fag": "electrical", "resultater": rows}), encoding="utf-8")
            write("1-basis.json", [{**row, "id": "X-1", "arm": "basis", "bestaaet": False}])
            write("2-basis.json", [{**row, "id": "X-1", "arm": "basis", "bestaaet": True},
                                   {**row, "id": "X-2", "arm": "basis", "bestaaet": True, "fejl": True}])
            write("3-plugin.json", [{**row, "id": "X-1", "arm": "plugin", "bestaaet": False, "sek": 12.0,
                                     "tokens_ud": 300},
                                    {**row, "id": "X-3", "arm": "plugin", "bestaaet": True, "sek": 8.0,
                                     "tokens_ud": 100}])
            write("9-ugyldig.json", [{**row, "id": "X-3", "arm": "plugin", "bestaaet": False}], res / "ugyldig")
            basis, sources = exam.latest_basis("electrical", {"X-1", "X-2"})
            expect("nyeste basis genbruges", len(basis) == 1 and basis[0]["bestaaet"] and sources == {"2-basis.json"})
            expect("basis med kørselsfejl genbruges ikke", all(r["id"] != "X-2" for r in basis))
            expect("kun-fejlede finder sidste plugin-fejl", exam.latest_failed_plugin("electrical") == {"X-1"})
            text = exam.report([res / "3-plugin.json"], basis, sources)
            expect("rapport med genbrugt basis viser regression", "## Regressioner" in text and "- X-1" in text)
            expect("rapport viser tid pr. opgave", "| Tid pr. opgave (s) |" in text and "10.0" in text)
            expect("rapport viser output-tokens pr. opgave", "| Output-tokens pr. opgave |" in text and "| 200 |" in text)
            expect("rapport nævner genbrugt basis", "Basis er genbrugt fra: 2-basis.json" in text)
    finally:
        exam.EXAM_DIR = original
    with tempfile.TemporaryDirectory() as tmp:
        dst = exam.prepare_plugin("byg-electrical", pathlib.Path(tmp))
        expect("videnbasens størrelse måles", exam.knowledge_base_bytes(dst) > 10_000)
    r = subprocess.run([sys.executable, str(ROOT / "scripts" / "exam.py"), "run", "electrical", "--set", "holdout"],
                       capture_output=True, text=True)
    expect("holdout kræver --release", r.returncode == 1 and "--release" in r.stdout)


def test_holdout_gaps_are_not_listed():
    rows = [{"id": "H-1", "arm": "plugin", "type": "valg", "saet": "holdout", "niveau": "svend", "maal": ["M1"],
             "bestaaet": False}]
    with tempfile.TemporaryDirectory() as tmp:
        f = pathlib.Path(tmp) / "r.json"
        f.write_text(json.dumps({"fag": "electrical", "resultater": rows}), encoding="utf-8")
        text = exam.report([f])
    expect("holdout-fejl listes ikke som huller", "- H-1" not in text and "1 holdout-opgaver er ikke bestået" in text)
    rows.append({**rows[0], "arm": "basis", "bestaaet": True})
    with tempfile.TemporaryDirectory() as tmp:
        f = pathlib.Path(tmp) / "r.json"
        f.write_text(json.dumps({"fag": "electrical", "resultater": rows}), encoding="utf-8")
        text = exam.report([f])
    expect("holdout-regression vises kun som antal", "H-1" not in text and "- og 1 i holdout" in text, text)


def case_task(**kw):
    t = {"id": "C-1", "maal": ["M1"], "saet": "udvikling", "type": "case", "niveau": "mester",
         "spoergsmaal": "Et parcelhus skal have ny tavle.", "kilde": "K1", "status": "V 2026-10-18",
         "dele": [{"del": "a", "type": "tal", "spoergsmaal": "Strøm?", "facit": {"vaerdi": 16, "enhed": "A"}},
                  {"del": "b", "type": "valg", "spoergsmaal": "Type?", "facit": "B",
                   "valgmuligheder": {"A": "AC", "B": "A", "C": "F", "D": "B"}},
                  {"del": "c", "type": "tal", "spoergsmaal": "Fald?", "facit": {"vaerdi": 2.0, "enhed": "%",
                                                                               "tolerance_pct": 5}}]}
    t.update(kw)
    return t


def test_case():
    t = case_task()
    prompt = exam.build_prompt(t)
    options, key = exam.shuffled_options(t["dele"][1], "C-1/b")
    expect("case-prompt har delene", "Del a) Strøm?" in prompt and "Del c) Fald?" in prompt)
    expect("case-prompt har blandede valgmuligheder", f"{key}) A" in prompt)
    other = next(k for k in options if k != key)
    answer = f"Del a ...\nANSWER a: 16 A\nDel b\nANSWER b: {key}\nDel c\nANSWER c: 2,5 %\nANSWER: 16"
    g = exam.grade_case(t, answer, pathlib.Path("."), None)
    expect("case-dele rettes hver for sig", g["dele"] == {"a": True, "b": True, "c": False}, str(g))
    expect("case bestået ved 2/3 ≥ 60 %", g["bestaaet"] and abs(g["point"] - 0.667) < 0.01, str(g))
    g = exam.grade_case(t, f"ANSWER a: 10 A\nANSWER b: {other}\nANSWER c: 2 %", pathlib.Path("."), None)
    expect("case ikke bestået ved 1/3", not g["bestaaet"], str(g))
    leak = case_task(dele=[{"del": "a", "type": "tal", "spoergsmaal": "Ik?", "facit": {"vaerdi": 170, "enhed": "A"}},
                           {"del": "b", "type": "valg", "spoergsmaal": "Er 170 A nok?", "facit": "A",
                            "valgmuligheder": {"A": "ja", "B": "nej", "C": "måske"}}])
    expect("case-lækage af tal opdages", any("170" in w for w in exam.case_leaks(leak)), str(exam.case_leaks(leak)))
    expect("ingen falsk lækage", exam.case_leaks(case_task()) == [], str(exam.case_leaks(case_task())))
    expect("ANSWER uden del ignorerer deludsvar", exam.extract_answer("ANSWER a: 3\nANSWER: 7") == "7")
    original = exam.EXAM_DIR
    try:
        with tempfile.TemporaryDirectory() as tmp:
            exam.EXAM_DIR = pathlib.Path(tmp)
            write_fixture(exam.EXAM_DIR, [case_task(), case_task(id="C-2", saet="holdout")])
            errors, _ = exam.validate("electrical")
            expect("gyldig case", not errors, str(errors))
        with tempfile.TemporaryDirectory() as tmp:
            exam.EXAM_DIR = pathlib.Path(tmp)
            bad = case_task(dele=[{"del": "a", "type": "valg", "spoergsmaal": "?", "facit": "Z",
                                   "valgmuligheder": {"A": "1", "B": "2", "C": "3"}}])
            write_fixture(exam.EXAM_DIR, [bad, case_task(id="C-2", saet="holdout")])
            errors, _ = exam.validate("electrical")
            expect("case med én del afvises", any("mindst 2 dele" in e for e in errors), str(errors))
            expect("case-del med forkert facit afvises", any("C-1/a" in e and "facit" in e for e in errors), str(errors))
    finally:
        exam.EXAM_DIR = original


def test_regrade_deterministic():
    """--only-deterministic grades choice/number parts again and reuses stored free-part verdicts (F-024)."""
    t = case_task(dele=[{"del": "a", "type": "tal", "spoergsmaal": "Udnyttelse?",
                         "facit": {"vaerdi": 0.87, "enhed": "-", "tolerance_pct": 2}},
                        {"del": "b", "type": "fri", "spoergsmaal": "Hvorfor?", "kriterier": ["Begrunder"]}])
    stored = {"svar": "ANSWER a: 0,87\nANSWER b: fordi", "bestaaet": False, "dele": {"a": False, "b": True}}
    expect("case med gemte fri-dele kan genbedømmes", exam.deterministic_regradable(t, stored))
    expect("case uden gemte fri-dele springes over", not exam.deterministic_regradable(t, {"svar": "x"}))
    expect("fri-opgave springes over", not exam.deterministic_regradable({"type": "fri"}, stored))
    expect("tal-opgave genbedømmes", exam.deterministic_regradable({"type": "tal"}, {}))
    original = exam.run_claude

    def no_examiner(*_a, **_k):
        raise AssertionError("censoren må ikke kaldes")

    try:
        exam.run_claude = no_examiner
        args = type("Args", (), {"only_deterministic": True, "grader": "sonnet", "timeout": 1})()
        g = exam.regrade_one(t, stored, pathlib.Path("."), args)
    finally:
        exam.run_claude = original
    expect("tal-del rettes igen, fri-del genbruges", g["dele"] == {"a": True, "b": True}, str(g))
    expect("genbedømt case bestået uden censorpris", g["bestaaet"] and g["pris_bedoemmelse"] == 0, str(g))
    legacy = {"fag": "statik", "resultater": [{"svar": "Regning\n**SVAR a:** 3 kN\nSVAR: 7", "id": "C-1"}]}
    exam.migrate_legacy(legacy, "structural")
    expect("gammel fil flyttes til nyt fagnavn", legacy["fag"] == "structural")
    expect("SVAR-linjer bliver til ANSWER", exam.extract_answer(legacy["resultater"][0]["svar"]) == "7"
           and exam.extract_answer(legacy["resultater"][0]["svar"], "a") == "3 kN", legacy)


def test_shuffle():
    t = {"id": "X-1", "type": "valg", "facit": "B", "valgmuligheder": {"A": "a", "B": "b", "C": "c", "D": "d"}}
    options, key = exam.shuffled_options(t)
    expect("blandet facit peger på samme tekst", options[key] == "b")
    expect("blanding er stabil", exam.shuffled_options(t) == (options, key))
    expect("blandede bogstaver er A-D", sorted(options) == ["A", "B", "C", "D"])
    keys = {exam.shuffled_options({**t, "id": f"X-{i}"})[1] for i in range(40)}
    expect("blanding flytter facit rundt", len(keys) >= 3, str(keys))
    expect("prompten bruger den blandede rækkefølge", f"{key}) b" in exam.build_prompt({**t, "spoergsmaal": "?"}))


def test_validation():
    original = exam.EXAM_DIR
    try:
        with tempfile.TemporaryDirectory() as tmp:
            exam.EXAM_DIR = pathlib.Path(tmp)
            write_fixture(exam.EXAM_DIR, [task("E1", "udvikling"), task("E2", "holdout")])
            errors, _ = exam.validate("electrical")
            expect("gyldigt sæt", not errors, str(errors))
        with tempfile.TemporaryDirectory() as tmp:
            exam.EXAM_DIR = pathlib.Path(tmp)
            write_fixture(exam.EXAM_DIR, [task("E1", "udvikling")])
            errors, _ = exam.validate("electrical")
            expect("mål uden holdout afvises", any("holdout" in e for e in errors), str(errors))
        with tempfile.TemporaryDirectory() as tmp:
            exam.EXAM_DIR = pathlib.Path(tmp)
            write_fixture(exam.EXAM_DIR, [task("E1", "udvikling", facit="D"), task("E2", "holdout", maal=["M9"]),
                                          task("E3", "holdout", type="tal", facit=5)])
            errors, _ = exam.validate("electrical")
            expect("facit uden for valgmuligheder", any("facit 'D'" in e for e in errors), str(errors))
            expect("ukendt mål", any("M9" in e for e in errors), str(errors))
            expect("tal uden facit-objekt", any("tal kræver" in e for e in errors), str(errors))
    finally:
        exam.EXAM_DIR = original


def test_plugin_copy_without_memory():
    with tempfile.TemporaryDirectory() as tmp:
        dst = exam.prepare_plugin("byg-electrical", pathlib.Path(tmp))
        agent = (dst / "agents" / "electrician.md").read_text(encoding="utf-8")
        head = agent[:agent.find("\n---", 4)]
        expect("plugin-kopi uden memory", "memory:" not in head)
        expect("plugin-kopi beholder resten af frontmatter", "name: electrician" in head and "model:" in head)
        manifest = json.loads((dst / ".claude-plugin" / "plugin.json").read_text(encoding="utf-8"))
        expect("plugin-kopi uden afhængigheder", "dependencies" not in manifest)
        expect("plugin-kopi uden evals", not (dst / "evals").exists())
    with tempfile.TemporaryDirectory() as tmp:
        dst = exam.prepare_plugin("byg-electrical", pathlib.Path(tmp), keep_memory=True)
        expect("--med-hukommelse beholder memory",
               "memory: user" in (dst / "agents" / "electrician.md").read_text(encoding="utf-8"))
    original = (ROOT / "plugins" / "byg-electrical" / "agents" / "electrician.md").read_text(encoding="utf-8")
    expect("originalen er urørt", "memory: user" in original)


def test_plugin_arm_can_read_its_plugin():
    class Args:
        web = False
        max_turns = 12
        model = ""
    extra = exam.arm_args("plugin", Args, pathlib.Path("/tmp/x/byg-electrical"), "byg-electrical:electrician")
    expect("plugin-armen får læseadgang til plugin-kopien (--add-dir)",
           extra[extra.index("--add-dir") + 1] == "/tmp/x/byg-electrical" if "--add-dir" in extra else False)
    expect("basis-armen har ingen plugin", "--plugin-dir" not in exam.arm_args("basis", Args, None, ""))
    with tempfile.TemporaryDirectory() as tmp:
        dst = exam.prepare_plugin("byg-electrical", pathlib.Path(tmp), rev="HEAD")
        expect("plugin fra git-revision", (dst / "agents" / "electrician.md").is_file())


def test_real_sets():
    for trade in exam.all_trades():
        errors, _ = exam.validate(trade)
        expect(f"eksamenssæt {trade} er gyldigt", not errors, "; ".join(errors[:5]))


if __name__ == "__main__":
    test_parsing()
    test_grading()
    test_report_skips_run_errors()
    test_efficiency_helpers()
    test_holdout_gaps_are_not_listed()
    test_case()
    test_regrade_deterministic()
    test_shuffle()
    test_validation()
    test_plugin_copy_without_memory()
    test_plugin_arm_can_read_its_plugin()
    test_real_sets()
    print(f"\n{len(FAILURES)} fejl")
    sys.exit(1 if FAILURES else 0)
