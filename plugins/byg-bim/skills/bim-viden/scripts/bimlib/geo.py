"""2D/3D geometry for the generator: wall footprints with joins, room outlines and roof planes (mm)."""
import math

import numpy as np
from shapely import affinity
from shapely.geometry import LineString, Point, Polygon, box
from shapely.ops import polygonize, unary_union

TOL = 20.0  # mm – a wall end "touches" another wall within this distance


def cross2(a, b):
    return float(a[0] * b[1] - a[1] * b[0])


def unit(v):
    v = np.asarray(v, dtype=float)
    n = np.linalg.norm(v)
    return v / n if n > 1e-12 else v


class WallGeo:
    """A wall segment in world coordinates (x, y) with a local frame: x along p1→p2, y to the left."""

    def __init__(self, seg, thickness, layers_from_right=True):
        self.seg = seg
        self.id = seg["id"]
        self.p1 = np.array(seg["p1"], dtype=float)
        self.p2 = np.array(seg["p2"], dtype=float)
        self.L = float(np.linalg.norm(self.p2 - self.p1))
        self.ux = unit(self.p2 - self.p1)
        self.uy = np.array([-self.ux[1], self.ux[0]])
        self.t = float(thickness)
        j = seg["justering"]
        # yR = right face (negative y), yL = left face
        self.yR, self.yL = {"midt": (-self.t / 2, self.t / 2), "venstre": (0.0, self.t),
                            "hoejre": (-self.t, 0.0)}[j]
        self.external = bool(seg.get("_ude"))
        self.prio = (1 if self.external else 0, self.t, -seg.get("_orden", 0))
        self.base = self.rect(0.0, self.L)
        self.footprint = self.base

    def local_to_world(self, x, y):
        return self.p1 + self.ux * x + self.uy * y

    def world_to_local(self, p):
        d = np.asarray(p, dtype=float) - self.p1
        return float(d @ self.ux), float(d @ self.uy)

    def rect(self, x0, x1):
        pts = [self.local_to_world(x, y) for x, y in ((x0, self.yR), (x1, self.yR), (x1, self.yL), (x0, self.yL))]
        return Polygon(pts)

    def face_lines(self):
        """The two long faces as infinite lines: (point, direction)."""
        return [(self.local_to_world(0, self.yR), self.ux), (self.local_to_world(0, self.yL), self.ux)]


def _half_plane(point, direction, side_point, big=1e6):
    """Half-plane bounded by the line (point, direction) on the side where side_point lies."""
    n = np.array([-direction[1], direction[0]])
    if (np.asarray(side_point) - point) @ n < 0:
        n = -n
    a = point - direction * big
    b = point + direction * big
    return Polygon([a, b, b + n * big, a + n * big])


def wall_joins(walls):
    """Computes the final footprints. An end touching another wall (o) is extended to o's far face.
    Overlap is cut away: T-junction → the stem is shortened; corner → the wall with the lowest priority is shortened
    (priority: external wall > thicker > first in the spec). Parallel walls are not joined."""
    ext, trim = {}, {w.id: [] for w in walls}
    for w in walls:
        poly = w.base
        m = w.local_to_world(w.L / 2, (w.yR + w.yL) / 2)
        for end, p in ((0, w.p1), (1, w.p2)):
            for o in walls:
                if o is w or abs(cross2(w.ux, o.ux)) < 0.1 or o.base.distance(Point(p)) > TOL:
                    continue
                corner = min(np.linalg.norm(o.p1 - p), np.linalg.norm(o.p2 - p)) <= max(o.t, w.t) + TOL
                big = 2 * (o.t + w.t) + 2 * TOL
                long_ = w.rect(-big, w.L) if end == 0 else w.rect(0, w.L + big)
                far = max(o.face_lines(), key=lambda f: abs(cross2(f[1], m - f[0])))
                keep = _half_plane(far[0], far[1], m)
                zone = Point(p).buffer(big * 1.5)
                poly = unary_union([poly.difference(zone), unary_union([poly, long_]).intersection(zone).intersection(keep)])
                if not corner or o.prio > w.prio:
                    trim[w.id].append((o, zone))
        ext[w.id] = poly
    for w in walls:
        poly = ext[w.id]
        for o, zone in trim[w.id]:
            poly = poly.difference(ext[o.id].intersection(zone))
        parts = [g for g in getattr(poly, "geoms", [poly]) if g.geom_type == "Polygon" and g.area > 1]
        if not parts:
            raise ValueError(f"væg {w.id}: fodaftrykket forsvandt ved samlingerne – tjek punkter og justering")
        m = Point(w.local_to_world(w.L / 2, (w.yR + w.yL) / 2))
        poly = next((g for g in parts if g.buffer(1).contains(m)), max(parts, key=lambda g: g.area))
        w.footprint = poly.simplify(0.01)
    return walls


