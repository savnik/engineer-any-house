"""Indlæsning, fletning og validering af modelspecifikationen (model.yaml).

Alle længder i mm, vinkler i grader. Koordinater er lokale bygningskoordinater (x, y i plan);
z er relativ til etagens gulv (etagens kote). Se references/spec.md for formatet.
"""
import copy
import math
import pathlib

import yaml

SEKTIONER = ("vaegge", "aabninger", "daek", "tage", "ovenlys", "trapper", "soejler", "bjaelker", "rum",
             "systemer", "installationer", "roer", "generisk")
FORSLAGSFELTER = ("basis", "basis_sha256", "nedrives", "slet")
IDLISTER = (*SEKTIONER, "etager", "fakta", "grupper")   # lister, hvor elementer flettes på id
GRUPPEFELTER = {"id", "navn", "under", "omfatter", "beskrivelse"}
FAELLES = {"id", "navn", "etage", "status", "kilde", "ref", "usikkerhed", "fakta", "note", "egenskaber",
           "klassifikation", "beskrivelse"}
FELTER = {
    "vaegge": {"type", "punkter", "lukket", "justering", "hoejde", "bund", "til_tag", "vend_lag"},
    "aabninger": {"vaeg", "type", "afstand", "brystning", "bredde", "hoejde", "slaar_mod", "haengsel", "placering"},
    "daek": {"type", "omrids", "top", "huller", "art", "tykkelse"},
    "tage": {"form", "omrids", "rygning", "haeldning", "tagfod", "udhaeng", "udhaeng_gavl", "tykkelse", "type",
             "hoej_side"},
    "ovenlys": {"tag", "type", "punkt", "flade", "bredde", "hoejde"},
    "trapper": {"start", "retning", "bredde", "stigninger", "stigning", "grund", "materiale", "bund"},
    "soejler": {"punkt", "profil", "hoejde", "bund", "rotation", "materiale"},
    "bjaelker": {"fra", "til", "profil", "materiale", "kant", "rotation"},
    "rum": {"punkt", "omrids", "hoejde", "bund", "til_tag", "anvendelse", "afgraensning"},
    "systemer": {"art", "farve"},
    "installationer": {"art", "klasse", "predefined", "punkt", "geometri", "rotation", "system", "producent",
                       "model", "materiale"},
    "roer": {"system", "punkter", "diameter", "godstykkelse", "materiale", "art"},
    "generisk": {"klasse", "predefined", "profil", "origo", "x_akse", "z_akse", "dybde", "mesh", "til_tag",
                 "materiale", "hoejde", "bund"},
}
TYPEFELTER = {"klasse", "navn", "lag", "ude", "baerende", "u", "bredde", "hoejde", "felter", "betjening",
              "egenskaber", "klassifikation", "beskrivelse", "ramme", "predefined", "brand"}
STATUS = {"eksisterende": "EXISTING", "ny": "NEW", "nedrives": "DEMOLISH", "midlertidig": "TEMPORARY"}
KILDER = {"D": "D – dokument/tegning", "M": "M – målt på stedet", "F": "F – foto", "B": "B – oplyst af bygherre",
          "K": "K – godkendt fagnotat", "A": "A – antagelse/skøn"}
JUSTERING = {"midt", "venstre", "hoejre", "yderside", "inderside"}
TYPEKLASSER = {"vaeg", "daek", "tag", "vindue", "doer"}
TAGFORMER = {"sadeltag", "valmtag", "pulttag", "fladt"}
PROFILFORMER = {"rekt": ("b", "h"), "rhs": ("b", "h", "t"), "i": ("h", "b", "tw", "tf"), "rund": ("d",),
                "roer": ("d", "t"), "l": ("h", "b", "t")}
