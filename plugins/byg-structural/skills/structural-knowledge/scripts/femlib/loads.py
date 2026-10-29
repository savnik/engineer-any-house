"""Load geometry for the drawings: arrows (start → tip) and texts per load case, in spec coordinates."""
import math

from . import shells

COLOURS = ["#1e8449", "#b9770e", "#2471a3", "#7d3c98", "#c0392b", "#117864", "#6e2c00", "#1b2631"]
AXIS = {"ned": (0, 0, -1), "x": (1, 0, 0), "y": (0, 1, 0), "z": (0, 0, 1)}


def colour(s: dict, lt: str) -> str:
    return COLOURS[list(s["lasttilfaelde"]).index(lt) % len(COLOURS)]


def span(s: dict) -> float:
    pts = list(shells.all_nodes(s).values())
    return max(max(p[i] for p in pts) - min(p[i] for p in pts) for i in range(3)) or 1.0


def _fmt(v, d=1):
    return f"{v:.{d}f}".replace(".", ",").replace("-", "−")


def _direction(l, v, s=None):
    r = l.get("retning", "ned")
    d = list(s["flader"][l["flade"]]["_n"]) if r == "normal" else list(AXIS[r])
    sg = 1 if v >= 0 else -1
    return [sg * c for c in d]


def _arrow(lt, tip, d, L, level=0):
    """Arrow with its tip at the point of application; several loads at the same place are stacked outwards (level = 0, 1, …)."""
    sp = [tip[i] - d[i] * L * 1.25 * level for i in range(3)]
    return {"lt": lt, "start": [sp[i] - d[i] * L for i in range(3)], "spids": sp}


def arrows(s: dict) -> dict:
    """{load case: {"pile": [{start, spids}], "tekster": [(point, text)]}}. The arrows end at the load's point of application."""
    sp = span(s)
    Lk, Lp = 0.07 * sp, 0.14 * sp
    out = {}
    levels = {}  # loads on the same member, line or shell are stacked

    def level(key):
        n = levels.get(key, 0)
        levels[key] = n + 1
        return n

    for lt, lt_d in s["lasttilfaelde"].items():
        g = out.setdefault(lt, {"pile": [], "tekster": []})
        lt_d = lt_d or {}
        if lt_d.get("egenvaegt"):
            g["tekster"].append((None, f"{lt}: egenvægt"))
        for l in lt_d.get("laster") or []:
            if "moment" in l:
                g["tekster"].append((s["knuder"][l["knude"]], f"{lt}: M = {_fmt(l['moment'])} kNm"))
                continue
            if "flade" in l:
                d = _direction(l, float(l["tryk"]), s)
                nv = level(("flade", l["flade"]))
                qs = {tuple(int(c) for c in qn.split("#")[1].split(".")): kn
                      for qn, fn, kn, _ in s["_quads"] if fn == l["flade"]}
                ni = max(i for i, _ in qs) + 1
                nj = max(j for _, j in qs) + 1
                si, sj = max(1, round(ni / 6)), max(1, round(nj / 6))  # approx. 6 × 6 arrows evenly over the shell
                for (i, j), kn in qs.items():
                    if (i - si // 2) % si == 0 and (j - sj // 2) % sj == 0:
                        g["pile"].append(_arrow(lt, shells.midpoint(s, kn), d, Lk, nv))
                f = s["flader"][l["flade"]]
                mid = list(f["_A"] + f["_u"] * f["_Lu"] / 2 + f["_v"] * f["_Lv"] / 2)
                g["tekster"].append(([mid[i] - d[i] * Lk * (1.2 + 1.25 * nv) for i in range(3)],
                                     f"{lt}: {_fmt(float(l['tryk']), 2)} kN/m²"))
                continue
            if "linjelast" in l:
                w = l["linjelast"]
                w1, w2 = (w, w) if not isinstance(w, (list, tuple)) else w
                if "linje" in l:
                    a, b = (s["knuder"][k] for k in l["linje"])
                    t0, t1 = 0.0, 1.0
                else:
                    e = s["elementer"][l["element"]]
                    a, b = (s["knuder"][e[k]] for k in ("fra", "til"))
                    t0 = float(l.get("fra") or 0) / e["_L"]
                    t1 = float(l["til"]) / e["_L"] if l.get("til") is not None else 1.0
                d = _direction(l, float(w1) if abs(float(w1)) > 1e-12 else float(w2))
                nv = level(("linje", tuple(l["linje"])) if "linje" in l else ("element", l["element"]))
                pts = [[a[i] + (b[i] - a[i]) * (t0 + (t1 - t0) * j / 8) for i in range(3)] for j in range(9)]
                for p in pts:
                    g["pile"].append(_arrow(lt, p, d, Lk, nv))
                g["linjer"] = g.get("linjer", []) + [[g["pile"][-9 + j]["start"] for j in range(9)]]
                text = f"{_fmt(float(w1))}–{_fmt(float(w2))}" if float(w1) != float(w2) else _fmt(float(w1))
                g["tekster"].append(([pts[4][i] - d[i] * Lk * (1.3 + 1.25 * nv) for i in range(3)], f"{lt}: {text} kN/m"))
                continue
            if "punktlast" in l:
                if "element" in l:
                    e = s["elementer"][l["element"]]
                    t = float(l.get("x", e["_L"] / 2)) / e["_L"]
                    a, b = (s["knuder"][e[k]] for k in ("fra", "til"))
                    p = [a[i] + (b[i] - a[i]) * t for i in range(3)]
                else:
                    p = s["knuder"][l["knude"]]
                d = _direction(l, float(l["punktlast"]))
                g["pile"].append(_arrow(lt, p, d, Lp))
                g["tekster"].append(([p[i] - d[i] * Lp * 1.1 for i in range(3)], f"{lt}: {_fmt(float(l['punktlast']))} kN"))
    return out


def length(p) -> float:
    return math.dist(p["start"], p["spids"])
