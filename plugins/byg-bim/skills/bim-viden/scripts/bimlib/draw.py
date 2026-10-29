"""Tegninger fra IFC-geometrien (PNG): plan med snit, lodret snit, facade og 3D.

Tegnes fra selve IFC-filen – ikke fra spec'en – så det, der ses, er det, der er i filen.
Konventioner: snit = fyldt og kraftig streg; under snittet = tynd streg; over snittet (bjælker) = stiplet.
Status: eksisterende sort/grå, NY rød, NEDRIVES gul stiplet. Kilde A (antagelse) har orange kant.
"""
import datetime as dt
import math
import pathlib

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import ifcopenshell  # noqa: E402
import ifcopenshell.util.element as ue  # noqa: E402
import ifcopenshell.util.placement as up  # noqa: E402
from matplotlib.patches import PathPatch  # noqa: E402
from matplotlib.path import Path as MPath  # noqa: E402
from matplotlib.transforms import Affine2D  # noqa: E402
from shapely.geometry import MultiLineString, Polygon  # noqa: E402
from shapely.ops import polygonize, unary_union  # noqa: E402

from .geometry import hent  # noqa: E402

FYLD = {"IfcWall": "#9a9a9a", "IfcColumn": "#5a5a5a", "IfcBeam": "#5a5a5a", "IfcSlab": "#c8c8c8",
        "IfcWindow": "#bfe0f0", "IfcDoor": "#d9b48c", "IfcStair": "#e0c9a0", "IfcChimney": "#b0705a",
        "IfcRoof": "#b0705a", "IfcSpace": "#eaf3fb"}
STATUSFARVE = {"NEW": "#d62728", "DEMOLISH": "#e0b000", "TEMPORARY": "#1f77b4"}
MAX_PX = 2400


# ------------------------------------------------------------------ snit af trekantnet
def snit_polygoner(v, f, n, d):
    """Snit af et lukket trekantnet med planet n·x = d. Returnerer (polygoner, segmenter) i 3D.
    Skæringspunkter beregnes pr. kant med ordnede indeks, så naboer får identiske punkter."""
    s = v @ n - d
    s[np.abs(s) < 1e-7] = 1e-7
    segs = []
    tri = f
    sgn = s[tri] > 0
    blandet = sgn.any(axis=1) & ~sgn.all(axis=1)
    for t in tri[blandet]:
        pts = []
        for a, b in ((t[0], t[1]), (t[1], t[2]), (t[2], t[0])):
            if (s[a] > 0) != (s[b] > 0):
                i, j = (a, b) if a < b else (b, a)
                w = s[i] / (s[i] - s[j])
                pts.append(tuple(np.round(v[i] + w * (v[j] - v[i]), 4)))
        if len(pts) == 2 and pts[0] != pts[1]:
            segs.append(pts)
    return segs


def til_2d(segs, akser):
    u, w = akser
    return [[(float(np.dot(p, u)), float(np.dot(p, w))) for p in s] for s in segs]


def polys_af(segs2d):
    """Snitlinjer → materialeflader. polygonize returnerer også hullerne som flader; lige-ulige-reglen
    (antal omsluttende flader) skiller dem fra."""
    if not segs2d:
        return []
    ml = unary_union(MultiLineString(segs2d))
    flader = [p for p in polygonize(ml) if p.area > 1.0]
    skaller = [Polygon(p.exterior) for p in flader]
    ud = []
    for i, p in enumerate(flader):
        rp = p.representative_point()
        n = sum(1 for j, sk in enumerate(skaller) if j != i and sk.area > p.area and sk.contains(rp))
        if n % 2 == 0:
            ud.append(p)
    return ud


def fyld_poly(ax, poly, **kw):
    if poly.is_empty:
        return
    for g in getattr(poly, "geoms", [poly]):
        if g.geom_type != "Polygon":
            continue
        verts, koder = [], []
        for ring in [g.exterior] + list(g.interiors):
            c = list(ring.coords)
            verts += c
            koder += [MPath.MOVETO] + [MPath.LINETO] * (len(c) - 2) + [MPath.CLOSEPOLY]
        ax.add_patch(PathPatch(MPath(verts, koder), **kw))