SYSTEMARTER = {"varme": "HEATING", "brugsvand_koldt": "DOMESTICCOLDWATER", "brugsvand_varmt": "DOMESTICHOTWATER",
               "afloeb": "DRAINAGE", "regnvand": "RAINWATER", "ventilation": "VENTILATION", "el": "ELECTRICAL",
               "gas": "GAS", "andet": "USERDEFINED"}


class SpecFejl(Exception):
    def __init__(self, fejl):
        self.fejl = fejl
        super().__init__("\n".join(fejl))


def _laes(sti: pathlib.Path) -> dict:
    try:
        d = yaml.safe_load(sti.read_text(encoding="utf-8")) or {}
    except yaml.YAMLError as e:
        raise SpecFejl([f"{sti.name}: YAML-fejl: {e}"]) from None
    if not isinstance(d, dict):
        raise SpecFejl([f"{sti.name}: topniveauet skal være en mapping"])
    return d


def _flet_dict(a: dict, b: dict) -> dict:
    """Mapping oven på mapping, rekursivt: kun de nævnte nøgler ændres, null fjerner, lister erstattes."""
    ud = dict(a)
    for f, x in b.items():
        if x is None:
            ud.pop(f, None)
        elif isinstance(x, dict) and isinstance(a.get(f), dict):
            ud[f] = _flet_dict(a[f], x)
        else:
            ud[f] = copy.deepcopy(x)
    return ud


def _flet(basis: dict, over: dict) -> dict:
    """Projektspec/forslag oven på basismodel: elementer med samme id erstatter felterne, nye tilføjes.

    Et felt sat til null i forslaget fjernes fra elementet. Topsektioner, der er mappinger (typer, vvs, model …),
    flettes rekursivt: skriv kun de nøgler, der ændres. `slet:` fjerner elementer helt (modelrettelse);
    `nedrives:` beholder dem med status nedrives (renovering). `bim.py flet` bruger samme regler."""
    ud = copy.deepcopy(basis)
    for k, v in over.items():
        if k in FORSLAGSFELTER:
            continue
        if k in IDLISTER:
            liste = ud.setdefault(k, [])
            idx = {str(e.get("id")): i for i, e in enumerate(liste)}
            for e in v or []:
                i = idx.get(str(e.get("id")))
                ny = copy.deepcopy(e) if i is None else {**liste[i], **copy.deepcopy(e)}
                ny = {f: x for f, x in ny.items() if x is not None}
                if i is None:
                    idx[str(e.get("id"))] = len(liste)
                    liste.append(ny)
                else:
                    liste[i] = ny
        elif isinstance(v, dict) and isinstance(ud.get(k), dict):
            ud[k] = _flet_dict(ud[k], v)
        else:
            ud[k] = copy.deepcopy(v)
    alle = {str(e.get("id")): e for s in SEKTIONER for e in ud.get(s) or []}
    for eid in over.get("nedrives") or []:
        eid = str(eid)
        if eid in alle:
            alle[eid]["status"] = "nedrives"
        elif eid.split(".")[0] in alle:
            ud.setdefault("_fejl", []).append(
                f"nedrives: '{eid}' er et vægsegment – opdel vægløkken i basismodellen, så segmentet er sin egen væg")
        else:
            ud.setdefault("_fejl", []).append(f"nedrives: id '{eid}' findes ikke i basismodellen")
    slet = {str(x) for x in over.get("slet") or []}
    if slet:
        fundet = set()
        for s in IDLISTER:
            if ud.get(s):
                fundet |= {str(e.get("id")) for e in ud[s] if str(e.get("id")) in slet}
                ud[s] = [e for e in ud[s] if str(e.get("id")) not in slet]
        for eid in sorted(slet - fundet):
            ud.setdefault("_fejl", []).append(f"slet: id '{eid}' findes ikke i basismodellen")
    return ud


