#!/usr/bin/env python3
"""Tests the data separation (scripts/check_data.py) with a fake home and a fake repo.

Run:  python3 tests/test_check_data.py
"""
import os
import pathlib
import subprocess
import sys
import tempfile

ROOT = pathlib.Path(__file__).resolve().parent.parent
CHECK = ROOT / "scripts" / "check_data.py"
FAILURES = []
KEY = "x" * 8 + "TESTNOEGLE" + "y" * 30  # fake key – for the test only
CASE = "2031-02-03-tag-test"
LINE = "Tagfladen mod syd har tre knækkede teglsten over køkkenvinduet og en utæt inddækning."
PROPERTY_LINE = "Træpillekedel på 12 kW fra 2009 med integreret returløft og elpatron på 6 kW i beholderen"
TEMPLATE_LINE = "**Kilder:** F foto · D dokument (typeskilt, manual, rapport, BBR) · M måling · B bygherren"


def run(home, repo):
    env = dict(os.environ, HOME=str(home), BYG_REPO_ROD=str(repo))
    r = subprocess.run([sys.executable, str(CHECK)], capture_output=True, text=True, env=env, timeout=60)
    return r.returncode, r.stdout


def expect(name, ok, out=""):
    print(("OK   " if ok else "FEJL ") + name + ("" if ok else f"\n{out}"))
    if not ok:
        FAILURES.append(name)


def main() -> int:
    with tempfile.TemporaryDirectory() as tmp:
        home, repo = pathlib.Path(tmp) / "hjem", pathlib.Path(tmp) / "repo"
        case_dir = pathlib.Path(tmp) / "arbejde" / "byg-cases" / CASE
        case_dir.mkdir(parents=True)
        (case_dir / "project-basis.md").write_text(f"# Projektgrundlag\n\n{LINE}\n", encoding="utf-8")
        properties = case_dir.parent / "properties"
        properties.mkdir()
        (properties / "lindevej-7b.md").write_text(f"# Ejendomskort\n\n| E-VVS-01 | Kedel | {PROPERTY_LINE} |\n", encoding="utf-8")
        vb = home / ".claude" / "plugins" / "data" / "byg-test" / "knowledge-bank"
        vb.mkdir(parents=True)
        (vb / "cases.md").write_text(f"| Sag-id | Sti |\n|---|---|\n| {CASE} | `{case_dir}` |\n| lindevej-7b | – |\n", encoding="utf-8")
        (home / ".config" / "byg-data").mkdir(parents=True)
        (home / ".config" / "byg-data" / "datafordeler_api_key").write_text(KEY, encoding="utf-8")
        (home / ".config" / "engineer-any-house").mkdir(parents=True)
        (home / ".config" / "engineer-any-house" / "private-termer.txt").write_text("# egne termer\nSolsikkevej 99\n", encoding="utf-8")
        (repo / "plugins" / "p" / "skills" / "s").mkdir(parents=True)
        clean = repo / "plugins" / "p" / "skills" / "s" / "SKILL.md"
        clean.write_text("# Generel viden\nTestadresse til evals: Rådhuspladsen 1, 1550 København V.\n\n```\n"
                       f"{TEMPLATE_LINE}\n```\n", encoding="utf-8")
        (case_dir / "status.md").write_text(f"# Status\n{TEMPLATE_LINE}\n", encoding="utf-8")  # template used in the case

        code, out = run(home, repo)
        expect("rent repo med testdata godkendes (sagsmappe + properties)", code == 0 and "2 sagsmappe(r)" in out, out)

        cases = {
            "sag-id fra videnbanken afvises": ("plugins/p/eksempel.md", f"Se sagen {CASE}."),
            "sag-id uden dato afvises": ("plugins/p/eksempel.md", "Som i sagen Lindevej-7B viste …"),
            "privat term afvises": ("plugins/p/eksempel.md", "Huset på Solsikkevej 99 har …"),
            "kopieret sagstekst afvises": ("plugins/p/references/praksis.md", f"- **Erfaring:** {LINE}"),
            "kopieret tekst fra ejendomskort afvises": ("plugins/p/references/praksis.md", f"- {PROPERTY_LINE}"),
            "ejendomskort i repoet afvises": ("properties/lindevej-7b.md", "kort"),
            "lokal API-nøgle afvises": ("tests/fixture.py", f'KEY = "{KEY}"'),
            "nøgle i URL afvises": ("plugins/p/x.md", "https://graphql.datafordeler.dk/BBR/v3?apiKey=" + "A1b2" * 8),
            "sagsmappe i repoet afvises": ("byg-cases/2031-01-01-x/noter.md", "noter"),
            "sagsfil i repoet afvises": ("plugins/p/decision-log.md", "log"),
            "PDF-bilag afvises": ("plugins/p/energimaerke.pdf", "%PDF"),
        }
        for name, (path, content) in cases.items():
            f = repo / path
            f.parent.mkdir(parents=True, exist_ok=True)
            f.write_text(content, encoding="utf-8")
            code, out = run(home, repo)
            expect(name, code == 1 and "FEJL" in out, out)
            if "nøgle" in name:
                expect(f"{name}: værdien udskrives ikke", KEY not in out and "A1b2A1b2" not in out, out)
            f.unlink()

        # Text already on origin/main comes from the plugin – a case that copies it is not a leak.
        def git(*a):
            subprocess.run(["git", "-C", str(repo), *a], capture_output=True, check=True)
        git("init", "-q")
        (repo / "plugins" / "p" / "praksis.md").write_text(f"- {LINE}\n", encoding="utf-8")
        git("add", "-A")
        git("-c", "user.name=t", "-c", "user.email=t@t", "commit", "-q", "-m", "main")
        git("update-ref", "refs/remotes/origin/main", "HEAD")
        code, out = run(home, repo)
        expect("sagstekst, der allerede står på origin/main, godkendes", code == 0, out)
        (repo / "plugins" / "p" / "ny.md").write_text(f"- {PROPERTY_LINE}\n", encoding="utf-8")
        code, out = run(home, repo)
        expect("ny kopieret sagstekst afvises stadig med git", code == 1 and "ny.md" in out, out)
        (repo / "plugins" / "p" / "ny.md").unlink()
        (repo / "plugins" / "p" / "praksis.md").unlink()

        code, out = run(pathlib.Path(tmp) / "tomt-hjem", repo)
        expect("uden lokale data (CI) køres strukturtjek alene", code == 0 and "0 private termer" in out, out)

    print(f"\n{'ALLE TESTS BESTÅET' if not FAILURES else f'{len(FAILURES)} FEJL'}")
    return 1 if FAILURES else 0


if __name__ == "__main__":
    sys.exit(main())
