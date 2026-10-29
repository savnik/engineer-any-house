"""Interactive HTML view (plotly, works offline): model with loads, M/V/N curves and deformation for members,
colour maps on shells (stress, membrane forces, plate moments, displacement) per combination with values on
hover, plus tables of reactions and results. Combination, quantity, load case and shells are chosen
in menus above the figure."""
import html
import json
import math
import pathlib

import plotly.graph_objects as go

from . import shells as fl
from . import loads as la
from .draw import COLOUR, SHELL_Q, _fmt, _point, colour_scale, file_name

MEMBER_Q = ("M", "V", "N", "d")


def _hover(en, e, c, i):
    return (f"<b>{en}</b> · {e['profil']} · {e['materiale']}<br>x = {_fmt(c['x'][i], 2)} m af {_fmt(e['_L'], 2)} m<br>"
            f"M = {_fmt(c['M'][i], 2)} kNm<br>V = {_fmt(c['V'][i], 2)} kN<br>N = {_fmt(c['N'][i], 2)} kN<br>"
            f"δ = {_fmt(c.get('d_spaend', c['d'])[i], 2)} mm" + (" (over hele spændet)" if "d_spaend" in c else ""))


def _xyz(p, plan):
    return (p[0], p[2]) if plan else (p[0], p[1], p[2])


def _line(pts, plan, **kw):
    if plan:
        return go.Scatter(x=[p[0] for p in pts], y=[p[1] for p in pts], mode="lines", **kw)
    return go.Scatter3d(x=[p[0] for p in pts], y=[p[1] for p in pts], z=[p[2] for p in pts], mode="lines", **kw)


