"""Model spec (YAML) → PyNite model → results.

Axes in spec and results: x, y horizontal, z vertical up. PyNite works with Y up, so the coordinates are mapped
(x, y, z) → (X, Y, Z) = (x, z, -y) (right-handed). In a plane model (all y = 0) the frame lies in PyNite's
X-Y plane, and in-plane bending is PyNite's Mz about the strong axis of the cross-section.
"""
import hashlib
import json
import math
import pathlib
import sys

import yaml

HERE = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HERE))
import statik  # noqa: E402  (section tables and materials are shared with the estimating tool)
from femlib import shells  # noqa: E402

N_PTS = 41  # points per member in result curves

# E and G in MPa, rho in kN/m3. Sources: E from statik.MATERIALS; G for timber = E0,mean/16 (EN 338 table 1 / EN 14080
# table 5), steel G = 81 000 MPa (EN 1993-1-1 3.2.6), concrete Ecm (EN 1992-1-1 table 3.1) and G = E/(2·1.2).
# rho = mean density (EN 338 / EN 14080) · g, steel 78.5 and reinforced concrete 25 kN/m3 (EN 1991-1-1 table A).
MATERIALS = {
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
    # masonry for shells: typical estimate values, E = K_E·f_k with K_E = 1000 (EN 1996-1-1, 3.7.2), ν = 0.2.
    # aerated concrete f_k ≈ 2.5 MPa, density approx. 535 kg/m3 + moisture; brick f_k ≈ 6 MPa, 1800 kg/m3. If f_k is known, give your own.
    "gasbeton": {"E": 2500, "G": 2500 / 2.4, "rho": 6.0},
    "tegl": {"E": 6000, "G": 6000 / 2.4, "rho": 18.0},
}
for _n, _m in MATERIALS.items():  # E must be the same as in the estimating tool
    if _n in statik.MATERIALS:
        assert statik.MATERIALS[_n]["E"] == _m["E"], _n

SUPPORTS = {  # type → degrees of freedom held (x, y, z translation; rx, ry, rz rotation)
    "indspaendt": ("x", "y", "z", "rx", "ry", "rz"),
    "charnier": ("x", "y", "z"),
    "rulle": ("z",),          # vertical only – free horizontally
    "rulle-x": ("y", "z"),    # free in x
    "rulle-y": ("x", "z"),    # free in y
}
TYPES = ("brud", "anvendelse")


class SpecError(Exception):
    pass


# ---------- cross-sections ----------
def cross_section(name: str, custom: dict) -> dict:
    """A [mm2], I_staerk, I_svag and J [mm4] for a section name (IPE/HEA/HEB), 'rekt BxH' or a custom cross-section."""
    if name in custom:
        t = custom[name]
        missing = [k for k in ("A", "I_staerk", "I_svag", "J") if k not in t]
        if missing:
            raise SpecError(f"tværsnit '{name}' mangler {', '.join(missing)} (mm2/mm4)")
        return {k: float(t[k]) for k in ("A", "I_staerk", "I_svag", "J")} | {"h": float(t.get("h", 0))}
    n = name.upper().replace(" ", "")
    if n.startswith("REKT"):
        try:
            b, h = (float(v.replace(",", ".")) for v in n[4:].split("X"))
        except ValueError:
            raise SpecError(f"tværsnit '{name}': skriv 'rekt BxH' i mm, fx 'rekt 45x195'")
        a, c = min(b, h), max(b, h)
        J = c * a ** 3 * (1 / 3 - 0.21 * a / c * (1 - a ** 4 / (12 * c ** 4)))  # Roark, rectangle
        return {"A": b * h, "I_staerk": b * h ** 3 / 12, "I_svag": h * b ** 3 / 12, "J": J, "h": h}
    for series, table in statik.PROFILES.items():
        if n.startswith(series) and n[len(series):].isdigit() and int(n[len(series):]) in table:
            h, b, tw, tf, r = table[int(n[len(series):])]
            t = statik.section_i(h, b, tw, tf, r)
            hw = h - 2 * tf
            I_svag = 2 * tf * b ** 3 / 12 + hw * tw ** 3 / 12
            J = (2 * b * tf ** 3 + hw * tw ** 3) / 3
            return {"A": t["A"], "I_staerk": t["Iy"], "I_svag": I_svag, "J": J, "h": h}
    known = ", ".join(f"{s}{k}" for s, t in statik.PROFILES.items() for k in t)
    raise SpecError(f"ukendt tværsnit '{name}'. Brug 'rekt BxH' (mm), et af {known} eller et eget under 'tvaersnit:'")


