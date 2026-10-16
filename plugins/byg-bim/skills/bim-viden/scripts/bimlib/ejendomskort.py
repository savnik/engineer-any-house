"""Ejendomskortet som en del af hovedmodellen (én source of truth).

Husets fakta står i model.yaml under `ejendomskort:` (titel, indledning, afsnit med kolonner, filsti) og `fakta:`
(én række pr. oplysning med id og afsnit). Markdown-kortet genereres herfra og rettes aldrig i hånden.

  ejendomskort <model.yaml>                 → skriv kortet (ejendomskort.fil, relativ til model.yaml)
  ejendomskort <model.yaml> --tjek          → 1, hvis kortet på disken afviger fra modellen
  ejendomskort <model.yaml> --importer <md> → forslag/ejendomskort-import.yaml med kortets indhold (flettes med flet)
"""
import os
import pathlib
import re

import yaml

from .spec import SpecFejl, _laes

GENERERET = "<!-- GENERERET fra {model} med bim.py ejendomskort – RET IKKE HER. Ret fakta i hovedmodellen via forslag + bim.py flet. -->"
NØGLER = {"ID": "id", "Emne": "emne", "Værdi": "vaerdi", "Dato": "dato", "Kilde": "kilde", "Spørgsmål": "spoergsmaal",
          "Hvem afklarer": "hvem", "Sag": "sag", "Tidligere værdi": "tidligere", "Erstattet (dato)": "erstattet",
          "Grund": "grund"}


def _nøgle(overskrift: str) -> str:
    if overskrift in NØGLER:
        return NØGLER[overskrift]
    k = overskrift.lower().translate(str.maketrans({"æ": "ae", "ø": "oe", "å": "aa"}))
    return re.sub(r"[^a-z0-9]+", "_", k).strip("_")


def _afsnit_id(titel: str) -> str:
    return _nøgle(titel.split(":")[0].split("(")[0].strip())


def _celler(linje: str):
    return [c.strip() for c in linje.strip().strip("|").split("|")]


def laes_md(tekst: str):
    """Markdown-kort → (ejendomskort-hoved, fakta). Tabeller i '## '-afsnit; alt andet bevares som tekst."""
    linjer = tekst.rstrip("\n").split("\n")
    linjer = [l for l in linjer if not l.startswith("<!-- GENERERET")]
    titel = linjer[0][2:] if linjer and linjer[0].startswith("# ") else ""
    i, indledning = 1, []
    while i < len(linjer) and not linjer[i].startswith("## "):
        indledning.append(linjer[i])
        i += 1
    afsnit, fakta, brugt = [], [], set()
    while i < len(linjer):
        t = linjer[i][3:]
        a = {"id": _afsnit_id(t), "titel": t}
        i += 1
        før, efter, kolonner, rækker = [], [], None, []
        while i < len(linjer) and not linjer[i].startswith("## "):
            l = linjer[i]
            if l.startswith("|") and kolonner is None:
                kolonner = _celler(l)
                i += 2   # overskrift + |---|
                continue
            if l.startswith("|") and kolonner is not None and not efter:
                rækker.append(_celler(l))
            elif kolonner is None:
                før.append(l)
            else:
                efter.append(l)
            i += 1
        a["kolonner"] = [[k, _nøgle(k)] for k in kolonner or []]
        if any(x.strip() for x in før):
            a["foer"] = før
        while efter and not efter[-1].strip():
            efter.pop()
        if efter:
            a["efter"] = efter
        afsnit.append(a)
        for r in rækker:
            række = {"id": None, "afsnit": a["id"]}
            for (_, k), v in zip(a["kolonner"], r):
                række[k] = v
            rid = række["id"]
            nøgle, n = rid, 2
            while nøgle in brugt:      # samme ID flere gange (fx under "Erstattede oplysninger")
                nøgle = f"{rid}@{n}"
                n += 1
            brugt.add(nøgle)
            række["id"] = nøgle
            fakta.append(række)
    return {"titel": titel, "indledning": indledning, "afsnit": afsnit}, fakta


def skriv_md(ek: dict, fakta: list, model_navn: str = "model.yaml") -> str:
    ud = [GENERERET.format(model=model_navn), f"# {ek.get('titel', '')}"] + list(ek.get("indledning") or [])
    for a in ek.get("afsnit") or []:
        ud.append(f"## {a['titel']}")
        ud += a.get("foer", [])
        kol = a.get("kolonner") or []
        if kol:
            ud.append("| " + " | ".join(k for k, _ in kol) + " |")
            ud.append("|" + "---|" * len(kol))
            for r in fakta:
                if r.get("afsnit") == a["id"]:
                    vis = {**r, "id": str(r["id"]).split("@")[0]}
                    ud.append("| " + " | ".join(str(vis.get(k, "") if vis.get(k) is not None else "") for _, k in kol) + " |")
        ud += a.get("efter", [])
        ud.append("")
    return "\n".join(ud).rstrip("\n") + "\n"