def projektion(fm, akser, normal_min=0.05):
    u, w = akser
    nrm = np.cross(u, w)
    P = fm.v[fm.f]
    nn = np.cross(P[:, 1] - P[:, 0], P[:, 2] - P[:, 0])
    ok = np.abs(nn @ nrm) > normal_min * (np.linalg.norm(nn, axis=1) + 1e-9)
    tris = [Polygon([(float(p @ u), float(p @ w)) for p in t]) for t in P[ok]]
    tris = [t for t in tris if t.is_valid and t.area > 0.5]
    return unary_union(tris) if tris else None


# ------------------------------------------------------------------ hjælpere
def _figur(bounds, titel):
    x0, y0, x1, y1 = bounds
    bx, by = max(x1 - x0, 1), max(y1 - y0, 1)
    dpi = 150
    skala = min(MAX_PX / dpi / bx, MAX_PX / dpi / by)
    fig = plt.figure(figsize=(max(bx * skala, 6), max(by * skala, 4) + 0.6), dpi=dpi)
    ax = fig.add_axes([0.02, 0.02, 0.96, 0.90])
    ax.set_aspect("equal")
    ax.set_xlim(x0, x1)
    ax.set_ylim(y0, y1)
    ax.axis("off")
    fig.suptitle(titel, fontsize=10, x=0.02, ha="left")
    return fig, ax


def _kant(fm, std="#000000"):
    if fm.status in STATUSFARVE:
        return STATUSFARVE[fm.status]
    return "#e67e00" if fm.kilde == "A" else std


def _maalestok(ax, bounds):
    x0, y0, x1, y1 = bounds
    L = 1000 if (x1 - x0) < 15000 else 5000
    x, y = x0 + 300, y0 + 300
    ax.plot([x, x + L], [y, y], color="k", lw=2)
    ax.text(x + L / 2, y + 120, f"{L // 1000} m", ha="center", fontsize=7)


def _nordpil(ax, f, bounds):
    ctx = next((c for c in f.by_type("IfcGeometricRepresentationContext") if c.ContextType == "Model"
                and not c.is_a("IfcGeometricRepresentationSubContext")), None)
    tn = getattr(ctx, "TrueNorth", None) if ctx else None
    if not tn:
        return
    dx, dy = tn.DirectionRatios[0], tn.DirectionRatios[1]
    x0, y0, x1, y1 = bounds
    cx, cy, L = x1 - 800, y1 - 1200, 700
    ax.annotate("", xy=(cx + dx * L, cy + dy * L), xytext=(cx, cy), arrowprops=dict(arrowstyle="-|>", lw=1.5))
    ax.text(cx + dx * L * 1.3, cy + dy * L * 1.3, "N", ha="center", va="center", fontsize=9, weight="bold")


def _forklaring(ax, f):
    ax.text(0.99, 0.005, "Kraftig: snit · tynd: under snit · stiplet: over snit · rød: NY · gul: NEDRIVES · orange kant: kilde A",
            transform=ax.transAxes, fontsize=6, ha="right", va="bottom", color="#444")


def _gem(fig, ud, navn):
    ud.mkdir(parents=True, exist_ok=True)
    sti = ud / navn
    fig.savefig(sti, dpi=fig.dpi, facecolor="white")
    plt.close(fig)
    return sti


def _affin(kal):
    """Kalibrering "px,py=x,y;…" → 2×3-matrix fra billedpixel til model-mm (2 punkter: ligedannet med
    spejling af billedets y; 3+: mindste kvadraters affin – X og Y skaleres hver for sig)."""
    par = []
    for led in kal.split(";"):
        if not led.strip():
            continue
        a, b = led.split("=")
        px, py = map(float, a.split(","))
        x, y = map(float, b.split(","))
        par.append(((px, py), (x, y)))
    if len(par) < 2:
        raise SystemExit("--kal kræver mindst 2 punktpar: \"px,py=x,y;px,py=x,y\"")
    if len(par) == 2:
        (p1, m1), (p2, m2) = par
        P1, P2 = complex(p1[0], -p1[1]), complex(p2[0], -p2[1])
        M1, M2 = complex(*m1), complex(*m2)
        a = (M1 - M2) / (P1 - P2)
        b = M1 - a * P1
        # z = a·(px − i·py) + b
        return np.array([[a.real, a.imag, b.real], [a.imag, -a.real, b.imag]]), par
    A = np.array([[px, py, 1] for (px, py), _ in par])
    X = np.array([m for _, m in par])
    sol, *_ = np.linalg.lstsq(A, X, rcond=None)
    return sol.T, par


