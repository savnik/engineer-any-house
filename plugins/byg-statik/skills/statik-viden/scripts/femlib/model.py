"""Modelspec (YAML) → PyNite-model → resultater.

Akser i spec og resultater: x, y vandret, z lodret op. PyNite regner med Y op, så koordinaterne afbildes
(x, y, z) → (X, Y, Z) = (x, z, -y) (højrehåndet). I en plan model (alle y = 0) ligger rammen i PyNites
X-Y-plan, og bøjning i planet er PyNites Mz om tværsnittets stærke akse.
"""
import hashlib
import json
import math
import pathlib
import sys

import yaml

HER = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HER))
import statik  # noqa: E402  (profiltabeller og materialer deles med overslagsværktøjet)

N_PKT = 41  # punkter pr. element i resultatkurver

# E og G i MPa, rho i kN/m3. Kilder: E fra statik.MATERIALER; G for træ = E0,mean/16 (EN 338 tabel 1 / EN 14080
# tabel 5), stål G = 81 000 MPa (EN 1993-1-1 3.2.6), beton Ecm (EN 1992-1-1 tabel 3.1) og G = E/(2·1,2).
# rho = middeldensitet (EN 338 / EN 14080) · g, stål 78,5 og armeret beton 25 kN/m3 (EN 1991-1-1 tabel A).
MATERIALER = {
    "C18": {"E": 9000, "G": 9000 / 16, "rho": 3.8},
    "C24": {"E": 11000, "G": 11000 / 16, "rho": 4.2},
    "GL24h": {"E": 11500, "G": 11500 / 16, "rho": 4.2},
    "GL30c": {"E": 13000, "G": 13000 / 16, "rho": 4.3},
    "GL32h": {"E": 14200, "G": 14200 / 16, "rho": 4.9},
    "S235": {"E": 210000, "G": 81000, "rho": 78.5},
    "S355": {"E": 210000, "G": 81000, "rho": 78.5},
    "C20/25": {"E": 30000, "G": 30000 / 2.4, "rho": 25.0},
    "C25/30": {"E": 31000, "G": 31000 / 2.4, "rho": 25.0},
    "C30/37": {"E": 33000, "G": 33000 / 2.4, "rho": 25.0},
}
for _n, _m in MATERIALER.items():  # E skal være den samme som i overslagsværktøjet
    if _n in statik.MATERIALER:
        assert statik.MATERIALER[_n]["E"] == _m["E"], _n

STOETTE = {  # type → frihedsgrader, der holdes (x, y, z translation; rx, ry, rz rotation)
    "indspaendt": ("x", "y", "z", "rx", "ry", "rz"),
    "charnier": ("x", "y", "z"),
    "rulle": ("z",),          # kun lodret – vandret fri
    "rulle-x": ("y", "z"),    # fri i x
    "rulle-y": ("x", "z"),    # fri i y
}
TYPER = ("brud", "anvendelse")


class SpecFejl(Exception):
    pass


# ---------- tværsnit ----------
def tvaersnit(navn: str, egne: dict) -> dict:
    """A [mm2], I_staerk, I_svag og J [mm4] for profilnavn (IPE/HEA/HEB), 'rekt BxH' eller et eget tværsnit."""
    if navn in egne:
        t = egne[navn]
        mangler = [k for k in ("A", "I_staerk", "I_svag", "J") if k not in t]
        if mangler:
            raise SpecFejl(f"tværsnit '{navn}' mangler {', '.join(mangler)} (mm2/mm4)")
        return {k: float(t[k]) for k in ("A", "I_staerk", "I_svag", "J")} | {"h": float(t.get("h", 0))}
    n = navn.upper().replace(" ", "")
    if n.startswith("REKT"):
        try:
            b, h = (float(v.replace(",", ".")) for v in n[4:].split("X"))
        except ValueError:
            raise SpecFejl(f"tværsnit '{navn}': skriv 'rekt BxH' i mm, fx 'rekt 45x195'")
        a, c = min(b, h), max(b, h)
        J = c * a ** 3 * (1 / 3 - 0.21 * a / c * (1 - a ** 4 / (12 * c ** 4)))  # Roark, rektangel
        return {"A": b * h, "I_staerk": b * h ** 3 / 12, "I_svag": h * b ** 3 / 12, "J": J, "h": h}
    for serie, tab in statik.PROFILER.items():
        if n.startswith(serie) and n[len(serie):].isdigit() and int(n[len(serie):]) in tab:
            h, b, tw, tf, r = tab[int(n[len(serie):])]
            t = statik.tvaersnit_i(h, b, tw, tf, r)
            hw = h - 2 * tf
            I_svag = 2 * tf * b ** 3 / 12 + hw * tw ** 3 / 12
            J = (2 * b * tf ** 3 + hw * tw ** 3) / 3
            return {"A": t["A"], "I_staerk": t["Iy"], "I_svag": I_svag, "J": J, "h": h}
    kendte = ", ".join(f"{s}{k}" for s, t in statik.PROFILER.items() for k in t)
    raise SpecFejl(f"ukendt tværsnit '{navn}'. Brug 'rekt BxH' (mm), et af {kendte} eller et eget under 'tvaersnit:'")


