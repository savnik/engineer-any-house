"""Compares a source drawing with the model in the drawing's own pixel frame.

For each view in afkodning.yaml:
  original.png  – the crop of the source drawing (bbox)
  model.png     – the model drawn in the same pixel frame (via the calibration): plan cut, section or elevation
  overlay.png   – the source drawing lightened, with the model in red and decoded points in green
  fliser/       – the same three side by side in tiles (for thorough high-resolution review)
  fliser.md     – which tiles to review: empty tiles are skipped, and with --previous
                  (the previous round's comparison folder) only tiles where the model changed or auto has findings
  auto.md/json  – automatic comparison of all decoded dimensions, rooms, openings, wall thicknesses and levels

The automatic part is deterministic; the visual review is done by bim-sammenligner.
"""
import json
import math
import pathlib
import re

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import ifcopenshell  # noqa: E402
import ifcopenshell.util.element as ue  # noqa: E402
from matplotlib.transforms import Affine2D  # noqa: E402
from PIL import Image, ImageDraw, ImageFont  # noqa: E402
from shapely import affinity  # noqa: E402
from shapely.geometry import Point  # noqa: E402
from shapely.ops import unary_union  # noqa: E402

from . import decode  # noqa: E402
from .geometry import fetch_shapes  # noqa: E402
from .draw import (_frame_for_side, fill_poly, plan_data, polys_from, projection, raster,  # noqa: E402
                   section_segments)

TILE = 760
INK = 160         # grey level below this value counts as ink
EMPTY_SHARE = 0.002   # a tile with less ink than this in both original and model is empty
CHANGED_PX = 25     # this many changed model pixels (after noise filter) make a tile changed
SEARCH = 150.0  # mm – search distance from a dimension point to a model face


# ------------------------------------------------------------------ transformations
def _px_matrix(M, x0, y0):
    """Model → crop pixel as a shapely matrix [a, b, d, e, xoff, yoff] and 3×3."""
    Li = np.linalg.inv(M[:, :2])
    t = Li @ M[:, 2]
    a, b, d, e = Li[0, 0], Li[0, 1], Li[1, 0], Li[1, 1]
    xo, yo = -t[0] - x0, -t[1] - y0
    return [a, b, d, e, xo, yo], np.array([[a, b, xo], [d, e, yo], [0, 0, 1.0]])


def _storey(f, sidecar, eid):
    name = ((sidecar or {}).get("etager") or {}).get(str(eid), {}).get("navn")
    for st in f.by_type("IfcBuildingStorey"):
        if st.Name == name or st.Name == str(eid) or (st.Name or "").lower().startswith(str(eid).lower()):
            return st
    raise SystemExit(f"Etagen '{eid}' findes ikke i modellen ({', '.join(s.Name for s in f.by_type('IfcBuildingStorey'))})")


def _norm(s):
    return re.sub(r"[^a-z0-9æøå]", "", (s or "").lower())


