"""Drawings from the IFC geometry (PNG): plan with cut, vertical section, elevation and 3D.

Drawn from the IFC file itself – not from the spec – so what you see is what is in the file.
Conventions: cut = filled and heavy line; below the cut = thin line; above the cut (beams) = dashed.
Status: existing black/grey, NEW red, DEMOLISH yellow dashed. Source A (assumption) has an orange edge.
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

from .geometry import fetch_shapes  # noqa: E402

FILL = {"IfcWall": "#9a9a9a", "IfcColumn": "#5a5a5a", "IfcBeam": "#5a5a5a", "IfcSlab": "#c8c8c8",
        "IfcWindow": "#bfe0f0", "IfcDoor": "#d9b48c", "IfcStair": "#e0c9a0", "IfcChimney": "#b0705a",
        "IfcRoof": "#b0705a", "IfcSpace": "#eaf3fb"}
STATUS_COLOUR = {"NEW": "#d62728", "DEMOLISH": "#e0b000", "TEMPORARY": "#1f77b4"}
MAX_PX = 2400


# ------------------------------------------------------------------ sectioning a triangle mesh
def section_segments(v, f, n, d):
    """Section of a closed triangle mesh with the plane n·x = d. Returns (polygons, segments) in 3D.
    Intersection points are computed per edge with ordered indices, so neighbours get identical points."""
    s = v @ n - d
    s[np.abs(s) < 1e-7] = 1e-7
    segs = []
    tri = f
    sgn = s[tri] > 0
    mixed = sgn.any(axis=1) & ~sgn.all(axis=1)
    for t in tri[mixed]:
        pts = []
        for a, b in ((t[0], t[1]), (t[1], t[2]), (t[2], t[0])):
            if (s[a] > 0) != (s[b] > 0):
                i, j = (a, b) if a < b else (b, a)
                w = s[i] / (s[i] - s[j])
                pts.append(tuple(np.round(v[i] + w * (v[j] - v[i]), 4)))
        if len(pts) == 2 and pts[0] != pts[1]:
            segs.append(pts)
    return segs


def to_2d(segs, axes):
    u, w = axes
    return [[(float(np.dot(p, u)), float(np.dot(p, w))) for p in s] for s in segs]


def polys_from(segs2d):
    """Section lines → material faces. polygonize also returns the holes as faces; the even-odd rule
    (number of enclosing faces) separates them."""
    if not segs2d:
        return []
    ml = unary_union(MultiLineString(segs2d))
    faces = [p for p in polygonize(ml) if p.area > 1.0]
    shells = [Polygon(p.exterior) for p in faces]
    out = []
    for i, p in enumerate(faces):
        rp = p.representative_point()
        n = sum(1 for j, sh in enumerate(shells) if j != i and sh.area > p.area and sh.contains(rp))
        if n % 2 == 0:
            out.append(p)
    return out


def fill_poly(ax, poly, **kw):
    if poly.is_empty:
        return
    for g in getattr(poly, "geoms", [poly]):
        if g.geom_type != "Polygon":
            continue
        verts, codes = [], []
        for ring in [g.exterior] + list(g.interiors):
            c = list(ring.coords)
            verts += c
            codes += [MPath.MOVETO] + [MPath.LINETO] * (len(c) - 2) + [MPath.CLOSEPOLY]
        ax.add_patch(PathPatch(MPath(verts, codes), **kw))


def projection(fm, axes, normal_min=0.05):
    u, w = axes
    nrm = np.cross(u, w)
    P = fm.v[fm.f]
    nn = np.cross(P[:, 1] - P[:, 0], P[:, 2] - P[:, 0])
    ok = np.abs(nn @ nrm) > normal_min * (np.linalg.norm(nn, axis=1) + 1e-9)
    tris = [Polygon([(float(p @ u), float(p @ w)) for p in t]) for t in P[ok]]
    tris = [t for t in tris if t.is_valid and t.area > 0.5]
    return unary_union(tris) if tris else None


# ------------------------------------------------------------------ helpers
def _figure(bounds, title):
    x0, y0, x1, y1 = bounds
    bx, by = max(x1 - x0, 1), max(y1 - y0, 1)
    dpi = 150
    scale = min(MAX_PX / dpi / bx, MAX_PX / dpi / by)
    fig = plt.figure(figsize=(max(bx * scale, 6), max(by * scale, 4) + 0.6), dpi=dpi)
    ax = fig.add_axes([0.02, 0.02, 0.96, 0.90])
    ax.set_aspect("equal")
    ax.set_xlim(x0, x1)
    ax.set_ylim(y0, y1)
    ax.axis("off")
    fig.suptitle(title, fontsize=10, x=0.02, ha="left")
    return fig, ax


def _edge_colour(fm, default="#000000"):
    if fm.status in STATUS_COLOUR:
        return STATUS_COLOUR[fm.status]
    return "#e67e00" if fm.source == "A" else default


def _scale_bar(ax, bounds):
    x0, y0, x1, y1 = bounds
    L = 1000 if (x1 - x0) < 15000 else 5000
    x, y = x0 + 300, y0 + 300
    ax.plot([x, x + L], [y, y], color="k", lw=2)
    ax.text(x + L / 2, y + 120, f"{L // 1000} m", ha="center", fontsize=7)


def _north_arrow(ax, f, bounds):
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


def _legend(ax, f):
    ax.text(0.99, 0.005, "Kraftig: snit · tynd: under snit · stiplet: over snit · rød: NY · gul: NEDRIVES · orange kant: kilde A",
            transform=ax.transAxes, fontsize=6, ha="right", va="bottom", color="#444")


def _save(fig, out, name):
    out.mkdir(parents=True, exist_ok=True)
    path = out / name
    fig.savefig(path, dpi=fig.dpi, facecolor="white")
    plt.close(fig)
    return path


def _affine(cal):
    """Calibration "px,py=x,y;…" → 2×3 matrix from image pixel to model mm (2 points: similarity with
    the image y mirrored; 3+: least-squares affine – X and Y scaled independently)."""
    pairs = []
    for part in cal.split(";"):
        if not part.strip():
            continue
        a, b = part.split("=")
        px, py = map(float, a.split(","))
        x, y = map(float, b.split(","))
        pairs.append(((px, py), (x, y)))
    if len(pairs) < 2:
        raise SystemExit("--kal kræver mindst 2 punktpar: \"px,py=x,y;px,py=x,y\"")
    if len(pairs) == 2:
        (p1, m1), (p2, m2) = pairs
        P1, P2 = complex(p1[0], -p1[1]), complex(p2[0], -p2[1])
        M1, M2 = complex(*m1), complex(*m2)
        a = (M1 - M2) / (P1 - P2)
        b = M1 - a * P1
        # z = a·(px − i·py) + b
        return np.array([[a.real, a.imag, b.real], [a.imag, -a.real, b.imag]]), pairs
    A = np.array([[px, py, 1] for (px, py), _ in pairs])
    X = np.array([m for _, m in pairs])
    sol, *_ = np.linalg.lstsq(A, X, rcond=None)
    return sol.T, pairs


def _underlay(ax, path, cal):
    import matplotlib.image as mpimg
    img = mpimg.imread(path)
    M, pairs = _affine(cal)
    tr = Affine2D(np.vstack([M, [0, 0, 1]])) + ax.transData
    h, w = img.shape[:2]
    ax.imshow(img, extent=(0, w, h, 0), transform=tr, alpha=0.55, zorder=0, interpolation="bilinear",
              cmap="gray" if img.ndim == 2 else None)
    residual = []
    for (px, py), (x, y) in pairs:
        xm = M @ np.array([px, py, 1])
        residual.append(math.dist(xm, (x, y)))
        ax.plot([x], [y], marker="+", color="blue", ms=10, zorder=9)
    return max(residual) if residual else 0.0


# ------------------------------------------------------------------ plan
def plan_data(f, shapes, storey, cut_height=1000.0):
    """Plan geometry in model mm: cut (filled), below cut, above cut (beams), spaces and door symbols."""
    z0 = float(storey.Elevation or 0.0)
    zc = z0 + cut_height
    own = [fm for fm in shapes if fm.storey is not None and fm.storey.id() == storey.id()]
    n, axes = np.array([0.0, 0.0, 1.0]), (np.array([1.0, 0, 0]), np.array([0, 1.0, 0]))
    d = {"z0": z0, "zc": zc, "snit": [], "under": [], "over": [], "rum": [], "doere": [], "mine": own}
    for fm in own:
        if fm.ifc_class == "IfcSpace":
            p = polys_from(to_2d(section_segments(fm.v, fm.f, n, z0 + 50), axes))
            if p:
                d["rum"].append((fm, unary_union(p)))
            continue
        if fm.zmin < zc < fm.zmax and fm.ifc_class != "IfcDoor":  # doors are shown with a swing symbol
            p = polys_from(to_2d(section_segments(fm.v, fm.f, n, zc), axes))
            if p:
                d["snit"].append((fm, unary_union(p)))
            if fm.ifc_class == "IfcStair":
                d["under"].append((fm, projection(fm, axes)))
        elif fm.zmax <= zc and fm.zmax > z0 + 1 and fm.ifc_class not in ("IfcSlab", "IfcCovering"):
            d["under"].append((fm, projection(fm, axes)))
        elif fm.zmin >= zc and fm.ifc_class == "IfcBeam" and fm.zmin < z0 + cut_height + 3000:
            d["over"].append((fm, projection(fm, axes)))
    d["under"] = [(fm, g) for fm, g in d["under"] if g is not None]
    d["over"] = [(fm, g) for fm, g in d["over"] if g is not None]
    d["doere"] = door_symbols(own, zc)
    return d


def door_symbols(own, zc):
    """Door leaf (90° open) and swing arc as lines in model mm: [(fm, LineString leaf, LineString arc)]."""
    from shapely.geometry import LineString
    out = []
    for fm in own:
        if fm.ifc_class != "IfcDoor" or not (fm.zmin < zc < fm.zmax):
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
        free = o + x * (0 if "RIGHT" in op else W)
        leaf = h + y * W  # the leaf opens towards the door's local +y
        a0 = math.atan2(*(free - h)[::-1])
        a1 = math.atan2(*(leaf - h)[::-1])
        da = (a1 - a0 + math.pi) % (2 * math.pi) - math.pi
        arc = [h + W * np.array([math.cos(a0 + da * t / 16), math.sin(a0 + da * t / 16)]) for t in range(17)]
        out.append((fm, LineString([h, leaf]), LineString(arc)))
    return out


def plan(f, shapes, storey, cut_height, out, show_id=False, dims=False, underlay=None, cal=None):
    d = plan_data(f, shapes, storey, cut_height)
    if not d["mine"]:
        return None
    combined = [g for _, g in d["snit"]] + [g for _, g in d["rum"]]
    if not combined:
        return None
    b = unary_union(combined).bounds
    m = 1500
    bounds = (b[0] - m, b[1] - m, b[2] + m, b[3] + m)
    title = (f"{f.by_type('IfcProject')[0].Name} – plan {storey.Name} (kote {d['z0']:+.0f}, snit +{cut_height:.0f})"
             f"  {dt.date.today()}")
    fig, ax = _figure(bounds, title)
    residual = None
    if underlay:
        residual = _underlay(ax, underlay, cal)
    for fm, g in d["rum"]:
        fill_poly(ax, g, facecolor=FILL["IfcSpace"], edgecolor="none", zorder=1, alpha=0.4 if underlay else 1)
    for fm, g in d["under"]:
        fill_poly(ax, g, facecolor="none", edgecolor=_edge_colour(fm, "#555"), lw=0.5, zorder=2)
    for fm, g in d["over"]:
        fill_poly(ax, g, facecolor="none", edgecolor="#555", lw=0.6, ls=(0, (4, 3)), zorder=2)
    for fm, g in d["snit"]:
        colour = FILL.get(fm.ifc_class, "#8c8c8c")
        if fm.status == "NEW":
            colour = "#f2a3a3"
        ls = (0, (3, 2)) if fm.status == "DEMOLISH" else "solid"
        fill_poly(ax, g, facecolor="none" if underlay else colour, edgecolor=_edge_colour(fm, "#c00000" if underlay else "#000"),
                  lw=1.3 if fm.ifc_class != "IfcWindow" else 0.6, ls=ls, zorder=3)
        if show_id:
            c = g.representative_point()
            ax.text(c.x, c.y, fm.tag, fontsize=5, ha="center", va="center", color="#003c8f", zorder=6)
    for fm, leaf, arc in d["doere"]:
        ax.plot(*leaf.xy, color="#c00000" if underlay else "#000", lw=0.8, zorder=5)
        ax.plot(*arc.xy, color="#c00000" if underlay else "#000", lw=0.5, zorder=5)
    for fm, g in d["rum"]:
        c = g.representative_point()
        q = ue.get_psets(fm.ent).get("Qto_SpaceBaseQuantities", {})
        a = q.get("NetFloorArea") or g.area / 1e6
        ax.text(c.x, c.y, f"{fm.name}\n{fm.tag} · {a:.1f} m²", fontsize=7, ha="center", va="center", zorder=7,
                color="#1a1a1a", bbox=dict(boxstyle="round,pad=0.2", fc="white", ec="none", alpha=0.7))
    if dims:
        _dimensions(ax, f, d["snit"], bounds)
    _scale_bar(ax, bounds)
    _north_arrow(ax, f, bounds)
    _legend(ax, f)
    if residual is not None:
        ax.text(0.01, 0.97, f"Underlag kalibreret: største restafvigelse {residual:.0f} mm", transform=ax.transAxes,
                fontsize=7, color="blue")
    name = f"plan-{_slug(storey.Name)}" + ("-underlag" if underlay else "") + ".png"
    return _save(fig, out, name)


def _slug(s):
    t = (s or "x").lower()
    for a, b in (("æ", "ae"), ("ø", "oe"), ("å", "aa"), (" ", "-"), (".", "")):
        t = t.replace(a, b)
    return "".join(ch for ch in t if ch.isalnum() or ch == "-")


def _dimensions(ax, f, cut, bounds):
    walls = [(fm, g) for fm, g in cut if fm.ifc_class == "IfcWall"]
    if not walls:
        return
    u = unary_union([g for _, g in walls])
    x0, y0, x1, y1 = u.bounds
    for (a, b, y, lbl) in ((x0, x1, y0 - 700, x1 - x0),):
        ax.annotate("", xy=(a, y), xytext=(b, y), arrowprops=dict(arrowstyle="|-|", lw=0.6, shrinkA=0, shrinkB=0))
        ax.text((a + b) / 2, y - 120, f"{lbl:.0f}", ha="center", va="top", fontsize=7)
    xx = x0 - 700
    ax.annotate("", xy=(xx, y0), xytext=(xx, y1), arrowprops=dict(arrowstyle="|-|", lw=0.6, shrinkA=0, shrinkB=0))
    ax.text(xx - 120, (y0 + y1) / 2, f"{y1 - y0:.0f}", ha="right", va="center", fontsize=7, rotation=90)
    for fm, g in walls:
        q = ue.get_psets(fm.ent).get("Qto_WallBaseQuantities", {})
        L = q.get("Length")
        if not L:
            continue
        r = g.minimum_rotated_rectangle
        c = r.centroid
        cs = list(r.exterior.coords)
        e1 = np.subtract(cs[1], cs[0])
        e2 = np.subtract(cs[2], cs[1])
        long_edge = e1 if np.linalg.norm(e1) >= np.linalg.norm(e2) else e2
        angle = math.degrees(math.atan2(long_edge[1], long_edge[0]))
        if angle > 90:
            angle -= 180
        if angle < -90:
            angle += 180
        ax.text(c.x, c.y, f"{L:.0f}", fontsize=5.5, ha="center", va="center", rotation=angle, color="#7a0000", zorder=8,
                bbox=dict(boxstyle="square,pad=0.05", fc="white", ec="none", alpha=0.75))


# ------------------------------------------------------------------ section, elevation, 3D (painter's algorithm)
def _light(nn, se):
    nn = nn / (np.linalg.norm(nn, axis=1, keepdims=True) + 1e-12)
    light = np.array([-0.4, -0.6, 0.7])
    light = light / np.linalg.norm(light)
    return 0.55 + 0.45 * np.abs(nn @ light)


def _surface_colour(styles):
    for st in styles or []:
        candidates = [st] if st.is_a("IfcSurfaceStyle") else list(getattr(st, "Styles", None) or [])
        for ss in candidates:
            if ss.is_a("IfcSurfaceStyle"):
                for x in ss.Styles:
                    if x.is_a("IfcSurfaceStyleShading"):
                        c = x.SurfaceColour
                        return np.array([c.Red, c.Green, c.Blue])
    return None


def _style_colour(ent):
    """Colour from IfcStyledItem on the geometry, otherwise from the material's style."""
    for rep in getattr(ent.Representation, "Representations", None) or []:
        items = list(rep.Items)
        while items:
            it = items.pop()
            if it.is_a("IfcMappedItem"):
                items += list(it.MappingSource.MappedRepresentation.Items)
                continue
            for si in getattr(it, "StyledByItem", None) or []:
                c = _surface_colour(si.Styles)
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
                    c = _surface_colour(si.Styles)
                    if c is not None:
                        return c
    return None


