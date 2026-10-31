#!/usr/bin/env python3
"""Single-line panel diagram (SVG) from a panel file in el.py's format (Python standard library only).

Draws the supply chain (service cable box with its fuses, service cable, meter, main switch, SPD) and the panel's
RCDs with their groups: per group the breaker and curve, breaking capacity, phase, cable and cross-section, length
and voltage drop, RCD type and mA, and what the group supplies. Lengths, voltage drop and findings come from
el.py's check_panel, so the diagram and `el.py panel` always agree. Symbols after EN 60617 (simplified); see
references/schematic.md.

Usage:  diagram.py <panel.json> [--out <file.svg>] [--title …] [--basis …] [--date YYYY-MM-DD] [--rev A]
        (the panel file comes from `bim.py panel <model.yaml> --out panel.json` or is written by hand from
        `el.py template`)
"""
import argparse
import json
import pathlib
import sys
import textwrap
from xml.sax.saxutils import escape

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from el import InputError, check_panel, fmt  # noqa: E402

INK, MUTED, RED, GREEN, AMBER = "#1d2330", "#5b6474", "#b42318", "#1a7f37", "#9a6700"
PHASE_COLOUR = {"L1": "#7a4a1e", "L2": "#1d2330", "L3": "#8a8f98"}  # brown, black, grey (DS/EN 60445)
SEVERITY_COLOUR = {"advarsel": RED, "vejledende": AMBER, "info": MUTED, "OK": GREEN}
ART = {  # art -> (singular, plural) for the "supplies" text
    "lampe": ("lampe", "lamper"), "afbryder": ("afbryder", "afbrydere"), "dimmer": ("lysdæmper", "lysdæmpere"),
    "stikkontakt": ("stikkontakt", "stikkontakter"), "komfur": ("komfur", "komfurer"),
    "opvaskemaskine": ("opvaskemaskine", "opvaskemaskiner"), "vaskemaskine": ("vaskemaskine", "vaskemaskiner"),
    "toerretumbler": ("tørretumbler", "tørretumblere"), "koeleskab": ("køleskab", "køleskabe"),
    "elbillader": ("elbillader", "elbilladere"), "varmepumpe": ("varmepumpe", "varmepumper"),
}

COL = 132       # px per group column
GAP = 26        # px between RCD blocks
LEFT = 330      # px reserved left of the first RCD block (supply chain, SPD)
X0 = 150        # x of the supply chain
BUS = 430       # y of the main busbar
SUB = 540       # y of the RCD busbars
MCB = 580       # y of the breakers
FRAME_BOTTOM = 630
TEXT_TOP = 668

DEFS = f"""<defs>
  <!-- symbols centred on (0,0) for a vertical conductor; a white mask hides the conductor behind the symbol -->
  <g id="sikring"><rect x="-6" y="-13" width="12" height="26" fill="#fff" stroke="{INK}" stroke-width="1.4"/><path d="M0,-13 V13" stroke="{INK}" stroke-width="1.2"/></g>
  <g id="automat"><rect x="-12" y="-11" width="24" height="22" fill="#fff"/><path d="M0,11 L-10,-8 M-4,-15 L4,-7 M4,-15 L-4,-7" fill="none" stroke="{INK}" stroke-width="1.5"/></g>
  <g id="rcd"><use href="#automat"/><ellipse cy="20" rx="11" ry="4.5" fill="none" stroke="{INK}" stroke-width="1.3"/><path d="M-11,20 L-7,1" fill="none" stroke="{INK}" stroke-width="1.1" stroke-dasharray="3 2"/></g>
  <g id="hovedafbryder"><rect x="-12" y="-11" width="24" height="22" fill="#fff"/><path d="M0,11 L-10,-8 M-5,-11 H5" fill="none" stroke="{INK}" stroke-width="1.5"/><circle cy="-11" r="2.2" fill="#fff" stroke="{INK}" stroke-width="1.2"/></g>
  <g id="maaler"><rect x="-22" y="-15" width="44" height="30" fill="#fff" stroke="{INK}" stroke-width="1.4"/><text y="4.5" text-anchor="middle" font-size="12" font-weight="700">kWh</text></g>
  <g id="spd"><rect x="-8" y="-15" width="16" height="30" fill="#fff" stroke="{INK}" stroke-width="1.4"/><path d="M-11,11 L8,-9 H12" fill="none" stroke="{INK}" stroke-width="1.3"/></g>
  <g id="jord"><path d="M0,0 V8 M-11,8 H11 M-7,12.5 H7 M-3,17 H3" fill="none" stroke="{INK}" stroke-width="1.5"/></g>
  <g id="udtag"><circle r="4" fill="#fff" stroke="{INK}" stroke-width="1.4"/></g>
  <g id="leder"><path d="M-5,4 L5,-4" stroke="{INK}" stroke-width="1.3"/></g>
</defs>"""