# ------------------------------------------------------------------ model geometry per view type (in the view's 2D coordinates)
def _view_geometry(f, shapes, v, sidecar, cut_height):
    """Returns a dict with 'linjer' (filled cuts), 'tynde', 'rum', 'doere', 'raster' and 'kanter' (for dimension checks)."""
    g = {"snit": [], "tynde": [], "rum": [], "doere": [], "raster": None, "aabninger": [], "vaegge": []}
    if v["type"] == "plan":
        st = _storey(f, sidecar, v["etage"])
        pd = plan_data(f, shapes, st, float(v.get("snithoejde", cut_height)))
        g["snit"] = pd["snit"]
        g["tynde"] = pd["under"]
        g["rum"] = pd["rum"]
        g["doere"] = [(fm, leaf, arc) for fm, leaf, arc in pd["doere"]]
        axes = (np.array([1.0, 0, 0]), np.array([0, 1.0, 0]))
        for fm in pd["mine"]:
            if fm.ifc_class in ("IfcWindow", "IfcDoor"):
                proj = projection(fm, axes)
                if proj is not None:
                    g["aabninger"].append((fm, proj))
        g["vaegge"] = [(fm, p) for fm, p in pd["snit"] if fm.ifc_class == "IfcWall"]
        g["kanter"] = [p for fm, p in pd["snit"] if fm.ifc_class in ("IfcWall", "IfcColumn", "IfcChimney")]
        g["zfri"] = None
        return g
    solids = [fm for fm in shapes if fm.ifc_class != "IfcSpace"]
    if v["type"] == "facade":
        u, w, d = _frame_for_side(f, v["side"])
        axes = (u, w)
        g["ramme"] = (u, w, d)
        visible = _visible(solids, (u, w, d))
        for k, fm in enumerate(solids):
            proj = projection(fm, axes)
            if proj is not None:
                g["tynde"].append((fm, proj))
                if fm.ifc_class in ("IfcWindow", "IfcDoor") and k in visible:
                    g["aabninger"].append((fm, proj))
        g["kanter"] = [p for _, p in g["tynde"]]
        g["raster_former"] = solids
        return g
    # section
    x1, y1, x2, y2 = map(float, v["linje"])
    p1, p2 = np.array([x1, y1, 0.0]), np.array([x2, y2, 0.0])
    u = (p2 - p1) / np.linalg.norm(p2 - p1)
    w = np.array([0, 0, 1.0])
    d = np.cross(w, u)
    n, dd = d, float(p1 @ d)
    off = float(p1 @ u)
    g["ramme"] = (u, w, d)
    g["snit_klip"] = (n, dd)
    g["u_off"] = off
    for fm in solids:
        if (fm.v @ n).min() < dd < (fm.v @ n).max():
            segs = section_segments(fm.v, fm.f, n, dd)
            ps = polys_from([[(float(p @ u) - off, float(p @ w)) for p in s] for s in segs])
            if ps:
                g["snit"].append((fm, unary_union(ps)))
    g["kanter"] = [p for _, p in g["snit"]]
    g["raster_former"] = [fm for fm in solids if (fm.v @ n).max() > dd]
    return g


def _visible(shapes, R):
    """Indices of the elements visible in a quick z-buffer rendering (approx. 25 mm/px)."""
    u, w, d = R
    stacked = np.vstack([fm.v for fm in shapes])
    bb = (float((stacked @ u).min()), float((stacked @ w).min()), float((stacked @ u).max()), float((stacked @ w).max()))
    eid = raster(shapes, R, bb, 0.04, ids_only=True)
    return {int(k) for k, n in zip(*np.unique(eid[eid >= 0], return_counts=True)) if n >= 8}


# ------------------------------------------------------------------ drawing in the pixel frame
def _draw(ax, g, mat, M3, colour, lw_cut=1.4, fill=None, labels=True):
    T = lambda geom: affinity.affine_transform(geom, mat)  # noqa: E731
    for fm, p in g["tynde"]:
        fill_poly(ax, T(p), facecolor="none", edgecolor=colour, lw=0.4, zorder=3)
    for fm, p in g["snit"]:
        fill_poly(ax, T(p), facecolor=fill or "none", edgecolor=colour, lw=lw_cut if fm.ifc_class != "IfcWindow" else 0.6,
                  zorder=4)
    for fm, leaf, arc in g["doere"]:
        for ln in (leaf, arc):
            x, y = T(ln).xy
            ax.plot(x, y, color=colour, lw=0.7, zorder=5)
    if labels:
        for fm, p in g["rum"]:
            c = T(p).representative_point()
            q = ue.get_psets(fm.ent).get("Qto_SpaceBaseQuantities", {})
            ax.text(c.x, c.y, f"{fm.name}\n{(q.get('NetFloorArea') or p.area / 1e6):.1f} m²", color=colour, fontsize=7,
                    ha="center", va="center", zorder=6)


def _figure_px(W, H):
    fig = plt.figure(figsize=(W / 100, H / 100), dpi=100)
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_xlim(0, W)
    ax.set_ylim(H, 0)
    ax.axis("off")
    return fig, ax


def _raster_px(ax, f, g, mat3, W, H, faded):
    """Raster image (elevation/section behind) in the model frame, placed in the pixel frame by an affine transform."""
    shapes = g.get("raster_former")
    if not shapes:
        return
    u, w, d = g["ramme"]
    stacked = np.vstack([fm.v for fm in shapes])
    off = g.get("u_off", 0.0)
    b = (float((stacked @ u).min()) - off, float((stacked @ w).min()), float((stacked @ u).max()) - off, float((stacked @ w).max()))
    bb = (b[0] + off, b[1], b[2] + off, b[3])
    px_per_mm = min(2400 / max(bb[2] - bb[0], 1), 2400 / max(bb[3] - bb[1], 1))
    img = raster(shapes, (u, w, d), bb, px_per_mm, clip=g.get("snit_klip"), faded=faded)
    trans = Affine2D(mat3) + ax.transData
    ax.imshow(img, extent=(b[0], b[2], b[1], b[3]), origin="upper", transform=trans, zorder=1, interpolation="bilinear")


