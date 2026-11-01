#!/usr/bin/env python3
"""Cable and panel checks for the electrician (Python standard library only, writes no files).

Deterministic checks of final circuits and a distribution board against DS/HD 60364: current-carrying capacity
(Annex B tables with correction factors), voltage drop, minimum short-circuit current at the end of the circuit,
breaking capacity and panel checks (RCD topology, selectivity, phase balance, spare space, LED inrush).
Results are a DESIGN AID – the authorised electrical contractor verifies the installation (BEK 1082 § 75).
Every table value and factor below carries its source and status (V = verified against the source, T = not
verified). See references/calc-tools.md for assumptions and limits.

Commands:
  el.py iz       --size MM2 --method M [--method …] [--insulated-mm MM] [--rating A --device mcb|gG] …
  el.py vdrop    --size MM2 --length M --current A [--phases 1|3] [--limit PCT] [--upstream PCT]
  el.py ikmin    --size MM2 --length M --rating A --curve B|C|D [--ik-net A | --service-fuse A]
                 [--feeder-size MM2 --feeder-length M --feeder-insulation pvc|xlpe]
  el.py ikmax    --icn A [--ik-net A] [--feeder-size MM2 --feeder-length M]
  el.py panel    <tavle.json> [--format md|json]     fixed panel schedule with findings
  el.py template                                     example panel file (copy, edit, save as JSON)
  el.py test                                         self-test
"""
import argparse
import json
import math
import pathlib
import shlex
import sys

U0 = 230.0      # V phase voltage
U_LINE = 400.0  # V line voltage

SIZES = (1.5, 2.5, 4.0, 6.0, 10.0, 16.0, 25.0)
METHODS = ("A1", "A2", "B1", "B2", "C", "E")

# --- Current-carrying capacity Iz [A], copper, ambient 30 °C – DS/HD 60364-5-52:2011 (= IEC 60364-5-52:2009) Annex B.
# (insulation, loaded conductors) -> method -> values per SIZES.
# PVC 70 °C: tables B.52.2 (2 loaded) and B.52.4 (3 loaded). XLPE/EPR 90 °C: B.52.3 and B.52.5. Method E (multicore
# cable in free air): B.52.10 (PVC) and B.52.12 (XLPE). Status: see IZ_STATUS. NOIKLX 90 is PEX/XLPE 90 °C (NKT data via
# wholesaler, V secondary); NOIKLX from before May 2015, PVIKLX and unknown cable: use the PVC tables (T).
IZ = {
    ("pvc", 2): {"A1": (14.5, 19.5, 26, 34, 46, 61, 80), "A2": (14, 18.5, 25, 32, 43, 57, 75),
                 "B1": (17.5, 24, 32, 41, 57, 76, 101), "B2": (16.5, 23, 30, 38, 52, 69, 90),
                 "C": (19.5, 27, 36, 46, 63, 85, 112), "E": (22, 30, 40, 51, 70, 94, 119)},
    ("pvc", 3): {"A1": (13.5, 18, 24, 31, 42, 56, 73), "A2": (13, 17.5, 23, 29, 39, 52, 68),
                 "B1": (15.5, 21, 28, 36, 50, 68, 89), "B2": (15, 20, 27, 34, 46, 62, 80),
                 "C": (17.5, 24, 32, 41, 57, 76, 96), "E": (18.5, 25, 34, 43, 60, 80, 101)},
    ("xlpe", 2): {"A1": (19, 26, 35, 45, 61, 81, 106), "A2": (18.5, 25, 33, 42, 57, 76, 99),
                  "B1": (23, 31, 42, 54, 75, 100, 133), "B2": (22, 30, 40, 51, 69, 91, 119),
                  "C": (24, 33, 45, 58, 80, 107, 138), "E": (26, 36, 49, 63, 86, 115, 149)},
    ("xlpe", 3): {"A1": (17, 23, 31, 40, 54, 73, 95), "A2": (16.5, 22, 30, 38, 51, 68, 89),
                  "B1": (20, 28, 37, 48, 66, 88, 117), "B2": (19.5, 26, 35, 44, 60, 80, 105),
                  "C": (22, 30, 40, 52, 71, 96, 119), "E": (23, 32, 42, 54, 75, 100, 127)},
}
IZ_STATUS = ("DS/HD 60364-5-52 anneks B, tabel B.52.2–B.52.5, B.52.10, B.52.12 (V sekundær 2026-10-31: alle værdier "
             "= Prysmian LV-kabelvejledning 2024 og Top Cable efter IEC 60364-5-52 ed. 3; DS/HD-teksten ikke læst)")
METHOD_TEXT = {
    "A1": "isolerede ledere i rør i varmeisoleret væg",
    "A2": "flerlederkabel i rør i varmeisoleret væg",
    "B1": "isolerede ledere i rør på eller i murværk/træ",
    "B2": "flerlederkabel i rør på eller i murværk/træ",
    "C": "kabel fastgjort direkte på væg eller loft (ikke isoleret)",
    "E": "flerlederkabel i fri luft (kabelbakke, perforeret)",
}
MAX_TEMP = {"pvc": 70.0, "xlpe": 90.0}  # °C maximum conductor temperature in normal service (Annex B table headings)

# Cable totally surrounded by thermal insulation: factor on the method C value. Values are BS 7671 table 52.2
# (V secondary 2026-10-31; valid up to 10 mm² and λ > 0,04 W/m·K); > 0,5 m → 0,5 matches DS/HD 60364-5-52 523.9 (T –
# the HD text was not read, the short-length table is probably UK only). Linear interpolation, 0,88 below 50 mm.
INSULATED = ((50, 0.88), (100, 0.78), (200, 0.63), (400, 0.51), (500, 0.50))

# Grouping, bunched in air, on a surface, embedded or enclosed: table B.52.17 row 1 (T – from memory, not re-checked). Between listed counts the
# value for the next larger count is used (on the safe side).
GROUPING = ((1, 1.00), (2, 0.80), (3, 0.70), (4, 0.65), (5, 0.60), (6, 0.57), (7, 0.54), (8, 0.52), (9, 0.50),
            (12, 0.45), (16, 0.41), (20, 0.38))