def indlaes(sti) -> dict:
    sti = pathlib.Path(sti).resolve()
    d = _laes(sti)
    kaede = [sti]
    while d.get("basis"):
        b = (kaede[-1].parent / d["basis"]).resolve()
        if b in kaede:
            raise SpecFejl([f"basis-løkke: {b}"])
        if not b.exists():
            raise SpecFejl([f"basis findes ikke: {b}"])
        kaede.append(b)
        bd = _laes(b)
        d = _flet(bd, d) | ({"basis": bd["basis"]} if bd.get("basis") else {})
        if not bd.get("basis"):
            d.pop("basis", None)
    d["_sti"] = str(sti)
    return normaliser(d)


def _tal(x, sti, fejl, positiv=False):
    if isinstance(x, bool) or not isinstance(x, (int, float)):
        fejl.append(f"{sti}: forventede et tal, fik {x!r}")
        return 0.0
    if positiv and x <= 0:
        fejl.append(f"{sti}: skal være > 0, fik {x}")
    return float(x)


def _pkt(p, n, sti, fejl):
    if not isinstance(p, (list, tuple)) or len(p) != n:
        fejl.append(f"{sti}: forventede et punkt med {n} koordinater, fik {p!r}")
        return tuple([0.0] * n)
    return tuple(_tal(v, sti, fejl) for v in p)


def _pkter(ps, n, sti, fejl, mindst=2):
    if not isinstance(ps, (list, tuple)) or len(ps) < mindst:
        fejl.append(f"{sti}: forventede mindst {mindst} punkter")
        return []
    return [_pkt(p, n, f"{sti}[{i}]", fejl) for i, p in enumerate(ps)]


