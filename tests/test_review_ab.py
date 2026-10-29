#!/usr/bin/env python3
"""Tests the control arm (scripts/review_ab.py): verdict parsing, classification and summary. No tokens.

Run:  python3 tests/test_review_ab.py
"""
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import review_ab  # noqa: E402

FAILURES = []


def expect(name, ok, detail=""):
    print(("OK   " if ok else "FEJL ") + name + ("" if ok else f"  {detail}"))
    if not ok:
        FAILURES.append(name)


def row(rid, before, cat, after_ok, cost=0.07, kcost=0.05, rcost=0.0):
    r = {"id": rid, "foer": {"bestaaet": before, "pris_usd": cost}, "kategori": cat,
         "kontrol": {"pris_usd": kcost}, "bestaaet_efter_kontrol": after_ok}
    if rcost:
        r["efter"] = {"pris_usd": rcost}
    return r


def main() -> int:
    text = 'Vurdering: afvist.\n```json\n{"leverance_id": "x", "dom": "afvist", "fund": [' \
           '{"id": "F1", "klasse": "væsentlig", "status": "nyt", "paastand": "forkert", "krav": "k", "kilde": "s"},' \
           '{"id": "F2", "klasse": "mindre", "status": "nyt"},' \
           '{"id": "F3", "klasse": "kritisk", "status": "lukket"}]}\n```'
    verdict = review_ab.parse_verdict(text)
    expect("parse_verdict finder den sidste JSON-blok med dom", verdict is not None and verdict["dom"] == "afvist")
    findings = review_ab.blocking_findings(verdict)
    expect("kun åbne kritiske/væsentlige fund er blokerende", [f["id"] for f in findings] == ["F1"], findings)
    expect("parse_verdict uden dom giver None", review_ab.parse_verdict('svar {"a": 1} slut') is None)
    nested = 'tekst {"x": {"dom": "nej"}} og til sidst {"dom": "godkendt", "fund": []}'
    expect("parse_verdict tager den sidste dom", review_ab.parse_verdict(nested)["dom"] == "godkendt")
    expect("ingen dom → ingen blokerende", review_ab.blocking_findings(None) == [])

    c = review_ab.classify
    expect("klassifikation", [c(True, False, None), c(False, False, None), c(True, True, True),
                              c(True, True, False), c(False, True, True), c(False, True, False)]
           == ["godkendt_korrekt", "overset", "falsk_afvisning_bevaret", "falsk_afvisning_skadet",
               "fanget_rettet", "fanget_ikke_rettet"])

    rows = [row("A", True, "godkendt_korrekt", True),
            row("B", True, "falsk_afvisning_bevaret", True, rcost=0.08),
            row("C", True, "falsk_afvisning_skadet", False, rcost=0.08),
            row("D", False, "fanget_rettet", True, rcost=0.08),
            row("E", False, "fanget_rettet", True, rcost=0.08),
            row("F", False, "overset", False),
            {"id": "G", "fejl": True, "foer": {"bestaaet": True}}]
    s = review_ab.summarize(rows)
    expect("sammendrag: antal og kørselsfejl", s["n"] == 6 and s["koerselsfejl"] == 1, s)
    expect("sammendrag: bestået før og efter", (s["bestaaet_foer"], s["bestaaet_efter"]) == (3, 4), s)
    expect("sammendrag: netto = rettet − skadet", s["netto"] == 1, s)
    expect("sammendrag: præcision og recall", (s["praecision"], s["recall"]) == (0.5, 0.667), s)
    expect("sammendrag: pris pr. bestået", s["pris_pr_bestaaet_plugin"] == 0.14
           and s["pris_pr_bestaaet_med_kontrol"] == round((0.42 + 0.30 + 0.32) / 4, 4), s)

    reg = review_ab.review_agent("byg-el")
    expect("kontrolagent slås op i fagregistret", reg == "el-kontrol", reg)

    print(f"\n{len(FAILURES)} fejl")
    return 1 if FAILURES else 0


if __name__ == "__main__":
    sys.exit(main())