# Conductor resistance at 20 °C [Ω/km], plain copper class 1/2 – IEC 60228 table 1/2 maximum values (T).
# Deliberate choice: per-size R20 × (1 + α(θ − 20)) gives ρ70 ≈ 0,0217–0,0222 Ω·mm²/m, about 1,5–3,5 % below the
# hand-calculation convention ρ = 0,0225 (1,25 × ρ20). See references/calc-tools.md, "Modstand".
R20 = {1.5: 12.1, 2.5: 7.41, 4.0: 4.61, 6.0: 3.08, 10.0: 1.83, 16.0: 1.15, 25.0: 0.727, 35.0: 0.524}
ALPHA_CU = 0.00393   # 1/K copper (IEC 60228 annex B)
X_PER_M = 0.08e-3    # Ω/m reactance per conductor – usual value for small cables (T; Annex G value not found)

# Socket-outlet rating → largest permitted rating of the nearest upstream short-circuit protection – BEK 1082/2016
# § 45 (V 2026-11-01, retsinformation.dk). A group with anvendelse "stik" and no stikkontakt_a is taken as 13 A.
SOCKET_MAX_FUSE = {10: 13, 13: 13, 16: 16}
SOCKET_DEFAULT_A = 13

# Instantaneous tripping, upper limit of the band → guaranteed instantaneous trip: EN 60898-1 (B 3–5, C 5–10,
# D 10–20 × In) (V secondary 2026-10-31, manufacturer catalogues; many D products trip at 10–14 × In).
CURVE_IA = {"B": 5, "C": 10, "D": 20}
# Conventional tripping current I2/In: MCB EN 60898-1 1,45 (T); gG fuse IEC 60269-1: In ≥ 16 A 1,6 (V secondary,
# IET); 4 < In < 16 A 1,9 and In ≤ 4 A 2,1 (T).

VDROP_LIMIT = 4.0  # % from the origin – DS/HD 60364-5-52 pkt. 525 recommendation (V secondary, weak; no Danish rule
#                    found – Fællesregulativet 2026 has none). Annex G.52.1 public supply: 3 % lighting / 5 % other (T).
IK_MAX_NET = 16000.0  # A, 3-phase, cos φ 0,3, just in front of the service cable – Fællesregulativet 2026 Del B pkt. 14 (V)
IK_MAX_COSPHI = 0.3
IK_MIN_FACTOR = 5.0  # Ik min L–N = 5 × service fuse In, just in front of the service cable – Fællesregulativet 2026 Del B
#                      pkt. 14 (V 2026-10-31). The service cable's impedance must be added to get the value at the panel.
# k for copper in the adiabatic equation t = (k·S/I)²: PVC 115, XLPE 143 – DS/HD 60364-4-43 434.5.2 / -5-54 (T).
K_ADIABATIC = {"pvc": 115.0, "xlpe": 143.0}
SPARE_MIN = 0.20     # spare space in the panel [ERFARING – vejledende]
SELECTIVITY_RATIO = 1.6  # upstream fuse ≥ 1,6 × largest group [ERFARING – vejledende; fabrikantens tabel afgør]
LED_PER_B16 = 30     # LED spots per B16, twice on C [ERFARING – vejledende; driverens datablad afgør]

SRC = {
    "433": "DS/HD 60364-4-43 pkt. 433.1 (Ib ≤ In ≤ Iz, I2 ≤ 1,45·Iz)",
    "411": "DS/HD 60364-4-41 pkt. 411.3.2 og tabel 41.1 (automatisk afbrydelse) og -4-43 pkt. 434 (kortslutning)",
    "434": "DS/HD 60364-4-43 pkt. 434.5.1 (brydeevne; back-up efter fabrikantens tabel)",
    "525": "DS/HD 60364-5-52 pkt. 525 og anneks G (anbefaling, ikke krav)",
    "35": "BEK 1082/2016 § 35 stk. 1–2 (RCD ≤ 30 mA)",
    "53": "BEK 1082/2016 § 53 (type AC ikke som fejlbeskyttelse i boliger)",
    "531": "DS/HD 60364-5-53 pkt. 531.3 (T) og fabrikantens anvisning: glat DC > 6 mA kan blinde type A/F foran",
    "722": "Sikkerhedsstyrelsen, opladning af elbiler / DS/HD 60364-7-722 (egen RCD, type B eller type A/F + RDC-DD 6 mA)",
    "535": "DS/HD 60364-5-53 pkt. 535 (T): selektivitet kræver type S foran og IΔn ≥ 3 × efterfølgende",
    "5313": "DS/HD 60364-5-53 pkt. 531.3.6 / Sikkerhedsstyrelsen, valg af RCD (som udgangspunkt mindst to RCD'er)",
    "45": "BEK 1082/2016 § 45 (stikkontakt 10 A og 13 A: højst 13 A kortslutningsbeskyttelse; 16 A: højst 16 A)",
    "erf": "[ERFARING – vejledende]",
}

TEMPLATE = {
    "tavle": {
        "navn": "Hovedtavle", "system": "TN", "forsikring": 35, "ik_min_net": None, "ik_max_net": 16000,
        "stikledning": {"tvaersnit": 16, "laengde": 15, "isolering": "xlpe"},
        "spaendingsfald_foran": 0.5, "spaendingsfald_graense": 4, "pladser": 36, "pladser_brugt": 24,
        "backup_ka": 25,
    },
    "rcd": [
        {"id": "RCD1", "type": "A", "ma": 30, "in": 40, "foran": None},
        {"id": "RCD2", "type": "A", "ma": 30, "in": 40, "foran": None},
        {"id": "RCD3", "type": "B-EV", "ma": 30, "in": 40, "foran": None},
    ],
    "grupper": [
        {"nr": "1", "navn": "Lys stue/køkken", "sikring": 13, "kurve": "B", "icn": 6000, "fase": "L1",
         "kabel": "PVIKLX", "tvaersnit": 1.5, "isolering": "pvc", "metode": ["B2"], "isoleret_mm": 0, "samlet": 1,
         "laengde": 20, "last": 5, "rcd": "RCD1", "anvendelse": "lys", "led_spots": 24},
        {"nr": "2", "navn": "Stik køkken", "sikring": 13, "kurve": "B", "icn": 6000, "fase": "L2",
         "kabel": "PVIKLX", "tvaersnit": 2.5, "isolering": "pvc", "metode": ["B2", "C"], "isoleret_mm": 100,
         "samlet": 1, "laengde": 18, "last": 10, "rcd": "RCD2", "anvendelse": "stik", "stikkontakt_a": 13},
        {"nr": "3", "navn": "Elbillader", "sikring": 16, "kurve": "B", "icn": 6000, "fase": "L1L2L3",
         "kabel": "NOIKLX", "tvaersnit": 6, "isolering": "xlpe", "metode": ["C"], "samlet": 1,
         "laengde": 25, "last": 16, "rcd": "RCD3", "anvendelse": "elbil"},
    ],
}


