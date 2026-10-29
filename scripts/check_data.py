#!/usr/bin/env python3
"""Data separation: makes sure concrete cases, user data and secrets do not end up in the plugin repo.

Usage:  python3 scripts/check_data.py        (also runs from validate.py and the git pre-commit hook)

Checks:
  1. Structure  – no case folders (byg-sager/), case files, property reports, PDFs or review state in the repo.
  2. Secrets    – no API keys: the local Datafordeler key and generic key patterns.
  3. Private terms – no case IDs from the local knowledge bank and no terms from ~/.config/engineer-any-house/private-termer.txt.
  4. Fingerprints – no text lines (>= 60 characters) copied from the local case folders. Lines that are already in
     the repo on origin/main do not count: they are published and typically come from the plugin itself (a case has
     copied the plugin's text, not the other way round).

The local sources (knowledge bank, case folders, key, private terms) are read only on the developer's machine and do not
exist in the repo. If they are missing (e.g. in CI), checks 3–4 are skipped. Test data (evals, test addresses, fixtures) is allowed.
Secret values are never printed.
"""
import os
import pathlib
import re
import subprocess
import sys

ROOT = pathlib.Path(os.environ.get("BYG_REPO_ROD") or pathlib.Path(__file__).resolve().parent.parent)
HOME = pathlib.Path.home()
CONFIG_DIRS = [HOME / ".config" / "engineer-any-house", HOME / ".config" / "byg-eksperter"]  # old name still read
SKIP = {".git", ".claude", "dist", "__pycache__", "results", "node_modules", ".DS_Store"}  # .claude: local worktrees
TEXT_SUFFIXES = {".md", ".json", ".py", ".txt", ".yml", ".yaml", ".toml", ".sh", ".html", ".csv", ""}

# Files that belong only in a case folder or the plugin's data folder
CASE_FILES = {"projektgrundlag.md", "beslutningslog.md", "kontrollog.md", "budget.md", "tidsplan.md", "risici.md",
             "graenseflader.md", "kontrolplan.md", "erfaringer.md", "status.md", "ejendomsdata.json",
             "ejendomsdata.md", "tilstand.json", "forankringskoe.md", "sager.md"}
CASE_DIRS = {"byg-sager", "fagnotater", "kvalitet", "bilag", "videnbank", "ejendomme"}
KEY_PATTERNS = [re.compile(r"apiKey=[A-Za-z0-9_\-]{20,}"),
                   re.compile(r"(?i)(api[_-]?key|secret|password|token)\s*[:=]\s*['\"]?[A-Za-z0-9_\-]{32,}")]
CASE_ID = re.compile(r"\b\d{4}-\d{2}-\d{2}-[a-z0-9æøå-]+\b")


def repo_files():
    for f in sorted(ROOT.rglob("*")):
        rel = f.relative_to(ROOT)
        if f.is_file() and not SKIP & set(rel.parts):
            yield f, rel


def norm(t):
    return re.sub(r"\s+", " ", re.sub(r"[*_`|#>\-]+", " ", t)).strip().lower()


def local_secrets():
    out = []
    k = HOME / ".config" / "byg-data" / "datafordeler_api_key"
    if k.exists() and k.read_text(encoding="utf-8").strip():
        out.append(("Datafordeler-nøglen", k.read_text(encoding="utf-8").strip()))
    return out


def knowledge_banks():
    return sorted((HOME / ".claude" / "plugins" / "data").glob("*/videnbank"))


def private_terms():
    """Case IDs from the knowledge bank's sager.md + the user's own terms (address, names, companies …)."""
    terms = set()
    for vb in knowledge_banks():
        s = vb / "sager.md"
        if s.exists():
            for line in s.read_text(encoding="utf-8").splitlines():
                cell = line.split("|")[1].strip() if line.startswith("|") and line.count("|") > 2 else ""
                if cell and not set(cell) <= set("-: ") and cell.lower() != "sag-id":
                    terms.add(cell)  # first column = case ID, whatever the name format
            terms |= set(CASE_ID.findall(s.read_text(encoding="utf-8")))
    for f in (k / "private-termer.txt" for k in CONFIG_DIRS):
        if f.exists():
            terms |= {line.strip() for line in f.read_text(encoding="utf-8").splitlines()
                       if line.strip() and not line.startswith("#")}
    return sorted(terms, key=len, reverse=True)


def case_dirs():
    """Paths from the knowledge bank's sager.md (the Sti column) and from ~/.config/engineer-any-house/sagsmapper.txt,
    plus the property cards in byg-sager/ejendomme/ next to the case folders."""
    paths = set()
    for vb in knowledge_banks():
        s = vb / "sager.md"
        if s.exists():
            paths |= {pathlib.Path(m).expanduser() for m in re.findall(r"`(/[^`]+|~/[^`]+)`", s.read_text(encoding="utf-8"))}
    for f in (k / "sagsmapper.txt" for k in CONFIG_DIRS):
        if f.exists():
            paths |= {pathlib.Path(line.strip()).expanduser() for line in f.read_text(encoding="utf-8").splitlines()
                      if line.strip() and not line.startswith("#")}
    paths |= {p.parent / "ejendomme" for p in list(paths)}
    return sorted(p for p in paths if p.is_dir() and ROOT not in (p, *p.parents))


