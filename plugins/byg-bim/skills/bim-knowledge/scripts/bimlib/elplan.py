"""bim.py elplan: el-plan per room from an IFC model – point list, § 57 outlet count and switch type per lysgruppe.

Rooms are IfcSpace; points are IfcOutlet, IfcLightFixture, IfcSwitchingDevice, IfcSensor and IfcElectricDistributionBoard,
assigned to the space whose footprint contains the point (or the nearest within 300 mm – wall-mounted points sit on the
wall face). Lysgruppe, kreds and dimmer come from the Byg_El set (spec fields lysgruppe/kreds/dimmer).

§ 57 (BEK 1082/2016): stk. 1 one 250 V outlet per started 4 m² floor, at most 10 required; stk. 2 kitchen region at
least 3 on at least 2 circuits; stk. 3 kogeniche at least 1; stk. 4 bathroom/wc not stk. 1 but at least 1; stk. 5
garage, carport, loft, storage and similar not covered by stk. 1.
"""
import math
import pathlib
import re

import ifcopenshell.util.element as ue
import ifcopenshell.util.placement as up
from shapely.geometry import Point

from .geometry import storey_of
from .measure import _footprint, _mesh, _open_model, _scale

NEAR_MM = 300.0
KIND_LABEL = {"stikkontakt": "Stikkontakt", "kraftstik": "Kraftstik 400 V", "data": "Data/tv", "lampe": "Lampeudtag",
              "afbryder": "Afbryder", "pir": "PIR-sensor", "tavle": "Tavle"}
ROOM_KINDS = (  # (regex on name/anvendelse, kind) – first match wins
    (r"grovk(ø|oe)kken|bryggers", "rum"),
    (r"kogeniche", "kogeniche"),
    (r"k(ø|oe)kken", "koekken"),
    (r"\bbad|wc|toilet", "bad"),
    (r"garage|carport|loft|depot|pulterrum|skur|udhus", "undtaget"),
)


def room_kind(text: str) -> str:
    t = text.lower()
    return next((k for rx, k in ROOM_KINDS if re.search(rx, t)), "rum")


def required(kind: str, area_m2: float):
    """(minimum outlets, rule text) for a room kind and area."""
    if kind == "undtaget":
        return 0, "ikke omfattet (§ 57, stk. 5)"
    if kind == "bad":
        return 1, "mindst 1 (§ 57, stk. 4)"
    if kind == "kogeniche":
        return 1, "mindst 1 (§ 57, stk. 3)"
    n = min(10, max(1, math.ceil(round(area_m2, 2) / 4)))
    rule = f"1 pr. påbegyndt 4 m² → {n} (§ 57, stk. 1)"
    if kind == "koekken":
        n = max(n, 3)
        rule += "; køkkenregion ≥ 3 på ≥ 2 kredse (stk. 2)"
    return n, rule


def switch_type(n_switches: int, krone: bool) -> str:
    if n_switches == 0:
        return "ingen betjening"
    if n_switches == 1:
        return "kroneafbryder" if krone else "1-polet afbryder"
    if n_switches == 2:
        return "korrespondance"
    return f"korrespondance + {n_switches - 2} krydsafbryder" + ("e" if n_switches > 3 else "")


def _kind(e, el):
    art = el.get("Art")
    if art in KIND_LABEL:
        return art
    pre = str(getattr(e, "PredefinedType", "") or "")
    if e.is_a("IfcOutlet"):
        return "data" if pre in ("DATAOUTLET", "AUDIOVISUALOUTLET", "TELEPHONEOUTLET", "COMMUNICATIONSOUTLET") \
            else "stikkontakt"
    if e.is_a("IfcSensor"):
        return "pir" if pre in ("MOVEMENTSENSOR", "OCCUPANCYSENSOR") else None
    return {"IfcLightFixture": "lampe", "IfcSwitchingDevice": "afbryder",
            "IfcElectricDistributionBoard": "tavle"}.get(e.is_a())


def _spaces(f):
    out = []
    for s in f.by_type("IfcSpace"):
        m = _mesh(s)
        if m is None:
            continue
        v, fa = m
        fp = _footprint(v, fa)
        q = ue.get_psets(s).get("Qto_SpaceBaseQuantities", {})
        area = q.get("NetFloorArea") or fp.area / 1e6
        use = ue.get_psets(s).get("Byg_Rum", {}).get("Anvendelse", "")
        name = s.LongName or s.Name or s.GlobalId
        out.append({"ent": s, "id": s.Name or s.GlobalId, "navn": name, "fp": fp, "z": (v[:, 2].min(), v[:, 2].max()),
                    "areal": float(area), "art": room_kind(f"{use} {name}"), "punkter": []})
    return out


