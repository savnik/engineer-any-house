"""Shells (walls, slabs, roof surfaces) as shell elements: spec → mesh → PyNite quads → results.

A shell is a rectangle with four corner nodes [A, B, C, D] in order around it. The shell's local axes:
u along A→B, v along A→D, normal n = u × v. Openings are given in (u, v) from A. The mesh is made so that nodes are shared
with other shells, spec nodes and lines lying on the shell; beams on a shell are connected at all the
nodes lying on them (PyNite's physical members split themselves).

Loads on shells are converted to node loads here (p·A/4 per quad corner), so the direction is set by the spec and
not by the quad elements' local axes.
"""
import math

import numpy as np

TOL = 1e-6
STD_MESH = 0.25  # m


class ShellError(Exception):
    pass


def _v(a):
    return np.array(a, dtype=float)


# ---------- spec ----------
def read(s: dict, materials: dict) -> None:
    """Validate shells, line supports and surface loads; add geometry (_A, _u, _v, _n, _Lu, _Lv, _t)."""
    s.setdefault("flader", {})
    s.setdefault("understoetninger_linje", [])
    s.setdefault("udtraek", {})
    for fn, f in s["flader"].items():
        h = f.get("hjoerner")
        if not (isinstance(h, list) and len(h) == 4 and all(k in s["knuder"] for k in h)):
            raise ShellError(f"flade {fn}: 'hjoerner' skal være fire knuder [A, B, C, D] i rækkefølge rundt")
        if "tykkelse" not in f or "materiale" not in f:
            raise ShellError(f"flade {fn}: angiv 'tykkelse' (mm) og 'materiale'")
        A, B, C, D = (_v(s["knuder"][k]) for k in h)
        u, v = B - A, D - A
        Lu, Lv = float(np.linalg.norm(u)), float(np.linalg.norm(v))
        if min(Lu, Lv) < 1e-3:
            raise ShellError(f"flade {fn}: to hjørner falder sammen")
        if abs(np.dot(u, v)) > 1e-4 * Lu * Lv or np.linalg.norm(A + u + v - C) > 1e-4 * max(Lu, Lv):
            raise ShellError(f"flade {fn}: hjørnerne danner ikke et rektangel (A→B ⟂ A→D og C = B + D − A)")
        mt = materials.get(f["materiale"])
        if mt is None:
            raise ShellError(f"flade {fn}: ukendt materiale '{f['materiale']}'")
        if not 0 <= nu(mt) < 0.5:
            raise ShellError(f"flade {fn}: materialet '{f['materiale']}' er ikke isotropt (ν = E/2G − 1 = {nu(mt):.2f}). "
                            "Træ kan ikke regnes som skal her – angiv et eget materiale med E, nu og rho")
        f["_A"], f["_u"], f["_v"] = A, u / Lu, v / Lv
        f["_n"] = np.cross(f["_u"], f["_v"])
        f["_Lu"], f["_Lv"] = Lu, Lv
        f["_t"] = float(f["tykkelse"]) / 1000
        for i, a in enumerate(f.get("aabninger") or []):
            if not all(k in a for k in ("x", "y", "b", "h")):
                raise ShellError(f"flade {fn}, åbning {i + 1}: angiv x, y, b, h (m, fra hjørne A langs A→B og A→D)")
            if a["x"] < -TOL or a["y"] < -TOL or a["x"] + a["b"] > Lu + TOL or a["y"] + a["h"] > Lv + TOL:
                raise ShellError(f"flade {fn}, åbning {i + 1}: ligger uden for fladen ({Lu:.2f} × {Lv:.2f} m)")
    for i, ls in enumerate(s["understoetninger_linje"]):
        if ls.get("fra") not in s["knuder"] or ls.get("til") not in s["knuder"]:
            raise ShellError(f"understoetninger_linje nr. {i + 1}: 'fra' og 'til' skal være knuder")
    for un, u in s["udtraek"].items():
        if u.get("flade") not in s["flader"]:
            raise ShellError(f"udtræk {un}: flade '{u.get('flade')}' findes ikke")


def nu(mt: dict) -> float:
    if "nu" in mt:
        return float(mt["nu"])
    return float(mt["E"]) / (2 * float(mt["G"])) - 1