# ---------- spec ----------
def set_value(s: dict, expr: str) -> None:
    """Change one input without touching the file: 'lasttilfaelde.Q.laster.0.linjelast=4.0' (list index from 0)."""
    if "=" not in expr:
        raise SpecError(f"--set '{expr}': skriv sti=værdi")
    path, value = expr.split("=", 1)
    parts = path.strip().split(".")
    o = s
    for d in parts[:-1]:
        try:
            o = o[int(d)] if isinstance(o, list) else o[d]
        except (KeyError, IndexError, ValueError):
            raise SpecError(f"--set: '{path}' findes ikke i spec'en")
    last_key = parts[-1]
    if isinstance(o, list):
        o[int(last_key)] = yaml.safe_load(value)
    elif isinstance(o, dict):
        o[last_key] = yaml.safe_load(value)
    else:
        raise SpecError(f"--set: '{path}' peger ikke på et felt")


def read_spec(path: pathlib.Path, changes: list | None = None) -> dict:
    text = path.read_text(encoding="utf-8")
    try:
        s = yaml.safe_load(text) or {}
    except yaml.YAMLError as e:
        raise SpecError(f"YAML-fejl: {e}")
    for a in changes or []:
        set_value(s, a)
    s["_aendringer"] = list(changes or [])
    s["_sha"] = hashlib.sha256(text.encode("utf-8")).hexdigest()[:12]
    s["_sti"] = str(path)
    for k in ("knuder", "lasttilfaelde", "kombinationer"):
        if not s.get(k):
            raise SpecError(f"'{k}' mangler eller er tom (se: fem.py template)")
    if not s.get("elementer") and not s.get("flader"):
        raise SpecError("modellen skal have 'elementer' (stænger) og/eller 'flader' (vægge, dæk)")
    if not s.get("understoetninger") and not s.get("understoetninger_linje"):
        raise SpecError("'understoetninger' (knuder) og/eller 'understoetninger_linje' mangler")
    s.setdefault("elementer", {})
    s.setdefault("understoetninger", {})
    s.setdefault("navn", path.stem)
    s.setdefault("materialer", {})
    s.setdefault("tvaersnit", {})
    for k, v in s["knuder"].items():
        if not (isinstance(v, (list, tuple)) and len(v) in (2, 3)):
            raise SpecError(f"knude {k}: skriv [x, z] (plan) eller [x, y, z] i m")
        s["knuder"][k] = [float(v[0]), 0.0, float(v[1])] if len(v) == 2 else [float(c) for c in v]
    s["_plan"] = all(abs(v[1]) < 1e-9 for v in s["knuder"].values()) and not s.get("flader")
    for n, e in s["elementer"].items():
        for k in ("fra", "til", "profil", "materiale"):
            if k not in e:
                raise SpecError(f"element {n}: '{k}' mangler")
        for k in ("fra", "til"):
            if e[k] not in s["knuder"]:
                raise SpecError(f"element {n}: knude '{e[k]}' findes ikke")
        if e["materiale"] not in s["materialer"] and e["materiale"] not in MATERIALS:
            raise SpecError(f"element {n}: ukendt materiale '{e['materiale']}' (kendte: {', '.join(MATERIALS)})")
        e["_t"] = cross_section(str(e["profil"]), s["tvaersnit"])
        a, b = (s["knuder"][e[k]] for k in ("fra", "til"))
        e["_L"] = math.dist(a, b)
        if e["_L"] < 1e-6:
            raise SpecError(f"element {n} har længden 0")
    for k, v in s["understoetninger"].items():
        if k not in s["knuder"]:
            raise SpecError(f"understøtning i ukendt knude '{k}'")
        if isinstance(v, str) and v not in SUPPORTS:
            raise SpecError(f"understøtning {k}: '{v}' – brug {', '.join(SUPPORTS)} eller en liste af x, y, z, rx, ry, rz")
    for kn, k in s["kombinationer"].items():
        if k.get("type") not in TYPES:
            raise SpecError(f"kombination {kn}: type skal være {' eller '.join(TYPES)}")
        for lt in (k.get("faktorer") or {}):
            if lt not in s["lasttilfaelde"]:
                raise SpecError(f"kombination {kn}: lasttilfælde '{lt}' findes ikke")
    for ltn, lt in s["lasttilfaelde"].items():
        for i, l in enumerate((lt or {}).get("laster") or []):
            where = f"lasttilfælde {ltn}, last nr. {i + 1}"
            if "element" in l and l["element"] not in s["elementer"]:
                raise SpecError(f"{where}: element '{l['element']}' findes ikke")
            if "knude" in l and l["knude"] not in s["knuder"]:
                raise SpecError(f"{where}: knude '{l['knude']}' findes ikke")
            if "flade" in l:
                if l["flade"] not in (s.get("flader") or {}):
                    raise SpecError(f"{where}: flade '{l['flade']}' findes ikke")
                if "tryk" not in l:
                    raise SpecError(f"{where}: en fladelast angives som 'tryk' (kN/m2)")
                if l.get("retning", "ned") not in ("ned", "x", "y", "z", "normal"):
                    raise SpecError(f"{where}: retning skal være ned, x, y, z eller normal")
                continue
            if "linje" in l and not (isinstance(l["linje"], list) and len(l["linje"]) == 2
                                     and all(k in s["knuder"] for k in l["linje"]) and "linjelast" in l):
                raise SpecError(f"{where}: en linjelast langs en linje angives som linje: [knude, knude] og linjelast")
            if "linjelast" in l and "element" not in l and "linje" not in l:
                raise SpecError(f"{where}: en linjelast skal have 'element' eller 'linje'")
            if not any(k in l for k in ("linjelast", "punktlast", "moment")):
                raise SpecError(f"{where}: angiv linjelast, punktlast, moment eller (på en flade) tryk")
            if l.get("retning", "ned") not in ("ned", "x", "y", "z") and "moment" not in l:
                raise SpecError(f"{where}: retning skal være ned, x, y eller z")
    try:
        shells.read(s, MATERIALS | s["materialer"])
        shells.mesh(s)
    except shells.ShellError as e:
        raise SpecError(str(e))
    return s