def fingerprints(dirs):
    lines = set()
    for m in dirs:
        for f in m.rglob("*.md"):
            if "bilag" in f.relative_to(m).parts:
                continue  # external and generated documents (e.g. ejendomsdata.md from the plugin's own script)
            rows = f.read_text(encoding="utf-8", errors="ignore").splitlines()
            for i, line in enumerate(rows):
                next_line = rows[i + 1] if i + 1 < len(rows) else ""
                if line.lstrip().startswith("|") and re.match(r"^\s*\|[\s:|-]+\|\s*$", next_line):
                    continue  # table header – typically from a template in the repo
                if line.lstrip().startswith("#"):
                    continue  # heading – typically from a template in the repo (e.g. the solution presentation)
                n = norm(line)
                if len(n) >= 60:
                    lines.add(n)
                if line.lstrip().startswith("|"):
                    # table cells on their own (e.g. a fact in the property card), so a copied value is caught too
                    lines |= {c for c in (norm(x) for x in line.split("|")) if len(c) >= 60}
    return lines


def template_lines():
    """Lines in code blocks in the repo's own .md files (templates). Case files reuse them verbatim, so they are not case text."""
    lines, in_block = set(), False
    for f, _ in repo_files():
        if f.suffix.lower() != ".md":
            continue
        for line in f.read_text(encoding="utf-8", errors="ignore").splitlines():
            if line.lstrip().startswith("```"):
                in_block = not in_block
            elif in_block:
                lines.add(norm(line))
        in_block = False
    return lines


def published_lines(prints):
    """Fingerprints already present in a file on origin/main. Without git or origin/main: none."""
    def git(*a, **kw):
        return subprocess.run(["git", "-C", str(ROOT), *a], capture_output=True, **kw)
    if not prints or git("rev-parse", "--verify", "-q", "origin/main").returncode:
        return set()
    paths = git("ls-tree", "-r", "--name-only", "origin/main", text=True).stdout.split("\n")
    paths = [s for s in paths if s and pathlib.PurePath(s).suffix.lower() in TEXT_SUFFIXES]
    blobs = git("cat-file", "--batch", input="\n".join(f"origin/main:{s}" for s in paths).encode()).stdout
    text = norm(blobs.decode("utf-8", errors="ignore"))
    return {line for line in prints if line in text}


def main() -> int:
    errors = []
    secrets = local_secrets()
    dirs = case_dirs()
    # property IDs (the file name of the property card) are typically an address
    properties = {f.stem for m in dirs if m.name == "ejendomme" for f in m.glob("*.md")}
    terms = sorted(set(private_terms()) | properties, key=len, reverse=True)
    prints = fingerprints(dirs) - template_lines()
    prints -= published_lines(prints)

    for f, rel in repo_files():
        # 1. Structure
        if CASE_DIRS & set(rel.parts[:-1]) and "skabelon" not in rel.parts:
            errors.append(f"{rel}: ligger i en sags-/datamappe – hører ikke hjemme i repoet")
        elif f.name in CASE_FILES and not {"skabelon", "evals", "tests"} & set(rel.parts):
            errors.append(f"{rel}: sagsfil – hører hjemme i en sagsmappe eller pluginets datamappe")
        # docs/img: README images rendered from the repo's own examples (scripts/demo_site.py --images)
        elif (f.suffix.lower() in (".pdf", ".docx", ".xlsx", ".jpg", ".jpeg", ".heic", ".png") and "evals" not in rel.parts
              and rel.parts[:2] != ("docs", "img")):
            errors.append(f"{rel}: bilag/dokument – hører hjemme i sagsmappens bilag/")
        if f.suffix.lower() not in TEXT_SUFFIXES:
            continue
        text = f.read_text(encoding="utf-8", errors="ignore")
        # 2. Secrets (the value is never printed)
        for name, v in secrets:
            if v in text:
                errors.append(f"{rel}: indeholder {name}")
        for m in KEY_PATTERNS:
            for hit in m.finditer(text):
                errors.append(f"{rel}:{text.count(chr(10), 0, hit.start()) + 1}: ligner en API-nøgle/hemmelighed")
        # 3. Private terms
        low = text.lower()
        for t in terms:
            i = low.find(t.lower())
            if i >= 0:
                errors.append(f"{rel}:{text.count(chr(10), 0, i) + 1}: privat term fra sag/videnbank ('{t}')")
        # 4. Fingerprints from case folders
        if prints:
            n = norm(text)
            for line in prints:
                if line in n:
                    errors.append(f"{rel}: indeholder tekst fra en sagsmappe: \"{line[:70]}…\"")

    local_summary = f"{len(terms)} private termer, {len(dirs)} sagsmappe(r), {len(prints)} fingeraftryk"
    for x in errors:
        print("FEJL  " + x)
    print(f"Dataseparation: {len(errors)} fejl ({local_summary})")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
