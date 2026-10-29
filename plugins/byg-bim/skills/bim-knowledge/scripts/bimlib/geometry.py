"""Triangulates an IFC model (world coordinates, mm) and collects metadata per element for drawings and checks."""
import multiprocessing

import numpy as np
import ifcopenshell
import ifcopenshell.geom
import ifcopenshell.util.element as ue

EXCLUDE = ["IfcOpeningElement", "IfcAnnotation", "IfcGrid", "IfcVirtualElement"]


class Shape:
    __slots__ = ("ent", "id", "tag", "ifc_class", "storey", "status", "source", "v", "f", "zmin", "zmax", "name", "pre")

    def __init__(self, ent, v, f, meta):
        self.ent, self.v, self.f = ent, v, f
        self.id = ent.id()
        self.ifc_class = ent.is_a()
        self.tag = getattr(ent, "Tag", None) or (ent.Name if ent.is_a("IfcSpace") else None) or ent.GlobalId
        self.name = getattr(ent, "LongName", None) or ent.Name or ""
        self.storey, self.status, self.source = meta
        self.zmin, self.zmax = (float(v[:, 2].min()), float(v[:, 2].max())) if len(v) else (0.0, 0.0)
        self.pre = getattr(ent, "PredefinedType", None)


def storey_of(ent):
    c = ue.get_container(ent)
    if c is None:
        agg = ue.get_aggregate(ent)
        if agg is not None and agg.is_a("IfcBuildingStorey"):
            return agg
        if agg is not None:
            return storey_of(agg)
        if ent.is_a("IfcFeatureElementSubtraction") and ent.VoidsElements:
            return storey_of(ent.VoidsElements[0].RelatingBuildingElement)
        return None
    return c if c.is_a("IfcBuildingStorey") else None


def meta(ent):
    st = storey_of(ent)
    psets = ue.get_psets(ent)
    status = None
    for p in psets.values():
        if "Status" in p:
            v = p["Status"]
            status = v[0] if isinstance(v, (list, tuple)) else v
            break
    source = str((psets.get("Byg_Kilde") or {}).get("Kilde", ""))[:1] or None
    return (st, status, source)


def fetch_shapes(f, include_spaces=True, errors=None):
    """All elements with Body geometry as Shape objects (mm, world coordinates)."""
    s = ifcopenshell.geom.settings()
    s.set("use-world-coords", True)
    s.set("weld-vertices", True)
    scale = 1000.0  # the geometry engine delivers metres; everything from here on is mm
    exclude = [x for x in EXCLUDE]
    if not include_spaces:
        exclude.append("IfcSpace")
    elements = [e for e in f.by_type("IfcProduct") if e.Representation and not any(e.is_a(k) for k in exclude)]
    shapes = []
    if not elements:
        return shapes
    it = ifcopenshell.geom.iterator(s, f, max(1, min(8, multiprocessing.cpu_count())), include=elements)
    seen_ok = set()
    if it.initialize():
        while True:
            sh = it.get()
            ent = f.by_id(sh.id)
            v = np.array(sh.geometry.verts, dtype=float).reshape(-1, 3) * scale
            fa = np.array(sh.geometry.faces, dtype=np.int64).reshape(-1, 3)
            if len(fa):
                shapes.append(Shape(ent, v, fa, meta(ent)))
                seen_ok.add(sh.id)
            if not it.next():
                break
    if errors is not None:
        for e in elements:
            if e.id() not in seen_ok:
                errors.append(e)
    return shapes
