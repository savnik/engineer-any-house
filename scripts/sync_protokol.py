#!/usr/bin/env python3
"""Indsætter de fælles protokoller i agentfilerne mellem markører.

Én kilde til sandhed:
  faelles/protokol.md        → fagagenter   (FÆLLES-PROTOKOL-markører)
  faelles/kontrolprotokol.md → kontrolagenter (KONTROL-PROTOKOL-markører)

Kør efter hver ændring i faelles/:  python3 scripts/sync_protokol.py [--check]
--staged tjekker indholdet i git-indekset (det, der committes); bruges af scripts/hooks/pre-commit.
"""
import fnmatch
import pathlib
import subprocess
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


def staged(rel: str) -> str | None:
    """Return the staged (index) text of a repo-relative path, or None if it is not in the index."""
    r = subprocess.run(["git", "-C", str(ROD), "show", f":{rel}"], capture_output=True)
    return r.stdout.decode("utf-8") if r.returncode == 0 else None


def staged_kandidater() -> list[str]:
    r = subprocess.run(["git", "-C", str(ROD), "ls-files"], capture_output=True, text=True, check=True)
    return sorted(f for f in r.stdout.splitlines()
                  if fnmatch.fnmatch(f, "plugins/*/agents/*.md") or fnmatch.fnmatch(f, "skabelon/*agents/*.md"))


def main() -> int:
    if "--staged" in sys.argv:
        return main_staged()
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


def main_staged() -> int:
    """Like --check, but on the index, so a commit cannot hold protocols out of sync."""
    afvigelser = 0
    for kilde, navn, hint in BLOKKE:
        start, slut = markoerer(navn, hint)
        tekst_kilde = (staged(f"faelles/{kilde}") or "").strip()
        blok = f"{start}\n{tekst_kilde}\n{slut}"
        for rel in staged_kandidater():
            tekst = staged(rel)
            if tekst is None or start not in tekst or slut not in tekst:
                continue
            if tekst.split(start, 1)[1].split(slut, 1)[0] != f"\n{tekst_kilde}\n":
                afvigelser += 1
                print(f"UDE AF SYNK i indekset ({navn}): {rel}")
    return 1 if afvigelser else 0


if __name__ == "__main__":
    sys.exit(main())
