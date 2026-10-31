"""Loading, merging and validation of the model specification (model.yaml).

All lengths in mm, angles in degrees. Coordinates are local building coordinates (x, y in plan);
z is relative to the storey floor (the storey level). See references/spec.md for the format.
"""
import copy
import math
import pathlib

import yaml

SECTIONS = ("vaegge", "aabninger", "daek", "tage", "ovenlys", "trapper", "soejler", "bjaelker", "rum",
             "systemer", "installationer", "roer", "generisk")
PROPOSAL_FIELDS = ("basis", "basis_sha256", "nedrives", "slet")
ID_LISTS = (*SECTIONS, "etager", "fakta", "grupper")   # lists whose elements are merged by id
GROUP_FIELDS = {"id", "navn", "under", "omfatter", "beskrivelse"}
COMMON_FIELDS = {"id", "navn", "etage", "status", "kilde", "ref", "usikkerhed", "fakta", "note", "egenskaber",
           "klassifikation", "beskrivelse"}
FIELDS = {
    "vaegge": {"type", "punkter", "lukket", "justering", "hoejde", "bund", "til_tag", "vend_lag"},
    "aabninger": {"vaeg", "type", "afstand", "brystning", "bredde", "hoejde", "slaar_mod", "haengsel", "placering"},
    "daek": {"type", "omrids", "top", "huller", "art", "tykkelse"},
    "tage": {"form", "omrids", "rygning", "haeldning", "tagfod", "udhaeng", "udhaeng_gavl", "tykkelse", "type", "spaer",
             "hoej_side"},
    "ovenlys": {"tag", "type", "punkt", "flade", "bredde", "hoejde"},
    "trapper": {"start", "retning", "bredde", "stigninger", "stigning", "grund", "materiale", "bund"},
    "soejler": {"punkt", "profil", "hoejde", "bund", "rotation", "materiale"},
    "bjaelker": {"fra", "til", "profil", "materiale", "kant", "rotation"},
    "rum": {"punkt", "omrids", "hoejde", "bund", "til_tag", "anvendelse", "afgraensning"},
    "systemer": {"art", "farve", "under", "el"},
    "installationer": {"art", "klasse", "predefined", "punkt", "geometri", "rotation", "system", "producent",
                       "model", "materiale", "del_af", "el"},
    "roer": {"system", "punkter", "diameter", "godstykkelse", "materiale", "art"},
    "generisk": {"klasse", "predefined", "profil", "origo", "x_akse", "z_akse", "dybde", "mesh", "til_tag",
                 "materiale", "hoejde", "bund"},
}
TYPE_FIELDS = {"klasse", "navn", "lag", "ude", "baerende", "u", "bredde", "hoejde", "felter", "betjening",
              "egenskaber", "klassifikation", "beskrivelse", "ramme", "predefined", "brand"}
STATUS = {"eksisterende": "EXISTING", "ny": "NEW", "nedrives": "DEMOLISH", "midlertidig": "TEMPORARY"}
SOURCES = {"D": "D – dokument/tegning", "M": "M – målt på stedet", "F": "F – foto", "B": "B – oplyst af bygherre",
          "K": "K – godkendt fagnotat", "A": "A – antagelse/skøn"}
ALIGNMENTS = {"midt", "venstre", "hoejre", "yderside", "inderside"}
TYPE_CLASSES = {"vaeg", "daek", "tag", "vindue", "doer"}
ROOF_FORMS = {"sadeltag", "valmtag", "pulttag", "fladt"}
PROFILE_FORMS = {"rekt": ("b", "h"), "rhs": ("b", "h", "t"), "i": ("h", "b", "tw", "tf"), "rund": ("d",),
                "roer": ("d", "t"), "l": ("h", "b", "t")}
SYSTEM_KINDS = {"varme": "HEATING", "brugsvand_koldt": "DOMESTICCOLDWATER", "brugsvand_varmt": "DOMESTICHOTWATER",
               "afloeb": "DRAINAGE", "regnvand": "RAINWATER", "ventilation": "VENTILATION", "el": "ELECTRICAL",
               "belysning": "LIGHTING", "gas": "GAS", "andet": "USERDEFINED"}


