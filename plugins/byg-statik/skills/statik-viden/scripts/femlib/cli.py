"""The command line for fem.py."""
import pathlib
import re
import shlex
import sys
import tempfile

from . import model
from .model import SpecError

EXAMPLE = pathlib.Path(__file__).resolve().parent.parent.parent / "assets" / "fem-eksempel.yaml"
EXAMPLE_SHELLS = EXAMPLE.with_name("fem-eksempel-flader.yaml")


def _fmt(v, d=1):
    v = 0.0 if abs(v) < 0.5 * 10 ** -d else v  # no "-0,0"
    return f"{v:.{d}f}".replace(".", ",")


def _opt(args, name, default=None):
    if name in args:
        i = args.index(name)
        v = args[i + 1] if i + 1 < len(args) else None
        del args[i:i + 2]
        return v
    return default


def _flag(args, name):
    if name in args:
        args.remove(name)
        return True
    return False


def _set_args(args) -> list:
    out = []
    while "--saet" in args:
        out.append(_opt(args, "--saet"))
    return out


def _out_dir(spec: pathlib.Path, out_arg) -> pathlib.Path:
    """--ud, otherwise <spec folder>/fem/ – but if the spec is already in a folder named fem, that folder."""
    if out_arg:
        return pathlib.Path(out_arg).expanduser()
    return spec.parent if spec.parent.name == "fem" else spec.parent / "fem"


def _command(argv):
    return "python3 fem.py " + " ".join(shlex.quote(a) for a in argv)


def _summary(res: dict) -> str:
    """Short summary for the screen (the full result is in the JSON file)."""
    out = [f"FEM {res['navn']} · spec-sha {res['spec_sha256_12']} · PyNite {res['pynite']} · {res['analyse']}"
          + (" · plan" if res["plan"] else " · 3D")]
    if res["aendringer"]:
        out.append("ÆNDREDE INPUT (--saet): " + " · ".join(res["aendringer"]))
    for kn, k in res["kombinationer"].items():
        balanced = all(v["ok"] for v in k["ligevaegt"].values())
        out.append(f"\n{kn} ({k['type']}) · ligevægt {'OK' if balanced else 'FEJL'}")
        out.append("  reaktioner: " + " · ".join(
            f"{n}: " + ", ".join(f"{a} {_fmt(v)}" for a, v in r.items()) for n, r in k["reaktioner"].items()))
        for en, e in k["elementer"].items():
            line = (f"  {en} {e['profil']} L={_fmt(e['L'], 2)}: M {_fmt(e['M_min'])}…{_fmt(e['M_max'])} kNm, "
                     f"|V| {_fmt(e['V_abs_max'])} kN, N {_fmt(e['N_min'])}…{_fmt(e['N_max'])} kN, δ {_fmt(e['delta_mm'])} mm")
            if k["type"] == "anvendelse" and e.get("L_over_delta"):
                line += f" (L/{e['L_over_delta']}" + (f", krav {e['graense']}: {'OK' if e['nedboejning_ok'] else 'OVERSKREDET'}"
                                                       if e.get("graense") else "") + ")"
            out.append(line)
        for fn, f in k.get("flader", {}).items():
            st = f["steder_med_stoerst_spaending"][0]["xyz"]
            out.append(f"  flade {fn} ({f['tykkelse_mm']} mm {f['materiale']}): σ_vM maks {_fmt(f['sigma_vM_max_MPa'], 2)} MPa "
                      f"ved ({', '.join(_fmt(c, 2) for c in st)}), n_u {_fmt(f['n_u_min_kN_m'])}…{_fmt(f['n_u_max_kN_m'])}, "
                      f"n_v {_fmt(f['n_v_min_kN_m'])}…{_fmt(f['n_v_max_kN_m'])} kN/m, |m| {_fmt(f['m_abs_max_kNm_m'], 2)} kNm/m, "
                      f"flytning {_fmt(f['flytning_max_mm'], 2)} mm")
        for un, u in k.get("udtraek", {}).items():
            if "fejl" in u:
                out.append(f"  udtræk {un}: {u['fejl']}")
                continue
            out.append(f"  udtræk {un} ({u['flade']}, x {u['x']}, y {u['y']}): σ_vM maks {_fmt(u['sigma_vM_max_MPa'], 2)} MPa, "
                      f"n_u {_fmt(u['n_u_min_kN_m'])}…{_fmt(u['n_u_max_kN_m'])}, n_v {_fmt(u['n_v_min_kN_m'])}…"
                      f"{_fmt(u['n_v_max_kN_m'])} kN/m, |m| {_fmt(u['m_abs_max_kNm_m'], 2)} kNm/m")
    return "\n".join(out)