# ---------- geometry ----------
def _local(f, p):
    d = _v(p) - f["_A"]
    return float(np.dot(d, f["_u"])), float(np.dot(d, f["_v"])), float(np.dot(d, f["_n"]))


def _on_shell(f, p):
    """(u, v) if the point lies in the shell's plane and inside the rectangle, otherwise None."""
    a, b, c = _local(f, p)
    if abs(c) < 1e-5 and -1e-5 <= a <= f["_Lu"] + 1e-5 and -1e-5 <= b <= f["_Lv"] + 1e-5:
        return min(max(a, 0.0), f["_Lu"]), min(max(b, 0.0), f["_Lv"])
    return None


def _in_opening(f, uc, vc):
    return any(a["x"] < uc < a["x"] + a["b"] and a["y"] < vc < a["y"] + a["h"] for a in f.get("aabninger") or [])


def _subdivide(control, L, ms):
    pts = sorted(control)
    clean = [pts[0]]
    for p in pts[1:]:
        if p - clean[-1] > 1e-3:
            clean.append(p)
    out = [clean[0]]
    for a, b in zip(clean, clean[1:]):
        n = max(1, math.ceil((b - a) / ms - 1e-9))
        out += [a + (b - a) * i / n for i in range(1, n + 1)]
    return out


def mesh(s: dict) -> None:
    """Build the mesh: s['_fknuder'] {name: [x, y, z]}, s['_quads'] [(name, shell, [4 nodes], area)]."""
    if not s["flader"]:
        s["_fknuder"], s["_quads"] = {}, []
        return
    ms_std = float(s.get("mesh", STD_MESH))
    special = [p for p in s["knuder"].values()]
    for ls in s["understoetninger_linje"]:
        special += [s["knuder"][ls["fra"]], s["knuder"][ls["til"]]]
    control = {}
    for fn, f in s["flader"].items():
        U, V = {0.0, f["_Lu"]}, {0.0, f["_Lv"]}
        for a in f.get("aabninger") or []:
            U |= {float(a["x"]), float(a["x"] + a["b"])}
            V |= {float(a["y"]), float(a["y"] + a["h"])}
        for p in special:
            uv = _on_shell(f, p)
            if uv:
                U.add(uv[0])
                V.add(uv[1])
        control[fn] = (U, V)
    # repeat until shells that meet have the same nodes along the shared edge
    for _ in range(10):
        grid = {}
        for fn, f in s["flader"].items():
            ms = float(f.get("mesh", ms_std))
            U, V = control[fn]
            grid[fn] = (_subdivide(U, f["_Lu"], ms), _subdivide(V, f["_Lv"], ms))
        changed = False
        for fn, f in s["flader"].items():
            gu, gv = grid[fn]
            edge_pts = [f["_A"] + a * f["_u"] + b * f["_v"] for a in gu for b in (gv[0], gv[-1])] + \
                      [f["_A"] + a * f["_u"] + b * f["_v"] for a in (gu[0], gu[-1]) for b in gv]
            for gn, g in s["flader"].items():
                if gn == fn:
                    continue
                U, V = control[gn]
                for p in edge_pts:
                    uv = _on_shell(g, p)
                    if uv and (min(abs(uv[0] - x) for x in U) > 1e-3 or min(abs(uv[1] - y) for y in V) > 1e-3):
                        U.add(uv[0])
                        V.add(uv[1])
                        changed = True
        if not changed:
            break
    else:
        raise ShellError("meshet kunne ikke gøres sammenhængende mellem fladerne – tjek, at fladerne mødes langs "
                        "hele kanter, eller angiv en fælles 'mesh'-størrelse")
    # nodes: reuse spec nodes, otherwise new names by coordinate
    keys = {}
    for k, p in s["knuder"].items():
        keys[tuple(round(c, 4) for c in p)] = k
    fkn, quads = {}, []

    def node(p):
        nk = tuple(round(float(c), 4) for c in p)
        if nk not in keys:
            name = f"_f{len(fkn) + 1}"
            keys[nk] = name
            fkn[name] = [float(c) for c in p]
        return keys[nk]

    for fn, f in s["flader"].items():
        gu, gv = grid[fn]
        for i in range(len(gu) - 1):
            for j in range(len(gv) - 1):
                uc, vc = (gu[i] + gu[i + 1]) / 2, (gv[j] + gv[j + 1]) / 2
                if _in_opening(f, uc, vc):
                    continue
                corners = [f["_A"] + a * f["_u"] + b * f["_v"]
                      for a, b in ((gu[i], gv[j]), (gu[i + 1], gv[j]), (gu[i + 1], gv[j + 1]), (gu[i], gv[j + 1]))]
                quads.append((f"{fn}#{i}.{j}", fn, [node(p) for p in corners], (gu[i + 1] - gu[i]) * (gv[j + 1] - gv[j])))
    s["_fknuder"], s["_quads"] = fkn, quads