class SpecError(Exception):
    def __init__(self, errors):
        self.errors = errors
        super().__init__("\n".join(errors))


def _read(path: pathlib.Path) -> dict:
    try:
        d = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except yaml.YAMLError as e:
        raise SpecError([f"{path.name}: YAML-fejl: {e}"]) from None
    if not isinstance(d, dict):
        raise SpecError([f"{path.name}: topniveauet skal være en mapping"])
    return d


def _merge_dict(a: dict, b: dict) -> dict:
    """Mapping over mapping, recursively: only the given keys change, null removes, lists are replaced."""
    out = dict(a)
    for f, x in b.items():
        if x is None:
            out.pop(f, None)
        elif isinstance(x, dict) and isinstance(a.get(f), dict):
            out[f] = _merge_dict(a[f], x)
        else:
            out[f] = copy.deepcopy(x)
    return out


def _merge(base: dict, overlay: dict) -> dict:
    """Project spec/proposal over the base model: elements with the same id replace the fields, new ones are added.

    A field set to null in the proposal is removed from the element. Top sections that are mappings (typer, vvs,
    model …) are merged recursively: write only the keys that change. `slet:` removes elements entirely (model
    correction); `nedrives:` keeps them with status nedrives (renovation). `bim.py merge` uses the same rules."""
    out = copy.deepcopy(base)
    for k, v in overlay.items():
        if k in PROPOSAL_FIELDS:
            continue
        if k in ID_LISTS:
            lst = out.setdefault(k, [])
            idx = {str(e.get("id")): i for i, e in enumerate(lst)}
            for e in v or []:
                i = idx.get(str(e.get("id")))
                new = copy.deepcopy(e) if i is None else {**lst[i], **copy.deepcopy(e)}
                new = {f: x for f, x in new.items() if x is not None}
                if i is None:
                    idx[str(e.get("id"))] = len(lst)
                    lst.append(new)
                else:
                    lst[i] = new
        elif isinstance(v, dict) and isinstance(out.get(k), dict):
            out[k] = _merge_dict(out[k], v)
        else:
            out[k] = copy.deepcopy(v)
    all_els = {str(e.get("id")): e for s in SECTIONS for e in out.get(s) or []}
    for eid in overlay.get("nedrives") or []:
        eid = str(eid)
        if eid in all_els:
            all_els[eid]["status"] = "nedrives"
        elif eid.split(".")[0] in all_els:
            out.setdefault("_fejl", []).append(
                f"nedrives: '{eid}' er et vægsegment – opdel vægløkken i basismodellen, så segmentet er sin egen væg")
        else:
            out.setdefault("_fejl", []).append(f"nedrives: id '{eid}' findes ikke i basismodellen")
    delete_ids = {str(x) for x in overlay.get("slet") or []}
    if delete_ids:
        found = set()
        for s in ID_LISTS:
            if out.get(s):
                found |= {str(e.get("id")) for e in out[s] if str(e.get("id")) in delete_ids}
                out[s] = [e for e in out[s] if str(e.get("id")) not in delete_ids]
        for eid in sorted(delete_ids - found):
            out.setdefault("_fejl", []).append(f"slet: id '{eid}' findes ikke i basismodellen")
    return out


def load(path) -> dict:
    path = pathlib.Path(path).resolve()
    d = _read(path)
    chain = [path]
    while d.get("basis"):
        b = (chain[-1].parent / d["basis"]).resolve()
        if b in chain:
            raise SpecError([f"basis-løkke: {b}"])
        if not b.exists():
            raise SpecError([f"basis findes ikke: {b}"])
        chain.append(b)
        bd = _read(b)
        d = _merge(bd, d) | ({"basis": bd["basis"]} if bd.get("basis") else {})
        if not bd.get("basis"):
            d.pop("basis", None)
    d["_sti"] = str(path)
    return normalize(d)


def _num(x, path, errors, positive=False):
    if isinstance(x, bool) or not isinstance(x, (int, float)):
        errors.append(f"{path}: forventede et tal, fik {x!r}")
        return 0.0
    if positive and x <= 0:
        errors.append(f"{path}: skal være > 0, fik {x}")
    return float(x)