def normaliser(d: dict) -> dict:
    fejl = list(d.pop("_fejl", []))
    m = d.setdefault("model", {})
    if not m.get("navn"):
        fejl.append("model.navn mangler")
    m.setdefault("schema", "IFC4")
    if m["schema"] not in ("IFC4", "IFC4X3"):
        fejl.append(f"model.schema skal være IFC4 eller IFC4X3, fik {m['schema']!r}")
    std = d.setdefault("standard", {})
    std.setdefault("kilde", "A")
    std.setdefault("status", "eksisterende")
    d.setdefault("materialer", {})
    d["typer"] = {str(k): v for k, v in (d.get("typer") or {}).items()}
    for tid, t in d["typer"].items():
        if not isinstance(t, dict):
            fejl.append(f"typer.{tid}: skal være en mapping")
            continue
        for k in set(t) - TYPEFELTER:
            fejl.append(f"typer.{tid}: ukendt felt '{k}'")
        if t.get("klasse") not in TYPEKLASSER:
            fejl.append(f"typer.{tid}.klasse skal være en af {sorted(TYPEKLASSER)}")
        if t.get("klasse") in ("vaeg", "daek", "tag"):
            lag = t.get("lag")
            if not lag:
                fejl.append(f"typer.{tid}: lag mangler (liste af [materiale, tykkelse])")
            else:
                t["lag"] = [(str(l[0]), _tal(l[1], f"typer.{tid}.lag[{i}]", fejl, positiv=True))
                            if isinstance(l, (list, tuple)) and len(l) == 2 else fejl.append(
                                f"typer.{tid}.lag[{i}]: skal være [materiale, tykkelse]") or ("?", 1.0)
                            for i, l in enumerate(lag)]
        if t.get("klasse") in ("vindue", "doer"):
            for k in ("bredde", "hoejde"):
                if k not in t:
                    fejl.append(f"typer.{tid}.{k} mangler")
                else:
                    t[k] = _tal(t[k], f"typer.{tid}.{k}", fejl, positiv=True)

    etager = d.get("etager") or []
    if not etager:
        fejl.append("etager mangler (mindst én)")
    for i, e in enumerate(etager):
        e["id"] = str(e.get("id", ""))
        if not e["id"]:
            fejl.append(f"etager[{i}].id mangler")
        e["kote"] = _tal(e.get("kote", 0), f"etager.{e['id']}.kote", fejl)
    etager.sort(key=lambda e: e["kote"])
    for i, e in enumerate(etager):
        if "hoejde" not in e:
            if i + 1 < len(etager):
                e["hoejde"] = etager[i + 1]["kote"] - e["kote"]
            else:
                e["hoejde"] = 2500.0
        e["hoejde"] = _tal(e["hoejde"], f"etager.{e['id']}.hoejde", fejl, positiv=True)
        e.setdefault("navn", e["id"])
        if "fri_hoejde" in e:
            e["fri_hoejde"] = _tal(e["fri_hoejde"], f"etager.{e['id']}.fri_hoejde", fejl, positiv=True)
    d["etager"] = etager
    eids = {e["id"] for e in etager}

    alle_id = {}
    for s in SEKTIONER:
        liste = d.get(s) or []
        if not isinstance(liste, list):
            fejl.append(f"{s}: skal være en liste")
            liste = []
        d[s] = liste
        for i, el in enumerate(liste):
            if not isinstance(el, dict):
                fejl.append(f"{s}[{i}]: skal være en mapping")
                continue
            el["id"] = str(el.get("id", ""))
            sti = f"{s}.{el['id'] or i}"
            if not el["id"]:
                fejl.append(f"{s}[{i}].id mangler")
            elif el["id"] in alle_id:
                fejl.append(f"{sti}: id findes allerede i {alle_id[el['id']]}")
            alle_id[el["id"]] = s
            for k in set(el) - FELTER[s] - FAELLES:
                fejl.append(f"{sti}: ukendt felt '{k}' (tilladt: {', '.join(sorted(FELTER[s]))})")
            if s not in ("systemer", "aabninger", "ovenlys"):  # openings and roof windows inherit the host's storey
                el["etage"] = str(el.get("etage", ""))
                if el["etage"] not in eids:
                    fejl.append(f"{sti}.etage '{el['etage']}' findes ikke (etager: {', '.join(sorted(eids))})")
            el.setdefault("status", std["status"])
            if el["status"] not in STATUS:
                fejl.append(f"{sti}.status skal være en af {sorted(STATUS)}")
            el.setdefault("kilde", std["kilde"])
            if str(el["kilde"])[:1] not in KILDER:
                fejl.append(f"{sti}.kilde skal starte med en af {''.join(KILDER)}")
            el.setdefault("ref", std.get("ref", ""))
            _tjek_element(s, el, sti, d, fejl)
    _udvid_vaegge(d, fejl)
    seg_ids = {w["id"] for w in d["_vaegsegmenter"]}
    for a in d["aabninger"]:
        if a.get("vaeg") is not None:
            a["vaeg"] = str(a["vaeg"])
            if a["vaeg"] not in seg_ids:
                kand = sorted(x for x in seg_ids if x.startswith(a["vaeg"] + "."))
                hint = f" – mente du {kand[0]} … {kand[-1]}?" if kand else ""
                fejl.append(f"aabninger.{a['id']}.vaeg '{a['vaeg']}' findes ikke{hint}")
    tag_ids = {t["id"] for t in d["tage"]}
    for o in d["ovenlys"]:
        o["tag"] = str(o.get("tag"))
        tag = next((t for t in d["tage"] if t["id"] == o["tag"]), None)
        if tag is None:
            fejl.append(f"ovenlys.{o['id']}.tag '{o['tag']}' findes ikke")
        else:
            o["etage"] = tag["etage"]
    for s in ("vaegge", "rum", "generisk"):
        for el in d[s]:
            if el.get("til_tag") is not None:
                el["til_tag"] = str(el["til_tag"])
                if el["til_tag"] not in tag_ids:
                    fejl.append(f"{s}.{el['id']}.til_tag '{el['til_tag']}' findes ikke")
    sys_ids = {x["id"] for x in d["systemer"]}
    for s in ("installationer", "roer"):
        for el in d[s]:
            if el.get("system") is not None and str(el["system"]) not in sys_ids:
                fejl.append(f"{s}.{el['id']}.system '{el['system']}' findes ikke")
    _tjek_grupper(d, fejl)
    from .ejendomskort import tjek_fakta
    fejl += tjek_fakta(d)
    if fejl:
        raise SpecFejl(fejl)
    return d