def P(v):
    """Spec coordinate → PyNite coordinate."""
    x, y, z = v
    return x, z, -y


def direction(r: str, w: float) -> tuple[str, float]:
    """Global load direction in spec → (PyNite direction, sign-corrected value)."""
    return {"ned": ("FY", -w), "z": ("FY", w), "x": ("FX", w), "y": ("FZ", -w)}[r]


# ---------- build and calculate ----------
def build(s: dict):
    from Pynite import FEModel3D
    m = FEModel3D()
    mats = MATERIALS | s["materialer"]
    for name in {e["materiale"] for e in s["elementer"].values()} | {f["materiale"] for f in s["flader"].values()}:
        mt = mats[name]
        nu = shells.nu(mt)
        m.add_material(name, float(mt["E"]) * 1e3, float(mt["G"]) * 1e3, nu if 0 <= nu < 0.5 else 0.3,
                       float(mt.get("rho", 0)))
    for n, e in s["elementer"].items():
        t = e["_t"]
        m.add_section(f"T_{n}", t["A"] * 1e-6, t["I_svag"] * 1e-12, t["I_staerk"] * 1e-12, t["J"] * 1e-12)
    used = {e[k] for e in s["elementer"].values() for k in ("fra", "til")} | set(s["understoetninger"]) \
        | {k for _, _, kn, _ in s["_quads"] for k in kn}
    for k, v in shells.all_nodes(s).items():
        if k in used:
            m.add_node(k, *P(v))
    for qn, fn, kn, _ in s["_quads"]:
        f = s["flader"][fn]
        m.add_quad(qn, *kn, f["_t"], f["materiale"])
    for n, e in s["elementer"].items():
        m.add_member(n, e["fra"], e["til"], e["materiale"], f"T_{n}", rotation=float(e.get("drej", 0)),
                     tension_only=e.get("kun_traek", False), comp_only=e.get("kun_tryk", False))
        releases = e.get("led") or []
        if isinstance(releases, str):
            releases = [releases]
        if releases:
            ri, rj = "start" in releases, "slut" in releases
            m.def_releases(n, Ryi=ri, Rzi=ri, Ryj=rj, Rzj=rj)
    # supports (spec degree of freedom → PyNite)
    pyn = {"x": "DX", "y": "DZ", "z": "DY", "rx": "RX", "ry": "RZ", "rz": "RY"}
    held = {k: set() for k in m.nodes}
    for k, v in s["understoetninger"].items():
        held[k] |= {pyn[d] for d in (SUPPORTS[v] if isinstance(v, str) else v)}
    for ls in s["understoetninger_linje"]:
        v = ls.get("type", "charnier")
        for _, k in shells.nodes_on_line(s, s["knuder"][ls["fra"]], s["knuder"][ls["til"]]):
            if k in held:
                held[k] |= {pyn[d] for d in (SUPPORTS[v] if isinstance(v, str) else v)}
    if s["_plan"]:  # plane frame: hold the out-of-plane degrees of freedom in all nodes
        for k in held:
            held[k] |= {"DZ", "RX", "RY"}
        # a node where all connected member ends are hinged has no in-plane rotational stiffness
        for k in s["knuder"]:
            if k not in m.nodes:
                continue
            ends = [(e, "start" if e["fra"] == k else "slut") for e in s["elementer"].values() if k in (e["fra"], e["til"])]
            if ends and all(side in (e.get("led") or []) for e, side in ends):
                held[k].add("RZ")
    for k, h in held.items():
        if h:
            m.def_support(k, **{f"support_{d}": True for d in h})
    # loads
    for ltn, lt in s["lasttilfaelde"].items():
        lt = lt or {}
        if lt.get("egenvaegt") and s["elementer"]:
            m.add_member_self_weight("FY", -1.0, case=ltn)
        for k, F in shells.node_loads(s, ltn, mats).items():
            if k not in m.nodes:
                raise SpecError(f"lasttilfælde {ltn}: last i knude '{k}', som hverken ligger på en flade eller et element")
            for d, v in zip(("FX", "FY", "FZ"), (F[0], F[2], -F[1])):
                if abs(v) > 1e-12:
                    m.add_node_load(k, d, float(v), case=ltn)
        for l in lt.get("laster") or []:
            if "flade" in l or "linje" in l:
                continue
            r = l.get("retning", "ned")
            if "element" in l and "linjelast" in l:
                w = l["linjelast"]
                w1, w2 = (w, w) if not isinstance(w, (list, tuple)) else w
                d, w1 = direction(r, float(w1))
                _, w2 = direction(r, float(w2))
                m.add_member_dist_load(l["element"], d, w1, w2, l.get("fra"), l.get("til"), case=ltn)
            elif "element" in l and "punktlast" in l:
                d, p = direction(r, float(l["punktlast"]))
                m.add_member_pt_load(l["element"], d, p, float(l.get("x", s["elementer"][l["element"]]["_L"] / 2)), case=ltn)
            elif "knude" in l and l["knude"] not in m.nodes:
                raise SpecError(f"lasttilfælde {ltn}: knude '{l['knude']}' hverken ligger på en flade eller et element")
            elif "knude" in l and "punktlast" in l:
                d, p = direction(r, float(l["punktlast"]))
                m.add_node_load(l["knude"], d, p, case=ltn)
            elif "knude" in l and "moment" in l:
                axis = l.get("akse", "y")
                d, sgn = {"x": ("MX", 1), "y": ("MZ", -1), "z": ("MY", 1)}[axis]
                m.add_node_load(l["knude"], d, sgn * float(l["moment"]), case=ltn)
            else:
                raise SpecError(f"lasttilfælde {ltn}: kan ikke fortolke last {l}")
    for kn, k in s["kombinationer"].items():
        m.add_load_combo(kn, {lt: float(f) for lt, f in (k.get("faktorer") or {}).items()})
    return m


