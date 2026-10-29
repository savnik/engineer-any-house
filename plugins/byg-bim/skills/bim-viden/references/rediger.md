# Redigering af fremmede IFC-filer (IfcOpenShell 0.9)

Til filer fra arkitekter, rådgivere og producenter. Egne modeller redigeres **kun** i `model.yaml`.

## Arbejdsgang
1. Kopiér originalen til `<sagsmappe>/bim/ind/<navn>.ifc`, og lad den være urørt. Arbejd på `<sagsmappe>/bim/ud/<navn>-rettet.ifc`.
2. `bim.py info <fil>` og `bim.py check <fil>` (baseline). Notér skema, enheder, georeference og fejl.
3. Find elementer: `bim.py find <fil> "IfcWall, /Pset_WallCommon/.IsExternal=TRUE"`, `bim.py show <fil> <GlobalId|#id>`.
4. Ret med `ifcedit` (ét API-kald pr. kommando) eller et kort script (nedenfor).
5. `bim.py diff <original> <rettet>` skal kun vise de tilsigtede ændringer. `bim.py check <rettet>` må ikke have nye fejl.

## ifcquery og ifcedit (ligger i værktøjets miljø)
```
Q=~/.local/share/byg-bim/venv/bin/ifcquery; E=~/.local/share/byg-bim/venv/bin/ifcedit
$Q fil.ifc summary · $Q fil.ifc tree · $Q fil.ifc info <step-id> · $Q fil.ifc select "IfcDoor" · $Q fil.ifc materials
$E list pset · $E docs pset.edit_pset
$E run fil.ifc attribute.edit_attributes --product 123 --attributes '{"Name": "D1"}' -o rettet.ifc   # se 'docs' for argumenter
```

## Scriptskabelon (kør med værktøjets Python)
```python
#!/usr/bin/env -S ~/.local/share/byg-bim/venv/bin/python
import numpy as np, ifcopenshell
import ifcopenshell.api.attribute, ifcopenshell.api.pset, ifcopenshell.api.geometry, ifcopenshell.api.root   # undermoduler SKAL importeres
import ifcopenshell.api.type, ifcopenshell.api.material, ifcopenshell.api.spatial, ifcopenshell.api.feature
import ifcopenshell.util.element as ue, ifcopenshell.util.placement as up, ifcopenshell.util.selector as us
from ifcopenshell import api

f = ifcopenshell.open("ind/model.ifc")
for w in us.filter_elements(f, "IfcWall"):
    api.attribute.edit_attributes(f, product=w, attributes={"Description": "kontrolleret"})
f.write("ud/model-rettet.ifc")
```

| Opgave | 0.9-kald (bemærk `products=[…]` som liste) |
|---|---|
| Attribut | `api.attribute.edit_attributes(f, product=e, attributes={"Name": "…"})` |
| Egenskab (eget sæt) | `p = api.pset.add_pset(f, product=e, name="Byg_X"); api.pset.edit_pset(f, pset=p, properties={...})` |
| Standardsæt med enum (Status) | Brug **ikke** `edit_pset` til enumererede værdier (den skriver IfcLabel): opret `IfcPropertyEnumeratedValue` med `EnumerationReference` fra skabelonen (`ifcopenshell.util.pset.get_template("IFC4").get_by_name(...)`) |
| Flyt element | `M = up.get_local_placement(e.ObjectPlacement).copy(); M[:3, 3] += (dx, dy, dz); api.geometry.edit_object_placement(f, product=e, matrix=M.copy(), is_si=False)` – giv **altid en kopi** |
| Skift type | `api.type.assign_type(f, related_objects=[e], relating_type=t)` |
| Flyt til etage | `api.spatial.assign_container(f, products=[e], relating_structure=etage)` |
| Slet element | `api.root.remove_product(f, product=e)` |
| Materiale | `api.material.assign_material(f, products=[e], type="IfcMaterial", material=m)` |
| Åbning i væg | `api.feature.add_feature(f, feature=aab, element=væg)` · `api.feature.add_filling(f, opening=aab, element=vindue)` |
| Klassifikation | `k = api.classification.add_classification(f, classification="BIM7AA"); api.classification.add_reference(f, products=[e], identification="…", name="…", classification=k)` |

Enheder: API-geometrifunktioner (`add_wall_representation` m.fl.) tager **meter**, ShapeBuilder og rå entiteter tager **projektenheder** (ofte mm). Tjek med `ifcopenshell.util.unit.calculate_unit_scale(f)`.

## ifcpatch (hele filen)
```
~/.local/share/byg-bim/venv/bin/python -m ifcpatch -i ind.ifc -o ud.ifc -r Migrate -a IFC2X3        # skemakonvertering
~/.local/share/byg-bim/venv/bin/python -m ifcpatch -i ind.ifc -o ud.ifc -r ExtractElements -a "IfcWall"
~/.local/share/byg-bim/venv/bin/python -m ifcpatch -i ind.ifc -o ud.ifc -r ResetAbsoluteCoordinates
```
Recepter: docs.ifcopenshell.org/autoapi/ifcpatch/recipes/index.html. Kontrollér altid resultatet med `check` og `diff`.