def _tjek_grupper(d, fejl):
    """grupper: [{id, navn, under, omfatter: [id-mønstre]}] – visningsgrupper (IfcGroup) ud over standardgrupperne."""
    from .byg import STANDARDGRUPPER
    g = d.get("grupper") or []
    if not isinstance(g, list):
        fejl.append("grupper: skal være en liste")
        g = []
    d["grupper"] = [x for x in g if isinstance(x, dict)]
    ids = set(STANDARDGRUPPER) | {str(x.get("id")) for x in d["grupper"]}
    for i, x in enumerate(d["grupper"]):
        x["id"] = str(x.get("id", ""))
        sti = f"grupper.{x['id'] or i}"
        if not x["id"]:
            fejl.append(f"grupper[{i}].id mangler")
        for k in set(x) - GRUPPEFELTER:
            fejl.append(f"{sti}: ukendt felt '{k}' (tilladt: {', '.join(sorted(GRUPPEFELTER))})")
        om = x.get("omfatter") or []
        if not isinstance(om, list) or not all(isinstance(m, str) for m in om):
            fejl.append(f"{sti}.omfatter skal være en liste af id'er/mønstre (fx '1-SP-*')")
        if x.get("under") is not None:
            x["under"] = str(x["under"])
            if x["under"] not in ids or x["under"] == x["id"]:
                fejl.append(f"{sti}.under '{x['under']}' er ikke en gruppe")


def _type(d, el, sti, fejl, klasser):
    t = el.get("type")
    if t is None:
        fejl.append(f"{sti}.type mangler")
        return None
    t = str(t)
    el["type"] = t
    if t == "hul" and "hul" in klasser:
        return None
    if t not in d["typer"]:
        fejl.append(f"{sti}.type '{t}' findes ikke under typer")
        return None
    if d["typer"][t].get("klasse") not in klasser:
        fejl.append(f"{sti}.type '{t}' har klasse {d['typer'][t].get('klasse')}, forventede {'/'.join(klasser)}")
    return d["typer"][t]


def _profil(p, sti, fejl):
    if not isinstance(p, dict) or p.get("form") not in PROFILFORMER:
        fejl.append(f"{sti}.profil skal have form: {'|'.join(PROFILFORMER)} og mål")
        return
    for k in PROFILFORMER[p["form"]]:
        if k not in p:
            fejl.append(f"{sti}.profil.{k} mangler (form {p['form']} kræver {', '.join(PROFILFORMER[p['form']])})")
        else:
            p[k] = _tal(p[k], f"{sti}.profil.{k}", fejl, positiv=True)