def calc(args, argv) -> int:
    no_files = _flag(args, "--ingen-filer")
    out_arg = _opt(args, "--ud")
    changes = _set_args(args)
    spec = pathlib.Path(args[0]).expanduser().resolve()
    s = model.read_spec(spec, changes)
    m = model.analyze(s)
    res = model.results(s, m, _command(argv))
    print(_summary(res))
    if not no_files:
        out_dir = _out_dir(spec, out_arg)
        out_dir.mkdir(parents=True, exist_ok=True)
        path = _json_for(spec, s, out_arg)
        model.save_json(res, path)
        print(f"\n→ {path}")
    if not all(v["ok"] for k in res["kombinationer"].values() for v in k["ligevaegt"].values()):
        print("ADVARSEL: ligevægten passer ikke – tjek laster og understøtninger.", file=sys.stderr)
        return 1
    return 0


def _json_for(spec: pathlib.Path, s: dict, out_arg) -> pathlib.Path:
    return _out_dir(spec, out_arg) / f"{re.sub(r'[^A-Za-z0-9æøåÆØÅ_.-]+', '_', s['navn'])}.fem.json"


def result(args, argv) -> int:
    """Looks up the saved fem.json without recalculating – and refuses it if fem.yaml has changed since."""
    import json
    out_arg = _opt(args, "--ud")
    combo = _opt(args, "--kombi")
    element = _opt(args, "--element")
    spec = pathlib.Path(args[0]).expanduser().resolve()
    s = model.read_spec(spec)
    path = _json_for(spec, s, out_arg)
    if not path.exists():
        print(f"Intet gemt resultat ({path}). Modellen er ikke regnet – det er statikerens opgave (fem.py regn).",
              file=sys.stderr)
        return 1
    res = json.loads(path.read_text(encoding="utf-8"))
    if res.get("spec_sha256_12") != s["_sha"]:
        print(f"FORÆLDET: {path.name} er regnet på spec-sha {res.get('spec_sha256_12')}, men {spec.name} har nu "
              f"{s['_sha']}. Tallene vises ikke – modellen skal regnes igen af statikeren (fem.py regn).", file=sys.stderr)
        return 1
    if res.get("aendringer"):
        print(f"{path.name} er regnet med ændrede input (--saet: {' · '.join(res['aendringer'])}) og svarer ikke til "
              f"{spec.name}. Tallene vises ikke – modellen skal regnes igen af statikeren (fem.py regn).", file=sys.stderr)
        return 1
    if combo:
        if combo not in res["kombinationer"]:
            raise SpecError(f"ukendt kombination '{combo}' (kendte: {', '.join(res['kombinationer'])})")
        res["kombinationer"] = {combo: res["kombinationer"][combo]}
    if element:
        names = sorted({n for k in res["kombinationer"].values() for f in ("elementer", "flader", "udtraek")
                        for n in k.get(f, {})})
        found = False
        for k in res["kombinationer"].values():
            for field in ("elementer", "flader", "udtraek"):
                if field in k:
                    k[field] = {n: v for n, v in k[field].items() if n.lower() == element.lower()}
                    found |= bool(k[field])
        if not found:
            raise SpecError(f"ukendt element, flade eller udtræk '{element}' (kendte: {', '.join(names)})")
    print(_summary(res))
    print(f"\nKilde: {path} (spec-sha {s['_sha']} = {spec.name}, ingen ny beregning)")
    print("OVERSLAG fra fem.py – skal eftervises af den ansvarlige statiker. Nævn kombinationen, når tallet bruges.")
    return 0


