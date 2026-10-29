"""PNG-tegninger af FEM-modellen: model med understøtninger og laster, deformation, M-, V- og N-kurver og
farvekort på flader (spænding, membrankræfter, pladmomenter, flytning)."""
import math
import pathlib
import re

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

FARVE = {"M": "#c0392b", "V": "#2471a3", "N": "#7d3c98", "d": "#d35400", "last": "#1e8449"}
ENHED = {"M": "kNm", "V": "kN", "N": "kN", "d": "mm", "S": "MPa", "nu": "kN/m", "nv": "kN/m", "m": "kNm/m", "u": "mm"}
NAVN = {"M": "Moment", "V": "Forskydning", "N": "Normalkraft", "d": "Deformation", "S": "Spænding σ_vM",
        "nu": "Membrankraft n_u", "nv": "Membrankraft n_v", "m": "Pladmoment", "u": "Flytning"}
FLADE_ST = ("S", "nu", "nv", "m", "u")
FIL = {"S": "spaending", "nu": "n_u", "nv": "n_v", "m": "pladmoment", "u": "flytning"}  # størrelser på flader (vægge, dæk)


def filnavn(s: str) -> str:
    return re.sub(r"[^A-Za-z0-9æøåÆØÅ_.-]+", "_", s)


def _fmt(v: float, d: int = 1) -> str:
    v = 0.0 if abs(v) < 0.5 * 10 ** -d else v  # ingen "−0,0"
    return f"{v:.{d}f}".replace(".", ",").replace("-", "−")


def _span(s: dict) -> float:
    from .loads import span
    return max(span(s), 1.0)


def _punkt(s, e, t):
    a, b = (s["knuder"][e[k]] for k in ("fra", "til"))
    return [a[i] + (b[i] - a[i]) * t for i in range(3)]


def _stoette_2d(ax, x, z, typ, sz):
    if typ == "indspaendt" or (isinstance(typ, list) and {"x", "z", "ry"} <= set(typ)):
        ax.plot([x - sz, x + sz], [z, z], color="k", lw=3)
        for i in range(5):
            xx = x - sz + i * sz / 2
            ax.plot([xx, xx - sz / 3], [z, z - sz / 3], color="k", lw=0.8)
        return
    ax.fill([x, x - sz * 0.6, x + sz * 0.6], [z, z - sz, z - sz], facecolor="white", edgecolor="k", lw=1.2, zorder=4)
    if typ in ("rulle", "rulle-x") or (isinstance(typ, list) and "x" not in typ):
        ax.plot([x - sz * 0.8, x + sz * 0.8], [z - sz * 1.25] * 2, color="k", lw=1.2)


