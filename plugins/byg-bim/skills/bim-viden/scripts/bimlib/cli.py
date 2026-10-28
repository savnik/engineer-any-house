"""Kommandolinje for bim.py. Udskrifter er korte; detaljer står i filer."""
import argparse
import pathlib
import time


def _byg(a):
    from .byg import byg
    from .spec import SpecFejl, indlaes
    try:
        spec = indlaes(a.spec)
    except SpecFejl as e:
        print(f"SPEC-FEJL ({len(e.fejl)}):")
        for x in e.fejl[:40]:
            print("  - " + x)
        return 1
    sp = pathlib.Path(a.spec).resolve()
    ud = pathlib.Path(a.ud).resolve() if a.ud else sp.parent / "ud" / (sp.parent.name if sp.stem == "model" else sp.stem)
    ud = ud.with_suffix(".ifc")
    t0 = time.time()
    f, b, sv = byg(spec, ud)
    tael = {}
    for v in sv["elementer"].values():
        tael[v["klasse"]] = tael.get(v["klasse"], 0) + 1
    print(f"BYGGET {ud}  ({time.time() - t0:.1f} s, {ud.stat().st_size // 1024} kB, {spec['model']['schema']})")
    print("  " + ", ".join(f"{k[3:]} {n}" for k, n in sorted(tael.items())))
    a_andel = sum(1 for v in sv["elementer"].values() if v.get("kilde") == "A")
    print(f"  kilde A (antagelse): {a_andel} af {len(sv['elementer'])} elementer")
    for e in spec["etager"]:
        rum = [v for v in sv["elementer"].values() if v.get("klasse") == "IfcSpace" and v["etage"] == e["id"]]
        if rum:
            print(f"  {e['id']}: {len(rum)} rum, netto {sum(r.get('areal_m2', 0) for r in rum):.1f} m²")
    for x in b.fejl:
        print("  FEJL: " + x)
    for x in b.adv:
        print("  advarsel: " + x)
    print("  næste: bim.py tjek " + str(ud) + " --tegn")
    return 1 if b.fejl else 0


def _tjek(a):
    from .tjek import tjek
    return tjek(pathlib.Path(a.ifc), ids=a.ids, ud=a.ud, tegn=a.tegn, notat=a.notat)


def _afkod(a):
    from .afkod import skabelon, tjek
    if a.handling == "skabelon":
        return skabelon()
    if not a.fil:
        print("afkod tjek kræver stien til afkodning.yaml")
        return 1
    return tjek(pathlib.Path(a.fil))


def _sammenlign(a):
    from .afkod import AfkodFejl
    from .sammenlign import sammenlign
    try:
        return sammenlign(pathlib.Path(a.ifc), pathlib.Path(a.afkodning), visning=a.visning, ud=a.ud,
                          snithoejde=a.snithoejde, forrige=a.forrige)
    except AfkodFejl as e:
        print(f"AFKODNING-FEJL ({len(e.fejl)}) – ret afkodningen og kør 'afkod tjek' først:")
        for x in e.fejl[:40]:
            print("  - " + x)
        return 1


def _tegn(a):
    from .tegn import tegn
    filer = tegn(pathlib.Path(a.ifc), a.hvad, etage=a.etage, linje=a.linje, side=a.side, fra=a.fra,
                 underlag=a.underlag, kal=a.kal, vis_id=a.id, maal=a.maal, ud=a.ud, snithoejde=a.snithoejde)
    for x in filer:
        print(x)
    return 0


def _eksport(a):
    from .export import export_glb
    return export_glb(pathlib.Path(a.ifc), pathlib.Path(a.ud) if a.ud else None)


def _info(a):
    from .inspicer import info
    return info(pathlib.Path(a.ifc))


def _vis(a):
    from .inspicer import vis
    return vis(pathlib.Path(a.ifc), a.id)


def _find(a):
    from .inspicer import find
    return find(pathlib.Path(a.ifc), a.selector)


def _maal(a):
    from .maal import maal
    return maal(pathlib.Path(a.ifc), a.a, a.b, rum=a.rum, etage_navn=a.etage)


def _diff(a):
    from .inspicer import diff
    return diff(pathlib.Path(a.gammel), pathlib.Path(a.ny))


def _pdf(a):
    from .kilde import pdf
    return pdf(pathlib.Path(a.pdf), a.sider, a.dpi, a.ud, a.oversigt)


def _gitter(a):
    from .kilde import gitter
    return gitter(pathlib.Path(a.billede), a.trin, a.beskaer, a.zoom, a.ud)


def _linjer(a):
    from .kilde import linjer
    return linjer(pathlib.Path(a.billede), a.beskaer, a.andel)


def _skala(a):
    from .kilde import skala
    return skala(a.kal, a.maal)


