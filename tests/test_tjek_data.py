#!/usr/bin/env python3
"""Tester dataseparationen (scripts/tjek_data.py) med et falsk hjem og et falsk repo.

Kør:  python3 tests/test_tjek_data.py
"""
import os
import pathlib
import subprocess
import sys
import tempfile

ROD = pathlib.Path(__file__).resolve().parent.parent
TJEK = ROD / "scripts" / "tjek_data.py"
FEJL = []
NOEGLE = "x" * 8 + "TESTNOEGLE" + "y" * 30  # falsk nøgle – kun til testen
SAG = "2031-02-03-tag-test"
LINJE = "Tagfladen mod syd har tre knækkede teglsten over køkkenvinduet og en utæt inddækning."


def kør(hjem, repo):
    env = dict(os.environ, HOME=str(hjem), BYG_REPO_ROD=str(repo))
    r = subprocess.run([sys.executable, str(TJEK)], capture_output=True, text=True, env=env, timeout=60)
    return r.returncode, r.stdout


def forvent(navn, ok, ud=""):
    print(("OK   " if ok else "FEJL ") + navn + ("" if ok else f"\n{ud}"))
    if not ok:
        FEJL.append(navn)


def main() -> int:
    with tempfile.TemporaryDirectory() as tmp:
        hjem, repo = pathlib.Path(tmp) / "hjem", pathlib.Path(tmp) / "repo"
        sagsmappe = pathlib.Path(tmp) / "arbejde" / "byg-sager" / SAG
        sagsmappe.mkdir(parents=True)
        (sagsmappe / "projektgrundlag.md").write_text(f"# Projektgrundlag\n\n{LINJE}\n", encoding="utf-8")
        vb = hjem / ".claude" / "plugins" / "data" / "byg-test" / "videnbank"
        vb.mkdir(parents=True)
        (vb / "sager.md").write_text(f"| Sag-id | Sti |\n|---|---|\n| {SAG} | `{sagsmappe}` |\n| lindevej-7b | – |\n", encoding="utf-8")
        (hjem / ".config" / "byg-data").mkdir(parents=True)
        (hjem / ".config" / "byg-data" / "datafordeler_api_key").write_text(NOEGLE, encoding="utf-8")
        (hjem / ".config" / "byg-eksperter").mkdir(parents=True)
        (hjem / ".config" / "byg-eksperter" / "private-termer.txt").write_text("# egne termer\nSolsikkevej 99\n", encoding="utf-8")
        (repo / "plugins" / "p" / "skills" / "s").mkdir(parents=True)
        ren = repo / "plugins" / "p" / "skills" / "s" / "SKILL.md"
        ren.write_text("# Generel viden\nTestadresse til evals: Rådhuspladsen 1, 1550 København V.\n", encoding="utf-8")

        kode, ud = kør(hjem, repo)
        forvent("rent repo med testdata godkendes", kode == 0 and "1 sagsmappe(r)" in ud, ud)

        tilfaelde = {
            "sag-id fra videnbanken afvises": ("plugins/p/eksempel.md", f"Se sagen {SAG}."),
            "sag-id uden dato afvises": ("plugins/p/eksempel.md", "Som i sagen Lindevej-7B viste …"),
            "privat term afvises": ("plugins/p/eksempel.md", "Huset på Solsikkevej 99 har …"),
            "kopieret sagstekst afvises": ("plugins/p/references/praksis.md", f"- **Erfaring:** {LINJE}"),
            "lokal API-nøgle afvises": ("tests/fixture.py", f'KEY = "{NOEGLE}"'),
            "nøgle i URL afvises": ("plugins/p/x.md", "https://graphql.datafordeler.dk/BBR/v3?apiKey=" + "A1b2" * 8),
            "sagsmappe i repoet afvises": ("byg-sager/2031-01-01-x/noter.md", "noter"),
            "sagsfil i repoet afvises": ("plugins/p/beslutningslog.md", "log"),
            "PDF-bilag afvises": ("plugins/p/energimaerke.pdf", "%PDF"),
        }
        for navn, (sti, indhold) in tilfaelde.items():
            f = repo / sti
            f.parent.mkdir(parents=True, exist_ok=True)
            f.write_text(indhold, encoding="utf-8")
            kode, ud = kør(hjem, repo)
            forvent(navn, kode == 1 and "FEJL" in ud, ud)
            if "nøgle" in navn:
                forvent(f"{navn}: værdien udskrives ikke", NOEGLE not in ud and "A1b2A1b2" not in ud, ud)
            f.unlink()

        kode, ud = kør(pathlib.Path(tmp) / "tomt-hjem", repo)
        forvent("uden lokale data (CI) køres strukturtjek alene", kode == 0 and "0 private termer" in ud, ud)

    print(f"\n{'ALLE TESTS BESTÅET' if not FEJL else f'{len(FEJL)} FEJL'}")
    return 1 if FEJL else 0


if __name__ == "__main__":
    sys.exit(main())
