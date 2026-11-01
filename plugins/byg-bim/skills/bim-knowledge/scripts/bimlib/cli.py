"""Command line for bim.py. Printouts are short; details go to files."""
import argparse
import pathlib
import time


def _build(a):
    from .build import build
    from .spec import SpecError, load
    try:
        spec = load(a.spec)
    except SpecError as e:
        print(f"SPEC-FEJL ({len(e.errors)}):")
        for x in e.errors[:40]:
            print("  - " + x)
        return 1
    sp = pathlib.Path(a.spec).resolve()
    out = pathlib.Path(a.out).resolve() if a.out else sp.parent / "out" / (sp.parent.name if sp.stem == "model" else sp.stem)
    out = out.with_suffix(".ifc")
    t0 = time.time()
    f, b, sv = build(spec, out)
    counts = {}
    for v in sv["elementer"].values():
        counts[v["klasse"]] = counts.get(v["klasse"], 0) + 1
    print(f"BYGGET {out}  ({time.time() - t0:.1f} s, {out.stat().st_size // 1024} kB, {spec['model']['schema']})")
    print("  " + ", ".join(f"{k[3:]} {n}" for k, n in sorted(counts.items())))
    a_share = sum(1 for v in sv["elementer"].values() if v.get("kilde") == "A")
    print(f"  kilde A (antagelse): {a_share} af {len(sv['elementer'])} elementer")
    for e in spec["etager"]:
        spaces = [v for v in sv["elementer"].values() if v.get("klasse") == "IfcSpace" and v["etage"] == e["id"]]
        if spaces:
            print(f"  {e['id']}: {len(spaces)} rum, netto {sum(r.get('areal_m2', 0) for r in spaces):.1f} m²")
    for x in b.errors:
        print("  FEJL: " + x)
    for x in b.warnings:
        print("  advarsel: " + x)
    print("  næste: bim.py check " + str(out) + " --draw")
    return 1 if b.errors else 0


def _check(a):
    from .check import check
    return check(pathlib.Path(a.ifc), ids=a.ids, out=a.out, draw=a.draw, note=a.model_note)


def _decode(a):
    from .decode import template, check
    if a.action == "template":
        return template()
    if not a.file:
        print("decode check kræver stien til decoding.yaml")
        return 1
    return check(pathlib.Path(a.file))


def _compare(a):
    from .decode import DecodeError
    from .compare import compare
    try:
        return compare(pathlib.Path(a.ifc), pathlib.Path(a.decoding), view=a.view, out=a.out,
                       cut_height=a.cut_height, previous=a.previous)
    except DecodeError as e:
        print(f"AFKODNING-FEJL ({len(e.errors)}) – ret afkodningen og kør 'decode check' først:")
        for x in e.errors[:40]:
            print("  - " + x)
        return 1


def _draw(a):
    from .draw import draw
    files = draw(pathlib.Path(a.ifc), a.what, storey=a.storey, line=a.line, side=a.side, view_from=a.from_,
                 underlay=a.underlay, cal=a.cal, show_id=a.id, dims=a.dims, out=a.out, cut_height=a.cut_height)
    for x in files:
        print(x)
    return 0


def _export(a):
    from .export import export_glb
    return export_glb(pathlib.Path(a.ifc), pathlib.Path(a.out) if a.out else None, a.transparent or (), a.alpha)


def _info(a):
    from .inspection import info
    return info(pathlib.Path(a.ifc))


def _show(a):
    from .inspection import show
    return show(pathlib.Path(a.ifc), a.id)


def _find(a):
    from .inspection import find
    return find(pathlib.Path(a.ifc), a.selector)


def _measure(a):
    from .measure import measure
    return measure(pathlib.Path(a.ifc), a.a, a.b, room=a.space, storey_name=a.storey)


def _elplan(a):
    from .elplan import elplan
    return elplan(pathlib.Path(a.ifc), a.out)


def _diff(a):
    from .inspection import diff
    return diff(pathlib.Path(a.old), pathlib.Path(a.new))


def _pdf(a):
    from .source import pdf
    return pdf(pathlib.Path(a.pdf), a.pages, a.dpi, a.out, a.overview)


def _grid(a):
    from .source import grid
    return grid(pathlib.Path(a.image), a.step, a.crop, a.zoom, a.out)


def _lines(a):
    from .source import lines
    return lines(pathlib.Path(a.image), a.crop, a.fraction)


def _scale(a):
    from .source import scale
    return scale(a.cal, a.measured)


def _proposal(a):
    from .merge import create
    return create(a.head, a.name, a.note, a.out)


def _merge(a):
    from .merge import merge
    return merge(a.proposal, dry_run=a.dry_run, force=a.force, note=a.note)


