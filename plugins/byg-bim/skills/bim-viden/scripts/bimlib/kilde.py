"""Kildegrundlag: rasterisering af PDF-tegninger, pixelgitter til aflæsning og målestok fra kendte mål.

Princip: modellen LÆSER påskrevne mål (tal) – den måler ikke i billedet, når et påskrevet mål findes.
Skalaen bestemmes af lange, kendte mål, X og Y hver for sig (scannere og papir er sjældent 1:1).
"""
import math
import pathlib

MAX_PX = 2400


def _sider(spec, n):
    if not spec:
        return list(range(1, n + 1))
    ud = []
    for led in spec.split(","):
        if "-" in led:
            a, b = led.split("-")
            ud += list(range(int(a), int(b) + 1))
        else:
            ud.append(int(led))
    return [s for s in ud if 1 <= s <= n]


def oversigt(doc, sti, ud, kolonner=8, bredde=260):
    """Kontaktark med alle sider som små billeder og sidenumre – find tegningssiderne, før der rasteriseres."""
    from PIL import Image, ImageDraw
    import pymupdf
    thumbs = []
    for i, side in enumerate(doc):
        z = bredde / side.rect.width
        pix = side.get_pixmap(matrix=pymupdf.Matrix(z, z))
        thumbs.append(Image.frombytes("RGB", (pix.width, pix.height), pix.samples))
    h = max(t.height for t in thumbs) + 22
    raekker = (len(thumbs) + kolonner - 1) // kolonner
    ark = Image.new("RGB", (kolonner * (bredde + 8), raekker * h), "white")
    d = ImageDraw.Draw(ark)
    for i, t in enumerate(thumbs):
        x, y = (i % kolonner) * (bredde + 8), (i // kolonner) * h
        ark.paste(t, (x, y + 20))
        d.text((x + 4, y + 3), f"s. {i + 1}  {'liggende' if t.width > t.height else ''}", fill=(200, 0, 0))
    fil = ud / f"{sti.stem}-oversigt.png"
    if max(ark.size) > MAX_PX * 2:
        ark.thumbnail((MAX_PX * 2, MAX_PX * 2))
    ark.save(fil)
    print(f"{fil}  {len(thumbs)} sider – vælg tegningssider og kør: bim.py pdf {sti} --sider <n,…> --dpi 200")
    return 0


def pdf(sti: pathlib.Path, sider, dpi, ud, vis_oversigt=False) -> int:
    import pymupdf
    doc = pymupdf.open(str(sti))
    ud = pathlib.Path(ud) if ud else sti.parent / "png"
    ud.mkdir(parents=True, exist_ok=True)
    if vis_oversigt:
        return oversigt(doc, sti, ud)
    for s in _sider(sider, doc.page_count):
        side = doc[s - 1]
        scan = ""
        try:
            info = side.get_image_info()
            if info:
                st = max(info, key=lambda i: i["width"] * i["height"])
                bb = st["bbox"]
                ppi = st["width"] / ((bb[2] - bb[0]) / 72) if bb[2] > bb[0] else 0
                scan = f" · scanning ca. {ppi:.0f} ppi"
                if dpi > ppi * 1.1 and ppi > 0:
                    scan += f" (dpi over {ppi:.0f} tilføjer ingen detaljer)"
        except Exception:
            pass
        pix = side.get_pixmap(dpi=dpi)
        fil = ud / f"{sti.stem}-s{s}.png"
        pix.save(str(fil))
        w_mm, h_mm = side.rect.width / 72 * 25.4, side.rect.height / 72 * 25.4
        print(f"{fil}  {pix.width}×{pix.height} px · side {w_mm:.0f}×{h_mm:.0f} mm · {dpi} dpi{scan}")
        if max(pix.width, pix.height) > MAX_PX:
            print(f"  for stort til at læse i ét billede – brug: bim.py gitter {fil} --beskaer x0,y0,x1,y1")
    return 0


def gitter(sti: pathlib.Path, trin, beskaer, zoom, ud) -> int:
    from PIL import Image, ImageDraw, ImageFont
    img = Image.open(sti).convert("RGB")
    x0, y0 = 0, 0
    if beskaer:
        x0, y0, x1, y1 = map(int, beskaer.split(","))
        img = img.crop((x0, y0, x1, y1))
    z = zoom
    if max(img.size) * z > MAX_PX:
        z = MAX_PX / max(img.size)
    if abs(z - 1) > 1e-6:
        img = img.resize((int(img.width * z), int(img.height * z)), Image.LANCZOS)
    d = ImageDraw.Draw(img, "RGBA")
    try:
        font = ImageFont.load_default(size=max(11, int(12 * max(1.0, z))))
    except TypeError:
        font = ImageFont.load_default()
    # linjer i ORIGINALE pixelkoordinater, så aflæsninger kan bruges direkte i --kal og skala
    start_x = (x0 // trin + 1) * trin
    start_y = (y0 // trin + 1) * trin
    for gx in range(start_x, x0 + int(img.width / z) + 1, trin):
        px = (gx - x0) * z
        d.line([(px, 0), (px, img.height)], fill=(255, 0, 0, 90), width=1)
        d.text((px + 2, 2), str(gx), fill=(200, 0, 0, 255), font=font)
    for gy in range(start_y, y0 + int(img.height / z) + 1, trin):
        py = (gy - y0) * z
        d.line([(0, py), (img.width, py)], fill=(0, 0, 255, 90), width=1)
        d.text((2, py + 2), str(gy), fill=(0, 0, 200, 255), font=font)
    navn = sti.stem + "-gitter" + (f"-{beskaer.replace(',', '-')}" if beskaer else "") + ".png"
    if ud and str(ud).lower().endswith(".png"):
        fil = pathlib.Path(ud)
        fil.parent.mkdir(parents=True, exist_ok=True)
    else:
        mappe = pathlib.Path(ud) if ud else sti.parent
        mappe.mkdir(parents=True, exist_ok=True)
        fil = mappe / navn
    img.save(fil)
    print(f"{fil}  {img.width}×{img.height} px · gitter hver {trin} px (originale koordinater) · zoom {z:.2f}")
    return 0


def linjer(sti: pathlib.Path, beskaer, andel=0.5, graense=128) -> int:
    """Præcise pixelpositioner af lodrette og vandrette streger i et udsnit (projektionsprofil).
    Bruges til kalibreringspunkter og hjælpelinjers fod: en streg, der dækker mindst `andel` af udsnittets
    højde (lodret) eller bredde (vandret), rapporteres med midte og bredde i originale koordinater."""
    import numpy as np
    from PIL import Image
    img = Image.open(sti).convert("L")
    x0, y0 = 0, 0
    if beskaer:
        x0, y0, x1, y1 = map(int, beskaer.split(","))
        img = img.crop((x0, y0, x1, y1))
    a = np.asarray(img) < graense
    h, w = a.shape

    def grupper(profil, n, off):
        idx = np.where(profil >= andel * n)[0]
        ud, start = [], None
        for i, j in zip(idx, list(idx[1:]) + [None]):
            start = i if start is None else start
            if j is None or j != i + 1:
                ud.append(((start + i) / 2 + off, i - start + 1, float(profil[start:i + 1].max()) / n))
                start = None
        return ud

    lod = grupper(a.sum(axis=0), h, x0)
    vand = grupper(a.sum(axis=1), w, y0)
    print(f"{sti.name} udsnit {beskaer or 'hele'} ({w}×{h} px), streger der dækker ≥ {andel:.0%}:")
    print("  lodrette (x): " + (", ".join(f"{x:.1f} ({b} px, {d:.0%})" for x, b, d in lod) or "ingen"))
    print("  vandrette (y): " + (", ".join(f"{y:.1f} ({b} px, {d:.0%})" for y, b, d in vand) or "ingen"))
    if not lod and not vand:
        print("  tip: gør udsnittet smallere omkring stregen, eller sænk --andel")
    return 0


def _par(tekst, med_maal=True):
    ud = []
    for led in (tekst or "").split(";"):
        led = led.strip()
        if not led:
            continue
        if med_maal:
            a, b = led.split("=")
            ud.append((tuple(map(float, a.split(","))), float(b)))
        else:
            ud.append(tuple(map(float, led.split(","))))
    return ud


def skala(kal, maal) -> int:
    """--kal "x1,y1,x2,y2=mm;…": kendte mål i billedet. Med mål i forskellige retninger bestemmes X- og Y-skala hver
    for sig (mm² = (sx·dx)² + (sy·dy)²)."""
    import numpy as np
    k = _par(kal)
    if not k:
        print("--kal mangler: \"x1,y1,x2,y2=mm;…\"")
        return 1
    rows, rhs = [], []
    for (x1, y1, x2, y2), mm in k:
        dx, dy = x2 - x1, y2 - y1
        L = math.hypot(dx, dy)
        print(f"  kendt mål {mm:.0f} mm = {L:.1f} px → {mm / L:.3f} mm/px (retning {math.degrees(math.atan2(dy, dx)):.0f}°)")
        rows.append([dx * dx, dy * dy])
        rhs.append(mm * mm)
    A, b = np.array(rows), np.array(rhs)
    if len(k) >= 2 and np.linalg.cond(A) < 50:  # mål i mindst to retninger
        (sx2, sy2), *_ = np.linalg.lstsq(A, b, rcond=None)
        sx, sy = math.sqrt(max(sx2, 1e-12)), math.sqrt(max(sy2, 1e-12))
        print(f"Skala: X {sx:.4f} mm/px · Y {sy:.4f} mm/px (forskel {100 * (sy - sx) / sx:+.1f} %)")
    else:
        s = float(np.median([mm / math.hypot(x2 - x1, y2 - y1) for (x1, y1, x2, y2), mm in k]))
        sx = sy = s
        print(f"Skala: {s:.4f} mm/px (samme i X og Y – giv også et kendt mål på tværs for at tjekke)")
    for (x1, y1, x2, y2), mm in k:
        est = math.hypot((x2 - x1) * sx, (y2 - y1) * sy)
        print(f"  kontrol: {mm:.0f} mm → beregnet {est:.0f} mm ({est - mm:+.0f})")
    for x1, y1, x2, y2 in _par(maal, med_maal=False):
        print(f"  mål ({x1:.0f},{y1:.0f})→({x2:.0f},{y2:.0f}): {math.hypot((x2 - x1) * sx, (y2 - y1) * sy):.0f} mm")
    return 0