def local_polygon(w, poly):
    """Footprint in the wall's local coordinates (x along the wall, y to the left)."""
    ring = [w.world_to_local(p) for p in list(poly.exterior.coords)[:-1]]
    return clean_ring(ring)


def clean_ring(ring, tol=0.05):
    out = []
    for p in ring:
        if not out or math.dist(out[-1], p) > tol:
            out.append((round(p[0], 3), round(p[1], 3)))
    if len(out) > 1 and math.dist(out[0], out[-1]) <= tol:
        out.pop()
    # remove collinear points
    clean = []
    n = len(out)
    for i in range(n):
        a, b, c = np.array(out[i - 1]), np.array(out[i]), np.array(out[(i + 1) % n])
        if abs(cross2(b - a, c - b)) > 1e-6 * max(1.0, np.linalg.norm(b - a) * np.linalg.norm(c - b)):
            clean.append(out[i])
    return clean if len(clean) >= 3 else out


def ccw(ring):
    a = sum(ring[i][0] * ring[(i + 1) % len(ring)][1] - ring[(i + 1) % len(ring)][0] * ring[i][1]
            for i in range(len(ring)))
    return ring if a > 0 else ring[::-1]


def room_polygon(point, wall_polys, boundaries=()):
    """The room's outline: the region between the walls (and any boundary lines) that contains the point."""
    if not wall_polys:
        return None
    walls = unary_union(wall_polys)
    minx, miny, maxx, maxy = walls.bounds
    frame = box(minx - 1000, miny - 1000, maxx + 1000, maxy + 1000)
    free = frame.difference(walls)
    for line in boundaries:
        free = free.difference(LineString(line).buffer(0.5))
    for g in getattr(free, "geoms", [free]):
        if g.contains(Point(point)):
            if g.buffer(-1).intersects(frame.exterior.buffer(10)):
                return None  # the point lies outside the building
            return g
    return None


def outline_from_walls(wall_polys, edge):
    """Outline of a wall loop: yderside = the facade outline; inderside = the region the loop encloses."""
    u = unary_union(wall_polys)
    polys = [g for g in getattr(u, "geoms", [u]) if g.geom_type == "Polygon"]
    if not polys:
        return None
    largest = max(polys, key=lambda g: g.area)
    if edge == "yderside":
        return Polygon(largest.exterior)
    if not largest.interiors:
        return None
    return Polygon(max(largest.interiors, key=lambda r: Polygon(r).area))


# ------------------------------------------------------------------ roofs
class RoofFace:
    """Plane roof face: polygon (3D, underside) and plane (point, upward normal)."""

    def __init__(self, name, pts3d, normal):
        self.name = name
        self.pts = [np.array(p, dtype=float) for p in pts3d]
        self.normal = unit(normal)
        self.origin = self.pts[0]


