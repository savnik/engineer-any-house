#!/usr/bin/env python3
"""A/B-test af agenternes effort: kører et plugins evals med agenternes nuværende effort (A) og med en anden (B).

Brug:  python3 scripts/effort_ab.py <plugin> [<plugin> …] [--effort medium] [--runs 3] [--max-cost-usd 20] [-j 3] [--ud <mappe>]
       plugin: sti eller navn under plugins/ (fx byg-vvs). Standard for --ud: en ny midlertidig mappe.

Begge arme er kopier af pluginet. Casenes prompt får en linje, der beder om fagagenten, så det er agenten,
der svarer (ellers svarer hovedmodellen ofte selv, og effort måles ikke). I B-armen er `effort:` i agents/*.md skiftet. Begge arme køres med
`claude plugin eval --ablation none`, og resultatet gemmes som <ud>/<plugin>-A.json og -B.json.
Til sidst vises score og forbrug side om side. Beslutningsregel: B (lavere effort) vælges kun, hvis scoren
holder (højst 0,05 lavere pr. case), og fagagenternes afvisningsrate i rigtige sager ikke stiger
(mål med scripts/usage.py før og efter).

Kræver login og koster tokens: hver arm kører hver case --runs gange.
"""
import json
import pathlib
import re
import shutil
import subprocess
import sys
import tempfile

ROOT = pathlib.Path(__file__).resolve().parent.parent
EFFORT_RE = re.compile(r"^effort:\s*\S+\s*$", re.MULTILINE)


def find_numbers(obj, keys: tuple) -> list:
    """All numeric values under keys that contain one of the words (the JSON format is not fixed)."""
    out = []
    if isinstance(obj, dict):
        for k, v in obj.items():
            if isinstance(v, (int, float)) and not isinstance(v, bool) and any(n in k.lower() for n in keys):
                out.append((k, v))
            else:
                out += find_numbers(v, keys)
    elif isinstance(obj, list):
        for v in obj:
            out += find_numbers(v, keys)
    return out


def summarize_result(path: pathlib.Path) -> dict:
    try:
        d = json.loads(path.read_text(encoding="utf-8"))
    except Exception as e:
        return {"error": str(e)}
    scores = [v for k, v in find_numbers(d, ("score",)) if 0 <= v <= 1]
    cost = [v for k, v in find_numbers(d, ("cost", "usd"))]
    tokens = [v for k, v in find_numbers(d, ("token",))]
    return {"mean_score": round(sum(scores) / len(scores), 3) if scores else None,
            "cost": round(max(cost), 2) if cost else None,   # the largest field is assumed to be the total
            "tokens": max(tokens) if tokens else None}


def run_eval(plugin: pathlib.Path, out: pathlib.Path, name: str, runs: int, max_cost: float, j: int) -> pathlib.Path:
    result = out / f"{name}.json"
    cmd = ["claude", "plugin", "eval", str(plugin), "--ablation", "none", "--runs", str(runs), "--no-publish",
           "--trust-plugin", "--json", str(result), "--report", str(out / f"{name}.html"), "--max-cost-usd", str(max_cost), "-j", str(j)]
    print("→", " ".join(cmd), flush=True)
    subprocess.run(cmd, check=False)
    return result


def main() -> int:
    args = sys.argv[1:]
    def opt(name, default):
        if name in args:
            i = args.index(name)
            v = args[i + 1]
            del args[i:i + 2]
            return v
        return default
    effort = opt("--effort", "medium")
    runs = int(opt("--runs", "3"))
    max_cost = float(opt("--max-cost-usd", "20"))
    j = int(opt("-j", "3"))
    out = pathlib.Path(opt("--ud", "") or tempfile.mkdtemp(prefix="effort-ab-"))
    out.mkdir(parents=True, exist_ok=True)
    if not args:
        print(__doc__)
        return 1
    rows = []
    for a in args:
        plugin = pathlib.Path(a) if pathlib.Path(a).is_dir() else ROOT / "plugins" / a
        if not (plugin / "agents").is_dir():
            print(f"Ingen agents/ i {plugin}")
            return 1
        agent = f"{plugin.name}:{sorted((plugin / 'agents').glob('*.md'))[0].stem}"
        arms = {}
        for arm, arm_effort in (("A", None), ("B", effort)):
            copy_dir = arms[arm] = out / f"{plugin.name}-{arm}"
            shutil.rmtree(copy_dir, ignore_errors=True)
            shutil.copytree(plugin, copy_dir)
            # Dependencies (byg-kontrol) are missing in the eval sandbox, and then the plugin is not loaded at all
            mf = copy_dir / ".claude-plugin" / "plugin.json"
            m = json.loads(mf.read_text(encoding="utf-8"))
            m.pop("dependencies", None)
            mf.write_text(json.dumps(m, ensure_ascii=False, indent=2), encoding="utf-8")
            for f in (copy_dir / "evals").glob("*/prompt.md"):
                t = f.read_text(encoding="utf-8")
                header, _, body = t.partition("\n---\n") if t.startswith("---") else ("", "", t)
                line = f"Brug fagagenten {agent} til at besvare dette.\n\n"
                f.write_text((header + "\n---\n" if header else "") + line + body.lstrip("\n"), encoding="utf-8")
            if arm_effort:
                for f in (copy_dir / "agents").glob("*.md"):
                    f.write_text(EFFORT_RE.sub(f"effort: {arm_effort}", f.read_text(encoding="utf-8"), count=1), encoding="utf-8")
        copy_dir = arms["B"]
        a_result = run_eval(arms["A"], out, f"{plugin.name}-A", runs, max_cost, j)
        b_result = run_eval(copy_dir, out, f"{plugin.name}-B", runs, max_cost, j)
        rows.append((plugin.name, summarize_result(a_result), summarize_result(b_result)))
    print(f"\nResultater i {out}  (A = nuværende effort, B = {effort})")
    print(f"{'plugin':18} {'score A':>8} {'score B':>8} {'$ A':>8} {'$ B':>8} {'tokens A':>10} {'tokens B':>10}")
    for name, a, b in rows:
        print(f"{name:18} {str(a.get('mean_score')):>8} {str(b.get('mean_score')):>8} {str(a.get('cost')):>8} "
              f"{str(b.get('cost')):>8} {str(a.get('tokens')):>10} {str(b.get('tokens')):>10}")
    print("Tjek tallene mod HTML-rapporterne; JSON-felterne findes ved navn, ikke ved et fast skema.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