def _underlag(ax, sti, kal):
    import matplotlib.image as mpimg
    img = mpimg.imread(sti)
    M, par = _affin(kal)
    tr = Affine2D(np.vstack([M, [0, 0, 1]])) + ax.transData
    h, w = img.shape[:2]
    ax.imshow(img, extent=(0, w, h, 0), transform=tr, alpha=0.55, zorder=0, interpolation="bilinear",
              cmap="gray" if img.ndim == 2 else None)
    rest = []
    for (px, py), (x, y) in par:
        xm = M @ np.array([px, py, 1])
        rest.append(math.dist(xm, (x, y)))
        ax.plot([x], [y], marker="+", color="blue", ms=10, zorder=9)
    return max(rest) if rest else 0.0


# ------------------------------------------------------------------ plan
def plan_data(f, former, etage, snithoejde=1000.0):
    """Plangeometri i model-mm: snit (fyldt), under snit, over snit (bjælker), rum og dørsymboler."""
    z0 = float(etage.Elevation or 0.0)
    zc = z0 + snithoejde
    mine = [fm for fm in former if fm.etage is not None and fm.etage.id() == etage.id()]
    n, akser = np.array([0.0, 0.0, 1.0]), (np.array([1.0, 0, 0]), np.array([0, 1.0, 0]))
    d = {"z0": z0, "zc": zc, "snit": [], "under": [], "over": [], "rum": [], "doere": [], "mine": mine}
    for fm in mine:
        if fm.klasse == "IfcSpace":
            p = polys_af(til_2d(snit_polygoner(fm.v, fm.f, n, z0 + 50), akser))
            if p:
                d["rum"].append((fm, unary_union(p)))
            continue
        if fm.zmin < zc < fm.zmax and fm.klasse != "IfcDoor":  # døre vises med slagsymbol
            p = polys_af(til_2d(snit_polygoner(fm.v, fm.f, n, zc), akser))
            if p:
                d["snit"].append((fm, unary_union(p)))
            if fm.klasse == "IfcStair":
                d["under"].append((fm, projektion(fm, akser)))
        elif fm.zmax <= zc and fm.zmax > z0 + 1 and fm.klasse not in ("IfcSlab", "IfcCovering"):
            d["under"].append((fm, projektion(fm, akser)))
        elif fm.zmin >= zc and fm.klasse == "IfcBeam" and fm.zmin < z0 + snithoejde + 3000:
            d["over"].append((fm, projektion(fm, akser)))
    d["under"] = [(fm, g) for fm, g in d["under"] if g is not None]
    d["over"] = [(fm, g) for fm, g in d["over"] if g is not None]
    d["doere"] = doersymboler(mine, zc)
    return d


def doersymboler(mine, zc):
    """Dørblad (90° åbent) og slagbue som linjer i model-mm: [(fm, LineString blad, LineString bue)]."""
    from shapely.geometry import LineString
    ud = []
    for fm in mine:
        if fm.klasse != "IfcDoor" or not (fm.zmin < zc < fm.zmax):
            continue
        d = fm.ent
        W = float(d.OverallWidth or 0)
        if not W:
            continue
        M = up.get_local_placement(d.ObjectPlacement)
        op = d.OperationType or getattr(ue.get_type(d), "OperationType", "") or ""
        if "SWING" not in op or "DOUBLE" in op:
            continue
        o, x, y = M[:2, 3], M[:2, 0], M[:2, 1]
        h = o + x * (W if "RIGHT" in op else 0)
        fri = o + x * (0 if "RIGHT" in op else W)
        blad = h + y * W  # bladet åbner mod dørens lokale +y
        a0 = math.atan2(*(fri - h)[::-1])
        a1 = math.atan2(*(blad - h)[::-1])
        da = (a1 - a0 + math.pi) % (2 * math.pi) - math.pi
        bue = [h + W * np.array([math.cos(a0 + da * t / 16), math.sin(a0 + da * t / 16)]) for t in range(17)]
        ud.append((fm, LineString([h, blad]), LineString(bue)))
    return ud