def _tables(res: dict) -> str:
    out = []
    for kn, k in res["kombinationer"].items():
        out.append(f"<h3>{html.escape(kn)} <span class=t>({k['type']}: "
                  + " + ".join(f"{f}·{lt}" for lt, f in (k['faktorer'] or {}).items()) + ")</span></h3>")
        balanced = all(v["ok"] for v in k["ligevaegt"].values())
        out.append("<p class=t>Ligevægt: " + ("OK" if balanced else "<b>FEJL</b>") + " · "
                  + " · ".join(f"Σ{a}: R {_fmt(v['reaktioner'], 2)} / last {_fmt(v['laster'], 2)} kN"
                               for a, v in k["ligevaegt"].items() if abs(v["laster"]) > 1e-9 or abs(v["reaktioner"]) > 1e-9)
                  + "</p>")
        out.append("<table><tr><th>Understøtning</th><th>Reaktioner (kN, kNm)</th></tr>")
        for kn2, r in k["reaktioner"].items():
            out.append(f"<tr><td>{html.escape(kn2)}</td><td>" + ", ".join(f"{a} = {_fmt(v, 2)}" for a, v in r.items())
                      + "</td></tr>")
        out.append("</table>")
        if k["elementer"]:
            out.append("<table><tr><th>Element</th><th>Profil</th><th>L [m]</th><th>N [kN]</th><th>|V| [kN]</th>"
                      "<th>M [kNm]</th><th>δ [mm]</th>" + ("<th>L/δ</th>" if k["type"] == "anvendelse" else "") + "</tr>")
            for en, e in k["elementer"].items():
                ld = ""
                if k["type"] == "anvendelse":
                    ok = e.get("nedboejning_ok")
                    ld = (f"<td class={'ok' if ok else ('fejl' if ok is False else '')}>"
                          f"{'L/' + str(e['L_over_delta']) if e.get('L_over_delta') else '–'}"
                          f"{' (krav ' + e['graense'] + ')' if e.get('graense') else ''}</td>")
                out.append(f"<tr><td>{en}</td><td>{html.escape(str(e['profil']))}</td><td>{_fmt(e['L'], 2)}</td>"
                          f"<td>{_fmt(e['N_min'])} … {_fmt(e['N_max'])}</td><td>{_fmt(e['V_abs_max'])}</td>"
                          f"<td>{_fmt(e['M_min'])} … {_fmt(e['M_max'])}</td><td>{_fmt(e['delta_mm'])}</td>{ld}</tr>")
            out.append("</table>")
        if k.get("flader"):
            out.append("<table><tr><th>Flade</th><th>t [mm]</th><th>Materiale</th><th>σ_vM maks [MPa] (sted x, y, z)</th>"
                      "<th>n_u [kN/m]</th><th>n_v [kN/m]</th><th>|m| maks [kNm/m]</th><th>Flytning maks [mm]</th></tr>")
            for fn, f in k["flader"].items():
                st = f["steder_med_stoerst_spaending"][0]["xyz"]
                out.append(f"<tr><td>{html.escape(fn)}</td><td>{f['tykkelse_mm']}</td><td>{html.escape(f['materiale'])}</td>"
                          f"<td>{_fmt(f['sigma_vM_max_MPa'], 2)} ({', '.join(_fmt(c, 2) for c in st)})</td>"
                          f"<td>{_fmt(f['n_u_min_kN_m'])} … {_fmt(f['n_u_max_kN_m'])}</td>"
                          f"<td>{_fmt(f['n_v_min_kN_m'])} … {_fmt(f['n_v_max_kN_m'])}</td>"
                          f"<td>{_fmt(f['m_abs_max_kNm_m'], 2)}</td><td>{_fmt(f['flytning_max_mm'], 2)}</td></tr>")
            out.append("</table>")
        if k.get("udtraek"):
            out.append("<table><tr><th>Udtræk</th><th>Område</th><th>σ_vM maks [MPa]</th><th>n_u [kN/m]</th>"
                      "<th>n_v [kN/m]</th><th>|m| maks [kNm/m]</th></tr>")
            for un, u in k["udtraek"].items():
                if "fejl" in u:
                    out.append(f"<tr><td>{html.escape(un)}</td><td colspan=5>{html.escape(u['fejl'])}</td></tr>")
                    continue
                out.append(f"<tr><td>{html.escape(un)}</td><td>{html.escape(u['flade'])}: x {u['x']}, y {u['y']}</td>"
                          f"<td>{_fmt(u['sigma_vM_max_MPa'], 2)}</td><td>{_fmt(u['n_u_min_kN_m'])} … {_fmt(u['n_u_max_kN_m'])}</td>"
                          f"<td>{_fmt(u['n_v_min_kN_m'])} … {_fmt(u['n_v_max_kN_m'])}</td><td>{_fmt(u['m_abs_max_kNm_m'], 2)}</td></tr>")
            out.append("</table>")
    return "\n".join(out)


def _r(v, n=4):
    return round(float(v), n)


def _shell_data(s: dict, curves: dict) -> dict:
    """Geometry (4 corners per quad, not shared, so each quad can be coloured on its own) and values per combination."""
    pts = fl.all_nodes(s)
    D = {"flader": {}, "kombi": {}, "skala": {}}
    for fn in s["flader"]:
        qs = [(qn, kn) for qn, f2, kn, _ in s["_quads"] if f2 == fn]
        D["flader"][fn] = {"xyz": [[_r(c) for c in pts[k]] for _, kn in qs for k in kn],
                           "q": [qn for qn, _ in qs], "kn": [k for _, kn in qs for k in kn]}
    for kn in s["kombinationer"]:
        kv = curves[kn]
        q = kv["flader"]["quads"]
        D["kombi"][kn] = {fn: {"S": [_r(q[qn]["svm"], 3) for qn in g["q"]],
                               "nu": [_r(q[qn]["nu"], 2) for qn in g["q"]],
                               "nv": [_r(q[qn]["nv"], 2) for qn in g["q"]],
                               "mu": [_r(q[qn]["mu"], 3) for qn in g["q"]],
                               "mv": [_r(q[qn]["mv"], 3) for qn in g["q"]],
                               "u": [[_r(c, 3) for c in kv["flader"]["flytning"][k]] for k in g["kn"]]}
                          for fn, g in D["flader"].items()}
        for st in SHELL_Q:
            _, vmin, vmax, cm, note = colour_scale(s, kv, st)
            D["skala"][f"{kn}|{st}"] = [vmin, vmax, cm, note]
        umax = max(math.hypot(*f) for f in kv["flader"]["flytning"].values()) or 1.0
        D["skala"][f"{kn}|ufak"] = 0.08 * la.span(s) / (umax / 1000)
    for g in D["flader"].values():
        del g["q"], g["kn"]
    return D


