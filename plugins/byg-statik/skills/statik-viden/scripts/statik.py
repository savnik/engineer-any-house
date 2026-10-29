#!/usr/bin/env python3
"""Preliminary calculations for the structural engineer (Python standard library only).

All results are ESTIMATES (OVERSLAG) – they must be verified by the responsible structural engineer.
Partial factors and material values are in COEFFS and MATERIALS with their source;
see references/regnevaerktoej.md for assumptions and limits.

All arithmetic happens here – including sums, tributary width and unit conversion. Every output contains
the command, so the appendix can be re-run by the reviewer.

Commands:
  statik.py regn "<udtryk>" [--var navn=værdi ...]   arithmetic (+ - * / **, sqrt, sin, cos, tan, radians, pi, min, max)
  statik.py last --lag navn:værdi ... [--opland M]    load take-down: sum layers (kN/m2 or thickness_m*kN/m3) → area load and line load
  statik.py profiler [--serie IPE|HEA|HEB]       section properties (computed from the geometry)
  statik.py bjaelke  ...                         simply supported beam: M, V, deflection
  statik.py tryk     --last KN --areal M2 --styrke KPA|MPA   contact pressure (bearing, foundation)
  statik.py test                                 self-test against table values
Run `statik.py bjaelke -h` for all parameters.
"""
import argparse
import ast
import json
import operator
import pathlib
import re
import shlex
import math
import sys

# --- Sections: h, b, tw, tf, r in mm (Euronorm geometry). Section properties are computed so they can be checked.
PROFILES = {
    "IPE": {80: (80, 46, 3.8, 5.2, 5), 100: (100, 55, 4.1, 5.7, 7), 120: (120, 64, 4.4, 6.3, 7),
            140: (140, 73, 4.7, 6.9, 7), 160: (160, 82, 5.0, 7.4, 9), 180: (180, 91, 5.3, 8.0, 9),
            200: (200, 100, 5.6, 8.5, 12), 220: (220, 110, 5.9, 9.2, 12), 240: (240, 120, 6.2, 9.8, 15),
            270: (270, 135, 6.6, 10.2, 15), 300: (300, 150, 7.1, 10.7, 15)},
    "HEA": {100: (96, 100, 5.0, 8.0, 12), 120: (114, 120, 5.0, 8.0, 12), 140: (133, 140, 5.5, 8.5, 12),
            160: (152, 160, 6.0, 9.0, 15), 180: (171, 180, 6.0, 9.5, 15), 200: (190, 200, 6.5, 10.0, 18),
            220: (210, 220, 7.0, 11.0, 18), 240: (230, 240, 7.5, 12.0, 21)},
    "HEB": {100: (100, 100, 6.0, 10.0, 12), 120: (120, 120, 6.5, 11.0, 12), 140: (140, 140, 7.0, 12.0, 12),
            160: (160, 160, 8.0, 13.0, 15), 180: (180, 180, 8.5, 14.0, 15), 200: (200, 200, 9.0, 15.0, 18),
            220: (220, 220, 9.5, 16.0, 18), 240: (240, 240, 10.0, 17.0, 21)},
}
# Table values Iy [cm4] from manufacturer tables – used only by the self-test.
TABLE_IY = {"IPE80": 80.1, "IPE100": 171, "IPE120": 318, "IPE140": 541, "IPE160": 869, "IPE180": 1317,
            "IPE200": 1943, "IPE220": 2772, "IPE240": 3892, "IPE270": 5790, "IPE300": 8356,
            "HEA100": 349, "HEA120": 606, "HEA140": 1033, "HEA160": 1673, "HEA180": 2510, "HEA200": 3692,
            "HEA220": 5410, "HEA240": 7763, "HEB100": 450, "HEB120": 864, "HEB140": 1509, "HEB160": 2492,
            "HEB180": 3831, "HEB200": 5696, "HEB220": 8091, "HEB240": 11260}