def _colour(fm):
    import matplotlib.colors as mc
    if fm.status in STATUS_COLOUR:
        return np.array(mc.to_rgb(STATUS_COLOUR[fm.status]))
    c = _style_colour(fm.ent)
    return c if c is not None else np.array(mc.to_rgb(FILL.get(fm.ifc_class, "#bbbbbb")))


def raster(shapes, R, bounds, px_per_mm, clip=None, faded=False, ids_only=False):
    """Z-buffer: rasterises the triangles orthographically in the frame R=(u, w, d) (d = view direction).
    Returns an RGB image with outlines where the element or face orientation changes. 2× supersampling."""
    u, w, d = R
    x0, y0, x1, y1 = bounds
    ss = 2
    s = px_per_mm * ss
    W, H = int((x1 - x0) * s) + 1, int((y1 - y0) * s) + 1
    depth = np.full((H, W), np.inf)
    colour = np.ones((H, W, 3))
    eid = np.full((H, W), -1, dtype=np.int32)
    nrm = np.zeros((H, W, 3))
    for k, fm in enumerate(shapes):
        P = fm.v[fm.f]
        if clip is not None:
            P = P[(P @ clip[0] - clip[1]).max(axis=1) > 0]
        if not len(P):
            continue
        X = (P @ u - x0) * s
        Y = (y1 - P @ w) * s
        Z = P @ d
        N = np.cross(P[:, 1] - P[:, 0], P[:, 2] - P[:, 0])
        N /= np.linalg.norm(N, axis=1, keepdims=True) + 1e-12
        base = _colour(fm)
        if faded:
            base = base * 0.35 + 0.6
        light = 0.55 + 0.45 * np.abs(N @ (np.array([-0.4, -0.6, 0.7]) / np.linalg.norm([-0.4, -0.6, 0.7])))
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
            inside = (l0 >= -1e-6) & (l1 >= -1e-6) & (l2 >= -1e-6)
            z = l0 * zs[0] + l1 * zs[1] + l2 * zs[2]
            sub = depth[b0:b1 + 1, a0:a1 + 1]
            m = inside & (z < sub - 0.5)
            if not m.any():
                continue
            sub[m] = z[m]
            colour[b0:b1 + 1, a0:a1 + 1][m] = np.clip(base * light[t], 0, 1)
            eid[b0:b1 + 1, a0:a1 + 1][m] = k
            nrm[b0:b1 + 1, a0:a1 + 1][m] = N[t]
    edges = np.zeros((H, W), bool)
    depth[~np.isfinite(depth)] = 1e12
    for ax_ in (0, 1):
        de = np.diff(eid, axis=ax_) != 0
        dn = (np.abs(np.diff(nrm, axis=ax_)).sum(axis=2) > 0.3) & (np.diff(eid, axis=ax_) == 0) & \
             (np.abs(np.diff(depth, axis=ax_)) < 1e11)
        dz = (np.abs(np.diff(depth, axis=ax_)) > 60) & (np.abs(np.diff(depth, axis=ax_)) < 1e11)
        e = de | dn | dz
        if ax_ == 0:
            edges[:-1] |= e
        else:
            edges[:, :-1] |= e
    if ids_only:
        return eid
    colour[edges] = colour[edges] * 0.25
    img = colour.reshape(H // ss, ss, W // ss, ss, 3).mean(axis=(1, 3)) if H % ss == 0 and W % ss == 0 else \
        colour[: H - H % ss, : W - W % ss].reshape(H // ss, ss, W // ss, ss, 3).mean(axis=(1, 3))
    return img


def _show_raster(ax, img, bounds, zorder=1):
    x0, y0, x1, y1 = bounds
    ax.imshow(img, extent=(x0, x1, y0, y1), origin="upper", zorder=zorder, interpolation="bilinear")


def _px_per_mm(bounds):
    return min(MAX_PX / max(bounds[2] - bounds[0], 1), MAX_PX / max(bounds[3] - bounds[1], 1))


def _frame_for_side(f, side):
    """Elevation side → (u, w, d): u horizontal to the right, w up, d = view direction (towards the house)."""
    side = (side or "syd").lower()
    local_dirs = {"x+": (1, 0), "x-": (-1, 0), "y+": (0, 1), "y-": (0, -1)}
    if side in local_dirs:
        outward = np.array([*local_dirs[side], 0.0])
    else:
        ctx = next((c for c in f.by_type("IfcGeometricRepresentationContext") if c.ContextType == "Model"
                    and not c.is_a("IfcGeometricRepresentationSubContext")), None)
        tn = getattr(ctx, "TrueNorth", None) if ctx else None
        north = np.array([tn.DirectionRatios[0], tn.DirectionRatios[1], 0.0]) if tn else np.array([0, 1.0, 0])
        east = np.array([north[1], -north[0], 0.0])
        outward = {"nord": north, "syd": -north, "oest": east, "øst": east, "vest": -east}.get(side)
        if outward is None:
            raise SystemExit("--side: nord|syd|oest|vest eller x+|x-|y+|y-")
    d = -outward / np.linalg.norm(outward)
    return _right(d), np.array([0, 0, 1.0]), d


def _right(d):
    # seen from the viewer looking in direction d: right = d × z
    return np.cross(d, np.array([0, 0, 1.0]))


def elevation(f, shapes, side, out):
    shapes = [fm for fm in shapes if fm.ifc_class != "IfcSpace"]
    u, w, d = _frame_for_side(f, side)
    combined = np.vstack([fm.v for fm in shapes])
    bx = combined @ u
    bz = combined @ w
    m = 1500
    bounds = (bx.min() - m, bz.min() - m, bx.max() + m, bz.max() + m)
    fig, ax = _figure(bounds, f"{f.by_type('IfcProject')[0].Name} – facade {side}  {dt.date.today()}")
    _show_raster(ax, raster(shapes, (u, w, d), bounds, _px_per_mm(bounds)), bounds)
    _storey_lines(ax, f, bounds)
    _scale_bar(ax, bounds)
    return _save(fig, out, f"facade-{_slug(side)}.png")


def _storey_lines(ax, f, bounds):
    for st in f.by_type("IfcBuildingStorey"):
        z = float(st.Elevation or 0)
        ax.plot([bounds[0] + 200, bounds[0] + 900], [z, z], color="#1f77b4", lw=0.8)
        ax.text(bounds[0] + 950, z, f"{st.Name} {z:+.0f}", fontsize=6, va="center", color="#1f77b4")


def section(f, shapes, line, out, show_id=False):
    x1, y1, x2, y2 = map(float, line.split(","))
    p1, p2 = np.array([x1, y1, 0.0]), np.array([x2, y2, 0.0])
    u = (p2 - p1) / np.linalg.norm(p2 - p1)
    w = np.array([0, 0, 1.0])
    d = np.cross(w, u)  # view direction: to the left of the line
    n, dd = d, float(p1 @ d)
    shapes = [fm for fm in shapes if fm.ifc_class not in ("IfcSpace",)]
    combined = np.vstack([fm.v for fm in shapes])
    bu, bz = combined @ u - p1 @ u, combined @ w
    m = 1500
    bounds = (bu.min() - m, bz.min() - m, bu.max() + m, bz.max() + m)
    fig, ax = _figure(bounds, f"{f.by_type('IfcProject')[0].Name} – snit {line} (set mod venstre)  {dt.date.today()}")
    behind = [fm for fm in shapes if (fm.v @ n).max() > dd]
    ob = (bounds[0] + float(p1 @ u), bounds[1], bounds[2] + float(p1 @ u), bounds[3])
    img = raster(behind, (u, w, d), ob, _px_per_mm(bounds), clip=(n, dd), faded=True)
    _show_raster(ax, img, bounds)
    for fm in shapes:
        if (fm.v @ n).min() < dd < (fm.v @ n).max():
            segs = section_segments(fm.v, fm.f, n, dd)
            ps = polys_from([[(float(p @ u) - float(p1 @ u), float(p @ w)) for p in s] for s in segs])
            if ps:
                g = unary_union(ps)
                fill_poly(ax, g, facecolor="#333333" if fm.ifc_class != "IfcWindow" else "#bfe0f0",
                          edgecolor=_edge_colour(fm), lw=1.0, zorder=4)
                if show_id:
                    c = g.representative_point()
                    ax.text(c.x, c.y, fm.tag, fontsize=5, color="#ffd400", ha="center", va="center", zorder=6)
    _storey_lines(ax, f, bounds)
    _scale_bar(ax, bounds)
    return _save(fig, out, f"snit-{int(x1)}-{int(y1)}-{int(x2)}-{int(y2)}.png")


def three_d(f, shapes, view_from, out):
    shapes = [fm for fm in shapes if fm.ifc_class not in ("IfcSpace",)]
    direction = {"sv": (-1, -1), "so": (1, -1), "nv": (-1, 1), "no": (1, 1), "s": (0, -1), "n": (0, 1), "v": (-1, 0),
            "o": (1, 0)}.get((view_from or "sv").lower(), (-1, -1))
    viewer = np.array([direction[0], direction[1], 0.9])
    d = -viewer / np.linalg.norm(viewer)
    u = np.cross(d, np.array([0, 0, 1.0]))
    u /= np.linalg.norm(u)
    w = np.cross(u, d)
    combined = np.vstack([fm.v for fm in shapes])
    bu, bw = combined @ u, combined @ w
    m = 1000
    bounds = (bu.min() - m, bw.min() - m, bu.max() + m, bw.max() + m)
    fig, ax = _figure(bounds, f"{f.by_type('IfcProject')[0].Name} – 3D fra {view_from}  {dt.date.today()}")
    _show_raster(ax, raster(shapes, (u, w, d), bounds, _px_per_mm(bounds)), bounds)
    return _save(fig, out, f"3d-{_slug(view_from)}.png")


# ------------------------------------------------------------------ entry point
def draw(ifc, what, storey=None, line=None, side=None, view_from="sv", underlay=None, cal=None, show_id=False, dims=False,
         out=None, cut_height=1000.0):
    f = ifcopenshell.open(str(ifc))
    out = pathlib.Path(out) if out else pathlib.Path(ifc).parent / "tegninger"
    shapes = fetch_shapes(f)
    files = []
    storeys = sorted(f.by_type("IfcBuildingStorey"), key=lambda s: float(s.Elevation or 0))
    if what in ("plan", "alle"):
        selected = storeys
        if storey:
            selected = [s for s in storeys if s.Name == storey or s.GlobalId == storey or _slug(s.Name) == _slug(storey)
                     or (s.Name or "").lower().startswith(storey.lower())]
            if not selected:
                raise SystemExit(f"Etage '{storey}' findes ikke: {', '.join(s.Name for s in storeys)}")
        if underlay and not cal:
            raise SystemExit("--underlag kræver --kal")
        for st in selected:
            p = plan(f, shapes, st, cut_height, out, show_id, dims, underlay if storey else None, cal)
            if p:
                files.append(p)
    if what == "snit":
        if not line:
            raise SystemExit("snit kræver --linje x1,y1,x2,y2 (mm, lokale koordinater; der ses mod venstre)")
        files.append(section(f, shapes, line, out, show_id))
    if what == "facade":
        files.append(elevation(f, shapes, side or "syd", out))
    if what == "alle":
        has_north = any(getattr(c, "TrueNorth", None) for c in f.by_type("IfcGeometricRepresentationContext"))
        for s in (("syd", "nord", "oest", "vest") if has_north else ("y-", "y+", "x+", "x-")):
            files.append(elevation(f, shapes, s, out))
    if what in ("3d", "alle"):
        files.append(three_d(f, shapes, view_from, out))
    return files
