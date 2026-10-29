#!/usr/bin/env python3
"""Builds distribution files in dist/.

  dist/cowork/<plugin>.plugin  one per trade plugin and byg-review (without evals) – trades require byg-review
  dist/cowork/byg.plugin       combined Cowork package: all agents, skills and hooks in one plugin named "byg"
  dist/engineer-any-house.zip  the whole repo (marketplace for Claude Code)

Usage: python3 scripts/package.py [--validate]   (--validate runs `claude plugin validate` on the combined package)
"""
import json
import pathlib
import shutil
import subprocess
import sys
import tempfile
import zipfile

ROOT = pathlib.Path(__file__).resolve().parent.parent
DIST = ROOT / "dist"
JUNK = {"__pycache__", ".DS_Store", "results", ".git", "dist"}


def zip_dir(src_dir: pathlib.Path, zip_file: pathlib.Path, prefix: str = "", exclude: set = frozenset()) -> int:
    n = 0
    with zipfile.ZipFile(zip_file, "w", zipfile.ZIP_DEFLATED) as z:
        for f in sorted(src_dir.rglob("*")):
            rel = f.relative_to(src_dir)
            if f.is_dir() or (set(rel.parts) & (JUNK | set(exclude))):
                continue
            z.write(f, (pathlib.PurePosixPath(prefix) / rel.as_posix()).as_posix() if prefix else rel.as_posix())
            n += 1
    return n


def merge_hooks(dst_file: pathlib.Path, new_file: pathlib.Path) -> None:
    a = json.loads(dst_file.read_text(encoding="utf-8"))
    b = json.loads(new_file.read_text(encoding="utf-8"))
    for event, lst in b.get("hooks", {}).items():
        a.setdefault("hooks", {}).setdefault(event, []).extend(lst)
    a["description"] = (a.get("description", "") + " · " + b.get("description", "")).strip(" ·")
    dst_file.write_text(json.dumps(a, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def combine(dst: pathlib.Path) -> None:
    plugins = [p for p in sorted((ROOT / "plugins").iterdir())
               if (p / ".claude-plugin" / "plugin.json").exists() and p.name != "byg-team"]
    version = json.loads((ROOT / "plugins" / "byg" / ".claude-plugin" / "plugin.json").read_text(encoding="utf-8"))["version"]
    for p in plugins:
        for part in ("agents", "skills", "hooks"):
            for f in sorted((p / part).rglob("*")) if (p / part).exists() else []:
                if f.is_dir() or set(f.parts) & JUNK:
                    continue
                rel = f.relative_to(p)
                out = dst / rel
                if rel.as_posix() == "hooks/hooks.json" and out.exists():
                    merge_hooks(out, f)  # several plugins with hooks: merge the events
                    continue
                if out.exists():
                    sys.exit(f"Navnekonflikt i samlet pakke: {rel} ({p.name})")
                out.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(f, out)
    (dst / ".claude-plugin").mkdir(parents=True, exist_ok=True)
    manifest = {
        "name": "byg",
        "displayName": "Byg – projektleder, fagagenter og kvalitetskontrol",
        "version": version,
        "description": "Samlet pakke: projektleder, fagagenter på mesterniveau (vvs, el, murer, ventilation, maler, tømrer, BIM) "
                       "og uafhængig kvalitetskontrol af hver leverance (højst 3 forsøg pr. runde, derefter RCA, forbedring af fagagenten og ny runde).",
        "author": {"name": "Peter Savnik"},
        "license": "MIT",
        "keywords": ["byggeri", "renovering", "projektledelse", "kvalitetskontrol", "danmark"],
    }
    (dst / ".claude-plugin" / "plugin.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    shutil.copy2(ROOT / "README.da.md", dst / "README.md")  # the Cowork package is Danish


def main() -> int:
    if DIST.exists():
        shutil.rmtree(DIST)
    (DIST / "cowork").mkdir(parents=True)
    for p in sorted((ROOT / "plugins").iterdir()):
        if p.name in ("byg", "byg-team") or not (p / ".claude-plugin" / "plugin.json").exists():
            continue
        n = zip_dir(p, DIST / "cowork" / f"{p.name}.plugin", exclude={"evals"})
        print(f"dist/cowork/{p.name}.plugin ({n} filer)")
    with tempfile.TemporaryDirectory() as tmp:
        combined = pathlib.Path(tmp) / "byg"
        combine(combined)
        if "--validate" in sys.argv and shutil.which("claude"):
            r = subprocess.run(["claude", "plugin", "validate", str(combined)], capture_output=True, text=True)
            print(r.stdout.strip().splitlines()[-1] if r.stdout.strip() else r.stderr)
            if "Validation passed" not in r.stdout:
                return 1
        n = zip_dir(combined, DIST / "cowork" / "byg.plugin")
        print(f"dist/cowork/byg.plugin – samlet pakke ({n} filer)")
    n = zip_dir(ROOT, DIST / "engineer-any-house.zip", prefix="engineer-any-house")
    print(f"dist/engineer-any-house.zip ({n} filer)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