# --- Materials (characteristic values, MPa). Timber: DS/EN 338 and DS/EN 14080. Steel: DS/EN 10025-2 (t ≤ 16 mm).
MATERIALS = {
    "C18": {"art": "træ", "fm": 18.0, "fv": 3.4, "E": 9000.0},
    "C24": {"art": "træ", "fm": 24.0, "fv": 4.0, "E": 11000.0},
    "GL24h": {"art": "limtræ", "fm": 24.0, "fv": 3.5, "E": 11500.0},
    "GL30c": {"art": "limtræ", "fm": 30.0, "fv": 3.5, "E": 13000.0},
    "GL32h": {"art": "limtræ", "fm": 32.0, "fv": 3.5, "E": 14200.0},
    "S235": {"art": "stål", "fy": 235.0, "E": 210000.0},
    "S355": {"art": "stål", "fy": 355.0, "E": 210000.0},
}

# --- Coefficients. Default values with source; can be overridden with parameters. See regnevaerktoej.md.
# V = verified 2026-10-11 in DK NA (bygningsreglementet.dk/nationale-annekser); T = DS/EN table behind paywall.
COEFFS = {
    "gamma_g": 1.0,     # V: EN 1990 DK NA:2024 table A1.2(B+C), 6.10b – self-weight unfavourable 1,0·KFI
    "gamma_g_a": 1.2,   # V: same, 6.10a – self-weight unfavourable 1,2·KFI
    "gamma_q": 1.5,     # V: same – leading variable load 1,5·KFI
    "kfi": 1.0,         # V: same, note 4 – KFI CC1 0,9 · CC2 1,0 · CC3 1,1 (dwellings are CC2)
    "gamma_m_trae": 1.35,   # V: EN 1995-1-1 DK NA:2024 table 2.3 – 1,35·γ0·γ3, γ3 = 1,0
    "gamma_m_limtrae": 1.3, # V: same – glulam 1,30·γ0·γ3
    "gamma_m0": 1.1,    # V: EN 1993-1-1 DK NA:2019 6.1(1) – 1,1·γ0·γ3
    "kcr": 0.67,        # T: DS/EN 1995-1-1 6.1.7 – crack factor for shear
    "psi2": 0.2,        # V: EN 1990 DK NA:2024 table A1.1 – category A dwelling ψ0/ψ1/ψ2 = 0,5/0,3/0,2
}
# T: DS/EN 1995-1-1 table 3.1 (solid timber and glulam, service class 1 and 2). Duration per DK NA table 2.2 (V):
# imposed load = medium, snow = short, wind = instantaneous.
KMOD = {"permanent": 0.6, "lang": 0.7, "mellem": 0.8, "kort": 0.9, "oejeblikkelig": 1.1}
KDEF = {1: 0.6, 2: 0.8}  # T: DS/EN 1995-1-1 table 3.2, solid timber and glulam


def output(res):
    """Print the result as JSON with the command that produced it (for the appendix and the reviewer's re-run)."""
    path = shlex.quote(str(pathlib.Path(__file__).resolve()))
    res = {"kommando": f"python3 {path} " + " ".join(shlex.quote(x) for x in sys.argv[1:]), **res}
    print(json.dumps(res, ensure_ascii=False, indent=2))


_OPS = {ast.Add: operator.add, ast.Sub: operator.sub, ast.Mult: operator.mul, ast.Div: operator.truediv,
        ast.Pow: operator.pow, ast.USub: operator.neg, ast.UAdd: operator.pos}
_FUNCS = {"sqrt": math.sqrt, "log": math.log, "exp": math.exp, "sin": math.sin, "cos": math.cos, "tan": math.tan, "radians": math.radians,
         "degrees": math.degrees, "min": min, "max": max, "abs": abs, "round": round}