def _tjek_element(s, el, sti, d, fejl):
    if s == "vaegge":
        _type(d, el, sti, fejl, ("vaeg",))
        el["punkter"] = _pkter(el.get("punkter"), 2, f"{sti}.punkter", fejl)
        el.setdefault("lukket", False)
        el.setdefault("justering", "midt")
        if el["justering"] not in JUSTERING:
            fejl.append(f"{sti}.justering skal være en af {sorted(JUSTERING)}")
        if el["lukket"] and len(el["punkter"]) < 3:
            fejl.append(f"{sti}: lukket væg kræver mindst 3 punkter")
        for k in ("hoejde", "bund"):
            if k in el:
                el[k] = _tal(el[k], f"{sti}.{k}", fejl, positiv=(k == "hoejde"))
    elif s == "aabninger":
        t = _type(d, el, sti, fejl, ("vindue", "doer", "hul"))
        if "vaeg" not in el:
            fejl.append(f"{sti}.vaeg mangler")
        el["afstand"] = _tal(el.get("afstand", None), f"{sti}.afstand", fejl)
        for k in ("bredde", "hoejde"):
            if k in el:
                el[k] = _tal(el[k], f"{sti}.{k}", fejl, positiv=True)
            elif t:
                el[k] = t[k]
            else:
                fejl.append(f"{sti}.{k} mangler (påkrævet for type hul)")
        kl = t.get("klasse") if t else "hul"
        el["_klasse"] = kl
        el["brystning"] = _tal(el.get("brystning", 0 if kl == "doer" else None), f"{sti}.brystning", fejl)
        if el.get("slaar_mod", "venstre") not in ("venstre", "hoejre", "inde", "ude"):
            fejl.append(f"{sti}.slaar_mod skal være venstre|hoejre|inde|ude")
        if el.get("haengsel", "start") not in ("start", "slut"):
            fejl.append(f"{sti}.haengsel skal være start|slut")
        if el.get("placering", "midt") not in ("midt", "ude", "inde"):
            fejl.append(f"{sti}.placering skal være midt|ude|inde")
    elif s == "ovenlys":
        t = _type(d, el, sti, fejl, ("vindue",))
        if "tag" not in el:
            fejl.append(f"{sti}.tag mangler")
        el["punkt"] = _pkt(el.get("punkt"), 2, f"{sti}.punkt", fejl)
        for k in ("bredde", "hoejde"):
            if k in el:
                el[k] = _tal(el[k], f"{sti}.{k}", fejl, positiv=True)
            elif t:
                el[k] = t[k]
    elif s == "daek":
        if "type" in el:
            _type(d, el, sti, fejl, ("daek", "tag"))
        elif "tykkelse" not in el:
            fejl.append(f"{sti}: angiv type eller tykkelse")
        o = el.get("omrids")
        if isinstance(o, dict):
            if "fra_vaegge" not in o:
                fejl.append(f"{sti}.omrids: brug en punktliste eller {{fra_vaegge: <væg-id>, kant: inderside|yderside}}")
            o["fra_vaegge"] = str(o.get("fra_vaegge"))
            o.setdefault("kant", "inderside")
        else:
            el["omrids"] = _pkter(o, 2, f"{sti}.omrids", fejl, mindst=3)
        el["huller"] = [_pkter(h, 2, f"{sti}.huller[{i}]", fejl, mindst=3) for i, h in enumerate(el.get("huller") or [])]
        el["top"] = _tal(el.get("top", 0), f"{sti}.top", fejl)
        el.setdefault("art", "gulv")
        if el["art"] not in ("gulv", "bund", "tag", "loft"):
            fejl.append(f"{sti}.art skal være gulv|bund|loft|tag")
    elif s == "tage":
        if el.get("form") not in TAGFORMER:
            fejl.append(f"{sti}.form skal være en af {sorted(TAGFORMER)}")
        o = el.get("omrids")
        if not (isinstance(o, (list, tuple)) and len(o) == 4 and all(isinstance(v, (int, float)) for v in o)):
            fejl.append(f"{sti}.omrids skal være [x0, y0, x1, y1] (rektangel ved facadens yderside)")
        else:
            x0, y0, x1, y1 = map(float, o)
            el["omrids"] = (min(x0, x1), min(y0, y1), max(x0, x1), max(y0, y1))
        for k, std in (("haeldning", 45), ("tagfod", None), ("udhaeng", 0), ("tykkelse", 250), ("udhaeng_gavl", 0)):
            if k not in el and std is None:
                fejl.append(f"{sti}.{k} mangler")
            el[k] = _tal(el.get(k, std if std is not None else 0), f"{sti}.{k}", fejl)
        if el.get("form") in ("sadeltag", "valmtag") and el.get("rygning") not in ("x", "y"):
            fejl.append(f"{sti}.rygning skal være x eller y (rygningens retning)")
        if el.get("form") == "pulttag" and el.get("hoej_side") not in ("x+", "x-", "y+", "y-"):
            fejl.append(f"{sti}.hoej_side skal være x+|x-|y+|y- (den høje side)")
        if el.get("form") != "fladt" and not 0 < el["haeldning"] < 80:
            fejl.append(f"{sti}.haeldning skal være mellem 0 og 80 grader")
        if "type" in el:
            _type(d, el, sti, fejl, ("tag", "daek"))
    elif s == "trapper":
        el["start"] = _pkt(el.get("start"), 2, f"{sti}.start", fejl)
        el["retning"] = _tal(el.get("retning", 0), f"{sti}.retning", fejl)
        for k in ("bredde", "stigninger", "grund"):
            el[k] = _tal(el.get(k), f"{sti}.{k}", fejl, positiv=True)
        if "stigning" in el:
            el["stigning"] = _tal(el["stigning"], f"{sti}.stigning", fejl, positiv=True)
        el["bund"] = _tal(el.get("bund", 0), f"{sti}.bund", fejl)
    elif s == "soejler":
        el["punkt"] = _pkt(el.get("punkt"), 2, f"{sti}.punkt", fejl)
        _profil(el.get("profil"), sti, fejl)
        if "hoejde" in el:
            el["hoejde"] = _tal(el["hoejde"], f"{sti}.hoejde", fejl, positiv=True)
        el["bund"] = _tal(el.get("bund", 0), f"{sti}.bund", fejl)
        el["rotation"] = _tal(el.get("rotation", 0), f"{sti}.rotation", fejl)
    elif s == "bjaelker":
        el["fra"] = _pkt(el.get("fra"), 3, f"{sti}.fra", fejl)
        el["til"] = _pkt(el.get("til"), 3, f"{sti}.til", fejl)
        _profil(el.get("profil"), sti, fejl)
        el.setdefault("kant", "top")
        if el["kant"] not in ("top", "midt", "bund"):
            fejl.append(f"{sti}.kant skal være top|midt|bund")
        el["rotation"] = _tal(el.get("rotation", 0), f"{sti}.rotation", fejl)
    elif s == "rum":
        if "punkt" in el:
            el["punkt"] = _pkt(el["punkt"], 2, f"{sti}.punkt", fejl)
        elif "omrids" in el:
            el["omrids"] = _pkter(el["omrids"], 2, f"{sti}.omrids", fejl, mindst=3)
        else:
            fejl.append(f"{sti}: angiv punkt (inde i rummet) eller omrids")
        if "hoejde" in el:
            el["hoejde"] = _tal(el["hoejde"], f"{sti}.hoejde", fejl, positiv=True)
        el["bund"] = _tal(el.get("bund", 0), f"{sti}.bund", fejl)
        el["afgraensning"] = [_pkter(l, 2, f"{sti}.afgraensning[{i}]", fejl) for i, l in
                              enumerate(el.get("afgraensning") or [])]
    elif s == "systemer":
        if el.get("art") not in SYSTEMARTER:
            fejl.append(f"{sti}.art skal være en af {sorted(SYSTEMARTER)}")
        if "farve" in el:
            f = el["farve"]
            if not (isinstance(f, list) and len(f) == 3 and all(isinstance(v, (int, float)) and 0 <= v <= 255 for v in f)):
                fejl.append(f"{sti}.farve skal være [r, g, b] med værdier 0–255")
    elif s == "installationer":
        if not el.get("art") and not el.get("klasse"):
            fejl.append(f"{sti}: angiv art (se spec.md) eller klasse (IFC-klasse)")
        el["punkt"] = _pkt(el.get("punkt"), 3, f"{sti}.punkt", fejl)
        g = el.get("geometri")
        if not (isinstance(g, dict) and (("kasse" in g and len(g["kasse"]) == 3) or
                                         ("cylinder" in g and len(g["cylinder"]) == 2))):
            fejl.append(f"{sti}.geometri skal være {{kasse: [b, d, h]}} eller {{cylinder: [diameter, h]}}")
        el["rotation"] = _tal(el.get("rotation", 0), f"{sti}.rotation", fejl)
    elif s == "roer":
        el["punkter"] = _pkter(el.get("punkter"), 3, f"{sti}.punkter", fejl)
        el["diameter"] = _tal(el.get("diameter"), f"{sti}.diameter", fejl, positiv=True)
        el.setdefault("art", "roer")
        if el["art"] not in ("roer", "kanal"):
            fejl.append(f"{sti}.art skal være roer|kanal")
    elif s == "generisk":
        if "mesh" in el:
            ms = el["mesh"]
            if not (isinstance(ms, dict) and ms.get("punkter") and ms.get("flader")):
                fejl.append(f"{sti}.mesh skal have punkter og flader")
            else:
                ms["punkter"] = _pkter(ms["punkter"], 3, f"{sti}.mesh.punkter", fejl, mindst=4)
        else:
            el["profil"] = _pkter(el.get("profil"), 2, f"{sti}.profil", fejl, mindst=3)
            el["origo"] = _pkt(el.get("origo", [0, 0, el.get("bund", 0)]), 3, f"{sti}.origo", fejl)
            el["x_akse"] = _pkt(el.get("x_akse", [1, 0, 0]), 3, f"{sti}.x_akse", fejl)
            el["z_akse"] = _pkt(el.get("z_akse", [0, 0, 1]), 3, f"{sti}.z_akse", fejl)
            el["dybde"] = _tal(el.get("dybde", el.get("hoejde")), f"{sti}.dybde (eller hoejde)", fejl, positiv=True)


