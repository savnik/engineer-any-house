#!/usr/bin/env python3
"""bim – byg, kontrollér og tegn IFC-modeller af huse ud fra en modelspec (YAML).

Kør altid med:  python3 bim.py <kommando> ...   (scriptet skifter selv til sit eget Python-miljø)

  opsaet [--test]                          Opretter/opdaterer miljøet (~/.local/share/byg-bim/venv) fra den låste
                                           requirements.txt (--test: + pytest til scripts/tests)
  byg   <model.yaml> [--ud <fil.ifc>]      Spec → IFC (+ <fil>.byg.json). Standard: <specmappe>/ud/<navn>.ifc
  tjek  <fil.ifc> [--ids <krav.ids>] [--ud <mappe>] [--tegn]
                                           Skema, buildingSMART-regler, geometri, semantik, mængder, IDS
  tegn  <fil.ifc> plan|snit|facade|3d|alle [--etage K] [--linje x1,y1,x2,y2] [--side syd] [--fra sv]
        [--underlag <png> --kal "px,py=x,y;px,py=x,y"] [--id] [--maal] [--ud <mappe>]
  afkod skabelon                           Komplet skabelon til afkodning.yaml
  afkod tjek <afkodning.yaml>              Kontrol af en tegningsafkodning (kalibrering, mål mod tegningen, kæder)
  sammenlign <fil.ifc> <afkodning.yaml> [--visning V1] [--ud <mappe>] [--forrige <forrige rundes mappe>]
                                           Model i tegningens pixelramme + automatisk sammenligning
  forslag <model.yaml> <navn> [--note …] [--ud <mappe>]  Ny forslagsfil forslag/<navn>.yaml (--ud: branch-sagens mappe) oven på hovedmodellen (ret aldrig i
                                           hovedmodellen selv – byg og kontrollér forslaget)
  flet  <forslag.yaml> [--proev] [--note …] [--tving]
                                           Godkendt forslag → hovedmodellen (kun berørte elementer skrives om;
                                           historik/ + flettelog; stopper ved konflikt)
  ejendomskort <model.yaml> [--tjek] [--importer <kort.md>]
                                           Ejendomskortet genereres fra hovedmodellens fakta: (ret aldrig i kortet);
                                           --tjek: afviger kortet?  --importer: kort → forslag/ejendomskort-import.yaml
  info  <fil.ifc>                          Overblik over en (fremmed) model
  vis   <fil.ifc> <id|GlobalId|#step>       Ét element: attributter, egenskaber, materiale, placering
  maal  <fil.ifc|model.yaml> <id> [<id2>] | --rum <navn> | --etage <navn>
                                           Mål i ét kald: væg (længde, tykkelse, højde, inder-/yderflade, åbninger),
                                           rum (indvendige mål, areal, højde), afstand mellem to elementer,
                                           alle vægge på en etage. Altid med kilden (Byg_Kilde). En .yaml bygges først
  find  <fil.ifc> "<selector>"             Fx "IfcWall, /Status=EXISTING/" (ifcopenshell-selector)
  diff  <gammel.ifc> <ny.ifc>              Ændringer mellem to versioner
  pdf   <fil.pdf> --oversigt                Kontaktark over alle sider (find tegningerne først)
  pdf   <fil.pdf> [--sider 1,3-4] [--dpi 200] [--ud <mappe>]   Rasterisér tegninger til PNG
  gitter <billede.png> [--trin 100] [--beskaer x0,y0,x1,y1] [--zoom 2]   Pixelgitter til aflæsning
  linjer <billede.png> --beskaer x0,y0,x1,y1 [--andel 0.5]   Præcise pixelpositioner af streger (vægflader, hjælpelinjer)
  skala --kal "x1,y1,x2,y2=mm[;…]" [--maal "x1,y1,x2,y2;…"]   Målestok fra kendte mål → mål i mm
"""
import pathlib
import sys

from miljoe import Miljoe

HER = pathlib.Path(__file__).resolve().parent
MILJOE = Miljoe("byg-bim", "BYG_BIM_VENV", HER / "requirements.txt",
                "import ifcopenshell, shapely, matplotlib, pymupdf, yaml, ifctester; print('ifcopenshell', ifcopenshell.version)")


def main() -> int:
    args = sys.argv[1:]
    if not args or args[0] in ("-h", "--help", "hjaelp"):
        print(__doc__)
        return 0
    if args[0] == "opsaet":
        return MILJOE.opsaet(HER / "requirements-test.txt" if "--test" in args else None)
    if (r := MILJOE.skift(__file__, args)) is not None:
        return r
    sys.path.insert(0, str(HER))
    from bimlib import cli
    return cli.main(args)


if __name__ == "__main__":
    sys.exit(main())
