"""2D/3D-geometri for generatoren: vægfodaftryk med samlinger, rumomrids og tagplaner (mm)."""
import math

import numpy as np
from shapely import affinity
from shapely.geometry import LineString, Point, Polygon, box
from shapely.ops import polygonize, unary_union

TOL = 20.0  # mm – et vægende "rører" en anden væg inden for denne afstand


def kryds2(a, b):
    return float(a[0] * b[1] - a[1] * b[0])


def enhed(v):
    v = np.asarray(v, dtype=float)
    n = np.linalg.norm(v)
    return v / n if n > 1e-12 else v


class VaegGeo:
    """Et vægsegment i verdenskoordinater (x, y) med lokal ramme: x langs p1→p2, y mod venstre."""

    def __init__(self, seg, tykkelse, lag_fra_hoejre=True):
        self.seg = seg
        self.id = seg["id"]
        self.p1 = np.array(seg["p1"], dtype=float)
        self.p2 = np.array(seg["p2"], dtype=float)
        self.L = float(np.linalg.norm(self.p2 - self.p1))
        self.ux = enhed(self.p2 - self.p1)
        self.uy = np.array([-self.ux[1], self.ux[0]])
        self.t = float(tykkelse)
        j = seg["justering"]
        # yR = højre flade (negativ y), yL = venstre flade
        self.yR, self.yL = {"midt": (-self.t / 2, self.t / 2), "venstre": (0.0, self.t),
                            "hoejre": (-self.t, 0.0)}[j]
        self.ude = bool(seg.get("_ude"))
        self.prio = (1 if self.ude else 0, self.t, -seg.get("_orden", 0))
        self.basis = self.rekt(0.0, self.L)
        self.fodaftryk = self.basis

    def lokal_til_verden(self, x, y):
        return self.p1 + self.ux * x + self.uy * y

    def verden_til_lokal(self, p):
        d = np.asarray(p, dtype=float) - self.p1
        return float(d @ self.ux), float(d @ self.uy)

    def rekt(self, x0, x1):
        pts = [self.lokal_til_verden(x, y) for x, y in ((x0, self.yR), (x1, self.yR), (x1, self.yL), (x0, self.yL))]
        return Polygon(pts)

    def flade_linjer(self):
        """De to lange flader som uendelige linjer: (punkt, retning)."""
        return [(self.lokal_til_verden(0, self.yR), self.ux), (self.lokal_til_verden(0, self.yL), self.ux)]


def _halvplan(punkt, retning, side_punkt, stor=1e6):
    """Halvplan afgrænset af linjen (punkt, retning) på den side, hvor side_punkt ligger."""
    n = np.array([-retning[1], retning[0]])
    if (np.asarray(side_punkt) - punkt) @ n < 0:
        n = -n
    a = punkt - retning * stor
    b = punkt + retning * stor
    return Polygon([a, b, b + n * stor, a + n * stor])


def vaegsamlinger(vaegge):
    """Beregner endelige fodaftryk. En ende, der rører en anden væg (o), forlænges til o's fjerne flade.
    Overlap skæres bort: T-samling → stammen afkortes; hjørne → væggen med lavest prioritet afkortes
    (prioritet: ydervæg > tykkere > først i spec). Parallelle vægge samles ikke."""
    ext, traek = {}, {w.id: [] for w in vaegge}
    for w in vaegge:
        poly = w.basis
        m = w.lokal_til_verden(w.L / 2, (w.yR + w.yL) / 2)
        for ende, p in ((0, w.p1), (1, w.p2)):
            for o in vaegge:
                if o is w or abs(kryds2(w.ux, o.ux)) < 0.1 or o.basis.distance(Point(p)) > TOL:
                    continue
                hjoerne = min(np.linalg.norm(o.p1 - p), np.linalg.norm(o.p2 - p)) <= max(o.t, w.t) + TOL
                stor = 2 * (o.t + w.t) + 2 * TOL
                lang = w.rekt(-stor, w.L) if ende == 0 else w.rekt(0, w.L + stor)
                fjern = max(o.flade_linjer(), key=lambda f: abs(kryds2(f[1], m - f[0])))
                behold = _halvplan(fjern[0], fjern[1], m)
                zone = Point(p).buffer(stor * 1.5)
                poly = unary_union([poly.difference(zone), unary_union([poly, lang]).intersection(zone).intersection(behold)])
                if not hjoerne or o.prio > w.prio:
                    traek[w.id].append((o, zone))
        ext[w.id] = poly
    for w in vaegge:
        poly = ext[w.id]
        for o, zone in traek[w.id]:
            poly = poly.difference(ext[o.id].intersection(zone))
        dele = [g for g in getattr(poly, "geoms", [poly]) if g.geom_type == "Polygon" and g.area > 1]
        if not dele:
            raise ValueError(f"væg {w.id}: fodaftrykket forsvandt ved samlingerne – tjek punkter og justering")
        m = Point(w.lokal_til_verden(w.L / 2, (w.yR + w.yL) / 2))
        poly = next((g for g in dele if g.buffer(1).contains(m)), max(dele, key=lambda g: g.area))
        w.fodaftryk = poly.simplify(0.01)
    return vaegge


