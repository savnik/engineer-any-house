"""Inspektion af (også fremmede) IFC-modeller: info, vis, find og diff. Korte udskrifter."""
import collections
import pathlib

import numpy as np
import ifcopenshell
import ifcopenshell.util.element as ue
import ifcopenshell.util.placement as up
import ifcopenshell.util.selector as us
import ifcopenshell.util.unit as uu


def _etage(e):
    c = ue.get_container(e)
    if c is None:
        a = ue.get_aggregate(e)
        while a is not None and not a.is_a("IfcBuildingStorey"):
            c2 = ue.get_container(a)
            if c2 is not None:
                return c2
            a = ue.get_aggregate(a)
        return a
    return c


def info(ifc: pathlib.Path) -> int:
    f = ifcopenshell.open(str(ifc))
    h = f.header.file_name
    print(f"{ifc.name}: {f.schema} · {ifc.stat().st_size // 1024} kB · program: {h.originating_system or '?'} · "
          f"enhed: {uu.get_project_unit(f, 'LENGTHUNIT').Prefix or ''}{uu.get_project_unit(f, 'LENGTHUNIT').Name}")
    p = f.by_type("IfcProject")
    print(f"Projekt: {p[0].Name if p else '-'} · grund: {', '.join(s.Name or '?' for s in f.by_type('IfcSite'))}"
          f" · bygning: {', '.join(b.Name or '?' for b in f.by_type('IfcBuilding'))}")
    mc = f.by_type("IfcMapConversion")
    if mc:
        m = mc[0]
        print(f"Georeference: {getattr(m.TargetCRS, 'Name', '?')} E {m.Eastings} N {m.Northings} H {m.OrthogonalHeight} "
              f"skala {m.Scale}")
    else:
        print("Georeference: ingen")
    pr_etage = collections.defaultdict(collections.Counter)
    for e in f.by_type("IfcElement"):
        if e.is_a("IfcFeatureElement"):
            continue
        st = _etage(e)
        pr_etage[st.Name if st else "(uden etage)"][e.is_a()[3:]] += 1
    for st in sorted(f.by_type("IfcBuildingStorey"), key=lambda s: float(s.Elevation or 0)):
        rum = [s for s in f.by_type("IfcSpace") if ue.get_aggregate(s) == st]
        c = pr_etage.get(st.Name, {})
        print(f"  {st.Name} (kote {float(st.Elevation or 0):+.0f}): {len(rum)} rum · "
              + ", ".join(f"{k} {n}" for k, n in sorted(c.items())))
    if "(uden etage)" in pr_etage:
        print("  (uden etage): " + ", ".join(f"{k} {n}" for k, n in sorted(pr_etage["(uden etage)"].items())))
    psets = collections.Counter(ps.Name for ps in f.by_type("IfcPropertySet"))
    print("Egenskabssæt: " + ", ".join(f"{k} {n}" for k, n in psets.most_common(12)))
    kl = f.by_type("IfcClassification")
    if kl:
        print("Klassifikation: " + ", ".join(k.Name for k in kl))
    print(f"Materialer: {len(f.by_type('IfcMaterial'))} · typer: {len(f.by_type('IfcTypeObject'))} · "
          f"systemer: {len(f.by_type('IfcSystem'))} · egen model (Byg_Kilde): {'ja' if 'Byg_Kilde' in psets else 'nej'}")
    return 0


def _find_en(f, noegle):
    if noegle.startswith("#"):
        return f.by_id(int(noegle[1:]))
    try:
        return f.by_guid(noegle)
    except RuntimeError:
        pass
    for e in f.by_type("IfcProduct"):
        if getattr(e, "Tag", None) == noegle or e.Name == noegle:
            return e
    return None