def collect(f):
    """Spaces with their el points and the points not inside any space."""
    scale = _scale(f)
    spaces = _spaces(f)
    loose = []
    classes = ("IfcOutlet", "IfcLightFixture", "IfcSwitchingDevice", "IfcSensor", "IfcElectricDistributionBoard")
    for e in (x for c in classes for x in f.by_type(c)):
        el = ue.get_psets(e).get("Byg_El", {})
        kind = _kind(e, el)
        if kind is None or not e.ObjectPlacement:
            continue
        x, y, z = up.get_local_placement(e.ObjectPlacement)[:3, 3] * scale
        groups = [g for g in str(el.get("Lysgruppe") or "").split(",") if g]
        p = {"id": e.Name or e.GlobalId, "art": kind, "z": z, "lysgrupper": groups, "kreds": el.get("Kreds"),
             "dimmer": bool(el.get("Dimmer")), "etage": getattr(storey_of(e), "Name", None)}
        pt = Point(x, y)
        cands = [s for s in spaces if s["z"][0] - 1 <= z <= s["z"][1] + 1]
        inside = [s for s in cands if s["fp"].contains(pt)]
        if not inside:
            near = sorted(cands, key=lambda s: s["fp"].distance(pt))
            inside = [s for s in near[:1] if s["fp"].distance(pt) <= NEAR_MM]
        if inside:
            p["hoejde"] = z - inside[0]["z"][0]
            inside[0]["punkter"].append(p)
        else:
            loose.append(p)
    return spaces, loose


def evaluate(spaces):
    """Per-room result rows and lysgruppe rows; findings with 'MANGLER'/'FEJL' are failures."""
    rooms, findings = [], []
    for s in spaces:
        pts = s["punkter"]
        outlets = [p for p in pts if p["art"] == "stikkontakt"]
        need, rule = required(s["art"], s["areal"])
        ok = len(outlets) >= need
        row = {"rum": s, "stik": len(outlets), "krav": need, "regel": rule, "ok": ok}
        if not ok:
            findings.append(f"MANGLER {s['id']} ({s['navn']}): {len(outlets)} stikkontakter, krav {need} – {rule}")
        if s["art"] == "koekken" and outlets:
            circuits = {p["kreds"] for p in outlets if p["kreds"]}
            if any(not p["kreds"] for p in outlets):
                findings.append(f"KONTROLLÉR {s['id']}: kreds ikke angivet på alle stikkontakter – § 57, stk. 2 kræver "
                                f"≥ 2 kredse i køkkenregionen")
            elif len(circuits) < 2:
                findings.append(f"MANGLER {s['id']} ({s['navn']}): stikkontakterne er på {len(circuits)} kreds – "
                                f"§ 57, stk. 2 kræver ≥ 2")
            row["kredse"] = sorted(circuits)
        rooms.append(row)
    groups = {}
    for s in spaces:
        for p in s["punkter"]:
            for g in p["lysgrupper"]:
                d = groups.setdefault(g, {"lamper": [], "afbrydere": [], "pir": [], "rum": set(), "dimmer": False})
                d[{"lampe": "lamper", "afbryder": "afbrydere", "pir": "pir"}.get(p["art"], "lamper")].append(p)
                d["rum"].add(s["id"])
                d["dimmer"] |= p["dimmer"]
    light = []
    for g, d in sorted(groups.items()):
        krone = len(d["afbrydere"]) == 1 and len(d["afbrydere"][0]["lysgrupper"]) == 2
        t = switch_type(len(d["afbrydere"]), krone)
        if len(d["afbrydere"]) == 1 and len(d["afbrydere"][0]["lysgrupper"]) > 2:
            t = f"afbryder med {len(d['afbrydere'][0]['lysgrupper'])} lysgrupper – kontrollér materiel"
        if not d["lamper"]:
            findings.append(f"FEJL lysgruppe {g}: betjenes, men har ingen lamper")
        if not d["afbrydere"] and not d["pir"]:
            findings.append(f"KONTROLLÉR lysgruppe {g}: ingen afbryder eller PIR")
        light.append({"gruppe": g, "type": t + (" · PIR" if d["pir"] else "") + (" · dæmpbar" if d["dimmer"] else ""),
                      **d})
    for s in spaces:
        for p in s["punkter"]:
            if p["art"] == "lampe" and not p["lysgrupper"]:
                findings.append(f"KONTROLLÉR {p['id']} i {s['id']}: lampe uden lysgruppe")
    return rooms, light, findings