def analyze(s: dict):
    m = build(s)
    try:
        if s.get("analyse") == "andenorden":
            m.analyze_PDelta(log=False)
        else:
            m.analyze(log=False, check_stability=True, check_statics=False)
    except Exception as e:  # PyNite reports instability as generic errors
        raise SpecError(f"analysen fejlede ({type(e).__name__}: {e}). Typisk årsag: modellen er ustabil – "
                       "tjek understøtninger, led og at alle elementer hænger sammen")
    return m


def _curves(mem, combo: str, plan: bool, cantilever: bool = False) -> dict:
    """Result curves along the member (x in m). δ relative to the member's chord, but absolute for cantilevers (the span: _delta_span)."""
    dfun = mem.deflection_array if cantilever else mem.rel_deflection_array
    x = [float(v) for v in mem.moment_array("Mz", N_PTS, combo)[0]]
    k = {"x": x,
         "M": [-float(v) for v in mem.moment_array("Mz", N_PTS, combo)[1]],  # PyNite: tension in the bottom face is negative
         "V": [float(v) for v in mem.shear_array("Fy", N_PTS, combo)[1]],
         "N": [-float(v) for v in mem.axial_array(N_PTS, combo)[1]],  # PyNite: compression is positive
         "d": [1000 * float(v) for v in dfun("dy", N_PTS, combo)[1]]}
    if not plan:
        k["M_svag"] = [-float(v) for v in mem.moment_array("My", N_PTS, combo)[1]]
        k["V_svag"] = [float(v) for v in mem.shear_array("Fz", N_PTS, combo)[1]]
        k["d_svag"] = [1000 * float(v) for v in dfun("dz", N_PTS, combo)[1]]
    return k