def vis(ifc: pathlib.Path, noegle: str) -> int:
    f = ifcopenshell.open(str(ifc))
    e = _find_en(f, noegle)
    if e is None:
        print(f"Ikke fundet: {noegle} (brug Tag/spec-id, Name, GlobalId eller #step-id)")
        return 1
    st = _etage(e)
    print(f"#{e.id()} {e.is_a()} '{e.Name}' Tag={getattr(e, 'Tag', None)} GlobalId={e.GlobalId}")
    pre = getattr(e, "PredefinedType", None)
    print(f"  PredefinedType={pre} ObjectType={getattr(e, 'ObjectType', None)} etage={st.Name if st else '-'}")
    t = ue.get_type(e)
    if t:
        print(f"  type: #{t.id()} {t.is_a()} '{t.Name}'")
    m = ue.get_material(e)
    if m is not None:
        if m.is_a("IfcMaterialLayerSetUsage"):
            ls = m.ForLayerSet
            print(f"  materiale: lag ({m.LayerSetDirection} {m.DirectionSense} offset {m.OffsetFromReferenceLine}): "
                  + " | ".join(f"{l.Material.Name} {l.LayerThickness:g}" for l in ls.MaterialLayers))
        elif m.is_a("IfcMaterialLayerSet"):
            print("  materiale: " + " | ".join(f"{l.Material.Name} {l.LayerThickness:g}" for l in m.MaterialLayers))
        else:
            print(f"  materiale: {getattr(m, 'Name', m.is_a())}")
    if getattr(e, "ObjectPlacement", None):
        M = up.get_local_placement(e.ObjectPlacement)
        print(f"  placering (mm): origo {np.round(M[:3, 3], 1).tolist()} x-akse {np.round(M[:3, 0], 3).tolist()}")
    for navn, props in ue.get_psets(e).items():
        props = {k: v for k, v in props.items() if k != "id"}
        print(f"  {navn}: " + ", ".join(f"{k}={v}" for k, v in props.items()))
    for attr in ("OverallWidth", "OverallHeight", "OperationType", "LongName", "Elevation"):
        if hasattr(e, attr) and getattr(e, attr) is not None:
            print(f"  {attr}={getattr(e, attr)}")
    if e.is_a("IfcElement"):
        aab = [r.RelatedOpeningElement for r in getattr(e, "HasOpenings", []) or []]
        if aab:
            print("  åbninger: " + ", ".join((o.Tag or o.Name or "?") for o in aab))
        if getattr(e, "FillsVoids", None):
            print(f"  fylder åbning i: {_navn(e.FillsVoids[0].RelatingOpeningElement.VoidsElements[0].RelatingBuildingElement)}")
    return 0


def _navn(e):
    return getattr(e, "Tag", None) or e.Name or f"#{e.id()}"


def find(ifc: pathlib.Path, selector: str) -> int:
    f = ifcopenshell.open(str(ifc))
    try:
        res = us.filter_elements(f, selector)
    except Exception as ex:
        print(f"Ugyldig selector: {ex}\nEksempler: 'IfcWall' · 'IfcWall, /Pset_WallCommon/.IsExternal=TRUE' · "
              "'IfcDoor, Name=D1' · 'IfcElement, location=\"Kælder\"'")
        return 1
    res = sorted(res, key=lambda e: e.id())
    for e in res[:100]:
        st = _etage(e) if e.is_a("IfcProduct") else None
        print(f"#{e.id()} {e.is_a()} {_navn(e)} {e.GlobalId} {st.Name if st else ''}")
    print(f"{len(res)} fundet" + (" (viser 100)" if len(res) > 100 else ""))
    return 0


def diff(gammel: pathlib.Path, ny: pathlib.Path) -> int:
    from ifcdiff import IfcDiff
    a, b = ifcopenshell.open(str(gammel)), ifcopenshell.open(str(ny))
    import contextlib
    import io
    d = IfcDiff(a, b, relationships=["geometry", "attributes", "type", "property", "container", "aggregate"])
    with contextlib.redirect_stdout(io.StringIO()):
        d.diff()
    print(f"Tilføjet {len(d.added_elements)} · slettet {len(d.deleted_elements)} · ændret {len(d.change_register)}")
    for g in list(d.added_elements)[:30]:
        e = b.by_guid(g)
        print(f"  + {e.is_a()} {_navn(e)}")
    for g in list(d.deleted_elements)[:30]:
        e = a.by_guid(g)
        print(f"  - {e.is_a()} {_navn(e)}")
    for g, ch in list(d.change_register.items())[:40]:
        e = b.by_guid(g)
        print(f"  ~ {e.is_a()} {_navn(e)}: {', '.join(sorted(k for k, v in ch.items() if v))}")
    return 0