def _laster_2d(ax, s, sz):
    niveau = {}  # linjelaster på samme element stables
    for ltn, lt in s["lasttilfaelde"].items():
        for l in (lt or {}).get("laster") or []:
            r = l.get("retning", "ned")
            if r not in ("ned", "z", "x") or "moment" in l:
                continue
            dx, dz = {"ned": (0, -1), "z": (0, 1), "x": (1, 0)}[r]
            if "linjelast" in l:
                e = s["elementer"][l["element"]]
                L = e["_L"]
                a = float(l.get("fra") or 0) / L
                b = float(l["til"]) / L if l.get("til") is not None else 1.0
                w = l["linjelast"]
                tekst = f"{ltn}: {_fmt(w[0]) + '–' + _fmt(w[1]) if isinstance(w, (list, tuple)) else _fmt(w)} kN/m"
                lv = niveau.get(l["element"], 0)
                niveau[l["element"]] = lv + 1
                h = sz * (1.6 + 1.4 * lv)
                pts = [_punkt(s, e, a + (b - a) * i / 6) for i in range(7)]
                for p in pts:
                    ax.annotate("", xy=(p[0] - dx * (h - sz * 1.6), p[2] - dz * (h - sz * 1.6)),
                                xytext=(p[0] - dx * h, p[2] - dz * h),
                                arrowprops=dict(arrowstyle="->", color=FARVE["last"], lw=0.9))
                ax.plot([p[0] - dx * h for p in pts], [p[2] - dz * h for p in pts], color=FARVE["last"], lw=0.9)
                m = pts[5]
                ax.text(m[0] - dx * (h + sz * 0.2), m[2] - dz * (h + sz * 0.2), tekst, color=FARVE["last"], fontsize=8,
                        ha="center", va="bottom" if dz < 0 else "top")
            elif "punktlast" in l:
                if "element" in l:
                    e = s["elementer"][l["element"]]
                    p = _punkt(s, e, float(l.get("x", e["_L"] / 2)) / e["_L"])
                else:
                    p = s["knuder"][l["knude"]]
                ax.annotate("", xy=(p[0], p[2]), xytext=(p[0] - dx * sz * 3, p[2] - dz * sz * 3),
                            arrowprops=dict(arrowstyle="-|>", color=FARVE["last"], lw=1.6))
                ax.text(p[0] - dx * sz * 3.2, p[2] - dz * sz * 3.2, f"{ltn}: {_fmt(l['punktlast'])} kN",
                        color=FARVE["last"], fontsize=8, ha="center", va="bottom" if dz < 0 else "top")