def _t(x, y, s, size=12, weight=None, anchor=None, colour=None, italic=False):
    attrs = f'x="{x:g}" y="{y:g}"'
    if size != 12:
        attrs += f' font-size="{size}"'
    if weight:
        attrs += f' font-weight="{weight}"'
    if anchor:
        attrs += f' text-anchor="{anchor}"'
    if colour:
        attrs += f' fill="{colour}"'
    if italic:
        attrs += ' font-style="italic"'
    return f"<text {attrs}>{escape(str(s))}</text>"


def _ticks(x, y, n):
    """n short slashes across a vertical conductor: the number of phase conductors in single-line notation."""
    return "".join(f'<use href="#leder" x="{x:g}" y="{y + 7 * i - 7 * (n - 1) / 2:g}"/>' for i in range(n))


def num(x, nd=1):
    """fmt() without a trailing ,0 on whole numbers (16 → 16, 1.5 → 1,5)."""
    return fmt(float(x), nd) if x is not None else "?"


def cable_text(c):
    """NOIKLX 3G1,5 from kabel/ledere/tvaersnit; without ledere: NOIKLX 1,5 mm²."""
    if not c:
        return ""
    size = num(c.get("tvaersnit"))
    if c.get("ledere"):
        return f"{c.get('kabel', '')} {c['ledere']}G{size}".strip()
    return f"{c.get('kabel', '')} {size} mm²".strip()


def supplies(g):
    parts = []
    for art, n in (g.get("forsyner") or {}).items():
        one, many = ART.get(art, (art, art))
        parts.append(f"{n} {one if n == 1 else many}")
    return ", ".join(parts)


def phases(g):
    p = str(g.get("fase", "L1")).upper().replace(" ", "")
    return ["L1", "L2", "L3"] if p in ("L1L2L3", "3", "3F") else [x for x in ("L1", "L2", "L3") if x in p] or ["L1"]


def rcd_text(rid, rcds):
    r = next((x for x in rcds if x["id"] == rid), None)
    if not r:
        return "uden RCD", RED
    return f"{rid} · type {r.get('type', '?')} · {num(r.get('ma'), 0)} mA", INK


