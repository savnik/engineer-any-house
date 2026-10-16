#!/usr/bin/env python3
"""A/B-test af agenternes effort: kører et plugins evals med agenternes nuværende effort (A) og med en anden (B).

Brug:  python3 scripts/effort_ab.py <plugin> [<plugin> …] [--effort medium] [--runs 3] [--max-cost-usd 20] [--ud <mappe>]
       plugin: sti eller navn under plugins/ (fx byg-vvs). Standard for --ud: en ny midlertidig mappe.

B-armen er en kopi af pluginet, hvor `effort:` i agents/*.md er skiftet. Begge arme køres med
`claude plugin eval --ablation none`, og resultatet gemmes som <ud>/<plugin>-A.json og -B.json.
Til sidst vises score og forbrug side om side. Beslutningsregel: B (lavere effort) vælges kun, hvis scoren
holder (højst 0,05 lavere pr. case), og fagagenternes afvisningsrate i rigtige sager ikke stiger
(mål med scripts/forbrug.py før og efter).

Kræver login og koster tokens: hver arm kører hver case --runs gange.
"""
import json
import pathlib
import re
import shutil
import subprocess
import sys
import tempfile

ROD = pathlib.Path(__file__).resolve().parent.parent
EFFORT_RE = re.compile(r"^effort:\s*\S+\s*$", re.MULTILINE)


def tal(obj, noegler: tuple) -> list:
    """Find alle talværdier under nøgler, der indeholder et af ordene (JSON-formatet er ikke fastlagt)."""
    ud = []
    if isinstance(obj, dict):
        for k, v in obj.items():
            if isinstance(v, (int, float)) and not isinstance(v, bool) and any(n in k.lower() for n in noegler):
                ud.append((k, v))
            else:
                ud += tal(v, noegler)
    elif isinstance(obj, list):
        for v in obj:
            ud += tal(v, noegler)
    return ud


def resume(sti: pathlib.Path) -> dict:
    try:
        d = json.loads(sti.read_text(encoding="utf-8"))
    except Exception as e:
        return {"fejl": str(e)}
    scores = [v for k, v in tal(d, ("score",)) if 0 <= v <= 1]
    cost = [v for k, v in tal(d, ("cost", "usd"))]
    tokens = [v for k, v in tal(d, ("token",))]
    return {"score_gns": round(sum(scores) / len(scores), 3) if scores else None,
            "omkostning": round(max(cost), 2) if cost else None,   # største felt antages at være totalen
            "tokens": max(tokens) if tokens else None}


def koer(plugin: pathlib.Path, ud: pathlib.Path, navn: str, runs: int, loft: float) -> pathlib.Path:
    res = ud / f"{navn}.json"
    cmd = ["claude", "plugin", "eval", str(plugin), "--ablation", "none", "--runs", str(runs), "--no-publish",
           "--trust-plugin", "--json", str(res), "--report", str(ud / f"{navn}.html"), "--max-cost-usd", str(loft)]
    print("→", " ".join(cmd), flush=True)
    subprocess.run(cmd, check=False)
    return res


def main() -> int:
    args = sys.argv[1:]
    def opt(navn, std):
        if navn in args:
            i = args.index(navn)
            v = args[i + 1]
            del args[i:i + 2]
            return v
        return std
    effort = opt("--effort", "medium")
    runs = int(opt("--runs", "3"))
    loft = float(opt("--max-cost-usd", "20"))
    ud = pathlib.Path(opt("--ud", "") or tempfile.mkdtemp(prefix="effort-ab-"))
    ud.mkdir(parents=True, exist_ok=True)
    if not args:
        print(__doc__)
        return 1
    raekker = []
    for a in args:
        plugin = pathlib.Path(a) if pathlib.Path(a).is_dir() else ROD / "plugins" / a
        if not (plugin / "agents").is_dir():
            print(f"Ingen agents/ i {plugin}")
            return 1
        kopi = ud / f"{plugin.name}-effort-{effort}"
        shutil.rmtree(kopi, ignore_errors=True)
        shutil.copytree(plugin, kopi)
        for f in (kopi / "agents").glob("*.md"):
            f.write_text(EFFORT_RE.sub(f"effort: {effort}", f.read_text(encoding="utf-8"), count=1), encoding="utf-8")
        a_res = koer(plugin, ud, f"{plugin.name}-A", runs, loft)
        b_res = koer(kopi, ud, f"{plugin.name}-B", runs, loft)
        raekker.append((plugin.name, resume(a_res), resume(b_res)))
    print(f"\nResultater i {ud}  (A = nuværende effort, B = {effort})")
    print(f"{'plugin':18} {'score A':>8} {'score B':>8} {'$ A':>8} {'$ B':>8} {'tokens A':>10} {'tokens B':>10}")
    for navn, a, b in raekker:
        print(f"{navn:18} {str(a.get('score_gns')):>8} {str(b.get('score_gns')):>8} {str(a.get('omkostning')):>8} "
              f"{str(b.get('omkostning')):>8} {str(a.get('tokens')):>10} {str(b.get('tokens')):>10}")
    print("Tjek tallene mod HTML-rapporterne; JSON-felterne findes ved navn, ikke ved et fast skema.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
