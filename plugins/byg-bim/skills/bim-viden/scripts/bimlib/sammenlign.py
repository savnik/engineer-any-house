"""Sammenligning af kildetegning og model i tegningens egen pixelramme.

For hver visning i afkodning.yaml:
  original.png  – udsnittet af kildetegningen (bbox)
  model.png     – modellen tegnet i samme pixelramme (via kalibreringen): plan i snit, snit eller facade
  overlay.png   – kildetegningen lysnet med modellen i rødt og afkodede punkter i grønt
  fliser/       – samme tre side om side i fliser (til grundig gennemgang i høj opløsning)
  auto.md/json  – automatisk sammenligning af alle afkodede mål, rum, åbninger, vægtykkelser og koter

Den automatiske del er deterministisk; den visuelle gennemgang laves af bim-sammenligner.
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

from . import afkod  # noqa: E402
from .geometri import hent  # noqa: E402
from .tegn import (_ramme_for_side, fyld_poly, plan_data, polys_af, projektion, raster,  # noqa: E402
                   snit_polygoner)

FLISE = 760
SOEG = 150.0  # mm – søgeafstand fra et målpunkt til en modelflade


# ------------------------------------------------------------------ transformationer
def _px_matrix(M, x0, y0):
    """Model → crop-pixel som shapely-matrix [a, b, d, e, xoff, yoff] og 3×3."""
    Li = np.linalg.inv(M[:, :2])
    t = Li @ M[:, 2]
    a, b, d, e = Li[0, 0], Li[0, 1], Li[1, 0], Li[1, 1]
    xo, yo = -t[0] - x0, -t[1] - y0
    return [a, b, d, e, xo, yo], np.array([[a, b, xo], [d, e, yo], [0, 0, 1.0]])


def _etage(f, sidevogn, eid):
    navn = ((sidevogn or {}).get("etager") or {}).get(str(eid), {}).get("navn")
    for st in f.by_type("IfcBuildingStorey"):
        if st.Name == navn or st.Name == str(eid) or (st.Name or "").lower().startswith(str(eid).lower()):
            return st
    raise SystemExit(f"Etagen '{eid}' findes ikke i modellen ({', '.join(s.Name for s in f.by_type('IfcBuildingStorey'))})")


def _norm(s):
    return re.sub(r"[^a-z0-9æøå]", "", (s or "").lower())


# ------------------------------------------------------------------ modelgeometri pr. visningstype (i visningens 2D-koordinater)
def _visningsgeometri(f, former, v, sidevogn, snithoejde):
    """Returnerer dict med 'linjer' (fyldte snit), 'tynde', 'rum', 'doere', 'raster' og 'kanter' (til målkontrol)."""
    g = {"snit": [], "tynde": [], "rum": [], "doere": [], "raster": None, "aabninger": [], "vaegge": []}
    if v["type"] == "plan":
        st = _etage(f, sidevogn, v["etage"])
        pd = plan_data(f, former, st, float(v.get("snithoejde", snithoejde)))
        g["snit"] = pd["snit"]
        g["tynde"] = pd["under"]
        g["rum"] = pd["rum"]
        g["doere"] = [(fm, blad, bue) for fm, blad, bue in pd["doere"]]
        akser = (np.array([1.0, 0, 0]), np.array([0, 1.0, 0]))
        for fm in pd["mine"]:
            if fm.klasse in ("IfcWindow", "IfcDoor"):
                pr = projektion(fm, akser)
                if pr is not None:
                    g["aabninger"].append((fm, pr))
        g["vaegge"] = [(fm, p) for fm, p in pd["snit"] if fm.klasse == "IfcWall"]
        g["kanter"] = [p for fm, p in pd["snit"] if fm.klasse in ("IfcWall", "IfcColumn", "IfcChimney")]
        g["zfri"] = None
        return g
    ude = [fm for fm in former if fm.klasse != "IfcSpace"]
    if v["type"] == "facade":
        u, w, d = _ramme_for_side(f, v["side"])
        akser = (u, w)
        g["ramme"] = (u, w, d)
        synlig = _synlige(ude, (u, w, d))
        for k, fm in enumerate(ude):
            pr = projektion(fm, akser)
            if pr is not None:
                g["tynde"].append((fm, pr))
                if fm.klasse in ("IfcWindow", "IfcDoor") and k in synlig:
                    g["aabninger"].append((fm, pr))
        g["kanter"] = [p for _, p in g["tynde"]]
        g["raster_former"] = ude
        return g
    # snit
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
    for fm in ude:
        if (fm.v @ n).min() < dd < (fm.v @ n).max():
            segs = snit_polygoner(fm.v, fm.f, n, dd)
            ps = polys_af([[(float(p @ u) - off, float(p @ w)) for p in s] for s in segs])
            if ps:
                g["snit"].append((fm, unary_union(ps)))
    g["kanter"] = [p for _, p in g["snit"]]
    g["raster_former"] = [fm for fm in ude if (fm.v @ n).max() > dd]
    return g


def _synlige(former, R):
    """Indeks på de elementer, der kan ses i en hurtig z-buffer-rendering (ca. 25 mm/px)."""
    u, w, d = R
    alle = np.vstack([fm.v for fm in former])
    bb = (float((alle @ u).min()), float((alle @ w).min()), float((alle @ u).max()), float((alle @ w).max()))
    eid = raster(former, R, bb, 0.04, med_id=True)
    return {int(k) for k, n in zip(*np.unique(eid[eid >= 0], return_counts=True)) if n >= 8}


# ------------------------------------------------------------------ tegning i pixelramme
def _tegn(ax, g, mat, M3, farve, lw_snit=1.4, fyld=None, tekst=True):
    T = lambda geom: affinity.affine_transform(geom, mat)  # noqa: E731
    for fm, p in g["tynde"]:
        fyld_poly(ax, T(p), facecolor="none", edgecolor=farve, lw=0.4, zorder=3)
    for fm, p in g["snit"]:
        fyld_poly(ax, T(p), facecolor=fyld or "none", edgecolor=farve, lw=lw_snit if fm.klasse != "IfcWindow" else 0.6,
                  zorder=4)
    for fm, blad, bue in g["doere"]:
        for ln in (blad, bue):
            x, y = T(ln).xy
            ax.plot(x, y, color=farve, lw=0.7, zorder=5)
    if tekst:
        for fm, p in g["rum"]:
            c = T(p).representative_point()
            q = ue.get_psets(fm.ent).get("Qto_SpaceBaseQuantities", {})
            ax.text(c.x, c.y, f"{fm.navn}\n{(q.get('NetFloorArea') or p.area / 1e6):.1f} m²", color=farve, fontsize=7,
                    ha="center", va="center", zorder=6)


def _figur_px(W, H):
    fig = plt.figure(figsize=(W / 100, H / 100), dpi=100)
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_xlim(0, W)
    ax.set_ylim(H, 0)
    ax.axis("off")
    return fig, ax


def _raster_px(ax, f, g, mat3, W, H, bleg):
    """Rasterbillede (facade/snit bagved) i modelramme, lagt i pixelrammen med affin transform."""
    former = g.get("raster_former")
    if not former:
        return
    u, w, d = g["ramme"]
    alle = np.vstack([fm.v for fm in former])
    off = g.get("u_off", 0.0)
    b = (float((alle @ u).min()) - off, float((alle @ w).min()), float((alle @ u).max()) - off, float((alle @ w).max()))
    bb = (b[0] + off, b[1], b[2] + off, b[3])
    px_pr_mm = min(2400 / max(bb[2] - bb[0], 1), 2400 / max(bb[3] - bb[1], 1))
    img = raster(former, (u, w, d), bb, px_pr_mm, klip=g.get("snit_klip"), bleg=bleg)
    tr = Affine2D(mat3) + ax.transData
    ax.imshow(img, extent=(b[0], b[2], b[1], b[3]), origin="upper", transform=tr, zorder=1, interpolation="bilinear")


# ------------------------------------------------------------------ automatiske sammenligninger
def _kantkoordinater(polys, akse):
    """Positioner af modelflader vinkelret på målretningen: akse 0 → x af lodrette kanter, 1 → y af vandrette."""
    ud = []
    for p in polys:
        for g in getattr(p, "geoms", [p]):
            if g.geom_type != "Polygon":
                continue
            for ring in [g.exterior] + list(g.interiors):
                c = np.array(ring.coords)
                for a, b in zip(c[:-1], c[1:]):
                    dx, dy = abs(b[0] - a[0]), abs(b[1] - a[1])
                    if akse == 0 and dx < 0.05 * max(dy, 1) and dy > 20:
                        ud.append(((a[0] + b[0]) / 2, min(a[1], b[1]), max(a[1], b[1])))
                    if akse == 1 and dy < 0.05 * max(dx, 1) and dx > 20:
                        ud.append(((a[1] + b[1]) / 2, min(a[0], b[0]), max(a[0], b[0])))
    return ud


def _naermeste(kanter, vaerdi, tvaer=None):
    """Nærmeste modelflade til målpunktet. Med tvaer (punktets anden koordinat) skal fladen også ligge ud for
    punktet – målpunktet sidder ved bygningsdelen (hjælpelinjens fod). Uden tvaer: kun positionen langs målet."""
    kand = [e for e in kanter if abs(e[0] - vaerdi) <= SOEG and
            (tvaer is None or e[1] - SOEG <= tvaer <= e[2] + SOEG)]
    if not kand:
        return None
    return min(kand, key=lambda e: abs(e[0] - vaerdi))[0]


def _auto(f, v, g, M, sidevogn):
    rows = []
    kanter = g.get("kanter") or []
    kx, ky = _kantkoordinater(kanter, 0), _kantkoordinater(kanter, 1)
    grans = unary_union([p.boundary for p in kanter]) if kanter else None
    for m in v.get("maal") or []:
        a, b = afkod.til_model(M, m["fra"]), afkod.til_model(M, m["til"])
        r = m.get("retning", "fri")
        tegn = afkod.maal_i_tegning(M, m)
        tol = afkod.tol_mm(m["vaerdi"])
        if r in ("x", "u", "y", "z"):
            akse = 0 if r in ("x", "u") else 1
            kk = kx if akse == 0 else ky
            loes = bool(m.get("paa_maalelinje"))
            ma = _naermeste(kk, a[akse], None if loes else a[1 - akse])
            mb = _naermeste(kk, b[akse], None if loes else b[1 - akse])
            model = abs(mb - ma) if ma is not None and mb is not None else None
        else:
            if grans is None:
                model = None
            else:
                from shapely.ops import nearest_points
                pa = nearest_points(grans, Point(a))[0]
                pb = nearest_points(grans, Point(b))[0]
                model = pa.distance(pb) if pa.distance(Point(a)) <= SOEG and pb.distance(Point(b)) <= SOEG else None
        if model is None:
            status = "MANGLER"
            note = ("ingen modelflade inden for 150 mm af et målpunkt"
                    + ("" if m.get("paa_maalelinje") else " (ud for punktet – sæt paa_maalelinje: true, hvis punkterne sidder på målelinjen)"))
        else:
            dev = model - m["vaerdi"]
            status = "OK" if abs(dev) <= tol else "AFVIGER"
            note = f"{dev:+.0f} mm"
        if abs(tegn - m["vaerdi"]) > tol:
            note += f"; NB tegningen selv viser {tegn:.0f} mm – tjek afkodningen"
        rows.append({"art": "mål", "id": m.get("id"), "tekst": m.get("tekst"), "original": m["vaerdi"],
                     "model": None if model is None else round(model), "status": status, "note": note,
                     "px": [m["fra"], m["til"]]})
    if v["type"] == "plan":
        for r in v.get("rum") or []:
            P = Point(afkod.til_model(M, r["punkt"]))
            hit = next(((fm, p) for fm, p in g["rum"] if p.buffer(1).contains(P)), None)
            if not hit:
                rows.append({"art": "rum", "id": r.get("navn"), "original": r.get("navn"), "model": None,
                             "status": "MANGLER", "note": "intet modelrum ved punktet", "px": [r["punkt"]]})
                continue
            fm, p = hit
            q = ue.get_psets(fm.ent).get("Qto_SpaceBaseQuantities", {})
            areal = q.get("NetFloorArea") or p.area / 1e6
            navn_ok = not r.get("navn") or _norm(r["navn"]) in _norm(fm.navn) or _norm(fm.navn) in _norm(r["navn"])
            status, note = "OK", f"{fm.tag} {fm.navn} {areal:.1f} m²"
            if not navn_ok:
                status, note = "AFVIGER", f"navn: model '{fm.navn}'"
            if r.get("areal"):
                dev = areal - float(r["areal"])
                if abs(dev) > max(0.5, 0.05 * float(r["areal"])):
                    status, note = "AFVIGER", note + f"; areal {areal:.1f} mod {r['areal']} m² ({dev:+.1f})"
            rows.append({"art": "rum", "id": r.get("navn"), "original": r.get("navn"), "model": fm.navn,
                         "status": status, "note": note, "px": [r["punkt"]]})
    brugt = set()
    for a in v.get("aabninger") or []:
        P = Point(afkod.til_model(M, a["punkt"]))
        kand = sorted(((p.distance(P), fm) for fm, p in g["aabninger"]), key=lambda x: x[0])
        if not kand or kand[0][0] > 400:
            rows.append({"art": "åbning", "id": a.get("id") or a.get("tekst"), "original": a["type"], "model": None,
                         "status": "MANGLER", "note": "ingen dør/vindue i modellen ved punktet", "px": [a["punkt"]]})
            continue
        dist, fm = kand[0]
        brugt.add(fm.id)
        typ = {"IfcWindow": "vindue", "IfcDoor": "doer"}.get(fm.klasse, fm.klasse)
        status, note = "OK", f"{fm.tag}"
        if a["type"] in ("vindue", "doer") and typ != a["type"]:
            status, note = "AFVIGER", f"{fm.tag} er {typ}"
        if a.get("bredde") and getattr(fm.ent, "OverallWidth", None):
            dev = float(fm.ent.OverallWidth) - float(a["bredde"])
            if abs(dev) > 50:
                status, note = "AFVIGER", note + f"; bredde {fm.ent.OverallWidth:.0f} mod {a['bredde']} ({dev:+.0f})"
        rows.append({"art": "åbning", "id": a.get("id") or a.get("tekst"), "original": a["type"], "model": fm.tag,
                     "status": status, "note": note, "px": [a["punkt"]]})
    if v.get("aabninger") is not None:
        x0, y0, x1, y1 = v["bbox"]
        hjorner = [afkod.til_model(M, (x, y)) for x, y in ((x0, y0), (x1, y0), (x1, y1), (x0, y1))]
        from shapely.geometry import Polygon as _P
        ramme = _P(hjorner)
        for fm, p in g["aabninger"]:
            if fm.id not in brugt and ramme.contains(p.centroid):
                rows.append({"art": "åbning", "id": fm.tag, "original": None, "model": fm.tag, "status": "EKSTRA",
                             "note": "i modellen, men ikke afkodet på tegningen", "px": []})
    for w in v.get("vaegge") or []:
        if not w.get("tykkelse"):
            continue
        P = Point(afkod.til_model(M, w["punkt"]))
        kand = sorted(((p.distance(P), fm, p) for fm, p in g.get("vaegge") or []), key=lambda x: x[0])
        if not kand or kand[0][0] > 250:
            rows.append({"art": "væg", "id": w.get("tekst"), "original": w["tykkelse"], "model": None, "status": "MANGLER",
                         "note": "ingen væg ved punktet", "px": [w["punkt"]]})
            continue
        _, fm, p = kand[0]
        tyk = ue.get_psets(fm.ent).get("Qto_WallBaseQuantities", {}).get("Width")
        if not tyk:
            r_ = p.minimum_rotated_rectangle
            cs = np.array(r_.exterior.coords)
            tyk = min(np.linalg.norm(cs[1] - cs[0]), np.linalg.norm(cs[2] - cs[1]))
        dev = float(tyk) - float(w["tykkelse"])
        rows.append({"art": "væg", "id": w.get("tekst") or fm.tag, "original": w["tykkelse"], "model": round(float(tyk)),
                     "status": "OK" if abs(dev) <= 20 else "AFVIGER", "note": f"{fm.tag} ({dev:+.0f} mm)",
                     "px": [w["punkt"]]})
    mc = f.by_type("IfcMapConversion")
    for k in v.get("koter") or []:
        if str(k.get("datum", "")).lower().startswith("relativ"):
            ets = [(float(st.Elevation or 0) / 1000, st.Name) for st in f.by_type("IfcBuildingStorey")]
            kote = float(k["kote"])
            naer = min(ets, key=lambda e: abs(e[0] - kote))
            dev = (naer[0] - kote) * 1000
            rows.append({"art": "kote", "id": k.get("beskrivelse"), "original": kote, "model": round(naer[0], 3),
                         "status": "OK" if abs(dev) <= 30 else "AFVIGER",
                         "note": f"relativ til ±0; nærmeste etage {naer[1]} ({dev:+.0f} mm)",
                         "px": [k["punkt"]] if k.get("punkt") else []})
            continue
        if not mc:
            rows.append({"art": "kote", "id": k.get("beskrivelse"), "original": k.get("kote"), "model": None,
                         "status": "IKKE SAMMENLIGNET", "note": "modellen har ingen georeference (kote for ±0)", "px": []})
            continue
        h0 = float(mc[0].OrthogonalHeight or 0)
        ets = [(h0 + float(st.Elevation or 0) / 1000, st.Name) for st in f.by_type("IfcBuildingStorey")]
        kote = float(k["kote"])
        naer = min(ets, key=lambda e: abs(e[0] - kote))
        dev = (naer[0] - kote) * 1000
        rows.append({"art": "kote", "id": k.get("beskrivelse"), "original": kote, "model": round(naer[0], 3),
                     "status": "OK" if abs(dev) <= 30 else "AFVIGER", "note": f"nærmeste etage {naer[1]} ({dev:+.0f} mm)",
                     "px": [k["punkt"]] if k.get("punkt") else []})
    return rows


# ------------------------------------------------------------------ fliser
def _fliser(orig, model, overlay, mappe, vid, x0, y0):
    mappe.mkdir(parents=True, exist_ok=True)
    W, H = orig.size
    nx, ny = max(1, math.ceil(W / FLISE)), max(1, math.ceil(H / FLISE))
    tw, th = math.ceil(W / nx), math.ceil(H / ny)
    try:
        font = ImageFont.load_default(size=14)
    except TypeError:
        font = ImageFont.load_default()
    filer = []
    for r in range(ny):
        for c in range(nx):
            box = (c * tw, r * th, min(W, (c + 1) * tw), min(H, (r + 1) * th))
            dele = [im.crop(box) for im in (orig, model, overlay)]
            w_, h_ = dele[0].size
            ark = Image.new("RGB", (3 * w_ + 20, h_ + 24), "white")
            for i, im in enumerate(dele):
                ark.paste(im.convert("RGB"), (i * (w_ + 10), 24))
            dr = ImageDraw.Draw(ark)
            dr.text((4, 4), f"{vid} r{r + 1}c{c + 1}  px x {box[0] + x0}-{box[2] + x0}, y {box[1] + y0}-{box[3] + y0}"
                            "   |  original  |  model  |  overlay", fill=(0, 0, 0), font=font)
            fil = mappe / f"flise-r{r + 1}c{c + 1}.png"
            ark.save(fil)
            filer.append(fil)
    return filer


# ------------------------------------------------------------------ indgang
def sammenlign(ifc, afk_sti, visning=None, ud=None, snithoejde=1000.0):
    ifc = pathlib.Path(ifc)
    d = afkod.indlaes(afk_sti)
    f = ifcopenshell.open(str(ifc))
    sv_sti = ifc.with_suffix(".byg.json")
    sidevogn = json.loads(sv_sti.read_text(encoding="utf-8")) if sv_sti.exists() else None
    former = hent(f)
    kildebillede = Image.open(d["kilde"]["_billede"]).convert("RGB")
    ud = pathlib.Path(ud) if ud else ifc.parent.parent / "sammenligning" / d["kilde"]["id"]
    total = {}
    for v in d["visninger"]:
        if v["type"] not in ("plan", "snit", "facade") or (visning and v["id"] != visning):
            continue
        M, rest, sx, sy = afkod.kalibrering(v)
        x0, y0, x1, y1 = map(int, v["bbox"])
        orig = kildebillede.crop((x0, y0, x1, y1))
        W, H = orig.size
        mat, mat3 = _px_matrix(M, x0, y0)
        g = _visningsgeometri(f, former, v, sidevogn, snithoejde)
        mappe = ud / v["id"]
        mappe.mkdir(parents=True, exist_ok=True)
        # model
        fig, ax = _figur_px(W, H)
        if v["type"] != "plan":
            _raster_px(ax, f, g, mat3, W, H, bleg=v["type"] == "snit")
        _tegn(ax, g, mat, mat3, "#000000", fyld="#9a9a9a" if v["type"] != "facade" else None)
        fig.savefig(mappe / "model.png", dpi=100, facecolor="white")
        plt.close(fig)
        model_img = Image.open(mappe / "model.png").convert("RGB").resize((W, H))
        # overlay
        fig, ax = _figur_px(W, H)
        bg = np.asarray(orig.convert("L"), dtype=float) / 255.0
        ax.imshow(0.45 + 0.55 * bg, cmap="gray", vmin=0, vmax=1, extent=(0, W, H, 0), zorder=0)
        _tegn(ax, g, mat, mat3, "#e00000", lw_snit=1.0, tekst=False)
        rows = _auto(f, v, g, M, sidevogn)
        for i, rw in enumerate(rows):
            for p in rw["px"]:
                px, py = p[0] - x0, p[1] - y0
                farve = {"OK": "#10a010", "AFVIGER": "#ff7f00", "MANGLER": "#ff00ff"}.get(rw["status"], "#808080")
                ax.plot([px], [py], marker="o", ms=6, mfc="none", mec=farve, mew=1.5, zorder=8)
            if rw["status"] in ("AFVIGER", "MANGLER") and rw["px"]:
                px, py = rw["px"][0][0] - x0, rw["px"][0][1] - y0
                ax.text(px + 6, py - 6, f"A{i + 1}", color="#ff7f00", fontsize=8, weight="bold", zorder=9)
        for kp in v["kal"]:
            ax.plot([kp["px"][0] - x0], [kp["px"][1] - y0], marker="+", color="blue", ms=12, zorder=9)
        fig.savefig(mappe / "overlay.png", dpi=100, facecolor="white")
        plt.close(fig)
        overlay_img = Image.open(mappe / "overlay.png").convert("RGB").resize((W, H))
        orig.save(mappe / "original.png")
        fliser = _fliser(orig, model_img, overlay_img, mappe / "fliser", v["id"], x0, y0)
        # tabel
        tael = {}
        for rw in rows:
            tael[rw["status"]] = tael.get(rw["status"], 0) + 1
        total[v["id"]] = tael
        lin = [f"# Automatisk sammenligning – {d['kilde']['id']} {v['id']} ({v['type']} {v.get('etage') or v.get('side') or ''})",
               f"Model: {ifc.name} · kalibrering: største rest {max(rest):.0f} mm, skala X {sx:.2f} · Y {sy:.2f} mm/px",
               "Status: " + ", ".join(f"{k} {n}" for k, n in sorted(tael.items())), "",
               "| # | Art | Id/tekst | Tegning | Model | Status | Note |", "|---|---|---|---|---|---|---|"]
        for i, rw in enumerate(rows):
            lin.append(f"| A{i + 1} | {rw['art']} | {rw.get('id') or rw.get('tekst') or ''} | {rw['original']} | "
                       f"{rw['model'] if rw['model'] is not None else '–'} | {rw['status']} | {rw['note']} |")
        lin += ["", "Billeder: original.png · model.png · overlay.png · fliser/ (" + str(len(fliser)) + ")",
                "Grønne cirkler = OK · orange = AFVIGER · magenta = MANGLER · blå kryds = kalibreringspunkter"]
        (mappe / "auto.md").write_text("\n".join(lin) + "\n", encoding="utf-8")
        (mappe / "auto.json").write_text(json.dumps(rows, ensure_ascii=False, indent=1, default=float), encoding="utf-8")
        print(f"SAMMENLIGN {d['kilde']['id']} {v['id']} ({v['type']}): " + ", ".join(f"{k} {n}" for k, n in sorted(tael.items()))
              + f" → {mappe}")
        for i, rw in enumerate(rows):
            if rw["status"] not in ("OK",) and i < 200:
                print(f"  A{i + 1} {rw['status']} {rw['art']} {rw.get('id') or ''}: tegning {rw['original']} · model "
                      f"{rw['model'] if rw['model'] is not None else '–'} · {rw['note']}")
        print(f"  billeder: {mappe}/overlay.png · {len(fliser)} fliser i {mappe / 'fliser'}")
    if not total:
        print("Ingen plan/snit/facade-visninger at sammenligne" + (f" med id {visning}" if visning else ""))
        return 1
    return 0