def report(rooms, light, findings, loose, title) -> str:
    L = [f"# El-plan – {title}", "",
         "Genereret af `bim.py elplan`. Antal efter installationsbekendtgørelsen (BEK 1082/2016) § 57. Placering, "
         "kredsdeling og køkkenregion skal stadig vurderes af en autoriseret elinstallatør. Rumtypen læses af "
         "rummets navn/anvendelse; tekniske rum (fx fyrrum) tælles efter stk. 1 – vurdér om de er \"lignende\" "
         "efter stk. 5.", "",
         "## Stikkontakter pr. rum (§ 57)", "",
         "| Rum | Navn | Areal m² | Stikkontakter | Krav | Regel | Status |", "|---|---|---|---|---|---|---|"]
    for r in rooms:
        s = r["rum"]
        status = "OK" if r["ok"] else "MANGLER"
        if r.get("kredse") is not None:
            status += f" · kredse: {', '.join(r['kredse']) or '–'}"
        L.append(f"| {s['id']} | {s['navn']} | {s['areal']:.1f} | {r['stik']} | {r['krav']} | {r['regel']} | {status} |")
    L += ["", "## Lysgrupper og afbrydertype", ""]
    if light:
        L += ["| Lysgruppe | Rum | Lamper | Betjening | Type |", "|---|---|---|---|---|"]
        for g in light:
            ops = [p["id"] for p in g["afbrydere"] + g["pir"]]
            L.append(f"| {g['gruppe']} | {', '.join(sorted(g['rum']))} | {len(g['lamper'])} | {', '.join(ops) or '–'} "
                     f"| {g['type']} |")
    else:
        L.append("Ingen lysgrupper angivet (feltet `lysgruppe` på lamper og afbrydere).")
    L += ["", "## Punktliste pr. rum", ""]
    for r in rooms:
        s = r["rum"]
        if not s["punkter"]:
            continue
        L += [f"### {s['id']} {s['navn']} ({s['areal']:.1f} m²)", "",
              "| Punkt | Type | Højde mm | Lysgruppe | Kreds | Dæmp |", "|---|---|---|---|---|---|"]
        for p in sorted(s["punkter"], key=lambda p: (list(KIND_LABEL).index(p["art"]), p["id"])):
            L.append(f"| {p['id']} | {KIND_LABEL[p['art']]} | {p['hoejde']:.0f} | {', '.join(p['lysgrupper']) or '–'} "
                     f"| {p['kreds'] or '–'} | {'ja' if p['dimmer'] else ''} |")
        L.append("")
    if loose:
        L += ["## Punkter uden for rum", ""] + [f"- {p['id']} ({KIND_LABEL[p['art']]}, etage {p['etage']})"
                                                 for p in loose] + [""]
    L += ["## Fund", ""] + ([f"- {x}" for x in findings] or ["- Ingen."])
    return "\n".join(L) + "\n"


def elplan(model: pathlib.Path, out=None) -> int:
    model = pathlib.Path(model)
    f = _open_model(model)
    spaces, loose = collect(f)
    if not spaces:
        print("Ingen rum (IfcSpace) med geometri i modellen – el-planen kræver rum.")
        return 2
    rooms, light, findings = evaluate(spaces)
    if out is None:
        base = model.parent / "out" if model.suffix.lower() in (".yaml", ".yml") else model.parent
        out = base / f"{model.parent.name if model.stem == 'model' else model.stem}-elplan.md"
    out = pathlib.Path(out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(report(rooms, light, findings, loose, model.stem), encoding="utf-8")
    n = sum(len(s["punkter"]) for s in spaces)
    print(f"EL-PLAN {out}  ({len(spaces)} rum, {n} punkter, {len(light)} lysgrupper)")
    for r in rooms:
        s = r["rum"]
        print(f"  {s['id']:<8} {s['navn'][:22]:<22} {s['areal']:6.1f} m²  stik {r['stik']:>2}/{r['krav']:<2} "
              f"{'OK' if r['ok'] else 'MANGLER'}")
    for g in light:
        print(f"  lysgruppe {g['gruppe']}: {g['type']}")
    for x in findings:
        print("  " + x)
    return 1 if any(x.startswith(("MANGLER", "FEJL")) for x in findings) else 0