def tjek_fakta(d: dict) -> list:
    fejl = []
    ek, fakta = d.get("ejendomskort"), d.get("fakta")
    if fakta is None and ek is None:
        return fejl
    if not isinstance(ek, dict) or not ek.get("afsnit"):
        return ["ejendomskort: mangler (titel, indledning, afsnit, fil), når der er fakta"]
    afs = {a.get("id") for a in ek["afsnit"]}
    set_ = set()
    for i, r in enumerate(fakta or []):
        if not isinstance(r, dict) or not r.get("id"):
            fejl.append(f"fakta[{i}]: id mangler")
            continue
        if r["id"] in set_:
            fejl.append(f"fakta.{r['id']}: id bruges to gange (brug {r['id']}@2 for en ekstra række)")
        set_.add(r["id"])
        if r.get("afsnit") not in afs:
            fejl.append(f"fakta.{r['id']}: ukendt afsnit '{r.get('afsnit')}' (findes: {', '.join(sorted(afs))})")
    return fejl


def _fil(model: pathlib.Path, d: dict) -> pathlib.Path:
    f = (d.get("ejendomskort") or {}).get("fil")
    if not f:
        raise SpecFejl(["ejendomskort.fil mangler i hovedmodellen"])
    return (model.parent / f).resolve()


def generer(model, tjek=False, stille=False) -> int:
    model = pathlib.Path(model).resolve()
    d = _laes(model)
    if d.get("basis"):
        print("Ejendomskortet genereres kun fra hovedmodellen (ikke fra et forslag)")
        return 1
    fejl = tjek_fakta(d)
    if fejl:
        print("FAKTA-FEJL:\n  - " + "\n  - ".join(fejl))
        return 1
    if not d.get("ejendomskort"):
        return 0
    md = skriv_md(d["ejendomskort"], d.get("fakta") or [], model.name)
    fil = _fil(model, d)
    if tjek:
        ok = fil.exists() and fil.read_text(encoding="utf-8") == md
        print(f"{'OK' if ok else 'AFVIGER'}: {fil} {'svarer til' if ok else 'svarer ikke til'} {model.name}"
              + ("" if ok else " – nogen har rettet i kortet; flyt rettelsen til et forslag, og generér igen"))
        return 0 if ok else 1
    fil.write_text(md, encoding="utf-8")
    if not stille:
        print(f"SKREVET {fil} ({len(d.get('fakta') or [])} fakta)")
    return 0


def importer(model, md) -> int:
    """Kortets indhold → forslag/ejendomskort-import.yaml (flettes med bim.py flet; derefter genereres kortet)."""
    from .flet import _flow, opret
    model, md = pathlib.Path(model).resolve(), pathlib.Path(md).resolve()
    ek, fakta = laes_md(md.read_text(encoding="utf-8"))
    ek = {"fil": os.path.relpath(md, model.parent), **ek}
    orig = md.read_text(encoding="utf-8")
    if skriv_md(ek, fakta).split("\n", 1)[1] != "\n".join(l for l in orig.split("\n") if not l.startswith("<!-- GENERERET")):
        print("STOP: kortet kan ikke gengives 1:1 fra det indlæste – formatet afviger fra tabelformen")
        return 1
    rc = opret(model, "ejendomskort-import", note=f"Import af {md.name} ({len(fakta)} fakta)")
    if rc:
        return rc
    f = model.parent / "forslag" / "ejendomskort-import.yaml"
    linjer = ["ejendomskort:"] + [f"  {k}: {_flow(v)}" for k, v in ek.items() if k != "afsnit"]
    linjer += ["  afsnit:"] + [f"    - {_flow(a)}" for a in ek["afsnit"]]
    linjer += ["fakta:"] + [f"  - {_flow(r)}" for r in fakta]
    f.write_text(f.read_text(encoding="utf-8") + "\n".join(linjer) + "\n", encoding="utf-8")
    print(f"  {len(fakta)} fakta i {len(ek['afsnit'])} afsnit → {f.name}; gengivelse 1:1 kontrolleret")
    return 0
