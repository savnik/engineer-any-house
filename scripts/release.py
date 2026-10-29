#!/usr/bin/env python3
"""Release: collects the version notes and raises the versions – in a release branch from main, after merge.

Feature branches never raise versions themselves (that is the biggest source of merge conflicts).
Instead each branch adds one version note in release-notes/<branch>.md:

    ---
    byg-review: minor
    byg: patch
    ---
    Short description of the change (becomes the release note).

Usage: python3 scripts/release.py            raise versions, write CHANGELOG.md, delete the released notes
       python3 scripts/release.py --dry-run  show what would happen
       python3 scripts/release.py --check    validate the notes (used by validate.py)
main is protected, so the release also goes through a PR:
       git switch -c release/<version> origin/main && python3 scripts/release.py
       git commit -am "Udgivelse <version>" && git push -u origin HEAD   → PR, CI green, merge
(pre-commit allows version changes in branches named release/*).
"""
import datetime
import json
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
NOTES_DIR = ROOT / "release-notes"
MARKETPLACE = ROOT / ".claude-plugin" / "marketplace.json"
CHANGELOG = ROOT / "CHANGELOG.md"
LEVEL = {"patch": 0, "minor": 1, "major": 2}


def plugin_json(name: str) -> pathlib.Path:
    return ROOT / "plugins" / name / ".claude-plugin" / "plugin.json"


def read_note(f: pathlib.Path) -> tuple[dict, str, list]:
    """(plugin → level, text, errors)."""
    t = f.read_text(encoding="utf-8")
    m = re.match(r"^---\n(.*?)\n---\n?(.*)$", t, re.S)
    if not m:
        return {}, "", [f"{f.name}: mangler '---'-blok med '<plugin>: patch|minor|major'"]
    bump, errors = {}, []
    for line in m.group(1).splitlines():
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        lm = re.match(r"^\s*([a-z0-9-]+)\s*:\s*(patch|minor|major)\s*$", line)
        if not lm:
            errors.append(f"{f.name}: ugyldig linje '{line}' (forventet '<plugin>: patch|minor|major')")
            continue
        if not plugin_json(lm.group(1)).is_file():
            errors.append(f"{f.name}: ukendt plugin '{lm.group(1)}'")
            continue
        bump[lm.group(1)] = lm.group(2)
    if not bump and not errors:
        errors.append(f"{f.name}: ingen plugins nævnt")
    if not m.group(2).strip():
        errors.append(f"{f.name}: mangler beskrivelse under '---'-blokken")
    return bump, m.group(2).strip(), errors


def raise_version(version: str, level: str) -> str:
    major, minor, patch = (int(x) for x in version.split("."))
    if level == "major":
        return f"{major + 1}.0.0"
    if level == "minor":
        return f"{major}.{minor + 1}.0"
    return f"{major}.{minor}.{patch + 1}"


def write_json(f: pathlib.Path, version: str, key_path: tuple) -> None:
    """Change only the version line, so the rest of the file (formatting) stays untouched."""
    t = f.read_text(encoding="utf-8")
    data = json.loads(t)
    obj = data
    for k in key_path:
        obj = obj[k]
    old = obj["version"]
    new_text, n = re.subn(rf'("version"\s*:\s*"){re.escape(old)}(")', rf"\g<1>{version}\g<2>", t, count=1)
    if n != 1:
        raise SystemExit(f"Fandt ikke versionslinjen i {f}")
    f.write_text(new_text, encoding="utf-8")


def main() -> int:
    dry_run, check = "--dry-run" in sys.argv, "--check" in sys.argv
    notes = sorted(f for f in NOTES_DIR.glob("*.md") if f.name != "README.md") if NOTES_DIR.is_dir() else []
    combined, texts, errors = {}, [], []
    for f in notes:
        bump, text, errs = read_note(f)
        errors += errs
        for p, n in bump.items():
            if p not in combined or LEVEL[n] > LEVEL[combined[p]]:
                combined[p] = n
        texts.append((f.stem, sorted(bump), text))
    if errors:
        print("\n".join("FEJL  " + x for x in errors))
        return 1
    if check:
        print(f"{len(notes)} versionsnote(r) ok")
        return 0
    if not combined:
        print("Ingen versionsnoter – intet at udgive.")
        return 0

    new = {}
    for p, n in sorted(combined.items()):
        old = json.loads(plugin_json(p).read_text(encoding="utf-8"))["version"]
        new[p] = (old, raise_version(old, n), n)
    marketplace = json.loads(MARKETPLACE.read_text(encoding="utf-8"))
    mp_old = marketplace["metadata"]["version"]
    mp_level = max(combined.values(), key=lambda n: LEVEL[n])
    mp_new = raise_version(mp_old, mp_level)

    for p, (o, n, lvl) in new.items():
        print(f"{p:16} {o} → {n}  ({lvl})")
    print(f"{'marketplace':16} {mp_old} → {mp_new}  ({mp_level})")
    if dry_run:
        return 0

    for p, (_, n, _) in new.items():
        write_json(plugin_json(p), n, ())
    write_json(MARKETPLACE, mp_new, ("metadata",))
    section = [f"## {mp_new} – {datetime.date.today().isoformat()}", ""]
    section += [f"- `{p}` {o} → {n}" for p, (o, n, _) in new.items()]
    section.append("")
    for name, plugins, text in texts:
        section += [f"### {name} ({', '.join(plugins)})", text, ""]
    old_log = CHANGELOG.read_text(encoding="utf-8") if CHANGELOG.exists() else "# Ændringslog\n"
    header, _, rest = old_log.partition("\n")
    new_log = header + "\n\n" + "\n".join(section)
    if rest.strip():
        new_log += "\n" + rest.lstrip("\n")
    CHANGELOG.write_text(new_log, encoding="utf-8")
    for f in notes:
        f.unlink()
    print(f"\nCHANGELOG.md opdateret, {len(notes)} note(r) udgivet. Commit i grenen release/{mp_new}: git commit -am \"Udgivelse {mp_new}\" – og åbn en PR")
    return 0


if __name__ == "__main__":
    sys.exit(main())