def evaluate(expr, variables):
    """Safe evaluation of an arithmetic expression (no names other than variables, pi and _FUNCS)."""
    names = {"pi": math.pi, **variables}

    def ev(n):
        if isinstance(n, ast.Expression):
            return ev(n.body)
        if isinstance(n, ast.Constant) and isinstance(n.value, (int, float)):
            return n.value
        if isinstance(n, ast.BinOp) and type(n.op) in _OPS:
            return _OPS[type(n.op)](ev(n.left), ev(n.right))
        if isinstance(n, ast.UnaryOp) and type(n.op) in _OPS:
            return _OPS[type(n.op)](ev(n.operand))
        if isinstance(n, ast.Name) and n.id in names:
            return names[n.id]
        if isinstance(n, ast.Call) and isinstance(n.func, ast.Name) and n.func.id in _FUNCS and not n.keywords:
            return _FUNCS[n.func.id](*[ev(x) for x in n.args])
        raise ValueError(f"ikke tilladt i udtryk: {ast.dump(n)[:60]}")

    s = expr.strip()
    if re.fullmatch(r"-?\d+,\d+", s):  # plain number with decimal comma
        s = s.replace(",", ".")
    return ev(ast.parse(s, mode="eval"))


def number(s):
    """Argument as a number or expression (e.g. '1/cos(radians(45))'). Decimal comma only in plain numbers."""
    try:
        return float(evaluate(s, {}))
    except (ValueError, SyntaxError, ZeroDivisionError, TypeError) as e:
        raise argparse.ArgumentTypeError(f"'{s}': {e}")


def calc(a):
    variables = {}
    for v in a.var or []:
        name, _, value = v.partition("=")
        if not name.isidentifier():
            sys.exit(f"Ugyldigt variabelnavn '{name}'")
        variables[name] = evaluate(value, variables)
    try:
        r = evaluate(a.udtryk, variables)
    except (ValueError, SyntaxError, ZeroDivisionError, TypeError) as e:
        sys.exit(f"Kan ikke beregne '{a.udtryk}': {e}")
    output({"variable": variables, "udtryk": a.udtryk, "resultat": r})


def load(a):
    """Sum layers: 'name:0.5' (kN/m2) or 'name:0.05*18' (thickness m × unit weight kN/m3)."""
    layers, total = [], 0.0
    for s in a.lag:
        name, _, v = s.rpartition(":")
        if not name:
            sys.exit(f"Lag '{s}' skal være navn:værdi")
        try:
            value = evaluate(v, {})
        except (ValueError, SyntaxError) as e:
            sys.exit(f"Lag '{s}': {e}")
        layers.append({"lag": name, "udtryk": v, "kN_m2": round(value, 4)})
        total += value
    res = {"lag": layers, "fladelast_kN_m2": round(total, 4)}
    if a.faktor != 1.0:
        res["faktor"] = a.faktor
        res["fladelast_x_faktor_kN_m2"] = round(total * a.faktor, 4)
    if a.opland:
        res["opland_m"] = a.opland
        res["linjelast_kN_m"] = round(total * a.faktor * a.opland, 4)
    output(res)


def section_i(h, b, tw, tf, r):
    """Area [mm2], Iy [mm4], Wy [mm3] and shear area Av [mm2] for a rolled I/H section."""
    hw = h - 2 * tf
    a_fillet = (1 - math.pi / 4) * r ** 2
    c = r * (10 - 3 * math.pi) / (12 - 3 * math.pi)  # centroid of the root fillet from the flange
    A = 2 * b * tf + hw * tw + 4 * a_fillet
    Iy = (b * h ** 3 - (b - tw) * hw ** 3) / 12 + 4 * a_fillet * (hw / 2 - c) ** 2
    Av = max(A - 2 * b * tf + (tw + 2 * r) * tf, hw * tw)  # DS/EN 1993-1-1 6.2.6(3)a, η = 1
    return {"A": A, "Iy": Iy, "Wy": Iy / (h / 2), "Av": Av}