def all_nodes(s: dict) -> dict:
    return s["knuder"] | s.get("_fknuder", {})


def nodes_on_line(s: dict, a, b) -> list:
    """Nodes (spec + mesh) on the line segment a–b, sorted, with parameter t ∈ [0, 1]."""
    a, b = _v(a), _v(b)
    L = float(np.linalg.norm(b - a))
    out = []
    for k, p in all_nodes(s).items():
        d = _v(p) - a
        t = float(np.dot(d, b - a)) / L ** 2
        if -1e-6 <= t <= 1 + 1e-6 and np.linalg.norm(d - t * (b - a)) < 1e-4:
            out.append((t, k))
    return sorted(out)


# ---------- loads ----------
DIRECTION = {"ned": (0, 0, -1), "x": (1, 0, 0), "y": (0, 1, 0), "z": (0, 0, 1)}


def node_loads(s: dict, ltn: str, mats: dict) -> dict:
    """Surface loads, line loads along lines and the shells' self-weight in a load case → {node: [Fx, Fy, Fz]} (spec)."""
    out = {}

    def add(k, vec):
        out.setdefault(k, np.zeros(3))
        out[k] += vec

    lt = s["lasttilfaelde"][ltn] or {}
    for l in lt.get("laster") or []:
        if "flade" in l:
            f = s["flader"][l["flade"]]
            r = l.get("retning", "ned")
            d = f["_n"] if r == "normal" else _v(DIRECTION[r])
            for _, fn, kn, A in s["_quads"]:
                if fn == l["flade"]:
                    for k in kn:
                        add(k, float(l["tryk"]) * A / 4 * d)
        elif "linje" in l:
            a, b = (s["knuder"][k] for k in l["linje"])
            pk = nodes_on_line(s, a, b)
            L = math.dist(a, b)
            d = _v(DIRECTION[l.get("retning", "ned")])
            for i, (t, k) in enumerate(pk):
                t0 = (t + pk[i - 1][0]) / 2 if i > 0 else t
                t1 = (t + pk[i + 1][0]) / 2 if i < len(pk) - 1 else t
                add(k, float(l["linjelast"]) * (t1 - t0) * L * d)
    if lt.get("egenvaegt"):
        for _, fn, kn, A in s["_quads"]:
            f = s["flader"][fn]
            g = float(mats[f["materiale"]].get("rho", 0)) * f["_t"] * A
            for k in kn:
                add(k, g / 4 * _v((0, 0, -1)))
    return out


# ---------- results ----------
def _vm(sx, sy, txy):
    return math.sqrt(max(sx * sx - sx * sy + sy * sy + 3 * txy * txy, 0.0))