def render(data, res, title="Tavlediagram", basis="tavlefil (el.py-format)", date=None, rev="A"):
    tavle = data.get("tavle", {})
    rcds = data.get("rcd", [])
    groups = data["grupper"]
    rows = {str(g.get("nr", "?")): r for g, r in zip(groups, res["grupper"])}
    by_rcd = {}
    for g in groups:
        by_rcd.setdefault(g.get("rcd"), []).append(g)
    blocks = [(r, sorted(by_rcd[r["id"]], key=lambda g: g.get("nr", 0))) for r in rcds if r["id"] in by_rcd]
    if None in by_rcd:
        blocks.append((None, by_rcd[None]))
    x_start = LEFT + 30
    width = int(x_start + sum(len(gs) for _, gs in blocks) * COL + GAP * (len(blocks) - 1) + 120)
    width = max(width, 1200)
    findings = [f for f in res["fund"] if f["alvor"] != "info"]
    summary_y = TEXT_TOP + 236
    height = summary_y + 18 * (min(len(findings), 8) + (len(findings) > 8)) + 180
    o = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" width="{width}" height="{height}" '
         f'font-family="system-ui, Helvetica, Arial, sans-serif" font-size="12" fill="{INK}">',
         f"<title>{escape(title)}</title>",
         "<desc>Enstregsdiagram for tavlen: forsyning, måler, hovedafbryder, SPD, fejlstrømsafbrydere og grupper. "
         "Ikke målfast. Symboler efter electrical-knowledge/references/schematic.md.</desc>", DEFS,
         f'<rect width="{width}" height="{height}" fill="#fff"/>',
         _t(40, 34, title, 20, "700"),
         _t(40, 54, f"Enstregsdiagram · {tavle.get('system', '?')}-system 3 × 400/230 V · ikke målfast · ID'er som i "
            "BIM-modellen", colour=MUTED)]

    # supply: service cable box with its fuses
    box = tavle.get("kabelskab") or {}
    fuse = next((u for u in box.get("udstyr", []) if u.get("art") == "sikring"), None)
    fuse_txt = (f"{fuse.get('poler', 3)} × {fmt(fuse.get('in'), 0)} A {fuse.get('kurve', 'gG')}" if fuse
                else f"{fmt(tavle.get('forsikring'), 0)} A")
    o.append(f'<path d="M{X0},76 V{BUS}" stroke="{INK}" stroke-width="2.2"/>')
    o.append(_t(X0 + 10, 84, "fra netselskabets net", 11, colour=MUTED))
    o.append(f'<rect x="40" y="96" width="300" height="92" fill="#f7f8fa" stroke="{INK}" stroke-width="1.2" '
             'stroke-dasharray="6 3"/>')
    o.append(_t(48, 112, box.get("id", "KABELSKAB"), 12, "700"))
    o.append(_t(48, 127, box.get("navn", "Kabelskab"), 11, colour=MUTED))
    o.append(f'<use href="#sikring" x="{X0}" y="158"/>{_ticks(X0 - 22, 158, 3)}')
    o.append(_t(X0 + 14, 152, (fuse or {}).get("id", "Forsikring"), 11, "700"))
    o.append(_t(X0 + 14, 166, f"Stikledningssikring {fuse_txt}", 11))
    feeder = tavle.get("stikledning") or {}
    o.append(_t(X0 + 14, 216, "Stikledning " + cable_text(feeder), 12, "700"))
    o.append(_t(X0 + 14, 231, " · ".join(x for x in [f"{num(feeder.get('laengde'))} m" if feeder.get("laengde")
                                                      else "", "i jord"] if x), 11, colour=MUTED))
    o.append(_ticks(X0, 222, 4))

    # panel frame
    frame_top = 250
    o.append(f'<rect x="30" y="{frame_top}" width="{width - 60}" height="{FRAME_BOTTOM - frame_top}" fill="none" '
             f'stroke="{INK}" stroke-width="1.4" stroke-dasharray="10 4"/>')
    spare = ""
    if tavle.get("pladser"):
        spare = f" · {tavle['pladser']} moduler, {tavle.get('pladser_brugt', '?')} brugt"
    o.append(_t(X0 + 14, frame_top + 18, f"{tavle.get('id', 'TAVLE')} {tavle.get('navn', '')}", 13, "700"))
    o.append(_t(X0 + 14, frame_top + 34, f"Forsikring {fmt(tavle.get('forsikring'), 0)} A{spare}", 11, colour=MUTED))
    kit = {u.get("art"): u for u in tavle.get("udstyr", [])}
    y = frame_top + 72
    meter = kit.get("elmaaler")
    o.append(f'<use href="#maaler" x="{X0}" y="{y}"/>')
    o.append(_t(X0 + 30, y - 2, (meter or {}).get("id", "Måler"), 11, "700"))
    o.append(_t(X0 + 30, y + 12, (meter or {}).get("navn", "Elmåler"), 11))
    y += 64
    ha = kit.get("hovedafbryder")
    o.append(f'<use href="#hovedafbryder" x="{X0}" y="{y}"/>')
    o.append(_t(X0 + 18, y - 2, (ha or {}).get("id", "HA"), 11, "700"))
    o.append(_t(X0 + 18, y + 12, (ha or {}).get("navn", "Hovedafbryder"), 11))

    # main busbar, SPD
    last = x_start + sum(len(gs) for _, gs in blocks[:-1]) * COL + GAP * (len(blocks) - 1) + COL / 2
    o.append(f'<path d="M{X0},{BUS} H{last + 30}" stroke="{INK}" stroke-width="4"/>')
    o.append(f'<circle cx="{X0}" cy="{BUS}" r="4" fill="{INK}"/>')
    spd = kit.get("overspaendingsbeskyttelse")
    if spd:
        xs = 250
        o.append(f'<path d="M{xs},{BUS} V{BUS + 70}" stroke="{INK}" stroke-width="1.6"/>'
                 f'<circle cx="{xs}" cy="{BUS}" r="4" fill="{INK}"/>')
        o.append(f'<use href="#spd" x="{xs}" y="{BUS + 40}"/><use href="#jord" x="{xs}" y="{BUS + 70}"/>')
        o.append(_t(xs - 16, BUS + 36, spd.get("id", "SPD"), 11, "700", "end"))
        o.append(_t(xs - 16, BUS + 50, f"type {spd.get('type', '?')}", 11, anchor="end"))
    o.append(_t(X0 - 10, BUS - 8, "L1 L2 L3 N", 11, anchor="end", colour=MUTED))
    o.append(_t(X0 - 6, BUS + 92, "PE/jord: TT – eget", 11, anchor="end", colour=MUTED))
    o.append(_t(X0 - 6, BUS + 106, "jordspyd", 11, anchor="end", colour=MUTED))

    # RCD blocks and groups
    x = x_start
    for r, gs in blocks:
        bw = len(gs) * COL
        if r:
            xr = x + COL / 2
            o.append(f'<path d="M{xr},{BUS} V{SUB}" stroke="{INK}" stroke-width="1.8"/>'
                     f'<circle cx="{xr}" cy="{BUS}" r="4" fill="{INK}"/>')
            o.append(f'<use href="#rcd" x="{xr}" y="{BUS + 42}"/>{_ticks(xr, BUS + 92, 3)}')
            typ = str(r.get("type", "?"))
            colour = RED if typ.upper() == "AC" else INK
            o.append(_t(xr + 18, BUS + 30, r["id"], 12, "700"))
            o.append(_t(xr + 18, BUS + 45, f"type {typ} · {fmt(r.get('ma'), 0)} mA", 12, "700", colour=colour))
            o.append(_t(xr + 18, BUS + 60, f"{fmt(r.get('in'), 0)} A · {r.get('poler', 4)}-polet", 11, colour=MUTED))
        else:
            o.append(f'<path d="M{x + COL / 2},{BUS} V{SUB}" stroke="{RED}" stroke-width="1.8"/>')
            o.append(_t(x + COL / 2 + 10, BUS + 45, "uden RCD", 12, "700", colour=RED))
        if len(gs) > 1:
            o.append(f'<path d="M{x + COL / 2},{SUB} H{x + bw - COL / 2}" stroke="{INK}" stroke-width="3"/>')
        for i, g in enumerate(gs):
            gx = x + COL * i + COL / 2
            row = rows.get(str(g.get("nr", "?")), {})
            ph = phases(g)
            o.append(f'<path d="M{gx},{SUB} V{FRAME_BOTTOM + 18}" stroke="{INK}" stroke-width="1.6"/>')
            if len(gs) > 1:
                o.append(f'<circle cx="{gx}" cy="{SUB}" r="3.5" fill="{INK}"/>')
            o.append(f'<use href="#automat" x="{gx}" y="{MCB}"/>{_ticks(gx, MCB + 34, len(ph))}')
            o.append(f'<use href="#udtag" x="{gx}" y="{FRAME_BOTTOM + 22}"/>')
            o.append(_t(gx + 14, MCB - 2, f"{g.get('kurve', 'B')}{fmt(g.get('sikring'), 0)}", 12, "700"))
            o.append(_t(gx + 14, MCB + 12, f"{fmt(g.get('icn', 6000) / 1000)} kA", 11, colour=MUTED))
            # text column below the panel
            tx, ty = gx - COL / 2 + 8, TEXT_TOP
            o.append(_t(tx, ty + 14, f"Gruppe {g.get('nr', '?')}", 13, "700"))
            bx = tx
            for p in ph:
                o.append(f'<rect x="{bx}" y="{ty + 22}" width="22" height="15" rx="3" fill="{PHASE_COLOUR[p]}"/>')
                o.append(_t(bx + 11, ty + 33.5, p, 10, "700", "middle", "#fff"))
                bx += 25
            lines = [(f"{g.get('kurve', 'B')}{fmt(g.get('sikring'), 0)} A · {fmt(g.get('icn', 6000) / 1000)} kA", INK),
                     (cable_text(g) + (f" · ref. {'+'.join(g['metode'])}" if isinstance(g.get('metode'), list) else ""),
                      INK),
                     (f"{num(row.get('laengde', g.get('laengde', 0)))} m · ΔU {fmt(row.get('du_pct', 0), 2)} %", INK),
                     rcd_text(g.get("rcd"), rcds)]
            ly = ty + 56
            for s, c in lines:
                o.append(_t(tx, ly, s, 11, colour=c))
                ly += 15
            ly += 6
            for s in textwrap.wrap(g.get("navn", ""), 19)[:3]:
                o.append(_t(tx, ly, s, 12, "700"))
                ly += 15
            for s in textwrap.wrap(supplies(g), 21)[:4]:
                o.append(_t(tx, ly, s, 11, colour=MUTED))
                ly += 14
            status = row.get("status", "?")
            o.append(_t(tx, TEXT_TOP + 196, status, 11, "700", colour=SEVERITY_COLOUR.get(status, INK)))
        x += bw + GAP

    # check summary and findings
    y = summary_y
    o.append(f'<path d="M40,{y - 18} H{width - 40}" stroke="#dde1e7"/>')
    loads = res["faselast"]
    count = {s: sum(1 for f in findings if f["alvor"] == s) for s in ("advarsel", "vejledende")}
    o.append(_t(40, y, f"el.py panel: Ik,min net {res['ik_min_net']} A · Ik,max ved tavlen "
                f"{fmt(res['ik_max_tavle'] / 1000)} kA · faselast L1/L2/L3 "
                f"{' / '.join(fmt(loads[k]) for k in ('L1', 'L2', 'L3'))} A (uden samtidighed) · "
                f"{count['advarsel']} advarsler, {count['vejledende']} vejledende", 12, "700"))
    for f in findings[:8]:
        y += 18
        o.append(_t(40, y, f"{f['alvor']} · {f['gruppe']}: {f['tekst']}"[:190], 11,
                    colour=SEVERITY_COLOUR.get(f["alvor"], INK)))
    if len(findings) > 8:
        y += 18
        o.append(_t(40, y, f"… {len(findings) - 8} fund mere – se el.py panel", 11, colour=MUTED))

    # legend and title block
    ly = height - 130
    o.append(f'<g transform="translate(40,{ly})">')
    o.append(_t(0, 0, "Signaturer (EN 60617, forenklet)", 12, "700"))
    items = [("sikring", "Sikring (gG)"), ("automat", "Automatsikring"), ("rcd", "Fejlstrømsafbryder (RCD)"),
             ("hovedafbryder", "Hovedafbryder"), ("maaler", "Elmåler"), ("spd", "Overspændingsbeskyttelse")]
    for i, (sym, label) in enumerate(items):
        cx, cy = 14 + (i // 3) * 230, 28 + (i % 3) * 30
        scale = ' transform="scale(.7)"' if sym in ("maaler", "rcd", "spd") else ""
        o.append(f'<g transform="translate({cx},{cy})"><g{scale}><use href="#{sym}"/></g></g>')
        o.append(_t(cx + 24, cy + 4, label, 11))
    o.append(f'<g transform="translate(474,28)">{_ticks(0, 0, 3)}</g>' + _t(498, 32, "Antal faseledere", 11))
    o.append('<g transform="translate(474,52)"><use href="#jord"/></g>' + _t(498, 64, "Jord", 11))
    o.append('<g transform="translate(474,88)"><use href="#udtag"/></g>' + _t(498, 92, "Gruppeafgang", 11))
    o.append("</g>")
    tb_x, tb_y = width - 500, height - 120
    o.append(f'<g transform="translate({tb_x},{tb_y})">')
    o.append(f'<rect width="460" height="90" fill="#fff" stroke="{INK}" stroke-width="1.4"/>'
             f'<path d="M0,30 H460 M270,30 V90" stroke="{INK}"/>')
    o.append(_t(10, 21, title, 14, "700"))
    o.append(_t(10, 50, f"Grundlag: {basis}", 11))
    o.append(_t(10, 66, "Ikke målfast · ikke til udførelse", 11))
    o.append(_t(10, 82, "Kabelføring i plan: se BIM-model", 11))
    o.append(_t(280, 50, "Udarbejdet: electrician", 11))
    o.append(_t(280, 66, "Status: projekteringshjælp", 11))
    o.append(_t(280, 82, f"Rev. {rev}" + (f" · {date}" if date else ""), 11))
    o.append("</g></svg>")
    return "\n".join(o) + "\n"


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("panel")
    ap.add_argument("--out")
    ap.add_argument("--title", default="Tavlediagram")
    ap.add_argument("--basis", default="tavlefil (el.py-format)")
    ap.add_argument("--date")
    ap.add_argument("--rev", default="A")
    a = ap.parse_args(argv)
    src = pathlib.Path(a.panel)
    try:
        data = json.loads(src.read_text(encoding="utf-8"))
        res = check_panel(data)
    except (OSError, json.JSONDecodeError, InputError, KeyError) as e:
        sys.exit(f"Fejl: {e}")
    out = pathlib.Path(a.out) if a.out else src.with_suffix(".svg")
    out.write_text(render(data, res, a.title, a.basis, a.date, a.rev), encoding="utf-8")
    n = {s: sum(1 for f in res["fund"] if f["alvor"] == s) for s in ("advarsel", "vejledende")}
    print(f"DIAGRAM {out}  ({len(data['grupper'])} grupper; {n['advarsel']} advarsler, {n['vejledende']} vejledende)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
