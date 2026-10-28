#!/usr/bin/env python3
"""bim – byg, kontrollér og tegn IFC-modeller af huse ud fra en modelspec (YAML).

Kør altid med:  python3 bim.py <kommando> ...   (scriptet skifter selv til sit eget Python-miljø)

  opsaet                                   Opretter/opdaterer miljøet (~/.local/share/byg-bim/venv)
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
  find  <fil.ifc> "<selector>"             Fx "IfcWall, /Status=EXISTING/" (ifcopenshell-selector)
  diff  <gammel.ifc> <ny.ifc>              Ændringer mellem to versioner
  pdf   <fil.pdf> --oversigt                Kontaktark over alle sider (find tegningerne først)
  pdf   <fil.pdf> [--sider 1,3-4] [--dpi 200] [--ud <mappe>]   Rasterisér tegninger til PNG
  gitter <billede.png> [--trin 100] [--beskaer x0,y0,x1,y1] [--zoom 2]   Pixelgitter til aflæsning
  linjer <billede.png> --beskaer x0,y0,x1,y1 [--andel 0.5]   Præcise pixelpositioner af streger (vægflader, hjælpelinjer)
  skala --kal "x1,y1,x2,y2=mm[;…]" [--maal "x1,y1,x2,y2;…"]   Målestok fra kendte mål → mål i mm
"""
import os
import pathlib
import subprocess
import sys

HER = pathlib.Path(__file__).resolve().parent
VENV = pathlib.Path(os.environ.get("BYG_BIM_VENV", pathlib.Path.home() / ".local" / "share" / "byg-bim" / "venv"))
VPY = VENV / "bin" / "python"
KRAV = HER / "requirements.txt"


def _i_venv() -> bool:
    return pathlib.Path(sys.prefix).resolve() == VENV.resolve()


def opsaet() -> int:
    if not VPY.exists():
        print(f"Opretter miljø i {VENV} …", flush=True)
        subprocess.run([sys.executable, "-m", "venv", str(VENV)], check=True)
    r = subprocess.run([str(VPY), "-m", "pip", "install", "-q", "--disable-pip-version-check", "-r", str(KRAV)])
    if r.returncode:
        return r.returncode
    out = subprocess.run([str(VPY), "-c", "import ifcopenshell, shapely, matplotlib, pymupdf, yaml, ifctester;"
                          "print('ifcopenshell', ifcopenshell.version)"], capture_output=True, text=True)
    print(out.stdout.strip() or out.stderr.strip())
    return out.returncode


def main() -> int:
    args = sys.argv[1:]
    if not args or args[0] in ("-h", "--help", "hjaelp"):
        print(__doc__)
        return 0
    if args[0] == "opsaet":
        return opsaet()
    if not _i_venv():
        if not VPY.exists():
            print("Miljøet mangler. Kør først:  python3 " + str(pathlib.Path(__file__)) + " opsaet", file=sys.stderr)
            return 2
        os.execv(str(VPY), [str(VPY), str(pathlib.Path(__file__))] + args)
    sys.path.insert(0, str(HER))
    from bimlib import cli
    return cli.main(args)


if __name__ == "__main__":
    sys.exit(main())
