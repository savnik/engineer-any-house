"""Checks an IFC model: schema, buildingSMART rules (selected normative rules), geometry, clashes,
semantics, source basis, quantities against BBR, and IDS. Writes tjek.md and a short printout.

Levels: FEJL (the model is wrong or invalid) · ADVARSEL (should be fixed/clarified) · INFO.
Always run tjek after byg and after any edit. The check can be run by someone other than the model's builder.
"""
import collections
import datetime as dt
import json
import logging
import pathlib
import re

import numpy as np
import ifcopenshell
import ifcopenshell.util.element as ue
import ifcopenshell.util.pset
from shapely import STRtree
from shapely.geometry import Polygon
from shapely.ops import unary_union

from .geometry import fetch_shapes
from .draw import polys_from, projection, section_segments, to_2d

ASSETS = pathlib.Path(__file__).resolve().parent.parent.parent / "assets"
HOSTS = {"IfcWall", "IfcSlab", "IfcRoof", "IfcCovering", "IfcCurtainWall"}


class Report:
    def __init__(self):
        self.items = []

    def add(self, level, category, text):
        self.items.append((level, category, text))

    def count(self, level):
        return sum(1 for p in self.items if p[0] == level)


def _name(e):
    return getattr(e, "Tag", None) or e.Name or f"#{e.id()}"


# ------------------------------------------------------------------ schema
def check_schema(f, r):
    try:
        import ifcopenshell.validate as iv
    except ImportError:
        r.add("ADVARSEL", "skema", "ifcopenshell.validate kunne ikke indlæses")
        return
    log = logging.getLogger("bimtjek")
    log.handlers = []
    log.propagate = False
    h = iv.json_logger()
    try:
        iv.validate(f, h, express_rules=True)
    except Exception as e:  # EXPRESS rules need pytest; the schema is checked anyway
        r.add("ADVARSEL", "skema", f"EXPRESS-regler ikke kørt ({e}); kun attributter er tjekket")
        h = iv.json_logger()
        iv.validate(f, h, express_rules=False)
    for st in h.statements[:30]:
        inst = st.get("instance")
        r.add("FEJL", "skema", f"{inst}: {st.get('message')}"[:300])
    if len(h.statements) > 30:
        r.add("FEJL", "skema", f"… {len(h.statements) - 30} skemafejl mere")


