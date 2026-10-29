#!/usr/bin/env python3
"""Format check of the frame files (references/rammer.md) so rows can be added over time.

Use: python3 scripts/check_frames.py
Checks: table header, six cells per row, ID format and uniqueness, status in the source column
(V with date, T, P with role and date, or "P – mangler"), and that every referenced R-ID exists.
Placeholder rows ("P – mangler") are allowed: the agents fall back to the normal workflow for them.
"""
import pathlib
import re
import sys

ROD = pathlib.Path(__file__).resolve().parent.parent
HOVED = "| ID | Situation | Ramme (alle betingelser) | Standardløsning | Uden for rammen | Kilde |"
ID = re.compile(r"R-[A-ZÆØÅ]+-\d{2}")
DATO = re.compile(r"\d{4}-\d{2}-\d{2}")
ROLLE = re.compile(r"(mester|ingeniør|statiker|installatør|rådgiver)", re.I)


def status(kilde: str) -> str | None:
    """Return V, T, P or P-mangler from the start of the source cell, or None if unknown."""
    if kilde.startswith("P – mangler"):
        return "P-mangler"
    for s in ("V", "T", "P"):
        if kilde == s or kilde.startswith((s + " ", s + " –")):
            return s
    return None


def tjek(filer: dict[str, str], andre: dict[str, str] | None = None) -> tuple[list[str], dict[str, int]]:
    """Check frame files {name: text}; `andre` are other texts whose R-ID references must exist."""
    fejl: list[str] = []
    antal = {"V": 0, "T": 0, "P": 0, "P-mangler": 0}
    ider: dict[str, str] = {}
    for navn, tekst in filer.items():
        if HOVED not in tekst:
            fejl.append(f"{navn}: mangler tabelhovedet {HOVED}")
        for nr, linje in enumerate(tekst.splitlines(), 1):
            if not linje.startswith("| R-"):
                continue
            celler = [c.strip() for c in linje.strip().strip("|").split("|")]
            sted = f"{navn}:{nr}"
            if len(celler) != 6:
                fejl.append(f"{sted}: {len(celler)} celler, forventer 6 (ID, situation, ramme, løsning, uden for, kilde)")
                continue
            rid, kilde = celler[0], celler[5]
            if not ID.fullmatch(rid):
                fejl.append(f"{sted}: ugyldigt ID '{rid}' (forventer fx R-MUR-01)")
            elif rid in ider:
                fejl.append(f"{sted}: ID {rid} findes også i {ider[rid]}")
            else:
                ider[rid] = sted
            s = status(kilde)
            if s is None:
                fejl.append(f"{sted}: kilde skal starte med V, T, P eller 'P – mangler'")
                continue
            antal[s] += 1
            if s == "V" and not DATO.search(kilde):
                fejl.append(f"{sted}: V-række mangler dato (ÅÅÅÅ-MM-DD)")
            if s == "P" and not (DATO.search(kilde) and ROLLE.search(kilde)):
                fejl.append(f"{sted}: P-række skal have fagrolle og dato, fx 'P – murermester, 2026-11-02'")
    for navn, tekst in {**filer, **(andre or {})}.items():
        for rid in sorted(set(ID.findall(tekst)) - set(ider)):
            fejl.append(f"{navn}: henviser til {rid}, som ikke findes i nogen rammer.md")
    return fejl, antal


def main() -> int:
    filer = {str(f.relative_to(ROD)): f.read_text(encoding="utf-8")
             for f in sorted(ROD.glob("plugins/*/skills/*/references/rammer.md"))}
    andre = {str(f.relative_to(ROD)): f.read_text(encoding="utf-8")
             for mønster in ("plugins/**/*.md", "faelles/*.md", "skabelon/**/*.md")
             for f in sorted(ROD.glob(mønster)) if f.name != "rammer.md"}
    fejl, antal = tjek(filer, andre)
    for f in fejl:
        print(f"FEJL  {f}")
    print(f"Rammer: {len(filer)} filer · {antal['V']} V · {antal['T']} T · {antal['P']} P · "
          f"{antal['P-mangler']} P – mangler · {len(fejl)} fejl")
    return 1 if fejl else 0


if __name__ == "__main__":
    sys.exit(main())