def spans(s: dict) -> dict:
    """Spans: chains of collinear members split at nodes without support (e.g. at a point load).
    A node splits a span only if exactly two members meet there in line with the same rotation, and neither of them
    is a cantilever. Returns {member: {"elementer": [...] in order, "start": node, "slut": node, "L": m}}."""
    ends = {k: [] for k in s["knuder"]}
    for n, e in s["elementer"].items():
        ends[e["fra"]].append(n)
        ends[e["til"]].append(n)

    def unit_dir(n):
        e = s["elementer"][n]
        a, b = P(s["knuder"][e["fra"]]), P(s["knuder"][e["til"]])
        return [(b[i] - a[i]) / e["_L"] for i in range(3)]

    def splits(k):
        el = ends[k]
        if k in s["understoetninger"] or len(el) != 2:
            return False
        e1, e2 = (s["elementer"][n] for n in el)
        if e1.get("udkragning") or e2.get("udkragning") or float(e1.get("drej", 0)) != float(e2.get("drej", 0)):
            return False
        r1, r2 = unit_dir(el[0]), unit_dir(el[1])
        cross = [r1[1] * r2[2] - r1[2] * r2[1], r1[2] * r2[0] - r1[0] * r2[2], r1[0] * r2[1] - r1[1] * r2[0]]
        return max(abs(v) for v in cross) < 1e-6

    out, seen = {}, set()
    for n in s["elementer"]:
        if n in seen:
            continue
        # walk to one end of the chain, then collect the members in order
        k, cur = s["elementer"][n]["fra"], n
        while splits(k):
            cur = next(x for x in ends[k] if x != cur)
            e = s["elementer"][cur]
            k = e["til"] if e["fra"] == k else e["fra"]
        start, chain = k, []
        while True:
            chain.append(cur)
            e = s["elementer"][cur]
            k = e["til"] if e["fra"] == k else e["fra"]
            if not splits(k):
                break
            cur = next(x for x in ends[k] if x != cur)
        info = {"elementer": chain, "start": start, "slut": k, "L": sum(s["elementer"][x]["_L"] for x in chain)}
        for x in chain:
            out[x] = info
            seen.add(x)
    return out


def _delta_span(s: dict, m, combo: str, info: dict, axis: str = "dy") -> dict:
    """δ (mm) along each member of a split span, relative to the line between the span's end nodes."""
    import numpy as np
    row = 1 if axis == "dy" else 2
    ref = np.array(m.members[info["elementer"][0]].T()[row, 0:3], dtype=float)
    a0 = np.array(P(s["knuder"][info["start"]]), dtype=float)
    a1 = np.array(P(s["knuder"][info["slut"]]), dtype=float)
    axis_v = (a1 - a0) / np.linalg.norm(a1 - a0)

    def u(k):
        n = m.nodes[k]
        return float(np.dot([n.DX[combo], n.DY[combo], n.DZ[combo]], ref))
    u0, u1 = u(info["start"]), u(info["slut"])
    out = {}
    for en in info["elementer"]:
        mem, e = m.members[en], s["elementer"][en]
        sign = float(np.dot(np.array(mem.T()[row, 0:3], dtype=float), ref))
        x, d = mem.deflection_array(axis, N_PTS, combo)
        p_start = float(np.dot(np.array(P(s["knuder"][e["fra"]])) - a0, axis_v))
        p_end = float(np.dot(np.array(P(s["knuder"][e["til"]])) - a0, axis_v))
        out[en] = [1000 * (sign * float(dv) - (u0 + (u1 - u0) * (p_start + (p_end - p_start) * float(xv) / e["_L"]) / info["L"]))
                  for xv, dv in zip(x, d)]
    return out