# ------------------------------------------------------------------ buildingSMART rules (selection)
def check_rules(f, r):
    schema = f.schema
    if len(f.by_type("IfcProject")) != 1:
        r.add("FEJL", "struktur", "Der skal være præcis ét IfcProject")
    if len(f.by_type("IfcSite")) > 1:
        r.add("FEJL", "struktur", "Højst én IfcSite (SPS001)")
    if not f.by_type("IfcBuildingStorey"):
        r.add("FEJL", "struktur", "Ingen IfcBuildingStorey")
    for st in f.by_type("IfcBuildingStorey"):
        agg = ue.get_aggregate(st)
        if not agg or not agg.is_a("IfcBuilding"):
            r.add("FEJL", "struktur", f"Etagen {st.Name} er ikke aggregeret under en IfcBuilding (SPS002)")
        if st.Elevation is None:
            r.add("ADVARSEL", "struktur", f"Etagen {st.Name} mangler Elevation")
    contained = {x.id() for rel in f.by_type("IfcRelContainedInSpatialStructure") for x in rel.RelatedElements}
    for sp in f.by_type("IfcSpace"):
        if sp.id() in contained:
            r.add("FEJL", "struktur", f"Rummet {sp.Name} er contained – IfcSpace skal aggregeres under etagen (SPS007)")
        if not ue.get_aggregate(sp):
            r.add("FEJL", "struktur", f"Rummet {sp.Name} er ikke aggregeret under en etage")
        if not sp.Representation or not any(x.RepresentationIdentifier == "Body" for x in sp.Representation.Representations):
            r.add("FEJL", "geometri", f"Rummet {sp.Name} mangler Body-geometri (GEM002)")
    for e in f.by_type("IfcElement"):
        if e.is_a("IfcFeatureElement"):
            if e.ContainedInStructure:
                r.add("FEJL", "struktur", f"{_name(e)}: åbninger må ikke være contained (SPS005)")
            if e.is_a("IfcOpeningElement") and not e.VoidsElements:
                r.add("FEJL", "struktur", f"{_name(e)}: åbning uden IfcRelVoidsElement")
            continue
        n = len(e.ContainedInStructure or [])
        agg = ue.get_aggregate(e)
        if n == 0 and not (agg and agg.is_a("IfcElement")):
            r.add("FEJL", "struktur", f"{e.is_a()} {_name(e)} ligger ikke i en etage (SPS007)")
        if n > 1:
            r.add("FEJL", "struktur", f"{e.is_a()} {_name(e)} er contained flere steder")
        if e.is_a() in ("IfcDoor", "IfcWindow") and not e.FillsVoids:
            r.add("ADVARSEL", "struktur", f"{e.is_a()} {_name(e)} fylder ikke en åbning (IfcRelFillsElement)")
        if e.is_a("IfcWallStandardCase") or e.is_a("IfcSlabStandardCase"):
            r.add("ADVARSEL", "struktur", f"{_name(e)}: *StandardCase er forældet – brug IfcWall/IfcSlab (IFC102)")
        pre = getattr(e, "PredefinedType", None)
        if pre == "USERDEFINED" and not getattr(e, "ObjectType", None):
            r.add("FEJL", "attributter", f"{_name(e)}: USERDEFINED kræver ObjectType")
    gids = collections.Counter(x.GlobalId for x in f.by_type("IfcRoot"))
    for g, n in gids.items():
        if n > 1:
            r.add("FEJL", "id", f"GlobalId {g} bruges {n} gange")
    # property sets and quantities
    tpl = ifcopenshell.util.pset.get_template(schema if schema != "IFC4X3_ADD2" else "IFC4X3")
    for ps in f.by_type("IfcPropertySet"):
        pname = ps.Name or ""
        if pname.lower().startswith("pset") and not pname.startswith("Pset_"):
            r.add("FEJL", "egenskaber", f"Eget sæt '{pname}' må ikke starte med 'pset' (PSE001)")
        if pname.startswith("Pset_"):
            t = tpl.get_by_name(pname)
            if not t:
                r.add("FEJL", "egenskaber", f"'{pname}' er ikke et standardsæt i {schema} (PSE001)")
                continue
            for p in ps.HasProperties:
                pt = next((x for x in t.HasPropertyTemplates if x.Name == p.Name), None)
                if not pt:
                    r.add("FEJL", "egenskaber", f"{pname}.{p.Name} findes ikke i standarden (PSE001)")
                elif pt.TemplateType == "P_ENUMERATEDVALUE" and not p.is_a("IfcPropertyEnumeratedValue"):
                    r.add("FEJL", "egenskaber", f"{pname}.{p.Name} skal være IfcPropertyEnumeratedValue (PSE001)")
                elif pt.TemplateType == "P_SINGLEVALUE" and p.is_a("IfcPropertySingleValue") and p.NominalValue \
                        and pt.PrimaryMeasureType and p.NominalValue.is_a() != pt.PrimaryMeasureType:
                    r.add("FEJL", "egenskaber", f"{pname}.{p.Name}: {p.NominalValue.is_a()} – forventet {pt.PrimaryMeasureType}")
    for q in f.by_type("IfcElementQuantity"):
        if (q.Name or "").startswith("Qto_") and q.MethodOfMeasurement != "BaseQuantities":
            r.add("ADVARSEL", "mængder", f"{q.Name}: MethodOfMeasurement bør være 'BaseQuantities' (QTY001)")
    # georeference
    mc = f.by_type("IfcMapConversion")
    if not mc:
        r.add("ADVARSEL", "geo", "Ingen georeference (IfcMapConversion) – modellen kan ikke placeres på kort (GRF000)")
    else:
        m = mc[0]
        crs = m.TargetCRS
        if not crs or not crs.is_a("IfcProjectedCRS"):
            r.add("ADVARSEL", "geo", "IfcMapConversion uden IfcProjectedCRS (GRF003)")
        import ifcopenshell.util.unit as uu
        unit_scale = uu.calculate_unit_scale(f)
        if abs(unit_scale - 0.001) < 1e-9 and abs((m.Scale or 1.0) - 0.001) > 1e-9:
            mu = getattr(crs, "MapUnit", None)
            if mu is None or (getattr(mu, "Prefix", None) is None and getattr(mu, "Name", "") == "METRE"):
                r.add("FEJL", "geo", f"Projektet er i mm, men IfcMapConversion.Scale = {m.Scale} – skal være 0.001 (GRF005)")


