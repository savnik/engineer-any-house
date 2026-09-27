#!/usr/bin/env python3
"""Bygger distributionsfiler i dist/.

  dist/cowork/<plugin>.plugin  ét pr. fag-plugin og byg-kontrol (uden evals) – fag kræver byg-kontrol
  dist/cowork/byg.plugin       samlet Cowork-pakke: alle agenter, skills og hooks i ét plugin ved navn "byg"
  dist/byg-eksperter.zip       hele repoet (marketplace til Claude Code)

Brug: python3 scripts/pak.py [--validate]   (--validate kører `claude plugin validate` på den samlede pakke)
"""
import json
import pathlib
import shutil
import subprocess
import sys
import tempfile
import zipfile

ROD = pathlib.Path(__file__).resolve().parent.parent
DIST = ROD / "dist"
SKRALD = {"__pycache__", ".DS_Store", "results", ".git", "dist"}


def zip_mappe(mappe: pathlib.Path, zipfil: pathlib.Path, prefix: str = "", udelad: set = frozenset()) -> int:
    n = 0
    with zipfile.ZipFile(zipfil, "w", zipfile.ZIP_DEFLATED) as z:
        for f in sorted(mappe.rglob("*")):
            rel = f.relative_to(mappe)
            if f.is_dir() or (set(rel.parts) & (SKRALD | set(udelad))):
                continue
            z.write(f, (pathlib.PurePosixPath(prefix) / rel.as_posix()).as_posix() if prefix else rel.as_posix())
            n += 1
    return n


def saml(maal: pathlib.Path) -> None:
    plugins = [p for p in sorted((ROD / "plugins").iterdir())
               if (p / ".claude-plugin" / "plugin.json").exists() and p.name != "byg-team"]
    version = json.loads((ROD / "plugins" / "byg" / ".claude-plugin" / "plugin.json").read_text(encoding="utf-8"))["version"]
    for p in plugins:
        for del_ in ("agents", "skills", "hooks"):
            for f in sorted((p / del_).rglob("*")) if (p / del_).exists() else []:
                if f.is_dir() or set(f.parts) & SKRALD:
                    continue
                rel = f.relative_to(p)
                ud = maal / rel
                if ud.exists():
                    sys.exit(f"Navnekonflikt i samlet pakke: {rel} ({p.name})")
                ud.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(f, ud)
    (maal / ".claude-plugin").mkdir(parents=True, exist_ok=True)
    manifest = {
        "name": "byg",
        "displayName": "Byg – projektleder, fagagenter og kvalitetskontrol",
        "version": version,
        "description": "Samlet pakke: projektleder, fagagenter på mesterniveau (vvs, el, murer, ventilation, maler, tømrer) "
                       "og uafhængig kvalitetskontrol af hver leverance (højst 3 forsøg pr. runde, derefter RCA, forbedring af fagagenten og ny runde).",
        "author": {"name": "Peter Savnik"},
        "keywords": ["byggeri", "renovering", "projektledelse", "kvalitetskontrol", "danmark"],
    }
    (maal / ".claude-plugin" / "plugin.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    shutil.copy2(ROD / "README.md", maal / "README.md")


def main() -> int:
    if DIST.exists():
        shutil.rmtree(DIST)
    (DIST / "cowork").mkdir(parents=True)
    for p in sorted((ROD / "plugins").iterdir()):
        if p.name in ("byg", "byg-team") or not (p / ".claude-plugin" / "plugin.json").exists():
            continue
        n = zip_mappe(p, DIST / "cowork" / f"{p.name}.plugin", udelad={"evals"})
        print(f"dist/cowork/{p.name}.plugin ({n} filer)")
    with tempfile.TemporaryDirectory() as tmp:
        samlet = pathlib.Path(tmp) / "byg"
        saml(samlet)
        if "--validate" in sys.argv and shutil.which("claude"):
            r = subprocess.run(["claude", "plugin", "validate", str(samlet)], capture_output=True, text=True)
            print(r.stdout.strip().splitlines()[-1] if r.stdout.strip() else r.stderr)
            if "Validation passed" not in r.stdout:
                return 1
        n = zip_mappe(samlet, DIST / "cowork" / "byg.plugin")
        print(f"dist/cowork/byg.plugin – samlet pakke ({n} filer)")
    n = zip_mappe(ROD, DIST / "byg-eksperter.zip", prefix="byg-eksperter")
    print(f"dist/byg-eksperter.zip ({n} filer)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