class InputError(Exception):
    pass


def fmt(x, nd=1):
    """Danish number format with decimal comma."""
    if isinstance(x, float) and x.is_integer() and nd <= 1:
        return str(int(x))
    return f"{x:.{nd}f}".replace(".", ",")


def output(res):
    """Print JSON with the command that produced it (for the appendix and the reviewer's re-run)."""
    path = shlex.quote(str(pathlib.Path(__file__).resolve()))
    res = {"kommando": f"python3 {path} " + " ".join(shlex.quote(x) for x in sys.argv[1:]), **res}
    print(json.dumps(res, ensure_ascii=False, indent=2))


# --- Core calculations -------------------------------------------------------------------------------------------

def size_index(size):
    for i, s in enumerate(SIZES):
        if abs(s - size) < 1e-9:
            return i
    raise InputError(f"tværsnit {fmt(size)} mm² findes ikke i tabellen ({', '.join(fmt(s) for s in SIZES)} mm²)")


def table_iz(size, method, insulation, loaded):
    if (insulation, loaded) not in IZ:
        raise InputError("isolering skal være pvc eller xlpe og belastede ledere 2 eller 3")
    if method not in IZ[(insulation, loaded)]:
        raise InputError(f"ukendt installationsmetode '{method}' ({', '.join(METHODS)})")
    return IZ[(insulation, loaded)][method][size_index(size)]


def insulated_factor(mm):
    """Factor for a cable totally surrounded by thermal insulation over mm millimetres (applied to method C)."""
    if mm <= 0:
        return 1.0
    if mm <= INSULATED[0][0]:
        return INSULATED[0][1]
    for (l0, f0), (l1, f1) in zip(INSULATED, INSULATED[1:]):
        if mm <= l1:
            return round(f0 + (f1 - f0) * (mm - l0) / (l1 - l0), 3)
    return INSULATED[-1][1]


def ambient_factor(insulation, ambient):
    """Ca = sqrt((θmax − θa)/(θmax − 30)); reproduces table B.52.14 (air) to two decimals."""
    tmax = MAX_TEMP[insulation]
    if ambient >= tmax:
        raise InputError(f"omgivelsestemperatur {fmt(ambient)} °C ≥ lederens maks. {fmt(tmax)} °C")
    return math.sqrt((tmax - ambient) / (tmax - 30.0))


def grouping_factor(n):
    n = max(1, int(n))
    for count, f in GROUPING:
        if n <= count:
            return f
    raise InputError(f"samlet fremføring over {GROUPING[-1][0]} kredse – brug tabel B.52.17 direkte (--cg)")


def conventional_factor(device, rating):
    if device == "mcb":
        return 1.45
    if rating <= 4:
        return 2.1
    return 1.9 if rating < 16 else 1.6


def capacity(size, methods, insulation="pvc", loaded=2, insulated_mm=0.0, ambient=30.0, grouped=1, cg=None):
    """Iz for each segment of the route; the worst segment governs."""
    ca = ambient_factor(insulation, ambient)
    g = cg if cg is not None else grouping_factor(grouped)
    segments = []
    for m in methods:
        base = table_iz(size, m, insulation, loaded)
        segments.append({"del": m, "beskrivelse": METHOD_TEXT[m], "iz_tabel": base, "ci": 1.0,
                         "iz": round(base * ca * g, 1)})
    if insulated_mm > 0:
        base = table_iz(size, "C", insulation, loaded)
        ci = insulated_factor(insulated_mm)
        segments.append({"del": f"isolering {fmt(insulated_mm, 0)} mm", "beskrivelse":
                         "kabel helt omgivet af varmeisolering (faktor på metode C)", "iz_tabel": base, "ci": ci,
                         "iz": round(base * ci * ca * g, 1)})
    if not segments:
        raise InputError("angiv mindst én installationsmetode")
    worst = min(segments, key=lambda s: s["iz"])
    return {"ca": round(ca, 3), "cg": g, "dele": segments, "iz": worst["iz"], "afgoerende": worst["del"]}


def overload_check(iz, rating, device="mcb", ib=None):
    k = conventional_factor(device, rating)
    i2 = k * rating
    res = {"in": rating, "i2": round(i2, 1), "i2_faktor": k, "krav_in_le_iz": rating <= iz,
           "krav_i2_le_145iz": i2 <= 1.45 * iz + 1e-9, "maks_in": round(min(iz, 1.45 * iz / k), 1)}
    if ib is not None:
        res["ib"] = ib
        res["krav_ib_le_in"] = ib <= rating
    res["ok"] = all(v for key, v in res.items() if key.startswith("krav_"))
    return res


def r_per_m(size, temp):
    if size not in R20:
        raise InputError(f"ingen ledermodstand for {fmt(size)} mm²")
    return R20[size] / 1000.0 * (1 + ALPHA_CU * (temp - 20.0))


def voltage_drop(size, length, current, phases=1, cosphi=1.0, temp=70.0):
    """ΔU in % of the nominal voltage. 1-phase: 2·L·I·(R'cosφ + X'sinφ)/230; 3-phase: √3·L·I·(…)/400."""
    k, u = (2.0, U0) if phases == 1 else (math.sqrt(3), U_LINE)
    sinphi = math.sqrt(max(0.0, 1 - cosphi ** 2))
    per_m_amp = k * (r_per_m(size, temp) * cosphi + X_PER_M * sinphi)
    return length * current * per_m_amp / u * 100.0, per_m_amp, u


