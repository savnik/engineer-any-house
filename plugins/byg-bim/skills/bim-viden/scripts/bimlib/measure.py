"""Measurements from an IFC model in one call: one element, a space, the distance between two elements or all walls on a storey.

All lengths in mm, areas in m². Dimensions are read from the model geometry (and Qto_, where present) and are only as good as
the model's source – which is why the source (Byg_Kilde) is always printed.
"""
import contextlib
import io
import pathlib
import tempfile

import numpy as np
import ifcopenshell
import ifcopenshell.geom
import ifcopenshell.util.element as ue
import ifcopenshell.util.placement as up
import ifcopenshell.util.unit as uu
from shapely.geometry import Polygon
from shapely.ops import nearest_points, unary_union

from .geometry import storey_of


def _settings():
    s = ifcopenshell.geom.settings()
    s.set("use-world-coords", True)
    s.set("weld-vertices", True)
    return s


def _mesh(e):
    """(verts mm, faces) in world coordinates, or None."""
    if not getattr(e, "Representation", None):
        return None
    body = [r for r in e.Representation.Representations if r.RepresentationIdentifier == "Body"]
    try:
        # without the Body representation the geometry engine takes the first one (e.g. the wall axis)
        sh = ifcopenshell.geom.create_shape(_settings(), e, *body[:1])
    except Exception:
        return None
    v = np.array(sh.geometry.verts, dtype=float).reshape(-1, 3) * 1000.0
    f = np.array(sh.geometry.faces, dtype=np.int64).reshape(-1, 3)
    return (v, f) if len(f) else None


def _footprint(v, f):
    """The element's outline seen from above (shapely, mm)."""
    tri = [Polygon(v[t, :2]) for t in f]
    return unary_union([t for t in tri if t.area > 1.0])


def _local(e, v, scale):
    """Corner points in the element's own coordinate system (mm): x along the wall, y across, z up."""
    M = up.get_local_placement(e.ObjectPlacement)
    M = M.copy()
    M[:3, 3] *= scale
    h = np.c_[v, np.ones(len(v))]
    return (np.linalg.inv(M) @ h.T).T[:, :3]


def _source(e):
    k = ue.get_psets(e).get("Byg_Kilde") or {}
    parts = [f"{n}={k[n]}" for n in k if n != "id"]
    return "kilde: " + (", ".join(parts) if parts else "ingen Byg_Kilde (fremmed model eller ukendt kilde)")


def _name(e):
    return getattr(e, "Tag", None) or e.Name or f"#{e.id()}"


def _find(f, key):
    """Element by #step-id, GlobalId, Tag, Name or (space) LongName – case-insensitive."""
    if key.startswith("#") and key[1:].isdigit():
        return f.by_id(int(key[1:]))
    try:
        return f.by_guid(key)
    except RuntimeError:
        pass
    n = key.casefold()
    for e in f.by_type("IfcProduct"):
        for a in ("Tag", "Name", "LongName"):
            if str(getattr(e, a, None) or "").casefold() == n:
                return e
    return None


def _scale(f):
    return uu.calculate_unit_scale(f) * 1000.0  # project unit → mm


def _qto_lengths(e, scale):
    out = {}
    for name, q in ue.get_psets(e, qtos_only=True).items():
        for k in ("Length", "Width", "Height"):
            if isinstance(q.get(k), (int, float)) and k not in out:
                out[k] = q[k] * scale
    return out


def _side_faces(loc, tol=1.0):
    """Length of the wall's two long faces (min-y and max-y side) from the corner points."""
    y0, y1 = loc[:, 1].min(), loc[:, 1].max()
    res = []
    for y in (y0, y1):
        xs = loc[np.abs(loc[:, 1] - y) < tol, 0]
        res.append((y, float(xs.max() - xs.min()) if len(xs) else None))
    return res


def _inner_side(f, e, loc_y, M_loc, scale):
    """Which side (y value in local coordinates) faces the centre of the storey? None if that makes no sense."""
    st = storey_of(e)
    if st is None:
        return None
    pts = []
    for w in f.by_type("IfcWall"):
        if storey_of(w) == st:
            M = up.get_local_placement(w.ObjectPlacement)
            pts.append(M[:2, 3] * scale)
    if len(pts) < 3:
        return None
    c = np.mean(pts, axis=0)
    M = M_loc.copy()
    M[:3, 3] *= scale
    cl = (np.linalg.inv(M) @ np.array([c[0], c[1], M[2, 3], 1.0]))[1]
    return min(loc_y, key=lambda y: abs(y - cl))


