#!/usr/bin/env python3
"""Format check of the frame files (references/frames.md) so rows can be added over time.

Use: python3 scripts/check_frames.py
Checks: table header, six cells per row, ID format and uniqueness, status in the source column
(V with date, T, P with role and date, or "P – mangler"), and that every referenced R-ID exists.
Placeholder rows ("P – mangler") are allowed: the agents fall back to the normal workflow for them.
"""
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
HEADER = "| ID | Situation | Ramme (alle betingelser) | Standardløsning | Uden for rammen | Kilde |"
ID = re.compile(r"R-[A-ZÆØÅ]+-\d{2}")
DATE = re.compile(r"\d{4}-\d{2}-\d{2}")
ROLE = re.compile(r"(mester|ingeniør|statiker|installatør|rådgiver)", re.I)


def status(source: str) -> str | None:
    """Return V, T, P or P-mangler from the start of the source cell, or None if unknown."""
    if source.startswith("P – mangler"):
        return "P-mangler"
    for s in ("V", "T", "P"):
        if source == s or source.startswith((s + " ", s + " –")):
            return s
    return None


def check(files: dict[str, str], others: dict[str, str] | None = None) -> tuple[list[str], dict[str, int]]:
    """Check frame files {name: text}; `others` are other texts whose R-ID references must exist."""
    errors: list[str] = []
    counts = {"V": 0, "T": 0, "P": 0, "P-mangler": 0}
    ids: dict[str, str] = {}
    for name, text in files.items():
        if HEADER not in text:
            errors.append(f"{name}: mangler tabelhovedet {HEADER}")
        for lineno, line in enumerate(text.splitlines(), 1):
            if not line.startswith("| R-"):
                continue
            cells = [c.strip() for c in line.strip().strip("|").split("|")]
            loc = f"{name}:{lineno}"
            if len(cells) != 6:
                errors.append(f"{loc}: {len(cells)} celler, forventer 6 (ID, situation, ramme, løsning, uden for, kilde)")
                continue
            rid, source = cells[0], cells[5]
            if not ID.fullmatch(rid):
                errors.append(f"{loc}: ugyldigt ID '{rid}' (forventer fx R-MUR-01)")
            elif rid in ids:
                errors.append(f"{loc}: ID {rid} findes også i {ids[rid]}")
            else:
                ids[rid] = loc
            s = status(source)
            if s is None:
                errors.append(f"{loc}: kilde skal starte med V, T, P eller 'P – mangler'")
                continue
            counts[s] += 1
            if s == "V" and not DATE.search(source):
                errors.append(f"{loc}: V-række mangler dato (ÅÅÅÅ-MM-DD)")
            if s == "P" and not (DATE.search(source) and ROLE.search(source)):
                errors.append(f"{loc}: P-række skal have fagrolle og dato, fx 'P – murermester, 2026-11-02'")
    for name, text in {**files, **(others or {})}.items():
        for rid in sorted(set(ID.findall(text)) - set(ids)):
            errors.append(f"{name}: henviser til {rid}, som ikke findes i nogen frames.md")
    return errors, counts


def main() -> int:
    files = {str(f.relative_to(ROOT)): f.read_text(encoding="utf-8")
             for f in sorted(ROOT.glob("plugins/*/skills/*/references/frames.md"))}
    others = {str(f.relative_to(ROOT)): f.read_text(encoding="utf-8")
             for pattern in ("plugins/**/*.md", "shared/*.md", "template/**/*.md")
             for f in sorted(ROOT.glob(pattern)) if f.name != "frames.md"}
    errors, counts = check(files, others)
    for f in errors:
        print(f"FEJL  {f}")
    print(f"Rammer: {len(files)} filer · {counts['V']} V · {counts['T']} T · {counts['P']} P · "
          f"{counts['P-mangler']} P – mangler · {len(errors)} fejl")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