def _udvid_vaegge(d, fejl):
    """Polylinjer → vægsegmenter med id <id>.<n> (ét segment beholder sit id).
    yderside/inderside: lukkede løkker bruger omløbsretningen; åbne vægge bruger bygningens midtpunkt
    (midten af alle vægpunkter) som "inde"."""
    alle = [p for w in d["vaegge"] for p in w.get("punkter") or []]
    midt = ((min(p[0] for p in alle) + max(p[0] for p in alle)) / 2,
            (min(p[1] for p in alle) + max(p[1] for p in alle)) / 2) if alle else (0.0, 0.0)
    segs = []
    for w in d["vaegge"]:
        ps = list(w["punkter"])
        if not ps:
            continue
        lukket = w["lukket"]
        if lukket and ps[0] == ps[-1]:
            ps = ps[:-1]
        n = len(ps) if lukket else len(ps) - 1
        areal = sum(ps[i][0] * ps[(i + 1) % len(ps)][1] - ps[(i + 1) % len(ps)][0] * ps[i][1]
                    for i in range(len(ps))) / 2 if lukket else 0
        for i in range(n):
            p1, p2 = ps[i], ps[(i + 1) % len(ps)]
            if math.dist(p1, p2) < 1:
                fejl.append(f"vaegge.{w['id']}: segment {i + 1} har længde 0")
                continue
            if lukket:
                inde_venstre = areal > 0  # mod uret: indersiden til venstre
            else:
                inde_venstre = (p2[0] - p1[0]) * (midt[1] - p1[1]) - (p2[1] - p1[1]) * (midt[0] - p1[0]) > 0
            just = w["justering"]
            if just == "yderside":
                just = "venstre" if inde_venstre else "hoejre"
            elif just == "inderside":
                just = "hoejre" if inde_venstre else "venstre"
            sid = w["id"] if n == 1 else f"{w['id']}.{i + 1}"
            seg = {k: v for k, v in w.items() if k not in ("punkter", "lukket", "justering")}
            seg.update(id=sid, p1=p1, p2=p2, justering=just, kaede=w["id"], nr=i)
            if lukket or w["justering"] in ("yderside", "inderside"):
                seg["ude_venstre"] = not inde_venstre
            segs.append(seg)
    d["_vaegsegmenter"] = segs