def find_profile(name):
    name = name.upper().replace(" ", "")
    for series, table in PROFILES.items():
        if name.startswith(series):
            n = int(name[len(series):])
            if n in table:
                return series + str(n), section_i(*table[n])
    sys.exit(f"Ukendt profil '{name}'. Kendte: " + ", ".join(f"{s}{n}" for s, t in PROFILES.items() for n in t))


def moments(L, q, points, n=400):
    """Max moment [kNm] and max shear [kN] for a simply supported beam. q in kN/m, points [(P, a)]."""
    RA = q * L / 2 + sum(P * (L - a) / L for P, a in points)
    RB = q * L / 2 + sum(P * a / L for P, a in points)
    mmax = 0.0
    for i in range(n + 1):
        x = L * i / n
        m = RA * x - q * x * x / 2 - sum(P * (x - a) for P, a in points if x > a)
        mmax = max(mmax, m)
    for P, a in points:  # moment exactly under the point load
        m = RA * a - q * a * a / 2 - sum(Pi * (a - ai) for Pi, ai in points if a > ai)
        mmax = max(mmax, m)
    return RA, RB, mmax, max(RA, RB)


def deflection(L, q, points, EI, n=400):
    """Max deflection [mm]. L in m, q in kN/m, P in kN, EI in Nmm2."""
    Lm = L * 1000
    umax = 0.0
    for i in range(1, n):
        x = Lm * i / n
        u = q * x * (Lm ** 3 - 2 * Lm * x ** 2 + x ** 3) / (24 * EI)
        for P, a in points:
            P_N, a_mm = P * 1000, a * 1000
            b_mm = Lm - a_mm
            if x <= a_mm:
                u += P_N * b_mm * x * (Lm ** 2 - b_mm ** 2 - x ** 2) / (6 * Lm * EI)
            else:
                xx = Lm - x
                u += P_N * a_mm * xx * (Lm ** 2 - a_mm ** 2 - xx ** 2) / (6 * Lm * EI)
        umax = max(umax, u)
    return umax


def read_points(raw):
    out = []
    for s in raw or []:
        parts = [float(v.replace(",", ".")) for v in s.split(":")]
        if len(parts) != 3:
            sys.exit(f"Punktlast '{s}' skal være G:Q:a (kN, kN, m fra venstre vederlag)")
        out.append(tuple(parts))
    return out