# ------------------------------------------------------------------ content and source basis
def check_semantics(f, r, sidecar):
    own = bool(f.by_type("IfcProject")[0].Name) and any(p.Name == "Byg_Kilde" for p in f.by_type("IfcPropertySet"))
    sources = collections.Counter()
    for e in f.by_type("IfcElement"):
        if e.is_a("IfcFeatureElement"):
            continue
        ps = ue.get_psets(e)
        status = next((p["Status"] for p in ps.values() if "Status" in p), None)
        if not status:
            r.add("ADVARSEL", "status", f"{e.is_a()} {_name(e)} mangler Status (EXISTING/NEW/DEMOLISH/TEMPORARY)")
        if e.is_a("IfcWall") or e.is_a("IfcSlab"):
            if not ue.get_material(e):
                r.add("ADVARSEL", "materiale", f"{_name(e)} har intet materiale")
        if e.is_a("IfcWall"):
            pw = ps.get("Pset_WallCommon", {})
            if "IsExternal" not in pw:
                r.add("ADVARSEL", "egenskaber", f"{_name(e)}: Pset_WallCommon.IsExternal mangler")
        if (e.is_a("IfcWindow") or e.is_a("IfcDoor")) and getattr(e, "FillsVoids", None):
            host = e.FillsVoids[0].RelatingOpeningElement.VoidsElements[0].RelatingBuildingElement
            host_external = next((p.get("IsExternal") for n, p in ue.get_psets(host).items() if n.endswith("Common")), None)
            own_external = next((p.get("IsExternal") for n, p in ps.items() if n.endswith("Common") and "IsExternal" in p), None)
            if host_external and own_external is not True:
                r.add("ADVARSEL", "egenskaber", f"{e.is_a()} {_name(e)} sidder i ydervæggen {_name(host)}, men IsExternal er "
                      f"{own_external} – skal være TRUE")
        if own:
            k = (ps.get("Byg_Kilde") or {}).get("Kilde")
            if not k:
                r.add("ADVARSEL", "kilde", f"{_name(e)} mangler Byg_Kilde")
            else:
                sources[str(k)[:1]] += 1
    if sources:
        tot = sum(sources.values())
        r.add("INFO", "kilde", "Kildegrundlag: " + ", ".join(f"{k} {n}" for k, n in sorted(sources.items()))
              + f" (A = antagelse: {100 * sources.get('A', 0) / tot:.0f} %)")
    for stair in f.by_type("IfcStair"):
        p = ue.get_psets(stair).get("Pset_StairCommon", {})
        s, g = p.get("RiserHeight"), p.get("TreadLength")
        if s and g:
            v = 2 * s + g
            if not 590 <= v <= 650:
                r.add("INFO", "trapper", f"{_name(stair)}: 2·stigning + grund = {v:.0f} mm (gængs 610–630) – kontrollér målene")
    if sidecar:
        for x in sidecar.get("fejl", []):
            r.add("FEJL", "byg", x)
        for x in sidecar.get("advarsler", []):
            r.add("ADVARSEL", "byg", x)


# ------------------------------------------------------------------ traceability
# Deliverable ID: <case>/<trade>/<no> or the short form <trade>-<no> (e.g. "vvs-13", "el-02-r2")
DELIVERABLE_REF = re.compile(r"[\w.-]+/[a-z]+/\d+|\b(?:vvs|el|murer|ventilation|maler|toemrer|tømrer|statik|bim|projekt)[-/ ]?\d+",
                           re.IGNORECASE)
