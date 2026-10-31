"""Export of the IFC geometry to glTF binary (.glb) for web viewers (model-viewer, three.js) – in the model's colours.

Spaces and openings are left out: the export shows the building as it looks, not the room volumes.
Selected elements (by id/Tag glob) can be made see-through, e.g. two facades, so the structure inside shows.
IFC colours are sRGB, glTF base colours linear: the export converts them, otherwise every colour renders washed out.
Materials are named after their IFC style, and system colours (pipes, ducts) glow slightly so thin pipes stand out.
"""
import fnmatch
import json
import multiprocessing
import pathlib
import struct
import uuid

import ifcopenshell
import ifcopenshell.geom
import ifcopenshell.guid

SKIP = ["IfcSpace", "IfcOpeningElement", "IfcAnnotation", "IfcGrid", "IfcVirtualElement"]


def export_glb(ifc: pathlib.Path, out: pathlib.Path | None = None, transparent=(), alpha: float = 0.15) -> int:
    f = ifcopenshell.open(str(ifc))
    out = (out or ifc.with_suffix(".glb")).resolve()
    out.parent.mkdir(parents=True, exist_ok=True)
    elements = [e for e in f.by_type("IfcProduct") if e.Representation and not any(e.is_a(k) for k in SKIP)]
    if not elements:
        print(f"Ingen elementer med geometri i {ifc}")
        return 1
    see_through = {e.GlobalId: e for e in elements
                   if any(fnmatch.fnmatchcase(getattr(e, "Tag", None) or e.GlobalId, g) for g in transparent)}
    if transparent and not see_through:
        print(f"Ingen elementer matcher --transparent {' '.join(transparent)}")
        return 1
    s = ifcopenshell.geom.settings()
    s.set("use-world-coords", True)
    s.set("weld-vertices", True)
    s.set("apply-default-materials", True)
    ser = ifcopenshell.geom.serializers.glb(str(out), s)
    ser.settings().set_("y-up", True)  # glTF is Y-up; IFC is Z-up
    ser.settings().set_("use-element-names", True)
    ser.setFile(f)
    ser.writeHeader()
    it = ifcopenshell.geom.iterator(s, f, max(1, min(8, multiprocessing.cpu_count())), include=elements)
    count = 0
    if it.initialize():
        while True:
            ser.write(it.get())
            count += 1
            if not it.next():
                break
    ser.finalize()
    del ser, it  # the serializer flushes the file when it is destroyed – before that the .glb on disk is incomplete
    names = {f"product-{uuid.UUID(ifcopenshell.guid.expand(g))}-body" for g in see_through}
    n = _postprocess(out, f, names, alpha)
    extra = f", {n} gennemsigtige" if see_through else ""
    print(f"EKSPORTERET {out}  ({count} elementer{extra}, {out.stat().st_size // 1024} kB)")
    return 0


def _linear(c: float) -> float:
    return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4


def _style_names(f) -> dict:
    """IfcSurfaceStyleShading id → name of the IfcSurfaceStyle that holds it (the serializer names materials by the former)."""
    return {f"IfcSurfaceStyleShading-{sh.id()}": st.Name for st in f.by_type("IfcSurfaceStyle") if st.Name
            for sh in st.Styles if sh.is_a("IfcSurfaceStyleShading")}


def _postprocess(glb: pathlib.Path, f, node_names: set, alpha: float) -> int:
    """Convert the base colours from sRGB to linear, name the materials after their IFC style, let system colours
    glow a little, and give the meshes of the named nodes alpha-blended copies of their materials (shared materials
    stay opaque for everything else). Only the JSON chunk changes; the binary chunk is copied as is."""
    data = glb.read_bytes()
    jlen = struct.unpack_from("<I", data, 12)[0]
    doc = json.loads(data[20:20 + jlen])
    rest = data[20 + jlen:]
    mats, copies, hit = doc.setdefault("materials", []), {}, 0
    styles = _style_names(f)
    for m in mats:
        pbr = m.setdefault("pbrMetallicRoughness", {})
        rgba = pbr.get("baseColorFactor", [0.8, 0.8, 0.8, 1.0])
        pbr["baseColorFactor"] = [round(_linear(c), 4) for c in rgba[:3]] + rgba[3:]
        m["name"] = styles.get(m.get("name"), m.get("name"))
        if str(m["name"]).startswith("system:"):
            m["emissiveFactor"] = [round(c * 0.5, 4) for c in pbr["baseColorFactor"][:3]]
    for node in doc.get("nodes", []):
        if node.get("name") not in node_names or "mesh" not in node:
            continue
        hit += 1
        for prim in doc["meshes"][node["mesh"]]["primitives"]:
            m = prim.get("material")
            if m not in copies:
                base = json.loads(json.dumps(mats[m])) if m is not None else {"pbrMetallicRoughness": {}}
                pbr = base.setdefault("pbrMetallicRoughness", {})
                rgba = list(pbr.get("baseColorFactor", [0.8, 0.8, 0.8, 1.0]))
                pbr["baseColorFactor"] = rgba[:3] + [min(rgba[3], alpha)]
                base.update(alphaMode="BLEND", doubleSided=True, name=f"{base.get('name', 'material')}-transparent")
                mats.append(base)
                copies[m] = len(mats) - 1
            prim["material"] = copies[m]
    js = json.dumps(doc, separators=(",", ":")).encode()
    js += b" " * (-len(js) % 4)
    body = struct.pack("<II", len(js), 0x4E4F534A) + js + rest
    glb.write_bytes(struct.pack("<III", 0x46546C67, 2, 12 + len(body)) + body)
    return hit