def _loads(fig, s, plan) -> dict:
    """Arrows for each load case (shaft + tip) and texts; returns {load case: [trace index]}."""
    idx = {}
    sp = la.span(s)
    for lt, g in la.arrows(s).items():
        f = la.colour(s, lt)
        start = len(fig.data)
        shafts = []
        for p in g["pile"]:
            shafts += [_xyz(p["start"], plan), _xyz(p["spids"], plan), None]
        for li in g.get("linjer", []):
            shafts += [_xyz(p, plan) for p in li] + [None]
        name = " · ".join(t for _, t in g["tekster"]) or lt
        grp = dict(legendgroup=lt)
        if shafts:
            if plan:
                fig.add_trace(go.Scatter(x=[p[0] if p else None for p in shafts], y=[p[1] if p else None for p in shafts],
                                         mode="lines", line=dict(color=f, width=1.5), name=name, hoverinfo="skip", **grp))
                fig.add_trace(go.Scatter(x=[p["spids"][0] for p in g["pile"]], y=[p["spids"][2] for p in g["pile"]],
                                         mode="markers", marker=dict(symbol="triangle-down" if all(
                                             p["spids"][2] < p["start"][2] for p in g["pile"]) else "circle",
                                             size=8, color=f), hoverinfo="skip", showlegend=False, **grp))
            else:
                fig.add_trace(go.Scatter3d(x=[p[0] if p else None for p in shafts], y=[p[1] if p else None for p in shafts],
                                           z=[p[2] if p else None for p in shafts], mode="lines",
                                           line=dict(color=f, width=4), name=name, hoverinfo="skip", **grp))
                if g["pile"]:
                    d = [[(p["spids"][i] - p["start"][i]) / max(la.length(p), 1e-9) for i in range(3)] for p in g["pile"]]
                    fig.add_trace(go.Cone(x=[p["spids"][0] for p in g["pile"]], y=[p["spids"][1] for p in g["pile"]],
                                          z=[p["spids"][2] for p in g["pile"]], u=[v[0] for v in d], v=[v[1] for v in d],
                                          w=[v[2] for v in d], anchor="tip", sizemode="absolute", sizeref=0.035 * sp,
                                          colorscale=[[0, f], [1, f]], showscale=False, hoverinfo="skip", showlegend=False,
                                          **grp))
        tk = [(pos, t) for pos, t in g["tekster"] if pos is not None]
        if tk:
            if plan:
                fig.add_trace(go.Scatter(x=[p[0] for p, _ in tk], y=[p[2] for p, _ in tk], mode="text",
                                         text=[t for _, t in tk], textfont=dict(color=f, size=12), hoverinfo="skip",
                                         showlegend=not shafts, name=name, **grp))
            else:
                fig.add_trace(go.Scatter3d(x=[p[0] for p, _ in tk], y=[p[1] for p, _ in tk], z=[p[2] for p, _ in tk],
                                           mode="text", text=[t for _, t in tk], textfont=dict(color=f, size=12),
                                           hoverinfo="skip", showlegend=not shafts, name=name, **grp))
        idx[lt] = list(range(start, len(fig.data)))
    return idx