def fields(s: dict, m, combo: str) -> dict:
    """Per quad at the midpoint: σ_vM (MPa, largest of top and bottom face), n_u, n_v, n_uv (kN/m),
    m_u, m_v, m_uv (kNm/m) and per node displacement (mm, spec axes). Cached on the model, so results and
    drawings do not compute them twice."""
    cache = m.__dict__.setdefault("_byg_felter", {})
    if combo in cache:
        return cache[combo]
    q_out = {}
    for qn, fn, kn, _ in s["_quads"]:
        q = m.quads[qn]
        t = s["flader"][fn]["_t"]
        sm = [float(v) for v in q.membrane(0, 0, True, combo).flatten()]
        mm = [float(v) for v in q.moment(0, 0, True, combo).flatten()]
        b = 6 / t ** 2
        svm = max(_vm(sm[0] + k * b * mm[0], sm[1] + k * b * mm[1], sm[2] + k * b * mm[2]) for k in (1, -1)) / 1000
        q_out[qn] = {"svm": svm, "nu": sm[0] * t, "nv": sm[1] * t, "nuv": sm[2] * t,
                    "mu": mm[0], "mv": mm[1], "muv": mm[2]}
    fl = {}
    for k in {k for _, _, kn, _ in s["_quads"] for k in kn}:
        n = m.nodes[k]
        fl[k] = (1000 * n.DX[combo], -1000 * n.DZ[combo], 1000 * n.DY[combo])
    cache[combo] = {"quads": q_out, "flytning": fl}
    return cache[combo]


def midpoint(s, kn):
    pts = all_nodes(s)
    return [sum(pts[k][i] for k in kn) / 4 for i in range(3)]


def summary(s: dict, fe: dict) -> dict:
    """Per shell: largest stress with location, membrane forces, moments and displacement; plus extracts."""
    out = {}
    for fn, f in s["flader"].items():
        qs = [(qn, kn) for qn, f2, kn, _ in s["_quads"] if f2 == fn]
        if not qs:
            continue
        v = {qn: fe["quads"][qn] for qn, _ in qs}
        top = sorted(qs, key=lambda x: -v[x[0]]["svm"])[:3]
        all_kn = {k for _, kn in qs for k in kn}
        umax = max(all_kn, key=lambda k: math.hypot(*fe["flytning"][k]))
        out[fn] = {
            "tykkelse_mm": f["tykkelse"], "materiale": f["materiale"], "elementer": len(qs),
            "sigma_vM_max_MPa": round(v[top[0][0]]["svm"], 3),
            "steder_med_stoerst_spaending": [{"xyz": [round(c, 2) for c in midpoint(s, kn)],
                                             "uv": [round(c, 2) for c in _local(f, midpoint(s, kn))[:2]],
                                             "sigma_vM_MPa": round(v[qn]["svm"], 3)} for qn, kn in top],
            "n_u_min_kN_m": round(min(x["nu"] for x in v.values()), 2),
            "n_v_min_kN_m": round(min(x["nv"] for x in v.values()), 2),
            "n_u_max_kN_m": round(max(x["nu"] for x in v.values()), 2),
            "n_v_max_kN_m": round(max(x["nv"] for x in v.values()), 2),
            "m_abs_max_kNm_m": round(max(max(abs(x["mu"]), abs(x["mv"])) for x in v.values()), 3),
            "flytning_max_mm": round(math.hypot(*fe["flytning"][umax]), 2),
            "flytning_max_knude_xyz": [round(c, 2) for c in all_nodes(s)[umax]],
        }
    extracts = {}
    for un, u in s["udtraek"].items():
        f = s["flader"][u["flade"]]
        uu, vv = u.get("x", [0, f["_Lu"]]), u.get("y", [0, f["_Lv"]])
        qs = []
        for qn, fn, kn, _ in s["_quads"]:
            if fn != u["flade"]:
                continue
            a, b, _ = _local(f, midpoint(s, kn))
            if uu[0] - 1e-6 <= a <= uu[1] + 1e-6 and vv[0] - 1e-6 <= b <= vv[1] + 1e-6:
                qs.append(fe["quads"][qn])
        if not qs:
            extracts[un] = {"fejl": "ingen elementer i området"}
            continue
        extracts[un] = {"flade": u["flade"], "x": uu, "y": vv, "elementer": len(qs),
                    "sigma_vM_max_MPa": round(max(q["svm"] for q in qs), 3),
                    "n_u_min_kN_m": round(min(q["nu"] for q in qs), 2), "n_v_min_kN_m": round(min(q["nv"] for q in qs), 2),
                    "n_u_max_kN_m": round(max(q["nu"] for q in qs), 2), "n_v_max_kN_m": round(max(q["nv"] for q in qs), 2),
                    "m_abs_max_kNm_m": round(max(max(abs(q["mu"]), abs(q["mv"])) for q in qs), 3)}
    return {"flader": out, "udtraek": extracts}
