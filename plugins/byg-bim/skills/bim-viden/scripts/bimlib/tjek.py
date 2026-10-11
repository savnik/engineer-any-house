"""Kontrol af en IFC-model: skema, buildingSMART-regler (udvalgte normative regler), geometri, kollisioner,
semantik, kildegrundlag, mængder mod BBR og IDS. Skriver tjek.md og en kort udskrift.

Niveauer: FEJL (modellen er forkert eller ugyldig) · ADVARSEL (bør rettes/afklares) · INFO.
Kør altid tjek efter byg og efter enhver redigering. Kontrollen kan køres af andre end den, der byggede modellen.
"""
import collections
import datetime as dt
import json
import logging
import pathlib

import numpy as np
import ifcopenshell
import ifcopenshell.util.element as ue
import ifcopenshell.util.pset
from shapely import STRtree
from shapely.geometry import Polygon
from shapely.ops import unary_union

from .geometri import hent
from .tegn import polys_af, projektion, snit_polygoner, til_2d

ASSETS = pathlib.Path(__file__).resolve().parent.parent.parent / "assets"
VAERT = {"IfcWall", "IfcSlab", "IfcRoof", "IfcCovering", "IfcCurtainWall"}


class Rapport:
    def __init__(self):
        self.punkter = []

    def add(self, niveau, kategori, tekst):
        self.punkter.append((niveau, kategori, tekst))

    def antal(self, niveau):
        return sum(1 for p in self.punkter if p[0] == niveau)


def _navn(e):
    return getattr(e, "Tag", None) or e.Name or f"#{e.id()}"


# ------------------------------------------------------------------ skema
def skema(f, r):
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
    except Exception as e:  # express-regler kræver pytest; skemaet tjekkes alligevel
        r.add("ADVARSEL", "skema", f"EXPRESS-regler ikke kørt ({e}); kun attributter er tjekket")
        h = iv.json_logger()
        iv.validate(f, h, express_rules=False)
    for st in h.statements[:30]:
        inst = st.get("instance")
        r.add("FEJL", "skema", f"{inst}: {st.get('message')}"[:300])
    if len(h.statements) > 30:
        r.add("FEJL", "skema", f"… {len(h.statements) - 30} skemafejl mere")


# ------------------------------------------------------------------ buildingSMART-regler (udvalg)
def regler(f, r):
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
                r.add("FEJL", "struktur", f"{_navn(e)}: åbninger må ikke være contained (SPS005)")
            if e.is_a("IfcOpeningElement") and not e.VoidsElements:
                r.add("FEJL", "struktur", f"{_navn(e)}: åbning uden IfcRelVoidsElement")
            continue
        n = len(e.ContainedInStructure or [])
        agg = ue.get_aggregate(e)
        if n == 0 and not (agg and agg.is_a("IfcElement")):
            r.add("FEJL", "struktur", f"{e.is_a()} {_navn(e)} ligger ikke i en etage (SPS007)")
        if n > 1:
            r.add("FEJL", "struktur", f"{e.is_a()} {_navn(e)} er contained flere steder")
        if e.is_a() in ("IfcDoor", "IfcWindow") and not e.FillsVoids:
            r.add("ADVARSEL", "struktur", f"{e.is_a()} {_navn(e)} fylder ikke en åbning (IfcRelFillsElement)")
        if e.is_a("IfcWallStandardCase") or e.is_a("IfcSlabStandardCase"):
            r.add("ADVARSEL", "struktur", f"{_navn(e)}: *StandardCase er forældet – brug IfcWall/IfcSlab (IFC102)")
        pre = getattr(e, "PredefinedType", None)
        if pre == "USERDEFINED" and not getattr(e, "ObjectType", None):
            r.add("FEJL", "attributter", f"{_navn(e)}: USERDEFINED kræver ObjectType")
    gids = collections.Counter(x.GlobalId for x in f.by_type("IfcRoot"))
    for g, n in gids.items():
        if n > 1:
            r.add("FEJL", "id", f"GlobalId {g} bruges {n} gange")
    # egenskabssæt og mængder
    tpl = ifcopenshell.util.pset.get_template(schema if schema != "IFC4X3_ADD2" else "IFC4X3")
    for ps in f.by_type("IfcPropertySet"):
        nav = ps.Name or ""
        if nav.lower().startswith("pset") and not nav.startswith("Pset_"):
            r.add("FEJL", "egenskaber", f"Eget sæt '{nav}' må ikke starte med 'pset' (PSE001)")
        if nav.startswith("Pset_"):
            t = tpl.get_by_name(nav)
            if not t:
                r.add("FEJL", "egenskaber", f"'{nav}' er ikke et standardsæt i {schema} (PSE001)")
                continue
            for p in ps.HasProperties:
                pt = next((x for x in t.HasPropertyTemplates if x.Name == p.Name), None)
                if not pt:
                    r.add("FEJL", "egenskaber", f"{nav}.{p.Name} findes ikke i standarden (PSE001)")
                elif pt.TemplateType == "P_ENUMERATEDVALUE" and not p.is_a("IfcPropertyEnumeratedValue"):
                    r.add("FEJL", "egenskaber", f"{nav}.{p.Name} skal være IfcPropertyEnumeratedValue (PSE001)")
                elif pt.TemplateType == "P_SINGLEVALUE" and p.is_a("IfcPropertySingleValue") and p.NominalValue \
                        and pt.PrimaryMeasureType and p.NominalValue.is_a() != pt.PrimaryMeasureType:
                    r.add("FEJL", "egenskaber", f"{nav}.{p.Name}: {p.NominalValue.is_a()} – forventet {pt.PrimaryMeasureType}")
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
        sk = uu.calculate_unit_scale(f)
        if abs(sk - 0.001) < 1e-9 and abs((m.Scale or 1.0) - 0.001) > 1e-9:
            mu = getattr(crs, "MapUnit", None)
            if mu is None or (getattr(mu, "Prefix", None) is None and getattr(mu, "Name", "") == "METRE"):
                r.add("FEJL", "geo", f"Projektet er i mm, men IfcMapConversion.Scale = {m.Scale} – skal være 0.001 (GRF005)")