def max_length_vdrop(size, current, budget_pct, phases=1, cosphi=1.0, temp=70.0):
    _, per_m_amp, u = voltage_drop(size, 1.0, current, phases, cosphi, temp)
    return max(0.0, budget_pct / 100.0 * u / (per_m_amp * current))


def tripping_current(curve, rating, ia=None):
    if ia:
        return ia
    if curve not in CURVE_IA:
        raise InputError("for sikringer (gG) og andre kurver skal --ia angives fra fabrikantens tid-strøm-kurve")
    return CURVE_IA[curve] * rating


def net_impedance_min(ik_net=None, service_fuse=None):
    if ik_net:
        return U0 / ik_net, ik_net, "angivet"
    if service_fuse:
        ik = IK_MIN_FACTOR * service_fuse
        return U0 / ik, ik, f"Fællesregulativet 2026: 5 × stikledningssikring {fmt(service_fuse, 0)} A"
    raise InputError("angiv --ik-net (fra netselskabet eller måling) eller --service-fuse")


def ik_min(size, length, rating, curve, ik_net=None, service_fuse=None, ia=None, temp=70.0,
           feeder_size=None, feeder_length=0.0, feeder_temp=90.0, insulation="pvc"):
    """Ik,min at the end of the circuit (phase–neutral): U0 / (Z_net + Z_feeder + Z_cable), magnitudes added."""
    z_net, ik_n, origin = net_impedance_min(ik_net, service_fuse)
    z_feed = 2 * feeder_length * r_per_m(feeder_size, feeder_temp) if feeder_size and feeder_length else 0.0
    r = r_per_m(size, temp)
    z_cable = 2 * length * r
    ik = U0 / (z_net + z_feed + z_cable)
    i_a = tripping_current(curve, rating, ia)
    l_max = max(0.0, (U0 / i_a - z_net - z_feed) / (2 * r))
    res = {"ik_net": round(ik_n), "ik_net_kilde": origin, "z_net": round(z_net, 4), "z_forsyning": round(z_feed, 4),
           "forsyning_temperatur": feeder_temp if z_feed else None, "z_kabel": round(z_cable, 4), "ledertemperatur": temp, "ik_min": round(ik, 1), "ia": i_a,
           "ok": ik >= i_a, "maks_laengde": round(l_max, 1)}
    if ik < i_a:
        # No instantaneous trip: the device's time-current curve must clear Ik,min before the conductor limit.
        res["maks_tid_s"] = round((K_ADIABATIC[insulation] * size / ik) ** 2, 1)
    return res


def ik_max_panel(ik_net=IK_MAX_NET, feeder_size=None, feeder_length=0.0):
    """3-phase Ik at the panel: network impedance (cos φ 0,3) plus service cable at 20 °C, added as vectors."""
    z = U0 / ik_net
    r, x = z * IK_MAX_COSPHI, z * math.sqrt(1 - IK_MAX_COSPHI ** 2)
    if feeder_size and feeder_length:
        r += feeder_length * r_per_m(feeder_size, 20.0)
        x += feeder_length * X_PER_M
    return U0 / math.hypot(r, x)


def next_size(size):
    i = size_index(size)
    return SIZES[i + 1] if i + 1 < len(SIZES) else None


# --- CLI commands ------------------------------------------------------------------------------------------------

def cmd_iz(a):
    cap = capacity(a.size, a.method, a.insulation, a.loaded, a.insulated_mm, a.ambient, a.grouped, a.cg)
    res = {"tvaersnit": a.size, "isolering": a.insulation, "belastede_ledere": a.loaded, **cap, "kilde": IZ_STATUS}
    if a.rating:
        res["kontrol"] = overload_check(cap["iz"], a.rating, a.device, a.ib)
        res["kontrol"]["kilde"] = SRC["433"]
    output(res)


def cmd_vdrop(a):
    temp = a.temp if a.temp is not None else MAX_TEMP[a.insulation]
    limit = a.limit if a.limit is not None else VDROP_LIMIT
    pct, _, u = voltage_drop(a.size, a.length, a.current, a.phases, a.cosphi, temp)
    budget = limit - a.upstream
    res = {"tvaersnit": a.size, "laengde": a.length, "strøm": a.current, "faser": a.phases, "spaending": u,
           "ledertemperatur": temp, "spaendingsfald_pct": round(pct, 2), "foran_pct": a.upstream,
           "samlet_pct": round(pct + a.upstream, 2), "graense_pct": limit,
           "graense_kilde": "angivet" if a.limit is not None else SRC["525"],
           "ok": pct + a.upstream <= limit + 1e-9,
           "maks_laengde": round(max_length_vdrop(a.size, a.current, budget, a.phases, a.cosphi, temp), 1)}
    nxt = next_size(a.size)
    if nxt:
        res["naeste_tvaersnit"] = {"tvaersnit": nxt, "maks_laengde": round(
            max_length_vdrop(nxt, a.current, budget, a.phases, a.cosphi, temp), 1)}
    output(res)


def cmd_ikmin(a):
    temp = a.temp if a.temp is not None else MAX_TEMP[a.insulation]
    feeder_temp = MAX_TEMP[a.feeder_insulation]
    res = ik_min(a.size, a.length, a.rating, a.curve, a.ik_net, a.service_fuse, a.ia, temp, a.feeder_size,
                 a.feeder_length, feeder_temp, a.insulation)
    res = {"tvaersnit": a.size, "laengde": a.length, "sikring": f"{a.curve}{fmt(a.rating, 0)}", **res,
           "krav": "Ik,min ≥ Ia (B 5·In, C 10·In, D 20·In – momentan udløsning inden for 0,1 s)", "kilde": SRC["411"]}
    nxt = next_size(a.size)
    if nxt:
        res["naeste_tvaersnit"] = {"tvaersnit": nxt, "maks_laengde": ik_min(
            nxt, a.length, a.rating, a.curve, a.ik_net, a.service_fuse, a.ia, temp, a.feeder_size, a.feeder_length,
            feeder_temp, a.insulation)["maks_laengde"]}
    output(res)