# ------------------------------------------------------------------ automatic comparisons
def _edge_coords(polys, axis):
    """Positions of model faces perpendicular to the dimension direction: axis 0 → x of vertical edges, 1 → y of horizontal ones."""
    out = []
    for p in polys:
        for g in getattr(p, "geoms", [p]):
            if g.geom_type != "Polygon":
                continue
            for ring in [g.exterior] + list(g.interiors):
                c = np.array(ring.coords)
                for a, b in zip(c[:-1], c[1:]):
                    dx, dy = abs(b[0] - a[0]), abs(b[1] - a[1])
                    if axis == 0 and dx < 0.05 * max(dy, 1) and dy > 20:
                        out.append(((a[0] + b[0]) / 2, min(a[1], b[1]), max(a[1], b[1])))
                    if axis == 1 and dy < 0.05 * max(dx, 1) and dx > 20:
                        out.append(((a[1] + b[1]) / 2, min(a[0], b[0]), max(a[0], b[0])))
    return out


def _nearest(edges, value, across=None):
    """Nearest model face to the dimension point. With across (the point's other coordinate) the face must also lie
    level with the point – the point sits at the building element (foot of the extension line). Without across: only the position along the dimension."""
    candidates = [e for e in edges if abs(e[0] - value) <= SEARCH and
            (across is None or e[1] - SEARCH <= across <= e[2] + SEARCH)]
    if not candidates:
        return None
    return min(candidates, key=lambda e: abs(e[0] - value))[0]