def beam(a):
    L = a.spaend
    g = a.g + a.g_flade * a.opland + (a.egenvaegt or 0.0)
    q = a.q + a.q_flade * a.opland
    pts = read_points(a.punkt)
    for _, _, x in pts:
        if not 0 < x < L:
            sys.exit("Punktlastens placering skal ligge mellem vederlagene.")
    k = dict(COEFFS)
    for name in ("gamma_g", "gamma_g_a", "gamma_q", "kfi", "gamma_m", "psi2"):
        v = getattr(a, name, None)
        if v is not None:
            k[name] = v

    # Load combinations (STR): 6.10a self-weight alone, 6.10b self-weight + imposed load. KFI on all partial factors.
    combos = {
        "6.10a": (k["kfi"] * k["gamma_g_a"] * g, [(k["kfi"] * k["gamma_g_a"] * G, x) for G, _, x in pts]),
        "6.10b": (k["kfi"] * (k["gamma_g"] * g + k["gamma_q"] * q),
                  [(k["kfi"] * (k["gamma_g"] * G + k["gamma_q"] * Q), x) for G, Q, x in pts]),
    }
    res = {"OVERSLAG": "skal eftervises af den ansvarlige statiker",
           "input": {"spaend_m": L, "g_kN_m": round(g, 3), "q_kN_m": round(q, 3),
                     "punktlaster_G_Q_a": pts, "materiale": a.materiale, "koefficienter": k}}

    mat = MATERIALS.get(a.materiale)
    if not mat:
        sys.exit(f"Ukendt materiale '{a.materiale}'. Kendte: {', '.join(MATERIALS)}")
    if mat["art"] == "stål":
        if not a.profil:
            sys.exit("Stål kræver --profil, fx HEB160.")
        name, ts = find_profile(a.profil)
        W, I, Av, E = ts["Wy"], ts["Iy"], ts["Av"], mat["E"]
        gm0 = k.get("gamma_m") if a.gamma_m else k["gamma_m0"]
        fmd = mat["fy"] / gm0
        fvd = mat["fy"] / math.sqrt(3) / gm0
        section = {"profil": name, "A_cm2": round(ts["A"] / 100, 1), "Iy_cm4": round(I / 1e4),
                 "Wy_el_cm3": round(W / 1e3, 1), "Av_cm2": round(Av / 100, 1)}
        kmod = 1.0
    else:
        if not (a.bredde and a.hoejde):
            sys.exit("Træ kræver --bredde og --hoejde i mm.")
        b, h = a.bredde, a.hoejde
        W, I, E = b * h ** 2 / 6, b * h ** 3 / 12, mat["E"]
        gm = k.get("gamma_m") if a.gamma_m else (k["gamma_m_trae"] if mat["art"] == "træ" else k["gamma_m_limtrae"])
        kmod_g, kmod_q = KMOD["permanent"], KMOD[a.lastvarighed]
        section = {"tvaersnit_mm": f"{b:g}x{h:g}", "Iy_cm4": round(I / 1e4), "Wy_cm3": round(W / 1e3, 1),
                 "gamma_M": gm, "kmod_6.10a": kmod_g, "kmod_6.10b": kmod_q,
                 "anvendelsesklasse": a.anvendelsesklasse}
        if h / b > 4:
            section["ADVARSEL"] = "h/b > 4: kipning (kcrit) ikke eftervist – kræver sideafstivning af trykranden"
    res["tvaersnit"] = section

    uls = {}
    for nv, (qd, pd) in combos.items():
        RA, RB, Md, Vd = moments(L, qd, pd)
        if mat["art"] == "stål":
            sig, tau = Md * 1e6 / W, Vd * 1e3 / Av
            fm_d, fv_d = fmd, fvd
        else:
            kmod = kmod_g if nv == "6.10a" else kmod_q
            sig, tau = Md * 1e6 / W, 1.5 * Vd * 1e3 / (k["kcr"] * b * h)
            fm_d, fv_d = kmod * mat["fm"] / gm, kmod * mat["fv"] / gm
        uls[nv] = {"RA_kN": round(RA, 2), "RB_kN": round(RB, 2), "Md_kNm": round(Md, 2), "Vd_kN": round(Vd, 2),
                   "udnyttelse_moment": round(sig / fm_d, 2), "udnyttelse_forskydning": round(tau / fv_d, 2)}
    res["brudgraense"] = uls

    # Deflection per EN 1995-1-1 DK NA:2024 table 7.2 (V): self-weight w_fin ≤ L/400, variable load w_inst ≤ L/400
    # (wind L/250). The same principle is used for steel (creep 0); the limits are agreed in the design basis.
    EI = E * I
    u_g = deflection(L, g, [(G, x) for G, _, x in pts], EI)
    u_q = deflection(L, q, [(Q, x) for _, Q, x in pts], EI)
    kd = 0.0 if mat["art"] == "stål" else KDEF[a.anvendelsesklasse]
    g_lim, q_lim = L * 1000 / a.graense, L * 1000 / (a.graense_q or a.graense)
    u_g_fin = u_g * (1 + kd)
    sls = {"u_inst_g_mm": round(u_g, 1), "kdef": kd, "u_fin_g_mm": round(u_g_fin, 1),
           "graense_g": f"L/{a.graense:g} = {g_lim:.1f} mm", "udnyttelse_g": round(u_g_fin / g_lim, 2),
           "u_inst_q_mm": round(u_q, 1), "graense_q": f"L/{(a.graense_q or a.graense):g} = {q_lim:.1f} mm",
           "udnyttelse_q": round(u_q / q_lim, 2),
           "info_u_fin_samlet_mm": round(u_g_fin + u_q * (1 + k["psi2"] * kd), 1)}
    sls["udnyttelse"] = max(sls["udnyttelse_g"], sls["udnyttelse_q"])
    res["anvendelsesgraense"] = sls
    res["karakteristiske_reaktioner_kN"] = {
        "g": [round(v, 2) for v in moments(L, g, [(G, x) for G, _, x in pts])[:2]],
        "q": [round(v, 2) for v in moments(L, q, [(Q, x) for _, Q, x in pts])[:2]]}
    max_util = max([v["udnyttelse_moment"] for v in uls.values()] +
                   [v["udnyttelse_forskydning"] for v in uls.values()] + [sls["udnyttelse"]])
    res["samlet"] = {"max_udnyttelse": max_util, "ok": max_util <= 1.0,
                     "ikke_eftervist": ["kipning/sideafstivning", "vederlag og punktlast på underlag",
                                        "brand", "svingninger", "samlinger og beslag", "stabilitet"]}
    output(res)


