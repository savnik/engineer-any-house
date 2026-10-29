#!/usr/bin/env python3
"""fem – FEM-beregning af bærende konstruktioner (bjælker, søjler, rammer, spær) og flader (vægge, dæk som
skalelementer) ud fra en modelspec (YAML).

Kør altid med:  python3 fem.py <kommando> ...   (scriptet skifter selv til sit eget Python-miljø)

  setup                                     Opretter/opdaterer miljøet (~/.local/share/byg-structural/venv) fra den låste
                                            requirements-fem.txt
  template [shells]                         Komplet eksempel på fem.yaml (shells: hus med vægge, dæk og bjælke)
  calc  <fem.yaml> [--out <mappe>] [--no-files] [--set <sti>=<værdi> …]
                                            Analyse: reaktioner, snitkræfter, nedbøjninger og ligevægt pr. kombination
                                            → <out>/<navn>.fem.json (+ resumé på skærmen). Standard-out: <specmappe>/fem/ (eller specmappen selv, hvis den hedder fem)
                                            --set ændrer ét input uden at røre filen (kontrollens egne input),
                                            fx --set lasttilfaelde.Q.laster.0.linjelast=4.0
  result <fem.yaml> [--element <navn>] [--combo <navn>] [--out <mappe>]
                                            Opslag i det gemte resultat (<navn>.fem.json) uden ny beregning. Afviser
                                            resultatet, hvis fem.yaml er ændret siden (spec-sha) eller regnet med --set
  draw  <fem.yaml> [model|deformation|M|V|N|stress|n_u|n_v|plate-moment|displacement|all] [--combo <navn>] [--out <mappe>]
                                            PNG til notatet og til din egen kontrol af modellen (model viser lasterne)
  view  <fem.yaml> [--out <mappe>] [--cdn]  Interaktiv HTML (åbnes i browseren): drej/zoom, laster som pile, vælg
                                            kombination og størrelse (M, V, N, deformation; på flader spænding,
                                            membrankræfter, pladmoment, flytning), skjul flader, værdier ved musen.
                                            --cdn: plotly hentes fra nettet – lille fil til en hjemmeside
  test                                      Selvtest mod håndformler (bjælker, ramme, plade, vægskive, bjælke på væg)

Enheder: længder i m, kræfter i kN, momenter i kNm; profiler og tværsnit i mm; nedbøjning vises i mm.
Akser: x og y vandret, z lodret op. En model med alle y = 0 regnes som plan ramme i x-z-planen.
Alle resultater er OVERSLAG – de skal eftervises af den ansvarlige statiker. Se references/fem.md.
"""
import pathlib
import sys

from environment import Environment

HERE = pathlib.Path(__file__).resolve().parent
ENV = Environment("byg-structural", "BYG_STATIK_VENV", HERE / "requirements-fem.txt",
                  ("import Pynite, plotly, yaml, matplotlib; from importlib.metadata import version;"
                   "print('PyNiteFEA', version('PyNiteFEA'), '· plotly', plotly.__version__)"))


def main() -> int:
    args = sys.argv[1:]
    if not args or args[0] in ("-h", "--help", "help"):
        print(__doc__)
        return 0
    if args[0] == "setup":
        return ENV.setup()
    if (r := ENV.switch(__file__, args)) is not None:
        return r
    sys.path.insert(0, str(HERE))
    from femlib import cli
    return cli.main(args)


if __name__ == "__main__":
    sys.exit(main())
