#!/usr/bin/env python3
"""Demo site for GitHub Pages: the BIM and FEM examples in interactive 3D viewers.

Builds the example house with bim.py, exports it to glTF and shows it in <model-viewer>; computes the FEM example
with fem.py and writes its plotly viewer (plotly.js from the CDN, so the page stays small).

Usage:  python3 scripts/demo_site.py [--out _site]      build the site (CI: .github/workflows/pages.yml)
        python3 scripts/demo_site.py --images            also refresh the README thumbnails in docs/img (needs Playwright)
"""
import argparse
import pathlib
import shutil
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
BIM = ROOT / "plugins/byg-bim/skills/bim-knowledge/scripts/bim.py"
FEM = ROOT / "plugins/byg-structural/skills/structural-knowledge/scripts/fem.py"
BIM_SPEC = ROOT / "plugins/byg-bim/skills/bim-knowledge/assets/eksempel/model.yaml"
FEM_SPEC = ROOT / "plugins/byg-structural/skills/structural-knowledge/assets/fem-example-house.yaml"
VVS_DIAGRAM = ROOT / "plugins/byg-plumbing/skills/plumbing-knowledge/assets/schematic-example-house.svg"
IMG = ROOT / "docs/img"
REPO = "https://github.com/savnik/engineer-any-house"
MODEL_VIEWER = "https://cdn.jsdelivr.net/npm/@google/model-viewer@3.5.0/dist/model-viewer.min.js"

STYLE = """
:root { color-scheme: light dark; --bg: #f6f7f9; --fg: #1d2330; --muted: #5b6474; --card: #fff; --line: #dde1e7; }
@media (prefers-color-scheme: dark) { :root { --bg: #14171c; --fg: #e6e8ec; --muted: #9aa3b2; --card: #1d2128; --line: #2c323c; } }
* { box-sizing: border-box; }
body { margin: 0; font: 16px/1.5 system-ui, sans-serif; background: var(--bg); color: var(--fg); }
header { padding: 16px; border-bottom: 1px solid var(--line); }
header h1 { margin: 0; font-size: 1.15rem; }
header p { margin: 4px 0 0; color: var(--muted); font-size: .9rem; }
a { color: inherit; }
"""

BIM_PAGE = """<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>BIM model – Engineer Any House</title>
<script type="module" src="{mv}"></script>
<style>{style}
body {{ display: flex; flex-direction: column; height: 100vh; }}
model-viewer {{ flex: 1; width: 100%; background: linear-gradient(#dfe7ef, #f6f7f9); }}
@media (prefers-color-scheme: dark) {{ model-viewer {{ background: linear-gradient(#232a33, #14171c); }} }}
</style></head><body>
<header><h1>BIM model of the example house</h1>
<p>The same house as the FEM model: structure, roof windows and the full plumbing and heating installation, with the south and west facades and the south roof face see-through.
IFC4 built with <code>bim.py build</code> from <a href="{repo}/blob/main/plugins/byg-bim/skills/bim-knowledge/assets/eksempel/model.yaml">model.yaml</a>,
exported with <code>bim.py export</code>. Drag to rotate, scroll to zoom. · <a href="../">All examples</a> · <a href="{repo}">GitHub</a></p></header>
<model-viewer src="hus.glb" alt="3D BIM model of the example house" camera-controls touch-action="pan-y"
  camera-orbit="-35deg 75deg auto" shadow-intensity="0.6" exposure="0.85" tone-mapping="neutral" environment-image="neutral"></model-viewer>
</body></html>
"""

INDEX_PAGE = """<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>Engineer Any House – 3D examples</title>
<style>{style}
main {{ max-width: 960px; margin: 0 auto; padding: 16px; display: grid; gap: 16px; grid-template-columns: repeat(auto-fit, minmax(260px, 1fr)); }}
.card {{ background: var(--card); border: 1px solid var(--line); border-radius: 10px; overflow: hidden; text-decoration: none; }}
.card img {{ display: block; width: 100%; aspect-ratio: 16 / 10; object-fit: cover; background: var(--line); }}
.card div {{ padding: 12px 14px; }} .card h2 {{ margin: 0; font-size: 1.05rem; }} .card p {{ margin: 4px 0 0; color: var(--muted); font-size: .9rem; }}
</style></head><body>
<header><h1>Engineer Any House – 3D examples</h1>
<p>Generated in CI from the examples in the repository. · <a href="{repo}">GitHub</a></p></header>
<main>
<a class="card" href="bim/"><img src="bim.png" alt=""><div><h2>BIM model</h2><p>IFC4 house with roof windows, central heating, hot and cold water and drains. Two facades and one roof face are see-through so the inside shows.</p></div></a>
<a class="card" href="plumbing/schematic.svg"><img src="plumbing/schematic.svg" alt="" style="object-fit: contain; background: #fff"><div><h2>Plumbing and heating diagram</h2><p>The same house's central heating, hot and cold water and drains as a schematic, drawn by the VVS agent's method (Danish labels).</p></div></a>
<a class="card" href="fem/"><img src="fem.png" alt=""><div><h2>FEM model</h2><p>The same house, with walls and slabs as shell elements: stresses, forces and deflection per load combination (Danish UI).</p></div></a>
</main></body></html>
"""


