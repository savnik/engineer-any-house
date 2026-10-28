#!/usr/bin/env python3
"""Udgivelse: samler versionsnoterne og hæver versionerne – i en udgivelsesgren fra main, efter merge.

Feature-grene hæver aldrig versioner selv (det er den største kilde til merge-konflikter).
I stedet lægger hver gren én versionsnote i versionsnoter/<gren>.md:

    ---
    byg-kontrol: minor
    byg: patch
    ---
    Kort beskrivelse af ændringen (bliver udgivelsesnoten).

Brug:  python3 scripts/udgiv.py            hæv versioner, skriv CHANGELOG.md, slet de udgivne noter
       python3 scripts/udgiv.py --proev    vis hvad der ville ske
       python3 scripts/udgiv.py --check    valider noterne (bruges af valider.py)
main er beskyttet, så udgivelsen går også gennem en PR:
       git switch -c udgivelse/<version> origin/main && python3 scripts/udgiv.py
       git commit -am "Udgivelse <version>" && git push -u origin HEAD   → PR, CI grøn, merge
(pre-commit tillader versionsændringer i grene, der hedder udgivelse/*).
"""
import datetime
import json
import pathlib
import re
import sys

ROD = pathlib.Path(__file__).resolve().parent.parent
NOTER = ROD / "versionsnoter"
MARKED = ROD / ".claude-plugin" / "marketplace.json"
CHANGELOG = ROD / "CHANGELOG.md"
NIVEAU = {"patch": 0, "minor": 1, "major": 2}


def plugin_json(navn: str) -> pathlib.Path:
    return ROD / "plugins" / navn / ".claude-plugin" / "plugin.json"


def laes_note(f: pathlib.Path) -> tuple[dict, str, list]:
    """(plugin → niveau, tekst, fejl)."""
    t = f.read_text(encoding="utf-8")
    m = re.match(r"^---\n(.*?)\n---\n?(.*)$", t, re.S)
    if not m:
        return {}, "", [f"{f.name}: mangler '---'-blok med '<plugin>: patch|minor|major'"]
    bump, fejl = {}, []
    for linje in m.group(1).splitlines():
        if not linje.strip() or linje.lstrip().startswith("#"):
            continue
        lm = re.match(r"^\s*([a-z0-9-]+)\s*:\s*(patch|minor|major)\s*$", linje)
        if not lm:
            fejl.append(f"{f.name}: ugyldig linje '{linje}' (forventet '<plugin>: patch|minor|major')")
            continue
        if not plugin_json(lm.group(1)).is_file():
            fejl.append(f"{f.name}: ukendt plugin '{lm.group(1)}'")
            continue
        bump[lm.group(1)] = lm.group(2)
    if not bump and not fejl:
        fejl.append(f"{f.name}: ingen plugins nævnt")
    if not m.group(2).strip():
        fejl.append(f"{f.name}: mangler beskrivelse under '---'-blokken")
    return bump, m.group(2).strip(), fejl


def hæv(version: str, niveau: str) -> str:
    major, minor, patch = (int(x) for x in version.split("."))
    if niveau == "major":
        return f"{major + 1}.0.0"
    if niveau == "minor":
        return f"{major}.{minor + 1}.0"
    return f"{major}.{minor}.{patch + 1}"


def skriv_json(f: pathlib.Path, version: str, nøgle_sti: tuple) -> None:
    """Ret kun versionslinjen, så resten af filen (formatering) står urørt."""
    t = f.read_text(encoding="utf-8")
    data = json.loads(t)
    obj = data
    for k in nøgle_sti:
        obj = obj[k]
    gammel = obj["version"]
    ny_t, n = re.subn(rf'("version"\s*:\s*"){re.escape(gammel)}(")', rf"\g<1>{version}\g<2>", t, count=1)
    if n != 1:
        raise SystemExit(f"Fandt ikke versionslinjen i {f}")
    f.write_text(ny_t, encoding="utf-8")


def main() -> int:
    proev, check = "--proev" in sys.argv, "--check" in sys.argv
    noter = sorted(f for f in NOTER.glob("*.md") if f.name != "README.md") if NOTER.is_dir() else []
    samlet, tekster, fejl = {}, [], []
    for f in noter:
        bump, tekst, ff = laes_note(f)
        fejl += ff
        for p, n in bump.items():
            if p not in samlet or NIVEAU[n] > NIVEAU[samlet[p]]:
                samlet[p] = n
        tekster.append((f.stem, sorted(bump), tekst))
    if fejl:
        print("\n".join("FEJL  " + x for x in fejl))
        return 1
    if check:
        print(f"{len(noter)} versionsnote(r) ok")
        return 0
    if not samlet:
        print("Ingen versionsnoter – intet at udgive.")
        return 0

    nye = {}
    for p, n in sorted(samlet.items()):
        gammel = json.loads(plugin_json(p).read_text(encoding="utf-8"))["version"]
        nye[p] = (gammel, hæv(gammel, n), n)
    marked = json.loads(MARKED.read_text(encoding="utf-8"))
    m_gammel = marked["metadata"]["version"]
    m_niveau = max(samlet.values(), key=lambda n: NIVEAU[n])
    m_ny = hæv(m_gammel, m_niveau)

    for p, (g, n, niv) in nye.items():
        print(f"{p:16} {g} → {n}  ({niv})")
    print(f"{'marketplace':16} {m_gammel} → {m_ny}  ({m_niveau})")
    if proev:
        return 0

    for p, (_, n, _) in nye.items():
        skriv_json(plugin_json(p), n, ())
    skriv_json(MARKED, m_ny, ("metadata",))
    afsnit = [f"## {m_ny} – {datetime.date.today().isoformat()}", ""]
    afsnit += [f"- `{p}` {g} → {n}" for p, (g, n, _) in nye.items()]
    afsnit.append("")
    for navn, plugins, tekst in tekster:
        afsnit += [f"### {navn} ({', '.join(plugins)})", tekst, ""]
    gammel_log = CHANGELOG.read_text(encoding="utf-8") if CHANGELOG.exists() else "# Ændringslog\n"
    hoved, _, rest = gammel_log.partition("\n")
    ny_log = hoved + "\n\n" + "\n".join(afsnit)
    if rest.strip():
        ny_log += "\n" + rest.lstrip("\n")
    CHANGELOG.write_text(ny_log, encoding="utf-8")
    for f in noter:
        f.unlink()
    print(f"\nCHANGELOG.md opdateret, {len(noter)} note(r) udgivet. Commit i grenen udgivelse/{m_ny}: git commit -am \"Udgivelse {m_ny}\" – og åbn en PR")
    return 0


if __name__ == "__main__":
    sys.exit(main())