def _openings(e, scale):
    rows = []
    for rel in getattr(e, "HasOpenings", []) or []:
        o = rel.RelatedOpeningElement
        fillings = [r.RelatedBuildingElement for r in getattr(o, "HasFillings", []) or []]
        m = _mesh(o)
        if m is None:
            continue
        loc = _local(e, m[0], scale)
        x0, x1 = loc[:, 0].min(), loc[:, 0].max()
        z0, z1 = loc[:, 2].min(), loc[:, 2].max()
        name = _name(fillings[0]) if fillings else _name(o)
        cls = fillings[0].is_a()[3:] if fillings else "hul"
        rows.append((x0, f"    {name} ({cls}): fra væggens start {x0:.0f} · bredde {x1 - x0:.0f} · "
                         f"brystning {max(z0, 0):.0f} · højde {z1 - z0:.0f}"))
    return [r for _, r in sorted(rows)]


def element(f, e) -> int:
    scale = _scale(f)
    st = storey_of(e)
    print(f"{_name(e)} · {e.is_a()} · etage {st.Name if st else '-'}"
          + (f" · type '{ue.get_type(e).Name}'" if ue.get_type(e) else ""))
    m = _mesh(e)
    if m is None:
        print("  ingen geometri – kan ikke måles")
        return 1
    v, fa = m
    if e.is_a("IfcSpace"):
        return _space(e, v, fa)
    q = _qto_lengths(e, scale)
    if e.is_a("IfcWall") and getattr(e, "ObjectPlacement", None):
        loc = _local(e, v, scale)
        L = float(loc[:, 0].max() - loc[:, 0].min())
        t = float(loc[:, 1].max() - loc[:, 1].min())
        h = float(loc[:, 2].max() - loc[:, 2].min())
        print(f"  længde (største) {L:.0f} · tykkelse {t:.0f} · højde {h:.0f}"
              + (f" · Qto: længde {q['Length']:.0f}" if "Length" in q else "")
              + f" · underkant kote {v[:, 2].min():+.0f}")
        sides = _side_faces(loc)
        external = ue.get_psets(e).get("Pset_WallCommon", {}).get("IsExternal")
        inner = (_inner_side(f, e, [y for y, _ in sides], up.get_local_placement(e.ObjectPlacement), scale)
               if external is not False else None)  # an interior wall has no inner and outer side
        for y, length in sides:
            mark = "" if inner is None else (" (inderside)" if y == inner else " (yderside)")
            print(f"  flade{mark}: {length:.0f}" if length is not None else f"  flade{mark}: ?")
        openings = _openings(e, scale)
        if openings:
            print("  åbninger (mål langs væggen fra dens startpunkt):")
            print("\n".join(openings))
    else:
        d = v.max(axis=0) - v.min(axis=0)
        print(f"  udstrækning x {d[0]:.0f} · y {d[1]:.0f} · z {d[2]:.0f} · underkant kote {v[:, 2].min():+.0f}"
              + "".join(f" · Qto {k} {x:.0f}" for k, x in q.items()))
    print("  " + _source(e))
    return 0


def _space(e, v, fa) -> int:
    fp = _footprint(v, fa)
    r = fp.minimum_rotated_rectangle
    xy = np.array(r.exterior.coords)[:4]
    a, b = sorted([float(np.linalg.norm(xy[1] - xy[0])), float(np.linalg.norm(xy[2] - xy[1]))], reverse=True)
    shape_desc = "rektangulært" if fp.area / max(r.area, 1) > 0.98 else f"ikke rektangulært ({fp.area / r.area:.0%} af den omskrevne firkant)"
    print(f"  {getattr(e, 'LongName', None) or e.Name}: indvendigt {a:.0f} × {b:.0f} ({shape_desc}) · gulvareal {fp.area / 1e6:.2f} m² "
          f"· omkreds {fp.exterior.length:.0f}")
    print(f"  højde {v[:, 2].max() - v[:, 2].min():.0f} (største; gulv kote {v[:, 2].min():+.0f})")
    print("  " + _source(e))
    return 0


