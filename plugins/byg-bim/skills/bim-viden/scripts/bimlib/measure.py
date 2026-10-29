"""Mål fra en IFC-model i ét kald: ét element, et rum, afstanden mellem to elementer eller alle vægge på en etage.

Alle længder i mm, arealer i m². Mål læses fra modellens geometri (og Qto_, når den findes) og er kun så gode som
modellens kilde – derfor skrives kilden (Byg_Kilde) altid med.
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

from .geometry import etage_af


def _settings():
    s = ifcopenshell.geom.settings()
    s.set("use-world-coords", True)
    s.set("weld-vertices", True)
    return s


def _mesh(e):
    """(verts mm, faces) i verdenskoordinater, eller None."""
    if not getattr(e, "Representation", None):
        return None
    body = [r for r in e.Representation.Representations if r.RepresentationIdentifier == "Body"]
    try:
        # uden Body-repræsentationen tager geometrimotoren den første (fx væggens akse)
        sh = ifcopenshell.geom.create_shape(_settings(), e, *body[:1])
    except Exception:
        return None
    v = np.array(sh.geometry.verts, dtype=float).reshape(-1, 3) * 1000.0
    f = np.array(sh.geometry.faces, dtype=np.int64).reshape(-1, 3)
    return (v, f) if len(f) else None


def _fodaftryk(v, f):
    """Elementets omrids set ovenfra (shapely, mm)."""
    tri = [Polygon(v[t, :2]) for t in f]
    return unary_union([t for t in tri if t.area > 1.0])


def _lokal(e, v, skala):
    """Hjørnepunkter i elementets eget koordinatsystem (mm): x langs væggen, y på tværs, z op."""
    M = up.get_local_placement(e.ObjectPlacement)
    M = M.copy()
    M[:3, 3] *= skala
    h = np.c_[v, np.ones(len(v))]
    return (np.linalg.inv(M) @ h.T).T[:, :3]


def _kilde(e):
    k = ue.get_psets(e).get("Byg_Kilde") or {}
    dele = [f"{n}={k[n]}" for n in k if n != "id"]
    return "kilde: " + (", ".join(dele) if dele else "ingen Byg_Kilde (fremmed model eller ukendt kilde)")


def _navn(e):
    return getattr(e, "Tag", None) or e.Name or f"#{e.id()}"


def _find(f, noegle):
    """Element ud fra #step-id, GlobalId, Tag, Name eller (rum) LongName – uden forskel på store/små bogstaver."""
    if noegle.startswith("#") and noegle[1:].isdigit():
        return f.by_id(int(noegle[1:]))
    try:
        return f.by_guid(noegle)
    except RuntimeError:
        pass
    n = noegle.casefold()
    for e in f.by_type("IfcProduct"):
        for a in ("Tag", "Name", "LongName"):
            if str(getattr(e, a, None) or "").casefold() == n:
                return e
    return None


def _skala(f):
    return uu.calculate_unit_scale(f) * 1000.0  # projektenhed → mm


def _qto_laengder(e, skala):
    out = {}
    for navn, q in ue.get_psets(e, qtos_only=True).items():
        for k in ("Length", "Width", "Height"):
            if isinstance(q.get(k), (int, float)) and k not in out:
                out[k] = q[k] * skala
    return out


def _sideflader(lok, tol=1.0):
    """Længden af væggens to lange flader (min-y og max-y side) ud fra hjørnepunkterne."""
    y0, y1 = lok[:, 1].min(), lok[:, 1].max()
    res = []
    for y in (y0, y1):
        xs = lok[np.abs(lok[:, 1] - y) < tol, 0]
        res.append((y, float(xs.max() - xs.min()) if len(xs) else None))
    return res


def _inderside(f, e, lok_y, M_lok, skala):
    """Hvilken side (y-værdi i lokale koordinater) vender ind mod etagens midte? None, hvis det ikke giver mening."""
    st = etage_af(e)
    if st is None:
        return None
    pts = []
    for w in f.by_type("IfcWall"):
        if etage_af(w) == st:
            M = up.get_local_placement(w.ObjectPlacement)
            pts.append(M[:2, 3] * skala)
    if len(pts) < 3:
        return None
    c = np.mean(pts, axis=0)
    M = M_lok.copy()
    M[:3, 3] *= skala
    cl = (np.linalg.inv(M) @ np.array([c[0], c[1], M[2, 3], 1.0]))[1]
    return min(lok_y, key=lambda y: abs(y - cl))


