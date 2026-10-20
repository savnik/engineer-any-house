#!/usr/bin/env python3
"""Tests the control arm (scripts/kontrol_ab.py): verdict parsing, classification and summary. No tokens.

Kør:  python3 tests/test_kontrol_ab.py
"""
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import kontrol_ab  # noqa: E402

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
    dom = kontrol_ab.parse_dom(text)
    expect("parse_dom finder den sidste JSON-blok med dom", dom is not None and dom["dom"] == "afvist")
    fund = kontrol_ab.blocking_findings(dom)
    expect("kun åbne kritiske/væsentlige fund er blokerende", [f["id"] for f in fund] == ["F1"], fund)
    expect("parse_dom uden dom giver None", kontrol_ab.parse_dom('svar {"a": 1} slut') is None)
    nested = 'tekst {"x": {"dom": "nej"}} og til sidst {"dom": "godkendt", "fund": []}'
    expect("parse_dom tager den sidste dom", kontrol_ab.parse_dom(nested)["dom"] == "godkendt")
    expect("ingen dom → ingen blokerende", kontrol_ab.blocking_findings(None) == [])

    c = kontrol_ab.classify
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
    s = kontrol_ab.summarize(rows)
    expect("sammendrag: antal og kørselsfejl", s["n"] == 6 and s["koerselsfejl"] == 1, s)
    expect("sammendrag: bestået før og efter", (s["bestaaet_foer"], s["bestaaet_efter"]) == (3, 4), s)
    expect("sammendrag: netto = rettet − skadet", s["netto"] == 1, s)
    expect("sammendrag: præcision og recall", (s["praecision"], s["recall"]) == (0.5, 0.667), s)
    expect("sammendrag: pris pr. bestået", s["pris_pr_bestaaet_plugin"] == 0.14
           and s["pris_pr_bestaaet_med_kontrol"] == round((0.42 + 0.30 + 0.32) / 4, 4), s)

    reg = kontrol_ab.control_agent("byg-el")
    expect("kontrolagent slås op i fagregistret", reg == "el-kontrol", reg)

    print(f"\n{len(FAILURES)} fejl")
    return 1 if FAILURES else 0


if __name__ == "__main__":
    sys.exit(main())