def _auto(f, v, g, M, sidecar):
    rows = []
    edges = g.get("kanter") or []
    kx, ky = _edge_coords(edges, 0), _edge_coords(edges, 1)
    boundary = unary_union([p.boundary for p in edges]) if edges else None
    for m in v.get("maal") or []:
        a, b = decode.to_model(M, m["fra"]), decode.to_model(M, m["til"])
        r = m.get("retning", "fri")
        drawn = decode.dim_in_drawing(M, m)
        tol = decode.tol_mm(m["vaerdi"])
        if r in ("x", "u", "y", "z"):
            axis = 0 if r in ("x", "u") else 1
            kk = kx if axis == 0 else ky
            on_line = bool(m.get("paa_maalelinje"))
            ma = _nearest(kk, a[axis], None if on_line else a[1 - axis])
            mb = _nearest(kk, b[axis], None if on_line else b[1 - axis])
            model = abs(mb - ma) if ma is not None and mb is not None else None
        else:
            if boundary is None:
                model = None
            else:
                from shapely.ops import nearest_points
                pa = nearest_points(boundary, Point(a))[0]
                pb = nearest_points(boundary, Point(b))[0]
                model = pa.distance(pb) if pa.distance(Point(a)) <= SEARCH and pb.distance(Point(b)) <= SEARCH else None
        if model is None:
            status = "MANGLER"
            note = ("ingen modelflade inden for 150 mm af et målpunkt"
                    + ("" if m.get("paa_maalelinje") else " (ud for punktet – sæt paa_maalelinje: true, hvis punkterne sidder på målelinjen)"))
        else:
            dev = model - m["vaerdi"]
            status = "OK" if abs(dev) <= tol else "AFVIGER"
            note = f"{dev:+.0f} mm"
        if abs(drawn - m["vaerdi"]) > tol:
            note += f"; NB tegningen selv viser {drawn:.0f} mm – tjek afkodningen"
        rows.append({"art": "mål", "id": m.get("id"), "tekst": m.get("tekst"), "original": m["vaerdi"],
                     "model": None if model is None else round(model), "status": status, "note": note,
                     "px": [m["fra"], m["til"]]})
    if v["type"] == "plan":
        for r in v.get("rum") or []:
            P = Point(decode.to_model(M, r["punkt"]))
            hit = next(((fm, p) for fm, p in g["rum"] if p.buffer(1).contains(P)), None)
            if not hit:
                rows.append({"art": "rum", "id": r.get("navn"), "original": r.get("navn"), "model": None,
                             "status": "MANGLER", "note": "intet modelrum ved punktet", "px": [r["punkt"]]})
                continue
            fm, p = hit
            q = ue.get_psets(fm.ent).get("Qto_SpaceBaseQuantities", {})
            area = q.get("NetFloorArea") or p.area / 1e6
            name_ok = not r.get("navn") or _norm(r["navn"]) in _norm(fm.name) or _norm(fm.name) in _norm(r["navn"])
            status, note = "OK", f"{fm.tag} {fm.name} {area:.1f} m²"
            if not name_ok:
                status, note = "AFVIGER", f"navn: model '{fm.name}'"
            if r.get("areal"):
                dev = area - float(r["areal"])
                if abs(dev) > max(0.5, 0.05 * float(r["areal"])):
                    status, note = "AFVIGER", note + f"; areal {area:.1f} mod {r['areal']} m² ({dev:+.1f})"
            rows.append({"art": "rum", "id": r.get("navn"), "original": r.get("navn"), "model": fm.name,
                         "status": status, "note": note, "px": [r["punkt"]]})
    used = set()
    for a in v.get("aabninger") or []:
        P = Point(decode.to_model(M, a["punkt"]))
        candidates = sorted(((p.distance(P), fm) for fm, p in g["aabninger"]), key=lambda x: x[0])
        if not candidates or candidates[0][0] > 400:
            rows.append({"art": "åbning", "id": a.get("id") or a.get("tekst"), "original": a["type"], "model": None,
                         "status": "MANGLER", "note": "ingen dør/vindue i modellen ved punktet", "px": [a["punkt"]]})
            continue
        dist, fm = candidates[0]
        used.add(fm.id)
        kind = {"IfcWindow": "vindue", "IfcDoor": "doer"}.get(fm.ifc_class, fm.ifc_class)
        status, note = "OK", f"{fm.tag}"
        if a["type"] in ("vindue", "doer") and kind != a["type"]:
            status, note = "AFVIGER", f"{fm.tag} er {kind}"
        if a.get("bredde") and getattr(fm.ent, "OverallWidth", None):
            dev = float(fm.ent.OverallWidth) - float(a["bredde"])
            if abs(dev) > 50:
                status, note = "AFVIGER", note + f"; bredde {fm.ent.OverallWidth:.0f} mod {a['bredde']} ({dev:+.0f})"
        rows.append({"art": "åbning", "id": a.get("id") or a.get("tekst"), "original": a["type"], "model": fm.tag,
                     "status": status, "note": note, "px": [a["punkt"]]})
    if v.get("aabninger") is not None:
        x0, y0, x1, y1 = v["bbox"]
        corners = [decode.to_model(M, (x, y)) for x, y in ((x0, y0), (x1, y0), (x1, y1), (x0, y1))]
        from shapely.geometry import Polygon as _P
        frame = _P(corners)
        for fm, p in g["aabninger"]:
            if fm.id not in used and frame.contains(p.centroid):
                rows.append({"art": "åbning", "id": fm.tag, "original": None, "model": fm.tag, "status": "EKSTRA",
                             "note": "i modellen, men ikke afkodet på tegningen", "px": []})
    for w in v.get("vaegge") or []:
        if not w.get("tykkelse"):
            continue
        P = Point(decode.to_model(M, w["punkt"]))
        candidates = sorted(((p.distance(P), fm, p) for fm, p in g.get("vaegge") or []), key=lambda x: x[0])
        if not candidates or candidates[0][0] > 250:
            rows.append({"art": "væg", "id": w.get("tekst"), "original": w["tykkelse"], "model": None, "status": "MANGLER",
                         "note": "ingen væg ved punktet", "px": [w["punkt"]]})
            continue
        _, fm, p = candidates[0]
        thickness = ue.get_psets(fm.ent).get("Qto_WallBaseQuantities", {}).get("Width")
        if not thickness:
            r_ = p.minimum_rotated_rectangle
            cs = np.array(r_.exterior.coords)
            thickness = min(np.linalg.norm(cs[1] - cs[0]), np.linalg.norm(cs[2] - cs[1]))
        dev = float(thickness) - float(w["tykkelse"])
        rows.append({"art": "væg", "id": w.get("tekst") or fm.tag, "original": w["tykkelse"], "model": round(float(thickness)),
                     "status": "OK" if abs(dev) <= 20 else "AFVIGER", "note": f"{fm.tag} ({dev:+.0f} mm)",
                     "px": [w["punkt"]]})
    mc = f.by_type("IfcMapConversion")
    for k in v.get("koter") or []:
        if str(k.get("datum", "")).lower().startswith("relativ"):
            storeys = [(float(st.Elevation or 0) / 1000, st.Name) for st in f.by_type("IfcBuildingStorey")]
            level_m = float(k["kote"])
            nearest = min(storeys, key=lambda e: abs(e[0] - level_m))
            dev = (nearest[0] - level_m) * 1000
            rows.append({"art": "kote", "id": k.get("beskrivelse"), "original": level_m, "model": round(nearest[0], 3),
                         "status": "OK" if abs(dev) <= 30 else "AFVIGER",
                         "note": f"relativ til ±0; nærmeste etage {nearest[1]} ({dev:+.0f} mm)",
                         "px": [k["punkt"]] if k.get("punkt") else []})
            continue
        if not mc:
            rows.append({"art": "kote", "id": k.get("beskrivelse"), "original": k.get("kote"), "model": None,
                         "status": "IKKE SAMMENLIGNET", "note": "modellen har ingen georeference (kote for ±0)", "px": []})
            continue
        h0 = float(mc[0].OrthogonalHeight or 0)
        storeys = [(h0 + float(st.Elevation or 0) / 1000, st.Name) for st in f.by_type("IfcBuildingStorey")]
        level_m = float(k["kote"])
        nearest = min(storeys, key=lambda e: abs(e[0] - level_m))
        dev = (nearest[0] - level_m) * 1000
        rows.append({"art": "kote", "id": k.get("beskrivelse"), "original": level_m, "model": round(nearest[0], 3),
                     "status": "OK" if abs(dev) <= 30 else "AFVIGER", "note": f"nærmeste etage {nearest[1]} ({dev:+.0f} mm)",
                     "px": [k["punkt"]] if k.get("punkt") else []})
    return rows