def draw(args, argv) -> int:
    from . import draw as t
    out_arg = _opt(args, "--ud")
    combo = _opt(args, "--kombi")
    changes = _set_args(args)
    spec = pathlib.Path(args[0]).expanduser().resolve()
    view_arg = args[1] if len(args) > 1 else "alle"
    s = model.read_spec(spec, changes)
    m = model.analyze(s)
    curves = model.all_curves(s, m)
    out_dir = _out_dir(spec, out_arg)
    uls = [k for k, v in s["kombinationer"].items() if v["type"] == "brud"]
    sls = [k for k, v in s["kombinationer"].items() if v["type"] == "anvendelse"]
    if combo and combo not in s["kombinationer"]:
        raise SpecError(f"ukendt kombination '{combo}' (kendte: {', '.join(s['kombinationer'])})")
    tasks = []
    names = {"model": "model", "deformation": "d", "M": "M", "V": "V", "N": "N", "spaending": "S", "n_u": "nu",
             "n_v": "nv", "pladmoment": "m", "flytning": "u"}
    if view_arg == "alle":
        views = ["model"] + (["d", "M", "V", "N"] if s["elementer"] else []) + (["S", "nv", "m", "u"] if s["flader"] else [])
    else:
        views = [names.get(view_arg)]
    if None in views:
        raise SpecError(f"ukendt visning '{view_arg}' – brug {', '.join(names)} eller alle")
    if any(v in t.SHELL_Q for v in views) and not s["flader"]:
        raise SpecError(f"visningen '{view_arg}' kræver flader i modellen")
    if any(v in ("d", "M", "V", "N") for v in views) and not s["elementer"]:
        raise SpecError(f"visningen '{view_arg}' kræver elementer i modellen")
    for v in views:
        if v == "model":
            tasks.append((v, None))
        elif combo:
            tasks.append((v, combo))
        elif v in ("d", "u"):
            tasks += [(v, k) for k in (sls or uls)[:1]]
        elif v in t.SHELL_Q:
            tasks += [(v, k) for k in (uls or sls)[:1]]
        else:
            tasks += [(v, k) for k in uls[:2] or sls[:1]]
    for v, k in tasks:
        print(t.draw(s, curves, v, k, out_dir))
    return 0


def view(args, argv) -> int:
    from . import viewer as v
    out_arg = _opt(args, "--ud")
    changes = _set_args(args)
    spec = pathlib.Path(args[0]).expanduser().resolve()
    s = model.read_spec(spec, changes)
    m = model.analyze(s)
    res = model.results(s, m, _command(argv))
    path = v.view(s, model.all_curves(s, m), res, _out_dir(spec, out_arg), cdn=_flag(args, "--cdn"))
    print(path)
    print("Åbn filen i en browser (dobbeltklik, eller: open " + shlex.quote(str(path)) + ").")
    return 0