def lokal_polygon(w, poly):
    """Fodaftryk i vægens lokale koordinater (x langs væggen, y mod venstre)."""
    ring = [w.verden_til_lokal(p) for p in list(poly.exterior.coords)[:-1]]
    return rens_ring(ring)


def rens_ring(ring, tol=0.05):
    ud = []
    for p in ring:
        if not ud or math.dist(ud[-1], p) > tol:
            ud.append((round(p[0], 3), round(p[1], 3)))
    if len(ud) > 1 and math.dist(ud[0], ud[-1]) <= tol:
        ud.pop()
    # fjern kollineære punkter
    ren = []
    n = len(ud)
    for i in range(n):
        a, b, c = np.array(ud[i - 1]), np.array(ud[i]), np.array(ud[(i + 1) % n])
        if abs(kryds2(b - a, c - b)) > 1e-6 * max(1.0, np.linalg.norm(b - a) * np.linalg.norm(c - b)):
            ren.append(ud[i])
    return ren if len(ren) >= 3 else ud


def ccw(ring):
    a = sum(ring[i][0] * ring[(i + 1) % len(ring)][1] - ring[(i + 1) % len(ring)][0] * ring[i][1]
            for i in range(len(ring)))
    return ring if a > 0 else ring[::-1]


def rum_polygon(punkt, vaeg_polys, afgraensninger=()):
    """Rummets omrids: det felt mellem væggene (og evt. afgrænsningslinjer), der indeholder punktet."""
    if not vaeg_polys:
        return None
    vaegge = unary_union(vaeg_polys)
    minx, miny, maxx, maxy = vaegge.bounds
    ramme = box(minx - 1000, miny - 1000, maxx + 1000, maxy + 1000)
    fri = ramme.difference(vaegge)
    for linje in afgraensninger:
        fri = fri.difference(LineString(linje).buffer(0.5))
    for g in getattr(fri, "geoms", [fri]):
        if g.contains(Point(punkt)):
            if g.buffer(-1).intersects(ramme.exterior.buffer(10)):
                return None  # punktet ligger uden for bygningen
            return g
    return None


def omrids_fra_vaegge(vaeg_polys, kant):
    """Omrids af en vægløkke: yderside = facadens omrids; inderside = det felt, løkken omslutter."""
    u = unary_union(vaeg_polys)
    polys = [g for g in getattr(u, "geoms", [u]) if g.geom_type == "Polygon"]
    if not polys:
        return None
    stoerst = max(polys, key=lambda g: g.area)
    if kant == "yderside":
        return Polygon(stoerst.exterior)
    if not stoerst.interiors:
        return None
    return Polygon(max(stoerst.interiors, key=lambda r: Polygon(r).area))


# ------------------------------------------------------------------ tage
class Tagflade:
    """Plan tagflade: polygon (3D, underside) og plan (punkt, normal opad)."""

    def __init__(self, navn, pkt3d, normal):
        self.navn = navn
        self.pkt = [np.array(p, dtype=float) for p in pkt3d]
        self.normal = enhed(normal)
        self.origo = self.pkt[0]


