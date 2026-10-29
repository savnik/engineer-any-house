#!/usr/bin/env python3
"""Inserts the shared protocols into the agent files between markers.

One source of truth:
  faelles/protokol.md        → trade agents  (FÆLLES-PROTOKOL markers)
  faelles/kontrolprotokol.md → review agents (KONTROL-PROTOKOL markers)

Run after every change in faelles/:  python3 scripts/sync_protocol.py [--check]
--staged checks the content in the git index (what gets committed); used by scripts/hooks/pre-commit.
"""
import fnmatch
import pathlib
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
BLOCKS = [
    ("protokol.md", "FÆLLES-PROTOKOL", "redigér faelles/protokol.md"),
    ("kontrolprotokol.md", "KONTROL-PROTOKOL", "redigér faelles/kontrolprotokol.md"),
]


def markers(name: str, hint: str) -> tuple[str, str]:
    return (f"<!-- {name}:START (genereres af scripts/sync_protocol.py – {hint}) -->",
            f"<!-- {name}:SLUT -->")


def candidates() -> list[pathlib.Path]:
    files = list(ROOT.glob("plugins/*/agents/*.md")) + list(ROOT.glob("skabelon/**/agents/*.md"))
    return sorted(set(files))


def staged(rel: str) -> str | None:
    """Return the staged (index) text of a repo-relative path, or None if it is not in the index."""
    r = subprocess.run(["git", "-C", str(ROOT), "show", f":{rel}"], capture_output=True)
    return r.stdout.decode("utf-8") if r.returncode == 0 else None


def staged_candidates() -> list[str]:
    r = subprocess.run(["git", "-C", str(ROOT), "ls-files"], capture_output=True, text=True, check=True)
    return sorted(f for f in r.stdout.splitlines()
                  if fnmatch.fnmatch(f, "plugins/*/agents/*.md") or fnmatch.fnmatch(f, "skabelon/*agents/*.md"))


def main() -> int:
    if "--staged" in sys.argv:
        return main_staged()
    check = "--check" in sys.argv
    mismatches = 0
    for src_name, name, hint in BLOCKS:
        start, end = markers(name, hint)
        source_text = (ROOT / "faelles" / src_name).read_text(encoding="utf-8").strip()
        block = f"{start}\n{source_text}\n{end}"
        for path in candidates():
            text = path.read_text(encoding="utf-8")
            if start not in text or end not in text:
                continue
            before, rest = text.split(start, 1)
            _, after = rest.split(end, 1)
            new = before + block + after
            if new != text:
                mismatches += 1
                if check:
                    print(f"UDE AF SYNK ({name}): {path.relative_to(ROOT)}")
                else:
                    path.write_text(new, encoding="utf-8")
                    print(f"opdateret ({name}): {path.relative_to(ROOT)}")
    if check and mismatches:
        return 1
    print("Protokoller i synk.")
    return 0


def main_staged() -> int:
    """Like --check, but on the index, so a commit cannot hold protocols out of sync."""
    mismatches = 0
    for src_name, name, hint in BLOCKS:
        start, end = markers(name, hint)
        source_text = (staged(f"faelles/{src_name}") or "").strip()
        for rel in staged_candidates():
            text = staged(rel)
            if text is None or start not in text or end not in text:
                continue
            if text.split(start, 1)[1].split(end, 1)[0] != f"\n{source_text}\n":
                mismatches += 1
                print(f"UDE AF SYNK i indekset ({name}): {rel}")
    return 1 if mismatches else 0


if __name__ == "__main__":
    sys.exit(main())