# ---------- self-test ----------
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
    "delt": """navn: t-delt
knuder: {A: [0, 0], C: [2, 0], B: [5, 0]}
elementer:
  B1: {fra: A, til: C, profil: IPE200, materiale: S235}
  B2: {fra: B, til: C, profil: IPE200, materiale: S235}
understoetninger: {A: charnier, B: rulle}
lasttilfaelde: {Q: {laster: [{element: B1, linjelast: 10, retning: ned}, {element: B2, linjelast: 10, retning: ned}]}}
kombinationer: {K: {type: anvendelse, faktorer: {Q: 1.0}, graense: 400}}
""",
    "kontinuert": """navn: t-kontinuert
knuder: {A: [0, 0], B: [4, 0], C: [8, 0]}
elementer:
  B1: {fra: A, til: B, profil: IPE200, materiale: S235}
  B2: {fra: B, til: C, profil: IPE200, materiale: S235}
understoetninger: {A: charnier, B: rulle, C: rulle}
lasttilfaelde: {Q: {laster: [{element: B1, linjelast: 10, retning: ned}, {element: B2, linjelast: 10, retning: ned}]}}
kombinationer: {K: {type: anvendelse, faktorer: {Q: 1.0}}}
""",
    "plade": """navn: t-plade
mesh: 0.1
knuder: {A: [0, 0, 0], B: [2, 0, 0], C: [2, 2, 0], D: [0, 2, 0], M: [1, 1, 0]}
flader: {P: {hjoerner: [A, B, C, D], tykkelse: 20, materiale: C25/30}}  # tynd: a/t = 100 (Kirchhoff)
understoetninger: {A: charnier, B: rulle-x}
understoetninger_linje: [{fra: A, til: B, type: rulle}, {fra: B, til: C, type: rulle},
                         {fra: C, til: D, type: rulle}, {fra: D, til: A, type: rulle}]
lasttilfaelde: {Q: {laster: [{flade: P, tryk: 10}]}}
kombinationer: {K: {type: anvendelse, faktorer: {Q: 1.0}}}
""",
    "skive": """navn: t-skive
knuder: {A: [0, 0, 0], B: [2, 0, 0], C: [2, 0, 2.5], D: [0, 0, 2.5]}
flader: {V: {hjoerner: [A, B, C, D], tykkelse: 100, materiale: gasbeton}}
understoetninger_linje: [{fra: A, til: B, type: indspaendt}]
udtraek: {midt: {flade: V, x: [0.5, 1.5], y: [1.0, 1.5]}}
lasttilfaelde: {Q: {laster: [{linje: [D, C], linjelast: 20}]}, W: {laster: [{flade: V, tryk: 1.0, retning: y}]}}
kombinationer: {K: {type: brud, faktorer: {Q: 1.0}}, KW: {type: brud, faktorer: {W: 1.0}}}
""",
    "bjaelke-paa-vaeg": """navn: t-bjaelke-paa-vaeg
knuder: {A: [0, 0, 0], B: [3, 0, 0], C: [3, 0, 2.5], D: [0, 0, 2.5]}
flader: {V: {hjoerner: [A, B, C, D], tykkelse: 100, materiale: gasbeton}}
elementer: {J: {fra: D, til: C, profil: rekt 100x200, materiale: C24}}
understoetninger_linje: [{fra: A, til: B, type: indspaendt}]
udtraek: {midt: {flade: V, x: [1.0, 2.0], y: [1.0, 1.5]}}
lasttilfaelde: {Q: {laster: [{element: J, linjelast: 10}]}}
kombinationer: {K: {type: brud, faktorer: {Q: 1.0}}}
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
    failures = []

    def check(name, actual, expected, tol=0.01):
        ok = abs(actual - expected) <= tol * max(abs(expected), 1e-9)
        print(("OK   " if ok else "FEJL ") + f"{name}: {actual:.4g} (forventet {expected:.4g})")
        if not ok:
            failures.append(name)

    with tempfile.TemporaryDirectory() as tmp:
        res = {}
        for n, txt in TEST.items():
            p = pathlib.Path(tmp) / f"{n}.yaml"
            p.write_text(txt, encoding="utf-8")
            s = model.read_spec(p)
            res[n] = (s, model.results(s, model.analyze(s), "test"))
        s, r = res["simpel"]
        e, k = s["elementer"]["B1"], r["kombinationer"]["K"]
        EI = 210e6 * e["_t"]["I_staerk"] * 1e-12
        check("simpel bjælke M = qL²/8", k["elementer"]["B1"]["M_max"], 10 * 5 ** 2 / 8)
        check("simpel bjælke R = qL/2", k["reaktioner"]["A"]["Rz"], 25)
        check("simpel bjælke δ = 5qL⁴/384EI [mm]", abs(k["elementer"]["B1"]["delta_mm"]), 5 * 10 * 5 ** 4 / (384 * EI) * 1000)
        s, r = res["udkraget"]
        e, k = s["elementer"]["B1"], r["kombinationer"]["K"]
        EI = 11000e3 * e["_t"]["I_staerk"] * 1e-12
        check("udkraget M = PL", abs(k["elementer"]["B1"]["M_min"]), 20)
        check("udkraget δ = PL³/3EI [mm] (bøjning, uden forskydning)", abs(k["elementer"]["B1"]["delta_mm"]),
             10 * 2 ** 3 / (3 * EI) * 1000, tol=0.02)
        s, r = res["delt"]
        k = r["kombinationer"]["K"]
        EI = 210e6 * s["elementer"]["B1"]["_t"]["I_staerk"] * 1e-12
        d5 = 5 * 10 * 5 ** 4 / (384 * EI) * 1000
        dmax = max(abs(k["elementer"][n]["delta_mm"]) for n in ("B1", "B2"))
        check("delt bjælke (2 + 3 m, B2 tegnet baglæns): δ over hele spændet = 5qL⁴/384EI [mm]", dmax, d5)
        check("delt bjælke: L/δ regnes med spændets længde 5 m", k["elementer"]["B2"]["L_over_delta"], round(5000 / d5))
        s, r = res["kontinuert"]
        k = r["kombinationer"]["K"]
        ok = "spaend" not in k["elementer"]["B1"] and "spaend" not in k["elementer"]["B2"]
        print(("OK   " if ok else "FEJL ") + "kontinuert bjælke: spænd deles ved den midterste understøtning")
        if not ok:
            failures.append("kontinuert spænd")
        check("kontinuert bjælke: δ = qL⁴/185EI [mm]", abs(k["elementer"]["B1"]["delta_mm"]), 10 * 4 ** 4 / (184.6 * EI) * 1000, tol=0.02)
        s, r = res["plade"]
        k = r["kombinationer"]["K"]
        D = 31000e3 * 0.02 ** 3 / (12 * (1 - 0.2 ** 2))
        check("plade (Navier, simpelt understøttet 2×2 m): w = 0,00406·qa⁴/D [mm]",
             k["flader"]["P"]["flytning_max_mm"], 0.00406 * 10 * 2 ** 4 / D * 1000, tol=0.03)
        check("plade: m = 0,0368·(1 + ν)·qa² [kNm/m]", k["flader"]["P"]["m_abs_max_kNm_m"], 0.0368 * 1.2 * 10 * 4, tol=0.03)
        check("plade: ΣR = q·a² (lodret ligevægt)", k["ligevaegt"]["z"]["reaktioner"], 40)
        s, r = res["skive"]
        k = r["kombinationer"]["K"]
        check("skive: n_v midt i væggen = −linjelast [kN/m]", k["udtraek"]["midt"]["n_v_min_kN_m"], -20, tol=0.02)
        check("skive: σ = n/t [MPa]", k["udtraek"]["midt"]["sigma_vM_max_MPa"], 0.2, tol=0.03)
        check("skive: ΣR = linjelast · længde", k["ligevaegt"]["z"]["reaktioner"], 40)
        kw = r["kombinationer"]["KW"]
        check("skive: vindtryk i +y giver reaktion i −y", kw["ligevaegt"]["y"]["reaktioner"], -5.0)
        check("skive: udkraget væg, m i y = 1,125 m = q·(h − y)²/2 [kNm/m]", kw["udtraek"]["midt"]["m_abs_max_kNm_m"],
             1.0 * (2.5 - 1.125) ** 2 / 2, tol=0.03)
        s, r = res["bjaelke-paa-vaeg"]
        k = r["kombinationer"]["K"]
        check("bjælke på væg: lasten går gennem væggen, n_v = −q [kN/m]", k["udtraek"]["midt"]["n_v_min_kN_m"], -10, tol=0.05)
        ok = max(abs(k["elementer"]["J"]["M_max"]), abs(k["elementer"]["J"]["M_min"])) < 0.05 * 10 * 3 ** 2 / 8
        print(("OK   " if ok else "FEJL ") + "bjælke på væg: bjælken er forbundet med væggen i hele længden (M < 5 % af qL²/8)")
        if not ok:
            failures.append("bjælke på væg")
        s, r = res["ramme"]
        k = r["kombinationer"]["K"]
        q = 1.2 * (12 + 78.5 * s["elementer"]["B1"]["_t"]["A"] * 1e-6)
        b1 = k["elementer"]["B1"]
        check("ramme: felt- + hjørnemoment = qL²/8", b1["M_max"] - b1["M_min"], q * 4.2 ** 2 / 8)
        ok = b1["M_max"] > 0 > b1["M_min"]
        print(("OK   " if ok else "FEJL ") + "ramme: feltmoment positivt (træk i underside), hjørnemoment negativt")
        if not ok:
            failures.append("fortegn")
        s1 = k["elementer"]["S1"]
        check("ramme: søjle i tryk, N ved fod = −R", s1["N_min"], -k["reaktioner"]["A"]["Rz"], tol=0.02)
        check("ramme: lodret ligevægt", k["ligevaegt"]["z"]["reaktioner"], -k["ligevaegt"]["z"]["laster"])
    print("\nALLE TESTS BESTÅET" if not failures else f"\n{len(failures)} FEJL")
    return 1 if failures else 0


def main(args) -> int:
    argv = list(args)
    cmd, rest = args[0], args[1:]
    try:
        if cmd == "skabelon":
            print((EXAMPLE_SHELLS if rest[:1] == ["flader"] else EXAMPLE).read_text(encoding="utf-8"))
            return 0
        if cmd == "test":
            return test(rest, argv)
        if cmd in ("regn", "tegn", "vis", "resultat"):
            if not rest:
                print(f"Brug: fem.py {cmd} <fem.yaml> …", file=sys.stderr)
                return 2
            return {"regn": calc, "tegn": draw, "vis": view, "resultat": result}[cmd](rest, argv)
        print(f"Ukendt kommando '{cmd}'. Se: python3 fem.py --help", file=sys.stderr)
        return 2
    except SpecError as e:
        print(f"FEJL i modellen: {e}", file=sys.stderr)
        return 2
    except FileNotFoundError as e:
        print(f"FEJL: {e}", file=sys.stderr)
        return 2