# ------------------------------------------------------------------ tiles
def _tiles(orig, model, overlay, folder, view_id, x0, y0):
    """Writes the tiles; returns (file, box) per tile. The box is in the view's pixel frame."""
    folder.mkdir(parents=True, exist_ok=True)
    for old in folder.glob("flise-*.png"):
        old.unlink()
    W, H = orig.size
    nx, ny = max(1, math.ceil(W / TILE)), max(1, math.ceil(H / TILE))
    tw, th = math.ceil(W / nx), math.ceil(H / ny)
    try:
        font = ImageFont.load_default(size=14)
    except TypeError:
        font = ImageFont.load_default()
    files = []
    for r in range(ny):
        for c in range(nx):
            box = (c * tw, r * th, min(W, (c + 1) * tw), min(H, (r + 1) * th))
            parts = [im.crop(box) for im in (orig, model, overlay)]
            w_, h_ = parts[0].size
            sheet = Image.new("RGB", (3 * w_ + 20, h_ + 24), "white")
            for i, im in enumerate(parts):
                sheet.paste(im.convert("RGB"), (i * (w_ + 10), 24))
            dr = ImageDraw.Draw(sheet)
            dr.text((4, 4), f"{view_id} r{r + 1}c{c + 1}  px x {box[0] + x0}-{box[2] + x0}, y {box[1] + y0}-{box[3] + y0}"
                            "   |  original  |  model  |  overlay", fill=(0, 0, 0), font=font)
            tile_file = folder / f"flise-r{r + 1}c{c + 1}.png"
            sheet.save(tile_file)
            files.append((tile_file, box))
    return files


def _ink(img):
    return np.asarray(img.convert("L")) < INK


def _changed(new, old):
    """Pixel mask of changed ink in the model; None if the previous model cannot be compared."""
    if old is None or old.size != new.size:
        return None
    d = _ink(new) ^ _ink(old)
    # single pixels (antialiasing) do not count: require a changed neighbour horizontally or vertically
    neighbour = np.zeros_like(d)
    neighbour[:, 1:] |= d[:, :-1]
    neighbour[:, :-1] |= d[:, 1:]
    neighbour[1:, :] |= d[:-1, :]
    neighbour[:-1, :] |= d[1:, :]
    return d & neighbour


