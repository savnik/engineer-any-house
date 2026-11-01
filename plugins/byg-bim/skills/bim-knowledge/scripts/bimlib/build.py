"""Deterministic generator: model spec → IFC (IFC4 by default).

Rules enforced here (buildingSMART Validation Service / Implementer Agreements):
- IfcProject → IfcSite → IfcBuilding → IfcBuildingStorey via IfcRelAggregates; IfcSpace is aggregated under the storey.
- Every element is contained in exactly one storey; openings via IfcRelVoidsElement, doors/windows via IfcRelFillsElement.
- IfcWall (not StandardCase) with IfcWallType + IfcMaterialLayerSetUsage; PredefinedType on the type, not the occurrence.
- Pset_*: only properties from the standard template; enumerated properties (e.g. Status) as IfcPropertyEnumeratedValue.
- Qto_*: MethodOfMeasurement = BaseQuantities. Custom sets are named Byg_* (never Pset_).
- Georeference: IfcMapConversion + IfcProjectedCRS (EPSG:25832, DVR90 = EPSG:5799), Scale 0.001 for mm.
  geo.hoejdesystem (default DVR90): anything other than DVR90 → VerticalDatum $ and the height system in Description.
- Stable GlobalIds: uuid5 of model name + element id, so ids survive a rebuild.
- Display groups: every element and system is assigned one discipline IfcGroup (Bygning, Tag, VVS …) via
  IfcRelAssignsToGroup – the spatial structure (storeys) is unchanged. The spec's `grupper:` overrides/extends.
"""
import datetime as dt
import json
import math
import pathlib
import uuid

import numpy as np
import ifcopenshell
import ifcopenshell.api.aggregate
import ifcopenshell.api.classification
import ifcopenshell.api.context
import ifcopenshell.api.feature
import ifcopenshell.api.geometry
import ifcopenshell.api.georeference
import ifcopenshell.api.group
import ifcopenshell.api.material
import ifcopenshell.api.project
import ifcopenshell.api.pset
import ifcopenshell.api.root
import ifcopenshell.api.spatial
import ifcopenshell.api.style
import ifcopenshell.api.system
import ifcopenshell.api.type
import ifcopenshell.api.unit
import ifcopenshell.guid
import ifcopenshell.util.pset
from ifcopenshell import api
from ifcopenshell.util.shape_builder import ShapeBuilder
from shapely.geometry import LineString, Point, Polygon, box
from shapely.ops import unary_union

from . import VERSION
from .geo import (WallGeo, ccw, unit, face_frame, local_polygon, outline_from_walls, clean_ring, room_polygon,
                  roof_faces, to_face_2d, wall_joins)
from .spec import SOURCES, STATUS, SYSTEM_KINDS

NS = uuid.UUID("6f1d3c52-8a4e-4b7e-9a51-0b1d2c3e4f50")

# art → (IFC class, PredefinedType). USERDEFINED gets ObjectType = art.
INSTALLATIONS = {
    "kedel": ("IfcBoiler", "WATER"), "pillefyr": ("IfcBoiler", "WATER"),
    "fjernvarmeunit": ("IfcHeatExchanger", "PLATE"), "varmeveksler": ("IfcHeatExchanger", "PLATE"),
    "varmepumpe": ("IfcUnitaryEquipment", "USERDEFINED"), "beholder": ("IfcTank", "STORAGE"),
    "buffertank": ("IfcTank", "STORAGE"), "ekspansionsbeholder": ("IfcTank", "EXPANSION"),
    "radiator": ("IfcSpaceHeater", "RADIATOR"), "konvektor": ("IfcSpaceHeater", "CONVECTOR"),
    "fordeler": ("IfcPipeFitting", "JUNCTION"), "pumpe": ("IfcPump", "CIRCULATOR"),
    "draenpumpe": ("IfcPump", "SUMPPUMP"), "ventil": ("IfcValve", "ISOLATING"), "blandeventil": ("IfcValve", "MIXING"),
    "sikkerhedsventil": ("IfcValve", "SAFETYVALVE"), "kontraventil": ("IfcValve", "CHECK"),
    "vandmaaler": ("IfcFlowMeter", "WATERMETER"), "energimaaler": ("IfcFlowMeter", "ENERGYMETER"),
    "wc": ("IfcSanitaryTerminal", "TOILETPAN"), "haandvask": ("IfcSanitaryTerminal", "WASHHANDBASIN"),
    "koekkenvask": ("IfcSanitaryTerminal", "SINK"), "bruser": ("IfcSanitaryTerminal", "SHOWER"),
    "badekar": ("IfcSanitaryTerminal", "BATH"), "gulvafloeb": ("IfcWasteTerminal", "FLOORTRAP"),
    "broend": ("IfcDistributionChamberElement", "INSPECTIONCHAMBER"),
    "tavle": ("IfcElectricDistributionBoard", "DISTRIBUTIONBOARD"), "stikkontakt": ("IfcOutlet", "POWEROUTLET"),
    "lampe": ("IfcLightFixture", "POINTSOURCE"), "afbryder": ("IfcSwitchingDevice", "TOGGLESWITCH"),
    "kraftstik": ("IfcOutlet", "POWEROUTLET"), "data": ("IfcOutlet", "DATAOUTLET"), "pir": ("IfcSensor", "MOVEMENTSENSOR"),
    "ventilationsaggregat": ("IfcUnitaryEquipment", "AIRHANDLER"), "ventilator": ("IfcFan", "PROPELLORAXIAL"),
    "luftventil": ("IfcAirTerminal", "DIFFUSER"), "emhaette": ("IfcAirTerminal", "USERDEFINED"),
    "solcellepanel": ("IfcSolarDevice", "SOLARPANEL"), "skorsten": ("IfcChimney", "NOTDEFINED"),
}
# Display groups (IfcGroup) – id: (name, parent group). Shown in Bonsai under Scene › Groups (show/hide/isolate).
STANDARD_GROUPS = {
    "BYGNING": ("Bygning", None), "TAG": ("Tag", None), "RUM": ("Rum", None), "INVENTAR": ("Inventar", None),
    "VVS": ("VVS", None), "VVS-BV": ("VVS – brugsvand", "VVS"), "VVS-VARME": ("VVS – varme", "VVS"),
    "VVS-GAS": ("VVS – gas", "VVS"), "KLOAK": ("Kloak og afløb", None), "VENTILATION": ("Ventilation", None),
    "EL": ("El", None), "OEVRIGE": ("Øvrige installationer", None),
}
SYSTEM_GROUP = {"varme": "VVS-VARME", "brugsvand_koldt": "VVS-BV", "brugsvand_varmt": "VVS-BV", "gas": "VVS-GAS",
                "afloeb": "KLOAK", "regnvand": "KLOAK", "ventilation": "VENTILATION", "el": "EL", "andet": "OEVRIGE"}
KIND_GROUP = {  # installations without a system
    **dict.fromkeys(("kedel", "pillefyr", "fjernvarmeunit", "varmeveksler", "buffertank", "ekspansionsbeholder",
                     "radiator", "konvektor", "energimaaler"), "VVS-VARME"),
    **dict.fromkeys(("beholder", "vandmaaler", "wc", "haandvask", "koekkenvask", "bruser", "badekar"), "VVS-BV"),
    **dict.fromkeys(("fordeler", "pumpe", "ventil", "blandeventil", "sikkerhedsventil", "kontraventil"), "VVS"),
    **dict.fromkeys(("gulvafloeb", "broend", "draenpumpe"), "KLOAK"),
    **dict.fromkeys(("tavle", "stikkontakt", "kraftstik", "data", "lampe", "afbryder", "pir", "solcellepanel"), "EL"),
    **dict.fromkeys(("ventilationsaggregat", "ventilator", "luftventil", "emhaette"), "VENTILATION"),
    "skorsten": "BYGNING",
}
CLASS_GROUP = (  # (IFC class, group) for elements without art/system; first match wins
    ("IfcRoof", "TAG"), ("IfcSpace", "RUM"), ("IfcFurnishingElement", "INVENTAR"), ("IfcFurniture", "INVENTAR"),
    ("IfcWasteTerminal", "KLOAK"), ("IfcAirTerminal", "VENTILATION"), ("IfcFlowMovingDevice", "OEVRIGE"),
    ("IfcDuctSegment", "VENTILATION"), ("IfcDuctFitting", "VENTILATION"), ("IfcLightFixture", "EL"),
    ("IfcOutlet", "EL"), ("IfcSwitchingDevice", "EL"), ("IfcElectricDistributionBoard", "EL"),
    ("IfcDistributionElement", "VVS"), ("IfcBuildingElementProxy", "BYGNING"), ("IfcElement", "BYGNING"),
)
MATERIAL_COLOURS = [  # (keywords, category, rgb, transparency)
    (("glas",), "glass", (0.62, 0.80, 0.90), 0.6), (("letbeton", "gasbeton", "leca", "blok"), "block", (0.86, 0.86, 0.82), 0),
    (("beton", "terrazzo"), "concrete", (0.74, 0.74, 0.71), 0), (("tegl", "mursten", "tagsten"), "brick", (0.70, 0.36, 0.26), 0),
    (("træ", "trae", "spær", "spaer", "lægte", "laegte", "krydsfiner", "planke", "bjælke", "bjaelke", "limtræ"), "wood",
     (0.80, 0.64, 0.43), 0),
    (("stål", "staal", "jern", "zink", "alu"), "steel", (0.56, 0.58, 0.62), 0),
    (("isolering", "mineraluld", "stenuld", "glasuld", "eps", "xps", "pir", "papiruld"), "insulation", (0.96, 0.86, 0.42), 0),
    (("gips", "fermacell"), "gypsum", (0.95, 0.95, 0.94), 0), (("puds", "mørtel", "moertel", "kalk"), "plaster",
                                                              (0.91, 0.89, 0.83), 0),
    (("pex", "pvc", "pe", "plast", "pp", "membran", "folie", "pap"), "plastic", (0.88, 0.88, 0.93), 0),
    (("kobber",), "copper", (0.80, 0.50, 0.30), 0), (("eternit", "fibercement", "skifer"), "stone", (0.58, 0.60, 0.60), 0),
    (("jord", "sand", "grus", "sten", "ral"), "earth", (0.60, 0.50, 0.36), 0),
]
CLASS_COLOUR = {"IfcSpace": ((0.55, 0.75, 0.95), 0.85), "IfcWindow": ((0.62, 0.80, 0.90), 0.5),
               "IfcDoor": ((0.66, 0.50, 0.34), 0), "IfcStair": ((0.80, 0.64, 0.43), 0),
               "roer": ((0.85, 0.20, 0.20), 0), "installation": ((0.93, 0.93, 0.95), 0)}


def _mat(name):
    n = name.lower()
    for words, category, rgb, tr in MATERIAL_COLOURS:
        if any(o in n for o in words):
            return category, rgb, tr
    return None, (0.80, 0.80, 0.80), 0


