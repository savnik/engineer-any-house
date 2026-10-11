"""Deterministisk generator: modelspec → IFC (IFC4 som standard).

Regler, der håndhæves her (buildingSMART Validation Service / Implementer Agreements):
- IfcProject → IfcSite → IfcBuilding → IfcBuildingStorey via IfcRelAggregates; IfcSpace aggregeres under etagen.
- Hvert element er contained i præcis én etage; åbninger via IfcRelVoidsElement, døre/vinduer via IfcRelFillsElement.
- IfcWall (ikke StandardCase) med IfcWallType + IfcMaterialLayerSetUsage; PredefinedType på typen, ikke forekomsten.
- Pset_*: kun egenskaber fra standardskabelonen; enumererede egenskaber (fx Status) som IfcPropertyEnumeratedValue.
- Qto_*: MethodOfMeasurement = BaseQuantities. Egne sæt hedder Byg_* (aldrig Pset_).
- Georeference: IfcMapConversion + IfcProjectedCRS (EPSG:25832, DVR90 = EPSG:5799), Scale 0.001 ved mm.
- Stabile GlobalId'er: uuid5 af modelnavn + element-id, så id'er overlever en genbygning.
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
from shapely.geometry import Polygon

from . import VERSION
from .geo import (VaegGeo, ccw, enhed, flade_ramme, lokal_polygon, omrids_fra_vaegge, rens_ring, rum_polygon,
                  tagflader, til_flade_2d, vaegsamlinger)
from .spec import KILDER, STATUS, SYSTEMARTER

NS = uuid.UUID("6f1d3c52-8a4e-4b7e-9a51-0b1d2c3e4f50")

# art → (IFC-klasse, PredefinedType). USERDEFINED får ObjectType = art.
INSTALLATIONER = {
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
    "ventilationsaggregat": ("IfcUnitaryEquipment", "AIRHANDLER"), "ventilator": ("IfcFan", "PROPELLORAXIAL"),
    "luftventil": ("IfcAirTerminal", "DIFFUSER"), "emhaette": ("IfcAirTerminal", "USERDEFINED"),
    "solcellepanel": ("IfcSolarDevice", "SOLARPANEL"), "skorsten": ("IfcChimney", "NOTDEFINED"),
}
MATFARVER = [  # (nøgleord, kategori, rgb, gennemsigtighed)
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
KLASSEFARVE = {"IfcSpace": ((0.55, 0.75, 0.95), 0.85), "IfcWindow": ((0.62, 0.80, 0.90), 0.5),
               "IfcDoor": ((0.66, 0.50, 0.34), 0), "IfcStair": ((0.80, 0.64, 0.43), 0),
               "roer": ((0.85, 0.20, 0.20), 0), "installation": ((0.93, 0.93, 0.95), 0)}


def _mat(navn):
    n = navn.lower()
    for ord_, kat, rgb, tr in MATFARVER:
        if any(o in n for o in ord_):
            return kat, rgb, tr
    return None, (0.80, 0.80, 0.80), 0


class Bygger:
    def __init__(self, spec: dict):
        self.s = spec
        self.m = spec["model"]
        self.f = None
        self.fejl, self.adv = [], []
        self._mats, self._stile, self._typer, self._klass = {}, {}, {}, {}
        self.elementer = {}  # spec-id → info til sidevognsfilen
        self.vaeggeo = {}

    # ------------------------------------------------------------------ basis
    def guid(self, noegle):
        return ifcopenshell.guid.compress(uuid.uuid5(NS, f"{self.m['navn']}|{noegle}").hex)

    def byg(self):
        self.f = api.project.create_file(version=self.m["schema"])
        self.b = ShapeBuilder(self.f)
        self._projekt()
        self._materialer_og_typer()
        self._vaegge()
        self._aabninger()
        self._daek()
        self._tage_og_klip()
        self._trapper()
        self._soejler_bjaelker()
        self._rum()
        self._systemer()
        self._installationer()
        self._roer()
        self._generisk()
        self._stabile_guids()
        return self.f

    def _projekt(self):
        f, m = self.f, self.m
        self.projekt = api.root.create_entity(f, ifc_class="IfcProject", name=m.get("projekt", m["navn"]))
        self.projekt.GlobalId = self.guid("projekt")
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
        self.bygning = self._spatial("IfcBuilding", "bygning", (m.get("bygning") or {}).get("navn", m["navn"]))
        api.aggregate.assign_object(f, relating_object=self.projekt, products=[self.site])
        api.aggregate.assign_object(f, relating_object=self.site, products=[self.bygning])
        for ent in (self.site, self.bygning):
            self._placer(ent, np.eye(4))
        self.etager, self.etage_kote = {}, {}
        for e in self.s["etager"]:
            st = self._spatial("IfcBuildingStorey", f"etage:{e['id']}", e["navn"])
            st.Elevation = e["kote"]
            api.aggregate.assign_object(f, relating_object=self.bygning, products=[st])
            self._placer(st, self._T((0, 0, e["kote"])))
            self.etager[e["id"]] = st
            self.etage_kote[e["id"]] = e["kote"]
            self._pset(st, "Pset_BuildingStoreyCommon", {"AboveGround": e["kote"] >= -500})
        self.etage_info = {e["id"]: e for e in self.s["etager"]}
        a = m.get("adresse")
        if a:
            adr = f.createIfcPostalAddress(AddressLines=[a.get("vej", "")],
                                          PostalCode=str(a.get("postnr", "")), Town=a.get("by"),
                                          Country=a.get("land", "Danmark"))
            self.bygning.BuildingAddress = adr
        bg = m.get("bygning") or {}
        props = {}
        if bg.get("opfoerelsesaar"):
            props["YearOfConstruction"] = str(bg["opfoerelsesaar"])
        if bg.get("anvendelse"):
            props["OccupancyType"] = str(bg["anvendelse"])
        if "fredet" in bg:
            props["IsLandmarked"] = bool(bg["fredet"])
        props["NumberOfStoreys"] = len(self.s["etager"])
        self._pset(self.bygning, "Pset_BuildingCommon", props)
        g = m.get("geo")
        if g:
            self._georef(g, mm)

    def _georef(self, g, mm):
        f = self.f
        b = math.radians(float(g.get("x_retning", 90)))  # kompasretning (grader fra nord, med uret) af lokal +x
        api.georeference.add_georeferencing(f, ifc_class="IfcMapConversion", name="EPSG:25832")
        meter = f.createIfcSIUnit(UnitType="LENGTHUNIT", Name="METRE")
        api.georeference.edit_georeferencing(
            f, coordinate_operation={"Eastings": float(g["oest"]), "Northings": float(g["nord"]),
                                     "OrthogonalHeight": float(g.get("kote", 0.0)), "XAxisAbscissa": math.sin(b),
                                     "XAxisOrdinate": math.cos(b), "Scale": 0.001},
            projected_crs={"Name": "EPSG:25832", "Description": "ETRS89 / UTM zone 32N, højder DVR90",
                           "GeodeticDatum": "ETRS89", "VerticalDatum": "EPSG:5799", "MapUnit": meter})
        try:
            api.georeference.edit_true_north(f, true_north=(math.cos(b), math.sin(b)))
        except Exception as e:  # true north er pæn at have, ikke kritisk
            self.adv.append(f"geo: true north kunne ikke sættes ({e})")

    def _spatial(self, klasse, noegle, navn):
        ent = api.root.create_entity(self.f, ifc_class=klasse, name=navn)
        ent.GlobalId = self.guid(noegle)
        return ent

    @staticmethod
    def _T(t=(0, 0, 0), x=(1, 0, 0), z=(0, 0, 1)):
        z = enhed(z)
        x = enhed(np.asarray(x, float) - z * (np.asarray(x, float) @ z))
        y = np.cross(z, x)
        M = np.eye(4)
        M[:3, 0], M[:3, 1], M[:3, 2], M[:3, 3] = x, y, z, t
        return M

    def _placer(self, ent, M):
        # edit_object_placement ændrer matricen på stedet (enhedsomregning) – giv altid en kopi
        api.geometry.edit_object_placement(self.f, product=ent, matrix=np.array(M, dtype=float), is_si=False)

    # ------------------------------------------------------------------ materialer, stile, typer
    def materiale(self, navn):
        if navn in self._mats:
            return self._mats[navn]
        info = (self.s.get("materialer") or {}).get(navn) or {}
        kat, rgb, tr = _mat(navn)
        kat = info.get("kategori", kat)
        if info.get("farve"):
            rgb = tuple(info["farve"])
        mat = api.material.add_material(self.f, name=navn, category=kat)
        stil = self.stil(f"mat:{navn}", rgb, info.get("gennemsigtighed", tr))
        api.style.assign_material_style(self.f, material=mat, style=stil, context=self.body)
        self._mats[navn] = mat
        return mat

    def stil(self, noegle, rgb, transp=0.0):
        if noegle in self._stile:
            return self._stile[noegle]
        st = api.style.add_style(self.f, name=noegle.split(":", 1)[-1])
        api.style.add_surface_style(self.f, style=st, ifc_class="IfcSurfaceStyleShading", attributes={
            "SurfaceColour": {"Name": None, "Red": rgb[0], "Green": rgb[1], "Blue": rgb[2]},
            "Transparency": float(transp)})
        self._stile[noegle] = st
        return st

    def _farv(self, rep, noegle, rgb=None, transp=0.0):
        if rgb is None:
            kat, rgb, transp = _mat(noegle)
        api.style.assign_representation_styles(self.f, shape_representation=rep,
                                               styles=[self.stil(f"farve:{noegle}", rgb, transp)])

    def _materialer_og_typer(self):
        f = self.f
        for tid, t in self.s["typer"].items():
            kl = t["klasse"]
            ifc = {"vaeg": "IfcWallType", "daek": "IfcSlabType", "tag": "IfcSlabType", "vindue": "IfcWindowType",
                   "doer": "IfcDoorType"}[kl]
            pre = t.get("predefined")
            if not pre:
                pre = {"vaeg": "SOLIDWALL" if t.get("ude") else ("STANDARD" if t.get("baerende") else "PARTITIONING"),
                       "daek": "FLOOR", "tag": "ROOF", "vindue": "WINDOW", "doer": "DOOR"}[kl]
            typ = api.root.create_entity(f, ifc_class=ifc, name=t.get("navn", tid), predefined_type=pre)
            typ.GlobalId = self.guid(f"type:{tid}")
            if t.get("beskrivelse"):
                typ.Description = t["beskrivelse"]
            if kl in ("vaeg", "daek", "tag"):
                ls = api.material.add_material_set(f, name=t.get("navn", tid), set_type="IfcMaterialLayerSet")
                for mnavn, tyk in t["lag"]:
                    lag = api.material.add_layer(f, layer_set=ls, material=self.materiale(mnavn))
                    api.material.edit_layer(f, layer=lag, attributes={"LayerThickness": float(tyk), "Name": mnavn})
                api.material.assign_material(f, products=[typ], type="IfcMaterialLayerSet", material=ls)
                t["_tykkelse"] = sum(x[1] for x in t["lag"])
                t["_lagsaet"] = ls
            elif kl == "vindue":
                typ.PartitioningType = {1: "SINGLE_PANEL", 2: "DOUBLE_PANEL_VERTICAL", 3: "TRIPLE_PANEL_VERTICAL"}.get(
                    int(t.get("felter", 1)), "SINGLE_PANEL")
            elif kl == "doer":
                # enkeltfløjet: NOTDEFINED på typen – venstre/højre sættes på hver dør
                typ.OperationType = {"enkelt": "NOTDEFINED", "dobbelt": "DOUBLE_DOOR_SINGLE_SWING",
                                     "skyde": "SLIDING_TO_LEFT"}.get(t.get("betjening", "enkelt"), "NOTDEFINED")
            common = {"vaeg": "Pset_WallCommon", "daek": "Pset_SlabCommon", "tag": "Pset_SlabCommon",
                      "vindue": "Pset_WindowCommon", "doer": "Pset_DoorCommon"}[kl]
            props = {"Reference": tid}
            if kl not in ("vindue", "doer") or "ude" in t:  # døre/vinduer arver IsExternal fra væggen pr. forekomst
                props["IsExternal"] = bool(t.get("ude", kl == "tag"))
            if "baerende" in t and kl in ("vaeg", "daek", "tag"):
                props["LoadBearing"] = bool(t["baerende"])
            if "u" in t:
                props["ThermalTransmittance"] = float(t["u"])
            if "brand" in t:
                props["FireRating"] = str(t["brand"])
            self._pset(typ, common, props)
            self._brugerdata(typ, t, f"typer.{tid}")
            self._typer[tid] = typ

    # ------------------------------------------------------------------ fælles for elementer
    def ny(self, klasse, el, suffix="", navn=None, predefined=None, objekttype=None):
        if predefined == "USERDEFINED" and not objekttype:
            objekttype = el.get("art") or el.get("navn") or el["id"]
        ent = api.root.create_entity(self.f, ifc_class=klasse, name=navn or el.get("navn") or el["id"],
                                     predefined_type=predefined)
        ent.GlobalId = self.guid(el["id"] + suffix)
        if hasattr(ent, "Tag"):
            ent.Tag = el["id"] + suffix
        if el.get("beskrivelse"):
            ent.Description = el["beskrivelse"]
        if objekttype and hasattr(ent, "ObjectType"):
            ent.ObjectType = objekttype
        return ent

    def indsaet(self, ent, el, M, common=None, props=None, sektion="", suffix=""):
        """Container, placering, egenskaber og kildedata for et element."""
        st = self.etager[el["etage"]]
        api.spatial.assign_container(self.f, products=[ent], relating_structure=st)
        self._placer(ent, M)
        self.egenskaber(ent, el, common, props or {}, sektion)
        self.elementer[el["id"] + suffix] = {"guid": ent.GlobalId, "klasse": ent.is_a(), "etage": el["etage"],
                                             "status": el["status"], "kilde": str(el["kilde"])[:1], "sektion": sektion}

    def egenskaber(self, ent, el, common, props, sektion):
        props = dict(props)
        status = STATUS[el["status"]]
        tpl_navn = common or self._common_pset(ent.is_a())
        if tpl_navn and self._har_prop(tpl_navn, "Status"):
            props["Status"] = status
        if tpl_navn and props:
            self._pset(ent, tpl_navn, props)
        kilde = str(el["kilde"])
        k = {"Kilde": KILDER.get(kilde[:1], kilde) + (kilde[1:] if len(kilde) > 1 else ""),
             "Reference": str(el.get("ref") or "")}
        if not (tpl_navn and self._har_prop(tpl_navn, "Status")):
            k["Status"] = status
        if el.get("usikkerhed") is not None:
            k["Usikkerhed_mm"] = float(el["usikkerhed"])
        if el.get("fakta"):
            k["Fakta"] = ", ".join(map(str, el["fakta"])) if isinstance(el["fakta"], list) else str(el["fakta"])
        if el.get("note"):
            k["Note"] = str(el["note"])
        p = api.pset.add_pset(self.f, product=ent, name="Byg_Kilde")
        api.pset.edit_pset(self.f, pset=p, properties={a: v for a, v in k.items() if v != ""})
        self._brugerdata(ent, el, f"{sektion}.{el['id']}")

    def _brugerdata(self, ent, el, sti):
        for pnavn, pv in (el.get("egenskaber") or {}).items():
            if pnavn.lower().startswith("qto_") or (pnavn.lower().startswith("pset") and not pnavn.startswith("Pset_")):
                self.fejl.append(f"{sti}.egenskaber: '{pnavn}' – egne sæt må ikke starte med 'pset'/'qto'")
                continue
            if not isinstance(pv, dict):
                self.fejl.append(f"{sti}.egenskaber.{pnavn}: skal være en mapping af egenskaber")
                continue
            self._pset(ent, pnavn, pv, sti=sti)
        kl = el.get("klassifikation")
        if kl:
            system = kl.get("system", "BIM7AA")
            if system not in self._klass:
                self._klass[system] = api.classification.add_classification(self.f, classification=system)
            api.classification.add_reference(self.f, products=[ent], identification=str(kl.get("kode", "")),
                                             name=kl.get("navn"), classification=self._klass[system])

    def _tpl(self):
        if not hasattr(self, "_tplc"):
            self._tplc = ifcopenshell.util.pset.get_template(self.m["schema"])
        return self._tplc

    def _common_pset(self, klasse):
        kand = [p.Name for p in self._tpl().get_applicable(klasse, pset_only=True)]
        navn = f"Pset_{klasse[3:]}Common"
        if navn in kand:
            return navn
        typ = f"Pset_{klasse[3:]}TypeCommon"
        if typ in kand:
            return typ
        return next((n for n in kand if n.endswith("Common") and n != "Pset_ElectricalDeviceCommon"), None)

    def _har_prop(self, pnavn, prop):
        t = self._tpl().get_by_name(pnavn)
        return bool(t) and any(p.Name == prop for p in t.HasPropertyTemplates)

    def _pset(self, ent, navn, props, sti=None):
        """Standardsæt (Pset_*) bygges direkte ud fra skabelonens datatyper – enumererede egenskaber som
        IfcPropertyEnumeratedValue (PSE001). Egne sæt (Byg_* m.fl.) får typer udledt af Python-værdien."""
        if not props:
            return
        if not navn.startswith("Pset_"):
            pset = api.pset.add_pset(self.f, product=ent, name=navn)
            api.pset.edit_pset(self.f, pset=pset, properties=props)
            return
        t = self._tpl().get_by_name(navn)
        if not t:
            self.fejl.append(f"{sti or ent.Name}: '{navn}' er ikke et standardsæt i {self.m['schema']}")
            return
        nye = []
        for k, v in props.items():
            pt = next((p for p in t.HasPropertyTemplates if p.Name == k), None)
            if not pt:
                self.fejl.append(f"{sti or ent.Name}: '{k}' findes ikke i {navn}")
                continue
            if pt.TemplateType == "P_ENUMERATEDVALUE":
                tilladt = [x.wrappedValue for x in pt.Enumerators.EnumerationValues]
                vs = [str(x).upper() for x in (v if isinstance(v, list) else [v])]
                if any(x not in tilladt for x in vs):
                    self.fejl.append(f"{sti or ent.Name}: {navn}.{k} skal være en af {tilladt}, fik {v}")
                    continue
                nye.append(self.f.createIfcPropertyEnumeratedValue(
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
                    nye.append(self.f.createIfcPropertySingleValue(Name=k, NominalValue=self.f.create_entity(mt, vv)))
                except (TypeError, ValueError, RuntimeError) as e:
                    self.fejl.append(f"{sti or ent.Name}: {navn}.{k} = {v!r} passer ikke til {mt} ({e})")
            else:
                self.fejl.append(f"{sti or ent.Name}: {navn}.{k} ({pt.TemplateType}) understøttes ikke – brug et Byg_-sæt")
        if nye:
            pset = api.pset.add_pset(self.f, product=ent, name=navn)
            pset.HasProperties = nye

    def _enumref(self, enumtpl):
        if not hasattr(self, "_enums"):
            self._enums = {}
        if enumtpl.Name not in self._enums:
            self._enums[enumtpl.Name] = self.f.createIfcPropertyEnumeration(
                Name=enumtpl.Name, EnumerationValues=[self.f.createIfcLabel(v.wrappedValue)
                                                      for v in enumtpl.EnumerationValues])
        return self._enums[enumtpl.Name]

    def _qto(self, ent, navn, q):
        q = {k: float(v) for k, v in q.items() if v is not None and v > 0}
        if not q:
            return
        qto = api.pset.add_qto(self.f, product=ent, name=navn)
        api.pset.edit_qto(self.f, qto=qto, properties=q)
        qto.MethodOfMeasurement = "BaseQuantities"
        self.elementer.setdefault(ent.Tag if hasattr(ent, "Tag") and ent.Tag else ent.Name, {}).setdefault("qto", {}).update(q)

    def _rep(self, ent, items, kontekst=None, farve=None, rgb=None, transp=0.0):
        rep = self.b.get_representation(kontekst or self.body, items if isinstance(items, list) else [items])
        api.geometry.assign_representation(self.f, product=ent, representation=rep)
        if farve or rgb:
            self._farv(rep, farve or ent.is_a(), rgb, transp)
        return rep

    def _ekstruder(self, ring, h, z0=0.0, huller=(), retning=(0, 0, 1)):
        ring = rens_ring(ring)
        kurve = self.b.polyline([tuple(p) for p in ccw(ring)], closed=True)
        indre = [self.b.polyline([tuple(p) for p in ccw(rens_ring(hh))[::-1]], closed=True) for hh in huller]
        prof = self.b.profile(kurve, inner_curves=indre)
        return self.b.extrude(prof, magnitude=float(h), position=(0.0, 0.0, float(z0)), extrusion_vector=retning)

    def _klip(self, solid, planer):
        for pkt, n in planer:
            hs = self.b.half_space_solid(self.b.plane(location=tuple(map(float, pkt)), normal=tuple(map(float, n))),
                                         agreement_flag=False)
            solid = self.f.createIfcBooleanClippingResult("DIFFERENCE", solid, hs)
        return solid

    def _materiale_til(self, ent, navn):
        if navn:
            api.material.assign_material(self.f, products=[ent], type="IfcMaterial", material=self.materiale(navn))

    # ------------------------------------------------------------------ vægge
    def _daek_over(self, etage_id):
        """Tykkelsen af det tykkeste gulvdæk på etagen over (0 hvis intet). Bruges til standardhøjder."""
        ids = [e["id"] for e in self.s["etager"]]
        i = ids.index(etage_id)
        if i + 1 >= len(ids):
            return 0.0
        tyk = [(self.s["typer"][d["type"]]["_tykkelse"] if d.get("type") else float(d.get("tykkelse", 0)))
               for d in self.s["daek"] if d["etage"] == ids[i + 1] and d["art"] in ("gulv", "loft") and d["top"] == 0]
        return max(tyk, default=0.0)

    def _vaegge(self):
        segs = self.s["_vaegsegmenter"]
        pr_etage = {}
        for i, seg in enumerate(segs):
            t = self.s["typer"][seg["type"]]
            seg["_ude"] = bool(t.get("ude"))
            seg["_orden"] = i
            pr_etage.setdefault(seg["etage"], []).append(VaegGeo(seg, sum(x[1] for x in t["lag"])))
        for eid, ws in pr_etage.items():
            try:
                vaegsamlinger(ws)
            except ValueError as e:
                self.fejl.append(str(e))
            for w in ws:
                self.vaeggeo[w.id] = w
        for seg in segs:
            w = self.vaeggeo[seg["id"]]
            t = self.s["typer"][seg["type"]]
            et = self.etage_info[seg["etage"]]
            # standard: ydervægge til næste etages gulv (de bærer dækket); indervægge til dækkets underside
            h = seg.get("hoejde", et["hoejde"] - (0.0 if t.get("ude") else self._daek_over(seg["etage"])))
            bund = seg.get("bund", 0.0)
            w.hoejde, w.bund = h, bund
            ent = self.ny("IfcWall", seg)
            ring = lokal_polygon(w, w.fodaftryk)
            solid = self._ekstruder(ring, h)
            w.solid = solid
            w.ent = ent
            M = self._T((w.p1[0], w.p1[1], self.etage_kote[seg["etage"]] + bund), (w.ux[0], w.ux[1], 0))
            w.M = M
            self.indsaet(ent, seg, M, "Pset_WallCommon", {}, "vaegge")
            akse = self.b.polyline([(0.0, 0.0), (float(w.L), 0.0)])
            self._rep(ent, akse, self.axis)
            w.rep = self._rep(ent, solid)
            self._farv(w.rep, t["lag"][0][0] if t["lag"] else "vaeg")
            api.type.assign_type(self.f, related_objects=[ent], relating_type=self._typer[seg["type"]],
                                 should_map_representations=False)
            usage = self._lagbrug(ent, t)
            # lag fra højre (yR) mod venstre; i ydervægsløkker skal første lag ligge ude
            ude_venstre = seg.get("ude_venstre")
            fra_venstre = (ude_venstre is True) != bool(seg.get("vend_lag"))
            if usage:
                api.material.edit_layer_usage(self.f, usage=usage, attributes={
                    "LayerSetDirection": "AXIS2", "DirectionSense": "NEGATIVE" if fra_venstre else "POSITIVE",
                    "OffsetFromReferenceLine": float(w.yL if fra_venstre else w.yR)})
            w.aabninger = []

    def _lagbrug(self, ent, t):
        """IfcMaterialLayerSetUsage på forekomsten (typen bærer selve lagsættet)."""
        def find():
            for r in getattr(ent, "HasAssociations", []) or []:
                if r.is_a("IfcRelAssociatesMaterial") and r.RelatingMaterial.is_a("IfcMaterialLayerSetUsage"):
                    return r.RelatingMaterial
            return None
        if find() is None and t.get("_lagsaet"):
            api.material.assign_material(self.f, products=[ent], type="IfcMaterialLayerSetUsage", material=t["_lagsaet"])
        return find()

    # ------------------------------------------------------------------ åbninger
    def _aabninger(self):
        f = self.f
        for a in self.s["aabninger"]:
            w = self.vaeggeo.get(a["vaeg"])
            if w is None:
                continue
            bredde, hoejde, x0, z0 = a["bredde"], a["hoejde"], a["afstand"], a["brystning"]
            sti = f"aabninger.{a['id']}"
            if x0 < -1 or x0 + bredde > w.L + 1:
                self.fejl.append(f"{sti}: åbningen ({x0:.0f}–{x0 + bredde:.0f}) ligger uden for væggens længde {w.L:.0f}")
            if z0 < -1 or z0 + hoejde > w.hoejde + 1:
                self.fejl.append(f"{sti}: åbningen (z {z0:.0f}–{z0 + hoejde:.0f}) går ud over væghøjden {w.hoejde:.0f}")
            for (b0, b1, aid) in w.aabninger:
                if x0 < b1 - 1 and x0 + bredde > b0 + 1:
                    self.fejl.append(f"{sti}: overlapper åbningen {aid} i væg {w.id}")
            w.aabninger.append((x0, x0 + bredde, a["id"]))
            # åbningselement gennem hele vægtykkelsen (+10 mm hver side)
            aab = self.ny("IfcOpeningElement", a, suffix="/hul", navn=f"Åbning {a['id']}", predefined="OPENING")
            api.feature.add_feature(f, feature=aab, element=w.ent)
            Mo = w.M @ self._T((x0, w.yR - 10, z0))
            self._placer(aab, Mo)
            prof = self.b.polyline([(0.0, 0.0), (bredde, 0.0), (bredde, w.t + 20), (0.0, w.t + 20)], closed=True)
            self._rep(aab, self.b.extrude(self.b.profile(prof), magnitude=hoejde))
            info = {"vaeg": w.id, "x0": x0, "x1": x0 + bredde, "z0": z0, "z1": z0 + hoejde}
            if a["_klasse"] == "hul":
                self.elementer[a["id"]] = {"guid": aab.GlobalId, "klasse": "IfcOpeningElement", "etage": w.seg["etage"],
                                           "status": a["status"], "kilde": str(a["kilde"])[:1], **info}
                continue
            t = self.s["typer"][a["type"]]
            el = {**a, "etage": w.seg["etage"]}
            yc = (w.yR + w.yL) / 2
            ude_y = w.yL if w.seg.get("ude_venstre") else w.yR
            plac = a.get("placering", "ude" if a["_klasse"] == "vindue" and w.seg.get("_ude") else "midt")
            if plac != "midt":
                ind_y = w.yR if ude_y == w.yL else w.yL
                yc = (3 * (ude_y if plac == "ude" else ind_y) + (ind_y if plac == "ude" else ude_y)) / 4
            if a["_klasse"] == "vindue":
                ld = min(w.t, float(t.get("ramme", 100)))
                ent = self.ny("IfcWindow", el)
                ent.OverallWidth, ent.OverallHeight = bredde, hoejde
                M = w.M @ self._T((x0, yc - ld / 2, z0))
                self._vindue_geo(ent, bredde, hoejde, ld, int(t.get("felter", 1)))
                kq = "Qto_WindowBaseQuantities"
            else:
                ld = w.t if not w.seg.get("_ude") else min(w.t, 150.0)
                ent = self.ny("IfcDoor", el)
                ent.OverallWidth, ent.OverallHeight = bredde, hoejde
                mod = a.get("slaar_mod", "venstre")
                if mod in ("inde", "ude"):
                    uv = w.seg.get("ude_venstre")
                    if uv is None:
                        self.fejl.append(f"{sti}: slaar_mod {mod} kræver en væg i en lukket ydervægsløkke – brug venstre/hoejre")
                        uv = False
                    mod = "venstre" if (mod == "ude") == uv else "hoejre"
                hs = a.get("haengsel", "start")
                if mod == "venstre":
                    M = w.M @ self._T((x0, yc - ld / 2, z0))
                    op = "SINGLE_SWING_LEFT" if hs == "start" else "SINGLE_SWING_RIGHT"
                else:
                    M = w.M @ self._T((x0 + bredde, yc + ld / 2, z0), x=(-1, 0, 0))
                    op = "SINGLE_SWING_LEFT" if hs == "slut" else "SINGLE_SWING_RIGHT"
                typop = self._typer[a["type"]].OperationType
                if typop in (None, "NOTDEFINED"):
                    ent.OperationType = op  # enkeltfløjet: håndetheden hører til forekomsten
                self._doer_geo(ent, bredde, hoejde, ld)
                kq = "Qto_DoorBaseQuantities"
                self.elementer.setdefault("_doere", {})[a["id"]] = {"aabner": op, "mod": mod}
            api.spatial.assign_container(f, products=[ent], relating_structure=self.etager[w.seg["etage"]])
            self._placer(ent, M)
            api.feature.add_filling(f, opening=aab, element=ent)
            api.type.assign_type(f, related_objects=[ent], relating_type=self._typer[a["type"]],
                                 should_map_representations=False)
            self.egenskaber(ent, el, None, {"IsExternal": bool(w.seg.get("_ude"))}, "aabninger")
            self.elementer[a["id"]] = {"guid": ent.GlobalId, "klasse": ent.is_a(), "etage": w.seg["etage"],
                                       "status": a["status"], "kilde": str(a["kilde"])[:1], **info}
            self._qto(ent, kq, {"Width": bredde, "Height": hoejde, "Area": bredde * hoejde / 1e6})
        for w in self.vaeggeo.values():
            if not hasattr(w, "ent"):
                continue
            L = self._laengde(w)
            aab_areal = sum((self.elementer[i]["x1"] - self.elementer[i]["x0"]) * (self.elementer[i]["z1"] - self.elementer[i]["z0"])
                            for _, _, i in w.aabninger if i in self.elementer) / 1e6
            q = {"Length": L, "Width": w.t, "Height": w.hoejde, "GrossFootprintArea": w.fodaftryk.area / 1e6}
            if not getattr(w, "klippet", False):
                q.update(GrossSideArea=L * w.hoejde / 1e6, NetSideArea=L * w.hoejde / 1e6 - aab_areal,
                         GrossVolume=w.fodaftryk.area * w.hoejde / 1e9,
                         NetVolume=w.fodaftryk.area * w.hoejde / 1e9 - aab_areal * w.t / 1000)
            w.qto = q

    def _kasse(self, x0, y0, z0, dx, dy, dz):
        prof = self.b.profile(self.b.polyline([(0.0, 0.0), (dx, 0.0), (dx, dy), (0.0, dy)], closed=True))
        return self.b.extrude(prof, magnitude=float(dz), position=(float(x0), float(y0), float(z0)))

    def _ramme_xz(self, pts, huller, ld):
        """Profil i xz-planet (x langs væggen, z op) ekstruderet gennem y = 0…ld."""
        ydre = self.b.polyline([tuple(map(float, q)) for q in ccw(pts)], closed=True)
        indre = [self.b.polyline([tuple(map(float, q)) for q in ccw(h)[::-1]], closed=True) for h in huller]
        return self.b.extrude(self.b.profile(ydre, inner_curves=indre), magnitude=float(ld), position=(0.0, float(ld), 0.0),
                              position_z_axis=(0.0, -1.0, 0.0), position_x_axis=(1.0, 0.0, 0.0))

    def _vindue_geo(self, ent, W, H, ld, felter, k=60.0):
        """Karm, poster og glas. Lokalt: x 0…W langs væggen, y 0…ld gennem væggen, z 0…H."""
        items = [self._ramme_xz([(0, 0), (W, 0), (W, H), (0, H)], [[(k, k), (W - k, k), (W - k, H - k), (k, H - k)]], ld)]
        for i in range(1, max(1, felter)):
            items.append(self._kasse(i * W / felter - k / 2, 0, k, k, ld, H - 2 * k))
        items.append(self._kasse(k, ld / 2 - 4, k, W - 2 * k, 8, H - 2 * k))
        rep = self._rep(ent, items)
        self._farv(rep, "IfcWindow", *KLASSEFARVE["IfcWindow"])
        return rep

    def _doer_geo(self, ent, W, H, ld, k=60.0):
        """Karm (U) og lukket dørblad. Slagretningen ligger i OperationType og dørens lokale +y."""
        karm = self._ramme_xz([(0, 0), (k, 0), (k, H - k), (W - k, H - k), (W - k, 0), (W, 0), (W, H), (0, H)], [], ld)
        blad = self._kasse(k + 3, ld / 2 - 20, 0, W - 2 * k - 6, 40, H - k - 3)
        rep = self._rep(ent, [karm, blad])
        self._farv(rep, "IfcDoor", *KLASSEFARVE["IfcDoor"])
        return rep

    def _laengde(self, w):
        xs = [w.verden_til_lokal(p)[0] for p in w.fodaftryk.exterior.coords]
        return max(xs) - min(xs)

    # ------------------------------------------------------------------ dæk
    def _daek(self):
        for d in self.s["daek"]:
            o = d["omrids"]
            if isinstance(o, dict):
                polys = [w.fodaftryk for w in self.vaeggeo.values() if w.seg["kaede"] == o["fra_vaegge"]]
                if not polys:
                    self.fejl.append(f"daek.{d['id']}.omrids.fra_vaegge: ingen vægge med id '{o['fra_vaegge']}'")
                    continue
                poly = omrids_fra_vaegge(polys, o["kant"])
                if poly is None:
                    self.fejl.append(f"daek.{d['id']}: væggene '{o['fra_vaegge']}' danner ikke en lukket løkke")
                    continue
                ring = list(poly.exterior.coords)[:-1]
            else:
                ring = list(o)
            t = self.s["typer"].get(d.get("type")) if d.get("type") else None
            tyk = t["_tykkelse"] if t else float(d["tykkelse"])
            pre = {"gulv": "FLOOR", "loft": "FLOOR", "bund": "BASESLAB", "tag": "ROOF"}[d["art"]]
            ent = self.ny("IfcSlab", d, predefined=None if t else pre)
            solid = self._ekstruder(ring, tyk, z0=0.0, huller=d["huller"], retning=(0, 0, -1))
            M = self._T((0, 0, self.etage_kote[d["etage"]] + d["top"]))
            self.indsaet(ent, d, M, "Pset_SlabCommon", {}, "daek")
            rep = self._rep(ent, solid)
            self._farv(rep, t["lag"][0][0] if t else "beton")
            if t:
                api.type.assign_type(self.f, related_objects=[ent], relating_type=self._typer[d["type"]],
                                     should_map_representations=False)
                usage = self._lagbrug(ent, t)
                if usage:
                    api.material.edit_layer_usage(self.f, usage=usage, attributes={
                        "LayerSetDirection": "AXIS3", "DirectionSense": "NEGATIVE", "OffsetFromReferenceLine": 0.0})
            p = Polygon(ring)
            netto = p.area - sum(Polygon(h).area for h in d["huller"])
            self._qto(ent, "Qto_SlabBaseQuantities", {"Width": tyk, "GrossArea": p.area / 1e6, "NetArea": netto / 1e6,
                                                      "Perimeter": p.length, "GrossVolume": p.area * tyk / 1e9,
                                                      "NetVolume": netto * tyk / 1e9})

    # ------------------------------------------------------------------ tage (og klipning af vægge/rum)
    def _tage_og_klip(self):
        self.tagplaner = {}
        for t in self.s["tage"]:
            kote = self.etage_kote[t["etage"]]
            flader = tagflader(t)
            typ = self.s["typer"].get(t.get("type")) if t.get("type") else None
            tyk = typ["_tykkelse"] if typ else t["tykkelse"]
            tag = self.ny("IfcRoof", t, predefined={"sadeltag": "GABLE_ROOF", "valmtag": "HIP_ROOF",
                                                    "pulttag": "SHED_ROOF", "fladt": "FLAT_ROOF"}[t["form"]])
            self.indsaet(tag, t, self._T((0, 0, kote)), "Pset_RoofCommon", {}, "tage")
            planer, dele = [], []
            for fl in flader:
                o, xa, ya, za = flade_ramme(fl)
                ring = til_flade_2d(fl, (o, xa, ya, za))
                el = {**t, "id": t["id"]}
                slab = self.ny("IfcSlab", el, suffix=f".{fl.navn}", navn=f"{t.get('navn', t['id'])} {fl.navn}",
                               predefined=None if typ else "ROOF")
                Mw = self._T((o[0], o[1], o[2] + kote), x=xa, z=za)
                self._placer(slab, Mw)
                rep = self._rep(slab, self._tagflade_solid(fl, ring, tyk, (o, xa, ya, za), t["form"]))
                self._farv(rep, typ["lag"][0][0] if typ else "tagsten")
                if typ:
                    api.type.assign_type(self.f, related_objects=[slab], relating_type=self._typer[t["type"]],
                                         should_map_representations=False)
                    usage = self._lagbrug(slab, typ)
                    if usage:
                        # lag listes ovenfra og ned: referencen er pladens overside (z = tykkelse), lagene går nedad
                        api.material.edit_layer_usage(self.f, usage=usage, attributes={
                            "LayerSetDirection": "AXIS3", "DirectionSense": "NEGATIVE", "OffsetFromReferenceLine": float(tyk)})
                self.egenskaber(slab, {**t, "id": t["id"]}, "Pset_SlabCommon", {}, "tage")
                areal = Polygon(ring).area
                self._qto(slab, "Qto_SlabBaseQuantities", {"Width": tyk, "GrossArea": areal / 1e6, "NetArea": areal / 1e6})
                dele.append(slab)
                planer.append((np.array([o[0], o[1], o[2] + kote]), za))
                self.elementer[f"{t['id']}.{fl.navn}"] = {"guid": slab.GlobalId, "klasse": "IfcSlab", "etage": t["etage"],
                                                         "status": t["status"], "kilde": str(t["kilde"])[:1], "sektion": "tage"}
            api.aggregate.assign_object(self.f, relating_object=tag, products=dele)
            self.tagplaner[t["id"]] = planer
        # klip vægge med til_tag
        for w in self.vaeggeo.values():
            tid = w.seg.get("til_tag")
            if not tid or not hasattr(w, "rep"):
                continue
            O = w.M[:3, 3]
            R = w.M[:3, :3]
            planer = [((p - O) @ R, n @ R) for p, n in self.tagplaner[tid]]
            klippet = self._klip(w.solid, planer)
            ny = self.b.get_representation(self.body, [klippet])
            api.geometry.unassign_representation(self.f, product=w.ent, representation=w.rep)
            api.geometry.assign_representation(self.f, product=w.ent, representation=ny)
            t = self.s["typer"][w.seg["type"]]
            self._farv(ny, t["lag"][0][0] if t["lag"] else "vaeg")
            ifcopenshell.api.geometry.remove_representation(self.f, representation=w.rep)
            w.rep, w.klippet = ny, True
            for k in ("GrossSideArea", "NetSideArea", "GrossVolume", "NetVolume"):
                w.qto.pop(k, None)
        for w in self.vaeggeo.values():
            if hasattr(w, "ent"):
                self._qto(w.ent, "Qto_WallBaseQuantities", w.qto)

    def _tagflade_solid(self, fl, ring, tyk, ramme, form):
        """Tagflade som plade vinkelret på fladen, skåret lodret (geret) langs alle kanter, så kip og
        grater slutter tæt og tagfod/gavl får lodret afskæring."""
        if form == "fladt":
            return self._ekstruder(ring, tyk)
        o, xa, ya, za = ramme
        stor = Polygon(ring).buffer(3 * tyk, join_style=2)
        solid = self._ekstruder(list(stor.exterior.coords)[:-1], tyk)
        c = np.mean(fl.pkt, axis=0)
        planer = []
        for i in range(len(fl.pkt)):
            a, b_ = fl.pkt[i], fl.pkt[(i + 1) % len(fl.pkt)]
            n = np.cross(b_ - a, (0, 0, 1.0))
            if np.linalg.norm(n) < 1e-9:
                continue
            n = enhed(n)
            if (c - a) @ n > 0:
                n = -n
            planer.append((np.array([(a - o) @ xa, (a - o) @ ya, (a - o) @ za]), np.array([n @ xa, n @ ya, n @ za])))
        return self._klip(solid, planer)

    # ------------------------------------------------------------------ trapper
    def _trapper(self):
        for tr in self.s["trapper"]:
            n = int(round(tr["stigninger"]))
            et = self.etage_info[tr["etage"]]
            R = tr.get("stigning") or et["hoejde"] / n
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
            # profil i (løb, z)-planet ekstruderet på tværs: lokal x = løb, lokal y = op, z = venstre→højre
            ent = self.ny("IfcStair", tr, predefined="STRAIGHT_RUN_STAIR")
            O = start + uy * tr["bredde"] + np.array([0, 0, self.etage_kote[tr["etage"]] + tr["bund"]])
            M = self._T(O, x=ux, z=-uy)
            self.indsaet(ent, tr, M, "Pset_StairCommon", {"NumberOfRiser": n, "NumberOfTreads": n - 1,
                                                          "RiserHeight": R, "TreadLength": G}, "trapper")
            rep = self._rep(ent, self._ekstruder(rens_ring(pts), tr["bredde"]))
            self._farv(rep, tr.get("materiale", "træ"))
            self._materiale_til(ent, tr.get("materiale"))
            self.elementer[tr["id"]]["trappe"] = {"stigning": R, "grund": G, "n": n,
                                                  "laengde": (n - 1) * G, "2s+g": 2 * R + G}

    # ------------------------------------------------------------------ søjler og bjælker
    def _profildef(self, p):
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

    def _soejler_bjaelker(self):
        for s in self.s["soejler"]:
            h = s.get("hoejde") or self.etage_info[s["etage"]]["hoejde"] - self._daek_over(s["etage"]) - s["bund"]
            ent = self.ny("IfcColumn", s, predefined="COLUMN")
            r = math.radians(s["rotation"])
            M = self._T((s["punkt"][0], s["punkt"][1], self.etage_kote[s["etage"]] + s["bund"]),
                        x=(math.cos(r), math.sin(r), 0))
            self.indsaet(ent, s, M, "Pset_ColumnCommon", {"LoadBearing": True}, "soejler")
            solid = self.f.createIfcExtrudedAreaSolid(self._profildef(s["profil"]), None,
                                                      self.f.createIfcDirection((0.0, 0.0, 1.0)), float(h))
            rep = self._rep(ent, solid)
            self._farv(rep, s.get("materiale", "stål"))
            self._materiale_til(ent, s.get("materiale"))
            self._qto(ent, "Qto_ColumnBaseQuantities", {"Length": h})
        for bj in self.s["bjaelker"]:
            a, b_ = np.array(bj["fra"], float), np.array(bj["til"], float)
            L = float(np.linalg.norm(b_ - a))
            if L < 1:
                self.fejl.append(f"bjaelker.{bj['id']}: længde 0")
                continue
            z = enhed(b_ - a)
            xh = np.cross((0, 0, 1), z)
            x = enhed(xh) if np.linalg.norm(xh) > 1e-6 else np.array([1.0, 0, 0])
            y = np.cross(z, x)
            p = bj["profil"]
            hh = p.get("h", p.get("d", 0))
            off = {"top": -hh / 2, "midt": 0.0, "bund": hh / 2}[bj["kant"]]
            O = a + y * off + np.array([0, 0, self.etage_kote[bj["etage"]]])
            ent = self.ny("IfcBeam", bj, predefined="BEAM")
            self.indsaet(ent, bj, self._T(O, x=x, z=z), "Pset_BeamCommon", {"LoadBearing": True}, "bjaelker")
            solid = self.f.createIfcExtrudedAreaSolid(self._profildef(p), None, self.f.createIfcDirection((0.0, 0.0, 1.0)), L)
            rep = self._rep(ent, solid)
            self._farv(rep, bj.get("materiale", "stål"))
            self._materiale_til(ent, bj.get("materiale"))
            self._qto(ent, "Qto_BeamBaseQuantities", {"Length": L})

    # ------------------------------------------------------------------ rum
    def _rum(self):
        for r in self.s["rum"]:
            et = self.etage_info[r["etage"]]
            if "punkt" in r:
                polys = [w.fodaftryk for w in self.vaeggeo.values() if w.seg["etage"] == r["etage"]]
                poly = rum_polygon(r["punkt"], polys, r.get("afgraensning") or ())
                if poly is None:
                    self.fejl.append(f"rum.{r['id']}: punktet {r['punkt']} ligger ikke i et lukket rum på etage "
                                     f"{r['etage']} (tjek vægge/afgrænsning, eller angiv omrids)")
                    continue
                if poly.interiors:
                    self.adv.append(f"rum.{r['id']}: rummet omslutter fritstående vægge/søjler ({len(poly.interiors)})")
                ring = list(poly.exterior.coords)[:-1]
                huller = [list(i.coords)[:-1] for i in poly.interiors]
            else:
                ring, huller = list(r["omrids"]), []
            h = r.get("hoejde") or et.get("fri_hoejde") or et["hoejde"]
            ent = self.ny("IfcSpace", r, navn=r["id"], predefined="INTERNAL")
            ent.LongName = r.get("navn") or r["id"]
            api.aggregate.assign_object(self.f, relating_object=self.etager[r["etage"]], products=[ent])
            self._placer(ent, self._T((0, 0, self.etage_kote[r["etage"]] + r["bund"])))
            solid = self._ekstruder(ring, h, huller=huller)
            if r.get("til_tag"):
                O = np.array([0, 0, self.etage_kote[r["etage"]] + r["bund"]])
                solid = self._klip(solid, [(p - O, n) for p, n in self.tagplaner[r["til_tag"]]])
            rep = self._rep(ent, solid)
            self._farv(rep, "IfcSpace", *KLASSEFARVE["IfcSpace"])
            props = {"Reference": r["id"], "IsExternal": False}
            self.egenskaber(ent, r, "Pset_SpaceCommon", props, "rum")
            if r.get("anvendelse"):
                self._pset(ent, "Byg_Rum", {"Anvendelse": str(r["anvendelse"])})
            areal = Polygon(ring, huller).area
            q = {"NetFloorArea": areal / 1e6, "GrossFloorArea": areal / 1e6, "Height": h,
                 "NetPerimeter": Polygon(ring).length}
            if not r.get("til_tag"):
                q["GrossVolume"] = areal * h / 1e9
            self.elementer[r["id"]] = {"guid": ent.GlobalId, "klasse": "IfcSpace", "etage": r["etage"],
                                       "status": r["status"], "kilde": str(r["kilde"])[:1], "navn": ent.LongName,
                                       "sektion": "rum"}
            self._qto(ent, "Qto_SpaceBaseQuantities", q)
            self.elementer[r["id"]]["areal_m2"] = round(areal / 1e6, 2)

    # ------------------------------------------------------------------ VVS/el
    def _systemer(self):
        self.systemer = {}
        for s in self.s["systemer"]:
            ent = api.system.add_system(self.f, ifc_class="IfcDistributionSystem")
            ent.Name = s.get("navn") or s["id"]
            ent.GlobalId = self.guid(s["id"])
            ent.PredefinedType = SYSTEMARTER[s["art"]]
            if ent.PredefinedType == "USERDEFINED":
                ent.ObjectType = s.get("navn") or s["id"]
            self.systemer[s["id"]] = ent
            if hasattr(ent, "Description") and s.get("beskrivelse"):
                ent.Description = s["beskrivelse"]

    def _installationer(self):
        schema = ifcopenshell.ifcopenshell_wrapper.schema_by_name(self.m["schema"] if self.m["schema"] != "IFC4X3" else "IFC4X3_ADD2")
        for el in self.s["installationer"]:
            if el.get("klasse"):
                klasse, pre = el["klasse"], el.get("predefined")
            elif el.get("art") in INSTALLATIONER:
                klasse, pre = INSTALLATIONER[el["art"]]
            else:
                self.fejl.append(f"installationer.{el['id']}.art '{el.get('art')}' er ukendt – brug klasse: Ifc… "
                                 f"eller en af {', '.join(sorted(INSTALLATIONER))}")
                continue
            try:
                schema.declaration_by_name(klasse)
            except Exception:
                self.fejl.append(f"installationer.{el['id']}: {klasse} findes ikke i {self.m['schema']}")
                continue
            ent = self.ny(klasse, el, predefined=pre, objekttype=el.get("art") if pre == "USERDEFINED" else None)
            r = math.radians(el["rotation"])
            p = el["punkt"]
            M = self._T((p[0], p[1], p[2] + self.etage_kote[el["etage"]]), x=(math.cos(r), math.sin(r), 0))
            props = {}
            self.indsaet(ent, el, M, None, props, "installationer")
            g = el["geometri"]
            if "kasse" in g:
                b, d, h = map(float, g["kasse"])
                prof = self.f.createIfcRectangleProfileDef("AREA", None, None, b, d)
            else:
                dia, h = map(float, g["cylinder"])
                prof = self.f.createIfcCircleProfileDef("AREA", None, None, dia / 2)
            solid = self.f.createIfcExtrudedAreaSolid(prof, None, self.f.createIfcDirection((0.0, 0.0, 1.0)), h)
            rep = self._rep(ent, solid)
            self._farv(rep, "installation", *KLASSEFARVE["installation"])
            self._materiale_til(ent, el.get("materiale"))
            if el.get("producent") or el.get("model"):
                self._pset(ent, "Pset_ManufacturerTypeInformation",
                           {k: v for k, v in (("Manufacturer", el.get("producent")), ("ModelLabel", el.get("model")))
                            if v})
            if el.get("system"):
                if ent.is_a("IfcDistributionElement"):
                    api.system.assign_system(self.f, products=[ent], system=self.systemer[str(el["system"])])
                else:
                    self.fejl.append(f"installationer.{el['id']}: {klasse} kan ikke indgå i et system")

    def _roer(self):
        for r in self.s["roer"]:
            pts = [np.array(p, float) for p in r["punkter"]]
            kote = self.etage_kote[r["etage"]]
            klasse = "IfcDuctSegment" if r["art"] == "kanal" else "IfcPipeSegment"
            forrige = None
            for i in range(len(pts) - 1):
                a, b_ = pts[i], pts[i + 1]
                L = float(np.linalg.norm(b_ - a))
                if L < 1:
                    continue
                z = enhed(b_ - a)
                xh = np.cross((0, 0, 1), z)
                x = enhed(xh) if np.linalg.norm(xh) > 1e-6 else np.array([1.0, 0, 0])
                el = {**r, "id": r["id"]}
                ent = self.ny(klasse, el, suffix=f".{i + 1}", predefined="RIGIDSEGMENT")
                M = self._T(a + np.array([0, 0, kote]), x=x, z=z)
                self.indsaet(ent, el, M, None, {}, "roer", suffix=f".{i + 1}")
                d = r["diameter"]
                prof = (self.f.createIfcCircleHollowProfileDef("AREA", None, None, d / 2, float(r["godstykkelse"]))
                        if r.get("godstykkelse") else self.f.createIfcCircleProfileDef("AREA", None, None, d / 2))
                solid = self.f.createIfcExtrudedAreaSolid(prof, None, self.f.createIfcDirection((0.0, 0.0, 1.0)), L)
                rep = self._rep(ent, solid)
                self._farv(rep, f"system:{r.get('system', 'roer')}", *self._systemfarve(r.get("system")))
                self._materiale_til(ent, r.get("materiale"))
                self._qto(ent, "Qto_PipeSegmentBaseQuantities" if klasse == "IfcPipeSegment" else
                          "Qto_DuctSegmentBaseQuantities", {"Length": L})
                p1 = api.system.add_port(self.f, element=ent)
                p2 = api.system.add_port(self.f, element=ent)
                for prt, pos, retn in ((p1, (0, 0, 0), "SINK"), (p2, (0, 0, L), "SOURCE")):
                    prt.FlowDirection = retn
                    prt.PredefinedType = "DUCT" if klasse == "IfcDuctSegment" else "PIPE"
                    self._placer(prt, M @ self._T(pos))
                if forrige is not None:
                    api.system.connect_port(self.f, port1=forrige, port2=p1)
                forrige = p2
                if r.get("system"):
                    api.system.assign_system(self.f, products=[ent], system=self.systemer[str(r["system"])])

    def _systemfarve(self, sid):
        art = next((s["art"] for s in self.s["systemer"] if s["id"] == str(sid)), None)
        return {"varme": ((0.85, 0.15, 0.15), 0), "brugsvand_koldt": ((0.15, 0.45, 0.85), 0),
                "brugsvand_varmt": ((0.90, 0.45, 0.10), 0), "afloeb": ((0.45, 0.35, 0.25), 0),
                "ventilation": ((0.40, 0.75, 0.40), 0), "gas": ((0.95, 0.85, 0.10), 0)}.get(art, ((0.6, 0.6, 0.6), 0))

    # ------------------------------------------------------------------ generisk
    def _generisk(self):
        schema = ifcopenshell.ifcopenshell_wrapper.schema_by_name(self.m["schema"] if self.m["schema"] != "IFC4X3" else "IFC4X3_ADD2")
        for g in self.s["generisk"]:
            klasse = g.get("klasse", "IfcBuildingElementProxy")
            try:
                schema.declaration_by_name(klasse)
            except Exception:
                self.fejl.append(f"generisk.{g['id']}: {klasse} findes ikke i {self.m['schema']}")
                continue
            ent = self.ny(klasse, g, predefined=g.get("predefined"))
            kote = self.etage_kote[g["etage"]]
            if "mesh" in g:
                M = self._T((0, 0, kote))
                self.indsaet(ent, g, M, None, {}, "generisk")
                ms = g["mesh"]
                item = self.b.mesh([tuple(map(float, p)) for p in ms["punkter"]], [list(fl) for fl in ms["flader"]])
                rep = self._rep(ent, item)
            else:
                O = np.array(g["origo"], float) + np.array([0, 0, kote])
                M = self._T(O, x=g["x_akse"], z=g["z_akse"])
                self.indsaet(ent, g, M, None, {}, "generisk")
                solid = self._ekstruder(g["profil"], g["dybde"])
                if g.get("til_tag"):
                    R = M[:3, :3]
                    solid = self._klip(solid, [((p - O) @ R, n @ R) for p, n in self.tagplaner[g["til_tag"]]])
                rep = self._rep(ent, solid)
            self._farv(rep, g.get("materiale", "generisk"))
            self._materiale_til(ent, g.get("materiale"))

    # ------------------------------------------------------------------ afslutning
    def _stabile_guids(self):
        """Relationer o.l. uden spec-id får GlobalId ud fra oprettelsesrækkefølgen, så filen er reproducerbar."""
        kendte = {e["guid"] for e in self.elementer.values() if isinstance(e, dict) and "guid" in e}
        n = 0
        for ent in self.f.by_type("IfcRoot"):
            if ent.GlobalId in kendte or ent.is_a() in ("IfcProject", "IfcSite", "IfcBuilding", "IfcBuildingStorey"):
                continue
            if ent.is_a("IfcTypeObject") or ent.is_a("IfcOpeningElement") or ent.is_a("IfcSystem"):
                continue
            n += 1
            ent.GlobalId = self.guid(f"auto:{ent.is_a()}:{n}")


def byg(spec: dict, ud: pathlib.Path):
    """Bygger IFC-filen og en sidevognsfil (<navn>.byg.json) med id → GlobalId, etage, klasse og mængder."""
    b = Bygger(spec)
    f = b.byg()
    ud.parent.mkdir(parents=True, exist_ok=True)
    f.header.file_name.name = ud.name
    f.header.file_name.originating_system = f"byg-bim {VERSION} (IfcOpenShell {ifcopenshell.version})"
    f.header.file_name.time_stamp = dt.datetime.now().replace(microsecond=0).isoformat()
    f.write(str(ud))
    sidevogn = {"model": spec["model"]["navn"], "schema": spec["model"]["schema"], "ifc": ud.name,
                "spec": spec.get("_sti"), "bygget": dt.datetime.now().isoformat(timespec="seconds"),
                "etager": {e["id"]: {"navn": e["navn"], "kote": e["kote"], "hoejde": e["hoejde"]} for e in spec["etager"]},
                "elementer": {k: v for k, v in b.elementer.items() if not k.startswith("_")},
                "doere": b.elementer.get("_doere", {}), "kontrol": spec["model"].get("kontrol"),
                "fejl": b.fejl, "advarsler": b.adv}
    ud.with_suffix(".byg.json").write_text(json.dumps(sidevogn, ensure_ascii=False, indent=1, default=float),
                                           encoding="utf-8")
    return f, b, sidevogn