def _tile_selection(tiles, orig, model_img, old_model, rows, x0, y0):
    """Decides per tile whether it must be reviewed. Returns rows for fliser.md."""
    o, m = _ink(orig), _ink(model_img)
    changed = _changed(model_img, old_model)
    selection = []
    for tile_file, (a, b, c, d) in tiles:
        area = max(1, (c - a) * (d - b))
        empty = o[b:d, a:c].sum() / area < EMPTY_SHARE and m[b:d, a:c].sum() / area < EMPTY_SHARE
        findings = [f"A{i + 1}" for i, rw in enumerate(rows) if rw["status"] != "OK"
                and any(a <= p[0] - x0 < c and b <= p[1] - y0 < d for p in rw["px"])]
        n_changed = None if changed is None else int(changed[b:d, a:c].sum())
        if empty:
            reason, review = "tom", False
        elif findings:
            reason, review = "auto-fund", True
        elif n_changed is None:
            reason, review = "første runde" if old_model is None else "forrige model kan ikke sammenlignes", True
        elif n_changed >= CHANGED_PX:
            reason, review = "model ændret", True
        else:
            reason, review = "uændret", False
        selection.append({"flise": tile_file.stem.removeprefix("flise-"), "fil": tile_file.name, "gennemgaa": review,
                     "grund": reason, "aendrede_px": n_changed, "fund": findings})
    return selection


def _tiles_md(selection, view_id, previous):
    g = [v for v in selection if v["gennemgaa"]]
    md = [f"# Fliser – {view_id}",
           f"Gennemgå {len(g)} af {len(selection)} fliser" + (f" (sammenlignet med {previous})" if previous else "") + ".",
           "Tomme fliser har hverken streger i originalen eller i modellen. Uændrede fliser er dækket af forrige "
           "runde – men læs en uændret flise alligevel, hvis en åben afvigelse fra forrige runde ligger i den.", "",
           "| Flise | Gennemgå | Grund | Ændrede px | Auto-fund |", "|---|---|---|---|---|"]
    for v in selection:
        md.append(f"| {v['flise']} | {'ja' if v['gennemgaa'] else 'nej'} | {v['grund']} | "
                   f"{'–' if v['aendrede_px'] is None else v['aendrede_px']} | {', '.join(v['fund']) or '–'} |")
    return "\n".join(md) + "\n"