class Builder:
    def __init__(self, spec: dict):
        self.s = spec
        self.m = spec["model"]
        self.f = None
        self.errors, self.warnings = [], []
        self._mats, self._styles, self._types, self._classifications = {}, {}, {}, {}
        self.elements = {}  # spec id → info for the sidecar file
        self.wallgeo = {}

    # ------------------------------------------------------------------ basics
    def guid(self, key):
        return ifcopenshell.guid.compress(uuid.uuid5(NS, f"{self.m['navn']}|{key}").hex)

    def build(self):
        self.f = api.project.create_file(version=self.m["schema"])
        self.b = ShapeBuilder(self.f)
        self._project()
        self._materials_and_types()
        self._walls()
        self._openings()
        self._slabs()
        self._roofs_and_clip()
        self._skylights()
        self._rafters()
        self._stairs()
        self._columns_beams()
        self._spaces()
        self._systems()
        self._installations()
        self._pipes()
        self._generic()
        self._groups()
        self._stable_guids()
        return self.f

    def _project(self):
        f, m = self.f, self.m
        self.project = api.root.create_entity(f, ifc_class="IfcProject", name=m.get("projekt", m["navn"]))
        self.project.GlobalId = self.guid("projekt")
        mm = api.unit.add_si_unit(f, unit_type="LENGTHUNIT", prefix="MILLI")
        api.unit.assign_unit(f, units=[mm, api.unit.add_si_unit(f, unit_type="AREAUNIT"),
                                       api.unit.add_si_unit(f, unit_type="VOLUMEUNIT"),
                                       api.unit.add_si_unit(f, unit_type="PLANEANGLEUNIT")])
        model = api.context.add_context(f, context_type="Model")
        self.body = api.context.add_context(f, context_type="Model", context_identifier="Body",
                                            target_view="MODEL_VIEW", parent=model)
        self.axis = api.context.add_context(f, context_type="Model", context_identifier="Axis",
                                            target_view="GRAPH_VIEW", parent=model)
        self.model_ctx = model
        self.site = self._spatial("IfcSite", "site", m.get("grund", "Grund"))
        self.building = self._spatial("IfcBuilding", "bygning", (m.get("bygning") or {}).get("navn", m["navn"]))
        api.aggregate.assign_object(f, relating_object=self.project, products=[self.site])
        api.aggregate.assign_object(f, relating_object=self.site, products=[self.building])
        for ent in (self.site, self.building):
            self._place(ent, np.eye(4))
        self.storeys, self.storey_level = {}, {}
        for e in self.s["etager"]:
            st = self._spatial("IfcBuildingStorey", f"etage:{e['id']}", e["navn"])
            st.Elevation = e["kote"]
            api.aggregate.assign_object(f, relating_object=self.building, products=[st])
            self._place(st, self._T((0, 0, e["kote"])))
            self.storeys[e["id"]] = st
            self.storey_level[e["id"]] = e["kote"]
            self._pset(st, "Pset_BuildingStoreyCommon", {"AboveGround": e["kote"] >= -500})
        self.storey_info = {e["id"]: e for e in self.s["etager"]}
        a = m.get("adresse")
        if a:
            adr = f.createIfcPostalAddress(AddressLines=[a.get("vej", "")],
                                          PostalCode=str(a.get("postnr", "")), Town=a.get("by"),
                                          Country=a.get("land", "Danmark"))
            self.building.BuildingAddress = adr
        bg = m.get("bygning") or {}
        props = {}
        if bg.get("opfoerelsesaar"):
            props["YearOfConstruction"] = str(bg["opfoerelsesaar"])
        if bg.get("anvendelse"):
            props["OccupancyType"] = str(bg["anvendelse"])
        if "fredet" in bg:
            props["IsLandmarked"] = bool(bg["fredet"])
        props["NumberOfStoreys"] = len(self.s["etager"])
        self._pset(self.building, "Pset_BuildingCommon", props)
        g = m.get("geo")
        if g:
            self._georef(g, mm)

    def _georef(self, g, mm):
        f = self.f
        b = math.radians(float(g.get("x_retning", 90)))  # compass bearing (degrees from north, clockwise) of local +x
        hs = str(g.get("hoejdesystem", "DVR90")).strip()  # height system for levels; only DVR90 gives VerticalDatum EPSG:5799
        dvr = hs.upper() == "DVR90"
        api.georeference.add_georeferencing(f, ifc_class="IfcMapConversion", name="EPSG:25832")
        meter = f.createIfcSIUnit(UnitType="LENGTHUNIT", Name="METRE")
        api.georeference.edit_georeferencing(
            f, coordinate_operation={"Eastings": float(g["oest"]), "Northings": float(g["nord"]),
                                     "OrthogonalHeight": float(g.get("kote", 0.0)), "XAxisAbscissa": math.sin(b),
                                     "XAxisOrdinate": math.cos(b), "Scale": 0.001},
            projected_crs={"Name": "EPSG:25832", "Description": f"ETRS89 / UTM zone 32N, højder {hs}" if not dvr
                           else "ETRS89 / UTM zone 32N, højder DVR90",
                           "GeodeticDatum": "ETRS89", "VerticalDatum": "EPSG:5799" if dvr else None, "MapUnit": meter})
        try:
            api.georeference.edit_true_north(f, true_north=(math.cos(b), math.sin(b)))
        except Exception as e:  # true north is nice to have, not critical
            self.warnings.append(f"geo: true north kunne ikke sættes ({e})")

    def _spatial(self, ifc_class, key, name):
        ent = api.root.create_entity(self.f, ifc_class=ifc_class, name=name)
        ent.GlobalId = self.guid(key)
        return ent

    @staticmethod
    def _T(t=(0, 0, 0), x=(1, 0, 0), z=(0, 0, 1)):
        z = unit(z)
        x = unit(np.asarray(x, float) - z * (np.asarray(x, float) @ z))
        y = np.cross(z, x)
        M = np.eye(4)
        M[:3, 0], M[:3, 1], M[:3, 2], M[:3, 3] = x, y, z, t
        return M

    def _place(self, ent, M):
        # edit_object_placement modifies the matrix in place (unit conversion) – always pass a copy
        api.geometry.edit_object_placement(self.f, product=ent, matrix=np.array(M, dtype=float), is_si=False)

    # ------------------------------------------------------------------ materials, styles, types
    def material(self, name):
        if name in self._mats:
            return self._mats[name]
        info = (self.s.get("materialer") or {}).get(name) or {}
        category, rgb, tr = _mat(name)
        category = info.get("kategori", category)
        if info.get("farve"):
            rgb = tuple(info["farve"])
        mat = api.material.add_material(self.f, name=name, category=category)
        style = self.style(f"mat:{name}", rgb, info.get("gennemsigtighed", tr))
        api.style.assign_material_style(self.f, material=mat, style=style, context=self.body)
        self._mats[name] = mat
        return mat

    def style(self, key, rgb, transp=0.0):
        if key in self._styles:
            return self._styles[key]
        st = api.style.add_style(self.f, name=key.split(":", 1)[-1])
        api.style.add_surface_style(self.f, style=st, ifc_class="IfcSurfaceStyleShading", attributes={
            "SurfaceColour": {"Name": None, "Red": rgb[0], "Green": rgb[1], "Blue": rgb[2]},
            "Transparency": float(transp)})
        self._styles[key] = st
        return st

    def _paint(self, rep, key, rgb=None, transp=0.0):
        if rgb is None:
            category, rgb, transp = _mat(key)
        api.style.assign_representation_styles(self.f, shape_representation=rep,
                                               styles=[self.style(f"farve:{key}", rgb, transp)])

    def _materials_and_types(self):
        f = self.f
        for type_id, t in self.s["typer"].items():
            kind = t["klasse"]
            ifc = {"vaeg": "IfcWallType", "daek": "IfcSlabType", "tag": "IfcSlabType", "vindue": "IfcWindowType",
                   "doer": "IfcDoorType"}[kind]
            pre = t.get("predefined")
            if not pre:
                pre = {"vaeg": "SOLIDWALL" if t.get("ude") else ("STANDARD" if t.get("baerende") else "PARTITIONING"),
                       "daek": "FLOOR", "tag": "ROOF", "vindue": "WINDOW", "doer": "DOOR"}[kind]
            typ = api.root.create_entity(f, ifc_class=ifc, name=t.get("navn", type_id), predefined_type=pre)
            typ.GlobalId = self.guid(f"type:{type_id}")
            if t.get("beskrivelse"):
                typ.Description = t["beskrivelse"]
            if kind in ("vaeg", "daek", "tag"):
                ls = api.material.add_material_set(f, name=t.get("navn", type_id), set_type="IfcMaterialLayerSet")
                for mat_name, thick in t["lag"]:
                    layer = api.material.add_layer(f, layer_set=ls, material=self.material(mat_name))
                    api.material.edit_layer(f, layer=layer, attributes={"LayerThickness": float(thick), "Name": mat_name})
                api.material.assign_material(f, products=[typ], type="IfcMaterialLayerSet", material=ls)
                t["_tykkelse"] = sum(x[1] for x in t["lag"])
                t["_lagsaet"] = ls
            elif kind == "vindue":
                typ.PartitioningType = {1: "SINGLE_PANEL", 2: "DOUBLE_PANEL_VERTICAL", 3: "TRIPLE_PANEL_VERTICAL"}.get(
                    int(t.get("felter", 1)), "SINGLE_PANEL")
            elif kind == "doer":
                # single leaf: NOTDEFINED on the type – left/right is set on each door
                typ.OperationType = {"enkelt": "NOTDEFINED", "dobbelt": "DOUBLE_DOOR_SINGLE_SWING",
                                     "skyde": "SLIDING_TO_LEFT"}.get(t.get("betjening", "enkelt"), "NOTDEFINED")
            common = {"vaeg": "Pset_WallCommon", "daek": "Pset_SlabCommon", "tag": "Pset_SlabCommon",
                      "vindue": "Pset_WindowCommon", "doer": "Pset_DoorCommon"}[kind]
            props = {"Reference": type_id}
            if kind not in ("vindue", "doer") or "ude" in t:  # doors/windows inherit IsExternal from the wall per occurrence
                props["IsExternal"] = bool(t.get("ude", kind == "tag"))
            if "baerende" in t and kind in ("vaeg", "daek", "tag"):
                props["LoadBearing"] = bool(t["baerende"])
            if "u" in t:
                props["ThermalTransmittance"] = float(t["u"])
            if "brand" in t:
                props["FireRating"] = str(t["brand"])
            self._pset(typ, common, props)
            self._user_data(typ, t, f"typer.{type_id}")
            self._types[type_id] = typ

    # ------------------------------------------------------------------ common to all elements
    def new_entity(self, ifc_class, el, suffix="", name=None, predefined=None, object_type=None):
        if predefined == "USERDEFINED" and not object_type:
            object_type = el.get("art") or el.get("navn") or el["id"]
        ent = api.root.create_entity(self.f, ifc_class=ifc_class, name=name or el.get("navn") or el["id"],
                                     predefined_type=predefined)
        ent.GlobalId = self.guid(el["id"] + suffix)
        if hasattr(ent, "Tag"):
            ent.Tag = el["id"] + suffix
        if el.get("beskrivelse"):
            ent.Description = el["beskrivelse"]
        if object_type and hasattr(ent, "ObjectType"):
            ent.ObjectType = object_type
        return ent

    def insert(self, ent, el, M, common=None, props=None, section="", suffix=""):
        """Container, placement, properties and source data for an element."""
        st = self.storeys[el["etage"]]
        api.spatial.assign_container(self.f, products=[ent], relating_structure=st)
        self._place(ent, M)
        self.properties(ent, el, common, props or {}, section)
        self.elements[el["id"] + suffix] = {"guid": ent.GlobalId, "klasse": ent.is_a(), "etage": el["etage"],
                                             "status": el["status"], "kilde": str(el["kilde"])[:1], "sektion": section}

    def properties(self, ent, el, common, props, section):
        props = dict(props)
        status = STATUS[el["status"]]
        tpl_name = common or self._common_pset(ent.is_a())
        if tpl_name and self._has_prop(tpl_name, "Status"):
            props["Status"] = status
        if tpl_name and props:
            self._pset(ent, tpl_name, props)
        source = str(el["kilde"])
        k = {"Kilde": SOURCES.get(source[:1], source) + (source[1:] if len(source) > 1 else ""),
             "Reference": str(el.get("ref") or "")}
        if not (tpl_name and self._has_prop(tpl_name, "Status")):
            k["Status"] = status
        if el.get("usikkerhed") is not None:
            k["Usikkerhed_mm"] = float(el["usikkerhed"])
        if el.get("fakta"):
            k["Fakta"] = ", ".join(map(str, el["fakta"])) if isinstance(el["fakta"], list) else str(el["fakta"])
        if el.get("note"):
            k["Note"] = str(el["note"])
        p = api.pset.add_pset(self.f, product=ent, name="Byg_Kilde")
        api.pset.edit_pset(self.f, pset=p, properties={a: v for a, v in k.items() if v != ""})
        self._user_data(ent, el, f"{section}.{el['id']}")

    def _user_data(self, ent, el, path):
        for pset_name, pv in (el.get("egenskaber") or {}).items():
            if pset_name.lower().startswith("qto_") or (pset_name.lower().startswith("pset") and not pset_name.startswith("Pset_")):
                self.errors.append(f"{path}.egenskaber: '{pset_name}' – egne sæt må ikke starte med 'pset'/'qto'")
                continue
            if not isinstance(pv, dict):
                self.errors.append(f"{path}.egenskaber.{pset_name}: skal være en mapping af egenskaber")
                continue
            self._pset(ent, pset_name, pv, path=path)
        classif = el.get("klassifikation")
        if classif:
            system = classif.get("system", "BIM7AA")
            if system not in self._classifications:
                self._classifications[system] = api.classification.add_classification(self.f, classification=system)
            api.classification.add_reference(self.f, products=[ent], identification=str(classif.get("kode", "")),
                                             name=classif.get("navn"), classification=self._classifications[system])

    def _tpl(self):
        if not hasattr(self, "_tplc"):
            self._tplc = ifcopenshell.util.pset.get_template(self.m["schema"])
        return self._tplc

    def _common_pset(self, ifc_class):
        candidates = [p.Name for p in self._tpl().get_applicable(ifc_class, pset_only=True)]
        name = f"Pset_{ifc_class[3:]}Common"
        if name in candidates:
            return name
        typ = f"Pset_{ifc_class[3:]}TypeCommon"
        if typ in candidates:
            return typ
        return next((n for n in candidates if n.endswith("Common") and n != "Pset_ElectricalDeviceCommon"), None)

    def _has_prop(self, pset_name, prop):
        t = self._tpl().get_by_name(pset_name)
        return bool(t) and any(p.Name == prop for p in t.HasPropertyTemplates)

    def _pset(self, ent, name, props, path=None):
        """Standard sets (Pset_*) are built directly from the template's data types – enumerated properties as
        IfcPropertyEnumeratedValue (PSE001). Custom sets (Byg_* etc.) get types inferred from the Python value."""
        if not props:
            return
        if not name.startswith("Pset_"):
            pset = api.pset.add_pset(self.f, product=ent, name=name)
            api.pset.edit_pset(self.f, pset=pset, properties=props)
            return
        t = self._tpl().get_by_name(name)
        if not t:
            self.errors.append(f"{path or ent.Name}: '{name}' er ikke et standardsæt i {self.m['schema']}")
            return
        new_props = []
        for k, v in props.items():
            pt = next((p for p in t.HasPropertyTemplates if p.Name == k), None)
            if not pt:
                self.errors.append(f"{path or ent.Name}: '{k}' findes ikke i {name}")
                continue
            if pt.TemplateType == "P_ENUMERATEDVALUE":
                allowed = [x.wrappedValue for x in pt.Enumerators.EnumerationValues]
                vs = [str(x).upper() for x in (v if isinstance(v, list) else [v])]
                if any(x not in allowed for x in vs):
                    self.errors.append(f"{path or ent.Name}: {name}.{k} skal være en af {allowed}, fik {v}")
                    continue
                new_props.append(self.f.createIfcPropertyEnumeratedValue(
                    Name=k, EnumerationValues=[self.f.createIfcLabel(x) for x in vs],
                    EnumerationReference=self._enumref(pt.Enumerators)))
            elif pt.TemplateType == "P_SINGLEVALUE":
                mt = pt.PrimaryMeasureType
                try:
                    if mt in ("IfcBoolean", "IfcLogical"):
                        vv = bool(v)
                    elif mt in ("IfcInteger", "IfcCountMeasure"):
                        vv = int(v)
                    elif mt in ("IfcLabel", "IfcIdentifier", "IfcText"):
                        vv = str(v)
                    else:
                        vv = float(v)
                    new_props.append(self.f.createIfcPropertySingleValue(Name=k, NominalValue=self.f.create_entity(mt, vv)))
                except (TypeError, ValueError, RuntimeError) as e:
                    self.errors.append(f"{path or ent.Name}: {name}.{k} = {v!r} passer ikke til {mt} ({e})")
            else:
                self.errors.append(f"{path or ent.Name}: {name}.{k} ({pt.TemplateType}) understøttes ikke – brug et Byg_-sæt")
        if new_props:
            pset = api.pset.add_pset(self.f, product=ent, name=name)
            pset.HasProperties = new_props

    def _enumref(self, enumtpl):
        if not hasattr(self, "_enums"):
            self._enums = {}
        if enumtpl.Name not in self._enums:
            self._enums[enumtpl.Name] = self.f.createIfcPropertyEnumeration(
                Name=enumtpl.Name, EnumerationValues=[self.f.createIfcLabel(v.wrappedValue)
                                                      for v in enumtpl.EnumerationValues])
        return self._enums[enumtpl.Name]

    def _qto(self, ent, name, q):
        q = {k: float(v) for k, v in q.items() if v is not None and v > 0}
        if not q:
            return
        qto = api.pset.add_qto(self.f, product=ent, name=name)
        api.pset.edit_qto(self.f, qto=qto, properties=q)
        qto.MethodOfMeasurement = "BaseQuantities"
        self.elements.setdefault(ent.Tag if hasattr(ent, "Tag") and ent.Tag else ent.Name, {}).setdefault("qto", {}).update(q)

    def _rep(self, ent, items, context=None, colour=None, rgb=None, transp=0.0):
        rep = self.b.get_representation(context or self.body, items if isinstance(items, list) else [items])
        api.geometry.assign_representation(self.f, product=ent, representation=rep)
        if colour or rgb:
            self._paint(rep, colour or ent.is_a(), rgb, transp)
        return rep

    def _extrude(self, ring, h, z0=0.0, holes=(), direction=(0, 0, 1)):
        ring = clean_ring(ring)
        curve = self.b.polyline([tuple(p) for p in ccw(ring)], closed=True)
        inner = [self.b.polyline([tuple(p) for p in ccw(clean_ring(hh))[::-1]], closed=True) for hh in holes]
        prof = self.b.profile(curve, inner_curves=inner)
        return self.b.extrude(prof, magnitude=float(h), position=(0.0, 0.0, float(z0)), extrusion_vector=direction)

    def _clip(self, solid, planes):
        for point, n in planes:
            hs = self.b.half_space_solid(self.b.plane(location=tuple(map(float, point)), normal=tuple(map(float, n))),
                                         agreement_flag=False)
            solid = self.f.createIfcBooleanClippingResult("DIFFERENCE", solid, hs)
        return solid

    def _assign_material(self, ent, name):
        if name:
            api.material.assign_material(self.f, products=[ent], type="IfcMaterial", material=self.material(name))

    # ------------------------------------------------------------------ walls
    def _slab_above(self, storey_id):
        """Thickness of the thickest floor slab on the storey above (0 if none). Used for default heights."""
        ids = [e["id"] for e in self.s["etager"]]
        i = ids.index(storey_id)
        if i + 1 >= len(ids):
            return 0.0
        thick = [(self.s["typer"][d["type"]]["_tykkelse"] if d.get("type") else float(d.get("tykkelse", 0)))
               for d in self.s["daek"] if d["etage"] == ids[i + 1] and d["art"] in ("gulv", "loft") and d["top"] == 0]
        return max(thick, default=0.0)

    def _walls(self):
        segs = self.s["_vaegsegmenter"]
        per_storey = {}
        for i, seg in enumerate(segs):
            t = self.s["typer"][seg["type"]]
            seg["_ude"] = bool(t.get("ude"))
            seg["_orden"] = i
            per_storey.setdefault(seg["etage"], []).append(WallGeo(seg, sum(x[1] for x in t["lag"])))
        for eid, ws in per_storey.items():
            try:
                wall_joins(ws)
            except ValueError as e:
                self.errors.append(str(e))
            for w in ws:
                self.wallgeo[w.id] = w
        for seg in segs:
            w = self.wallgeo[seg["id"]]
            t = self.s["typer"][seg["type"]]
            storey = self.storey_info[seg["etage"]]
            # default: external walls up to the next storey's floor (they carry the slab); internal walls to the slab's underside
            h = seg.get("hoejde", storey["hoejde"] - (0.0 if t.get("ude") else self._slab_above(seg["etage"])))
            bottom = seg.get("bund", 0.0)
            w.height, w.bottom = h, bottom
            ent = self.new_entity("IfcWall", seg)
            ring = local_polygon(w, w.footprint)
            solid = self._extrude(ring, h)
            w.solid = solid
            w.ent = ent
            M = self._T((w.p1[0], w.p1[1], self.storey_level[seg["etage"]] + bottom), (w.ux[0], w.ux[1], 0))
            w.M = M
            self.insert(ent, seg, M, "Pset_WallCommon", {}, "vaegge")
            axis = self.b.polyline([(0.0, 0.0), (float(w.L), 0.0)])
            self._rep(ent, axis, self.axis)
            w.rep = self._rep(ent, solid)
            self._paint(w.rep, t["lag"][0][0] if t["lag"] else "vaeg")
            api.type.assign_type(self.f, related_objects=[ent], relating_type=self._types[seg["type"]],
                                 should_map_representations=False)
            usage = self._layer_usage(ent, t)
            # layers from right (yR) towards left; in external wall loops the first layer must be outside
            out_left = seg.get("ude_venstre")
            from_left = (out_left is True) != bool(seg.get("vend_lag"))
            if usage:
                api.material.edit_layer_usage(self.f, usage=usage, attributes={
                    "LayerSetDirection": "AXIS2", "DirectionSense": "NEGATIVE" if from_left else "POSITIVE",
                    "OffsetFromReferenceLine": float(w.yL if from_left else w.yR)})
            w.openings = []

    def _layer_usage(self, ent, t):
        """IfcMaterialLayerSetUsage on the occurrence (the type carries the layer set itself)."""
        def find():
            for r in getattr(ent, "HasAssociations", []) or []:
                if r.is_a("IfcRelAssociatesMaterial") and r.RelatingMaterial.is_a("IfcMaterialLayerSetUsage"):
                    return r.RelatingMaterial
            return None
        if find() is None and t.get("_lagsaet"):
            api.material.assign_material(self.f, products=[ent], type="IfcMaterialLayerSetUsage", material=t["_lagsaet"])
        return find()

    # ------------------------------------------------------------------ openings
    def _openings(self):
        f = self.f
        for a in self.s["aabninger"]:
            w = self.wallgeo.get(a["vaeg"])
            if w is None:
                continue
            width, height, x0, z0 = a["bredde"], a["hoejde"], a["afstand"], a["brystning"]
            path = f"aabninger.{a['id']}"
            if x0 < -1 or x0 + width > w.L + 1:
                self.errors.append(f"{path}: åbningen ({x0:.0f}–{x0 + width:.0f}) ligger uden for væggens længde {w.L:.0f}")
            if z0 < -1 or z0 + height > w.height + 1:
                self.errors.append(f"{path}: åbningen (z {z0:.0f}–{z0 + height:.0f}) går ud over væghøjden {w.height:.0f}")
            for (b0, b1, aid) in w.openings:
                if x0 < b1 - 1 and x0 + width > b0 + 1:
                    self.errors.append(f"{path}: overlapper åbningen {aid} i væg {w.id}")
            w.openings.append((x0, x0 + width, a["id"]))
            # opening element through the full wall thickness (+10 mm each side)
            opening = self.new_entity("IfcOpeningElement", a, suffix="/hul", name=f"Åbning {a['id']}", predefined="OPENING")
            api.feature.add_feature(f, feature=opening, element=w.ent)
            Mo = w.M @ self._T((x0, w.yR - 10, z0))
            self._place(opening, Mo)
            prof = self.b.polyline([(0.0, 0.0), (width, 0.0), (width, w.t + 20), (0.0, w.t + 20)], closed=True)
            self._rep(opening, self.b.extrude(self.b.profile(prof), magnitude=height))
            info = {"vaeg": w.id, "x0": x0, "x1": x0 + width, "z0": z0, "z1": z0 + height}
            if a["_klasse"] == "hul":
                self.elements[a["id"]] = {"guid": opening.GlobalId, "klasse": "IfcOpeningElement", "etage": w.seg["etage"],
                                           "status": a["status"], "kilde": str(a["kilde"])[:1], **info}
                continue
            t = self.s["typer"][a["type"]]
            el = {**a, "etage": w.seg["etage"]}
            yc = (w.yR + w.yL) / 2
            out_y = w.yL if w.seg.get("ude_venstre") else w.yR
            placement = a.get("placering", "ude" if a["_klasse"] == "vindue" and w.seg.get("_ude") else "midt")
            if placement != "midt":
                in_y = w.yR if out_y == w.yL else w.yL
                yc = (3 * (out_y if placement == "ude" else in_y) + (in_y if placement == "ude" else out_y)) / 4
            if a["_klasse"] == "vindue":
                ld = min(w.t, float(t.get("ramme", 100)))
                ent = self.new_entity("IfcWindow", el)
                ent.OverallWidth, ent.OverallHeight = width, height
                M = w.M @ self._T((x0, yc - ld / 2, z0))
                self._window_geo(ent, width, height, ld, int(t.get("felter", 1)))
                kq = "Qto_WindowBaseQuantities"
            else:
                ld = w.t if not w.seg.get("_ude") else min(w.t, 150.0)
                ent = self.new_entity("IfcDoor", el)
                ent.OverallWidth, ent.OverallHeight = width, height
                side = a.get("slaar_mod", "venstre")
                if side in ("inde", "ude"):
                    uv = w.seg.get("ude_venstre")
                    if uv is None:
                        self.errors.append(f"{path}: slaar_mod {side} kræver en væg i en lukket ydervægsløkke – brug venstre/hoejre")
                        uv = False
                    side = "venstre" if (side == "ude") == uv else "hoejre"
                hs = a.get("haengsel", "start")
                if side == "venstre":
                    M = w.M @ self._T((x0, yc - ld / 2, z0))
                    op = "SINGLE_SWING_LEFT" if hs == "start" else "SINGLE_SWING_RIGHT"
                else:
                    M = w.M @ self._T((x0 + width, yc + ld / 2, z0), x=(-1, 0, 0))
                    op = "SINGLE_SWING_LEFT" if hs == "slut" else "SINGLE_SWING_RIGHT"
                type_op = self._types[a["type"]].OperationType
                if type_op in (None, "NOTDEFINED"):
                    ent.OperationType = op  # single leaf: the handedness belongs to the occurrence
                self._door_geo(ent, width, height, ld)
                kq = "Qto_DoorBaseQuantities"
                self.elements.setdefault("_doere", {})[a["id"]] = {"aabner": op, "mod": side}
            api.spatial.assign_container(f, products=[ent], relating_structure=self.storeys[w.seg["etage"]])
            self._place(ent, M)
            api.feature.add_filling(f, opening=opening, element=ent)
            api.type.assign_type(f, related_objects=[ent], relating_type=self._types[a["type"]],
                                 should_map_representations=False)
            self.properties(ent, el, None, {"IsExternal": bool(w.seg.get("_ude"))}, "aabninger")
            self.elements[a["id"]] = {"guid": ent.GlobalId, "klasse": ent.is_a(), "etage": w.seg["etage"],
                                       "status": a["status"], "kilde": str(a["kilde"])[:1], **info}
            self._qto(ent, kq, {"Width": width, "Height": height, "Area": width * height / 1e6})
        for w in self.wallgeo.values():
            if not hasattr(w, "ent"):
                continue
            L = self._length(w)
            opening_area = sum((self.elements[i]["x1"] - self.elements[i]["x0"]) * (self.elements[i]["z1"] - self.elements[i]["z0"])
                            for _, _, i in w.openings if i in self.elements) / 1e6
            q = {"Length": L, "Width": w.t, "Height": w.height, "GrossFootprintArea": w.footprint.area / 1e6}
            if not getattr(w, "clipped", False):
                q.update(GrossSideArea=L * w.height / 1e6, NetSideArea=L * w.height / 1e6 - opening_area,
                         GrossVolume=w.footprint.area * w.height / 1e9,
                         NetVolume=w.footprint.area * w.height / 1e9 - opening_area * w.t / 1000)
            w.qto = q

    def _box(self, x0, y0, z0, dx, dy, dz):
        prof = self.b.profile(self.b.polyline([(0.0, 0.0), (dx, 0.0), (dx, dy), (0.0, dy)], closed=True))
        return self.b.extrude(prof, magnitude=float(dz), position=(float(x0), float(y0), float(z0)))

    def _frame_xz(self, pts, holes, ld):
        """Profile in the xz plane (x along the wall, z up) extruded through y = 0…ld."""
        outer = self.b.polyline([tuple(map(float, q)) for q in ccw(pts)], closed=True)
        inner = [self.b.polyline([tuple(map(float, q)) for q in ccw(h)[::-1]], closed=True) for h in holes]
        return self.b.extrude(self.b.profile(outer, inner_curves=inner), magnitude=float(ld), position=(0.0, float(ld), 0.0),
                              position_z_axis=(0.0, -1.0, 0.0), position_x_axis=(1.0, 0.0, 0.0))

    def _window_geo(self, ent, W, H, ld, panes, k=60.0):
        """Frame, mullions and glass. Locally: x 0…W along the wall, y 0…ld through the wall, z 0…H."""
        items = [self._frame_xz([(0, 0), (W, 0), (W, H), (0, H)], [[(k, k), (W - k, k), (W - k, H - k), (k, H - k)]], ld)]
        for i in range(1, max(1, panes)):
            items.append(self._box(i * W / panes - k / 2, 0, k, k, ld, H - 2 * k))
        items.append(self._box(k, ld / 2 - 4, k, W - 2 * k, 8, H - 2 * k))
        rep = self._rep(ent, items)
        self._paint(rep, "IfcWindow", *CLASS_COLOUR["IfcWindow"])
        return rep

    def _door_geo(self, ent, W, H, ld, k=60.0):
        """Frame (U) and closed door leaf. The swing direction lives in OperationType and the door's local +y."""
        casing = self._frame_xz([(0, 0), (k, 0), (k, H - k), (W - k, H - k), (W - k, 0), (W, 0), (W, H), (0, H)], [], ld)
        leaf = self._box(k + 3, ld / 2 - 20, 0, W - 2 * k - 6, 40, H - k - 3)
        rep = self._rep(ent, [casing, leaf])
        self._paint(rep, "IfcDoor", *CLASS_COLOUR["IfcDoor"])
        return rep

    def _length(self, w):
        xs = [w.world_to_local(p)[0] for p in w.footprint.exterior.coords]
        return max(xs) - min(xs)

    # ------------------------------------------------------------------ slabs
    def _slabs(self):
        for d in self.s["daek"]:
            o = d["omrids"]
            if isinstance(o, dict):
                polys = [w.footprint for w in self.wallgeo.values() if w.seg["kaede"] == o["fra_vaegge"]]
                if not polys:
                    self.errors.append(f"daek.{d['id']}.omrids.fra_vaegge: ingen vægge med id '{o['fra_vaegge']}'")
                    continue
                poly = outline_from_walls(polys, o["kant"])
                if poly is None:
                    self.errors.append(f"daek.{d['id']}: væggene '{o['fra_vaegge']}' danner ikke en lukket løkke")
                    continue
                ring = list(poly.exterior.coords)[:-1]
            else:
                ring = list(o)
            t = self.s["typer"].get(d.get("type")) if d.get("type") else None
            thick = t["_tykkelse"] if t else float(d["tykkelse"])
            pre = {"gulv": "FLOOR", "loft": "FLOOR", "bund": "BASESLAB", "tag": "ROOF"}[d["art"]]
            ent = self.new_entity("IfcSlab", d, predefined=None if t else pre)
            solid = self._extrude(ring, thick, z0=0.0, holes=d["huller"], direction=(0, 0, -1))
            M = self._T((0, 0, self.storey_level[d["etage"]] + d["top"]))
            self.insert(ent, d, M, "Pset_SlabCommon", {}, "daek")
            rep = self._rep(ent, solid)
            self._paint(rep, t["lag"][0][0] if t else "beton")
            if t:
                api.type.assign_type(self.f, related_objects=[ent], relating_type=self._types[d["type"]],
                                     should_map_representations=False)
                usage = self._layer_usage(ent, t)
                if usage:
                    api.material.edit_layer_usage(self.f, usage=usage, attributes={
                        "LayerSetDirection": "AXIS3", "DirectionSense": "NEGATIVE", "OffsetFromReferenceLine": 0.0})
            p = Polygon(ring)
            net = p.area - sum(Polygon(h).area for h in d["huller"])
            self._qto(ent, "Qto_SlabBaseQuantities", {"Width": thick, "GrossArea": p.area / 1e6, "NetArea": net / 1e6,
                                                      "Perimeter": p.length, "GrossVolume": p.area * thick / 1e9,
                                                      "NetVolume": net * thick / 1e9})

    # ------------------------------------------------------------------ roofs (and clipping of walls/spaces)
    def _roofs_and_clip(self):
        self.roof_planes = {}
        self.roof_faces = {}  # roof id → [(face, slab, world matrix, 2D ring, thickness)] for roof windows
        self.roof_holes = {}  # (roof id, face name) → [(u0, v0, u1, v1)] roof window openings in the face frame
        self._roof_ent = {}
        for t in self.s["tage"]:
            level = self.storey_level[t["etage"]]
            faces = roof_faces(t)
            typ = self.s["typer"].get(t.get("type")) if t.get("type") else None
            thick = typ["_tykkelse"] if typ else t["tykkelse"]
            roof = self.new_entity("IfcRoof", t, predefined={"sadeltag": "GABLE_ROOF", "valmtag": "HIP_ROOF",
                                                    "pulttag": "SHED_ROOF", "fladt": "FLAT_ROOF"}[t["form"]])
            self.insert(roof, t, self._T((0, 0, level)), "Pset_RoofCommon", {}, "tage")
            self._roof_ent[t["id"]] = roof
            planes, parts = [], []
            for fl in faces:
                o, xa, ya, za = face_frame(fl)
                ring = to_face_2d(fl, (o, xa, ya, za))
                el = {**t, "id": t["id"]}
                slab = self.new_entity("IfcSlab", el, suffix=f".{fl.name}", name=f"{t.get('navn', t['id'])} {fl.name}",
                               predefined=None if typ else "ROOF")
                Mw = self._T((o[0], o[1], o[2] + level), x=xa, z=za)
                self._place(slab, Mw)
                rep = self._rep(slab, self._roof_face_solid(fl, ring, thick, (o, xa, ya, za), t["form"]))
                self._paint(rep, typ["lag"][0][0] if typ else "tagsten")
                if typ:
                    api.type.assign_type(self.f, related_objects=[slab], relating_type=self._types[t["type"]],
                                         should_map_representations=False)
                    usage = self._layer_usage(slab, typ)
                    if usage:
                        # layers are listed top-down: the reference is the slab's top face (z = thickness), layers go downwards
                        api.material.edit_layer_usage(self.f, usage=usage, attributes={
                            "LayerSetDirection": "AXIS3", "DirectionSense": "NEGATIVE", "OffsetFromReferenceLine": float(thick)})
                self.properties(slab, {**t, "id": t["id"]}, "Pset_SlabCommon", {}, "tage")
                area = Polygon(ring).area
                self._qto(slab, "Qto_SlabBaseQuantities", {"Width": thick, "GrossArea": area / 1e6, "NetArea": area / 1e6})
                parts.append(slab)
                self.roof_faces.setdefault(t["id"], []).append((fl, slab, Mw, ring, thick))
                planes.append((np.array([o[0], o[1], o[2] + level]), za))
                self.elements[f"{t['id']}.{fl.name}"] = {"guid": slab.GlobalId, "klasse": "IfcSlab", "etage": t["etage"],
                                                         "status": t["status"], "kilde": str(t["kilde"])[:1], "sektion": "tage"}
            api.aggregate.assign_object(self.f, relating_object=roof, products=parts)
            self.roof_planes[t["id"]] = planes
        # clip walls that have til_tag
        for w in self.wallgeo.values():
            roof_id = w.seg.get("til_tag")
            if not roof_id or not hasattr(w, "rep"):
                continue
            O = w.M[:3, 3]
            R = w.M[:3, :3]
            planes = [((p - O) @ R, n @ R) for p, n in self.roof_planes[roof_id]]
            clipped = self._clip(w.solid, planes)
            new_rep = self.b.get_representation(self.body, [clipped])
            api.geometry.unassign_representation(self.f, product=w.ent, representation=w.rep)
            api.geometry.assign_representation(self.f, product=w.ent, representation=new_rep)
            t = self.s["typer"][w.seg["type"]]
            self._paint(new_rep, t["lag"][0][0] if t["lag"] else "vaeg")
            ifcopenshell.api.geometry.remove_representation(self.f, representation=w.rep)
            w.rep, w.clipped = new_rep, True
            for k in ("GrossSideArea", "NetSideArea", "GrossVolume", "NetVolume"):
                w.qto.pop(k, None)
        for w in self.wallgeo.values():
            if hasattr(w, "ent"):
                self._qto(w.ent, "Qto_WallBaseQuantities", w.qto)

    def _skylights(self):
        """Roof windows: an opening through the roof face (perpendicular to it) filled by an IfcWindow.
        `punkt` is the window centre in plan; width runs along the eaves, height up the slope."""
        for o in self.s["ovenlys"]:
            path = f"ovenlys.{o['id']}"
            faces = self.roof_faces.get(o["tag"], [])
            x, y = o["punkt"]
            hit = [f for f in faces if (o.get("flade") or f[0].name) == f[0].name
                   and Polygon([(p[0], p[1]) for p in f[0].pts]).contains(Point(x, y))]
            if not hit:
                self.errors.append(f"{path}: punktet ({x:.0f}, {y:.0f}) ligger ikke på en tagflade af {o['tag']}"
                                 + (f" ({o['flade']})" if o.get("flade") else ""))
                continue
            fl, slab, Mw, ring, thick = hit[0]
            _, xa, ya, za = face_frame(fl)
            if abs(za[2]) < 1e-6:
                self.errors.append(f"{path}: tagfladen {fl.name} er lodret")
                continue
            # the point on the face's underside straight above (x, y), in the face's own frame
            z = fl.origin[2] - (za[0] * (x - fl.origin[0]) + za[1] * (y - fl.origin[1])) / za[2]
            d = np.array([x, y, z]) - fl.origin
            u, v = d @ xa, d @ ya
            W, H = o["bredde"], o["hoejde"]
            u0, v0 = u - W / 2, v - H / 2
            if not Polygon(ring).contains(Polygon([(u0, v0), (u0 + W, v0), (u0 + W, v0 + H), (u0, v0 + H)])):
                self.errors.append(f"{path}: ovenlyset ({W:.0f} × {H:.0f}) går ud over tagfladen {fl.name}")
            opening = self.new_entity("IfcOpeningElement", o, suffix="/hul", name=f"Åbning {o['id']}", predefined="OPENING")
            api.feature.add_feature(self.f, feature=opening, element=slab)
            self._place(opening, Mw @ self._T((u0, v0, -10.0)))
            self.roof_holes.setdefault((o["tag"], fl.name), []).append((u0, v0, u0 + W, v0 + H))
            prof = self.b.polyline([(0.0, 0.0), (W, 0.0), (W, H), (0.0, H)], closed=True)
            self._rep(opening, self.b.extrude(self.b.profile(prof), magnitude=thick + 20))
            t = self.s["typer"][o["type"]]
            ld = min(thick, float(t.get("ramme", 100)))
            ent = self.new_entity("IfcWindow", o, predefined="SKYLIGHT")
            ent.OverallWidth, ent.OverallHeight = W, H
            # window frame: x along the eaves, z up the slope, y down through the roof from its top face
            M = Mw @ self._T((u0, v0, thick + 20.0), x=(1, 0, 0), z=(0, 1, 0))
            api.spatial.assign_container(self.f, products=[ent], relating_structure=self.storeys[o["etage"]])
            self._place(ent, M)
            self._window_geo(ent, W, H, ld, int(t.get("felter", 1)))
            api.feature.add_filling(self.f, opening=opening, element=ent)
            api.type.assign_type(self.f, related_objects=[ent], relating_type=self._types[o["type"]],
                                 should_map_representations=False)
            self.properties(ent, o, None, {"IsExternal": True}, "ovenlys")
            self.elements[o["id"]] = {"guid": ent.GlobalId, "klasse": "IfcWindow", "etage": o["etage"],
                                       "status": o["status"], "kilde": str(o["kilde"])[:1], "sektion": "ovenlys",
                                       "tag": f"{o['tag']}.{fl.name}"}
            self._qto(ent, "Qto_WindowBaseQuantities", {"Width": W, "Height": H, "Area": W * H / 1e6})

    def _roof_face_solid(self, fl, ring, thick, frame, form):
        """Roof face as a slab perpendicular to the face, cut vertically (mitred) along all edges, so ridge and
        hips close tightly and eaves/gable get a vertical cut."""
        if form == "fladt":
            return self._extrude(ring, thick)
        enlarged = Polygon(ring).buffer(3 * thick, join_style=2)
        solid = self._extrude(list(enlarged.exterior.coords)[:-1], thick)
        return self._clip(solid, self._edge_planes(fl, frame))

    @staticmethod
    def _edge_planes(fl, frame):
        """The vertical planes through the face's edges, in the face frame, with outward normals."""
        o, xa, ya, za = frame
        c = np.mean(fl.pts, axis=0)
        planes = []
        for i in range(len(fl.pts)):
            a, b_ = fl.pts[i], fl.pts[(i + 1) % len(fl.pts)]
            n = np.cross(b_ - a, (0, 0, 1.0))
            if np.linalg.norm(n) < 1e-9:
                continue
            n = unit(n)
            if (c - a) @ n > 0:
                n = -n
            planes.append((np.array([(a - o) @ xa, (a - o) @ ya, (a - o) @ za]), np.array([n @ xa, n @ ya, n @ za])))
        return planes

    # ------------------------------------------------------------------ rafters
    CHIMNEY_CLEARANCE = 50  # mm clearance between rafters/collars and a chimney

    def _rafters(self):
        """Rafters (IfcMember RAFTER) in the bottom layer of each roof face, at most `afstand` apart, with trimmers
        around roof windows and chimneys, and optionally collar ties (hanebånd) across a gable roof and wind braces
        (vindbånd) under the rafters."""
        chimneys = []
        for g in self.s["generisk"]:
            if g.get("klasse") == "IfcChimney" and "profil" in g and abs(unit(np.array(g["z_akse"], float))[2]) > 0.999:
                x = unit(np.array(g["x_akse"], float))
                y = np.cross((0, 0, 1.0), x)
                o = np.array(g["origo"], float)
                chimneys.append(Polygon([(o[0] + px * x[0] + py * y[0], o[1] + px * x[1] + py * y[1])
                                         for px, py in g["profil"]]).buffer(self.CHIMNEY_CLEARANCE, join_style=2))
        for t in self.s["tage"]:
            sp = t.get("spaer")
            if not sp:
                continue
            level = self.storey_level[t["etage"]]
            typ = self.s["typer"].get(t.get("type")) if t.get("type") else None
            rafter_layers = [tk for name, tk in (typ["lag"] if typ else []) if "spær" in name.lower() or "spaer" in name.lower()]
            b, h, mat = sp["b"], sp.get("h") or (rafter_layers[-1] if rafter_layers else 150.0), sp["materiale"]
            el = {"id": t["id"], "etage": t["etage"], "status": t["status"], "kilde": t["kilde"], "ref": t.get("ref")}
            parts, rafters = [], {}  # spaer: face name → [(world point at the eaves line, axis up the slope, segments)]
            for fl, slab, Mw, ring, thick in self.roof_faces.get(t["id"], []):
                frame = face_frame(fl)
                o, xa, ya, za = frame
                if abs(za[2]) > 0.999:
                    continue  # flat roof: no rafters
                planes = self._edge_planes(fl, frame)
                face = Polygon(ring)
                holes = list(self.roof_holes.get((t["id"], fl.name), []))
                for ch in chimneys:
                    # the chimney's footprint where it passes the rafter layer (underside and top of the rafters)
                    pts = []
                    for d in (-10.0, h - 10.0):
                        for x, y in ch.exterior.coords:
                            z = o[2] + (d - za[0] * (x - o[0]) - za[1] * (y - o[1])) / za[2]
                            q = np.array([x, y, z]) - o
                            pts.append((q @ xa, q @ ya))
                    hp = Polygon(pts).convex_hull
                    if hp.intersects(face):
                        holes.append(hp.bounds)
                u_min, _, u_max, _ = face.bounds
                n = max(1, math.ceil((u_max - u_min - b) / sp["afstand"]))
                pos = [u_min + b / 2 + i * (u_max - u_min - b) / n for i in range(n + 1)]
                flanks = [u for u0, _, u1, _ in holes for u in (u0 - b / 2, u1 + b / 2)]
                pos = sorted([u for u in pos if all(abs(u - fu) >= 1.5 * b for fu in flanks)] + flanks)
                cutters = unary_union([box(u0 - b / 2, v0 - b, u1 + b / 2, v1 + b) for u0, v0, u1, v1 in holes]) \
                    if holes else None
                pieces = []  # (u, va, vb) rafter pieces and (va, vb, v) trimmers in the face frame
                for u in pos:
                    line = LineString([(u, -1e6), (u, 1e6)]).intersection(face)
                    if cutters is not None and u not in flanks:
                        line = line.difference(cutters)
                    segs = []
                    for g in getattr(line, "geoms", [line]):
                        if g.is_empty or g.length < 2 * b:
                            continue
                        va, vb = sorted(c[1] for c in g.coords)
                        segs.append((va, vb))
                        # ends on the face's edges run past it and are cut by the edge planes like the slab
                        ea = 3 * h if face.exterior.distance(Point(u, va)) < 0.5 else 0.0
                        eb = 3 * h if face.exterior.distance(Point(u, vb)) < 0.5 else 0.0
                        pieces.append(("S", [(u - b / 2, va - ea), (u + b / 2, va - ea), (u + b / 2, vb + eb),
                                              (u - b / 2, vb + eb)], vb - va))
                    rafters.setdefault(fl.name, []).append((o + u * xa, ya, segs))
                for u0, v0, u1, v1 in holes:
                    for v in (v0 - b / 2, v1 + b / 2):
                        pieces.append(("V", [(u0, v - b / 2), (u1, v - b / 2), (u1, v + b / 2), (u0, v + b / 2)], u1 - u0))
                counter = {"S": 0, "V": 0}
                for kind, rect, length in pieces:
                    counter[kind] += 1
                    ent = self.new_entity("IfcMember", el, suffix=f".{fl.name}.{kind}{counter[kind]:02d}",
                                  name=f"{'Spær' if kind == 'S' else 'Veksel'} {fl.name} {counter[kind]}", predefined="RAFTER")
                    self._place(ent, Mw)
                    # the rafter hangs 10 mm below the face's underside so it doesn't share a plane with the slab
                    solid = self._clip(self._extrude(rect, h, z0=-10.0), planes)
                    self._member(ent, el, solid, mat, length, parts)
                if sp.get("vindbaand"):
                    self._wind_braces(t, el, sp["vindbaand"], mat, fl, Mw, frame, face, holes, parts)
            if sp.get("hanebaand") and t["form"] == "sadeltag" and len(rafters) == 2:
                self._collar_ties(t, el, sp, b, h, mat, level, rafters, chimneys, parts)
            if parts:
                api.aggregate.assign_object(self.f, relating_object=self._roof_ent[t["id"]], products=parts)

    def _wind_braces(self, t, el, wb, mat, fl, Mw, frame, face, holes, parts):
        """Wind braces: two boards per roof face nailed to the rafters' underside, each running at 45° in the face
        between the wall plate and the ridge from a gable towards the middle, inside the outline. Each brace takes the
        first route clear of roof openings: from the eaves corner, from the ridge corner, then shifted one rafter
        spacing at a time along the face; if none is clear it is interrupted at the openings."""
        o, xa, ya, za = frame
        bw, tw = wb["b"], wb["t"]
        x0, y0, x1, y1 = t["omrids"]
        pts = []
        for x, y in ((x0, y0), (x1, y0), (x1, y1), (x0, y1)):
            z = o[2] + (-za[0] * (x - o[0]) - za[1] * (y - o[1])) / za[2]  # the outline projected into the face
            q = np.array([x, y, z]) - o
            pts.append((q @ xa, q @ ya))
        region = face.intersection(Polygon(pts))
        if region.is_empty:
            return
        u_min, v_min, u_max, v_max = region.bounds
        blocked = unary_union([box(u0 - bw, v0 - bw, u1 + bw, v1 + bw) for u0, v0, u1, v1 in holes]) if holes else None
        reach = 2 * (u_max - u_min + v_max - v_min)
        step = t["spaer"]["afstand"]

        def strip(u0, du, v0, dv):
            d = np.array([du, dv]) / math.sqrt(2)
            p0 = np.array([u0 + du * bw / math.sqrt(2), v0])  # the board's outer edge starts at the corner
            return LineString([tuple(p0 - d * bw), tuple(p0 + d * reach)]).buffer(bw / 2, cap_style=2).intersection(region), d

        nr = 0
        for u_end, du in ((u_min, 1.0), (u_max, -1.0)):
            routes = [(u_end + du * k * step, v0, dv) for k in range(int((u_max - u_min) / 2 // step) + 1)
                      for v0, dv in ((v_min, 1.0), (v_max, -1.0))]
            piece, d = next((r for r in (strip(u0, du, v0, dv) for u0, v0, dv in routes)
                             if blocked is None or not r[0].intersects(blocked)), (None, None))
            if piece is None:
                piece, d = strip(u_end, du, v_min, 1.0)
                piece = piece.difference(blocked)
            for g in getattr(piece, "geoms", [piece]):
                if not isinstance(g, Polygon) or g.is_empty or g.area < 4 * bw * bw:
                    continue
                proj = [np.array(c) @ d for c in g.exterior.coords]
                nr += 1
                ent = self.new_entity("IfcMember", el, suffix=f".{fl.name}.W{nr:02d}", name=f"Vindbånd {fl.name} {nr}",
                                      predefined="BRACE")
                self._place(ent, Mw)
                # under the rafters, which hang from 10 mm below the face's underside
                solid = self._extrude(list(g.exterior.coords)[:-1], tw, z0=-10.0 - tw)
                self._member(ent, el, solid, mat, max(proj) - min(proj), parts)

    def _collar_ties(self, t, el, sp, b, h, mat, level, rafters, chimneys, parts):
        """Collar ties between rafter pairs: top at `hanebaand` above the floor, inside the walls, clear of chimneys."""
        a_side, b_side = rafters.values()
        x0, y0, x1, y1 = t["omrids"]
        inside = box(x0, y0, x1, y1)
        zc = level + sp["hanebaand"]

        def at_height(p0, axis, segs):
            # the point on the rafter's underside at height zc, if a rafter piece is there
            if abs(axis[2]) < 1e-9:
                return None
            v = (zc - (p0[2] + level)) / axis[2]
            # underside is 10 mm below the face plane: shift along the face normal is negligible for the collar's ends
            return p0 + axis * v + np.array([0, 0, level]) if any(va <= v <= vb for va, vb in segs) else None

        nr = 0
        for pa, aa, sa in a_side:
            for pb, ab, sb in b_side:
                d = (pb - pa)[:2]
                if abs(d @ unit(np.array([aa[1], -aa[0]]))) > 1.0:  # not the same rafter line across the ridge
                    continue
                A, B = at_height(pa, aa, sa), at_height(pb, ab, sb)
                if A is None or B is None:
                    continue
                plan = LineString([A[:2], B[:2]]).buffer(b / 2, cap_style=2)
                if not inside.contains(plan) or any(plan.intersects(c) for c in chimneys):
                    continue
                nr += 1
                L = float(np.linalg.norm(B - A))
                z = unit(B - A)
                x = unit(np.cross((0, 0, 1.0), z))
                ent = self.new_entity("IfcMember", el, suffix=f".H{nr:02d}", name=f"Hanebånd {nr}", predefined="COLLAR")
                self._place(ent, self._T(A - np.array([0, 0, h / 2]), x=x, z=z))
                solid = self.f.createIfcExtrudedAreaSolid(self._profile_def({"form": "rekt", "b": b, "h": h}), None,
                                                          self.f.createIfcDirection((0.0, 0.0, 1.0)), L)
                self._member(ent, el, solid, mat, L, parts)
                break

    def _member(self, ent, el, solid, mat, length, parts):
        rep = self._rep(ent, solid)
        self._paint(rep, mat)
        self._assign_material(ent, mat)
        self.properties(ent, el, "Pset_MemberCommon", {"LoadBearing": True}, "tage")
        self._qto(ent, "Qto_MemberBaseQuantities", {"Length": float(length)})
        self.elements[ent.Tag] = {"guid": ent.GlobalId, "klasse": "IfcMember", "etage": el["etage"],
                                   "status": el["status"], "kilde": str(el["kilde"])[:1], "sektion": "tage"}
        parts.append(ent)

    # ------------------------------------------------------------------ stairs
    def _stairs(self):
        for tr in self.s["trapper"]:
            n = int(round(tr["stigninger"]))
            storey = self.storey_info[tr["etage"]]
            R = tr.get("stigning") or storey["hoejde"] / n
            G = tr["grund"]
            pts = [(0.0, 0.0)]
            for i in range(n):
                pts += [(i * G, (i + 1) * R), ((i + 1) * G if i < n - 1 else i * G + 0.0, (i + 1) * R)]
            pts = pts[:-1]
            waist = max(250.0, R + 60)
            pts += [((n - 1) * G, n * R - waist)]
            r = math.radians(tr["retning"])
            ux = np.array([math.cos(r), math.sin(r), 0])
            uy = np.array([-math.sin(r), math.cos(r), 0])
            start = np.array([tr["start"][0], tr["start"][1], 0]) - uy * tr["bredde"] / 2
            # profile in the (run, z) plane extruded across: local x = run, local y = up, z = left→right
            ent = self.new_entity("IfcStair", tr, predefined="STRAIGHT_RUN_STAIR")
            O = start + uy * tr["bredde"] + np.array([0, 0, self.storey_level[tr["etage"]] + tr["bund"]])
            M = self._T(O, x=ux, z=-uy)
            self.insert(ent, tr, M, "Pset_StairCommon", {"NumberOfRiser": n, "NumberOfTreads": n - 1,
                                                          "RiserHeight": R, "TreadLength": G}, "trapper")
            rep = self._rep(ent, self._extrude(clean_ring(pts), tr["bredde"]))
            self._paint(rep, tr.get("materiale", "træ"))
            self._assign_material(ent, tr.get("materiale"))
            self.elements[tr["id"]]["trappe"] = {"stigning": R, "grund": G, "n": n,
                                                  "laengde": (n - 1) * G, "2s+g": 2 * R + G}

    # ------------------------------------------------------------------ columns and beams
    def _profile_def(self, p):
        f = self.f
        if p["form"] == "rekt":
            return f.createIfcRectangleProfileDef("AREA", None, None, p["b"], p["h"])
        if p["form"] == "rhs":
            return f.createIfcRectangleHollowProfileDef("AREA", None, None, p["b"], p["h"], p["t"])
        if p["form"] == "i":
            return f.createIfcIShapeProfileDef("AREA", None, None, p["b"], p["h"], p["tw"], p["tf"])
        if p["form"] == "rund":
            return f.createIfcCircleProfileDef("AREA", None, None, p["d"] / 2)
        if p["form"] == "roer":
            return f.createIfcCircleHollowProfileDef("AREA", None, None, p["d"] / 2, p["t"])
        if p["form"] == "l":
            return f.createIfcLShapeProfileDef("AREA", None, None, p["h"], p["b"], p["t"])
        raise ValueError(p["form"])

    def _columns_beams(self):
        for s in self.s["soejler"]:
            h = s.get("hoejde") or self.storey_info[s["etage"]]["hoejde"] - self._slab_above(s["etage"]) - s["bund"]
            ent = self.new_entity("IfcColumn", s, predefined="COLUMN")
            r = math.radians(s["rotation"])
            M = self._T((s["punkt"][0], s["punkt"][1], self.storey_level[s["etage"]] + s["bund"]),
                        x=(math.cos(r), math.sin(r), 0))
            self.insert(ent, s, M, "Pset_ColumnCommon", {"LoadBearing": True}, "soejler")
            solid = self.f.createIfcExtrudedAreaSolid(self._profile_def(s["profil"]), None,
                                                      self.f.createIfcDirection((0.0, 0.0, 1.0)), float(h))
            rep = self._rep(ent, solid)
            self._paint(rep, s.get("materiale", "stål"))
            self._assign_material(ent, s.get("materiale"))
            self._qto(ent, "Qto_ColumnBaseQuantities", {"Length": h})
        for bj in self.s["bjaelker"]:
            a, b_ = np.array(bj["fra"], float), np.array(bj["til"], float)
            L = float(np.linalg.norm(b_ - a))
            if L < 1:
                self.errors.append(f"bjaelker.{bj['id']}: længde 0")
                continue
            z = unit(b_ - a)
            xh = np.cross((0, 0, 1), z)
            x = unit(xh) if np.linalg.norm(xh) > 1e-6 else np.array([1.0, 0, 0])
            y = np.cross(z, x)
            p = bj["profil"]
            hh = p.get("h", p.get("d", 0))
            off = {"top": -hh / 2, "midt": 0.0, "bund": hh / 2}[bj["kant"]]
            O = a + y * off + np.array([0, 0, self.storey_level[bj["etage"]]])
            ent = self.new_entity("IfcBeam", bj, predefined="BEAM")
            self.insert(ent, bj, self._T(O, x=x, z=z), "Pset_BeamCommon", {"LoadBearing": True}, "bjaelker")
            solid = self.f.createIfcExtrudedAreaSolid(self._profile_def(p), None, self.f.createIfcDirection((0.0, 0.0, 1.0)), L)
            rep = self._rep(ent, solid)
            self._paint(rep, bj.get("materiale", "stål"))
            self._assign_material(ent, bj.get("materiale"))
            self._qto(ent, "Qto_BeamBaseQuantities", {"Length": L})

    # ------------------------------------------------------------------ spaces
    def _spaces(self):
        for r in self.s["rum"]:
            storey = self.storey_info[r["etage"]]
            if "punkt" in r:
                polys = [w.footprint for w in self.wallgeo.values() if w.seg["etage"] == r["etage"]]
                poly = room_polygon(r["punkt"], polys, r.get("afgraensning") or ())
                if poly is None:
                    self.errors.append(f"rum.{r['id']}: punktet {r['punkt']} ligger ikke i et lukket rum på etage "
                                     f"{r['etage']} (tjek vægge/afgrænsning, eller angiv omrids)")
                    continue
                if poly.interiors:
                    self.warnings.append(f"rum.{r['id']}: rummet omslutter fritstående vægge/søjler ({len(poly.interiors)})")
                ring = list(poly.exterior.coords)[:-1]
                holes = [list(i.coords)[:-1] for i in poly.interiors]
            else:
                ring, holes = list(r["omrids"]), []
            h = r.get("hoejde") or storey.get("fri_hoejde") or storey["hoejde"]
            ent = self.new_entity("IfcSpace", r, name=r["id"], predefined="INTERNAL")
            ent.LongName = r.get("navn") or r["id"]
            api.aggregate.assign_object(self.f, relating_object=self.storeys[r["etage"]], products=[ent])
            self._place(ent, self._T((0, 0, self.storey_level[r["etage"]] + r["bund"])))
            solid = self._extrude(ring, h, holes=holes)
            if r.get("til_tag"):
                O = np.array([0, 0, self.storey_level[r["etage"]] + r["bund"]])
                solid = self._clip(solid, [(p - O, n) for p, n in self.roof_planes[r["til_tag"]]])
            rep = self._rep(ent, solid)
            self._paint(rep, "IfcSpace", *CLASS_COLOUR["IfcSpace"])
            props = {"Reference": r["id"], "IsExternal": False}
            self.properties(ent, r, "Pset_SpaceCommon", props, "rum")
            if r.get("anvendelse"):
                self._pset(ent, "Byg_Rum", {"Anvendelse": str(r["anvendelse"])})
            area = Polygon(ring, holes).area
            q = {"NetFloorArea": area / 1e6, "GrossFloorArea": area / 1e6, "Height": h,
                 "NetPerimeter": Polygon(ring).length}
            if not r.get("til_tag"):
                q["GrossVolume"] = area * h / 1e9
            self.elements[r["id"]] = {"guid": ent.GlobalId, "klasse": "IfcSpace", "etage": r["etage"],
                                       "status": r["status"], "kilde": str(r["kilde"])[:1], "navn": ent.LongName,
                                       "sektion": "rum"}
            self._qto(ent, "Qto_SpaceBaseQuantities", q)
            self.elements[r["id"]]["areal_m2"] = round(area / 1e6, 2)

    # ------------------------------------------------------------------ plumbing/electrical
    def _systems(self):
        self.systems = {}
        for s in self.s["systemer"]:
            ent = api.system.add_system(self.f, ifc_class="IfcDistributionSystem")
            ent.Name = s.get("navn") or s["id"]
            ent.GlobalId = self.guid(s["id"])
            ent.PredefinedType = SYSTEM_KINDS[s["art"]]
            if ent.PredefinedType == "USERDEFINED":
                ent.ObjectType = s.get("navn") or s["id"]
            self.systems[s["id"]] = ent
            if hasattr(ent, "Description") and s.get("beskrivelse"):
                ent.Description = s["beskrivelse"]

    def _installations(self):
        schema = ifcopenshell.ifcopenshell_wrapper.schema_by_name(self.m["schema"] if self.m["schema"] != "IFC4X3" else "IFC4X3_ADD2")
        for el in self.s["installationer"]:
            if el.get("klasse"):
                ifc_class, pre = el["klasse"], el.get("predefined")
            elif el.get("art") in INSTALLATIONS:
                ifc_class, pre = INSTALLATIONS[el["art"]]
            else:
                self.errors.append(f"installationer.{el['id']}.art '{el.get('art')}' er ukendt – brug klasse: Ifc… "
                                 f"eller en af {', '.join(sorted(INSTALLATIONS))}")
                continue
            try:
                schema.declaration_by_name(ifc_class)
            except Exception:
                self.errors.append(f"installationer.{el['id']}: {ifc_class} findes ikke i {self.m['schema']}")
                continue
            ent = self.new_entity(ifc_class, el, predefined=pre, object_type=el.get("art") if pre == "USERDEFINED" else None)
            r = math.radians(el["rotation"])
            p = el["punkt"]
            M = self._T((p[0], p[1], p[2] + self.storey_level[el["etage"]]), x=(math.cos(r), math.sin(r), 0))
            props = {}
            self.insert(ent, el, M, None, props, "installationer")
            g = el["geometri"]
            if "kasse" in g:
                b, d, h = map(float, g["kasse"])
                prof = self.f.createIfcRectangleProfileDef("AREA", None, None, b, d)
            else:
                dia, h = map(float, g["cylinder"])
                prof = self.f.createIfcCircleProfileDef("AREA", None, None, dia / 2)
            solid = self.f.createIfcExtrudedAreaSolid(prof, None, self.f.createIfcDirection((0.0, 0.0, 1.0)), h)
            rep = self._rep(ent, solid)
            self._paint(rep, "installation", *CLASS_COLOUR["installation"])
            self._assign_material(ent, el.get("materiale"))
            if el.get("producent") or el.get("model"):
                self._pset(ent, "Pset_ManufacturerTypeInformation",
                           {k: v for k, v in (("Manufacturer", el.get("producent")), ("ModelLabel", el.get("model")))
                            if v})
            if KIND_GROUP.get(el.get("art")) == "EL" or any(k in el for k in ("lysgruppe", "kreds", "dimmer")):
                self._pset(ent, "Byg_El", {k: v for k, v in (
                    ("Art", el.get("art")), ("Lysgruppe", ",".join(el.get("lysgruppe") or [])),
                    ("Kreds", el.get("kreds")), ("Dimmer", el.get("dimmer"))) if v not in (None, "")})
            if el.get("system"):
                if ent.is_a("IfcDistributionElement"):
                    api.system.assign_system(self.f, products=[ent], system=self.systems[str(el["system"])])
                else:
                    self.errors.append(f"installationer.{el['id']}: {ifc_class} kan ikke indgå i et system")

    def _pipes(self):
        for r in self.s["roer"]:
            pts = [np.array(p, float) for p in r["punkter"]]
            level = self.storey_level[r["etage"]]
            ifc_class = "IfcDuctSegment" if r["art"] == "kanal" else "IfcPipeSegment"
            previous = None
            for i in range(len(pts) - 1):
                a, b_ = pts[i], pts[i + 1]
                L = float(np.linalg.norm(b_ - a))
                if L < 1:
                    continue
                z = unit(b_ - a)
                xh = np.cross((0, 0, 1), z)
                x = unit(xh) if np.linalg.norm(xh) > 1e-6 else np.array([1.0, 0, 0])
                el = {**r, "id": r["id"]}
                ent = self.new_entity(ifc_class, el, suffix=f".{i + 1}", predefined="RIGIDSEGMENT")
                M = self._T(a + np.array([0, 0, level]), x=x, z=z)
                self.insert(ent, el, M, None, {}, "roer", suffix=f".{i + 1}")
                d = r["diameter"]
                prof = (self.f.createIfcCircleHollowProfileDef("AREA", None, None, d / 2, float(r["godstykkelse"]))
                        if r.get("godstykkelse") else self.f.createIfcCircleProfileDef("AREA", None, None, d / 2))
                solid = self.f.createIfcExtrudedAreaSolid(prof, None, self.f.createIfcDirection((0.0, 0.0, 1.0)), L)
                rep = self._rep(ent, solid)
                self._paint(rep, f"system:{r.get('system', 'roer')}", *self._system_colour(r.get("system")))
                self._assign_material(ent, r.get("materiale"))
                self._qto(ent, "Qto_PipeSegmentBaseQuantities" if ifc_class == "IfcPipeSegment" else
                          "Qto_DuctSegmentBaseQuantities", {"Length": L})
                p1 = api.system.add_port(self.f, element=ent)
                p2 = api.system.add_port(self.f, element=ent)
                for prt, pos, flow_dir in ((p1, (0, 0, 0), "SINK"), (p2, (0, 0, L), "SOURCE")):
                    prt.FlowDirection = flow_dir
                    prt.PredefinedType = "DUCT" if ifc_class == "IfcDuctSegment" else "PIPE"
                    self._place(prt, M @ self._T(pos))
                if previous is not None:
                    api.system.connect_port(self.f, port1=previous, port2=p1)
                previous = p2
                if r.get("system"):
                    api.system.assign_system(self.f, products=[ent], system=self.systems[str(r["system"])])

    def _system_colour(self, sid):
        system = next((s for s in self.s["systemer"] if s["id"] == str(sid)), {})
        if system.get("farve"):
            return tuple(v / 255 for v in system["farve"]), 0
        kind = system.get("art")
        return {"varme": ((0.85, 0.15, 0.15), 0), "brugsvand_koldt": ((0.15, 0.45, 0.85), 0),
                "brugsvand_varmt": ((0.90, 0.45, 0.10), 0), "afloeb": ((0.45, 0.35, 0.25), 0),
                "ventilation": ((0.40, 0.75, 0.40), 0), "gas": ((0.95, 0.85, 0.10), 0)}.get(kind, ((0.6, 0.6, 0.6), 0))

    # ------------------------------------------------------------------ generic
    def _generic(self):
        schema = ifcopenshell.ifcopenshell_wrapper.schema_by_name(self.m["schema"] if self.m["schema"] != "IFC4X3" else "IFC4X3_ADD2")
        for g in self.s["generisk"]:
            ifc_class = g.get("klasse", "IfcBuildingElementProxy")
            try:
                schema.declaration_by_name(ifc_class)
            except Exception:
                self.errors.append(f"generisk.{g['id']}: {ifc_class} findes ikke i {self.m['schema']}")
                continue
            ent = self.new_entity(ifc_class, g, predefined=g.get("predefined"))
            level = self.storey_level[g["etage"]]
            if "mesh" in g:
                M = self._T((0, 0, level))
                self.insert(ent, g, M, None, {}, "generisk")
                ms = g["mesh"]
                item = self.b.mesh([tuple(map(float, p)) for p in ms["punkter"]], [list(fl) for fl in ms["flader"]])
                rep = self._rep(ent, item)
            else:
                O = np.array(g["origo"], float) + np.array([0, 0, level])
                M = self._T(O, x=g["x_akse"], z=g["z_akse"])
                self.insert(ent, g, M, None, {}, "generisk")
                solid = self._extrude(g["profil"], g["dybde"])
                if ent.is_a("IfcWindow") or ent.is_a("IfcDoor"):
                    # e.g. a skylight in the roof face: the profile's extent is the frame's outer dimensions
                    xs, ys = zip(*g["profil"])
                    ent.OverallWidth, ent.OverallHeight = float(max(xs) - min(xs)), float(max(ys) - min(ys))
                if g.get("til_tag"):
                    R = M[:3, :3]
                    solid = self._clip(solid, [((p - O) @ R, n @ R) for p, n in self.roof_planes[g["til_tag"]]])
                rep = self._rep(ent, solid)
            self._paint(rep, g.get("materiale", "generisk"))
            self._assign_material(ent, g.get("materiale"))

    # ------------------------------------------------------------------ display groups
    def _groups(self):
        """One discipline IfcGroup per element/system (show/hide in e.g. Bonsai). Order of assignment:
        1) the spec's grupper[].omfatter (id or pattern, first match), 2) elements with a system follow the system,
        3) the system's art, the installation's art or the IFC class (STANDARD_GROUPS)."""
        import fnmatch
        spec_g = self.s.get("grupper") or []
        defs = {k: {"navn": n, "under": u} for k, (n, u) in STANDARD_GROUPS.items()}
        for g in spec_g:
            defs[g["id"]] = {**defs.get(g["id"], {"navn": g["id"], "under": None}),
                             **{k: g[k] for k in ("navn", "under", "beskrivelse") if k in g}}
        rules = [(m, g["id"]) for g in spec_g for m in g.get("omfatter") or []]
        used = set()

        def explicit(*ids):
            for m, gid in rules:
                if any(fnmatch.fnmatchcase(i, m) for i in ids):
                    used.add(m)
                    return gid
            return None

        spec_el = {str(e["id"]): e for sec in ("installationer", "roer", "generisk") for e in self.s.get(sec) or []}
        members = {}
        for s in self.s["systemer"]:
            gid = explicit(s["id"]) or SYSTEM_GROUP.get(s["art"], "OEVRIGE")
            members.setdefault(gid, []).append(self.systems[s["id"]])
        for key, info in self.elements.items():
            if key.startswith("_") or not isinstance(info, dict) or "guid" not in info:
                continue
            sid = key.split(".")[0] if info.get("sektion") in ("roer", "vaegge") else key
            el = spec_el.get(sid, {})
            gid = explicit(key, sid)
            if gid is None and el.get("system") and info.get("sektion") in ("installationer", "roer"):
                info["gruppe"] = "system:" + str(el["system"])
                continue
            ent = self.f.by_guid(info["guid"])
            if gid is None:
                if info.get("sektion") == "tage":
                    gid = "TAG"
                elif el.get("art") in KIND_GROUP and info.get("sektion") == "installationer":
                    gid = KIND_GROUP[el["art"]]
                else:
                    gid = next(g for k, g in CLASS_GROUP if ent.is_a(k)) if ent.is_a("IfcElement") or \
                        ent.is_a("IfcSpace") else "BYGNING"
            info["gruppe"] = gid
            members.setdefault(gid, []).append(ent)
        for m, gid in rules:
            if m not in used:
                self.warnings.append(f"grupper.{gid}.omfatter '{m}' rammer intet element eller system")
        # create the used groups and their parent groups (top groups first, stable order)
        active, queue = [], list(members)
        while queue:
            gid = queue.pop(0)
            if gid in active:
                continue
            if gid not in defs:
                defs[gid] = {"navn": gid, "under": None}
            active.append(gid)
            if defs[gid].get("under"):
                queue.append(defs[gid]["under"])
        order = list(defs)
        ents = {}
        for gid in sorted(active, key=order.index):
            g = api.group.add_group(self.f, name=defs[gid]["navn"], description=defs[gid].get("beskrivelse"))
            g.GlobalId = self.guid("gruppe:" + gid)
            g.ObjectType = "Disciplin"
            ents[gid] = g
        for gid in sorted(active, key=order.index):
            children = [ents[k] for k in active if defs[k].get("under") == gid]
            prod = members.get(gid, []) + children
            if prod:
                api.group.assign_group(self.f, products=prod, group=ents[gid])
        self.elements["_grupper"] = {gid: {"navn": defs[gid]["navn"], "under": defs[gid].get("under"),
                                            "antal": len(members.get(gid, []))} for gid in active}

    # ------------------------------------------------------------------ finishing
    def _stable_guids(self):
        """Relationships etc. without a spec id get a GlobalId from the creation order, so the file is reproducible."""
        known = {e["guid"] for e in self.elements.values() if isinstance(e, dict) and "guid" in e}
        n = 0
        for ent in self.f.by_type("IfcRoot"):
            if ent.GlobalId in known or ent.is_a() in ("IfcProject", "IfcSite", "IfcBuilding", "IfcBuildingStorey"):
                continue
            if ent.is_a("IfcTypeObject") or ent.is_a("IfcOpeningElement") or ent.is_a("IfcGroup"):
                continue
            n += 1
            ent.GlobalId = self.guid(f"auto:{ent.is_a()}:{n}")


def build(spec: dict, out: pathlib.Path):
    """Builds the IFC file and a sidecar file (<name>.byg.json) with id → GlobalId, storey, class and quantities."""
    b = Builder(spec)
    f = b.build()
    out.parent.mkdir(parents=True, exist_ok=True)
    f.header.file_name.name = out.name
    f.header.file_name.originating_system = f"byg-bim {VERSION} (IfcOpenShell {ifcopenshell.version})"
    f.header.file_name.time_stamp = dt.datetime.now().replace(microsecond=0).isoformat()
    f.write(str(out))
    sidecar = {"model": spec["model"]["navn"], "schema": spec["model"]["schema"], "ifc": out.name,
                "spec": spec.get("_sti"), "bygget": dt.datetime.now().isoformat(timespec="seconds"),
                "etager": {e["id"]: {"navn": e["navn"], "kote": e["kote"], "hoejde": e["hoejde"]} for e in spec["etager"]},
                "elementer": {k: v for k, v in b.elements.items() if not k.startswith("_")},
                "doere": b.elements.get("_doere", {}), "grupper": b.elements.get("_grupper", {}), "kontrol": spec["model"].get("kontrol"),
                "fejl": b.errors, "advarsler": b.warnings}
    out.with_suffix(".byg.json").write_text(json.dumps(sidecar, ensure_ascii=False, indent=1, default=float),
                                           encoding="utf-8")
    return f, b, sidecar