SIDE = """<!doctype html><html lang="da"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1"><title>__TITEL__ · FEM</title>
<style>body{font-family:system-ui,-apple-system,sans-serif;margin:16px;color:#222;max-width:1250px}
h1{font-size:20px;margin:0 0 4px} h3{font-size:15px;margin:22px 0 4px} .t{color:#666;font-weight:normal;font-size:13px}
table{border-collapse:collapse;margin:6px 0 10px;font-size:13px} td,th{border:1px solid #ddd;padding:3px 8px;text-align:left}
th{background:#f5f5f5} .ok{color:#1e8449} .fejl{color:#c0392b;font-weight:bold}
.note{background:#fff8e1;border:1px solid #f0d78c;padding:6px 10px;font-size:13px;margin:8px 0}
.styr{display:flex;flex-wrap:wrap;gap:8px 18px;align-items:center;font-size:14px;margin:8px 0}
.styr select{font-size:14px;padding:2px 4px} #skalanote{color:#666;font-size:12px}</style></head><body>
<h1>__TITEL__</h1>
<p class=t>__UNDERTITEL__</p>
<div class=note><b>OVERSLAG</b> – resultaterne skal eftervises af den ansvarlige statiker.__FLADENOTE__ __FORTEGN__</div>
<div class=styr><label>Kombination <select id=kombi>__KOMBI__</select></label>
<label>Størrelse <select id=st>__ST__</select></label>__BOKSE__<span id=skalanote></span></div>
__PLOT__
__TABELLER__
<script>
const D = __DATA__;
const fmt = (v, d) => v.toFixed(d).replace('.', ',').replace('-', '−');
const cache = {};
function hover(k, fn) {
  const key = k + '|' + fn;
  if (cache[key]) return cache[key];
  const v = D.F.kombi[k][fn], ud = [];
  for (let q = 0; q < v.S.length; q++) {
    const t = `<b>${fn}</b><br>σ_vM = ${fmt(v.S[q], 2)} MPa<br>n_u = ${fmt(v.nu[q], 1)} kN/m · n_v = ${fmt(v.nv[q], 1)} kN/m`
      + `<br>m_u = ${fmt(v.mu[q], 2)} · m_v = ${fmt(v.mv[q], 2)} kNm/m`;
    for (let a = 0; a < 4; a++) {
      const u = v.u[4 * q + a];
      ud.push(t + `<br>flytning = ${fmt(Math.hypot(u[0], u[1], u[2]), 2)} mm`);
    }
  }
  return cache[key] = ud;
}
function vaerdi(v, st, q) {
  if (st === 'm') return Math.max(Math.abs(v.mu[q]), Math.abs(v.mv[q]));
  if (st === 'u') { let s = 0; for (let a = 0; a < 4; a++) { const u = v.u[4 * q + a]; s += Math.hypot(u[0], u[1], u[2]); } return s / 4; }
  return v[st][q];
}
const CS = D.CS;
const ENH = {S: 'MPa', nu: 'kN/m', nv: 'kN/m', m: 'kNm/m', u: 'mm'};
function opdater() {
  const k = document.getElementById('kombi').value, st = document.getElementById('st').value;
  const gd = document.getElementById('fem');
  const synlig = gd.data.map(t => false);
  D.faste.forEach(i => synlig[i] = true);
  (D.grupper[k + '|' + st] || []).forEach(i => synlig[i] = true);
  Object.values(D.laster).forEach(ix => ix.forEach(i => synlig[i] = gd.data[ix[0]].visible === 'legendonly' ? 'legendonly' : true));
  const valgte = new Set([...document.querySelectorAll('input.fl:checked')].map(c => c.value));
  let note = '';
  if (D.F) {
    const fst = D.FST.includes(st), sk = D.F.skala[k + '|' + st] || [0, 1, 'turbo', ''], fak = D.F.skala[k + '|ufak'];
    let foerste = true;
    for (const [fn, ix] of Object.entries(D.flader)) {
      const vis = valgte.has(fn);
      synlig[ix[0]] = vis; synlig[ix[1]] = vis;
      const g = D.F.flader[fn], v = D.F.kombi[k][fn], n = g.xyz.length / 4, f = (st === 'u') ? fak / 1000 : 0;
      const x = [], y = [], z = [], I = [], kx = [], ky = [], kz = [];
      for (let p = 0; p < g.xyz.length; p++) {
        const u = v.u[p];
        x.push(g.xyz[p][0] + f * u[0]); y.push(g.xyz[p][1] + f * u[1]); z.push(g.xyz[p][2] + f * u[2]);
      }
      for (let q = 0; q < n; q++) {
        const w = fst ? vaerdi(v, st, q) : 0; I.push(w, w);
        for (const a of [0, 1, 2, 3, 0]) { kx.push(x[4 * q + a]); ky.push(y[4 * q + a]); kz.push(z[4 * q + a]); }
        kx.push(null); ky.push(null); kz.push(null);
      }
      Plotly.restyle(gd, {x: [x], y: [y], z: [z], intensity: [I], text: [hover(k, fn)],
        colorscale: [fst ? CS[sk[2]] : [[0, '#cccccc'], [1, '#cccccc']]], cmin: [sk[0]], cmax: [sk[1]],
        showscale: [fst && vis && foerste], opacity: [fst ? 1 : 0.45],
        'colorbar.title.text': [ENH[st] || '']}, [ix[0]]);
      Plotly.restyle(gd, {x: [kx], y: [ky], z: [kz]}, [ix[1]]);
      if (fst && vis) foerste = false;
    }
    if (fst) note = (sk[3] || '').replace(/\\./g, ',') + (st === 'u' ? ` · forstørret ×${Math.round(fak)}` : '');
  }
  document.getElementById('skalanote').textContent = note;
  Plotly.restyle(gd, {visible: synlig});
}
document.getElementById('kombi').onchange = opdater;
document.getElementById('st').onchange = opdater;
document.querySelectorAll('input.fl').forEach(c => c.onchange = opdater);
window.addEventListener('load', opdater);
</script>
</body></html>"""