NOTE_A_SHARE = re.compile(r"[Kk]ilde\s*A\b[^\n%]{0,60}?(\d{1,3})(?:[,.]\d+)?\s*%")


def check_traceability(f, r, note=None):
    """Deterministic part of the source check (formerly the BIM review's most frequent finding):
    source != A needs a reference, K (approved trade note) needs a deliverable ID, A needs an uncertainty,
    and the share of assumptions stated in the model note must match the model."""
    own = any(p.Name == "Byg_Kilde" for p in f.by_type("IfcPropertySet"))
    if not own:
        return
    sources = collections.Counter()
    missing = collections.defaultdict(list)
    for e in f.by_type("IfcElement"):
        if e.is_a("IfcFeatureElement"):
            continue
        bk = ue.get_psets(e).get("Byg_Kilde") or {}
        k = str(bk.get("Kilde") or "")[:1].upper()
        if not k:
            continue
        sources[k] += 1
        ref = str(bk.get("Reference") or "").strip()
        if k != "A" and not ref:
            missing["kilde uden reference"].append(_name(e))
        if k == "K" and ref and not DELIVERABLE_REF.search(ref):
            missing["kilde K uden leverance-ID (fx <sag>/vvs/13 eller vvs-13) i reference"].append(_name(e))
        if k == "A" and bk.get("Usikkerhed_mm") is None:
            missing["antagelse (A) uden usikkerhed"].append(_name(e))
    for what, names in missing.items():
        r.add("ADVARSEL", "sporbarhed", f"{len(names)} elementer med {what}: " + ", ".join(names[:12])
              + (" …" if len(names) > 12 else ""))
    if note and sources:
        path = pathlib.Path(note)
        if path.is_file():
            m = NOTE_A_SHARE.search(path.read_text(encoding="utf-8"))
            share = 100 * sources.get("A", 0) / sum(sources.values())
            if m and abs(int(m.group(1)) - share) > 2:
                r.add("ADVARSEL", "sporbarhed", f"Modelnotatet oplyser kilde A {m.group(1)} %, men modellen har {share:.0f} % "
                      "– ret notatet eller mærkningen")
            elif not m:
                r.add("INFO", "sporbarhed", f"{path.name} oplyser ikke andelen af kilde A (modellen: {share:.0f} %)")
        else:
            r.add("ADVARSEL", "sporbarhed", f"Modelnotatet findes ikke: {path}")


# ------------------------------------------------------------------ geometry, clashes, areas
def check_geometry(f, r, shapes_out):
    errors = []
    shapes = fetch_shapes(f, errors=errors)
    for e in errors:
        r.add("FEJL", "geometri", f"{e.is_a()} {_name(e)}: geometrien kan ikke dannes")
    shapes_out.extend(shapes)
    if not shapes:
        return
    cut_z = set()
    for st in f.by_type("IfcBuildingStorey"):
        z = float(st.Elevation or 0)
        cut_z.update({z + 150, z + 1000, z + 1900})
    for fm in shapes:
        if fm.ifc_class == "IfcSlab":
            cut_z.add(round((fm.zmin + fm.zmax) / 2, 1))
    n = np.array([0, 0, 1.0])
    axes = (np.array([1.0, 0, 0]), np.array([0, 1.0, 0]))
    found = {}
    candidates = [fm for fm in shapes if fm.ifc_class not in ("IfcSpace", "IfcDoor", "IfcWindow")]
    for z in sorted(cut_z):
        layer = []
        for fm in candidates:
            if fm.zmin + 1 < z < fm.zmax - 1:
                ps = polys_from(to_2d(section_segments(fm.v, fm.f, n, z), axes))
                if ps:
                    layer.append((fm, unary_union(ps)))
        if len(layer) < 2:
            continue
        geoms = [g for _, g in layer]
        tree = STRtree(geoms)
        for i, (fa, ga) in enumerate(layer):
            for j in tree.query(ga):
                if j <= i:
                    continue
                fb, gb = layer[j]
                if _ignore(fa, fb):
                    continue
                a = ga.intersection(gb).area
                if a > 2000:  # mm² (e.g. 20 × 100 mm)
                    k = (min(fa.id, fb.id), max(fa.id, fb.id))
                    if a > found.get(k, (0,))[0]:
                        found[k] = (a, fa, fb, z)
    for a, fa, fb, z in sorted(found.values(), key=lambda x: -x[0]):
        pair = {fa.ifc_class, fb.ifc_class}
        pipes = pair & {"IfcPipeSegment", "IfcDuctSegment", "IfcFlowSegment", "IfcCableCarrierSegment"}
        if pipes and pair & HOSTS:
            r.add("INFO", "gennemføring", f"{fa.tag} / {fb.tag}: rør eller kanal gennem {(pair & HOSTS).pop()[3:]} ved z={z:.0f}")
        elif "IfcChimney" in pair and pair & {"IfcSlab", "IfcRoof"}:
            level = "INFO" if _is_roof(fa) or _is_roof(fb) else "ADVARSEL"
            r.add(level, "gennemføring", f"{fa.tag} / {fb.tag}: skorsten gennem dæk/tag ved z={z:.0f} uden hul i dækket"
                  + ("" if level == "INFO" else " – tilføj huller i daek"))
        else:
            r.add("FEJL" if a > 10000 else "ADVARSEL", "kollision",
                  f"{fa.tag} ({fa.ifc_class[3:]}) overlapper {fb.tag} ({fb.ifc_class[3:]}): {a / 1e6:.3f} m² i snit z={z:.0f}")