def _aabninger(e, skala):
    rows = []
    for rel in getattr(e, "HasOpenings", []) or []:
        o = rel.RelatedOpeningElement
        fyld = [r.RelatedBuildingElement for r in getattr(o, "HasFillings", []) or []]
        m = _mesh(o)
        if m is None:
            continue
        lok = _lokal(e, m[0], skala)
        x0, x1 = lok[:, 0].min(), lok[:, 0].max()
        z0, z1 = lok[:, 2].min(), lok[:, 2].max()
        navn = _navn(fyld[0]) if fyld else _navn(o)
        klasse = fyld[0].is_a()[3:] if fyld else "hul"
        rows.append((x0, f"    {navn} ({klasse}): fra væggens start {x0:.0f} · bredde {x1 - x0:.0f} · "
                         f"brystning {max(z0, 0):.0f} · højde {z1 - z0:.0f}"))
    return [r for _, r in sorted(rows)]


def element(f, e) -> int:
    skala = _skala(f)
    st = etage_af(e)
    print(f"{_navn(e)} · {e.is_a()} · etage {st.Name if st else '-'}"
          + (f" · type '{ue.get_type(e).Name}'" if ue.get_type(e) else ""))
    m = _mesh(e)
    if m is None:
        print("  ingen geometri – kan ikke måles")
        return 1
    v, fa = m
    if e.is_a("IfcSpace"):
        return _rum(e, v, fa)
    q = _qto_laengder(e, skala)
    if e.is_a("IfcWall") and getattr(e, "ObjectPlacement", None):
        lok = _lokal(e, v, skala)
        L = float(lok[:, 0].max() - lok[:, 0].min())
        t = float(lok[:, 1].max() - lok[:, 1].min())
        h = float(lok[:, 2].max() - lok[:, 2].min())
        print(f"  længde (største) {L:.0f} · tykkelse {t:.0f} · højde {h:.0f}"
              + (f" · Qto: længde {q['Length']:.0f}" if "Length" in q else "")
              + f" · underkant kote {v[:, 2].min():+.0f}")
        sider = _sideflader(lok)
        ude = ue.get_psets(e).get("Pset_WallCommon", {}).get("IsExternal")
        ind = (_inderside(f, e, [y for y, _ in sider], up.get_local_placement(e.ObjectPlacement), skala)
               if ude is not False else None)  # en indervæg har ingen inder- og yderside
        for y, laengde in sider:
            mrk = "" if ind is None else (" (inderside)" if y == ind else " (yderside)")
            print(f"  flade{mrk}: {laengde:.0f}" if laengde is not None else f"  flade{mrk}: ?")
        ab = _aabninger(e, skala)
        if ab:
            print("  åbninger (mål langs væggen fra dens startpunkt):")
            print("\n".join(ab))
    else:
        d = v.max(axis=0) - v.min(axis=0)
        print(f"  udstrækning x {d[0]:.0f} · y {d[1]:.0f} · z {d[2]:.0f} · underkant kote {v[:, 2].min():+.0f}"
              + "".join(f" · Qto {k} {x:.0f}" for k, x in q.items()))
    print("  " + _kilde(e))
    return 0


def _rum(e, v, fa) -> int:
    fp = _fodaftryk(v, fa)
    r = fp.minimum_rotated_rectangle
    xy = np.array(r.exterior.coords)[:4]
    a, b = sorted([float(np.linalg.norm(xy[1] - xy[0])), float(np.linalg.norm(xy[2] - xy[1]))], reverse=True)
    form = "rektangulært" if fp.area / max(r.area, 1) > 0.98 else f"ikke rektangulært ({fp.area / r.area:.0%} af den omskrevne firkant)"
    print(f"  {getattr(e, 'LongName', None) or e.Name}: indvendigt {a:.0f} × {b:.0f} ({form}) · gulvareal {fp.area / 1e6:.2f} m² "
          f"· omkreds {fp.exterior.length:.0f}")
    print(f"  højde {v[:, 2].max() - v[:, 2].min():.0f} (største; gulv kote {v[:, 2].min():+.0f})")
    print("  " + _kilde(e))
    return 0