# ------------------------------------------------------------------ indhold og kildegrundlag
def semantik(f, r, sidevogn):
    egne = bool(f.by_type("IfcProject")[0].Name) and any(p.Name == "Byg_Kilde" for p in f.by_type("IfcPropertySet"))
    kilder = collections.Counter()
    for e in f.by_type("IfcElement"):
        if e.is_a("IfcFeatureElement"):
            continue
        ps = ue.get_psets(e)
        status = next((p["Status"] for p in ps.values() if "Status" in p), None)
        if not status:
            r.add("ADVARSEL", "status", f"{e.is_a()} {_navn(e)} mangler Status (EXISTING/NEW/DEMOLISH/TEMPORARY)")
        if e.is_a("IfcWall") or e.is_a("IfcSlab"):
            if not ue.get_material(e):
                r.add("ADVARSEL", "materiale", f"{_navn(e)} har intet materiale")
        if e.is_a("IfcWall"):
            pw = ps.get("Pset_WallCommon", {})
            if "IsExternal" not in pw:
                r.add("ADVARSEL", "egenskaber", f"{_navn(e)}: Pset_WallCommon.IsExternal mangler")
        if (e.is_a("IfcWindow") or e.is_a("IfcDoor")) and getattr(e, "FillsVoids", None):
            vaert = e.FillsVoids[0].RelatingOpeningElement.VoidsElements[0].RelatingBuildingElement
            vaert_ude = next((p.get("IsExternal") for n, p in ue.get_psets(vaert).items() if n.endswith("Common")), None)
            eget = next((p.get("IsExternal") for n, p in ps.items() if n.endswith("Common") and "IsExternal" in p), None)
            if vaert_ude and eget is not True:
                r.add("ADVARSEL", "egenskaber", f"{e.is_a()} {_navn(e)} sidder i ydervæggen {_navn(vaert)}, men IsExternal er "
                      f"{eget} – skal være TRUE")
        if egne:
            k = (ps.get("Byg_Kilde") or {}).get("Kilde")
            if not k:
                r.add("ADVARSEL", "kilde", f"{_navn(e)} mangler Byg_Kilde")
            else:
                kilder[str(k)[:1]] += 1
    if kilder:
        tot = sum(kilder.values())
        r.add("INFO", "kilde", "Kildegrundlag: " + ", ".join(f"{k} {n}" for k, n in sorted(kilder.items()))
              + f" (A = antagelse: {100 * kilder.get('A', 0) / tot:.0f} %)")
    for tr in f.by_type("IfcStair"):
        p = ue.get_psets(tr).get("Pset_StairCommon", {})
        s, g = p.get("RiserHeight"), p.get("TreadLength")
        if s and g:
            v = 2 * s + g
            if not 590 <= v <= 650:
                r.add("INFO", "trapper", f"{_navn(tr)}: 2·stigning + grund = {v:.0f} mm (gængs 610–630) – kontrollér målene")
    if sidevogn:
        for x in sidevogn.get("fejl", []):
            r.add("FEJL", "byg", x)
        for x in sidevogn.get("advarsler", []):
            r.add("ADVARSEL", "byg", x)


