"""Interaktiv HTML-visning (plotly, virker offline): model, M/V/N-kurver og deformation pr. kombination med
værdier, når musen holdes over et element, samt tabeller med reaktioner og snitkræfter."""
import html
import math
import pathlib

import plotly.graph_objects as go

from .tegn import ENHED, FARVE, NAVN, _fmt, _punkt, _span, filnavn

STORRELSER = ("M", "V", "N", "d")


def _hover(en, e, c, i):
    return (f"<b>{en}</b> · {e['profil']} · {e['materiale']}<br>x = {_fmt(c['x'][i], 2)} m af {_fmt(e['_L'], 2)} m<br>"
            f"M = {_fmt(c['M'][i], 2)} kNm<br>V = {_fmt(c['V'][i], 2)} kN<br>N = {_fmt(c['N'][i], 2)} kN<br>"
            f"δ = {_fmt(c.get('d_spaend', c['d'])[i], 2)} mm" + (" (over hele spændet)" if "d_spaend" in c else ""))


def _xyz(p, plan):
    return (p[0], p[2]) if plan else (p[0], p[1], p[2])


def _linje(pts, plan, **kw):
    if plan:
        return go.Scatter(x=[p[0] for p in pts], y=[p[1] for p in pts], mode="lines", **kw)
    return go.Scatter3d(x=[p[0] for p in pts], y=[p[1] for p in pts], z=[p[2] for p in pts], mode="lines", **kw)


def _tabeller(res: dict) -> str:
    ud = []
    for kn, k in res["kombinationer"].items():
        ud.append(f"<h3>{html.escape(kn)} <span class=t>({k['type']}: "
                  + " + ".join(f"{f}·{lt}" for lt, f in (k['faktorer'] or {}).items()) + ")</span></h3>")
        lig = all(v["ok"] for v in k["ligevaegt"].values())
        ud.append("<p class=t>Ligevægt: " + ("OK" if lig else "<b>FEJL</b>") + " · "
                  + " · ".join(f"Σ{a}: R {_fmt(v['reaktioner'], 2)} / last {_fmt(v['laster'], 2)} kN"
                               for a, v in k["ligevaegt"].items() if abs(v["laster"]) > 1e-9 or abs(v["reaktioner"]) > 1e-9)
                  + "</p>")
        ud.append("<table><tr><th>Understøtning</th><th>Reaktioner (kN, kNm)</th></tr>")
        for kn2, r in k["reaktioner"].items():
            ud.append(f"<tr><td>{kn2}</td><td>" + ", ".join(f"{a} = {_fmt(v, 2)}" for a, v in r.items()) + "</td></tr>")
        ud.append("</table><table><tr><th>Element</th><th>Profil</th><th>L [m]</th><th>N [kN]</th><th>|V| [kN]</th>"
                  "<th>M [kNm]</th><th>δ [mm]</th>" + ("<th>L/δ</th>" if k["type"] == "anvendelse" else "") + "</tr>")
        for en, e in k["elementer"].items():
            ld = ""
            if k["type"] == "anvendelse":
                ok = e.get("nedboejning_ok")
                ld = (f"<td class={'ok' if ok else ('fejl' if ok is False else '')}>"
                      f"{'L/' + str(e['L_over_delta']) if e.get('L_over_delta') else '–'}"
                      f"{' (krav ' + e['graense'] + ')' if e.get('graense') else ''}</td>")
            ud.append(f"<tr><td>{en}</td><td>{html.escape(str(e['profil']))}</td><td>{_fmt(e['L'], 2)}</td>"
                      f"<td>{_fmt(e['N_min'])} … {_fmt(e['N_max'])}</td><td>{_fmt(e['V_abs_max'])}</td>"
                      f"<td>{_fmt(e['M_min'])} … {_fmt(e['M_max'])}</td><td>{_fmt(e['delta_mm'])}</td>{ld}</tr>")
        ud.append("</table>")
    return "\n".join(ud)