def tegn(s: dict, kurver: dict, visning: str, kombi: str, ud: pathlib.Path) -> pathlib.Path:
    if not s["_plan"]:
        return _tegn_3d(s, kurver, visning, kombi, ud)
    span = _span(s)
    sz = span * 0.025
    fig, ax = plt.subplots(figsize=(11, 6.5), dpi=130)
    ax.set_aspect("equal")
    ax.axis("off")
    stil = dict(color="#999", lw=1.2, ls="--") if visning == "d" else dict(color="k", lw=2.2)
    for en, e in s["elementer"].items():
        a, b = (s["knuder"][e[k]] for k in ("fra", "til"))
        ax.plot([a[0], b[0]], [a[2], b[2]], zorder=3, **stil)
        if visning == "model":
            mid = _punkt(s, e, 0.5)
            ax.text(mid[0], mid[2], f" {en}\n {e['profil']}", fontsize=7.5, color="#555", va="center")
            for side, t in (("start", 0.04), ("slut", 0.96)):
                if side in (e.get("led") or []):
                    p = _punkt(s, e, t)
                    ax.plot(p[0], p[2], "o", mfc="white", mec="k", ms=5, zorder=5)
    for k, v in s["knuder"].items():
        ax.plot(v[0], v[2], "o", color="k", ms=3, zorder=4)
        if visning == "model":
            ax.text(v[0] + sz * 0.4, v[2] + sz * 0.4, k, fontsize=7, color="#1a5276")
    for k, typ in s["understoetninger"].items():
        v = s["knuder"][k]
        _stoette_2d(ax, v[0], v[2], typ, sz)
    titel = f"{s['navn']} · model"
    if visning == "model":
        _laster_2d(ax, s, sz)
    else:
        kv = kurver[kombi]
        titel = f"{s['navn']} · {NAVN[visning]} · {kombi}"
        if visning == "d":
            dmax = max(max(abs(c) for c in f) for f in kv["flytning"].values())
            dmax = max(dmax, max(max(abs(x) for x in c["d"]) for c in kv["elementer"].values()))
            fak = (span * 0.08) / (dmax / 1000) if dmax > 1e-9 else 1.0
            for en, e in s["elementer"].items():
                c = kv["elementer"][en]
                fa, fb = kv["flytning"][e["fra"]], kv["flytning"][e["til"]]
                ny = kurver["_lokal_y"][en]
                xs, zs = [], []
                for i, x in enumerate(c["x"]):
                    t = x / e["_L"]
                    p = _punkt(s, e, t)
                    u = [(fa[j] + (fb[j] - fa[j]) * t) / 1000 for j in range(3)]
                    dl = c["d"][i] / 1000
                    xs.append(p[0] + fak * (u[0] + dl * ny[0]))
                    zs.append(p[2] + fak * (u[2] + dl * ny[2]))
                ax.plot(xs, zs, color=FARVE["d"], lw=2, zorder=5)
            ft = max(kv["flytning"].items(), key=lambda kv_: math.hypot(*kv_[1]))
            titel += f" (forstørret ×{_fmt(fak, 0)})"
            dm = max(kv["delta"].items(), key=lambda t: abs(t[1]))
            ax.text(0.0, -0.02, f"Største nedbøjning i forhold til spændets korde: {_fmt(dm[1])} mm ({dm[0]}) · "
                    f"største knudeflytning: {_fmt(math.hypot(*ft[1]))} mm ({ft[0]})", transform=ax.transAxes, fontsize=8.5,
                    va="top")
        else:
            vmax = max(max(abs(x) for x in c[visning]) for c in kv["elementer"].values()) or 1.0
            fak = span * 0.12 / vmax
            for en, e in s["elementer"].items():
                c = kv["elementer"][en]
                ny = kurver["_lokal_y"][en]
                sgn = -1 if visning == "M" else 1  # momentkurven tegnes på trækssiden
                pts = [_punkt(s, e, x / e["_L"]) for x in c["x"]]
                off = [(p[0] + sgn * fak * v * ny[0], p[2] + sgn * fak * v * ny[2]) for p, v in zip(pts, c[visning])]
                poly_x = [pts[0][0]] + [o[0] for o in off] + [pts[-1][0]]
                poly_z = [pts[0][2]] + [o[1] for o in off] + [pts[-1][2]]
                ax.fill(poly_x, poly_z, color=FARVE[visning], alpha=0.18, lw=0, zorder=2)
                ax.plot(poly_x, poly_z, color=FARVE[visning], lw=1.1, zorder=2)
                for i in {max(range(len(c[visning])), key=lambda j: c[visning][j]),
                          min(range(len(c[visning])), key=lambda j: c[visning][j])}:
                    v = c[visning][i]
                    if abs(v) >= 0.02 * vmax:
                        ax.plot(*off[i], "o", color=FARVE[visning], ms=3)
                        ax.text(off[i][0], off[i][1], f" {_fmt(v)}", fontsize=8, color=FARVE[visning],
                                fontweight="bold", va="center")
            titel += f" [{ENHED[visning]}]"
    ax.set_title(titel, fontsize=11, loc="left")
    ax.text(1.0, -0.02, f"OVERSLAG · fem.py · spec {s['_sha']}", transform=ax.transAxes, fontsize=7,
            color="#888", ha="right", va="top")
    ax.margins(0.12)
    ud.mkdir(parents=True, exist_ok=True)
    sti = ud / filnavn(f"{s['navn']}-{'model' if visning == 'model' else NAVN[visning].lower()}"
                       + ("" if visning == "model" else f"-{kombi}") + ".png")
    fig.savefig(sti, bbox_inches="tight")
    plt.close(fig)
    return sti


def _fladefelt(s, kv, st):
    """Værdi pr. quad for en fladestørrelse."""
    q = kv["flader"]["quads"]
    if st == "S":
        return [q[qn]["svm"] for qn, _, _, _ in s["_quads"]]
    if st == "m":
        return [max(abs(q[qn]["mu"]), abs(q[qn]["mv"])) for qn, _, _, _ in s["_quads"]]
    if st == "u":
        fl = kv["flader"]["flytning"]
        return [sum(math.hypot(*fl[k]) for k in kn) / 4 for _, _, kn, _ in s["_quads"]]
    return [q[qn][st] for qn, _, _, _ in s["_quads"]]