def cmd_ikmax(a):
    ik = ik_max_panel(a.ik_net, a.feeder_size, a.feeder_length)
    output({"ik_max_net": a.ik_net, "ik_max_tavle": round(ik), "icn": a.icn, "ok": a.icn >= ik,
            "note": "Icn < Ik,max kræver back-up-beskyttelse dokumenteret i fabrikantens tabel" if a.icn < ik else "",
            "kilde": SRC["434"] + "; Fællesregulativet 2026 Del B pkt. 13"})


# --- Panel -------------------------------------------------------------------------------------------------------

def rcd_chain(rcds, rid):
    chain, seen = [], set()
    while rid:
        if rid in seen:
            raise InputError(f"RCD-kæden har en løkke ved {rid}")
        if rid not in rcds:
            raise InputError(f"ukendt RCD '{rid}'")
        seen.add(rid)
        chain.append(rcds[rid])
        rid = rcds[rid].get("foran")
    return chain


def is_type_b(t):
    return str(t).upper().startswith("B")


def check_panel(data):
    panel = data.get("tavle", {})
    rcds = {r["id"]: r for r in data.get("rcd", [])}
    groups = data.get("grupper", [])
    if not groups:
        raise InputError("tavlefilen har ingen grupper")
    findings = []

    def add(group, severity, text, src):
        findings.append({"gruppe": group, "alvor": severity, "tekst": text, "kilde": SRC.get(src, src)})

    fuse = panel.get("forsikring")
    feeder = panel.get("stikledning") or {}
    f_size, f_len = feeder.get("tvaersnit"), feeder.get("laengde", 0.0)
    f_temp = MAX_TEMP[feeder.get("isolering", "xlpe")]
    ik_min_net = panel.get("ik_min_net") or (IK_MIN_FACTOR * fuse if fuse else None)
    if not ik_min_net:
        raise InputError("tavle.ik_min_net eller tavle.forsikring skal angives")
    ik_max = ik_max_panel(panel.get("ik_max_net") or IK_MAX_NET, f_size, f_len)
    limit = panel.get("spaendingsfald_graense", VDROP_LIMIT)
    upstream = panel.get("spaendingsfald_foran", 0.0)
    backup = (panel.get("backup_ka") or 0) * 1000.0  # combined breaking capacity from the manufacturer's table

    # RCD topology
    for r in rcds.values():
        t = str(r.get("type", "")).upper()
        if t == "AC":
            add(r["id"], "advarsel", f"{r['id']} er type AC", "53")
        up = rcds.get(r.get("foran")) if r.get("foran") else None
        if r.get("foran") and up is None:
            raise InputError(f"ukendt RCD '{r['foran']}' foran {r['id']}")
        if up:
            if is_type_b(t) and not is_type_b(up.get("type")):
                add(r["id"], "advarsel", f"type {r['type']} ({r['id']}) efter type {up['type']} ({up['id']}): glat "
                    "DC-fejlstrøm kan blinde RCD'en foran – sæt type B først, forsyn fra tilgangssiden, eller vis at "
                    "type B'en begrænser DC til 6 mA (fabrikantens datablad)", "531")
            up_s = str(up.get("type", "")).upper().endswith("S") or up.get("selektiv")
            if not up_s:
                add(r["id"], "vejledende", f"{up['id']} og {r['id']} i serie uden type S – ingen selektivitet; "
                    "en fejl kan slå begge fra", "535")
            elif up.get("ma", 0) < 3 * r.get("ma", 30):
                add(r["id"], "vejledende", f"{up['id']} (S) har IΔn under 3 × {r['id']} – ikke selektiv", "535")
        if fuse and r.get("in") and r["in"] < fuse:
            add(r["id"], "vejledende", f"{r['id']} {fmt(r['in'], 0)} A har mindre mærkestrøm end forsikringen "
                f"{fmt(fuse, 0)} A – kontrollér fabrikantens maks. forsikring/back-up og summen af gruppesikringer",
                "erf")
    final_rcds = {g.get("rcd") for g in groups if g.get("rcd")}
    if len([r for r in final_rcds if rcds.get(r, {}).get("ma", 999) <= 30]) < 2 and len(groups) > 1:
        add("tavle", "vejledende", "grupperne fordeles på færre end to 30 mA-RCD'er – én fejl afbryder hele "
            "installationen", "5313")

    rows, phase_load, largest = [], {"L1": 0.0, "L2": 0.0, "L3": 0.0}, 0.0
    for g in groups:
        gid = str(g.get("nr", "?"))
        before = len(findings)
        ins = g.get("isolering", "pvc")
        phases_txt = str(g.get("fase", "L1")).upper().replace(" ", "")
        three = phases_txt in ("L1L2L3", "3", "3F")
        phases = 3 if three else 1
        rating, curve = g["sikring"], str(g.get("kurve", "B")).upper()
        largest = max(largest, rating)
        methods = g.get("metode") or ["C"]
        methods = [methods] if isinstance(methods, str) else methods
        cap = capacity(g["tvaersnit"], methods, ins, 3 if three else 2, g.get("isoleret_mm", 0.0),
                       g.get("omgivelse", 30.0), g.get("samlet", 1), g.get("cg"))
        device = "gG" if curve == "GG" else "mcb"
        ov = overload_check(cap["iz"], rating, device, g.get("last"))
        if not ov["krav_in_le_iz"] or not ov["krav_i2_le_145iz"]:
            add(gid, "advarsel", f"{curve}{fmt(rating, 0)} beskytter ikke kablet: Iz {fmt(cap['iz'])} A "
                f"(afgørende: {cap['afgoerende']}), maks. sikring {fmt(ov['maks_in'])} A", "433")
        if ov.get("krav_ib_le_in") is False:
            add(gid, "advarsel", f"last {fmt(g['last'])} A over sikringen {fmt(rating, 0)} A", "433")
        ib = g.get("last") or rating
        length = g.get("laengde", 0.0)
        temp = MAX_TEMP[ins]
        du, _, _ = voltage_drop(g["tvaersnit"], length, ib, phases, g.get("cosphi", 1.0), temp)
        if du + upstream > limit:
            add(gid, "vejledende", f"spændingsfald {fmt(du + upstream, 2)} % (inkl. {fmt(upstream, 2)} % foran) over "
                f"{fmt(limit)} % ved {fmt(ib)} A", "525")
        if curve not in CURVE_IA and not g.get("ia"):
            raise InputError(f"gruppe {gid}: angiv 'ia' (udløsestrøm fra fabrikantens kurve) for kurve {curve}")
        ik = ik_min(g["tvaersnit"], length, rating, curve, ik_min_net, None, g.get("ia"), temp, f_size, f_len,
                    f_temp, ins)
        if not ik["ok"]:
            add(gid, "advarsel", f"Ik,min {fmt(ik['ik_min'], 0)} A < Ia {fmt(ik['ia'], 0)} A – ingen momentan "
                f"udkobling; maks. længde {fmt(ik['maks_laengde'])} m, ellers vis med tid-strøm-kurven at sikringen "
                f"bryder inden {fmt(ik['maks_tid_s'])} s (kablets grænse)", "411")
        icn = g.get("icn", 6000)
        if icn < ik_max and backup < ik_max:
            add(gid, "vejledende", f"brydeevne {fmt(icn / 1000)} kA < Ik,max ved tavlen {fmt(ik_max / 1000)} kA – "
                "dokumentér back-up med forsikringen efter fabrikantens tabel (tavle.backup_ka)", "434")
        # RCD per group
        chain = rcd_chain(rcds, g.get("rcd")) if g.get("rcd") else []
        if not chain:
            add(gid, "advarsel", "gruppen har ingen RCD", "35")
        elif not any(r.get("ma", 999) <= 30 for r in chain):
            add(gid, "advarsel", f"gruppen sidder kun bag {chain[0]['id']} {fmt(chain[0].get('ma', 0), 0)} mA – "
                "endelige kredse skal have RCD ≤ 30 mA", "35")
        use = str(g.get("anvendelse", "")).lower()
        if use == "stik" or g.get("stikkontakt_a"):
            socket = g.get("stikkontakt_a") or SOCKET_DEFAULT_A
            max_fuse = SOCKET_MAX_FUSE.get(int(socket)) if float(socket).is_integer() else None
            if max_fuse is None:
                raise InputError(f"gruppe {gid}: stikkontakt_a skal være 10, 13 eller 16 (A)")
            if rating > max_fuse:
                assumed = "" if g.get("stikkontakt_a") else " (antaget – angiv stikkontakt_a, hvis de er 16 A)"
                add(gid, "advarsel", f"{curve}{fmt(rating, 0)} foran {fmt(socket, 0)} A-stikkontakter{assumed} – "
                    f"højst {max_fuse} A kortslutningsbeskyttelse", "45")
        if use == "elbil" and chain:
            if not any(is_type_b(r.get("type")) for r in chain) and not g.get("rdc_dd"):
                add(gid, "advarsel", "elbillader uden type B og uden RDC-DD (6 mA DC-detektering)", "722")
            shared = [o.get("nr") for o in groups if o is not g and o.get("rcd") == g.get("rcd")]
            if shared:
                add(gid, "advarsel", f"elbilladerens RCD deles med gruppe {', '.join(map(str, shared))} – hvert "
                    "tilslutningspunkt skal have sin egen RCD", "722")
        if use in ("varmepumpe", "frekvensomformer") and chain and not any(
                is_type_b(r.get("type")) or str(r.get("type")).upper() == "F" for r in chain):
            add(gid, "vejledende", "frekvensomformer: 1-faset → type F, 3-faset → type B, medmindre fabrikanten "
                "angiver andet", "erf")
        if g.get("led_spots"):
            led_max = g.get("led_maks") or (LED_PER_B16 * rating / 16 * (2 if curve == "C" else 1)
                                            if curve in ("B", "C") else None)
            if led_max and g["led_spots"] > led_max:
                add(gid, "vejledende", f"{g['led_spots']} LED-spots på {curve}{fmt(rating, 0)} – indkoblingsstrømmen "
                    f"kan udløse automatsikringen (ca. {fmt(led_max, 0)}); driverens datablad afgør", "erf")
        for ph in ("L1", "L2", "L3"):
            if three or ph in phases_txt:
                phase_load[ph] += g.get("last") or 0.0
        sev = {f["alvor"] for f in findings[before:]}
        status = "advarsel" if "advarsel" in sev else ("vejledende" if "vejledende" in sev else "OK")
        rcd_txt = " → ".join(f"{r['id']} {r.get('type', '?')}/{fmt(r.get('ma', 0), 0)}" for r in chain) or "–"
        rows.append({
            "gruppe": f"{gid} {g.get('navn', '')}".strip(), "sikring": f"{curve}{fmt(rating, 0)} ({fmt(icn / 1000)} kA)",
            "fase": phases_txt, "kabel": f"{g.get('kabel', '')} {fmt(g['tvaersnit'])} mm² {'+'.join(methods)}"
            + (f" + isol. {fmt(g.get('isoleret_mm'), 0)} mm" if g.get("isoleret_mm") else "")
            + f" · Iz {fmt(cap['iz'])} A", "rcd": rcd_txt, "laengde": length, "du_pct": round(du + upstream, 2),
            "ik_min": ik["ik_min"], "ia": ik["ia"], "status": status})

    # Panel-wide checks
    if fuse and largest and fuse < SELECTIVITY_RATIO * largest:
        add("tavle", "vejledende", f"forsikring {fmt(fuse, 0)} A < {fmt(SELECTIVITY_RATIO)} × største gruppe "
            f"{fmt(largest, 0)} A – risiko for manglende selektivitet; fabrikantens tabel afgør", "erf")
    loads = [v for v in phase_load.values()]
    if any(loads):
        if fuse and max(loads) > fuse:
            add("tavle", "advarsel", f"belastning på mest belastede fase {fmt(max(loads))} A over forsikringen "
                f"{fmt(fuse, 0)} A (uden samtidighed)", "erf")
        if max(loads) - min(loads) > max(10.0, 0.3 * max(loads)):
            add("tavle", "vejledende", "ubalance mellem faserne over 30 % og 10 A – flyt grupper", "erf")
    else:
        add("tavle", "info", "faselast ikke beregnet – angiv 'last' (A) pr. gruppe", "erf")
    slots, used = panel.get("pladser"), panel.get("pladser_brugt")
    if slots and used is not None:
        spare = 1 - used / slots
        if spare < SPARE_MIN:
            add("tavle", "vejledende", f"reserveplads {fmt(spare * 100, 0)} % – under 20 % til senere udvidelse", "erf")
    return {"tavle": panel.get("navn", ""), "ik_min_net": round(ik_min_net), "ik_max_tavle": round(ik_max),
            "faselast": {k: round(v, 1) for k, v in phase_load.items()}, "grupper": rows, "fund": findings}


