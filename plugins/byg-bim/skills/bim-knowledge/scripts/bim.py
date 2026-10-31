#!/usr/bin/env python3
"""bim – byg, kontrollér og tegn IFC-modeller af huse ud fra en modelspec (YAML).

Kør altid med:  python3 bim.py <kommando> ...   (scriptet skifter selv til sit eget Python-miljø)

  setup [--test]                           Opretter/opdaterer miljøet (~/.local/share/byg-bim/venv) fra den låste
                                           requirements.txt (--test: + pytest til scripts/tests)
  build <model.yaml> [--out <fil.ifc>]     Spec → IFC (+ <fil>.byg.json). Standard: <specmappe>/out/<navn>.ifc
  check <fil.ifc> [--ids <krav.ids>] [--out <mappe>] [--model-note <modelnotat.md>] [--draw]
                                           Skema, buildingSMART-regler, geometri, semantik, mængder, IDS
  draw  <fil.ifc> plan|section|elevation|3d|all [--storey K] [--line x1,y1,x2,y2] [--side syd] [--from sv]
        [--underlay <png> --cal "px,py=x,y;px,py=x,y"] [--id] [--dims] [--cut-height 1000] [--out <mappe>]
  export <fil.ifc> [--out <fil.glb>] [--transparent <id-glob> …] [--alpha 0.25]
                                           3D til webvisning: glTF (.glb) i modellens farver, uden rum og huller;
                                           --transparent gør fx facadevægge gennemsigtige, så konstruktionen ses
  decode template                          Komplet skabelon til decoding.yaml
  decode check <decoding.yaml>            Kontrol af en tegningsafkodning (kalibrering, mål mod tegningen, kæder)
  compare <fil.ifc> <decoding.yaml> [--view V1] [--out <mappe>] [--previous <forrige rundes mappe>]
                                           Model i tegningens pixelramme + automatisk sammenligning
  propose <model.yaml> <navn> [--note …] [--out <mappe>]  Ny forslagsfil proposals/<navn>.yaml (--out: branch-sagens mappe) oven på hovedmodellen (ret aldrig i
                                           hovedmodellen selv – byg og kontrollér forslaget)
  merge <proposal.yaml> [--dry-run] [--note …] [--force]
                                           Godkendt forslag → hovedmodellen (kun berørte elementer skrives om;
                                           history/ + merge-log; stopper ved konflikt)
  property-card <model.yaml> [--check] [--import <kort.md>]
                                           Ejendomskortet genereres fra hovedmodellens fakta: (ret aldrig i kortet);
                                           --check: afviger kortet?  --import: kort → proposals/property-card-import.yaml
  panel <model.yaml> [--tavle <id>] [--out <panel.json>]
                                           Tavlens grupper, RCD'er og kabellængder i el.py's tavleformat (til
                                           el.py panel og electrical-knowledge/scripts/diagram.py)
  info  <fil.ifc>                          Overblik over en (fremmed) model
  show  <fil.ifc> <id|GlobalId|#step>      Ét element: attributter, egenskaber, materiale, placering
  measure <fil.ifc|model.yaml> <id> [<id2>] | --space <navn> | --storey <navn>
                                           Mål i ét kald: væg (længde, tykkelse, højde, inder-/yderflade, åbninger),
                                           rum (indvendige mål, areal, højde), afstand mellem to elementer,
                                           alle vægge på en etage. Altid med kilden (Byg_Kilde). En .yaml bygges først
  find  <fil.ifc> "<selector>"             Fx "IfcWall, /Status=EXISTING/" (ifcopenshell-selector)
  diff  <gammel.ifc> <ny.ifc>              Ændringer mellem to versioner
  pdf   <fil.pdf> --overview               Kontaktark over alle sider (find tegningerne først)
  pdf   <fil.pdf> [--pages 1,3-4] [--dpi 200] [--out <mappe>]   Rasterisér tegninger til PNG
  grid  <billede.png> [--step 100] [--crop x0,y0,x1,y1] [--zoom 2] [--out <mappe>]   Pixelgitter til aflæsning
  lines <billede.png> --crop x0,y0,x1,y1 [--fraction 0.5]   Præcise pixelpositioner af streger (vægflader, hjælpelinjer)
  scale --cal "x1,y1,x2,y2=mm[;…]" [--measured "x1,y1,x2,y2;…"]   Målestok fra kendte mål → mål i mm
"""
import pathlib
import sys

from environment import Environment

HERE = pathlib.Path(__file__).resolve().parent
ENV = Environment("byg-bim", "BYG_BIM_VENV", HERE / "requirements.txt",
                  "import ifcopenshell, shapely, matplotlib, pymupdf, yaml, ifctester; print('ifcopenshell', ifcopenshell.version)")


def main() -> int:
    args = sys.argv[1:]
    if not args or args[0] in ("-h", "--help", "help"):
        print(__doc__)
        return 0
    if args[0] == "setup":
        return ENV.setup(HERE / "requirements-test.txt" if "--test" in args else None)
    if (r := ENV.switch(__file__, args)) is not None:
        return r
    sys.path.insert(0, str(HERE))
    from bimlib import cli
    return cli.main(args)


if __name__ == "__main__":
    sys.exit(main())