def plan(f, former, etage, snithoejde, ud, vis_id=False, maal=False, underlag=None, kal=None):
    d = plan_data(f, former, etage, snithoejde)
    if not d["mine"]:
        return None
    alle = [g for _, g in d["snit"]] + [g for _, g in d["rum"]]
    if not alle:
        return None
    b = unary_union(alle).bounds
    m = 1500
    bounds = (b[0] - m, b[1] - m, b[2] + m, b[3] + m)
    titel = (f"{f.by_type('IfcProject')[0].Name} – plan {etage.Name} (kote {d['z0']:+.0f}, snit +{snithoejde:.0f})"
             f"  {dt.date.today()}")
    fig, ax = _figur(bounds, titel)
    rest = None
    if underlag:
        rest = _underlag(ax, underlag, kal)
    for fm, g in d["rum"]:
        fyld_poly(ax, g, facecolor=FYLD["IfcSpace"], edgecolor="none", zorder=1, alpha=0.4 if underlag else 1)
    for fm, g in d["under"]:
        fyld_poly(ax, g, facecolor="none", edgecolor=_kant(fm, "#555"), lw=0.5, zorder=2)
    for fm, g in d["over"]:
        fyld_poly(ax, g, facecolor="none", edgecolor="#555", lw=0.6, ls=(0, (4, 3)), zorder=2)
    for fm, g in d["snit"]:
        farve = FYLD.get(fm.klasse, "#8c8c8c")
        if fm.status == "NEW":
            farve = "#f2a3a3"
        ls = (0, (3, 2)) if fm.status == "DEMOLISH" else "solid"
        fyld_poly(ax, g, facecolor="none" if underlag else farve, edgecolor=_kant(fm, "#c00000" if underlag else "#000"),
                  lw=1.3 if fm.klasse != "IfcWindow" else 0.6, ls=ls, zorder=3)
        if vis_id:
            c = g.representative_point()
            ax.text(c.x, c.y, fm.tag, fontsize=5, ha="center", va="center", color="#003c8f", zorder=6)
    for fm, blad, bue in d["doere"]:
        ax.plot(*blad.xy, color="#c00000" if underlag else "#000", lw=0.8, zorder=5)
        ax.plot(*bue.xy, color="#c00000" if underlag else "#000", lw=0.5, zorder=5)
    for fm, g in d["rum"]:
        c = g.representative_point()
        q = ue.get_psets(fm.ent).get("Qto_SpaceBaseQuantities", {})
        a = q.get("NetFloorArea") or g.area / 1e6
        ax.text(c.x, c.y, f"{fm.navn}\n{fm.tag} · {a:.1f} m²", fontsize=7, ha="center", va="center", zorder=7,
                color="#1a1a1a", bbox=dict(boxstyle="round,pad=0.2", fc="white", ec="none", alpha=0.7))
    if maal:
        _maal(ax, f, d["snit"], bounds)
    _maalestok(ax, bounds)
    _nordpil(ax, f, bounds)
    _forklaring(ax, f)
    if rest is not None:
        ax.text(0.01, 0.97, f"Underlag kalibreret: største restafvigelse {rest:.0f} mm", transform=ax.transAxes,
                fontsize=7, color="blue")
    navn = f"plan-{_slug(etage.Name)}" + ("-underlag" if underlag else "") + ".png"
    return _gem(fig, ud, navn)


def _slug(s):
    t = (s or "x").lower()
    for a, b in (("æ", "ae"), ("ø", "oe"), ("å", "aa"), (" ", "-"), (".", "")):
        t = t.replace(a, b)
    return "".join(ch for ch in t if ch.isalnum() or ch == "-")


