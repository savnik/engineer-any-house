"""Afkodning af en tegning (afkodning.yaml): indlæsning, kalibrering og deterministisk kontrol.

Afkodningen er det strukturerede udtræk af ALT på en tegning: visninger (plan/snit/facade), kalibrering
(pixel → model-mm), påskrevne mål, rum, åbninger, vægtykkelser, koter, tekster og usikre steder.
`afkod tjek` kontrollerer afkodningen mod tegningen selv: passer hvert aflæst mål med afstanden mellem dets
endepunkter på tegningen (via kalibreringen)? Summerer målkæderne? Passer skalaen med den påskrevne målestok?
Se references/afkodning.md.
"""
import pathlib

import numpy as np
import yaml

VISNINGSTYPER = {"plan", "snit", "facade", "detalje", "situationsplan", "tekst"}
AABNINGSTYPER = {"vindue", "doer", "port", "hul"}


class AfkodFejl(Exception):
    def __init__(self, fejl):
        self.fejl = fejl
        super().__init__("\n".join(fejl))


def _pkt(p, sti, fejl):
    if not (isinstance(p, (list, tuple)) and len(p) == 2 and all(isinstance(v, (int, float)) for v in p)):
        fejl.append(f"{sti}: forventede [x, y], fik {p!r}")
        return None
    return (float(p[0]), float(p[1]))


def indlaes(sti) -> dict:
    sti = pathlib.Path(sti).resolve()
    try:
        d = yaml.safe_load(sti.read_text(encoding="utf-8")) or {}
    except yaml.YAMLError as e:
        raise AfkodFejl([f"YAML-fejl: {e}"]) from None
    fejl = []
    k = d.get("kilde") or {}
    for felt in ("id", "fil", "dokument"):
        if not k.get(felt):
            fejl.append(f"kilde.{felt} mangler")
    if k.get("fil"):
        billede = (sti.parent / k["fil"]).resolve()
        if not billede.exists():
            fejl.append(f"kilde.fil findes ikke: {billede}")
        k["_billede"] = str(billede)
    vis = d.get("visninger") or []
    if not vis:
        fejl.append("visninger mangler (mindst én)")
    ids = set()
    for i, v in enumerate(vis):
        vid = str(v.get("id", f"V{i + 1}"))
        v["id"] = vid
        s = f"visninger.{vid}"
        if vid in ids:
            fejl.append(f"{s}: id findes allerede")
        ids.add(vid)
        if v.get("type") not in VISNINGSTYPER:
            fejl.append(f"{s}.type skal være en af {sorted(VISNINGSTYPER)}")
        if v.get("type") == "plan" and v.get("etage") is None:
            fejl.append(f"{s}: plan kræver etage (modellens etage-id)")
        if v.get("type") == "snit" and not v.get("linje"):
            fejl.append(f"{s}: snit kræver linje [x1, y1, x2, y2] i modelkoordinater (snitlinjen fra planen)")
        if v.get("type") == "facade" and not v.get("side"):
            fejl.append(f"{s}: facade kræver side (syd|nord|oest|vest eller x+|x-|y+|y-)")
        bb = v.get("bbox")
        if not (isinstance(bb, list) and len(bb) == 4):
            fejl.append(f"{s}.bbox skal være [x0, y0, x1, y1] i pixel")
        if v.get("type") in ("plan", "snit", "facade"):
            kal = v.get("kal") or []
            if len(kal) < 3:
                fejl.append(f"{s}.kal: mindst 3 punktpar (px → model) – helst i hver sit hjørne af visningen")
            for j, kp in enumerate(kal):
                _pkt(kp.get("px"), f"{s}.kal[{j}].px", fejl)
                _pkt(kp.get("model"), f"{s}.kal[{j}].model", fejl)
        for j, m in enumerate(v.get("maal") or []):
            ms = f"{s}.maal[{m.get('id', j)}]"
            if not isinstance(m.get("vaerdi"), (int, float)):
                fejl.append(f"{ms}.vaerdi skal være et tal i mm (tekst: som skrevet på tegningen)")
            _pkt(m.get("fra"), f"{ms}.fra", fejl)
            _pkt(m.get("til"), f"{ms}.til", fejl)
            if m.get("retning", "fri") not in ("x", "y", "z", "u", "fri"):
                fejl.append(f"{ms}.retning skal være x|y (plan), u|z (snit/facade) eller fri")
        for j, r in enumerate(v.get("rum") or []):
            _pkt(r.get("punkt"), f"{s}.rum[{j}].punkt", fejl)
        for j, a in enumerate(v.get("aabninger") or []):
            _pkt(a.get("punkt"), f"{s}.aabninger[{j}].punkt", fejl)
            if a.get("type") not in AABNINGSTYPER:
                fejl.append(f"{s}.aabninger[{j}].type skal være en af {sorted(AABNINGSTYPER)}")
        for j, w in enumerate(v.get("vaegge") or []):
            _pkt(w.get("punkt"), f"{s}.vaegge[{j}].punkt", fejl)
    if fejl:
        raise AfkodFejl(fejl)
    d["_sti"] = str(sti)
    return d