def _point(p, n, path, errors):
    if not isinstance(p, (list, tuple)) or len(p) != n:
        errors.append(f"{path}: forventede et punkt med {n} koordinater, fik {p!r}")
        return tuple([0.0] * n)
    return tuple(_num(v, path, errors) for v in p)


def _points(ps, n, path, errors, min_count=2):
    if not isinstance(ps, (list, tuple)) or len(ps) < min_count:
        errors.append(f"{path}: forventede mindst {min_count} punkter")
        return []
    return [_point(p, n, f"{path}[{i}]", errors) for i, p in enumerate(ps)]


def normalize(d: dict) -> dict:
    errors = list(d.pop("_fejl", []))
    m = d.setdefault("model", {})
    if not m.get("navn"):
        errors.append("model.navn mangler")
    m.setdefault("schema", "IFC4")
    if m["schema"] not in ("IFC4", "IFC4X3"):
        errors.append(f"model.schema skal være IFC4 eller IFC4X3, fik {m['schema']!r}")
    std = d.setdefault("standard", {})
    std.setdefault("kilde", "A")
    std.setdefault("status", "eksisterende")
    d.setdefault("materialer", {})
    d["typer"] = {str(k): v for k, v in (d.get("typer") or {}).items()}
    for tid, t in d["typer"].items():
        if not isinstance(t, dict):
            errors.append(f"typer.{tid}: skal være en mapping")
            continue
        for k in set(t) - TYPE_FIELDS:
            errors.append(f"typer.{tid}: ukendt felt '{k}'")
        if t.get("klasse") not in TYPE_CLASSES:
            errors.append(f"typer.{tid}.klasse skal være en af {sorted(TYPE_CLASSES)}")
        if t.get("klasse") in ("vaeg", "daek", "tag"):
            layers = t.get("lag")
            if not layers:
                errors.append(f"typer.{tid}: lag mangler (liste af [materiale, tykkelse])")
            else:
                t["lag"] = [(str(l[0]), _num(l[1], f"typer.{tid}.lag[{i}]", errors, positive=True))
                            if isinstance(l, (list, tuple)) and len(l) == 2 else errors.append(
                                f"typer.{tid}.lag[{i}]: skal være [materiale, tykkelse]") or ("?", 1.0)
                            for i, l in enumerate(layers)]
        if t.get("klasse") in ("vindue", "doer"):
            for k in ("bredde", "hoejde"):
                if k not in t:
                    errors.append(f"typer.{tid}.{k} mangler")
                else:
                    t[k] = _num(t[k], f"typer.{tid}.{k}", errors, positive=True)

    storeys = d.get("etager") or []
    if not storeys:
        errors.append("etager mangler (mindst én)")
    for i, e in enumerate(storeys):
        e["id"] = str(e.get("id", ""))
        if not e["id"]:
            errors.append(f"etager[{i}].id mangler")
        e["kote"] = _num(e.get("kote", 0), f"etager.{e['id']}.kote", errors)
    storeys.sort(key=lambda e: e["kote"])
    for i, e in enumerate(storeys):
        if "hoejde" not in e:
            if i + 1 < len(storeys):
                e["hoejde"] = storeys[i + 1]["kote"] - e["kote"]
            else:
                e["hoejde"] = 2500.0
        e["hoejde"] = _num(e["hoejde"], f"etager.{e['id']}.hoejde", errors, positive=True)
        e.setdefault("navn", e["id"])
        if "fri_hoejde" in e:
            e["fri_hoejde"] = _num(e["fri_hoejde"], f"etager.{e['id']}.fri_hoejde", errors, positive=True)
    d["etager"] = storeys
    storey_ids = {e["id"] for e in storeys}

    all_ids = {}
    for s in SECTIONS:
        lst = d.get(s) or []
        if not isinstance(lst, list):
            errors.append(f"{s}: skal være en liste")
            lst = []
        d[s] = lst
        for i, el in enumerate(lst):
            if not isinstance(el, dict):
                errors.append(f"{s}[{i}]: skal være en mapping")
                continue
            el["id"] = str(el.get("id", ""))
            path = f"{s}.{el['id'] or i}"
            if not el["id"]:
                errors.append(f"{s}[{i}].id mangler")
            elif el["id"] in all_ids:
                errors.append(f"{path}: id findes allerede i {all_ids[el['id']]}")
            all_ids[el["id"]] = s
            for k in set(el) - FIELDS[s] - COMMON_FIELDS:
                errors.append(f"{path}: ukendt felt '{k}' (tilladt: {', '.join(sorted(FIELDS[s]))})")
            if s not in ("systemer", "aabninger", "ovenlys"):  # openings and roof windows inherit the host's storey
                el["etage"] = str(el.get("etage", ""))
                if el["etage"] not in storey_ids:
                    errors.append(f"{path}.etage '{el['etage']}' findes ikke (etager: {', '.join(sorted(storey_ids))})")
            el.setdefault("status", std["status"])
            if el["status"] not in STATUS:
                errors.append(f"{path}.status skal være en af {sorted(STATUS)}")
            el.setdefault("kilde", std["kilde"])
            if str(el["kilde"])[:1] not in SOURCES:
                errors.append(f"{path}.kilde skal starte med en af {''.join(SOURCES)}")
            el.setdefault("ref", std.get("ref", ""))
            _check_element(s, el, path, d, errors)
    _expand_walls(d, errors)
    seg_ids = {w["id"] for w in d["_vaegsegmenter"]}
    for a in d["aabninger"]:
        if a.get("vaeg") is not None:
            a["vaeg"] = str(a["vaeg"])
            if a["vaeg"] not in seg_ids:
                candidates = sorted(x for x in seg_ids if x.startswith(a["vaeg"] + "."))
                hint = f" – mente du {candidates[0]} … {candidates[-1]}?" if candidates else ""
                errors.append(f"aabninger.{a['id']}.vaeg '{a['vaeg']}' findes ikke{hint}")
    roof_ids = {t["id"] for t in d["tage"]}
    for o in d["ovenlys"]:
        o["tag"] = str(o.get("tag"))
        roof = next((t for t in d["tage"] if t["id"] == o["tag"]), None)
        if roof is None:
            errors.append(f"ovenlys.{o['id']}.tag '{o['tag']}' findes ikke")
        else:
            o["etage"] = roof["etage"]
    for s in ("vaegge", "rum", "generisk"):
        for el in d[s]:
            if el.get("til_tag") is not None:
                el["til_tag"] = str(el["til_tag"])
                if el["til_tag"] not in roof_ids:
                    errors.append(f"{s}.{el['id']}.til_tag '{el['til_tag']}' findes ikke")
    sys_ids = {x["id"] for x in d["systemer"]}
    for s in ("installationer", "roer"):
        for el in d[s]:
            if el.get("system") is not None and str(el["system"]) not in sys_ids:
                errors.append(f"{s}.{el['id']}.system '{el['system']}' findes ikke")
    _check_parents(d, errors)
    _check_groups(d, errors)
    from .property_card import check_facts
    errors += check_facts(d)
    if errors:
        raise SpecError(errors)
    return d