def pressure(a):
    strength = a.styrke * (1000 if a.enhed == "MPa" else 1)  # kPa
    p = a.last / a.areal  # kN/m2 = kPa
    output({"OVERSLAG": "skal eftervises af den ansvarlige statiker", "tryk_kPa": round(p, 1),
        "styrke_kPa": strength, "udnyttelse": round(p / strength, 2)})


def list_profiles(a):
    for series, table in PROFILES.items():
        if a.serie and series != a.serie.upper():
            continue
        for n, geo in table.items():
            ts = section_i(*geo)
            print(f"{series}{n:<4} h={geo[0]:>5g} b={geo[1]:>5g}  A={ts['A']/100:6.1f} cm2  "
                  f"Iy={ts['Iy']/1e4:7.0f} cm4  Wy={ts['Wy']/1e3:6.1f} cm3  Av={ts['Av']/100:5.1f} cm2")


def test(_a):
    errors = 0
    for name, iy in TABLE_IY.items():
        _, ts = find_profile(name)
        dev = abs(ts["Iy"] / 1e4 - iy) / iy
        if dev > 0.015:
            errors += 1
            print(f"FEJL {name}: regnet {ts['Iy']/1e4:.0f} cm4, tabel {iy} cm4 ({dev:.1%})")
    # Known answer: q = 10 kN/m, L = 4 m → M = qL²/8 = 20 kNm; P = 10 kN at midspan → M = PL/4 = 10 kNm
    _, _, m1, _ = moments(4, 10, [])
    _, _, m2, _ = moments(4, 0, [(10, 2)])
    u1 = deflection(4, 10, [], 1e12)
    u_fac = 5 * 10 * 4000 ** 4 / (384 * 1e12)
    r = evaluate("0.05*18 + sqrt(16) - 2**3/4 + max(1,2) - 2", {}) + evaluate("0,0", {})
    for name, v, f in (("M jævn", m1, 20), ("M punkt", m2, 10), ("u jævn", u1, u_fac), ("regn", r, 2.9)):
        if abs(v - f) / f > 0.005:
            errors += 1
            print(f"FEJL {name}: {v:.3f} ≠ {f:.3f}")
    print("Selvtest OK" if not errors else f"Selvtest: {errors} fejl")
    return 1 if errors else 0