def kalibrering(v):
    """Affin px → model (2×3) med mindste kvadrater; returnerer (M, rest_mm pr. punkt, skala_x, skala_y)."""
    par = [(np.array(kp["px"], float), np.array(kp["model"], float)) for kp in v["kal"]]
    A = np.array([[p[0], p[1], 1.0] for p, _ in par])
    X = np.array([m for _, m in par])
    sol, *_ = np.linalg.lstsq(A, X, rcond=None)
    M = sol.T
    rest = [float(np.linalg.norm(M @ np.array([p[0], p[1], 1.0]) - m)) for p, m in par]
    sx = float(np.linalg.norm(M[:, 0]))
    sy = float(np.linalg.norm(M[:, 1]))
    return M, rest, sx, sy


def til_model(M, p):
    return M @ np.array([p[0], p[1], 1.0])


def til_px(M, q):
    """Model → px (inverse af den affine kalibrering)."""
    L = M[:, :2]
    return np.linalg.solve(L, np.asarray(q, float) - M[:, 2])


def tol_mm(vaerdi):
    return max(50.0, 0.015 * abs(vaerdi))


def maal_i_tegning(M, m):
    a, b = til_model(M, m["fra"]), til_model(M, m["til"])
    r = m.get("retning", "fri")
    if r in ("x", "u"):
        return abs(b[0] - a[0])
    if r in ("y", "z"):
        return abs(b[1] - a[1])
    return float(np.linalg.norm(b - a))


def skabelon() -> int:
    print((pathlib.Path(__file__).resolve().parent.parent.parent / "assets" / "afkodning-skabelon.yaml").read_text(encoding="utf-8"))
    return 0


def tjek(sti) -> int:
    try:
        d = indlaes(sti)
    except AfkodFejl as e:
        print(f"AFKODNING-FEJL ({len(e.fejl)}):")
        for x in e.fejl[:40]:
            print("  - " + x)
        return 1
    k = d["kilde"]
    n_fejl = n_adv = 0
    print(f"AFKODNING {k['id']} · {k.get('dokument')} · {len(d['visninger'])} visning(er)")
    dpi = k.get("dpi")
    maalestok = str(k.get("maalestok") or "")
    for v in d["visninger"]:
        tael = {x: len(v.get(x) or []) for x in ("maal", "rum", "aabninger", "vaegge", "koter", "tekster", "usikre")}
        print(f"  {v['id']} {v['type']} {v.get('etage') or v.get('side') or v.get('linje') or ''}: "
              + ", ".join(f"{n} {x}" for x, n in tael.items() if n))
        if v["type"] not in ("plan", "snit", "facade"):
            continue
        M, rest, sx, sy = kalibrering(v)
        rmax = max(rest)
        niveau = "FEJL" if rmax > 100 else ("ADVARSEL" if rmax > 40 else "ok")
        print(f"    kalibrering: {len(rest)} punkter, største rest {rmax:.0f} mm, skala X {sx:.2f} · Y {sy:.2f} mm/px"
              f" ({100 * (sy - sx) / sx:+.1f} %) [{niveau}]")
        n_fejl += niveau == "FEJL"
        n_adv += niveau == "ADVARSEL"
        lm = v.get("maalestok") or maalestok
        if dpi and lm.startswith("1:"):
            forventet = 25.4 / float(dpi) * float(lm[2:])
            afv = ((sx + sy) / 2 - forventet) / forventet
            tekst = f"    målestok {lm} ved {dpi} dpi giver {forventet:.2f} mm/px; kalibreret {afv:+.1%}"
            if abs(afv) > 0.03:
                tekst += " – kopien er formindsket/forstørret, eller målestokken er en anden (brug kalibreringen, ikke målestokken)"
                n_adv += 1
            print(tekst)
        afvig = []
        for m in v.get("maal") or []:
            tegn = maal_i_tegning(M, m)
            dev = tegn - m["vaerdi"]
            if abs(dev) > tol_mm(m["vaerdi"]):
                afvig.append((m, tegn, dev))
        n_m = len(v.get("maal") or [])
        print(f"    mål: {n_m - len(afvig)} af {n_m} passer med tegningens geometri (tolerance max(50 mm; 1,5 %))")
        for m, tegn, dev in afvig[:20]:
            print(f"    FEJL mål {m.get('id', '?')} '{m.get('tekst', m['vaerdi'])}' = {m['vaerdi']:.0f} mm, men tegningen "
                  f"viser {tegn:.0f} mm ({dev:+.0f}) – fejllæst tal, forkerte endepunkter eller målet er ikke målfast tegnet")
        n_fejl += len(afvig)
        kaeder = {}
        for m in v.get("maal") or []:
            if m.get("kaede"):
                kaeder.setdefault(m["kaede"], []).append(m)
        for navn, ms in kaeder.items():
            tot = [m for m in ms if m.get("total")]
            dele = [m for m in ms if not m.get("total")]
            if tot and dele:
                s_ = sum(m["vaerdi"] for m in dele)
                dev = s_ - tot[0]["vaerdi"]
                ok = abs(dev) <= 10
                print(f"    kæde {navn}: delmål {s_:.0f} mod total {tot[0]['vaerdi']:.0f} ({dev:+.0f}) "
                      f"[{'ok' if ok else 'FEJL – et delmål er fejllæst eller mangler'}]")
                n_fejl += not ok
        if v.get("usikre"):
            print(f"    usikre steder: {len(v['usikre'])} (skal nævnes i modelnotatet og på opmålingslisten)")
    print(f"RESULTAT: {n_fejl} fejl, {n_adv} advarsler")
    return 1 if n_fejl else 0


__all__ = ["indlaes", "kalibrering", "til_model", "til_px", "tjek", "tol_mm", "maal_i_tegning", "AfkodFejl"]