# ------------------------------------------------------------------ geometri, kollisioner, arealer
def geometri(f, r, former_ud):
    fejl = []
    former = hent(f, fejl=fejl)
    for e in fejl:
        r.add("FEJL", "geometri", f"{e.is_a()} {_navn(e)}: geometrien kan ikke dannes")
    former_ud.extend(former)
    if not former:
        return
    snit_z = set()
    for st in f.by_type("IfcBuildingStorey"):
        z = float(st.Elevation or 0)
        snit_z.update({z + 150, z + 1000, z + 1900})
    for fm in former:
        if fm.klasse == "IfcSlab":
            snit_z.add(round((fm.zmin + fm.zmax) / 2, 1))
    n = np.array([0, 0, 1.0])
    akser = (np.array([1.0, 0, 0]), np.array([0, 1.0, 0]))
    fund = {}
    kandidater = [fm for fm in former if fm.klasse not in ("IfcSpace", "IfcDoor", "IfcWindow")]
    for z in sorted(snit_z):
        lag = []
        for fm in kandidater:
            if fm.zmin + 1 < z < fm.zmax - 1:
                ps = polys_af(til_2d(snit_polygoner(fm.v, fm.f, n, z), akser))
                if ps:
                    lag.append((fm, unary_union(ps)))
        if len(lag) < 2:
            continue
        geoms = [g for _, g in lag]
        trae = STRtree(geoms)
        for i, (fa, ga) in enumerate(lag):
            for j in trae.query(ga):
                if j <= i:
                    continue
                fb, gb = lag[j]
                if _ignorer(fa, fb):
                    continue
                a = ga.intersection(gb).area
                if a > 2000:  # mm² (fx 20 × 100 mm)
                    k = (min(fa.id, fb.id), max(fa.id, fb.id))
                    if a > fund.get(k, (0,))[0]:
                        fund[k] = (a, fa, fb, z)
    for a, fa, fb, z in sorted(fund.values(), key=lambda x: -x[0]):
        par = {fa.klasse, fb.klasse}
        roer = par & {"IfcPipeSegment", "IfcDuctSegment", "IfcFlowSegment", "IfcCableCarrierSegment"}
        if roer and par & VAERT:
            r.add("INFO", "gennemføring", f"{fa.tag} / {fb.tag}: rør eller kanal gennem {(par & VAERT).pop()[3:]} ved z={z:.0f}")
        elif "IfcChimney" in par and par & {"IfcSlab", "IfcRoof"}:
            niveau = "INFO" if _er_tag(fa) or _er_tag(fb) else "ADVARSEL"
            r.add(niveau, "gennemføring", f"{fa.tag} / {fb.tag}: skorsten gennem dæk/tag ved z={z:.0f} uden hul i dækket"
                  + ("" if niveau == "INFO" else " – tilføj huller i daek"))
        else:
            r.add("FEJL" if a > 10000 else "ADVARSEL", "kollision",
                  f"{fa.tag} ({fa.klasse[3:]}) overlapper {fb.tag} ({fb.klasse[3:]}): {a / 1e6:.3f} m² i snit z={z:.0f}")


def _er_tag(fm):
    agg = ue.get_aggregate(fm.ent)
    return fm.klasse == "IfcSlab" and agg is not None and agg.is_a("IfcRoof")


def _ignorer(fa, fb):
    ka, kb = fa.klasse, fb.klasse
    if {ka, kb} <= {"IfcPipeSegment", "IfcDuctSegment"}:
        return str(fa.tag).rsplit(".", 1)[0] == str(fb.tag).rsplit(".", 1)[0]
    if ka == kb == "IfcSlab" and ue.get_aggregate(fa.ent) is not None and ue.get_aggregate(fa.ent) == ue.get_aggregate(fb.ent):
        return True  # tagflader i samme tag mødes ved kip/grat
    return False