def farveskala(s, kv, st):
    """(værdier, vmin, vmax, cmap, note) – fortegnsløse størrelser klippes ved 99,5 %-fraktilen, så enkelte
    spændingskoncentrationer (fx i åbningshjørner) ikke gør resten ensfarvet."""
    v = _fladefelt(s, kv, st)
    if st in ("nu", "nv"):
        srt = sorted(abs(x) for x in v)
        a = srt[min(len(srt) - 1, int(0.995 * len(srt)))] or (srt[-1] or 1.0)
        note = "rød = tryk, blå = træk" + (f" · farveskala klippet ved ±{_fmt(a, 0)} (99,5 %-fraktilen); "
                                           f"min {_fmt(min(v), 0)}, maks {_fmt(max(v), 0)}" if srt[-1] > a * 1.05 else "")
        return v, -a, a, "RdBu", note
    srt = sorted(v)
    top = srt[min(len(srt) - 1, int(0.995 * len(srt)))] or (srt[-1] or 1.0)
    note = f"farveskala klippet ved 99,5 %-fraktilen ({_fmt(top, 2)}); maks {_fmt(srt[-1], 2)}" if srt[-1] > top * 1.05 else ""
    return v, 0.0, top, "turbo", note


def _tegn_3d(s, kurver, visning, kombi, ud):
    from matplotlib.lines import Line2D
    from mpl_toolkits.mplot3d.art3d import Poly3DCollection

    from . import shells as fl
    from . import loads as la
    fig = plt.figure(figsize=(12, 8), dpi=130)
    ax = fig.add_subplot(projection="3d")
    span = la.span(s)
    pts = fl.alle_knuder(s)
    flade_st = visning in FLADE_ST
    titel = f"{s['navn']} · model"
    kv = kurver[kombi] if kombi else None
    fak = 1.0
    if visning == "u":
        fmax = max(math.hypot(*f) for f in kv["flader"]["flytning"].values()) or 1.0
        fak = 0.08 * span / (fmax / 1000)

    def P(k):
        p = pts[k]
        if visning == "u":
            f = kv["flader"]["flytning"][k]
            return [p[i] + fak * f[i] / 1000 for i in range(3)]
        return p

    if s["_quads"]:
        polys = [[P(k) for k in kn] for _, _, kn, _ in s["_quads"]]
        if flade_st:
            v, vmin, vmax, cm, note = farveskala(s, kv, visning)
            cmap = plt.get_cmap(cm)
            norm = plt.Normalize(vmin, vmax)
            ax.add_collection3d(Poly3DCollection(polys, facecolors=[cmap(norm(min(max(x, vmin), vmax))) for x in v],
                                                 edgecolors="k", linewidths=0.15))
            sm = plt.cm.ScalarMappable(cmap=cmap, norm=norm)
            fig.colorbar(sm, ax=ax, shrink=0.55, pad=0.1, label=f"{NAVN[visning]} [{ENHED[visning]}]")
            i = max(range(len(v)), key=lambda j: abs(v[j]))
            c = fl.midtpunkt(s, s["_quads"][i][2])
            ax.scatter(*c, marker="*", s=160, color="k", depthshade=False, zorder=10)
            ax.text(*c, f"  maks {_fmt(v[i], 2)} ({s['_quads'][i][1]})", fontsize=8, zorder=10)
            titel = f"{s['navn']} · {NAVN[visning]} · {kombi}" + (f" (forstørret ×{_fmt(fak, 0)})" if visning == "u" else "")
            if note:
                titel += "\n" + note
        else:
            ax.add_collection3d(Poly3DCollection(polys, facecolors=(0.8, 0.8, 0.8, 0.35), edgecolors=(0.5, 0.5, 0.5, 0.4),
                                                 linewidths=0.15))
    for en, e in s["elementer"].items():
        a, b = (s["knuder"][e[k]] for k in ("fra", "til"))
        if visning in ("M", "V", "N", "d"):
            c = kv["elementer"][en]
            st = "d" if visning == "d" else visning
            vmax_e = max(max(abs(x) for x in cc[st]) for cc in kv["elementer"].values()) or 1.0
            v = max(c[st], key=abs)
            ax.plot(*zip(a, b), color=plt.get_cmap("plasma")(abs(v) / vmax_e), lw=3)
            ax.text(*_punkt(s, e, 0.5), f" {_fmt(v)}", fontsize=7)
        else:
            ax.plot(*zip(a, b), color="k", lw=2)
            if visning == "model":
                ax.text(*_punkt(s, e, 0.5), f" {en}", fontsize=7, color="#555")
    if visning in ("M", "V", "N", "d"):
        vmax_e = max(max(abs(x) for x in cc["d" if visning == "d" else visning]) for cc in kv["elementer"].values()) or 1.0
        sm = plt.cm.ScalarMappable(cmap=plt.get_cmap("plasma"), norm=plt.Normalize(0, vmax_e))
        fig.colorbar(sm, ax=ax, shrink=0.55, pad=0.1, label=f"|{NAVN[visning]}| [{ENHED[visning]}]")
        titel = f"{s['navn']} · {NAVN[visning]} · {kombi}"
    for k in s["understoetninger"]:
        ax.scatter(*s["knuder"][k], marker="^", s=60, color="#1a5276")
    for ls in s["understoetninger_linje"]:
        ax.plot(*zip(s["knuder"][ls["fra"]], s["knuder"][ls["til"]]), color="#1a5276", lw=4, alpha=0.8)
    if visning == "model":
        haand = []
        for lt, g in la.pile(s).items():
            f = la.farve(s, lt)
            for p in g["pile"]:
                d = [p["spids"][i] - p["start"][i] for i in range(3)]
                ax.quiver(*p["start"], *d, color=f, arrow_length_ratio=0.3, linewidth=1.0)
            for li in g.get("linjer", []):
                ax.plot(*zip(*li), color=f, lw=1)
            for pos, tekst in g["tekster"]:
                if pos is not None:
                    ax.text(*pos, tekst, fontsize=7.5, color=f)
            haand.append(Line2D([0], [0], color=f, lw=2, label=" · ".join(t for _, t in g["tekster"]) or lt))
        if haand:
            ax.legend(handles=haand, loc="upper left", fontsize=8, frameon=False)
    lo = [min(p[i] for p in pts.values()) for i in range(3)]
    hi = [max(p[i] for p in pts.values()) for i in range(3)]
    for i, f in enumerate((ax.set_xlim, ax.set_ylim, ax.set_zlim)):
        f(lo[i] - 0.05 * span, hi[i] + 0.05 * span)
    ax.set_box_aspect([max(0.05, (hi[i] - lo[i] + 0.1 * span) / span) for i in range(3)])
    for i, akse in enumerate((ax.xaxis, ax.yaxis, ax.zaxis)):
        if hi[i] - lo[i] < 0.05 * span:  # næsten flad model: ingen sammenklumpede tal på den korte akse
            akse.set_ticks([round((lo[i] + hi[i]) / 2, 2)])
    ax.view_init(elev=24, azim=-60)
    ax.set_xlabel("x [m]")
    ax.set_ylabel("y [m]")
    ax.set_zlabel("z [m]")
    ax.set_title(titel, fontsize=11 if "\n" not in titel else 10, loc="left")
    ax.text2D(1.0, 0.0, f"OVERSLAG · fem.py · spec {s['_sha']}", transform=ax.transAxes, fontsize=7, color="#888", ha="right")
    ud.mkdir(parents=True, exist_ok=True)
    sti = ud / filnavn(f"{s['navn']}-{'model' if visning == 'model' else FIL.get(visning, NAVN[visning].lower())}"
                       + ("" if visning == "model" else f"-{kombi}") + ".png")
    fig.savefig(sti, bbox_inches="tight")
    plt.close(fig)
    return sti