def external_load(s: dict, combo: str) -> dict:
    """Sum of the applied loads (global, kN) in a combination – for the equilibrium check."""
    tot = {"x": 0.0, "y": 0.0, "z": 0.0}
    mats = MATERIALS | s["materialer"]
    for lt, f in (s["kombinationer"][combo].get("faktorer") or {}).items():
        lt_d = s["lasttilfaelde"][lt] or {}
        if lt_d.get("egenvaegt"):
            for e in s["elementer"].values():
                tot["z"] -= f * float(mats[e["materiale"]].get("rho", 0)) * e["_t"]["A"] * 1e-6 * e["_L"]
        for F in shells.node_loads(s, lt, mats).values():
            for i, a in enumerate("xyz"):
                tot[a] += f * float(F[i])
        for l in lt_d.get("laster") or []:
            if "moment" in l or "flade" in l or "linje" in l:
                continue
            r = l.get("retning", "ned")
            axis, sgn = ("z", -1) if r == "ned" else (r, 1)
            if "linjelast" in l:
                w = l["linjelast"]
                w1, w2 = (w, w) if not isinstance(w, (list, tuple)) else w
                L = s["elementer"][l["element"]]["_L"]
                a, b = float(l.get("fra") or 0), float(l["til"]) if l.get("til") is not None else L
                tot[axis] += f * sgn * (float(w1) + float(w2)) / 2 * (b - a)
            else:
                tot[axis] += f * sgn * float(l["punktlast"])
    return tot


