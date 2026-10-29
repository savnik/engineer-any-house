"""The property card as part of the main model (one source of truth).

The house's facts live in model.yaml under `ejendomskort:` (titel, indledning, afsnit with kolonner, file path) and `fakta:`
(one row per fact with id and afsnit). The Markdown card is generated from there and is never edited by hand.

  property-card <model.yaml>                → write the card (ejendomskort.fil, relative to model.yaml)
  property-card <model.yaml> --check        → 1 if the card on disk differs from the model
  property-card <model.yaml> --import <md>  → forslag/ejendomskort-import.yaml with the card's content (merged with merge)
"""
import os
import pathlib
import re

from .spec import SpecError, _read

GENERATED_BANNER = "<!-- GENERERET fra {model} med bim.py property-card – RET IKKE HER. Ret fakta i hovedmodellen via forslag + bim.py merge. -->"
HEADER_KEYS = {"ID": "id", "Emne": "emne", "Værdi": "vaerdi", "Dato": "dato", "Kilde": "kilde", "Spørgsmål": "spoergsmaal",
          "Hvem afklarer": "hvem", "Sag": "sag", "Tidligere værdi": "tidligere", "Erstattet (dato)": "erstattet",
          "Grund": "grund"}


def _key(heading: str) -> str:
    if heading in HEADER_KEYS:
        return HEADER_KEYS[heading]
    k = heading.lower().translate(str.maketrans({"æ": "ae", "ø": "oe", "å": "aa"}))
    return re.sub(r"[^a-z0-9]+", "_", k).strip("_")


def _section_id(title: str) -> str:
    return _key(title.split(":")[0].split("(")[0].strip())


def _cells(line: str):
    return [c.strip() for c in line.strip().strip("|").split("|")]


def read_md(text: str):
    """Markdown card → (ejendomskort header, fakta). Tables in '## ' sections; everything else is kept as text."""
    lines = text.rstrip("\n").split("\n")
    lines = [l for l in lines if not l.startswith("<!-- GENERERET")]
    title = lines[0][2:] if lines and lines[0].startswith("# ") else ""
    i, intro = 1, []
    while i < len(lines) and not lines[i].startswith("## "):
        intro.append(lines[i])
        i += 1
    sections, facts, used = [], [], set()
    while i < len(lines):
        t = lines[i][3:]
        a = {"id": _section_id(t), "titel": t}
        i += 1
        before, after, columns, rows = [], [], None, []
        while i < len(lines) and not lines[i].startswith("## "):
            l = lines[i]
            if l.startswith("|") and columns is None:
                columns = _cells(l)
                i += 2   # header + |---|
                continue
            if l.startswith("|") and columns is not None and not after:
                rows.append(_cells(l))
            elif columns is None:
                before.append(l)
            else:
                after.append(l)
            i += 1
        a["kolonner"] = [[k, _key(k)] for k in columns or []]
        if any(x.strip() for x in before):
            a["foer"] = before
        while after and not after[-1].strip():
            after.pop()
        if after:
            a["efter"] = after
        sections.append(a)
        for r in rows:
            row = {"id": None, "afsnit": a["id"]}
            for (_, k), v in zip(a["kolonner"], r):
                row[k] = v
            rid = row["id"]
            key, n = rid, 2
            while key in used:      # same ID several times (e.g. under "Erstattede oplysninger")
                key = f"{rid}@{n}"
                n += 1
            used.add(key)
            row["id"] = key
            facts.append(row)
    return {"titel": title, "indledning": intro, "afsnit": sections}, facts


def write_md(card: dict, facts: list, model_name: str = "model.yaml") -> str:
    out = [GENERATED_BANNER.format(model=model_name), f"# {card.get('titel', '')}"] + list(card.get("indledning") or [])
    for a in card.get("afsnit") or []:
        out.append(f"## {a['titel']}")
        out += a.get("foer", [])
        cols = a.get("kolonner") or []
        if cols:
            out.append("| " + " | ".join(k for k, _ in cols) + " |")
            out.append("|" + "---|" * len(cols))
            for r in facts:
                if r.get("afsnit") == a["id"]:
                    shown = {**r, "id": str(r["id"]).split("@")[0]}
                    out.append("| " + " | ".join(str(shown.get(k, "") if shown.get(k) is not None else "") for _, k in cols) + " |")
        out += a.get("efter", [])
        out.append("")
    return "\n".join(out).rstrip("\n") + "\n"


