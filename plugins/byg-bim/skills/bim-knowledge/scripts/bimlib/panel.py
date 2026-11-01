"""Panel export: a distribution board in the model spec → el.py's panel format (JSON).

Read from the spec, not the IFC, so the electrical data stays exactly as written. Group lengths are measured
along the cable segments (`roer` with art kabel): the longest route from the board to the end of the group,
rounded up to whole metres, unless the group's `el.laengde` is given."""
import heapq
import json
import math
import pathlib

from .spec import SpecError, load

TOL = 1.0  # mm – a branch starting on another segment is joined to it


def _on_segment(p, a, b):
    ab = [b[i] - a[i] for i in range(3)]
    ap = [p[i] - a[i] for i in range(3)]
    n2 = sum(x * x for x in ab)
    if n2 == 0:
        return None
    t = sum(ab[i] * ap[i] for i in range(3)) / n2
    if not 0 < t < 1:
        return None
    q = [a[i] + t * ab[i] for i in range(3)]
    return t if math.dist(p, q) <= TOL else None


def _graph(runs):
    """Cable runs (lists of 3D points) → adjacency {point: {point: length}}; a run's end lying on another run's
    segment splits that segment, so branches join their trunk."""
    ends = [tuple(p) for r in runs for p in r]
    adj = {}
    for r in runs:
        for a, b in zip(r, r[1:]):
            a, b = tuple(a), tuple(b)
            cuts = sorted({(t, p) for p in ends if (t := _on_segment(p, a, b)) is not None})
            chain = [a] + [p for _, p in cuts] + [b]
            for u, v in zip(chain, chain[1:]):
                d = math.dist(u, v)
                adj.setdefault(u, {})[v] = d
                adj.setdefault(v, {})[u] = d
    return adj


def route_length(runs, origin):
    """Longest shortest-path distance (mm) from the point nearest `origin` to any point of the runs, and the total
    cable length (mm)."""
    if not runs:
        return 0.0, 0.0
    adj = _graph(runs)
    total = sum(math.dist(a, b) for r in runs for a, b in zip(r, r[1:]))
    start = min(adj, key=lambda p: math.dist(p, origin))
    dist, todo = {start: 0.0}, [(0.0, start)]
    while todo:
        d, u = heapq.heappop(todo)
        if d > dist[u]:
            continue
        for v, w in adj[u].items():
            if d + w < dist.get(v, math.inf):
                dist[v] = d + w
                heapq.heappush(todo, (d + w, v))
    return max(dist.values()), total


def _metres(mm):
    return float(math.ceil(mm / 1000.0 - 1e-9))


def panel_data(spec, board=None):
    inst = spec.get("installationer", [])
    by_id = {i["id"]: i for i in inst}
    boards = [i for i in inst if i.get("art") == "tavle" and (board is None or i["id"] == board)]
    if not boards:
        raise SpecError([f"ingen tavle '{board}'" if board else "ingen installation med art tavle"])
    t = boards[0]
    sysid = t.get("system")
    cables = [r for r in spec.get("roer", []) if r.get("art") == "kabel"]
    origin = t["punkt"]
    el = t.get("el") or {}
    tavle = {**el, "id": t["id"], "navn": el.get("navn", t.get("navn", t["id"]))}
    feeder = [r["punkter"] for r in cables if r.get("system") == sysid]
    if feeder and isinstance(tavle.get("stikledning"), dict) and "laengde" not in tavle["stikledning"]:
        tavle["stikledning"] = {**tavle["stikledning"], "laengde": _metres(route_length(feeder, origin)[1])}
    parts = [i for i in inst if i.get("del_af") == t["id"]]
    rcds = [{"id": i["id"], "navn": i.get("navn", i["id"]), **(i.get("el") or {})}
            for i in parts if i.get("art") == "fejlstroemsafbryder"]
    tavle["udstyr"] = [{"id": i["id"], "art": i["art"], "navn": i.get("navn", i["id"]), **(i.get("el") or {})}
                       for i in parts if i.get("art") not in ("fejlstroemsafbryder", "automatsikring")]
    up = by_id.get(t.get("del_af")) or next((i for i in inst if i.get("art") == "kabelskab"
                                             and i.get("system") == sysid), None)
    if up:
        tavle["kabelskab"] = {"id": up["id"], "navn": up.get("navn", up["id"]),
                              "udstyr": [{"id": i["id"], "art": i["art"], "navn": i.get("navn", i["id"]),
                                          **(i.get("el") or {})} for i in inst if i.get("del_af") == up["id"]]}
    groups = []
    for s in spec.get("systemer", []):
        if s.get("under") != sysid or not s.get("el"):
            continue
        g = {**s["el"], "navn": s["el"].get("navn", s.get("navn", s["id"])), "system": s["id"]}
        runs = [r["punkter"] for r in cables if r.get("system") == s["id"]]
        longest, total = route_length(runs, origin)
        if "laengde" not in g and runs:
            g["laengde"] = _metres(longest)
        g["kabel_total"] = round(total / 1000.0, 1)
        count = {}
        for i in inst:
            if i.get("system") == s["id"] and i.get("art") != "automatsikring":
                count[i["art"]] = count.get(i["art"], 0) + 1
        g["forsyner"] = count
        groups.append(g)
    groups.sort(key=lambda g: (g.get("nr") is None, g.get("nr", 0)))
    return {"tavle": tavle, "rcd": rcds, "grupper": groups}


def panel(spec_path, board=None, out=None):
    try:
        data = panel_data(load(spec_path), board)
    except SpecError as e:
        print(f"SPEC-FEJL ({len(e.errors)}):")
        for x in e.errors[:40]:
            print("  - " + x)
        return 1
    text = json.dumps(data, ensure_ascii=False, indent=2) + "\n"
    if out:
        pathlib.Path(out).write_text(text, encoding="utf-8")
        g = data["grupper"]
        print(f"TAVLE {data['tavle']['navn']}: {len(g)} grupper, {len(data['rcd'])} RCD'er → {out}")
        print("  næste: el.py panel " + str(out) + "  ·  diagram.py " + str(out))
    else:
        print(text, end="")
    return 0
