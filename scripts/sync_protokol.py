#!/usr/bin/env python3
"""Indsætter de fælles protokoller i agentfilerne mellem markører.

Én kilde til sandhed:
  faelles/protokol.md        → fagagenter   (FÆLLES-PROTOKOL-markører)
  faelles/kontrolprotokol.md → kontrolagenter (KONTROL-PROTOKOL-markører)

Kør efter hver ændring i faelles/:  python3 scripts/sync_protokol.py [--check]
"""
import pathlib
import sys

ROD = pathlib.Path(__file__).resolve().parent.parent
BLOKKE = [
    ("protokol.md", "FÆLLES-PROTOKOL", "redigér faelles/protokol.md"),
    ("kontrolprotokol.md", "KONTROL-PROTOKOL", "redigér faelles/kontrolprotokol.md"),
]


def markoerer(navn: str, hint: str) -> tuple[str, str]:
    return (f"<!-- {navn}:START (genereres af scripts/sync_protokol.py – {hint}) -->",
            f"<!-- {navn}:SLUT -->")


def kandidater() -> list[pathlib.Path]:
    filer = list(ROD.glob("plugins/*/agents/*.md")) + list(ROD.glob("skabelon/**/agents/*.md"))
    return sorted(set(filer))


def main() -> int:
    check = "--check" in sys.argv
    afvigelser = 0
    for kilde, navn, hint in BLOKKE:
        start, slut = markoerer(navn, hint)
        tekst_kilde = (ROD / "faelles" / kilde).read_text(encoding="utf-8").strip()
        blok = f"{start}\n{tekst_kilde}\n{slut}"
        for fil in kandidater():
            tekst = fil.read_text(encoding="utf-8")
            if start not in tekst or slut not in tekst:
                continue
            foer, rest = tekst.split(start, 1)
            _, efter = rest.split(slut, 1)
            ny = foer + blok + efter
            if ny != tekst:
                afvigelser += 1
                if check:
                    print(f"UDE AF SYNK ({navn}): {fil.relative_to(ROD)}")
                else:
                    fil.write_text(ny, encoding="utf-8")
                    print(f"opdateret ({navn}): {fil.relative_to(ROD)}")
    if check and afvigelser:
        return 1
    print("Protokoller i synk.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
