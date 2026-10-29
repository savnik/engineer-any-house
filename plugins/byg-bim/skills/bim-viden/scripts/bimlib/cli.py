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
    out = pathlib.Path(a.ud).resolve() if a.ud else sp.parent / "ud" / (sp.parent.name if sp.stem == "model" else sp.stem)
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
    print("  næste: bim.py tjek " + str(out) + " --tegn")
    return 1 if b.errors else 0


def _check(a):
    from .check import check
    return check(pathlib.Path(a.ifc), ids=a.ids, out=a.ud, draw=a.tegn, note=a.notat)


def _decode(a):
    from .decode import template, check
    if a.handling == "skabelon":
        return template()
    if not a.fil:
        print("afkod tjek kræver stien til afkodning.yaml")
        return 1
    return check(pathlib.Path(a.fil))


def _compare(a):
    from .decode import DecodeError
    from .compare import compare
    try:
        return compare(pathlib.Path(a.ifc), pathlib.Path(a.afkodning), view=a.visning, out=a.ud,
                       cut_height=a.snithoejde, previous=a.forrige)
    except DecodeError as e:
        print(f"AFKODNING-FEJL ({len(e.errors)}) – ret afkodningen og kør 'afkod tjek' først:")
        for x in e.errors[:40]:
            print("  - " + x)
        return 1


def _draw(a):
    from .draw import draw
    files = draw(pathlib.Path(a.ifc), a.hvad, storey=a.etage, line=a.linje, side=a.side, view_from=a.fra,
                 underlay=a.underlag, cal=a.kal, show_id=a.id, dims=a.maal, out=a.ud, cut_height=a.snithoejde)
    for x in files:
        print(x)
    return 0


def _export(a):
    from .export import export_glb
    return export_glb(pathlib.Path(a.ifc), pathlib.Path(a.ud) if a.ud else None, a.gennemsigtig or (), a.alfa)


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
    return measure(pathlib.Path(a.ifc), a.a, a.b, room=a.rum, storey_name=a.etage)


def _diff(a):
    from .inspection import diff
    return diff(pathlib.Path(a.gammel), pathlib.Path(a.ny))


def _pdf(a):
    from .source import pdf
    return pdf(pathlib.Path(a.pdf), a.sider, a.dpi, a.ud, a.oversigt)


def _grid(a):
    from .source import grid
    return grid(pathlib.Path(a.billede), a.trin, a.beskaer, a.zoom, a.ud)


def _lines(a):
    from .source import lines
    return lines(pathlib.Path(a.billede), a.beskaer, a.andel)


def _scale(a):
    from .source import scale
    return scale(a.kal, a.maal)


def _proposal(a):
    from .merge import create
    return create(a.hoved, a.navn, a.note, a.ud)


def _merge(a):
    from .merge import merge
    return merge(a.forslag, dry_run=a.proev, force=a.tving, note=a.note)


def _property_card(a):
    from .property_card import generate, import_card
    return import_card(a.model, a.importer) if a.importer else generate(a.model, check=a.tjek)


def main(argv):
    p = argparse.ArgumentParser(prog="bim.py")
    sp = p.add_subparsers(dest="cmd", required=True)
    x = sp.add_parser("byg"); x.add_argument("spec"); x.add_argument("--ud"); x.set_defaults(fn=_build)
    x = sp.add_parser("tjek"); x.add_argument("ifc"); x.add_argument("--ids"); x.add_argument("--ud")
    x.add_argument("--notat", help="modelnotatet: andelen af kilde A skal passe med modellen")
    x.add_argument("--tegn", action="store_true"); x.set_defaults(fn=_check)
    x = sp.add_parser("tegn"); x.add_argument("ifc"); x.add_argument("hvad", choices=["plan", "snit", "facade", "3d", "alle"])
    x.add_argument("--etage"); x.add_argument("--linje"); x.add_argument("--side"); x.add_argument("--fra", default="sv")
    x.add_argument("--underlag"); x.add_argument("--kal"); x.add_argument("--id", action="store_true")
    x.add_argument("--maal", action="store_true"); x.add_argument("--ud"); x.add_argument("--snithoejde", type=float, default=1000)
    x.set_defaults(fn=_draw)
    x = sp.add_parser("afkod"); x.add_argument("handling", choices=["tjek", "skabelon"]); x.add_argument("fil", nargs="?")
    x.set_defaults(fn=_decode)
    x = sp.add_parser("sammenlign"); x.add_argument("ifc"); x.add_argument("afkodning"); x.add_argument("--visning")
    x.add_argument("--ud"); x.add_argument("--snithoejde", type=float, default=1000)
    x.add_argument("--forrige", help="forrige rundes sammenligningsmappe: marker kun ændrede fliser til gennemgang")
    x.set_defaults(fn=_compare)
    x = sp.add_parser("eksport"); x.add_argument("ifc"); x.add_argument("--ud")
    x.add_argument("--gennemsigtig", nargs="+", metavar="ID", help="elementer (id/Tag, glob som 'S-YV.1' eller '*-YV.4') der gøres gennemsigtige")
    x.add_argument("--alfa", type=float, default=0.25, help="dækkevne for --gennemsigtig (0–1, standard 0.25)")
    x.set_defaults(fn=_export)
    x = sp.add_parser("info"); x.add_argument("ifc"); x.set_defaults(fn=_info)
    x = sp.add_parser("vis"); x.add_argument("ifc"); x.add_argument("id"); x.set_defaults(fn=_show)
    x = sp.add_parser("find"); x.add_argument("ifc"); x.add_argument("selector"); x.set_defaults(fn=_find)
    x = sp.add_parser("maal"); x.add_argument("ifc"); x.add_argument("a", nargs="?"); x.add_argument("b", nargs="?")
    x.add_argument("--rum"); x.add_argument("--etage"); x.set_defaults(fn=_measure)
    x = sp.add_parser("diff"); x.add_argument("gammel"); x.add_argument("ny"); x.set_defaults(fn=_diff)
    x = sp.add_parser("pdf"); x.add_argument("pdf"); x.add_argument("--sider"); x.add_argument("--dpi", type=int, default=200)
    x.add_argument("--oversigt", action="store_true")
    x.add_argument("--ud"); x.set_defaults(fn=_pdf)
    x = sp.add_parser("gitter"); x.add_argument("billede"); x.add_argument("--trin", type=int, default=100)
    x.add_argument("--beskaer"); x.add_argument("--zoom", type=float, default=1.0); x.add_argument("--ud")
    x.set_defaults(fn=_grid)
    x = sp.add_parser("linjer"); x.add_argument("billede"); x.add_argument("--beskaer")
    x.add_argument("--andel", type=float, default=0.5); x.set_defaults(fn=_lines)
    x = sp.add_parser("skala"); x.add_argument("--kal", required=True); x.add_argument("--maal"); x.set_defaults(fn=_scale)
    x = sp.add_parser("forslag"); x.add_argument("hoved"); x.add_argument("navn"); x.add_argument("--note"); x.add_argument("--ud")
    x.set_defaults(fn=_proposal)
    x = sp.add_parser("flet"); x.add_argument("forslag"); x.add_argument("--proev", action="store_true")
    x.add_argument("--tving", action="store_true"); x.add_argument("--note"); x.set_defaults(fn=_merge)
    x = sp.add_parser("ejendomskort"); x.add_argument("model"); x.add_argument("--tjek", action="store_true")
    x.add_argument("--importer"); x.set_defaults(fn=_property_card)
    a = p.parse_args(argv)
    return a.fn(a)