# ---------- spec ----------
def saet(s: dict, udtryk: str) -> None:
    """Ændr ét input uden at røre filen: 'lasttilfaelde.Q.laster.0.linjelast=4.0' (liste-indeks fra 0)."""
    if "=" not in udtryk:
        raise SpecFejl(f"--saet '{udtryk}': skriv sti=værdi")
    sti, vaerdi = udtryk.split("=", 1)
    dele = sti.strip().split(".")
    o = s
    for d in dele[:-1]:
        try:
            o = o[int(d)] if isinstance(o, list) else o[d]
        except (KeyError, IndexError, ValueError):
            raise SpecFejl(f"--saet: '{sti}' findes ikke i spec'en")
    sidste = dele[-1]
    if isinstance(o, list):
        o[int(sidste)] = yaml.safe_load(vaerdi)
    elif isinstance(o, dict):
        o[sidste] = yaml.safe_load(vaerdi)
    else:
        raise SpecFejl(f"--saet: '{sti}' peger ikke på et felt")


def laes_spec(sti: pathlib.Path, aendringer: list | None = None) -> dict:
    tekst = sti.read_text(encoding="utf-8")
    try:
        s = yaml.safe_load(tekst) or {}
    except yaml.YAMLError as e:
        raise SpecFejl(f"YAML-fejl: {e}")
    for a in aendringer or []:
        saet(s, a)
    s["_aendringer"] = list(aendringer or [])
    s["_sha"] = hashlib.sha256(tekst.encode("utf-8")).hexdigest()[:12]
    s["_sti"] = str(sti)
    for k in ("knuder", "elementer", "understoetninger", "lasttilfaelde", "kombinationer"):
        if not s.get(k):
            raise SpecFejl(f"'{k}' mangler eller er tom (se: fem.py skabelon)")
    s.setdefault("navn", sti.stem)
    s.setdefault("materialer", {})
    s.setdefault("tvaersnit", {})
    for k, v in s["knuder"].items():
        if not (isinstance(v, (list, tuple)) and len(v) in (2, 3)):
            raise SpecFejl(f"knude {k}: skriv [x, z] (plan) eller [x, y, z] i m")
        s["knuder"][k] = [float(v[0]), 0.0, float(v[1])] if len(v) == 2 else [float(c) for c in v]
    s["_plan"] = all(abs(v[1]) < 1e-9 for v in s["knuder"].values())
    for n, e in s["elementer"].items():
        for k in ("fra", "til", "profil", "materiale"):
            if k not in e:
                raise SpecFejl(f"element {n}: '{k}' mangler")
        for k in ("fra", "til"):
            if e[k] not in s["knuder"]:
                raise SpecFejl(f"element {n}: knude '{e[k]}' findes ikke")
        if e["materiale"] not in s["materialer"] and e["materiale"] not in MATERIALER:
            raise SpecFejl(f"element {n}: ukendt materiale '{e['materiale']}' (kendte: {', '.join(MATERIALER)})")
        e["_t"] = tvaersnit(str(e["profil"]), s["tvaersnit"])
        a, b = (s["knuder"][e[k]] for k in ("fra", "til"))
        e["_L"] = math.dist(a, b)
        if e["_L"] < 1e-6:
            raise SpecFejl(f"element {n} har længden 0")
    for k, v in s["understoetninger"].items():
        if k not in s["knuder"]:
            raise SpecFejl(f"understøtning i ukendt knude '{k}'")
        if isinstance(v, str) and v not in STOETTE:
            raise SpecFejl(f"understøtning {k}: '{v}' – brug {', '.join(STOETTE)} eller en liste af x, y, z, rx, ry, rz")
    for kn, k in s["kombinationer"].items():
        if k.get("type") not in TYPER:
            raise SpecFejl(f"kombination {kn}: type skal være {' eller '.join(TYPER)}")
        for lt in (k.get("faktorer") or {}):
            if lt not in s["lasttilfaelde"]:
                raise SpecFejl(f"kombination {kn}: lasttilfælde '{lt}' findes ikke")
    for ltn, lt in s["lasttilfaelde"].items():
        for i, l in enumerate((lt or {}).get("laster") or []):
            hvor = f"lasttilfælde {ltn}, last nr. {i + 1}"
            if "element" in l and l["element"] not in s["elementer"]:
                raise SpecFejl(f"{hvor}: element '{l['element']}' findes ikke")
            if "knude" in l and l["knude"] not in s["knuder"]:
                raise SpecFejl(f"{hvor}: knude '{l['knude']}' findes ikke")
            if not any(k in l for k in ("linjelast", "punktlast", "moment")):
                raise SpecFejl(f"{hvor}: angiv linjelast, punktlast eller moment")
            if l.get("retning", "ned") not in ("ned", "x", "y", "z") and "moment" not in l:
                raise SpecFejl(f"{hvor}: retning skal være ned, x, y eller z")
    return s


