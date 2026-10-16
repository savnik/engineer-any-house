"""Kommandolinjen for fem.py."""
import pathlib
import re
import shlex
import sys
import tempfile

from . import model
from .model import SpecFejl

EKSEMPEL = pathlib.Path(__file__).resolve().parent.parent.parent / "assets" / "fem-eksempel.yaml"


def _fmt(v, d=1):
    v = 0.0 if abs(v) < 0.5 * 10 ** -d else v  # ingen "-0,0"
    return f"{v:.{d}f}".replace(".", ",")


def _opt(args, navn, std=None):
    if navn in args:
        i = args.index(navn)
        v = args[i + 1] if i + 1 < len(args) else None
        del args[i:i + 2]
        return v
    return std


def _flag(args, navn):
    if navn in args:
        args.remove(navn)
        return True
    return False


def _saet(args) -> list:
    ud = []
    while "--saet" in args:
        ud.append(_opt(args, "--saet"))
    return ud


def _kommando(argv):
    return "python3 fem.py " + " ".join(shlex.quote(a) for a in argv)


def _resume(res: dict) -> str:
    """Kort resumé til skærmen (det fulde resultat står i JSON-filen)."""
    ud = [f"FEM {res['navn']} · spec-sha {res['spec_sha256_12']} · PyNite {res['pynite']} · {res['analyse']}"
          + (" · plan" if res["plan"] else " · 3D")]
    if res["aendringer"]:
        ud.append("ÆNDREDE INPUT (--saet): " + " · ".join(res["aendringer"]))
    for kn, k in res["kombinationer"].items():
        lig = all(v["ok"] for v in k["ligevaegt"].values())
        ud.append(f"\n{kn} ({k['type']}) · ligevægt {'OK' if lig else 'FEJL'}")
        ud.append("  reaktioner: " + " · ".join(
            f"{n}: " + ", ".join(f"{a} {_fmt(v)}" for a, v in r.items()) for n, r in k["reaktioner"].items()))
        for en, e in k["elementer"].items():
            linje = (f"  {en} {e['profil']} L={_fmt(e['L'], 2)}: M {_fmt(e['M_min'])}…{_fmt(e['M_max'])} kNm, "
                     f"|V| {_fmt(e['V_abs_max'])} kN, N {_fmt(e['N_min'])}…{_fmt(e['N_max'])} kN, δ {_fmt(e['delta_mm'])} mm")
            if k["type"] == "anvendelse" and e.get("L_over_delta"):
                linje += f" (L/{e['L_over_delta']}" + (f", krav {e['graense']}: {'OK' if e['nedboejning_ok'] else 'OVERSKREDET'}"
                                                       if e.get("graense") else "") + ")"
            ud.append(linje)
    return "\n".join(ud)


def regn(args, argv) -> int:
    ingen = _flag(args, "--ingen-filer")
    uddir = _opt(args, "--ud")
    aendr = _saet(args)
    spec = pathlib.Path(args[0]).expanduser().resolve()
    s = model.laes_spec(spec, aendr)
    m = model.analyser(s)
    res = model.resultater(s, m, _kommando(argv))
    print(_resume(res))
    if not ingen:
        ud = pathlib.Path(uddir).expanduser() if uddir else spec.parent / "fem"
        ud.mkdir(parents=True, exist_ok=True)
        sti = ud / f"{re.sub(r'[^A-Za-z0-9æøåÆØÅ_.-]+', '_', s['navn'])}.fem.json"
        model.gem_json(res, sti)
        print(f"\n→ {sti}")
    if not all(v["ok"] for k in res["kombinationer"].values() for v in k["ligevaegt"].values()):
        print("ADVARSEL: ligevægten passer ikke – tjek laster og understøtninger.", file=sys.stderr)
        return 1
    return 0


def tegn(args, argv) -> int:
    from . import tegn as t
    uddir = _opt(args, "--ud")
    kombi = _opt(args, "--kombi")
    aendr = _saet(args)
    spec = pathlib.Path(args[0]).expanduser().resolve()
    visning = args[1] if len(args) > 1 else "alle"
    s = model.laes_spec(spec, aendr)
    m = model.analyser(s)
    kurver = model.kurver_alle(s, m)
    ud = pathlib.Path(uddir).expanduser() if uddir else spec.parent / "fem"
    brud = [k for k, v in s["kombinationer"].items() if v["type"] == "brud"]
    anv = [k for k, v in s["kombinationer"].items() if v["type"] == "anvendelse"]
    if kombi and kombi not in s["kombinationer"]:
        raise SpecFejl(f"ukendt kombination '{kombi}' (kendte: {', '.join(s['kombinationer'])})")
    opgaver = []
    vis = ["model", "d", "M", "V", "N"] if visning == "alle" else [
        {"model": "model", "deformation": "d", "M": "M", "V": "V", "N": "N"}.get(visning)]
    if None in vis:
        raise SpecFejl(f"ukendt visning '{visning}' – brug model, deformation, M, V, N eller alle")
    for v in vis:
        if v == "model":
            opgaver.append((v, None))
        elif kombi:
            opgaver.append((v, kombi))
        elif v == "d":
            opgaver += [(v, k) for k in (anv or brud)[:1]]
        else:
            opgaver += [(v, k) for k in brud[:2] or anv[:1]]
    for v, k in opgaver:
        print(t.tegn(s, kurver, v, k, ud))
    return 0


def vis(args, argv) -> int:
    from . import vis as v
    uddir = _opt(args, "--ud")
    aendr = _saet(args)
    spec = pathlib.Path(args[0]).expanduser().resolve()
    s = model.laes_spec(spec, aendr)
    m = model.analyser(s)
    res = model.resultater(s, m, _kommando(argv))
    sti = v.vis(s, model.kurver_alle(s, m), res, pathlib.Path(uddir).expanduser() if uddir else spec.parent / "fem")
    print(sti)
    print("Åbn filen i en browser (dobbeltklik, eller: open " + shlex.quote(str(sti)) + ").")
    return 0


