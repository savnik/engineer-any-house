"""Decoding of a drawing (decoding.yaml): loading, calibration and deterministic check.

The decoding is the structured extract of EVERYTHING on a drawing: views (plan/section/elevation), calibration
(pixel → model mm), written dimensions, rooms, openings, wall thicknesses, levels, texts and uncertain spots.
`decode check` checks the decoding against the drawing itself: does each dimension read match the distance between its
end points on the drawing (via the calibration)? Do the dimension chains add up? Does the scale match the written scale?
See references/decoding.md.
"""
import pathlib

import numpy as np
import yaml

VIEW_TYPES = {"plan", "snit", "facade", "detalje", "situationsplan", "tekst"}
OPENING_TYPES = {"vindue", "doer", "port", "hul"}


class DecodeError(Exception):
    def __init__(self, errors):
        self.errors = errors
        super().__init__("\n".join(errors))


def _point_check(p, path, errors):
    if not (isinstance(p, (list, tuple)) and len(p) == 2 and all(isinstance(v, (int, float)) for v in p)):
        errors.append(f"{path}: forventede [x, y], fik {p!r}")
        return None
    return (float(p[0]), float(p[1]))


def load(path) -> dict:
    path = pathlib.Path(path).resolve()
    try:
        d = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except yaml.YAMLError as e:
        raise DecodeError([f"YAML-fejl: {e}"]) from None
    errors = []
    k = d.get("kilde") or {}
    for field in ("id", "fil", "dokument"):
        if not k.get(field):
            errors.append(f"kilde.{field} mangler")
    if k.get("fil"):
        image = (path.parent / k["fil"]).resolve()
        if not image.exists():
            errors.append(f"kilde.fil findes ikke: {image}")
        k["_billede"] = str(image)
    views = d.get("visninger") or []
    if not views:
        errors.append("visninger mangler (mindst én)")
    ids = set()
    for i, v in enumerate(views):
        vid = str(v.get("id", f"V{i + 1}"))
        v["id"] = vid
        s = f"visninger.{vid}"
        if vid in ids:
            errors.append(f"{s}: id findes allerede")
        ids.add(vid)
        if v.get("type") not in VIEW_TYPES:
            errors.append(f"{s}.type skal være en af {sorted(VIEW_TYPES)}")
        if v.get("type") == "plan" and v.get("etage") is None:
            errors.append(f"{s}: plan kræver etage (modellens etage-id)")
        if v.get("type") == "snit" and not v.get("linje"):
            errors.append(f"{s}: snit kræver linje [x1, y1, x2, y2] i modelkoordinater (snitlinjen fra planen)")
        if v.get("type") == "facade" and not v.get("side"):
            errors.append(f"{s}: facade kræver side (syd|nord|oest|vest eller x+|x-|y+|y-)")
        bb = v.get("bbox")
        if not (isinstance(bb, list) and len(bb) == 4):
            errors.append(f"{s}.bbox skal være [x0, y0, x1, y1] i pixel")
        if v.get("type") in ("plan", "snit", "facade"):
            cal = v.get("kal") or []
            if len(cal) < 3:
                errors.append(f"{s}.kal: mindst 3 punktpar (px → model) – helst i hver sit hjørne af visningen")
            for j, kp in enumerate(cal):
                _point_check(kp.get("px"), f"{s}.kal[{j}].px", errors)
                _point_check(kp.get("model"), f"{s}.kal[{j}].model", errors)
        for j, m in enumerate(v.get("maal") or []):
            ms = f"{s}.maal[{m.get('id', j)}]"
            if not isinstance(m.get("vaerdi"), (int, float)):
                errors.append(f"{ms}.vaerdi skal være et tal i mm (tekst: som skrevet på tegningen)")
            _point_check(m.get("fra"), f"{ms}.fra", errors)
            _point_check(m.get("til"), f"{ms}.til", errors)
            if m.get("retning", "fri") not in ("x", "y", "z", "u", "fri"):
                errors.append(f"{ms}.retning skal være x|y (plan), u|z (snit/facade) eller fri")
        for j, r in enumerate(v.get("rum") or []):
            _point_check(r.get("punkt"), f"{s}.rum[{j}].punkt", errors)
        for j, a in enumerate(v.get("aabninger") or []):
            _point_check(a.get("punkt"), f"{s}.aabninger[{j}].punkt", errors)
            if a.get("type") not in OPENING_TYPES:
                errors.append(f"{s}.aabninger[{j}].type skal være en af {sorted(OPENING_TYPES)}")
        for j, w in enumerate(v.get("vaegge") or []):
            _point_check(w.get("punkt"), f"{s}.vaegge[{j}].punkt", errors)
    if errors:
        raise DecodeError(errors)
    d["_sti"] = str(path)
    return d


def calibrate(v):
    """Affine px → model (2×3) by least squares; returns (M, residual_mm per point, scale_x, scale_y)."""
    pairs = [(np.array(kp["px"], float), np.array(kp["model"], float)) for kp in v["kal"]]
    A = np.array([[p[0], p[1], 1.0] for p, _ in pairs])
    X = np.array([m for _, m in pairs])
    sol, *_ = np.linalg.lstsq(A, X, rcond=None)
    M = sol.T
    residual = [float(np.linalg.norm(M @ np.array([p[0], p[1], 1.0]) - m)) for p, m in pairs]
    sx = float(np.linalg.norm(M[:, 0]))
    sy = float(np.linalg.norm(M[:, 1]))
    return M, residual, sx, sy