def P(v):
    """Spec-koordinat → PyNite-koordinat."""
    x, y, z = v
    return x, z, -y


def retning(r: str, w: float) -> tuple[str, float]:
    """Global lastretning i spec → (PyNite-retning, fortegn-korrigeret værdi)."""
    return {"ned": ("FY", -w), "z": ("FY", w), "x": ("FX", w), "y": ("FZ", -w)}[r]


# ---------- byg og regn ----------
def byg(s: dict):
    from Pynite import FEModel3D
    m = FEModel3D()
    mats = MATERIALER | s["materialer"]
    for navn in {e["materiale"] for e in s["elementer"].values()}:
        mt = mats[navn]
        m.add_material(navn, float(mt["E"]) * 1e3, float(mt["G"]) * 1e3, 0.3, float(mt.get("rho", 0)))
    for n, e in s["elementer"].items():
        t = e["_t"]
        m.add_section(f"T_{n}", t["A"] * 1e-6, t["I_svag"] * 1e-12, t["I_staerk"] * 1e-12, t["J"] * 1e-12)
    for k, v in s["knuder"].items():
        m.add_node(k, *P(v))
    for n, e in s["elementer"].items():
        m.add_member(n, e["fra"], e["til"], e["materiale"], f"T_{n}", rotation=float(e.get("drej", 0)),
                     tension_only=e.get("kun_traek", False), comp_only=e.get("kun_tryk", False))
        led = e.get("led") or []
        if isinstance(led, str):
            led = [led]
        if led:
            ri, rj = "start" in led, "slut" in led
            m.def_releases(n, Ryi=ri, Rzi=ri, Ryj=rj, Rzj=rj)
    # understøtninger (spec-frihedsgrad → PyNite)
    pyn = {"x": "DX", "y": "DZ", "z": "DY", "rx": "RX", "ry": "RZ", "rz": "RY"}
    holdt = {k: set() for k in s["knuder"]}
    for k, v in s["understoetninger"].items():
        holdt[k] |= {pyn[d] for d in (STOETTE[v] if isinstance(v, str) else v)}
    if s["_plan"]:  # plan ramme: hold frihedsgraderne ud af planen i alle knuder
        for k in holdt:
            holdt[k] |= {"DZ", "RX", "RY"}
        # en knude, hvor alle tilsluttede elementender er leddede, har ingen stivhed mod rotation i planet
        for k in s["knuder"]:
            ender = [(e, "start" if e["fra"] == k else "slut") for e in s["elementer"].values() if k in (e["fra"], e["til"])]
            if ender and all(side in (e.get("led") or []) for e, side in ender):
                holdt[k].add("RZ")
    for k, h in holdt.items():
        if h:
            m.def_support(k, **{f"support_{d}": True for d in h})
    # laster
    for ltn, lt in s["lasttilfaelde"].items():
        lt = lt or {}
        if lt.get("egenvaegt"):
            m.add_member_self_weight("FY", -1.0, case=ltn)
        for l in lt.get("laster") or []:
            r = l.get("retning", "ned")
            if "element" in l and "linjelast" in l:
                w = l["linjelast"]
                w1, w2 = (w, w) if not isinstance(w, (list, tuple)) else w
                d, w1 = retning(r, float(w1))
                _, w2 = retning(r, float(w2))
                m.add_member_dist_load(l["element"], d, w1, w2, l.get("fra"), l.get("til"), case=ltn)
            elif "element" in l and "punktlast" in l:
                d, p = retning(r, float(l["punktlast"]))
                m.add_member_pt_load(l["element"], d, p, float(l.get("x", s["elementer"][l["element"]]["_L"] / 2)), case=ltn)
            elif "knude" in l and "punktlast" in l:
                d, p = retning(r, float(l["punktlast"]))
                m.add_node_load(l["knude"], d, p, case=ltn)
            elif "knude" in l and "moment" in l:
                akse = l.get("akse", "y")
                d, sgn = {"x": ("MX", 1), "y": ("MZ", -1), "z": ("MY", 1)}[akse]
                m.add_node_load(l["knude"], d, sgn * float(l["moment"]), case=ltn)
            else:
                raise SpecFejl(f"lasttilfælde {ltn}: kan ikke fortolke last {l}")
    for kn, k in s["kombinationer"].items():
        m.add_load_combo(kn, {lt: float(f) for lt, f in (k.get("faktorer") or {}).items()})
    return m