def distance(f, a, b) -> int:
    ma, mb = _mesh(a), _mesh(b)
    if ma is None or mb is None:
        print("Mindst ét af elementerne har ingen geometri")
        return 1
    pa, pb = _footprint(*ma), _footprint(*mb)
    d = pa.distance(pb)
    p, q = nearest_points(pa, pb)
    za = (ma[0][:, 2].min(), ma[0][:, 2].max())
    zb = (mb[0][:, 2].min(), mb[0][:, 2].max())
    print(f"{_name(a)} → {_name(b)}: vandret fri afstand {d:.0f} (set ovenfra, mellem nærmeste flader; "
          f"fra ({p.x:.0f}, {p.y:.0f}) til ({q.x:.0f}, {q.y:.0f}))")
    vertical = max(zb[0] - za[1], za[0] - zb[1])
    if vertical > 0:
        print(f"  lodret afstand {vertical:.0f} (elementerne overlapper ikke i højden)")
    print(f"  {_name(a)}: {_source(a)}")
    print(f"  {_name(b)}: {_source(b)}")
    return 0


def storey(f, key) -> int:
    n = key.casefold()
    st = [s for s in f.by_type("IfcBuildingStorey") if n in (str(s.Name or "").casefold(), str(s.LongName or "").casefold())]
    if not st:
        print(f"Etage ikke fundet: {key}. Findes: " + ", ".join(s.Name or "?" for s in f.by_type("IfcBuildingStorey")))
        return 1
    st = st[0]
    scale = _scale(f)
    walls = sorted((w for w in f.by_type("IfcWall") if storey_of(w) == st), key=_name)
    print(f"{st.Name}: {len(walls)} vægge (mm) · id | type | længde | tykkelse | højde | kilde")
    for w in walls:
        q = _qto_lengths(w, scale)
        if not {"Length", "Width", "Height"} <= q.keys():
            m = _mesh(w)
            if m is not None:
                loc = _local(w, m[0], scale)
                ext = loc.max(axis=0) - loc.min(axis=0)
                q = {"Length": ext[0], "Width": ext[1], "Height": ext[2], **q}
        t = ue.get_type(w)
        k = ue.get_psets(w).get("Byg_Kilde") or {}
        print(f"  {_name(w)} | {t.Name if t else '-'} | {q.get('Length', 0):.0f} | {q.get('Width', 0):.0f} | "
              f"{q.get('Height', 0):.0f} | {k.get('Kilde', '?')}" + (f" ({k['Reference']})" if k.get("Reference") else ""))
    spaces = [s for s in f.by_type("IfcSpace") if ue.get_aggregate(s) == st]
    if spaces:
        print("Rum: " + ", ".join(f"{s.Name} {s.LongName or ''}".strip() for s in spaces) + "  (mål: measure <ifc> --space <navn>)")
    return 0


def _open_model(model: pathlib.Path):
    """An IFC file directly, or a spec (model.yaml/proposal) built in a temporary directory – so the current model is measured,
    even when ud/*.ifc has not been built after the latest merge."""
    if model.suffix.lower() not in (".yaml", ".yml"):
        return ifcopenshell.open(str(model))
    from .build import build
    from .spec import load
    with tempfile.TemporaryDirectory() as d, contextlib.redirect_stdout(io.StringIO()):
        build(load(model), pathlib.Path(d) / "m.ifc")
        return ifcopenshell.open(str(pathlib.Path(d) / "m.ifc"))


def measure(ifc: pathlib.Path, a=None, b=None, room=None, storey_name=None) -> int:
    f = _open_model(pathlib.Path(ifc))
    if storey_name:
        return storey(f, storey_name)
    keys = [x for x in (room, a, b) if x]
    if not keys:
        print("Angiv et element, --space <navn> eller --storey <navn> (se bim.py --help)")
        return 2
    ents = []
    for n in keys:
        e = _find(f, n)
        if e is None or (room and n == room and not e.is_a("IfcSpace")):
            print(f"Ikke fundet: {n} (brug Tag/spec-id, navn, rumnavn, GlobalId eller #step-id; 'find' viser id'er)")
            return 1
        ents.append(e)
    if len(ents) == 2:
        return distance(f, *ents)
    return element(f, ents[0])