def panel_markdown(res, command):
    head = ("| Gruppe | Sikring/kurve | Fase | Kabel/tværsnit/metode | RCD (type/mA) | Længde | ΔU % | Ik,min | Status |\n"
            "|---|---|---|---|---|---|---|---|---|")
    lines = [f"Kommando: `{command}`", "",
             f"**{res['tavle']}** – Ik,min net {res['ik_min_net']} A · Ik,max ved tavlen {fmt(res['ik_max_tavle'] / 1000)}"
             f" kA · faselast L1/L2/L3 {' / '.join(fmt(v) for v in res['faselast'].values())} A", "", head]
    for r in res["grupper"]:
        lines.append(f"| {r['gruppe']} | {r['sikring']} | {r['fase']} | {r['kabel']} | {r['rcd']} | "
                     f"{fmt(r['laengde'])} m | {fmt(r['du_pct'], 2)} | {fmt(r['ik_min'], 0)} A (≥ {fmt(r['ia'], 0)}) | "
                     f"{r['status']} |")
    lines += ["", "| Gruppe | Alvor | Fund | Kilde |", "|---|---|---|---|"]
    lines += [f"| {f['gruppe']} | {f['alvor']} | {f['tekst']} | {f['kilde']} |" for f in res["fund"]] or [
        "| – | – | ingen fund | – |"]
    lines += ["", "Projekteringshjælp – den autoriserede elinstallatør verificerer (BEK 1082 § 75)."]
    return "\n".join(lines)