def analyser(s: dict):
    m = byg(s)
    try:
        if s.get("analyse") == "andenorden":
            m.analyze_PDelta(log=False)
        else:
            m.analyze(log=False, check_stability=True, check_statics=False)
    except Exception as e:  # PyNite melder ustabilitet som generelle fejl
        raise SpecFejl(f"analysen fejlede ({type(e).__name__}: {e}). Typisk årsag: modellen er ustabil – "
                       "tjek understøtninger, led og at alle elementer hænger sammen")
    return m


def _kurver(mem, kombi: str, plan: bool, udkragning: bool = False) -> dict:
    """Resultatkurver langs elementet (x i m). δ i forhold til korden, men absolut for udkragninger."""
    dfun = mem.deflection_array if udkragning else mem.rel_deflection_array
    x = [float(v) for v in mem.moment_array("Mz", N_PKT, kombi)[0]]
    k = {"x": x,
         "M": [-float(v) for v in mem.moment_array("Mz", N_PKT, kombi)[1]],  # PyNite: træk i underside er negativ
         "V": [float(v) for v in mem.shear_array("Fy", N_PKT, kombi)[1]],
         "N": [-float(v) for v in mem.axial_array(N_PKT, kombi)[1]],  # PyNite: tryk er positiv
         "d": [1000 * float(v) for v in dfun("dy", N_PKT, kombi)[1]]}
    if not plan:
        k["M_svag"] = [-float(v) for v in mem.moment_array("My", N_PKT, kombi)[1]]
        k["V_svag"] = [float(v) for v in mem.shear_array("Fz", N_PKT, kombi)[1]]
        k["d_svag"] = [1000 * float(v) for v in dfun("dz", N_PKT, kombi)[1]]
    return k


def ydre_last(s: dict, kombi: str) -> dict:
    """Sum af de påførte laster (globalt, kN) i en kombination – til ligevægtskontrol."""
    tot = {"x": 0.0, "y": 0.0, "z": 0.0}
    mats = MATERIALER | s["materialer"]
    for lt, f in (s["kombinationer"][kombi].get("faktorer") or {}).items():
        lt_d = s["lasttilfaelde"][lt] or {}
        if lt_d.get("egenvaegt"):
            for e in s["elementer"].values():
                tot["z"] -= f * float(mats[e["materiale"]].get("rho", 0)) * e["_t"]["A"] * 1e-6 * e["_L"]
        for l in lt_d.get("laster") or []:
            if "moment" in l:
                continue
            r = l.get("retning", "ned")
            akse, sgn = ("z", -1) if r == "ned" else (r, 1)
            if "linjelast" in l:
                w = l["linjelast"]
                w1, w2 = (w, w) if not isinstance(w, (list, tuple)) else w
                L = s["elementer"][l["element"]]["_L"]
                a, b = float(l.get("fra") or 0), float(l["til"]) if l.get("til") is not None else L
                tot[akse] += f * sgn * (float(w1) + float(w2)) / 2 * (b - a)
            else:
                tot[akse] += f * sgn * float(l["punktlast"])
    return tot