def afstand(f, a, b) -> int:
    ma, mb = _mesh(a), _mesh(b)
    if ma is None or mb is None:
        print("Mindst ét af elementerne har ingen geometri")
        return 1
    pa, pb = _fodaftryk(*ma), _fodaftryk(*mb)
    d = pa.distance(pb)
    p, q = nearest_points(pa, pb)
    za = (ma[0][:, 2].min(), ma[0][:, 2].max())
    zb = (mb[0][:, 2].min(), mb[0][:, 2].max())
    print(f"{_navn(a)} → {_navn(b)}: vandret fri afstand {d:.0f} (set ovenfra, mellem nærmeste flader; "
          f"fra ({p.x:.0f}, {p.y:.0f}) til ({q.x:.0f}, {q.y:.0f}))")
    lodret = max(zb[0] - za[1], za[0] - zb[1])
    if lodret > 0:
        print(f"  lodret afstand {lodret:.0f} (elementerne overlapper ikke i højden)")
    print(f"  {_navn(a)}: {_kilde(a)}")
    print(f"  {_navn(b)}: {_kilde(b)}")
    return 0


def etage(f, noegle) -> int:
    n = noegle.casefold()
    st = [s for s in f.by_type("IfcBuildingStorey") if n in (str(s.Name or "").casefold(), str(s.LongName or "").casefold())]
    if not st:
        print(f"Etage ikke fundet: {noegle}. Findes: " + ", ".join(s.Name or "?" for s in f.by_type("IfcBuildingStorey")))
        return 1
    st = st[0]
    skala = _skala(f)
    vaegge = sorted((w for w in f.by_type("IfcWall") if etage_af(w) == st), key=_navn)
    print(f"{st.Name}: {len(vaegge)} vægge (mm) · id | type | længde | tykkelse | højde | kilde")
    for w in vaegge:
        q = _qto_laengder(w, skala)
        if not {"Length", "Width", "Height"} <= q.keys():
            m = _mesh(w)
            if m is not None:
                lok = _lokal(w, m[0], skala)
                ext = lok.max(axis=0) - lok.min(axis=0)
                q = {"Length": ext[0], "Width": ext[1], "Height": ext[2], **q}
        t = ue.get_type(w)
        k = ue.get_psets(w).get("Byg_Kilde") or {}
        print(f"  {_navn(w)} | {t.Name if t else '-'} | {q.get('Length', 0):.0f} | {q.get('Width', 0):.0f} | "
              f"{q.get('Height', 0):.0f} | {k.get('Kilde', '?')}" + (f" ({k['Reference']})" if k.get("Reference") else ""))
    rum = [s for s in f.by_type("IfcSpace") if ue.get_aggregate(s) == st]
    if rum:
        print("Rum: " + ", ".join(f"{s.Name} {s.LongName or ''}".strip() for s in rum) + "  (mål: maal <ifc> --rum <navn>)")
    return 0


def _aabn(model: pathlib.Path):
    """IFC-fil direkte, eller en spec (model.yaml/forslag), der bygges i en midlertidig mappe – så måles den aktuelle model,
    også når ud/*.ifc ikke er bygget efter seneste fletning."""
    if model.suffix.lower() not in (".yaml", ".yml"):
        return ifcopenshell.open(str(model))
    from .build import byg
    from .spec import indlaes
    with tempfile.TemporaryDirectory() as d, contextlib.redirect_stdout(io.StringIO()):
        byg(indlaes(model), pathlib.Path(d) / "m.ifc")
        return ifcopenshell.open(str(pathlib.Path(d) / "m.ifc"))


def maal(ifc: pathlib.Path, a=None, b=None, rum=None, etage_navn=None) -> int:
    f = _aabn(pathlib.Path(ifc))
    if etage_navn:
        return etage(f, etage_navn)
    noegler = [x for x in (rum, a, b) if x]
    if not noegler:
        print("Angiv et element, --rum <navn> eller --etage <navn> (se bim.py --help)")
        return 2
    ents = []
    for n in noegler:
        e = _find(f, n)
        if e is None or (rum and n == rum and not e.is_a("IfcSpace")):
            print(f"Ikke fundet: {n} (brug Tag/spec-id, navn, rumnavn, GlobalId eller #step-id; 'find' viser id'er)")
            return 1
        ents.append(e)
    if len(ents) == 2:
        return afstand(f, *ents)
    return element(f, ents[0])