def arealer(f, r, former, sidevogn):
    kontrol = (sidevogn or {}).get("kontrol") or {}
    maal = kontrol.get("areal") or {}
    tol = float(kontrol.get("tolerance", 0.05))
    id_til_navn = {k: v["navn"] for k, v in ((sidevogn or {}).get("etager") or {}).items()}
    linjer = []
    for st in sorted(f.by_type("IfcBuildingStorey"), key=lambda s: float(s.Elevation or 0)):
        ude = [fm for fm in former if fm.klasse == "IfcWall" and fm.etage is not None and fm.etage.id() == st.id()
               and ue.get_psets(fm.ent).get("Pset_WallCommon", {}).get("IsExternal")]
        polys = [g for g in (projektion(fm, (np.array([1.0, 0, 0]), np.array([0, 1.0, 0]))) for fm in ude) if g is not None]
        brutto = None
        if polys:
            u = unary_union([p.buffer(5) for p in polys]).buffer(-5)
            dele = [g for g in getattr(u, "geoms", [u]) if g.geom_type == "Polygon"]
            if dele:
                brutto = Polygon(max(dele, key=lambda g: g.area).exterior).area / 1e6
        netto = sum((ue.get_psets(sp).get("Qto_SpaceBaseQuantities", {}) or {}).get("NetFloorArea", 0) or 0
                    for sp in f.by_type("IfcSpace") if ue.get_aggregate(sp) == st)
        linjer.append(f"{st.Name}: brutto (til ydervæggenes yderside) {brutto:.1f} m², rum netto {netto:.1f} m²"
                      if brutto else f"{st.Name}: rum netto {netto:.1f} m²")
        for eid, m2 in maal.items():
            if id_til_navn.get(str(eid), str(eid)) == st.Name and brutto:
                afv = (brutto - float(m2)) / float(m2)
                niveau = "ADVARSEL" if abs(afv) > tol else "INFO"
                r.add(niveau, "areal", f"{st.Name}: brutto {brutto:.1f} m² mod kontrolværdi {m2} m² ({afv:+.1%}, tolerance ±{tol:.0%})")
    for l in linjer:
        r.add("INFO", "areal", l)


# ------------------------------------------------------------------ IDS
def ids_tjek(f, sti, r):
    try:
        import ifctester.ids
        import ifctester.reporter
    except ImportError:
        r.add("ADVARSEL", "ids", "ifctester mangler – kør bim.py opsaet")
        return
    spec = ifctester.ids.open(str(sti))
    spec.validate(f)
    for s in spec.specifications:
        if s.status is False:
            fejlede = [x for req in s.requirements for x in (getattr(req, "failures", None) or [])]
            eks = "; ".join(_navn(x["element"]) + ": " + str(x.get("reason", ""))[:80]
                            for x in fejlede[:3] if isinstance(x, dict) and x.get("element") is not None)
            r.add("FEJL", "ids",
                  f"{sti.name} · {s.name}: {len(fejlede)} fejl" + (f" – {eks}" if eks else ""))
        else:
            r.add("INFO", "ids", f"{sti.name} · {s.name}: bestået")


# ------------------------------------------------------------------ indgang
def tjek(ifc, ids=None, ud=None, tegn=False):
    ifc = pathlib.Path(ifc)
    f = ifcopenshell.open(str(ifc))
    sv_sti = ifc.with_suffix(".byg.json")
    sidevogn = json.loads(sv_sti.read_text(encoding="utf-8")) if sv_sti.exists() else None
    r = Rapport()
    skema(f, r)
    regler(f, r)
    semantik(f, r, sidevogn)
    former = []
    geometri(f, r, former)
    arealer(f, r, former, sidevogn)
    ids_sti = pathlib.Path(ids) if ids else (ASSETS / "ids" / "byg-bolig.ids")
    if ids_sti.exists():
        ids_tjek(f, ids_sti, r)
    ud = pathlib.Path(ud) if ud else ifc.parent
    ud.mkdir(parents=True, exist_ok=True)
    rap = ud / f"{ifc.stem}.tjek.md"
    nf, na = r.antal("FEJL"), r.antal("ADVARSEL")
    lin = [f"# Tjek – {ifc.name}", f"**Dato:** {dt.datetime.now():%Y-%m-%d %H:%M} · **Skema:** {f.schema} · "
           f"**Resultat:** {nf} fejl, {na} advarsler", ""]
    for niveau in ("FEJL", "ADVARSEL", "INFO"):
        pk = [p for p in r.punkter if p[0] == niveau]
        if pk:
            lin.append(f"## {niveau} ({len(pk)})")
            lin += [f"- [{k}] {t}" for _, k, t in pk]
            lin.append("")
    filer = []
    if tegn:
        from .tegn import tegn as tegn_fn
        filer = tegn_fn(ifc, "alle", ud=ud / "tegninger", maal=True)
        lin.append("## Tegninger")
        lin += [f"- {p}" for p in filer]
    rap.write_text("\n".join(lin) + "\n", encoding="utf-8")
    print(f"TJEK {ifc.name}: {nf} fejl, {na} advarsler → {rap}")
    vist = 0
    for niveau in ("FEJL", "ADVARSEL"):
        for _, k, t in [p for p in r.punkter if p[0] == niveau]:
            if vist < 25:
                print(f"  {niveau} [{k}] {t}")
                vist += 1
    if nf + na > vist:
        print(f"  … se resten i {rap.name}")
    for _, k, t in [p for p in r.punkter if p[0] == "INFO" and p[1] in ("areal", "kilde")]:
        print(f"  INFO [{k}] {t}")
    for p in filer:
        print(f"  tegning: {p}")
    return 1 if nf else 0