def tagflader(t):
    """Tagfladernes underside i etagens koordinater (z rel. etagegulv)."""
    x0, y0, x1, y1 = t["omrids"]
    o, og = t["udhaeng"], t.get("udhaeng_gavl", 0)
    tan = math.tan(math.radians(t["haeldning"])) if t["form"] != "fladt" else 0.0
    ze = t["tagfod"] - o * tan  # tagfod ved udhængets kant
    X0, Y0, X1, Y1 = x0 - o, y0 - o, x1 + o, y1 + o
    form = t["form"]
    F = []
    if form == "fladt":
        F.append(Tagflade("flad", [(X0, Y0, t["tagfod"]), (X1, Y0, t["tagfod"]), (X1, Y1, t["tagfod"]),
                                   (X0, Y1, t["tagfod"])], (0, 0, 1)))
        return F
    if form == "pulttag":
        side = t["hoej_side"]
        if side[0] == "x":
            lav, hoej = (X0, X1) if side == "x+" else (X1, X0)
            dz = abs(X1 - X0) * tan
            pk = [(lav, Y0, ze), (lav, Y1, ze), (hoej, Y1, ze + dz), (hoej, Y0, ze + dz)]
            n = (-(1 if side == "x+" else -1) * tan, 0, 1)
        else:
            lav, hoej = (Y0, Y1) if side == "y+" else (Y1, Y0)
            dz = abs(Y1 - Y0) * tan
            pk = [(X0, lav, ze), (X1, lav, ze), (X1, hoej, ze + dz), (X0, hoej, ze + dz)]
            n = (0, -(1 if side == "y+" else -1) * tan, 1)
        F.append(Tagflade("pult", pk, n))
        return F
    # sadel/valm – rygning langs x eller y. Arbejd i (u langs rygning, v på tværs) og spejl til x/y.
    langs_x = t["rygning"] == "x"
    U0, U1, V0, V1 = (X0, X1, Y0, Y1) if langs_x else (Y0, Y1, X0, X1)
    vm = (V0 + V1) / 2
    zr = ze + (vm - V0) * tan
    if form == "sadeltag":
        U0g, U1g = U0 - og, U1 + og
        sider = [("side1", [(U0g, V0, ze), (U1g, V0, ze), (U1g, vm, zr), (U0g, vm, zr)], (0, -tan, 1)),
                 ("side2", [(U1g, V1, ze), (U0g, V1, ze), (U0g, vm, zr), (U1g, vm, zr)], (0, tan, 1))]
    else:
        h = (V1 - V0) / 2  # valmens vandrette dybde = halv bredde
        ua, ub = U0 + h, U1 - h
        if ua > ub:
            ua = ub = (U0 + U1) / 2
        sider = [("side1", [(U0, V0, ze), (U1, V0, ze), (ub, vm, zr), (ua, vm, zr)], (0, -tan, 1)),
                 ("side2", [(U1, V1, ze), (U0, V1, ze), (ua, vm, zr), (ub, vm, zr)], (0, tan, 1)),
                 ("valm1", [(U0, V1, ze), (U0, V0, ze), (ua, vm, zr)], (-tan, 0, 1)),
                 ("valm2", [(U1, V0, ze), (U1, V1, ze), (ub, vm, zr)], (tan, 0, 1))]
    for navn, pk, n in sider:
        if not langs_x:
            pk = [(v, u, z) for u, v, z in pk]
            n = (n[1], n[0], n[2])
            pk = pk[::-1]  # spejling vender omløbsretningen
        F.append(Tagflade(navn, pk, n))
    return F


def flade_ramme(fl):
    """Lokal ramme i fladen: x langs første kant, z = normal (opad), y = z × x."""
    xa = enhed(fl.pkt[1] - fl.pkt[0])
    za = fl.normal
    xa = enhed(xa - za * (xa @ za))
    ya = np.cross(za, xa)
    return fl.origo, xa, ya, za


def til_flade_2d(fl, ramme):
    o, xa, ya, _ = ramme
    return [((p - o) @ xa, (p - o) @ ya) for p in fl.pkt]


def transform_ring_2d(ring, vinkel_grader, flyt):
    poly = affinity.translate(affinity.rotate(Polygon(ring), vinkel_grader, origin=(0, 0)), *flyt)
    return list(poly.exterior.coords)[:-1]


__all__ = ["VaegGeo", "vaegsamlinger", "lokal_polygon", "rens_ring", "ccw", "rum_polygon", "omrids_fra_vaegge",
           "tagflader", "flade_ramme", "til_flade_2d", "enhed", "polygonize"]
