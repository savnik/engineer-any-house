"""PNG-tegninger af FEM-modellen: model med understøtninger og laster, deformation og M-, V- og N-kurver."""
import math
import pathlib
import re

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

FARVE = {"M": "#c0392b", "V": "#2471a3", "N": "#7d3c98", "d": "#d35400", "last": "#1e8449"}
ENHED = {"M": "kNm", "V": "kN", "N": "kN", "d": "mm"}
NAVN = {"M": "Moment", "V": "Forskydning", "N": "Normalkraft", "d": "Deformation"}


def filnavn(s: str) -> str:
    return re.sub(r"[^A-Za-z0-9æøåÆØÅ_.-]+", "_", s)


def _fmt(v: float, d: int = 1) -> str:
    v = 0.0 if abs(v) < 0.5 * 10 ** -d else v  # ingen "−0,0"
    return f"{v:.{d}f}".replace(".", ",").replace("-", "−")


def _span(s: dict) -> float:
    xs = [v[0] for v in s["knuder"].values()]
    ys = [v[1] for v in s["knuder"].values()]
    zs = [v[2] for v in s["knuder"].values()]
    return max(max(xs) - min(xs), max(ys) - min(ys), max(zs) - min(zs), 1.0)


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
            dm = max(((en, max(c["d"], key=abs)) for en, c in kv["elementer"].items()), key=lambda t: abs(t[1]))
            ax.text(0.0, -0.02, f"Største nedbøjning i forhold til korden: {_fmt(dm[1])} mm ({dm[0]}) · "
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


def _tegn_3d(s, kurver, visning, kombi, ud):
    fig = plt.figure(figsize=(11, 7.5), dpi=130)
    ax = fig.add_subplot(projection="3d")
    span = _span(s)
    titel = f"{s['navn']} · model"
    if visning == "model":
        for en, e in s["elementer"].items():
            a, b = (s["knuder"][e[k]] for k in ("fra", "til"))
            ax.plot(*zip(a, b), color="k", lw=2)
            m = _punkt(s, e, 0.5)
            ax.text(*m, f" {en}", fontsize=7, color="#555")
        for k in s["understoetninger"]:
            ax.scatter(*s["knuder"][k], marker="^", s=60, color="#1a5276")
    else:
        kv = kurver[kombi]
        titel = f"{s['navn']} · {NAVN[visning]} · {kombi}"
        storrelse = "d" if visning == "d" else visning
        vmax = max(max(abs(x) for x in c[storrelse]) for c in kv["elementer"].values()) or 1.0
        cmap = plt.get_cmap("plasma")
        for en, e in s["elementer"].items():
            a, b = (s["knuder"][e[k]] for k in ("fra", "til"))
            c = kv["elementer"][en]
            v = max(c[storrelse], key=abs)
            ax.plot(*zip(a, b), color=cmap(abs(v) / vmax), lw=3)
            m = _punkt(s, e, 0.5)
            ax.text(*m, f" {_fmt(v)}", fontsize=7)
        sm = plt.cm.ScalarMappable(cmap=cmap, norm=plt.Normalize(0, vmax))
        fig.colorbar(sm, ax=ax, shrink=0.6, label=f"|{NAVN[visning]}| [{ENHED[visning]}]")
    ax.set_box_aspect([max(1e-3, (max(v[i] for v in s["knuder"].values()) - min(v[i] for v in s["knuder"].values())) / span)
                       for i in range(3)])
    ax.set_xlabel("x [m]")
    ax.set_ylabel("y [m]")
    ax.set_zlabel("z [m]")
    ax.set_title(titel, fontsize=11, loc="left")
    ud.mkdir(parents=True, exist_ok=True)
    sti = ud / filnavn(f"{s['navn']}-{'model' if visning == 'model' else NAVN[visning].lower()}"
                       + ("" if visning == "model" else f"-{kombi}") + ".png")
    fig.savefig(sti, bbox_inches="tight")
    plt.close(fig)
    return sti
