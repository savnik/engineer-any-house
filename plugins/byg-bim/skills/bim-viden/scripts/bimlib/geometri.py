"""Triangulerer en IFC-model (verdenskoordinater, mm) og samler metadata pr. element til tegning og kontrol."""
import multiprocessing

import numpy as np
import ifcopenshell
import ifcopenshell.geom
import ifcopenshell.util.element as ue

UDELAD = ["IfcOpeningElement", "IfcAnnotation", "IfcGrid", "IfcVirtualElement"]


class Form:
    __slots__ = ("ent", "id", "tag", "klasse", "etage", "status", "kilde", "v", "f", "zmin", "zmax", "navn", "pre")

    def __init__(self, ent, v, f, meta):
        self.ent, self.v, self.f = ent, v, f
        self.id = ent.id()
        self.klasse = ent.is_a()
        self.tag = getattr(ent, "Tag", None) or (ent.Name if ent.is_a("IfcSpace") else None) or ent.GlobalId
        self.navn = getattr(ent, "LongName", None) or ent.Name or ""
        self.etage, self.status, self.kilde = meta
        self.zmin, self.zmax = (float(v[:, 2].min()), float(v[:, 2].max())) if len(v) else (0.0, 0.0)
        self.pre = getattr(ent, "PredefinedType", None)


def etage_af(ent):
    c = ue.get_container(ent)
    if c is None:
        agg = ue.get_aggregate(ent)
        if agg is not None and agg.is_a("IfcBuildingStorey"):
            return agg
        if agg is not None:
            return etage_af(agg)
        if ent.is_a("IfcFeatureElementSubtraction") and ent.VoidsElements:
            return etage_af(ent.VoidsElements[0].RelatingBuildingElement)
        return None
    return c if c.is_a("IfcBuildingStorey") else None


def meta(ent):
    st = etage_af(ent)
    psets = ue.get_psets(ent)
    status = None
    for p in psets.values():
        if "Status" in p:
            v = p["Status"]
            status = v[0] if isinstance(v, (list, tuple)) else v
            break
    kilde = str((psets.get("Byg_Kilde") or {}).get("Kilde", ""))[:1] or None
    return (st, status, kilde)


def hent(f, inkl_rum=True, fejl=None):
    """Alle elementer med Body-geometri som Form-objekter (mm, verdenskoordinater)."""
    s = ifcopenshell.geom.settings()
    s.set("use-world-coords", True)
    s.set("weld-vertices", True)
    skala = 1000.0  # geometrimotoren leverer meter; alt herfra er mm
    udelad = [x for x in UDELAD]
    if not inkl_rum:
        udelad.append("IfcSpace")
    elementer = [e for e in f.by_type("IfcProduct") if e.Representation and not any(e.is_a(k) for k in udelad)]
    former = []
    if not elementer:
        return former
    it = ifcopenshell.geom.iterator(s, f, max(1, min(8, multiprocessing.cpu_count())), include=elementer)
    set_ok = set()
    if it.initialize():
        while True:
            sh = it.get()
            ent = f.by_id(sh.id)
            v = np.array(sh.geometry.verts, dtype=float).reshape(-1, 3) * skala
            fa = np.array(sh.geometry.faces, dtype=np.int64).reshape(-1, 3)
            if len(fa):
                former.append(Form(ent, v, fa, meta(ent)))
                set_ok.add(sh.id)
            if not it.next():
                break
    if fejl is not None:
        for e in elementer:
            if e.id() not in set_ok:
                fejl.append(e)
    return former