def cmd_panel(a):
    try:
        data = json.loads(pathlib.Path(a.file).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as e:
        raise InputError(f"kan ikke læse {a.file}: {e}")
    res = check_panel(data)
    if a.format == "json":
        output(res)
    else:
        path = shlex.quote(str(pathlib.Path(__file__).resolve()))
        print(panel_markdown(res, f"python3 {path} " + " ".join(shlex.quote(x) for x in sys.argv[1:])))


def cmd_template(_a):
    print(json.dumps(TEMPLATE, ensure_ascii=False, indent=2))


# --- Self-test ---------------------------------------------------------------------------------------------------

def selftest(_a=None):
    errors = []

    def expect(name, got, want, tol=0.01):
        if abs(got - want) > tol:
            errors.append(f"{name}: {got} ≠ {want}")

    for key, methods in IZ.items():
        for m, vals in methods.items():
            if len(vals) != len(SIZES) or list(vals) != sorted(vals):
                errors.append(f"IZ{key}[{m}] skal stige med tværsnittet")
    for loaded in (2, 3):
        for m in METHODS:
            if any(p >= x for p, x in zip(IZ[("pvc", loaded)][m], IZ[("xlpe", loaded)][m])):
                errors.append(f"PVC skal være under XLPE ({m}, {loaded} belastede)")
            if any(t > d for t, d in zip(IZ[("pvc", 3)][m], IZ[("pvc", 2)][m])):
                errors.append(f"3 belastede skal være ≤ 2 belastede ({m})")
    # Table B.52.14 (air): PVC 40 °C 0,87 · 25 °C 1,06; XLPE 40 °C 0,91 · 50 °C 0,82
    expect("Ca PVC 40", round(ambient_factor("pvc", 40), 2), 0.87)
    expect("Ca PVC 25", round(ambient_factor("pvc", 25), 2), 1.06)
    expect("Ca XLPE 40", round(ambient_factor("xlpe", 40), 2), 0.91)
    expect("Ca XLPE 50", round(ambient_factor("xlpe", 50), 2), 0.82)
    expect("Ci 100 mm", insulated_factor(100), 0.78)
    expect("Ci 600 mm", insulated_factor(600), 0.50)
    expect("Ci 150 mm", insulated_factor(150), 0.705)
    expect("Cg 4", grouping_factor(4), 0.65)
    # Worst segment governs: 2,5 mm² PVC B2 23 A, C through 100 mm insulation 27·0,78 = 21,06 A
    expect("Iz rute", capacity(2.5, ["B2", "C"], "pvc", 2, 100)["iz"], 21.1, 0.05)
    expect("I2 gG 16", conventional_factor("gG", 16), 1.6)
    # Hand calculation: 2,5 mm², 25 m, 10 A, 1-phase, 70 °C: 2·25·10·7,41e-3·(1+0,00393·50)/230 = 1,927 %
    expect("ΔU", voltage_drop(2.5, 25, 10)[0], 1.927, 0.002)
    # 3-phase, cos φ 1: √3·L·I·r/400
    expect("ΔU 3f", voltage_drop(6, 40, 16, 3)[0], math.sqrt(3) * 40 * 16 * r_per_m(6, 70) / 400 * 100, 1e-6)
    # Ik,min: 175 A network (5 × 35 A), B16, 2,5 mm² 30 m at 70 °C → 230/(1,3143 + 0,532) = 124,7 A; Lmax 88,0 m
    r = ik_min(2.5, 30, 16, "B", service_fuse=35)
    expect("Ik,min", r["ik_min"], 124.7, 0.2)
    expect("Lmax Ik", r["maks_laengde"], 88.0, 0.2)
    if not r["ok"]:
        errors.append("Ik,min-kontrol: 124,7 A ≥ 80 A skal være OK")
    expect("Ik,max uden stikledning", ik_max_panel(), 16000, 1)
    if ik_max_panel(16000, 16, 15) >= 16000:
        errors.append("stikledningen skal sænke Ik,max")
    res = check_panel(TEMPLATE)
    if any(f["alvor"] == "advarsel" for f in res["fund"]):
        errors.append(f"skabelonen skal være uden advarsler: {res['fund']}")
    bad = json.loads(json.dumps(TEMPLATE))
    bad["rcd"][2]["foran"] = "RCD1"
    bad["grupper"][0]["sikring"] = 20
    bad["grupper"][1]["sikring"] = 16
    texts = " ".join(f["tekst"] for f in check_panel(bad)["fund"])
    for want in ("blinde", "beskytter ikke kablet", "A-stikkontakter"):
        if want not in texts:
            errors.append(f"tavlekontrol fandt ikke '{want}'")
    print("Selvtest OK" if not errors else "Selvtest: " + str(len(errors)) + " fejl\n" + "\n".join(errors))
    return 1 if errors else 0


def main():
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0], formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)

    def cable_args(s):
        s.add_argument("--size", type=float, required=True, help="tværsnit mm²")
        s.add_argument("--insulation", choices=("pvc", "xlpe"), default="pvc",
                       help="pvc (70 °C) eller xlpe (90 °C) – se calc-tools.md for kabeltyper")

    s = sub.add_parser("iz", help="Strømværdi Iz pr. rute (værste del afgør) og kontrol Ib ≤ In ≤ Iz")
    cable_args(s)
    s.add_argument("--method", action="append", choices=METHODS, required=True, help="installationsmetode; gentag pr. del af ruten")
    s.add_argument("--loaded", type=int, choices=(2, 3), default=2, help="belastede ledere (1-faset 2, 3-faset 3)")
    s.add_argument("--insulated-mm", type=float, default=0.0, help="længde helt omgivet af varmeisolering (mm)")
    s.add_argument("--ambient", type=float, default=30.0, help="omgivelsestemperatur °C")
    s.add_argument("--grouped", type=int, default=1, help="antal samlet fremførte kredse")
    s.add_argument("--cg", type=float, help="korrektionsfaktor for samlet fremføring (overstyrer --grouped)")
    s.add_argument("--rating", type=float, help="sikringens mærkestrøm In (A)")
    s.add_argument("--device", choices=("mcb", "gG"), default="mcb", help="automatsikring eller smeltesikring")
    s.add_argument("--ib", type=float, help="belastningsstrøm Ib (A)")
    s.set_defaults(fn=cmd_iz)

    s = sub.add_parser("vdrop", help="Spændingsfald og maks. længde (også for næste tværsnit)")
    cable_args(s)
    s.add_argument("--length", type=float, required=True, help="kabellængde m (enkelt vej)")
    s.add_argument("--current", type=float, required=True, help="strøm A (Ib, ellers In)")
    s.add_argument("--phases", type=int, choices=(1, 3), default=1)
    s.add_argument("--cosphi", type=float, default=1.0)
    s.add_argument("--temp", type=float, help="ledertemperatur °C (standard: isoleringens maks.)")
    s.add_argument("--limit", type=float, help=f"grænse i %% (standard {VDROP_LIMIT} – DS/HD 60364-5-52 pkt. 525)")
    s.add_argument("--upstream", type=float, default=0.0, help="spændingsfald foran tavlen i %%")
    s.set_defaults(fn=cmd_vdrop)

    s = sub.add_parser("ikmin", help="Mindste kortslutningsstrøm i kredsens ende og maks. længde")
    cable_args(s)
    s.add_argument("--length", type=float, required=True)
    s.add_argument("--rating", type=float, required=True, help="sikringens mærkestrøm In (A)")
    s.add_argument("--curve", choices=("B", "C", "D", "gG"), required=True)
    s.add_argument("--ia", type=float, help="udløsestrøm (A) – kræves for gG")
    s.add_argument("--ik-net", type=float, help="Ik,min ved tavlen/tilslutningen (A) fra netselskab eller måling")
    s.add_argument("--service-fuse", type=float, help="stikledningssikring (A) → Ik,min = 5 × In (Fællesregulativet)")
    s.add_argument("--feeder-size", type=float, help="stikledning/hovedledning mm² (lægges til, hvis Ik gælder foran den)")
    s.add_argument("--feeder-length", type=float, default=0.0)
    s.add_argument("--feeder-insulation", choices=("pvc", "xlpe"), default="xlpe",
                   help="stikledningens isolering: pvc (70 °C) eller xlpe (90 °C, standard)")
    s.add_argument("--temp", type=float, help="ledertemperatur °C (standard: isoleringens maks.)")
    s.set_defaults(fn=cmd_ikmin)

    s = sub.add_parser("ikmax", help="Største kortslutningsstrøm ved tavlen mod brydeevne")
    s.add_argument("--icn", type=float, required=True, help="automatsikringens brydeevne (A), fx 6000 eller 10000")
    s.add_argument("--ik-net", type=float, default=IK_MAX_NET, help="Ik,max foran stikledningen (A)")
    s.add_argument("--feeder-size", type=float)
    s.add_argument("--feeder-length", type=float, default=0.0)
    s.set_defaults(fn=cmd_ikmax)

    s = sub.add_parser("panel", help="Fast gruppeskema med fund for en tavle (JSON-fil)")
    s.add_argument("file")
    s.add_argument("--format", choices=("md", "json"), default="md")
    s.set_defaults(fn=cmd_panel)

    sub.add_parser("template", help="Eksempel på tavlefil").set_defaults(fn=cmd_template)
    sub.add_parser("test", help="Selvtest").set_defaults(fn=selftest)

    a = p.parse_args()
    try:
        return a.fn(a) or 0
    except (InputError, KeyError) as e:
        sys.exit(f"Fejl: {e}")


if __name__ == "__main__":
    sys.exit(main())