EL_CURVES = {"B", "C", "D", "gG"}
EL_PHASES = {"L1", "L2", "L3", "L1L2L3"}


def _check_parents(d, errors):
    """systemer.under (circuit under a distribution system) and installationer.del_af (part of a host installation)."""
    inst_ids = {x["id"] for x in d["installationer"]}
    for s, key, ids in (("systemer", "under", {x["id"] for x in d["systemer"]}), ("installationer", "del_af", inst_ids)):
        parent = {}
        for el in d[s]:
            if el.get(key) is None:
                continue
            el[key] = str(el[key])
            if el[key] not in ids or el[key] == el["id"]:
                errors.append(f"{s}.{el['id']}.{key} '{el[key]}' findes ikke under {s}")
            else:
                parent[el["id"]] = el[key]
        for start in parent:
            seen, x = {start}, parent[start]
            while x in parent:
                if x in seen:
                    errors.append(f"{s}.{start}.{key}: kæden af {key} går i ring")
                    break
                seen.add(x)
                x = parent[x]
    for el in d["systemer"]:
        e = el.get("el")
        if e is None:
            continue
        path = f"systemer.{el['id']}.el"
        if not isinstance(e, dict):
            errors.append(f"{path}: skal være en mapping (gruppedata som el.py's tavleformat)")
            continue
        for k in ("sikring", "tvaersnit", "laengde", "last"):
            if k in e:
                _num(e[k], f"{path}.{k}", errors, positive=(k != "last"))
        if "kurve" in e and e["kurve"] not in EL_CURVES:
            errors.append(f"{path}.kurve skal være en af {sorted(EL_CURVES)}")
        if "fase" in e and e["fase"] not in EL_PHASES:
            errors.append(f"{path}.fase skal være en af {sorted(EL_PHASES)}")
        for k in ("rcd", "tavle"):
            if k in e and str(e[k]) not in inst_ids:
                errors.append(f"{path}.{k} '{e[k]}' findes ikke under installationer")
    for el in d["installationer"]:
        if el.get("el") is not None and not isinstance(el["el"], dict):
            errors.append(f"installationer.{el['id']}.el: skal være en mapping")