def _maal(ax, f, snit, bounds):
    vaegge = [(fm, g) for fm, g in snit if fm.klasse == "IfcWall"]
    if not vaegge:
        return
    u = unary_union([g for _, g in vaegge])
    x0, y0, x1, y1 = u.bounds
    for (a, b, y, lbl) in ((x0, x1, y0 - 700, x1 - x0),):
        ax.annotate("", xy=(a, y), xytext=(b, y), arrowprops=dict(arrowstyle="|-|", lw=0.6, shrinkA=0, shrinkB=0))
        ax.text((a + b) / 2, y - 120, f"{lbl:.0f}", ha="center", va="top", fontsize=7)
    xx = x0 - 700
    ax.annotate("", xy=(xx, y0), xytext=(xx, y1), arrowprops=dict(arrowstyle="|-|", lw=0.6, shrinkA=0, shrinkB=0))
    ax.text(xx - 120, (y0 + y1) / 2, f"{y1 - y0:.0f}", ha="right", va="center", fontsize=7, rotation=90)
    for fm, g in vaegge:
        q = ue.get_psets(fm.ent).get("Qto_WallBaseQuantities", {})
        L = q.get("Length")
        if not L:
            continue
        r = g.minimum_rotated_rectangle
        c = r.centroid
        cs = list(r.exterior.coords)
        e1 = np.subtract(cs[1], cs[0])
        e2 = np.subtract(cs[2], cs[1])
        lang = e1 if np.linalg.norm(e1) >= np.linalg.norm(e2) else e2
        vink = math.degrees(math.atan2(lang[1], lang[0]))
        if vink > 90:
            vink -= 180
        if vink < -90:
            vink += 180
        ax.text(c.x, c.y, f"{L:.0f}", fontsize=5.5, ha="center", va="center", rotation=vink, color="#7a0000", zorder=8,
                bbox=dict(boxstyle="square,pad=0.05", fc="white", ec="none", alpha=0.75))


# ------------------------------------------------------------------ snit, facade, 3D (malerens algoritme)
def _lys(nn, se):
    nn = nn / (np.linalg.norm(nn, axis=1, keepdims=True) + 1e-12)
    lys = np.array([-0.4, -0.6, 0.7])
    lys = lys / np.linalg.norm(lys)
    return 0.55 + 0.45 * np.abs(nn @ lys)


def _overflade(styles):
    for st in styles or []:
        kand = [st] if st.is_a("IfcSurfaceStyle") else list(getattr(st, "Styles", None) or [])
        for ss in kand:
            if ss.is_a("IfcSurfaceStyle"):
                for x in ss.Styles:
                    if x.is_a("IfcSurfaceStyleShading"):
                        c = x.SurfaceColour
                        return np.array([c.Red, c.Green, c.Blue])
    return None


def _stilfarve(ent):
    """Farve fra IfcStyledItem på geometrien, ellers fra materialets stil."""
    for rep in getattr(ent.Representation, "Representations", None) or []:
        items = list(rep.Items)
        while items:
            it = items.pop()
            if it.is_a("IfcMappedItem"):
                items += list(it.MappingSource.MappedRepresentation.Items)
                continue
            for si in getattr(it, "StyledByItem", None) or []:
                c = _overflade(si.Styles)
                if c is not None:
                    return c
    mat = ue.get_material(ent, should_skip_usage=True)
    mats = []
    if mat is not None:
        if mat.is_a("IfcMaterial"):
            mats = [mat]
        elif mat.is_a("IfcMaterialLayerSet"):
            mats = [l.Material for l in mat.MaterialLayers]
    for m in mats:
        for dr in getattr(m, "HasRepresentation", None) or []:
            for r in dr.Representations:
                for si in r.Items:
                    c = _overflade(si.Styles)
                    if c is not None:
                        return c
    return None


def _farve(fm):
    import matplotlib.colors as mc
    if fm.status in STATUSFARVE:
        return np.array(mc.to_rgb(STATUSFARVE[fm.status]))
    c = _stilfarve(fm.ent)
    return c if c is not None else np.array(mc.to_rgb(FYLD.get(fm.klasse, "#bbbbbb")))