# ---------- selvtest ----------
TEST = {
    "simpel": """navn: t-simpel
knuder: {A: [0, 0], B: [5, 0]}
elementer: {B1: {fra: A, til: B, profil: IPE200, materiale: S235}}
understoetninger: {A: charnier, B: rulle}
lasttilfaelde: {Q: {laster: [{element: B1, linjelast: 10, retning: ned}]}}
kombinationer: {K: {type: anvendelse, faktorer: {Q: 1.0}}}
""",
    "udkraget": """navn: t-udkraget
knuder: {A: [0, 0], B: [2, 0]}
elementer: {B1: {fra: A, til: B, profil: rekt 100x200, materiale: C24, udkragning: true}}
understoetninger: {A: indspaendt}
lasttilfaelde: {Q: {laster: [{knude: B, punktlast: 10, retning: ned}]}}
kombinationer: {K: {type: anvendelse, faktorer: {Q: 1.0}}}
""",
    "ramme": """navn: t-ramme
knuder: {A: [0, 0], B: [0, 2.5], C: [4.2, 2.5], D: [4.2, 0]}
elementer:
  S1: {fra: A, til: B, profil: HEB160, materiale: S235}
  B1: {fra: B, til: C, profil: HEB160, materiale: S235}
  S2: {fra: D, til: C, profil: HEB160, materiale: S235}
understoetninger: {A: charnier, D: charnier}
lasttilfaelde: {G: {egenvaegt: true, laster: [{element: B1, linjelast: 12, retning: ned}]}}
kombinationer: {K: {type: brud, faktorer: {G: 1.2}}}
""",
}


def test(args, argv) -> int:
    fejl = []

    def tjek(navn, faktisk, forventet, tol=0.01):
        ok = abs(faktisk - forventet) <= tol * max(abs(forventet), 1e-9)
        print(("OK   " if ok else "FEJL ") + f"{navn}: {faktisk:.4g} (forventet {forventet:.4g})")
        if not ok:
            fejl.append(navn)

    with tempfile.TemporaryDirectory() as tmp:
        res = {}
        for n, txt in TEST.items():
            p = pathlib.Path(tmp) / f"{n}.yaml"
            p.write_text(txt, encoding="utf-8")
            s = model.laes_spec(p)
            res[n] = (s, model.resultater(s, model.analyser(s), "test"))
        s, r = res["simpel"]
        e, k = s["elementer"]["B1"], r["kombinationer"]["K"]
        EI = 210e6 * e["_t"]["I_staerk"] * 1e-12
        tjek("simpel bjælke M = qL²/8", k["elementer"]["B1"]["M_max"], 10 * 5 ** 2 / 8)
        tjek("simpel bjælke R = qL/2", k["reaktioner"]["A"]["Rz"], 25)
        tjek("simpel bjælke δ = 5qL⁴/384EI [mm]", abs(k["elementer"]["B1"]["delta_mm"]), 5 * 10 * 5 ** 4 / (384 * EI) * 1000)
        s, r = res["udkraget"]
        e, k = s["elementer"]["B1"], r["kombinationer"]["K"]
        EI = 11000e3 * e["_t"]["I_staerk"] * 1e-12
        tjek("udkraget M = PL", abs(k["elementer"]["B1"]["M_min"]), 20)
        tjek("udkraget δ = PL³/3EI [mm] (bøjning, uden forskydning)", abs(k["elementer"]["B1"]["delta_mm"]),
             10 * 2 ** 3 / (3 * EI) * 1000, tol=0.02)
        s, r = res["ramme"]
        k = r["kombinationer"]["K"]
        q = 1.2 * (12 + 78.5 * s["elementer"]["B1"]["_t"]["A"] * 1e-6)
        b1 = k["elementer"]["B1"]
        tjek("ramme: felt- + hjørnemoment = qL²/8", b1["M_max"] - b1["M_min"], q * 4.2 ** 2 / 8)
        ok = b1["M_max"] > 0 > b1["M_min"]
        print(("OK   " if ok else "FEJL ") + "ramme: feltmoment positivt (træk i underside), hjørnemoment negativt")
        if not ok:
            fejl.append("fortegn")
        s1 = k["elementer"]["S1"]
        tjek("ramme: søjle i tryk, N ved fod = −R", s1["N_min"], -k["reaktioner"]["A"]["Rz"], tol=0.02)
        tjek("ramme: lodret ligevægt", k["ligevaegt"]["z"]["reaktioner"], -k["ligevaegt"]["z"]["laster"])
    print("\nALLE TESTS BESTÅET" if not fejl else f"\n{len(fejl)} FEJL")
    return 1 if fejl else 0


def main(args) -> int:
    argv = list(args)
    cmd, rest = args[0], args[1:]
    try:
        if cmd == "skabelon":
            print(EKSEMPEL.read_text(encoding="utf-8"))
            return 0
        if cmd == "test":
            return test(rest, argv)
        if cmd in ("regn", "tegn", "vis"):
            if not rest:
                print(f"Brug: fem.py {cmd} <fem.yaml> …", file=sys.stderr)
                return 2
            return {"regn": regn, "tegn": tegn, "vis": vis}[cmd](rest, argv)
        print(f"Ukendt kommando '{cmd}'. Se: python3 fem.py --help", file=sys.stderr)
        return 2
    except SpecFejl as e:
        print(f"FEJL i modellen: {e}", file=sys.stderr)
        return 2
    except FileNotFoundError as e:
        print(f"FEJL: {e}", file=sys.stderr)
        return 2