def _forslag(a):
    from .flet import opret
    return opret(a.hoved, a.navn, a.note, a.ud)


def _flet(a):
    from .flet import flet
    return flet(a.forslag, proev=a.proev, tving=a.tving, note=a.note)


def _ejendomskort(a):
    from .ejendomskort import generer, importer
    return importer(a.model, a.importer) if a.importer else generer(a.model, tjek=a.tjek)


def main(argv):
    p = argparse.ArgumentParser(prog="bim.py")
    sp = p.add_subparsers(dest="cmd", required=True)
    x = sp.add_parser("byg"); x.add_argument("spec"); x.add_argument("--ud"); x.set_defaults(fn=_byg)
    x = sp.add_parser("tjek"); x.add_argument("ifc"); x.add_argument("--ids"); x.add_argument("--ud")
    x.add_argument("--notat", help="modelnotatet: andelen af kilde A skal passe med modellen")
    x.add_argument("--tegn", action="store_true"); x.set_defaults(fn=_tjek)
    x = sp.add_parser("tegn"); x.add_argument("ifc"); x.add_argument("hvad", choices=["plan", "snit", "facade", "3d", "alle"])
    x.add_argument("--etage"); x.add_argument("--linje"); x.add_argument("--side"); x.add_argument("--fra", default="sv")
    x.add_argument("--underlag"); x.add_argument("--kal"); x.add_argument("--id", action="store_true")
    x.add_argument("--maal", action="store_true"); x.add_argument("--ud"); x.add_argument("--snithoejde", type=float, default=1000)
    x.set_defaults(fn=_tegn)
    x = sp.add_parser("afkod"); x.add_argument("handling", choices=["tjek", "skabelon"]); x.add_argument("fil", nargs="?")
    x.set_defaults(fn=_afkod)
    x = sp.add_parser("sammenlign"); x.add_argument("ifc"); x.add_argument("afkodning"); x.add_argument("--visning")
    x.add_argument("--ud"); x.add_argument("--snithoejde", type=float, default=1000)
    x.add_argument("--forrige", help="forrige rundes sammenligningsmappe: marker kun ændrede fliser til gennemgang")
    x.set_defaults(fn=_sammenlign)
    x = sp.add_parser("eksport"); x.add_argument("ifc"); x.add_argument("--ud"); x.set_defaults(fn=_eksport)
    x = sp.add_parser("info"); x.add_argument("ifc"); x.set_defaults(fn=_info)
    x = sp.add_parser("vis"); x.add_argument("ifc"); x.add_argument("id"); x.set_defaults(fn=_vis)
    x = sp.add_parser("find"); x.add_argument("ifc"); x.add_argument("selector"); x.set_defaults(fn=_find)
    x = sp.add_parser("maal"); x.add_argument("ifc"); x.add_argument("a", nargs="?"); x.add_argument("b", nargs="?")
    x.add_argument("--rum"); x.add_argument("--etage"); x.set_defaults(fn=_maal)
    x = sp.add_parser("diff"); x.add_argument("gammel"); x.add_argument("ny"); x.set_defaults(fn=_diff)
    x = sp.add_parser("pdf"); x.add_argument("pdf"); x.add_argument("--sider"); x.add_argument("--dpi", type=int, default=200)
    x.add_argument("--oversigt", action="store_true")
    x.add_argument("--ud"); x.set_defaults(fn=_pdf)
    x = sp.add_parser("gitter"); x.add_argument("billede"); x.add_argument("--trin", type=int, default=100)
    x.add_argument("--beskaer"); x.add_argument("--zoom", type=float, default=1.0); x.add_argument("--ud")
    x.set_defaults(fn=_gitter)
    x = sp.add_parser("linjer"); x.add_argument("billede"); x.add_argument("--beskaer")
    x.add_argument("--andel", type=float, default=0.5); x.set_defaults(fn=_linjer)
    x = sp.add_parser("skala"); x.add_argument("--kal", required=True); x.add_argument("--maal"); x.set_defaults(fn=_skala)
    x = sp.add_parser("forslag"); x.add_argument("hoved"); x.add_argument("navn"); x.add_argument("--note"); x.add_argument("--ud")
    x.set_defaults(fn=_forslag)
    x = sp.add_parser("flet"); x.add_argument("forslag"); x.add_argument("--proev", action="store_true")
    x.add_argument("--tving", action="store_true"); x.add_argument("--note"); x.set_defaults(fn=_flet)
    x = sp.add_parser("ejendomskort"); x.add_argument("model"); x.add_argument("--tjek", action="store_true")
    x.add_argument("--importer"); x.set_defaults(fn=_ejendomskort)
    a = p.parse_args(argv)
    return a.fn(a)