def _check_groups(d, errors):
    """grupper: [{id, navn, under, omfatter: [id patterns]}] – display groups (IfcGroup) besides the standard groups."""
    from .build import STANDARD_GROUPS
    g = d.get("grupper") or []
    if not isinstance(g, list):
        errors.append("grupper: skal være en liste")
        g = []
    d["grupper"] = [x for x in g if isinstance(x, dict)]
    ids = set(STANDARD_GROUPS) | {str(x.get("id")) for x in d["grupper"]}
    for i, x in enumerate(d["grupper"]):
        x["id"] = str(x.get("id", ""))
        path = f"grupper.{x['id'] or i}"
        if not x["id"]:
            errors.append(f"grupper[{i}].id mangler")
        for k in set(x) - GROUP_FIELDS:
            errors.append(f"{path}: ukendt felt '{k}' (tilladt: {', '.join(sorted(GROUP_FIELDS))})")
        covers = x.get("omfatter") or []
        if not isinstance(covers, list) or not all(isinstance(m, str) for m in covers):
            errors.append(f"{path}.omfatter skal være en liste af id'er/mønstre (fx '1-SP-*')")
        if x.get("under") is not None:
            x["under"] = str(x["under"])
            if x["under"] not in ids or x["under"] == x["id"]:
                errors.append(f"{path}.under '{x['under']}' er ikke en gruppe")


def _type(d, el, path, errors, classes):
    t = el.get("type")
    if t is None:
        errors.append(f"{path}.type mangler")
        return None
    t = str(t)
    el["type"] = t
    if t == "hul" and "hul" in classes:
        return None
    if t not in d["typer"]:
        errors.append(f"{path}.type '{t}' findes ikke under typer")
        return None
    if d["typer"][t].get("klasse") not in classes:
        errors.append(f"{path}.type '{t}' har klasse {d['typer'][t].get('klasse')}, forventede {'/'.join(classes)}")
    return d["typer"][t]


def _profile(p, path, errors):
    if not isinstance(p, dict) or p.get("form") not in PROFILE_FORMS:
        errors.append(f"{path}.profil skal have form: {'|'.join(PROFILE_FORMS)} og mål")
        return
    for k in PROFILE_FORMS[p["form"]]:
        if k not in p:
            errors.append(f"{path}.profil.{k} mangler (form {p['form']} kræver {', '.join(PROFILE_FORMS[p['form']])})")
        else:
            p[k] = _num(p[k], f"{path}.profil.{k}", errors, positive=True)


