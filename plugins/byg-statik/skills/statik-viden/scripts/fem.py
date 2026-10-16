#!/usr/bin/env python3
"""fem – FEM-beregning af bærende konstruktioner (bjælker, søjler, rammer, spær) og flader (vægge, dæk som
skalelementer) ud fra en modelspec (YAML).

Kør altid med:  python3 fem.py <kommando> ...   (scriptet skifter selv til sit eget Python-miljø)

  opsaet                                    Opretter/opdaterer miljøet (~/.local/share/byg-statik/venv)
  skabelon [flader]                         Komplet eksempel på fem.yaml (flader: hus med vægge, dæk og bjælke)
  regn  <fem.yaml> [--ud <mappe>] [--ingen-filer] [--saet <sti>=<værdi> …]
                                            Analyse: reaktioner, snitkræfter, nedbøjninger og ligevægt pr. kombination
                                            → <ud>/<navn>.fem.json (+ resumé på skærmen). Standard-ud: <specmappe>/fem/ (eller specmappen selv, hvis den hedder fem)
                                            --saet ændrer ét input uden at røre filen (kontrollens egne input),
                                            fx --saet lasttilfaelde.Q.laster.0.linjelast=4.0
  tegn  <fem.yaml> [model|deformation|M|V|N|spaending|n_u|n_v|pladmoment|flytning|alle] [--kombi <navn>] [--ud <mappe>]
                                            PNG til notatet og til din egen kontrol af modellen (model viser lasterne)
  vis   <fem.yaml> [--ud <mappe>]           Interaktiv HTML (åbnes i browseren): drej/zoom, laster som pile, vælg
                                            kombination og størrelse (M, V, N, deformation; på flader spænding,
                                            membrankræfter, pladmoment, flytning), skjul flader, værdier ved musen
  test                                      Selvtest mod håndformler (bjælker, ramme, plade, vægskive, bjælke på væg)

Enheder: længder i m, kræfter i kN, momenter i kNm; profiler og tværsnit i mm; nedbøjning vises i mm.
Akser: x og y vandret, z lodret op. En model med alle y = 0 regnes som plan ramme i x-z-planen.
Alle resultater er OVERSLAG – de skal eftervises af den ansvarlige statiker. Se references/fem.md.
"""
import os
import pathlib
import subprocess
import sys

HER = pathlib.Path(__file__).resolve().parent
VENV = pathlib.Path(os.environ.get("BYG_STATIK_VENV", pathlib.Path.home() / ".local" / "share" / "byg-statik" / "venv"))
VPY = VENV / "bin" / "python"
KRAV = HER / "requirements-fem.txt"


def _i_venv() -> bool:
    return pathlib.Path(sys.prefix).resolve() == VENV.resolve()


def opsaet() -> int:
    if not VPY.exists():
        print(f"Opretter miljø i {VENV} …", flush=True)
        subprocess.run([sys.executable, "-m", "venv", str(VENV)], check=True)
    r = subprocess.run([str(VPY), "-m", "pip", "install", "-q", "--disable-pip-version-check", "-r", str(KRAV)])
    if r.returncode:
        return r.returncode
    out = subprocess.run([str(VPY), "-c", "import Pynite, plotly, yaml, matplotlib; from importlib.metadata import version;"
                          "print('PyNiteFEA', version('PyNiteFEA'), '· plotly', plotly.__version__)"],
                         capture_output=True, text=True)
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
    from femlib import cli
    return cli.main(args)


if __name__ == "__main__":
    sys.exit(main())