def roof_faces(t):
    """The undersides of the roof faces in storey coordinates (z relative to the storey floor)."""
    x0, y0, x1, y1 = t["omrids"]
    o, og = t["udhaeng"], t.get("udhaeng_gavl", 0)
    tan = math.tan(math.radians(t["haeldning"])) if t["form"] != "fladt" else 0.0
    ze = t["tagfod"] - o * tan  # eaves level at the overhang's edge
    X0, Y0, X1, Y1 = x0 - o, y0 - o, x1 + o, y1 + o
    form = t["form"]
    F = []
    if form == "fladt":
        F.append(RoofFace("flad", [(X0, Y0, t["tagfod"]), (X1, Y0, t["tagfod"]), (X1, Y1, t["tagfod"]),
                                   (X0, Y1, t["tagfod"])], (0, 0, 1)))
        return F
    if form == "pulttag":
        side = t["hoej_side"]
        if side[0] == "x":
            low, high = (X0, X1) if side == "x+" else (X1, X0)
            dz = abs(X1 - X0) * tan
            pk = [(low, Y0, ze), (low, Y1, ze), (high, Y1, ze + dz), (high, Y0, ze + dz)]
            n = (-(1 if side == "x+" else -1) * tan, 0, 1)
        else:
            low, high = (Y0, Y1) if side == "y+" else (Y1, Y0)
            dz = abs(Y1 - Y0) * tan
            pk = [(X0, low, ze), (X1, low, ze), (X1, high, ze + dz), (X0, high, ze + dz)]
            n = (0, -(1 if side == "y+" else -1) * tan, 1)
        F.append(RoofFace("pult", pk, n))
        return F
    # gable/hip – ridge along x or y. Work in (u along the ridge, v across) and mirror to x/y.
    along_x = t["rygning"] == "x"
    U0, U1, V0, V1 = (X0, X1, Y0, Y1) if along_x else (Y0, Y1, X0, X1)
    vm = (V0 + V1) / 2
    zr = ze + (vm - V0) * tan
    if form == "sadeltag":
        U0g, U1g = U0 - og, U1 + og
        sides = [("side1", [(U0g, V0, ze), (U1g, V0, ze), (U1g, vm, zr), (U0g, vm, zr)], (0, -tan, 1)),
                 ("side2", [(U1g, V1, ze), (U0g, V1, ze), (U0g, vm, zr), (U1g, vm, zr)], (0, tan, 1))]
    else:
        h = (V1 - V0) / 2  # horizontal depth of the hip = half the width
        ua, ub = U0 + h, U1 - h
        if ua > ub:
            ua = ub = (U0 + U1) / 2
        sides = [("side1", [(U0, V0, ze), (U1, V0, ze), (ub, vm, zr), (ua, vm, zr)], (0, -tan, 1)),
                 ("side2", [(U1, V1, ze), (U0, V1, ze), (ua, vm, zr), (ub, vm, zr)], (0, tan, 1)),
                 ("valm1", [(U0, V1, ze), (U0, V0, ze), (ua, vm, zr)], (-tan, 0, 1)),
                 ("valm2", [(U1, V0, ze), (U1, V1, ze), (ub, vm, zr)], (tan, 0, 1))]
    for name, pk, n in sides:
        if not along_x:
            pk = [(v, u, z) for u, v, z in pk]
            n = (n[1], n[0], n[2])
            pk = pk[::-1]  # mirroring reverses the winding
        F.append(RoofFace(name, pk, n))
    return F


def face_frame(fl):
    """Local frame in the face: x along the first edge, z = normal (upward), y = z × x."""
    xa = unit(fl.pts[1] - fl.pts[0])
    za = fl.normal
    xa = unit(xa - za * (xa @ za))
    ya = np.cross(za, xa)
    return fl.origin, xa, ya, za


def to_face_2d(fl, frame):
    o, xa, ya, _ = frame
    return [((p - o) @ xa, (p - o) @ ya) for p in fl.pts]


def transform_ring_2d(ring, angle_deg, offset):
    poly = affinity.translate(affinity.rotate(Polygon(ring), angle_deg, origin=(0, 0)), *offset)
    return list(poly.exterior.coords)[:-1]


__all__ = ["WallGeo", "wall_joins", "local_polygon", "clean_ring", "ccw", "room_polygon", "outline_from_walls",
           "roof_faces", "face_frame", "to_face_2d", "unit", "polygonize"]