def _check_element(s, el, path, d, errors):
    if s == "vaegge":
        _type(d, el, path, errors, ("vaeg",))
        el["punkter"] = _points(el.get("punkter"), 2, f"{path}.punkter", errors)
        el.setdefault("lukket", False)
        el.setdefault("justering", "midt")
        if el["justering"] not in ALIGNMENTS:
            errors.append(f"{path}.justering skal være en af {sorted(ALIGNMENTS)}")
        if el["lukket"] and len(el["punkter"]) < 3:
            errors.append(f"{path}: lukket væg kræver mindst 3 punkter")
        for k in ("hoejde", "bund"):
            if k in el:
                el[k] = _num(el[k], f"{path}.{k}", errors, positive=(k == "hoejde"))
    elif s == "aabninger":
        t = _type(d, el, path, errors, ("vindue", "doer", "hul"))
        if "vaeg" not in el:
            errors.append(f"{path}.vaeg mangler")
        el["afstand"] = _num(el.get("afstand", None), f"{path}.afstand", errors)
        for k in ("bredde", "hoejde"):
            if k in el:
                el[k] = _num(el[k], f"{path}.{k}", errors, positive=True)
            elif t:
                el[k] = t[k]
            else:
                errors.append(f"{path}.{k} mangler (påkrævet for type hul)")
        kind = t.get("klasse") if t else "hul"
        el["_klasse"] = kind
        el["brystning"] = _num(el.get("brystning", 0 if kind == "doer" else None), f"{path}.brystning", errors)
        if el.get("slaar_mod", "venstre") not in ("venstre", "hoejre", "inde", "ude"):
            errors.append(f"{path}.slaar_mod skal være venstre|hoejre|inde|ude")
        if el.get("haengsel", "start") not in ("start", "slut"):
            errors.append(f"{path}.haengsel skal være start|slut")
        if el.get("placering", "midt") not in ("midt", "ude", "inde"):
            errors.append(f"{path}.placering skal være midt|ude|inde")
    elif s == "ovenlys":
        t = _type(d, el, path, errors, ("vindue",))
        if "tag" not in el:
            errors.append(f"{path}.tag mangler")
        el["punkt"] = _point(el.get("punkt"), 2, f"{path}.punkt", errors)
        for k in ("bredde", "hoejde"):
            if k in el:
                el[k] = _num(el[k], f"{path}.{k}", errors, positive=True)
            elif t:
                el[k] = t[k]
    elif s == "daek":
        if "type" in el:
            _type(d, el, path, errors, ("daek", "tag"))
        elif "tykkelse" not in el:
            errors.append(f"{path}: angiv type eller tykkelse")
        o = el.get("omrids")
        if isinstance(o, dict):
            if "fra_vaegge" not in o:
                errors.append(f"{path}.omrids: brug en punktliste eller {{fra_vaegge: <væg-id>, kant: inderside|yderside}}")
            o["fra_vaegge"] = str(o.get("fra_vaegge"))
            o.setdefault("kant", "inderside")
        else:
            el["omrids"] = _points(o, 2, f"{path}.omrids", errors, min_count=3)
        el["huller"] = [_points(h, 2, f"{path}.huller[{i}]", errors, min_count=3) for i, h in enumerate(el.get("huller") or [])]
        el["top"] = _num(el.get("top", 0), f"{path}.top", errors)
        el.setdefault("art", "gulv")
        if el["art"] not in ("gulv", "bund", "tag", "loft"):
            errors.append(f"{path}.art skal være gulv|bund|loft|tag")
    elif s == "tage":
        if el.get("form") not in ROOF_FORMS:
            errors.append(f"{path}.form skal være en af {sorted(ROOF_FORMS)}")
        o = el.get("omrids")
        if not (isinstance(o, (list, tuple)) and len(o) == 4 and all(isinstance(v, (int, float)) for v in o)):
            errors.append(f"{path}.omrids skal være [x0, y0, x1, y1] (rektangel ved facadens yderside)")
        else:
            x0, y0, x1, y1 = map(float, o)
            el["omrids"] = (min(x0, x1), min(y0, y1), max(x0, x1), max(y0, y1))
        for k, std in (("haeldning", 45), ("tagfod", None), ("udhaeng", 0), ("tykkelse", 250), ("udhaeng_gavl", 0)):
            if k not in el and std is None:
                errors.append(f"{path}.{k} mangler")
            el[k] = _num(el.get(k, std if std is not None else 0), f"{path}.{k}", errors)
        if el.get("form") in ("sadeltag", "valmtag") and el.get("rygning") not in ("x", "y"):
            errors.append(f"{path}.rygning skal være x eller y (rygningens retning)")
        if el.get("form") == "pulttag" and el.get("hoej_side") not in ("x+", "x-", "y+", "y-"):
            errors.append(f"{path}.hoej_side skal være x+|x-|y+|y- (den høje side)")
        if el.get("form") != "fladt" and not 0 < el["haeldning"] < 80:
            errors.append(f"{path}.haeldning skal være mellem 0 og 80 grader")
        if "type" in el:
            _type(d, el, path, errors, ("tag", "daek"))
        if el.get("spaer") is not None:
            sp = el["spaer"]
            if not isinstance(sp, dict):
                errors.append(f"{path}.spaer skal være en mapping (afstand, b, h, materiale, hanebaand)")
            else:
                unknown = set(sp) - {"afstand", "b", "h", "materiale", "hanebaand"}
                if unknown:
                    errors.append(f"{path}.spaer: ukendte felter {sorted(unknown)}")
                for k, std in (("afstand", 900), ("b", 50)):
                    sp[k] = _num(sp.get(k, std), f"{path}.spaer.{k}", errors, positive=True)
                for k in ("h", "hanebaand"):
                    if k in sp:
                        sp[k] = _num(sp[k], f"{path}.spaer.{k}", errors, positive=True)
                if "hanebaand" in sp and el.get("form") != "sadeltag":
                    errors.append(f"{path}.spaer.hanebaand kræver form: sadeltag")
                sp.setdefault("materiale", "træ")
    elif s == "trapper":
        el["start"] = _point(el.get("start"), 2, f"{path}.start", errors)
        el["retning"] = _num(el.get("retning", 0), f"{path}.retning", errors)
        for k in ("bredde", "stigninger", "grund"):
            el[k] = _num(el.get(k), f"{path}.{k}", errors, positive=True)
        if "stigning" in el:
            el["stigning"] = _num(el["stigning"], f"{path}.stigning", errors, positive=True)
        el["bund"] = _num(el.get("bund", 0), f"{path}.bund", errors)
    elif s == "soejler":
        el["punkt"] = _point(el.get("punkt"), 2, f"{path}.punkt", errors)
        _profile(el.get("profil"), path, errors)
        if "hoejde" in el:
            el["hoejde"] = _num(el["hoejde"], f"{path}.hoejde", errors, positive=True)
        el["bund"] = _num(el.get("bund", 0), f"{path}.bund", errors)
        el["rotation"] = _num(el.get("rotation", 0), f"{path}.rotation", errors)
    elif s == "bjaelker":
        el["fra"] = _point(el.get("fra"), 3, f"{path}.fra", errors)
        el["til"] = _point(el.get("til"), 3, f"{path}.til", errors)
        _profile(el.get("profil"), path, errors)
        el.setdefault("kant", "top")
        if el["kant"] not in ("top", "midt", "bund"):
            errors.append(f"{path}.kant skal være top|midt|bund")
        el["rotation"] = _num(el.get("rotation", 0), f"{path}.rotation", errors)
    elif s == "rum":
        if "punkt" in el:
            el["punkt"] = _point(el["punkt"], 2, f"{path}.punkt", errors)
        elif "omrids" in el:
            el["omrids"] = _points(el["omrids"], 2, f"{path}.omrids", errors, min_count=3)
        else:
            errors.append(f"{path}: angiv punkt (inde i rummet) eller omrids")
        if "hoejde" in el:
            el["hoejde"] = _num(el["hoejde"], f"{path}.hoejde", errors, positive=True)
        el["bund"] = _num(el.get("bund", 0), f"{path}.bund", errors)
        el["afgraensning"] = [_points(l, 2, f"{path}.afgraensning[{i}]", errors) for i, l in
                              enumerate(el.get("afgraensning") or [])]
    elif s == "systemer":
        if el.get("art") not in SYSTEM_KINDS:
            errors.append(f"{path}.art skal være en af {sorted(SYSTEM_KINDS)}")
        if "farve" in el:
            f = el["farve"]
            if not (isinstance(f, list) and len(f) == 3 and all(isinstance(v, (int, float)) and 0 <= v <= 255 for v in f)):
                errors.append(f"{path}.farve skal være [r, g, b] med værdier 0–255")
    elif s == "installationer":
        if not el.get("art") and not el.get("klasse"):
            errors.append(f"{path}: angiv art (se spec.md) eller klasse (IFC-klasse)")
        el["punkt"] = _point(el.get("punkt"), 3, f"{path}.punkt", errors)
        g = el.get("geometri")
        if not (isinstance(g, dict) and (("kasse" in g and len(g["kasse"]) == 3) or
                                         ("cylinder" in g and len(g["cylinder"]) == 2))):
            errors.append(f"{path}.geometri skal være {{kasse: [b, d, h]}} eller {{cylinder: [diameter, h]}}")
        el["rotation"] = _num(el.get("rotation", 0), f"{path}.rotation", errors)
    elif s == "roer":
        el["punkter"] = _points(el.get("punkter"), 3, f"{path}.punkter", errors)
        el["diameter"] = _num(el.get("diameter"), f"{path}.diameter", errors, positive=True)
        el.setdefault("art", "roer")
        if el["art"] not in ("roer", "kanal", "kabel"):
            errors.append(f"{path}.art skal være roer|kanal|kabel")
    elif s == "generisk":
        if "mesh" in el:
            ms = el["mesh"]
            if not (isinstance(ms, dict) and ms.get("punkter") and ms.get("flader")):
                errors.append(f"{path}.mesh skal have punkter og flader")
            else:
                ms["punkter"] = _points(ms["punkter"], 3, f"{path}.mesh.punkter", errors, min_count=4)
        else:
            el["profil"] = _points(el.get("profil"), 2, f"{path}.profil", errors, min_count=3)
            el["origo"] = _point(el.get("origo", [0, 0, el.get("bund", 0)]), 3, f"{path}.origo", errors)
            el["x_akse"] = _point(el.get("x_akse", [1, 0, 0]), 3, f"{path}.x_akse", errors)
            el["z_akse"] = _point(el.get("z_akse", [0, 0, 1]), 3, f"{path}.z_akse", errors)
            el["dybde"] = _num(el.get("dybde", el.get("hoejde")), f"{path}.dybde (eller hoejde)", errors, positive=True)


