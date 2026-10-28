"""Export of the IFC geometry to glTF binary (.glb) for web viewers (model-viewer, three.js) – in the model's colours.

Spaces and openings are left out: the export shows the building as it looks, not the room volumes.
"""
import multiprocessing
import pathlib

import ifcopenshell
import ifcopenshell.geom

SKIP = ["IfcSpace", "IfcOpeningElement", "IfcAnnotation", "IfcGrid", "IfcVirtualElement"]


def export_glb(ifc: pathlib.Path, out: pathlib.Path | None = None) -> int:
    f = ifcopenshell.open(str(ifc))
    out = (out or ifc.with_suffix(".glb")).resolve()
    out.parent.mkdir(parents=True, exist_ok=True)
    elements = [e for e in f.by_type("IfcProduct") if e.Representation and not any(e.is_a(k) for k in SKIP)]
    if not elements:
        print(f"Ingen elementer med geometri i {ifc}")
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
    print(f"EKSPORTERET {out}  ({count} elementer, {out.stat().st_size // 1024} kB)")
    return 0
