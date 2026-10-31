#!/usr/bin/env python3
"""Tests el.py (electrical cable and panel checks) beyond its built-in self-test: hand calculations and panel findings.

Run:  python3 tests/test_el.py
"""
import copy
import json
import pathlib
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
EL = ROOT / "plugins" / "byg-electrical" / "skills" / "electrical-knowledge" / "scripts" / "el.py"
sys.path.insert(0, str(EL.parent))
import el  # noqa: E402

FAILURES = []


def expect(name, ok, detail=""):
    print(("OK   " if ok else "FEJL ") + name + ("" if ok else f"\n     {detail}"))
    if not ok:
        FAILURES.append(name)


def near(a, b, tol):
    return abs(a - b) <= tol


def texts(data):
    return " | ".join(f"{f['gruppe']}:{f['alvor']}:{f['tekst']}" for f in el.check_panel(data)["fund"])


def run(*args):
    return subprocess.run([sys.executable, str(EL), *args], capture_output=True, text=True)


def main():
    # Iz: table lookup, worst segment, grouping and ambient
    expect("Iz 1,5 PVC C 2 belastede = 19,5", el.table_iz(1.5, "C", "pvc", 2) == 19.5)
    expect("Iz 6 XLPE E 3 belastede = 54", el.table_iz(6, "E", "xlpe", 3) == 54)
    cap = el.capacity(1.5, ["C"], "pvc", 2, insulated_mm=600)
    expect("1,5 mm² > 0,5 m i isolering: 19,5 · 0,5", near(cap["iz"], 9.8, 0.05), cap)
    cap = el.capacity(2.5, ["C"], "pvc", 2, grouped=3, ambient=40)
    expect("Cg 3 kredse og 40 °C: 27 · 0,7 · 0,87", near(cap["iz"], 27 * 0.7 * el.ambient_factor("pvc", 40), 0.1), cap)
    expect("Cg 10 kredse → værdien for 12", el.grouping_factor(10) == 0.45)
    ov = el.overload_check(15.0, 16, "mcb")
    expect("B16 på Iz 15 A fejler", not ov["ok"] and ov["maks_in"] == 15.0, ov)
    ov = el.overload_check(20.0, 16, "gG")
    expect("gG16: I2 25,6 ≤ 1,45 · 20", ov["ok"] and ov["i2"] == 25.6, ov)
    # Voltage drop and max length are each other's inverse
    pct, _, _ = el.voltage_drop(1.5, 30, 10)
    lmax = el.max_length_vdrop(1.5, 10, pct)
    expect("ΔU → maks. længde er invers", near(lmax, 30, 1e-6), lmax)
    # Ik,min: closed-form max length gives exactly Ia
    r = el.ik_min(1.5, 10, 10, "C", service_fuse=25)
    at_max = el.ik_min(1.5, r["maks_laengde"], 10, "C", service_fuse=25)["ik_min"]
    expect("Ik,min ved maks. længde = Ia", near(at_max, 100, 0.5), (r, at_max))
    expect("Ik,min under Ia giver maks. tid", "maks_tid_s" in el.ik_min(1.5, 40, 10, "C", service_fuse=25))
    expect("Ik,min kræver netværdi", run("ikmin", "--size", "1.5", "--length", "10", "--rating", "10",
                                         "--curve", "B").returncode != 0)
    # Panel: the template is clean; each defect is found
    expect("Skabelon uden fund", not el.check_panel(el.TEMPLATE)["fund"], texts(el.TEMPLATE))
    cases = [
        ("type AC", lambda d: d["rcd"][0].update(type="AC"), "type AC"),
        ("type B efter type A", lambda d: d["rcd"][2].update(foran="RCD1"), "blinde"),
        ("to 30 mA i serie", lambda d: d["rcd"][1].update(foran="RCD1"), "uden type S"),
        ("gruppe uden RCD", lambda d: d["grupper"][0].pop("rcd"), "ingen RCD"),
        ("elbil på type A uden RDC-DD", lambda d: d["grupper"][2].update(rcd="RCD2"), "uden type B"),
        ("elbil deler RCD", lambda d: (d["rcd"][2].update(type="B"), d["grupper"][1].update(rcd="RCD3")), "deles"),
        ("kabel i isolering overbelastet", lambda d: d["grupper"][0].update(isoleret_mm=500), "beskytter ikke"),
        ("lang gruppe – Ik,min", lambda d: d["grupper"][0].update(laengde=120), "Ik,min"),
        ("spændingsfald", lambda d: d["grupper"][1].update(laengde=60, last=13), "spændingsfald"),
        ("brydeevne uden back-up", lambda d: d["tavle"].pop("backup_ka"), "brydeevne"),
        ("reserveplads", lambda d: d["tavle"].update(pladser_brugt=34), "reserveplads"),
        ("selektivitet forsikring", lambda d: d["tavle"].update(forsikring=25), "selektivitet"),
        ("LED-indkobling", lambda d: d["grupper"][0].update(led_spots=40), "LED"),
        ("kun én RCD", lambda d: (d.update(grupper=d["grupper"][:2]), d["grupper"][1].update(rcd="RCD1")), "færre end to"),
        ("varmepumpe på type A", lambda d: d["grupper"].append(dict(d["grupper"][1], nr="4", anvendelse="varmepumpe",
                                                                     isoleret_mm=0)), "type F"),
    ]
    for name, mutate, want in cases:
        d = copy.deepcopy(el.TEMPLATE)
        mutate(d)
        t = texts(d)
        expect(f"Tavle: {name}", want in t, t)
    # CLI: markdown table header is stable (the diagram reuses it) and the command line is printed first
    path = pathlib.Path("/tmp/el_test_tavle.json")
    path.write_text(json.dumps(el.TEMPLATE, ensure_ascii=False), encoding="utf-8")
    out = run("panel", str(path)).stdout
    expect("Fast tabelhoved", "| Gruppe | Sikring/kurve | Fase | Kabel/tværsnit/metode | RCD (type/mA) | Længde | ΔU % | "
                              "Ik,min | Status |" in out, out[:400])
    expect("Kommandolinje først", out.startswith("Kommando: `python3 "), out[:100])
    out = json.loads(run("panel", str(path), "--format", "json").stdout)
    expect("JSON med kommando og grupper", out["kommando"].startswith("python3 ") and len(out["grupper"]) == 3)
    expect("Selvtest", run("test").returncode == 0)
    print("\nALLE TESTS BESTÅET" if not FAILURES else f"\n{len(FAILURES)} FEJL")
    return 1 if FAILURES else 0


if __name__ == "__main__":
    sys.exit(main())