def _expand_walls(d, errors):
    """Polylines → wall segments with id <id>.<n> (a single segment keeps its id).
    yderside/inderside: closed loops use the winding direction; open walls use the building's centre
    (the middle of all wall points) as "inside"."""
    all_pts = [p for w in d["vaegge"] for p in w.get("punkter") or []]
    centre = ((min(p[0] for p in all_pts) + max(p[0] for p in all_pts)) / 2,
              (min(p[1] for p in all_pts) + max(p[1] for p in all_pts)) / 2) if all_pts else (0.0, 0.0)
    segs = []
    for w in d["vaegge"]:
        ps = list(w["punkter"])
        if not ps:
            continue
        closed = w["lukket"]
        if closed and ps[0] == ps[-1]:
            ps = ps[:-1]
        n = len(ps) if closed else len(ps) - 1
        area = sum(ps[i][0] * ps[(i + 1) % len(ps)][1] - ps[(i + 1) % len(ps)][0] * ps[i][1]
                    for i in range(len(ps))) / 2 if closed else 0
        for i in range(n):
            p1, p2 = ps[i], ps[(i + 1) % len(ps)]
            if math.dist(p1, p2) < 1:
                errors.append(f"vaegge.{w['id']}: segment {i + 1} har længde 0")
                continue
            if closed:
                inside_left = area > 0  # counter-clockwise: the inside is to the left
            else:
                inside_left = (p2[0] - p1[0]) * (centre[1] - p1[1]) - (p2[1] - p1[1]) * (centre[0] - p1[0]) > 0
            align = w["justering"]
            if align == "yderside":
                align = "venstre" if inside_left else "hoejre"
            elif align == "inderside":
                align = "hoejre" if inside_left else "venstre"
            sid = w["id"] if n == 1 else f"{w['id']}.{i + 1}"
            seg = {k: v for k, v in w.items() if k not in ("punkter", "lukket", "justering")}
            seg.update(id=sid, p1=p1, p2=p2, justering=align, kaede=w["id"], nr=i)
            if closed or w["justering"] in ("yderside", "inderside"):
                seg["ude_venstre"] = not inside_left
            segs.append(seg)
    d["_vaegsegmenter"] = segs