def _is_roof(fm):
    agg = ue.get_aggregate(fm.ent)
    return fm.ifc_class == "IfcSlab" and agg is not None and agg.is_a("IfcRoof")


def _ignore(fa, fb):
    ka, kb = fa.ifc_class, fb.ifc_class
    if {ka, kb} <= {"IfcPipeSegment", "IfcDuctSegment"}:
        return str(fa.tag).rsplit(".", 1)[0] == str(fb.tag).rsplit(".", 1)[0]
    if {ka, kb} <= {"IfcSlab", "IfcMember"}:
        agg = ue.get_aggregate(fa.ent)
        if agg is not None and agg.is_a("IfcRoof") and agg == ue.get_aggregate(fb.ent):
            return True  # roof faces meet at ridge/hip; rafters lie in the faces' rafter layer and meet each other
    return False


def check_areas(f, r, shapes, sidecar):
    control = (sidecar or {}).get("kontrol") or {}
    targets = control.get("areal") or {}
    tol = float(control.get("tolerance", 0.05))
    id_to_name = {k: v["navn"] for k, v in ((sidecar or {}).get("etager") or {}).items()}
    lines = []
    for st in sorted(f.by_type("IfcBuildingStorey"), key=lambda s: float(s.Elevation or 0)):
        external = [fm for fm in shapes if fm.ifc_class == "IfcWall" and fm.storey is not None and fm.storey.id() == st.id()
               and ue.get_psets(fm.ent).get("Pset_WallCommon", {}).get("IsExternal")]
        polys = [g for g in (projection(fm, (np.array([1.0, 0, 0]), np.array([0, 1.0, 0]))) for fm in external) if g is not None]
        gross = None
        if polys:
            u = unary_union([p.buffer(5) for p in polys]).buffer(-5)
            parts = [g for g in getattr(u, "geoms", [u]) if g.geom_type == "Polygon"]
            if parts:
                gross = Polygon(max(parts, key=lambda g: g.area).exterior).area / 1e6
        net = sum((ue.get_psets(sp).get("Qto_SpaceBaseQuantities", {}) or {}).get("NetFloorArea", 0) or 0
                    for sp in f.by_type("IfcSpace") if ue.get_aggregate(sp) == st)
        lines.append(f"{st.Name}: brutto (til ydervæggenes yderside) {gross:.1f} m², rum netto {net:.1f} m²"
                      if gross else f"{st.Name}: rum netto {net:.1f} m²")
        for eid, m2 in targets.items():
            if id_to_name.get(str(eid), str(eid)) == st.Name and gross:
                dev = (gross - float(m2)) / float(m2)
                level = "ADVARSEL" if abs(dev) > tol else "INFO"
                r.add(level, "areal", f"{st.Name}: brutto {gross:.1f} m² mod kontrolværdi {m2} m² ({dev:+.1%}, tolerance ±{tol:.0%})")
    for l in lines:
        r.add("INFO", "areal", l)