def to_model(M, p):
    return M @ np.array([p[0], p[1], 1.0])


def to_px(M, q):
    """Model → px (inverse of the affine calibration)."""
    L = M[:, :2]
    return np.linalg.solve(L, np.asarray(q, float) - M[:, 2])


def tol_mm(value):
    return max(50.0, 0.015 * abs(value))


def dim_in_drawing(M, m):
    a, b = to_model(M, m["fra"]), to_model(M, m["til"])
    r = m.get("retning", "fri")
    if r in ("x", "u"):
        return abs(b[0] - a[0])
    if r in ("y", "z"):
        return abs(b[1] - a[1])
    return float(np.linalg.norm(b - a))


def template() -> int:
    print((pathlib.Path(__file__).resolve().parent.parent.parent / "assets" / "decoding-template.yaml").read_text(encoding="utf-8"))
    return 0


def check(path) -> int:
    try:
        d = load(path)
    except DecodeError as e:
        print(f"AFKODNING-FEJL ({len(e.errors)}):")
        for x in e.errors[:40]:
            print("  - " + x)
        return 1
    k = d["kilde"]
    n_err = n_warn = 0
    print(f"AFKODNING {k['id']} · {k.get('dokument')} · {len(d['visninger'])} visning(er)")
    dpi = k.get("dpi")
    drawing_scale = str(k.get("maalestok") or "")
    for v in d["visninger"]:
        counts = {x: len(v.get(x) or []) for x in ("maal", "rum", "aabninger", "vaegge", "koter", "tekster", "usikre")}
        print(f"  {v['id']} {v['type']} {v.get('etage') or v.get('side') or v.get('linje') or ''}: "
              + ", ".join(f"{n} {x}" for x, n in counts.items() if n))
        if v["type"] not in ("plan", "snit", "facade"):
            continue
        M, residual, sx, sy = calibrate(v)
        rmax = max(residual)
        level = "FEJL" if rmax > 100 else ("ADVARSEL" if rmax > 40 else "ok")
        print(f"    kalibrering: {len(residual)} punkter, største rest {rmax:.0f} mm, skala X {sx:.2f} · Y {sy:.2f} mm/px"
              f" ({100 * (sy - sx) / sx:+.1f} %) [{level}]")
        n_err += level == "FEJL"
        n_warn += level == "ADVARSEL"
        lm = v.get("maalestok") or drawing_scale
        if dpi and lm.startswith("1:"):
            expected = 25.4 / float(dpi) * float(lm[2:])
            rel_dev = ((sx + sy) / 2 - expected) / expected
            text = f"    målestok {lm} ved {dpi} dpi giver {expected:.2f} mm/px; kalibreret {rel_dev:+.1%}"
            if abs(rel_dev) > 0.03:
                text += " – kopien er formindsket/forstørret, eller målestokken er en anden (brug kalibreringen, ikke målestokken)"
                n_warn += 1
            print(text)
        deviations = []
        for m in v.get("maal") or []:
            drawn = dim_in_drawing(M, m)
            dev = drawn - m["vaerdi"]
            if abs(dev) > tol_mm(m["vaerdi"]):
                deviations.append((m, drawn, dev))
        n_m = len(v.get("maal") or [])
        print(f"    mål: {n_m - len(deviations)} af {n_m} passer med tegningens geometri (tolerance max(50 mm; 1,5 %))")
        for m, drawn, dev in deviations[:20]:
            print(f"    FEJL mål {m.get('id', '?')} '{m.get('tekst', m['vaerdi'])}' = {m['vaerdi']:.0f} mm, men tegningen "
                  f"viser {drawn:.0f} mm ({dev:+.0f}) – fejllæst tal, forkerte endepunkter eller målet er ikke målfast tegnet")
        n_err += len(deviations)
        chains = {}
        for m in v.get("maal") or []:
            if m.get("kaede"):
                chains.setdefault(m["kaede"], []).append(m)
        for name, ms in chains.items():
            tot = [m for m in ms if m.get("total")]
            parts = [m for m in ms if not m.get("total")]
            if tot and parts:
                s_ = sum(m["vaerdi"] for m in parts)
                dev = s_ - tot[0]["vaerdi"]
                ok = abs(dev) <= 10
                print(f"    kæde {name}: delmål {s_:.0f} mod total {tot[0]['vaerdi']:.0f} ({dev:+.0f}) "
                      f"[{'ok' if ok else 'FEJL – et delmål er fejllæst eller mangler'}]")
                n_err += not ok
        if v.get("usikre"):
            print(f"    usikre steder: {len(v['usikre'])} (skal nævnes i modelnotatet og på opmålingslisten)")
    print(f"RESULTAT: {n_err} fejl, {n_warn} advarsler")
    return 1 if n_err else 0


__all__ = ["load", "calibrate", "to_model", "to_px", "check", "tol_mm", "dim_in_drawing", "DecodeError"]