# ------------------------------------------------------------------ entry point
def compare(ifc, decoding_path, view=None, out=None, cut_height=1000.0, previous=None):
    ifc = pathlib.Path(ifc)
    d = decode.load(decoding_path)
    f = ifcopenshell.open(str(ifc))
    sidecar_path = ifc.with_suffix(".byg.json")
    sidecar = json.loads(sidecar_path.read_text(encoding="utf-8")) if sidecar_path.exists() else None
    shapes = fetch_shapes(f)
    source_image = Image.open(d["kilde"]["_billede"]).convert("RGB")
    out = pathlib.Path(out) if out else ifc.parent.parent / "sammenligning" / d["kilde"]["id"]
    previous = pathlib.Path(previous) if previous else None
    if previous and previous.resolve() == out.resolve():
        print("--previous skal være en anden mappe end --out (forrige rundes sammenligning)")
        return 1
    total = {}
    for v in d["visninger"]:
        if v["type"] not in ("plan", "snit", "facade") or (view and v["id"] != view):
            continue
        M, residual, sx, sy = decode.calibrate(v)
        x0, y0, x1, y1 = map(int, v["bbox"])
        orig = source_image.crop((x0, y0, x1, y1))
        W, H = orig.size
        mat, mat3 = _px_matrix(M, x0, y0)
        g = _view_geometry(f, shapes, v, sidecar, cut_height)
        folder = out / v["id"]
        folder.mkdir(parents=True, exist_ok=True)
        # model
        fig, ax = _figure_px(W, H)
        if v["type"] != "plan":
            _raster_px(ax, f, g, mat3, W, H, faded=v["type"] == "snit")
        _draw(ax, g, mat, mat3, "#000000", fill="#9a9a9a" if v["type"] != "facade" else None)
        fig.savefig(folder / "model.png", dpi=100, facecolor="white")
        plt.close(fig)
        model_img = Image.open(folder / "model.png").convert("RGB").resize((W, H))
        # overlay
        fig, ax = _figure_px(W, H)
        bg = np.asarray(orig.convert("L"), dtype=float) / 255.0
        ax.imshow(0.45 + 0.55 * bg, cmap="gray", vmin=0, vmax=1, extent=(0, W, H, 0), zorder=0)
        _draw(ax, g, mat, mat3, "#e00000", lw_cut=1.0, labels=False)
        rows = _auto(f, v, g, M, sidecar)
        for i, rw in enumerate(rows):
            for p in rw["px"]:
                px, py = p[0] - x0, p[1] - y0
                colour = {"OK": "#10a010", "AFVIGER": "#ff7f00", "MANGLER": "#ff00ff"}.get(rw["status"], "#808080")
                ax.plot([px], [py], marker="o", ms=6, mfc="none", mec=colour, mew=1.5, zorder=8)
            if rw["status"] in ("AFVIGER", "MANGLER") and rw["px"]:
                px, py = rw["px"][0][0] - x0, rw["px"][0][1] - y0
                ax.text(px + 6, py - 6, f"A{i + 1}", color="#ff7f00", fontsize=8, weight="bold", zorder=9)
        for kp in v["kal"]:
            ax.plot([kp["px"][0] - x0], [kp["px"][1] - y0], marker="+", color="blue", ms=12, zorder=9)
        fig.savefig(folder / "overlay.png", dpi=100, facecolor="white")
        plt.close(fig)
        overlay_img = Image.open(folder / "overlay.png").convert("RGB").resize((W, H))
        orig.save(folder / "original.png")
        tiles = _tiles(orig, model_img, overlay_img, folder / "fliser", v["id"], x0, y0)
        old_path = previous / v["id"] / "model.png" if previous else None
        old = Image.open(old_path).convert("RGB") if old_path and old_path.exists() else None
        selection = _tile_selection(tiles, orig, model_img, old, rows, x0, y0)
        (folder / "fliser.md").write_text(_tiles_md(selection, v["id"], previous), encoding="utf-8")
        (folder / "fliser.json").write_text(json.dumps(selection, ensure_ascii=False, indent=1), encoding="utf-8")
        n_g = sum(x["gennemgaa"] for x in selection)
        # table
        counts = {}
        for rw in rows:
            counts[rw["status"]] = counts.get(rw["status"], 0) + 1
        total[v["id"]] = counts
        md = [f"# Automatisk sammenligning – {d['kilde']['id']} {v['id']} ({v['type']} {v.get('etage') or v.get('side') or ''})",
              f"Model: {ifc.name} · kalibrering: største rest {max(residual):.0f} mm, skala X {sx:.2f} · Y {sy:.2f} mm/px",
              "Status: " + ", ".join(f"{k} {n}" for k, n in sorted(counts.items())), "",
              "| # | Art | Id/tekst | Tegning | Model | Status | Note |", "|---|---|---|---|---|---|---|"]
        for i, rw in enumerate(rows):
            md.append(f"| A{i + 1} | {rw['art']} | {rw.get('id') or rw.get('tekst') or ''} | {rw['original']} | "
                       f"{rw['model'] if rw['model'] is not None else '–'} | {rw['status']} | {rw['note']} |")
        md += ["", "Billeder: original.png · model.png · overlay.png · fliser/ (" + str(len(tiles))
               + f", gennemgå {n_g} – se fliser.md)",
               "Grønne cirkler = OK · orange = AFVIGER · magenta = MANGLER · blå kryds = kalibreringspunkter"]
        (folder / "auto.md").write_text("\n".join(md) + "\n", encoding="utf-8")
        (folder / "auto.json").write_text(json.dumps(rows, ensure_ascii=False, indent=1, default=float), encoding="utf-8")
        print(f"SAMMENLIGN {d['kilde']['id']} {v['id']} ({v['type']}): " + ", ".join(f"{k} {n}" for k, n in sorted(counts.items()))
              + f" → {folder}")
        for i, rw in enumerate(rows):
            if rw["status"] not in ("OK",) and i < 200:
                print(f"  A{i + 1} {rw['status']} {rw['art']} {rw.get('id') or ''}: tegning {rw['original']} · model "
                      f"{rw['model'] if rw['model'] is not None else '–'} · {rw['note']}")
        print(f"  billeder: {folder}/overlay.png · {len(tiles)} fliser i {folder / 'fliser'}, gennemgå {n_g} "
              f"({', '.join(x['flise'] for x in selection if x['gennemgaa']) or 'ingen'}) – se fliser.md")
    if not total:
        print("Ingen plan/snit/facade-visninger at sammenligne" + (f" med id {view}" if view else ""))
        return 1
    return 0