def run(*cmd):
    print("$", " ".join(str(c) for c in cmd), flush=True)
    subprocess.run([sys.executable, *map(str, cmd)], check=True)


def build(out: pathlib.Path):
    if out.exists():
        shutil.rmtree(out)
    work = out / "_work"
    (out / "bim").mkdir(parents=True)
    run(BIM, "build", BIM_SPEC, "--out", work / "hus.ifc")
    # south (segment .1) and west (.4) facades on every storey and the south roof face see-through, so the inside shows
    run(BIM, "export", work / "hus.ifc", "--out", out / "bim/hus.glb", "--transparent", "*-YV.1", "*-YV.4", "TAG1.side1")
    (out / "bim/index.html").write_text(BIM_PAGE.format(mv=MODEL_VIEWER, style=STYLE, repo=REPO), encoding="utf-8")
    shutil.copy(FEM_SPEC, work / "fem.yaml")
    run(FEM, "calc", work / "fem.yaml", "--out", work)
    run(FEM, "view", work / "fem.yaml", "--out", work, "--cdn")
    html = sorted(work.glob("*.html"))
    if len(html) != 1:
        sys.exit(f"Forventede én HTML fra fem.py view i {work}, fandt {len(html)}")
    (out / "fem").mkdir()
    shutil.copy(html[0], out / "fem/index.html")
    (out / "plumbing").mkdir()
    shutil.copy(VVS_DIAGRAM, out / "plumbing/schematic.svg")
    (out / "index.html").write_text(INDEX_PAGE.format(style=STYLE, repo=REPO), encoding="utf-8")
    for name in ("bim.png", "fem.png"):
        if (IMG / name).exists():
            shutil.copy(IMG / name, out / name)
    shutil.rmtree(work)
    (out / ".nojekyll").touch()
    print(f"SIDE {out}")


def thumbnails(out: pathlib.Path):
    """Screenshots of the two viewers and the plumbing diagram, served over http (model-viewer won't load a .glb from file://)."""
    import functools
    import http.server
    import threading

    from playwright.sync_api import sync_playwright

    handler = functools.partial(http.server.SimpleHTTPRequestHandler, directory=str(out))
    srv = http.server.ThreadingHTTPServer(("127.0.0.1", 0), handler)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    base = f"http://127.0.0.1:{srv.server_address[1]}"
    IMG.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as p:
        try:
            b = p.chromium.launch()
        except Exception:  # no Playwright browser downloaded: use an installed Chrome
            b = p.chromium.launch(channel="chrome")
        pg = b.new_page(viewport={"width": 1200, "height": 750}, color_scheme="light")
        pg.goto(f"{base}/bim/")
        pg.wait_for_function("document.querySelector('model-viewer')?.loaded === true", timeout=30000)
        pg.wait_for_timeout(1500)
        pg.locator("model-viewer").screenshot(path=str(IMG / "bim.png"))
        pg.goto(f"{base}/fem/")
        pg.wait_for_selector("#fem .main-svg", timeout=30000)
        pg.wait_for_timeout(2500)
        pg.locator("#fem").screenshot(path=str(IMG / "fem.png"))
        pg.set_viewport_size({"width": 1400, "height": 1040})
        pg.goto(f"{base}/plumbing/schematic.svg")
        pg.screenshot(path=str(IMG / "plumbing.png"))
        b.close()
    srv.shutdown()
    for name in ("bim.png", "fem.png"):
        shutil.copy(IMG / name, out / name)
    print(f"BILLEDER {IMG}/bim.png, {IMG}/fem.png, {IMG}/plumbing.png")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out", default=str(ROOT / "_site"))
    ap.add_argument("--images", action="store_true")
    a = ap.parse_args()
    out = pathlib.Path(a.out).resolve()
    build(out)
    if a.images:
        thumbnails(out)


if __name__ == "__main__":
    main()