def vis(s: dict, kurver: dict, res: dict, ud: pathlib.Path) -> pathlib.Path:
    plan = s["_plan"]
    span = _span(s)
    fig = go.Figure()
    faste = 0
    for en, e in s["elementer"].items():
        pts = [_punkt(s, e, i / 20) for i in range(21)]
        txt = (f"<b>{en}</b> · {e['profil']} · {e['materiale']}<br>{e['fra']} → {e['til']} · L = {_fmt(e['_L'], 2)} m"
               + (f"<br>led: {', '.join(e['led']) if isinstance(e.get('led'), list) else e['led']}" if e.get("led") else ""))
        fig.add_trace(_linje([_xyz(p, plan) for p in pts], plan, line=dict(color="#222", width=4), name=en,
                             text=[txt] * len(pts), hoverinfo="text", showlegend=False))
        faste += 1
    rtxt = []
    for k in s["understoetninger"]:
        linjer = [f"<b>{k}</b> ({s['understoetninger'][k]})"]
        for kn, kk in res["kombinationer"].items():
            linjer.append(f"{kn}: " + ", ".join(f"{a} = {_fmt(v, 1)}" for a, v in kk["reaktioner"][k].items()))
        rtxt.append("<br>".join(linjer))
    sp = [s["knuder"][k] for k in s["understoetninger"]]
    marker = dict(symbol="triangle-up", size=14, color="#1a5276")
    if plan:
        fig.add_trace(go.Scatter(x=[p[0] for p in sp], y=[p[2] for p in sp], mode="markers", marker=marker,
                                 text=rtxt, hoverinfo="text", showlegend=False))
    else:
        fig.add_trace(go.Scatter3d(x=[p[0] for p in sp], y=[p[1] for p in sp], z=[p[2] for p in sp], mode="markers",
                                   marker=dict(symbol="diamond", size=6, color="#1a5276"), text=rtxt, hoverinfo="text",
                                   showlegend=False))
    faste += 1
    # skala pr. størrelse fælles for alle kombinationer, så de kan sammenlignes
    skala = {}
    for st in STORRELSER:
        vmax = max(max(abs(v) for v in c[st]) for kn in s["kombinationer"] for c in kurver[kn]["elementer"].values())
        if st == "d":
            fl = max(math.hypot(*f) for kn in s["kombinationer"] for f in kurver[kn]["flytning"].values())
            vmax = max(vmax, fl)
            skala[st] = span * 0.08 / (vmax / 1000) if vmax > 1e-9 else 1.0
        else:
            skala[st] = span * 0.12 / vmax if vmax > 1e-9 else 1.0
    grupper = []
    for kn in s["kombinationer"]:
        kv = kurver[kn]
        for st in STORRELSER:
            start = len(fig.data)
            for en, e in s["elementer"].items():
                c = kv["elementer"][en]
                ny = kurver["_lokal_y"][en]
                pts = []
                for i, x in enumerate(c["x"]):
                    t = x / e["_L"]
                    p = _punkt(s, e, t)
                    if st == "d":
                        fa, fb = kv["flytning"][e["fra"]], kv["flytning"][e["til"]]
                        u = [(fa[j] + (fb[j] - fa[j]) * t) / 1000 + c["d"][i] / 1000 * ny[j] for j in range(3)]
                        q = [p[j] + skala[st] * u[j] for j in range(3)]
                    else:
                        sgn = -1 if st == "M" else 1
                        q = [p[j] + sgn * skala[st] * c[st][i] * ny[j] for j in range(3)]
                    pts.append(_xyz(q, plan))
                tekst = [_hover(en, e, c, i) for i in range(len(c["x"]))]
                fill = {} if (st == "d" or not plan) else dict(fill="toself", fillcolor="rgba(0,0,0,0.06)")
                if st != "d" and plan:  # luk kurven mod elementaksen
                    a0, a1 = _xyz(_punkt(s, e, 0), plan), _xyz(_punkt(s, e, 1), plan)
                    pts = [a0] + pts + [a1]
                    tekst = [tekst[0]] + tekst + [tekst[-1]]
                fig.add_trace(_linje(pts, plan, line=dict(color=FARVE[st], width=3), text=tekst, hoverinfo="text",
                                     visible=False, showlegend=False, **fill))
            grupper.append((f"{kn} · {NAVN[st]}" + (f" [{ENHED[st]}]" if st != "d" else " (forstørret)"),
                            start, len(fig.data)))
    n = len(fig.data)
    knapper = []
    for label, a, b in grupper:
        synlig = [i < faste or a <= i < b for i in range(n)]
        knapper.append(dict(label=label, method="update", args=[{"visible": synlig}]))
    knapper.insert(0, dict(label="Kun model", method="update", args=[{"visible": [i < faste for i in range(n)]}]))
    if len(knapper) > 1:  # vis første momentkurve fra start
        for i in range(grupper[0][1], grupper[0][2]):
            fig.data[i].visible = True
    fig.update_layout(updatemenus=[dict(buttons=knapper, active=1 if len(knapper) > 1 else 0, x=0, y=1.12,
                                        xanchor="left", direction="down")],
                      margin=dict(l=10, r=10, t=70, b=10), height=640, plot_bgcolor="white",
                      hoverlabel=dict(bgcolor="white", font_size=13))
    if plan:
        fig.update_xaxes(title="x [m]", scaleanchor="y", scaleratio=1, showgrid=True, gridcolor="#eee", zeroline=False)
        fig.update_yaxes(title="z [m]", showgrid=True, gridcolor="#eee", zeroline=False)
    else:
        fig.update_layout(scene=dict(aspectmode="data", xaxis_title="x [m]", yaxis_title="y [m]", zaxis_title="z [m]"))
    plot = fig.to_html(include_plotlyjs=True, full_html=False, config={"displaylogo": False, "responsive": True})
    side = f"""<!doctype html><html lang="da"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1"><title>{html.escape(s['navn'])} · FEM</title>
<style>body{{font-family:system-ui,-apple-system,sans-serif;margin:16px;color:#222;max-width:1200px}}
h1{{font-size:20px;margin:0 0 4px}} h3{{font-size:15px;margin:22px 0 4px}} .t{{color:#666;font-weight:normal;font-size:13px}}
table{{border-collapse:collapse;margin:6px 0 10px;font-size:13px}} td,th{{border:1px solid #ddd;padding:3px 8px;text-align:left}}
th{{background:#f5f5f5}} .ok{{color:#1e8449}} .fejl{{color:#c0392b;font-weight:bold}}
.note{{background:#fff8e1;border:1px solid #f0d78c;padding:6px 10px;font-size:13px;margin:8px 0}}</style></head><body>
<h1>{html.escape(s['navn'])}</h1>
<p class=t>FEM-model (PyNite {res['pynite']}, {res['analyse']}) · spec {html.escape(pathlib.Path(s['_sti']).name)}
· sha {s['_sha']} · enheder kN, kNm, m, mm</p>
<div class=note><b>OVERSLAG</b> – resultaterne skal eftervises af den ansvarlige statiker. Vælg kombination og
størrelse i menuen, og hold musen over et element for værdierne. {html.escape(res['fortegn'])}</div>
{plot}
{_tabeller(res)}
</body></html>"""
    ud.mkdir(parents=True, exist_ok=True)
    sti = ud / filnavn(f"{s['navn']}.html")
    sti.write_text(side, encoding="utf-8")
    return sti