def main():
    ap = argparse.ArgumentParser(description="Statiske overslag (OVERSLAG – skal eftervises af ansvarlig statiker).")
    sub = ap.add_subparsers(dest="kmd", required=True)
    p = sub.add_parser("profiler")
    p.add_argument("--serie")
    p.set_defaults(fn=list_profiles)
    r = sub.add_parser("regn", help="Aritmetik – brug den til ALLE mellemregninger")
    r.add_argument("udtryk")
    r.add_argument("--var", action="append", help="navn=værdi (kan gentages; værdien må være et udtryk)")
    r.set_defaults(fn=calc)
    la = sub.add_parser("last", help="Lastopgørelse: summér lag til fladelast og evt. linjelast")
    la.add_argument("--lag", action="append", required=True, help="navn:kN/m2 eller navn:tykkelse*tyngde")
    la.add_argument("--faktor", type=number, default=1.0, help="Fx formfaktor eller omregning fra tagflade til vandret")
    la.add_argument("--opland", type=number, default=0.0, help="Oplandsbredde [m] → linjelast")
    la.set_defaults(fn=load)
    t = sub.add_parser("test")
    t.set_defaults(fn=test)
    k = sub.add_parser("tryk", help="Kontakttryk: last [kN] / areal [m2] mod regningsmæssig styrke")
    k.add_argument("--last", type=number, required=True, help="Regningsmæssig last [kN]")
    k.add_argument("--areal", type=number, required=True, help="Kontaktareal [m2]")
    k.add_argument("--styrke", type=number, required=True, help="Regningsmæssig styrke (fra statiker/geotekniker/norm)")
    k.add_argument("--enhed", choices=["kPa", "MPa"], default="kPa")
    k.set_defaults(fn=pressure)
    b = sub.add_parser("bjaelke", help="Simpelt understøttet bjælke")
    b.add_argument("--spaend", type=number, required=True, help="Regningsmæssigt spænd [m]")
    b.add_argument("--materiale", required=True, help=", ".join(MATERIALS))
    b.add_argument("--profil", help="Stålprofil, fx HEB160")
    b.add_argument("--bredde", type=number, help="Træ: bredde [mm]")
    b.add_argument("--hoejde", type=number, help="Træ: højde [mm]")
    b.add_argument("--g", type=number, default=0.0, help="Linjelast, egenlast [kN/m] (karakteristisk)")
    b.add_argument("--q", type=number, default=0.0, help="Linjelast, nyttelast/sne [kN/m] (karakteristisk)")
    b.add_argument("--g-flade", dest="g_flade", type=number, default=0.0, help="Fladelast egenlast [kN/m2]")
    b.add_argument("--q-flade", dest="q_flade", type=number, default=0.0, help="Fladelast nyttelast [kN/m2]")
    b.add_argument("--opland", type=number, default=0.0, help="Oplandsbredde for fladelaster [m]")
    b.add_argument("--egenvaegt", type=number, help="Bjælkens egenvægt [kN/m]")
    b.add_argument("--punkt", action="append", help="Punktlast G:Q:a (kN, kN, m) – kan gentages")
    b.add_argument("--lastvarighed", choices=list(KMOD), default="mellem", help="Træ: varighed for den variable last")
    b.add_argument("--anvendelsesklasse", type=int, choices=[1, 2], default=1, help="Træ: 1 inde/opvarmet, 2 uopvarmet/overdækket")
    b.add_argument("--graense", type=number, default=400, help="Egenlast: w_fin ≤ L/x (DK NA EN 1995 tabel 7.2: 400)")
    b.add_argument("--graense-q", dest="graense_q", type=number, help="Variabel last: w_inst ≤ L/x (400; vind 250). Standard = --graense")
    b.add_argument("--kfi", type=number, help="KFI (CC1 0,9 · CC2 1,0 · CC3 1,1)")
    b.add_argument("--gamma-g", dest="gamma_g", type=number)
    b.add_argument("--gamma-g-a", dest="gamma_g_a", type=number)
    b.add_argument("--gamma-q", dest="gamma_q", type=number)
    b.add_argument("--gamma-m", dest="gamma_m", type=number, help="Overskriv materialets partialkoefficient")
    b.add_argument("--psi2", type=number)
    b.set_defaults(fn=beam)
    a = ap.parse_args()
    return a.fn(a) or 0


if __name__ == "__main__":
    sys.exit(main())