def resultater(s: dict, m, kommando: str) -> dict:
    from importlib.metadata import version
    res = {"kommando": kommando, "spec": s["_sti"], "spec_sha256_12": s["_sha"], "navn": s["navn"],
           "aendringer": s["_aendringer"], "pynite": version("PyNiteFEA"), "plan": s["_plan"], "analyse": s.get("analyse", "førsteorden"),
           "enheder": {"kraft": "kN", "moment": "kNm", "laengde": "m", "nedboejning": "mm"},
           "fortegn": "N > 0 træk. M > 0 giver træk i elementets lokale −y-side (vandret element tegnet fra venstre "
                      "mod højre: træk i undersiden). δ er nedbøjning i forhold til elementets korde (absolut for "
                      "elementer med udkragning: true).",
           "kombinationer": {}}
    for kn, k in s["kombinationer"].items():
        kr = {"type": k["type"], "faktorer": k.get("faktorer"), "reaktioner": {}, "elementer": {}}
        sum_r = {"x": 0.0, "y": 0.0, "z": 0.0}
        for knude in s["understoetninger"]:
            n = m.nodes[knude]
            r = {"Rx": n.RxnFX[kn], "Ry": -n.RxnFZ[kn], "Rz": n.RxnFY[kn],
                 "Mx": n.RxnMX[kn], "My": -n.RxnMZ[kn], "Mz": n.RxnMY[kn]}
            r = {a: round(float(v), 3) for a, v in r.items() if abs(v) > 1e-6}
            kr["reaktioner"][knude] = r
            for a in sum_r:
                sum_r[a] += r.get("R" + a, 0.0)
        last = ydre_last(s, kn)
        kr["ligevaegt"] = {a: {"reaktioner": round(sum_r[a], 3), "laster": round(last[a], 3),
                               "ok": abs(sum_r[a] + last[a]) <= 1e-3 * max(1.0, abs(last[a]))} for a in sum_r}
        for en, e in s["elementer"].items():
            kurv = _kurver(m.members[en], kn, s["_plan"], bool(e.get("udkragning")))
            dmax = max(kurv["d"], key=abs)
            iM = max(range(len(kurv["M"])), key=lambda i: abs(kurv["M"][i]))
            er = {"L": round(e["_L"], 3), "profil": e["profil"], "materiale": e["materiale"],
                  "N_max": round(max(kurv["N"]), 2), "N_min": round(min(kurv["N"]), 2),
                  "V_abs_max": round(max(abs(v) for v in kurv["V"]), 2),
                  "M_max": round(max(kurv["M"]), 2), "M_min": round(min(kurv["M"]), 2),
                  "x_ved_M_abs_max": round(kurv["x"][iM], 3),
                  "delta_mm": round(dmax, 2)}
            if not s["_plan"]:
                er["M_svag_abs_max"] = round(max(abs(v) for v in kurv["M_svag"]), 2)
                er["delta_svag_mm"] = round(max(kurv["d_svag"], key=abs), 2)
            if k["type"] == "anvendelse":
                Lref = e["_L"] * (2 if e.get("udkragning") else 1)
                er["L_over_delta"] = round(Lref * 1000 / abs(dmax)) if abs(dmax) > 1e-6 else None
                g = e.get("graense", k.get("graense"))
                if g and er["L_over_delta"]:
                    er["graense"] = f"L/{g}"
                    er["nedboejning_ok"] = er["L_over_delta"] >= g
            kr["elementer"][en] = er
        res["kombinationer"][kn] = kr
    return res


def kurver_alle(s: dict, m) -> dict:
    """Kurver pr. kombination og element plus knudeflytninger (mm) – til tegn og vis."""
    ud = {}
    for kn in s["kombinationer"]:
        el = {en: _kurver(m.members[en], kn, s["_plan"], bool(e.get("udkragning"))) for en, e in s["elementer"].items()}
        fl = {}
        for k in s["knuder"]:
            n = m.nodes[k]
            fl[k] = (1000 * n.DX[kn], -1000 * n.DZ[kn], 1000 * n.DY[kn])
        ud[kn] = {"elementer": el, "flytning": fl}
    ud["_lokal_y"] = {en: lokal_y(m.members[en]) for en in s["elementer"]}
    return ud


def lokal_y(mem) -> tuple:
    """Elementets lokale y-akse i spec-koordinater (retningen for δ og for momentkurvens fortegn)."""
    T = mem.T()
    X, Y, Z = (float(v) for v in T[1, 0:3])
    return X, -Z, Y


def gem_json(res: dict, sti: pathlib.Path) -> None:
    sti.write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")