def check_facts(d: dict) -> list:
    errors = []
    card, facts = d.get("ejendomskort"), d.get("fakta")
    if facts is None and card is None:
        return errors
    if not isinstance(card, dict) or not card.get("afsnit"):
        return ["ejendomskort: mangler (titel, indledning, afsnit, fil), når der er fakta"]
    section_ids = {a.get("id") for a in card["afsnit"]}
    seen = set()
    for i, r in enumerate(facts or []):
        if not isinstance(r, dict) or not r.get("id"):
            errors.append(f"fakta[{i}]: id mangler")
            continue
        if r["id"] in seen:
            errors.append(f"fakta.{r['id']}: id bruges to gange (brug {r['id']}@2 for en ekstra række)")
        seen.add(r["id"])
        if r.get("afsnit") not in section_ids:
            errors.append(f"fakta.{r['id']}: ukendt afsnit '{r.get('afsnit')}' (findes: {', '.join(sorted(section_ids))})")
    return errors


def _card_path(model: pathlib.Path, d: dict) -> pathlib.Path:
    f = (d.get("ejendomskort") or {}).get("fil")
    if not f:
        raise SpecError(["ejendomskort.fil mangler i hovedmodellen"])
    return (model.parent / f).resolve()


def generate(model, check=False, quiet=False) -> int:
    model = pathlib.Path(model).resolve()
    d = _read(model)
    if d.get("basis"):
        print("Ejendomskortet genereres kun fra hovedmodellen (ikke fra et forslag)")
        return 1
    errors = check_facts(d)
    if errors:
        print("FAKTA-FEJL:\n  - " + "\n  - ".join(errors))
        return 1
    if not d.get("ejendomskort"):
        return 0
    md = write_md(d["ejendomskort"], d.get("fakta") or [], model.name)
    card_path = _card_path(model, d)
    if check:
        ok = card_path.exists() and card_path.read_text(encoding="utf-8") == md
        print(f"{'OK' if ok else 'AFVIGER'}: {card_path} {'svarer til' if ok else 'svarer ikke til'} {model.name}"
              + ("" if ok else " – nogen har rettet i kortet; flyt rettelsen til et forslag, og generér igen"))
        return 0 if ok else 1
    card_path.write_text(md, encoding="utf-8")
    if not quiet:
        print(f"SKREVET {card_path} ({len(d.get('fakta') or [])} fakta)")
    return 0


def import_card(model, md) -> int:
    """The card's content → forslag/ejendomskort-import.yaml (merged with bim.py merge; the card is then generated)."""
    from .merge import _flow, create
    model, md = pathlib.Path(model).resolve(), pathlib.Path(md).resolve()
    card, facts = read_md(md.read_text(encoding="utf-8"))
    card = {"fil": os.path.relpath(md, model.parent), **card}
    orig = md.read_text(encoding="utf-8")
    if write_md(card, facts).split("\n", 1)[1] != "\n".join(l for l in orig.split("\n") if not l.startswith("<!-- GENERERET")):
        print("STOP: kortet kan ikke gengives 1:1 fra det indlæste – formatet afviger fra tabelformen")
        return 1
    rc = create(model, "ejendomskort-import", note=f"Import af {md.name} ({len(facts)} fakta)")
    if rc:
        return rc
    f = model.parent / "forslag" / "ejendomskort-import.yaml"
    lines = ["ejendomskort:"] + [f"  {k}: {_flow(v)}" for k, v in card.items() if k != "afsnit"]
    lines += ["  afsnit:"] + [f"    - {_flow(a)}" for a in card["afsnit"]]
    lines += ["fakta:"] + [f"  - {_flow(r)}" for r in facts]
    f.write_text(f.read_text(encoding="utf-8") + "\n".join(lines) + "\n", encoding="utf-8")
    print(f"  {len(facts)} fakta i {len(card['afsnit'])} afsnit → {f.name}; gengivelse 1:1 kontrolleret")
    return 0