def raster(former, R, bounds, px_pr_mm, klip=None, bleg=False, med_id=False):
    """Z-buffer: rasteriserer trekanterne ortografisk i rammen R=(u, w, d) (d = synsretning).
    Returnerer RGB-billede med konturer, hvor element eller fladeorientering skifter. 2× supersampling."""
    u, w, d = R
    x0, y0, x1, y1 = bounds
    ss = 2
    s = px_pr_mm * ss
    W, H = int((x1 - x0) * s) + 1, int((y1 - y0) * s) + 1
    dyb = np.full((H, W), np.inf)
    farve = np.ones((H, W, 3))
    eid = np.full((H, W), -1, dtype=np.int32)
    nrm = np.zeros((H, W, 3))
    for k, fm in enumerate(former):
        P = fm.v[fm.f]
        if klip is not None:
            P = P[(P @ klip[0] - klip[1]).max(axis=1) > 0]
        if not len(P):
            continue
        X = (P @ u - x0) * s
        Y = (y1 - P @ w) * s
        Z = P @ d
        N = np.cross(P[:, 1] - P[:, 0], P[:, 2] - P[:, 0])
        N /= np.linalg.norm(N, axis=1, keepdims=True) + 1e-12
        base = _farve(fm)
        if bleg:
            base = base * 0.35 + 0.6
        lys = 0.55 + 0.45 * np.abs(N @ (np.array([-0.4, -0.6, 0.7]) / np.linalg.norm([-0.4, -0.6, 0.7])))
        for t in range(len(P)):
            xs, ys, zs = X[t], Y[t], Z[t]
            a0, a1 = max(int(xs.min()), 0), min(int(xs.max()) + 1, W - 1)
            b0, b1 = max(int(ys.min()), 0), min(int(ys.max()) + 1, H - 1)
            if a1 < a0 or b1 < b0:
                continue
            gx, gy = np.meshgrid(np.arange(a0, a1 + 1) + 0.5, np.arange(b0, b1 + 1) + 0.5)
            den = (ys[1] - ys[2]) * (xs[0] - xs[2]) + (xs[2] - xs[1]) * (ys[0] - ys[2])
            if abs(den) < 1e-9:
                continue
            l0 = ((ys[1] - ys[2]) * (gx - xs[2]) + (xs[2] - xs[1]) * (gy - ys[2])) / den
            l1 = ((ys[2] - ys[0]) * (gx - xs[2]) + (xs[0] - xs[2]) * (gy - ys[2])) / den
            l2 = 1 - l0 - l1
            ind = (l0 >= -1e-6) & (l1 >= -1e-6) & (l2 >= -1e-6)
            z = l0 * zs[0] + l1 * zs[1] + l2 * zs[2]
            sub = dyb[b0:b1 + 1, a0:a1 + 1]
            m = ind & (z < sub - 0.5)
            if not m.any():
                continue
            sub[m] = z[m]
            farve[b0:b1 + 1, a0:a1 + 1][m] = np.clip(base * lys[t], 0, 1)
            eid[b0:b1 + 1, a0:a1 + 1][m] = k
            nrm[b0:b1 + 1, a0:a1 + 1][m] = N[t]
    kant = np.zeros((H, W), bool)
    dyb[~np.isfinite(dyb)] = 1e12
    for ax_ in (0, 1):
        de = np.diff(eid, axis=ax_) != 0
        dn = (np.abs(np.diff(nrm, axis=ax_)).sum(axis=2) > 0.3) & (np.diff(eid, axis=ax_) == 0) & \
             (np.abs(np.diff(dyb, axis=ax_)) < 1e11)
        dz = (np.abs(np.diff(dyb, axis=ax_)) > 60) & (np.abs(np.diff(dyb, axis=ax_)) < 1e11)
        e = de | dn | dz
        if ax_ == 0:
            kant[:-1] |= e
        else:
            kant[:, :-1] |= e
    if med_id:
        return eid
    farve[kant] = farve[kant] * 0.25
    img = farve.reshape(H // ss, ss, W // ss, ss, 3).mean(axis=(1, 3)) if H % ss == 0 and W % ss == 0 else \
        farve[: H - H % ss, : W - W % ss].reshape(H // ss, ss, W // ss, ss, 3).mean(axis=(1, 3))
    return img


def _vis_raster(ax, img, bounds, zorder=1):
    x0, y0, x1, y1 = bounds
    ax.imshow(img, extent=(x0, x1, y0, y1), origin="upper", zorder=zorder, interpolation="bilinear")


def _px_pr_mm(bounds):
    return min(MAX_PX / max(bounds[2] - bounds[0], 1), MAX_PX / max(bounds[3] - bounds[1], 1))


def _ramme_for_side(f, side):
    """Facadeside → (u, w, d): u vandret mod højre, w op, d = synsretning (ind mod huset)."""
    side = (side or "syd").lower()
    lokal = {"x+": (1, 0), "x-": (-1, 0), "y+": (0, 1), "y-": (0, -1)}
    if side in lokal:
        ud_ = np.array([*lokal[side], 0.0])
    else:
        ctx = next((c for c in f.by_type("IfcGeometricRepresentationContext") if c.ContextType == "Model"
                    and not c.is_a("IfcGeometricRepresentationSubContext")), None)
        tn = getattr(ctx, "TrueNorth", None) if ctx else None
        nord = np.array([tn.DirectionRatios[0], tn.DirectionRatios[1], 0.0]) if tn else np.array([0, 1.0, 0])
        oest = np.array([nord[1], -nord[0], 0.0])
        ud_ = {"nord": nord, "syd": -nord, "oest": oest, "øst": oest, "vest": -oest}.get(side)
        if ud_ is None:
            raise SystemExit("--side: nord|syd|oest|vest eller x+|x-|y+|y-")
    d = -ud_ / np.linalg.norm(ud_)
    return _hoejre(d), np.array([0, 0, 1.0]), d


def _hoejre(d):
    # set fra beskueren, der kigger i retning d: højre = d × z
    return np.cross(d, np.array([0, 0, 1.0]))


def facade(f, former, side, ud):
    former = [fm for fm in former if fm.klasse != "IfcSpace"]
    u, w, d = _ramme_for_side(f, side)
    alle = np.vstack([fm.v for fm in former])
    bx = alle @ u
    bz = alle @ w
    m = 1500
    bounds = (bx.min() - m, bz.min() - m, bx.max() + m, bz.max() + m)
    fig, ax = _figur(bounds, f"{f.by_type('IfcProject')[0].Name} – facade {side}  {dt.date.today()}")
    _vis_raster(ax, raster(former, (u, w, d), bounds, _px_pr_mm(bounds)), bounds)
    _etagelinjer(ax, f, bounds)
    _maalestok(ax, bounds)
    return _gem(fig, ud, f"facade-{_slug(side)}.png")


def _etagelinjer(ax, f, bounds):
    for st in f.by_type("IfcBuildingStorey"):
        z = float(st.Elevation or 0)
        ax.plot([bounds[0] + 200, bounds[0] + 900], [z, z], color="#1f77b4", lw=0.8)
        ax.text(bounds[0] + 950, z, f"{st.Name} {z:+.0f}", fontsize=6, va="center", color="#1f77b4")


def snit(f, former, linje, ud, vis_id=False):
    x1, y1, x2, y2 = map(float, linje.split(","))
    p1, p2 = np.array([x1, y1, 0.0]), np.array([x2, y2, 0.0])
    u = (p2 - p1) / np.linalg.norm(p2 - p1)
    w = np.array([0, 0, 1.0])
    d = np.cross(w, u)  # synsretning: mod venstre for linjen
    n, dd = d, float(p1 @ d)
    former = [fm for fm in former if fm.klasse not in ("IfcSpace",)]
    alle = np.vstack([fm.v for fm in former])
    bu, bz = alle @ u - p1 @ u, alle @ w
    m = 1500
    bounds = (bu.min() - m, bz.min() - m, bu.max() + m, bz.max() + m)
    fig, ax = _figur(bounds, f"{f.by_type('IfcProject')[0].Name} – snit {linje} (set mod venstre)  {dt.date.today()}")
    bag = [fm for fm in former if (fm.v @ n).max() > dd]
    ob = (bounds[0] + float(p1 @ u), bounds[1], bounds[2] + float(p1 @ u), bounds[3])
    img = raster(bag, (u, w, d), ob, _px_pr_mm(bounds), klip=(n, dd), bleg=True)
    _vis_raster(ax, img, bounds)
    for fm in former:
        if (fm.v @ n).min() < dd < (fm.v @ n).max():
            segs = snit_polygoner(fm.v, fm.f, n, dd)
            ps = polys_af([[(float(p @ u) - float(p1 @ u), float(p @ w)) for p in s] for s in segs])
            if ps:
                g = unary_union(ps)
                fyld_poly(ax, g, facecolor="#333333" if fm.klasse != "IfcWindow" else "#bfe0f0",
                          edgecolor=_kant(fm), lw=1.0, zorder=4)
                if vis_id:
                    c = g.representative_point()
                    ax.text(c.x, c.y, fm.tag, fontsize=5, color="#ffd400", ha="center", va="center", zorder=6)
    _etagelinjer(ax, f, bounds)
    _maalestok(ax, bounds)
    return _gem(fig, ud, f"snit-{int(x1)}-{int(y1)}-{int(x2)}-{int(y2)}.png")


def tre_d(f, former, fra, ud):
    former = [fm for fm in former if fm.klasse not in ("IfcSpace",)]
    retn = {"sv": (-1, -1), "so": (1, -1), "nv": (-1, 1), "no": (1, 1), "s": (0, -1), "n": (0, 1), "v": (-1, 0),
            "o": (1, 0)}.get((fra or "sv").lower(), (-1, -1))
    beskuer = np.array([retn[0], retn[1], 0.9])
    d = -beskuer / np.linalg.norm(beskuer)
    u = np.cross(d, np.array([0, 0, 1.0]))
    u /= np.linalg.norm(u)
    w = np.cross(u, d)
    alle = np.vstack([fm.v for fm in former])
    bu, bw = alle @ u, alle @ w
    m = 1000
    bounds = (bu.min() - m, bw.min() - m, bu.max() + m, bw.max() + m)
    fig, ax = _figur(bounds, f"{f.by_type('IfcProject')[0].Name} – 3D fra {fra}  {dt.date.today()}")
    _vis_raster(ax, raster(former, (u, w, d), bounds, _px_pr_mm(bounds)), bounds)
    return _gem(fig, ud, f"3d-{_slug(fra)}.png")


# ------------------------------------------------------------------ indgang
def tegn(ifc, hvad, etage=None, linje=None, side=None, fra="sv", underlag=None, kal=None, vis_id=False, maal=False,
         ud=None, snithoejde=1000.0):
    f = ifcopenshell.open(str(ifc))
    ud = pathlib.Path(ud) if ud else pathlib.Path(ifc).parent / "tegninger"
    former = hent(f)
    filer = []
    etager = sorted(f.by_type("IfcBuildingStorey"), key=lambda s: float(s.Elevation or 0))
    if hvad in ("plan", "alle"):
        valgt = etager
        if etage:
            valgt = [s for s in etager if s.Name == etage or s.GlobalId == etage or _slug(s.Name) == _slug(etage)
                     or (s.Name or "").lower().startswith(etage.lower())]
            if not valgt:
                raise SystemExit(f"Etage '{etage}' findes ikke: {', '.join(s.Name for s in etager)}")
        if underlag and not kal:
            raise SystemExit("--underlag kræver --kal")
        for st in valgt:
            p = plan(f, former, st, snithoejde, ud, vis_id, maal, underlag if etage else None, kal)
            if p:
                filer.append(p)
    if hvad == "snit":
        if not linje:
            raise SystemExit("snit kræver --linje x1,y1,x2,y2 (mm, lokale koordinater; der ses mod venstre)")
        filer.append(snit(f, former, linje, ud, vis_id))
    if hvad == "facade":
        filer.append(facade(f, former, side or "syd", ud))
    if hvad == "alle":
        har_nord = any(getattr(c, "TrueNorth", None) for c in f.by_type("IfcGeometricRepresentationContext"))
        for s in (("syd", "nord", "oest", "vest") if har_nord else ("y-", "y+", "x+", "x-")):
            filer.append(facade(f, former, s, ud))
    if hvad in ("3d", "alle"):
        filer.append(tre_d(f, former, fra, ud))
    return filer
