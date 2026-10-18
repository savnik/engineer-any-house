#!/usr/bin/env python3
"""Tests the exam layer (scripts/exam.py): answer parsing, grading and coverage validation.

Kør:  python3 tests/test_exam.py
"""
import json
import pathlib
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
    expect("svar-linje findes", exam.extract_answer("bla\n**SVAR: B**") == "B")
    expect("sidste svar-linje vinder", exam.extract_answer("SVAR: A\n...\nSVAR: C") == "C")
    expect("ingen svar-linje", exam.extract_answer("Jeg mener B") is None)
    for raw, want in [("30 mA", 30), ("2,5 mm²", 2.5), ("1.500 W", 1500), ("1,234.5", 1234.5),
                      ("1.234,5 kWh", 1234.5), ("0.4 s", 0.4), ("−3,2 %", -3.2), ("12 345 l", 12345)]:
        got = exam.parse_number(raw)
        expect(f"tal '{raw}'", got == want, f"fik {got}")


def test_grading():
    choice = {"type": "valg", "facit": "B", "valgmuligheder": {"A": "a", "B": "b", "C": "c"}}
    expect("valg rigtigt", exam.grade_choice(choice, "SVAR: B) 30 mA")[0])
    expect("valg forkert", not exam.grade_choice(choice, "SVAR: A")[0])
    number = {"type": "tal", "facit": {"vaerdi": 10.0, "enhed": "A", "tolerance_pct": 5}}
    expect("tal inden for tolerance", exam.grade_number(number, "SVAR: 10,4 A")[0])
    expect("tal uden for tolerance", not exam.grade_number(number, "SVAR: 10,6 A")[0])
    exact = {"type": "tal", "facit": {"vaerdi": 30, "enhed": "mA"}}
    expect("tal eksakt", exam.grade_number(exact, "SVAR: 30 mA")[0])
    expect("dom bestået", exam.grade_verdict("K1: ja\nDOM: BESTÅET")[0])
    expect("dom ikke bestået", not exam.grade_verdict("K1: nej\nDOM: IKKE BESTÅET")[0])
    expect("ingen dom", not exam.grade_verdict("K1: ja")[0])


def write_fixture(base: pathlib.Path, tasks: list[dict]):
    d = base / "el"
    d.mkdir(parents=True)
    goals = {
        "fag": "el", "plugin": "byg-el", "agent": "el-installatoer",
        "kilder": [{"id": "K1", "titel": "Kilde", "url": "https://example.org", "laest": "2026-10-17"}],
        "maal": [
            {"id": "M1", "kilde": "K1 pkt. 1", "tekst": "Mål 1", "rolle": "i"},
            {"id": "M2", "kilde": "K1 pkt. 2", "tekst": "Mål 2", "rolle": "uden", "begrundelse": "industri"},
        ],
    }
    (d / "laeringsmaal.json").write_text(json.dumps(goals), encoding="utf-8")
    (d / "opgaver.json").write_text(json.dumps({"opgaver": tasks}), encoding="utf-8")


def task(tid, saet, **kw):
    t = {"id": tid, "maal": ["M1"], "saet": saet, "type": "valg", "niveau": "svend", "spoergsmaal": "?",
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
        f.write_text(json.dumps({"fag": "el", "resultater": rows}), encoding="utf-8")
        text = exam.report([f])
    expect("kørselsfejl tæller ikke som regression", "## Regressioner" in text and "- X-1" not in text.split("## Regressioner")[1])
    expect("kørselsfejl vises", "1 kørselsfejl er ikke talt med" in text)
    expect("grænsebesked genkendes", bool(exam.LIMIT_RE.search("You've hit your session limit · resets 2:40am")))


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
            errors, _ = exam.validate("el")
            expect("gyldigt sæt", not errors, str(errors))
        with tempfile.TemporaryDirectory() as tmp:
            exam.EXAM_DIR = pathlib.Path(tmp)
            write_fixture(exam.EXAM_DIR, [task("E1", "udvikling")])
            errors, _ = exam.validate("el")
            expect("mål uden holdout afvises", any("holdout" in e for e in errors), str(errors))
        with tempfile.TemporaryDirectory() as tmp:
            exam.EXAM_DIR = pathlib.Path(tmp)
            write_fixture(exam.EXAM_DIR, [task("E1", "udvikling", facit="D"), task("E2", "holdout", maal=["M9"]),
                                          task("E3", "holdout", type="tal", facit=5)])
            errors, _ = exam.validate("el")
            expect("facit uden for valgmuligheder", any("facit 'D'" in e for e in errors), str(errors))
            expect("ukendt mål", any("M9" in e for e in errors), str(errors))
            expect("tal uden facit-objekt", any("tal kræver" in e for e in errors), str(errors))
    finally:
        exam.EXAM_DIR = original


def test_plugin_copy_without_memory():
    with tempfile.TemporaryDirectory() as tmp:
        dst = exam.prepare_plugin("byg-el", pathlib.Path(tmp))
        agent = (dst / "agents" / "el-installatoer.md").read_text(encoding="utf-8")
        head = agent[:agent.find("\n---", 4)]
        expect("plugin-kopi uden memory", "memory:" not in head)
        expect("plugin-kopi beholder resten af frontmatter", "name: el-installatoer" in head and "model:" in head)
        manifest = json.loads((dst / ".claude-plugin" / "plugin.json").read_text(encoding="utf-8"))
        expect("plugin-kopi uden afhængigheder", "dependencies" not in manifest)
        expect("plugin-kopi uden evals", not (dst / "evals").exists())
    with tempfile.TemporaryDirectory() as tmp:
        dst = exam.prepare_plugin("byg-el", pathlib.Path(tmp), keep_memory=True)
        expect("--med-hukommelse beholder memory",
               "memory: user" in (dst / "agents" / "el-installatoer.md").read_text(encoding="utf-8"))
    original = (ROOT / "plugins" / "byg-el" / "agents" / "el-installatoer.md").read_text(encoding="utf-8")
    expect("originalen er urørt", "memory: user" in original)


def test_real_sets():
    for trade in exam.all_trades():
        errors, _ = exam.validate(trade)
        expect(f"eksamenssæt {trade} er gyldigt", not errors, "; ".join(errors[:5]))


if __name__ == "__main__":
    test_parsing()
    test_grading()
    test_report_skips_run_errors()
    test_shuffle()
    test_validation()
    test_plugin_copy_without_memory()
    test_real_sets()
    print(f"\n{len(FAILURES)} fejl")
    sys.exit(1 if FAILURES else 0)