# ------------------------------------------------------------------ IDS
def check_ids(f, path, r):
    try:
        import ifctester.ids
        import ifctester.reporter
    except ImportError:
        r.add("ADVARSEL", "ids", "ifctester mangler – kør bim.py opsaet")
        return
    spec = ifctester.ids.open(str(path))
    spec.validate(f)
    for s in spec.specifications:
        if s.status is False:
            failed = [x for req in s.requirements for x in (getattr(req, "failures", None) or [])]
            examples = "; ".join(_name(x["element"]) + ": " + str(x.get("reason", ""))[:80]
                            for x in failed[:3] if isinstance(x, dict) and x.get("element") is not None)
            r.add("FEJL", "ids",
                  f"{path.name} · {s.name}: {len(failed)} fejl" + (f" – {examples}" if examples else ""))
        else:
            r.add("INFO", "ids", f"{path.name} · {s.name}: bestået")


# ------------------------------------------------------------------ entry point
def check(ifc, ids=None, out=None, draw=False, note=None):
    ifc = pathlib.Path(ifc)
    f = ifcopenshell.open(str(ifc))
    sidecar_path = ifc.with_suffix(".byg.json")
    sidecar = json.loads(sidecar_path.read_text(encoding="utf-8")) if sidecar_path.exists() else None
    r = Report()
    check_schema(f, r)
    check_rules(f, r)
    check_semantics(f, r, sidecar)
    check_traceability(f, r, note)
    shapes = []
    check_geometry(f, r, shapes)
    check_areas(f, r, shapes, sidecar)
    ids_path = pathlib.Path(ids) if ids else (ASSETS / "ids" / "byg-bolig.ids")
    if ids_path.exists():
        check_ids(f, ids_path, r)
    out = pathlib.Path(out) if out else ifc.parent
    out.mkdir(parents=True, exist_ok=True)
    report_path = out / f"{ifc.stem}.tjek.md"
    nf, na = r.count("FEJL"), r.count("ADVARSEL")
    ns = sum(1 for p in r.items if p[1] == "sporbarhed" and p[0] != "INFO")
    md = [f"# Tjek – {ifc.name}", f"**Dato:** {dt.datetime.now():%Y-%m-%d %H:%M} · **Skema:** {f.schema} · "
           f"**Resultat:** {nf} fejl, {na} advarsler, {ns} sporbarhed", ""]
    for level in ("FEJL", "ADVARSEL", "INFO"):
        level_items = [p for p in r.items if p[0] == level]
        if level_items:
            md.append(f"## {level} ({len(level_items)})")
            md += [f"- [{k}] {t}" for _, k, t in level_items]
            md.append("")
    files = []
    if draw:
        from .draw import draw as draw_fn
        files = draw_fn(ifc, "alle", out=out / "tegninger", dims=True)
        md.append("## Tegninger")
        md += [f"- {p}" for p in files]
    report_path.write_text("\n".join(md) + "\n", encoding="utf-8")
    print(f"TJEK {ifc.name}: {nf} fejl, {na} advarsler, {ns} sporbarhed → {report_path}")
    shown = 0
    for level in ("FEJL", "ADVARSEL"):
        for _, k, t in [p for p in r.items if p[0] == level]:
            if shown < 25:
                print(f"  {level} [{k}] {t}")
                shown += 1
    if nf + na > shown:
        print(f"  … se resten i {report_path.name}")
    for _, k, t in [p for p in r.items if p[0] == "INFO" and p[1] in ("areal", "kilde")]:
        print(f"  INFO [{k}] {t}")
    for p in files:
        print(f"  tegning: {p}")
    return 1 if nf else 0

