#!/usr/bin/env python3
"""Kører et fag-plugins evals, så pluginet faktisk indlæses.

Brug:  python3 scripts/eval_trade.py <plugin> [flere argumenter til claude plugin eval …]
       fx  python3 scripts/eval_trade.py byg-vvs --runs 2

Fag-plugins afhænger af byg-kontrol, som ikke findes i eval-sandkassen. Så indlæser Claude Code slet ikke
pluginet, og evalen tester kun den bare model (uddelegerings-graderen fejler altid). Scriptet kører derfor
evalen på en midlertidig kopi uden "dependencies" i plugin.json. Kontrol-hooken er ikke med i kørslen.
Kræver login og koster tokens.
"""
import json
import pathlib
import shutil
import subprocess
import sys
import tempfile

ROD = pathlib.Path(__file__).resolve().parent.parent


def main() -> int:
    if len(sys.argv) < 2 or sys.argv[1] in ("-h", "--help"):
        print(__doc__)
        return 1
    plugin = pathlib.Path(sys.argv[1]) if pathlib.Path(sys.argv[1]).is_dir() else ROD / "plugins" / sys.argv[1]
    if not (plugin / ".claude-plugin" / "plugin.json").is_file():
        print(f"Intet plugin i {plugin}")
        return 1
    with tempfile.TemporaryDirectory(prefix="eval-fag-") as tmp:
        kopi = pathlib.Path(tmp) / plugin.name
        shutil.copytree(plugin, kopi, ignore=shutil.ignore_patterns("__pycache__", "results"))
        mf = kopi / ".claude-plugin" / "plugin.json"
        m = json.loads(mf.read_text(encoding="utf-8"))
        m.pop("dependencies", None)
        mf.write_text(json.dumps(m, ensure_ascii=False, indent=2), encoding="utf-8")
        ekstra = sys.argv[2:]
        if "--report" not in ekstra:
            ekstra += ["--report", str(pathlib.Path(tempfile.gettempdir()) / f"eval-{plugin.name}.html")]
        return subprocess.run(["claude", "plugin", "eval", str(kopi), "--trust-plugin", *ekstra]).returncode


if __name__ == "__main__":
    sys.exit(main())