def view(s: dict, curves: dict, res: dict, out_dir: pathlib.Path, cdn: bool = False) -> pathlib.Path:
    """cdn: load plotly.js from its CDN instead of embedding it (a small file for the web; needs internet)."""
    plan = s["_plan"]
    span = la.span(s)
    fig = go.Figure()
    fixed = []
    for en, e in s["elementer"].items():
        pts = [_point(s, e, i / 20) for i in range(21)]
        txt = (f"<b>{en}</b> · {e['profil']} · {e['materiale']}<br>{e['fra']} → {e['til']} · L = {_fmt(e['_L'], 2)} m"
               + (f"<br>led: {', '.join(e['led']) if isinstance(e.get('led'), list) else e['led']}" if e.get("led") else ""))
        fixed.append(len(fig.data))
        fig.add_trace(_line([_xyz(p, plan) for p in pts], plan, line=dict(color="#222", width=4), name=en,
                             text=[txt] * len(pts), hoverinfo="text", showlegend=False))
    rtxt = []
    for k in s["understoetninger"]:
        lines = [f"<b>{k}</b> ({s['understoetninger'][k]})"]
        for kn, kk in res["kombinationer"].items():
            lines.append(f"{kn}: " + ", ".join(f"{a} = {_fmt(v, 1)}" for a, v in kk["reaktioner"][k].items()))
        rtxt.append("<br>".join(lines))
    sp = [s["knuder"][k] for k in s["understoetninger"]]
    if sp:
        fixed.append(len(fig.data))
        if plan:
            fig.add_trace(go.Scatter(x=[p[0] for p in sp], y=[p[2] for p in sp], mode="markers",
                                     marker=dict(symbol="triangle-up", size=14, color="#1a5276"),
                                     text=rtxt, hoverinfo="text", showlegend=False))
        else:
            fig.add_trace(go.Scatter3d(x=[p[0] for p in sp], y=[p[1] for p in sp], z=[p[2] for p in sp], mode="markers",
                                       marker=dict(symbol="diamond", size=6, color="#1a5276"), text=rtxt, hoverinfo="text",
                                       showlegend=False))
    for ls in s["understoetninger_linje"]:
        nv = f"linje {ls['fra']}–{ls['til']}"
        txt = f"<b>{nv}</b> ({ls.get('type', 'charnier')})<br>" + "<br>".join(
            f"{kn}: " + ", ".join(f"{a} = {_fmt(v, 1)}" for a, v in kk["reaktioner"][nv].items())
            for kn, kk in res["kombinationer"].items())
        fixed.append(len(fig.data))
        fig.add_trace(_line([_xyz(s["knuder"][ls["fra"]], plan), _xyz(s["knuder"][ls["til"]], plan)], plan,
                             line=dict(color="#1a5276", width=9), text=[txt, txt], hoverinfo="text", showlegend=False))
    # shells: one Mesh3d + grid lines per shell; colours and shape are set by the script for the chosen combination and quantity
    shell_idx = {}
    fdata = _shell_data(s, curves) if s["flader"] else None
    for fn in s["flader"]:
        xyz = fdata["flader"][fn]["xyz"]
        n = len(xyz) // 4
        shell_idx[fn] = [len(fig.data), len(fig.data) + 1]
        fig.add_trace(go.Mesh3d(x=[p[0] for p in xyz], y=[p[1] for p in xyz], z=[p[2] for p in xyz],
                                i=[4 * q for q in range(n) for _ in (0, 1)],
                                j=[4 * q + a for q in range(n) for a in (1, 2)],
                                k=[4 * q + a for q in range(n) for a in (2, 3)], intensity=[0] * (2 * n),
                                intensitymode="cell", colorscale=[[0, "#cccccc"], [1, "#cccccc"]], showscale=False,
                                flatshading=True, name=fn, hovertemplate="%{text}<extra></extra>", text=[fn] * len(xyz),
                                lighting=dict(ambient=0.8, diffuse=0.4, specular=0.05)))
        edges = []
        for q in range(n):
            edges += [xyz[4 * q + a] for a in (0, 1, 2, 3, 0)] + [None]
        fig.add_trace(go.Scatter3d(x=[p[0] if p else None for p in edges], y=[p[1] if p else None for p in edges],
                                   z=[p[2] if p else None for p in edges], mode="lines",
                                   line=dict(color="rgba(0,0,0,0.35)", width=1), hoverinfo="skip", showlegend=False))
    load_idx = _loads(fig, s, plan)
    # member curves per combination and quantity (scale shared by all combinations, so they can be compared)
    scale = {}
    for st in MEMBER_Q if s["elementer"] else ():
        vmax = max(max(abs(v) for v in c[st]) for kn in s["kombinationer"] for c in curves[kn]["elementer"].values())
        if st == "d":
            fmax = max((math.hypot(*f) for kn in s["kombinationer"] for f in curves[kn]["flytning"].values()), default=0)
            vmax = max(vmax, fmax)
            scale[st] = span * 0.08 / (vmax / 1000) if vmax > 1e-9 else 1.0
        else:
            scale[st] = span * 0.12 / vmax if vmax > 1e-9 else 1.0
    groups = {}
    for kn in s["kombinationer"]:
        kv = curves[kn]
        for st in MEMBER_Q if s["elementer"] else ():
            start = len(fig.data)
            for en, e in s["elementer"].items():
                c = kv["elementer"][en]
                ny = curves["_lokal_y"][en]
                pts = []
                for i, x in enumerate(c["x"]):
                    t = x / e["_L"]
                    p = _point(s, e, t)
                    if st == "d":
                        fa, fb = kv["flytning"][e["fra"]], kv["flytning"][e["til"]]
                        u = [(fa[j] + (fb[j] - fa[j]) * t) / 1000 + c["d"][i] / 1000 * ny[j] for j in range(3)]
                        q = [p[j] + scale[st] * u[j] for j in range(3)]
                    else:
                        sgn = -1 if st == "M" else 1
                        q = [p[j] + sgn * scale[st] * c[st][i] * ny[j] for j in range(3)]
                    pts.append(_xyz(q, plan))
                text = [_hover(en, e, c, i) for i in range(len(c["x"]))]
                fill = {} if (st == "d" or not plan) else dict(fill="toself", fillcolor="rgba(0,0,0,0.06)")
                if st != "d" and plan:  # close the curve towards the member axis
                    a0, a1 = _xyz(_point(s, e, 0), plan), _xyz(_point(s, e, 1), plan)
                    pts = [a0] + pts + [a1]
                    text = [text[0]] + text + [text[-1]]
                fig.add_trace(_line(pts, plan, line=dict(color=COLOUR[st], width=3), text=text, hoverinfo="text",
                                     visible=False, showlegend=False, **fill))
            groups[f"{kn}|{st}"] = list(range(start, len(fig.data)))
    fig.update_layout(margin=dict(l=10, r=10, t=10, b=10), height=680, plot_bgcolor="white",
                      hoverlabel=dict(bgcolor="white", font_size=13),
                      legend=dict(title=dict(text="Laster (klik for at skjule)"), x=0, y=1, bgcolor="rgba(255,255,255,0.7)"))
    if plan:
        fig.update_xaxes(title="x [m]", scaleanchor="y", scaleratio=1, showgrid=True, gridcolor="#eee", zeroline=False)
        fig.update_yaxes(title="z [m]", showgrid=True, gridcolor="#eee", zeroline=False)
    else:
        fig.update_layout(scene=dict(aspectmode="data", xaxis_title="x [m]", yaxis_title="y [m]", zaxis_title="z [m]",
                                     camera=dict(eye=dict(x=-1.3, y=-1.6, z=0.9))))
    plot = fig.to_html(include_plotlyjs="cdn" if cdn else True, full_html=False, div_id="fem",
                       config={"displaylogo": False, "responsive": True})
    combos = list(s["kombinationer"])
    uls = [k for k in combos if s["kombinationer"][k]["type"] == "brud"]
    q_options = ([("S", "Spænding σ_vM (MPa)"), ("nv", "Membrankraft n_v (kN/m) – lodret i vægge"),
                ("nu", "Membrankraft n_u (kN/m)"), ("m", "Pladmoment |m| (kNm/m)"), ("u", "Flytning (mm, forstørret)")]
               if s["flader"] else []) + \
              ([("M", "Moment M (kNm)"), ("V", "Forskydning V (kN)"), ("N", "Normalkraft N (kN)"),
                ("d", "Deformation, elementer (forstørret)")] if s["elementer"] else [])
    import matplotlib.pyplot as plt
    cs = {}
    for name in ("turbo", "RdBu"):
        cm = plt.get_cmap(name)
        cs[name] = [[i / 20, "rgb({},{},{})".format(*(round(255 * c) for c in cm(i / 20)[:3]))] for i in range(21)]
    data = {"faste": fixed, "grupper": groups, "flader": shell_idx, "laster": load_idx, "F": fdata, "FST": list(SHELL_Q),
            "CS": cs}
    replacements = {
        "__TITEL__": html.escape(s["navn"]),
        "__UNDERTITEL__": (f"FEM-model (PyNite {res['pynite']}, {res['analyse']}) · spec "
                           f"{html.escape(pathlib.Path(s['_sti']).name)} · sha {s['_sha']} · enheder kN, kNm, m, mm, MPa"),
        "__FLADENOTE__": (" Flader regnes lineært-elastisk uden revnedannelse, og spændingstoppe i hjørner af åbninger "
                          "afhænger af meshet: brug dem til at se, hvor lasten samler sig, ikke som bæreevne."
                          if s["flader"] else ""),
        "__FORTEGN__": html.escape(res["fortegn"]),
        "__KOMBI__": "".join(f"<option{' selected' if k == (uls or combos)[0] else ''}>{html.escape(k)}</option>"
                             for k in combos),
        "__ST__": "".join(f"<option value='{v}'>{html.escape(t)}</option>" for v, t in q_options)
                  + "<option value=''>Kun model</option>",
        "__BOKSE__": ("<span>Flader: " + "".join(
            f"<label><input type=checkbox class=fl value='{html.escape(fn)}' checked> {html.escape(fn)}</label> "
            for fn in s["flader"]) + "</span>") if s["flader"] else "",
        "__TABELLER__": _tables(res),
        "__DATA__": json.dumps(data, ensure_ascii=False, separators=(",", ":")),
    }
    page = SIDE
    for a, b in replacements.items():
        page = page.replace(a, b)
    page = page.replace("__PLOT__", plot)  # last, so the plotly code is not searched for placeholders
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / file_name(f"{s['navn']}.html")
    path.write_text(page, encoding="utf-8")
    return path