def results(s: dict, m, command: str) -> dict:
    from importlib.metadata import version
    res = {"kommando": command, "spec": s["_sti"], "spec_sha256_12": s["_sha"], "navn": s["navn"],
           "aendringer": s["_aendringer"], "pynite": version("PyNiteFEA"), "plan": s["_plan"], "analyse": s.get("analyse", "førsteorden"),
           "enheder": {"kraft": "kN", "moment": "kNm", "laengde": "m", "nedboejning": "mm"},
           "fortegn": "N > 0 træk. M > 0 giver træk i elementets lokale −y-side (vandret element tegnet fra venstre "
                      "mod højre: træk i undersiden). δ er nedbøjning i forhold til spændets korde – linjen mellem "
                      "spændets endeknuder; et spænd kan bestå af flere elementer på linje (absolut for elementer med "
                      "udkragning: true). L i L/δ er spændets længde.",
           "kombinationer": {}}
    sp = spans(s)
    for kn, k in s["kombinationer"].items():
        kr = {"type": k["type"], "faktorer": k.get("faktorer"), "reaktioner": {}, "elementer": {}}
        sum_r = {"x": 0.0, "y": 0.0, "z": 0.0}
        def reactions_at(node):
            n = m.nodes[node]
            return {"Rx": n.RxnFX[kn], "Ry": -n.RxnFZ[kn], "Rz": n.RxnFY[kn],
                    "Mx": n.RxnMX[kn], "My": -n.RxnMZ[kn], "Mz": n.RxnMY[kn]}
        counted = set()
        groups = [(node, [node]) for node in s["understoetninger"]]
        for ls in s["understoetninger_linje"]:
            groups.append((f"linje {ls['fra']}–{ls['til']}", [k for _, k in shells.nodes_on_line(
                s, s["knuder"][ls["fra"]], s["knuder"][ls["til"]]) if k in m.nodes]))
        for group_name, node_list in groups:
            r = {}
            for node in node_list:
                if node in counted:
                    continue
                counted.add(node)
                for a, v in reactions_at(node).items():
                    r[a] = r.get(a, 0.0) + float(v)
            for a in sum_r:
                sum_r[a] += r.get("R" + a, 0.0)
            r = {a: round(v, 3) for a, v in r.items() if abs(v) > 1e-6 and not (a[0] == "M" and len(node_list) > 1)}
            kr["reaktioner"][group_name] = r
        load = external_load(s, kn)
        tol = 1e-3 * max(1.0, *(abs(v) for v in load.values()))  # numerical noise scales with the largest load
        kr["ligevaegt"] = {a: {"reaktioner": round(sum_r[a], 3), "laster": round(load[a], 3),
                               "ok": abs(sum_r[a] + load[a]) <= tol} for a in sum_r}
        for en, e in s["elementer"].items():
            curve = _curves(m.members[en], kn, s["_plan"], bool(e.get("udkragning")))
            info = sp[en]
            split = len(info["elementer"]) > 1
            if split:
                curve["d"] = _delta_span(s, m, kn, info)[en]
                if not s["_plan"]:
                    curve["d_svag"] = _delta_span(s, m, kn, info, "dz")[en]
            dmax = max(curve["d"], key=abs)
            iM = max(range(len(curve["M"])), key=lambda i: abs(curve["M"][i]))
            member_res = {"L": round(e["_L"], 3), "profil": e["profil"], "materiale": e["materiale"],
                  "N_max": round(max(curve["N"]), 2), "N_min": round(min(curve["N"]), 2),
                  "V_abs_max": round(max(abs(v) for v in curve["V"]), 2),
                  "M_max": round(max(curve["M"]), 2), "M_min": round(min(curve["M"]), 2),
                  "x_ved_M_abs_max": round(curve["x"][iM], 3),
                  "delta_mm": round(dmax, 2)}
            if split:
                member_res["spaend"] = info["elementer"]
                member_res["L_spaend"] = round(info["L"], 3)
            if not s["_plan"]:
                member_res["M_svag_abs_max"] = round(max(abs(v) for v in curve["M_svag"]), 2)
                member_res["delta_svag_mm"] = round(max(curve["d_svag"], key=abs), 2)
            if k["type"] == "anvendelse":
                Lref = info["L"] if split else e["_L"] * (2 if e.get("udkragning") else 1)
                member_res["L_over_delta"] = round(Lref * 1000 / abs(dmax)) if abs(dmax) > 1e-6 else None
                g = e.get("graense", k.get("graense"))
                if g and member_res["L_over_delta"]:
                    member_res["graense"] = f"L/{g}"
                    member_res["nedboejning_ok"] = member_res["L_over_delta"] >= g
            kr["elementer"][en] = member_res
        if s["flader"]:
            kr.update(shells.summary(s, shells.fields(s, m, kn)))
        res["kombinationer"][kn] = kr
    return res


def all_curves(s: dict, m) -> dict:
    """Curves per combination and member plus node displacements (mm) – for draw and view.
    The curve "d" is relative to the member's own chord (for the drawing); "delta" is the largest δ relative to the span."""
    out = {}
    sp = spans(s)
    for kn in s["kombinationer"]:
        el = {en: _curves(m.members[en], kn, s["_plan"], bool(e.get("udkragning"))) for en, e in s["elementer"].items()}
        delta = {en: max(c["d"], key=abs) for en, c in el.items()}
        for en, info in sp.items():
            if len(info["elementer"]) > 1:
                el[en]["d_spaend"] = _delta_span(s, m, kn, info)[en]
                delta[en] = max(el[en]["d_spaend"], key=abs)
        fl = {}
        for k in s["knuder"]:
            if k not in m.nodes:
                continue
            n = m.nodes[k]
            fl[k] = (1000 * n.DX[kn], -1000 * n.DZ[kn], 1000 * n.DY[kn])
        out[kn] = {"elementer": el, "flytning": fl, "delta": delta}
        if s["flader"]:
            out[kn]["flader"] = shells.fields(s, m, kn)
    out["_lokal_y"] = {en: local_y(m.members[en]) for en in s["elementer"]}
    return out


def local_y(mem) -> tuple:
    """The member's local y axis in spec coordinates (the direction of δ and of the moment curve's sign)."""
    T = mem.T()
    X, Y, Z = (float(v) for v in T[1, 0:3])
    return X, -Z, Y


def save_json(res: dict, path: pathlib.Path) -> None:
    path.write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")