def _property_card(a):
    from .property_card import generate, import_card
    return import_card(a.model, a.import_) if a.import_ else generate(a.model, check=a.check)


def main(argv):
    p = argparse.ArgumentParser(prog="bim.py")
    sp = p.add_subparsers(dest="cmd", required=True)
    x = sp.add_parser("build"); x.add_argument("spec"); x.add_argument("--out"); x.set_defaults(fn=_build)
    x = sp.add_parser("check"); x.add_argument("ifc"); x.add_argument("--ids"); x.add_argument("--out")
    x.add_argument("--model-note", help="modelnotatet: andelen af kilde A skal passe med modellen")
    x.add_argument("--draw", action="store_true"); x.set_defaults(fn=_check)
    x = sp.add_parser("draw"); x.add_argument("ifc"); x.add_argument("what", choices=["plan", "section", "elevation", "3d", "all"])
    x.add_argument("--storey"); x.add_argument("--line"); x.add_argument("--side")
    x.add_argument("--from", dest="from_", default="sv")
    x.add_argument("--underlay"); x.add_argument("--cal"); x.add_argument("--id", action="store_true")
    x.add_argument("--dims", action="store_true"); x.add_argument("--out"); x.add_argument("--cut-height", type=float, default=1000)
    x.set_defaults(fn=_draw)
    x = sp.add_parser("decode"); x.add_argument("action", choices=["check", "template"]); x.add_argument("file", nargs="?")
    x.set_defaults(fn=_decode)
    x = sp.add_parser("compare"); x.add_argument("ifc"); x.add_argument("decoding"); x.add_argument("--view")
    x.add_argument("--out"); x.add_argument("--cut-height", type=float, default=1000)
    x.add_argument("--previous", help="forrige rundes sammenligningsmappe: marker kun ændrede fliser til gennemgang")
    x.set_defaults(fn=_compare)
    x = sp.add_parser("export"); x.add_argument("ifc"); x.add_argument("--out")
    x.add_argument("--transparent", nargs="+", metavar="ID", help="elementer (id/Tag, glob som 'S-YV.1' eller '*-YV.4') der gøres gennemsigtige")
    x.add_argument("--alpha", type=float, default=0.25, help="dækkevne for --transparent (0–1, standard 0.25)")
    x.set_defaults(fn=_export)
    x = sp.add_parser("info"); x.add_argument("ifc"); x.set_defaults(fn=_info)
    x = sp.add_parser("show"); x.add_argument("ifc"); x.add_argument("id"); x.set_defaults(fn=_show)
    x = sp.add_parser("find"); x.add_argument("ifc"); x.add_argument("selector"); x.set_defaults(fn=_find)
    x = sp.add_parser("measure"); x.add_argument("ifc"); x.add_argument("a", nargs="?"); x.add_argument("b", nargs="?")
    x.add_argument("--space"); x.add_argument("--storey"); x.set_defaults(fn=_measure)
    x = sp.add_parser("elplan"); x.add_argument("ifc"); x.add_argument("--out"); x.set_defaults(fn=_elplan)
    x = sp.add_parser("diff"); x.add_argument("old"); x.add_argument("new"); x.set_defaults(fn=_diff)
    x = sp.add_parser("pdf"); x.add_argument("pdf"); x.add_argument("--pages"); x.add_argument("--dpi", type=int, default=200)
    x.add_argument("--overview", action="store_true")
    x.add_argument("--out"); x.set_defaults(fn=_pdf)
    x = sp.add_parser("grid"); x.add_argument("image"); x.add_argument("--step", type=int, default=100)
    x.add_argument("--crop"); x.add_argument("--zoom", type=float, default=1.0); x.add_argument("--out")
    x.set_defaults(fn=_grid)
    x = sp.add_parser("lines"); x.add_argument("image"); x.add_argument("--crop")
    x.add_argument("--fraction", type=float, default=0.5); x.set_defaults(fn=_lines)
    x = sp.add_parser("scale"); x.add_argument("--cal", required=True); x.add_argument("--measured"); x.set_defaults(fn=_scale)
    x = sp.add_parser("propose"); x.add_argument("head"); x.add_argument("name"); x.add_argument("--note"); x.add_argument("--out")
    x.set_defaults(fn=_proposal)
    x = sp.add_parser("merge"); x.add_argument("proposal"); x.add_argument("--dry-run", action="store_true")
    x.add_argument("--force", action="store_true"); x.add_argument("--note"); x.set_defaults(fn=_merge)
    x = sp.add_parser("property-card"); x.add_argument("model"); x.add_argument("--check", action="store_true")
    x.add_argument("--import", dest="import_"); x.set_defaults(fn=_property_card)
    a = p.parse_args(argv)
    return a.fn(a)
