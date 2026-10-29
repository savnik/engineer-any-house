"""Source material: rasterising PDF drawings, pixel grid for reading off and scale from known dimensions.

Principle: the model READS written dimensions (numbers) – it does not measure in the image when a written one exists.
The scale is determined from long, known dimensions, X and Y separately (scanners and paper are rarely 1:1).
"""
import math
import pathlib

MAX_PX = 2400


def _pages(spec, n):
    if not spec:
        return list(range(1, n + 1))
    out = []
    for part in spec.split(","):
        if "-" in part:
            a, b = part.split("-")
            out += list(range(int(a), int(b) + 1))
        else:
            out.append(int(part))
    return [s for s in out if 1 <= s <= n]


def overview(doc, path, out, columns=8, width=260):
    """Contact sheet with all pages as thumbnails and page numbers – find the drawing pages before rasterising."""
    from PIL import Image, ImageDraw
    import pymupdf
    thumbs = []
    for i, page in enumerate(doc):
        z = width / page.rect.width
        pix = page.get_pixmap(matrix=pymupdf.Matrix(z, z))
        thumbs.append(Image.frombytes("RGB", (pix.width, pix.height), pix.samples))
    h = max(t.height for t in thumbs) + 22
    rows = (len(thumbs) + columns - 1) // columns
    sheet = Image.new("RGB", (columns * (width + 8), rows * h), "white")
    d = ImageDraw.Draw(sheet)
    for i, t in enumerate(thumbs):
        x, y = (i % columns) * (width + 8), (i // columns) * h
        sheet.paste(t, (x, y + 20))
        d.text((x + 4, y + 3), f"s. {i + 1}  {'liggende' if t.width > t.height else ''}", fill=(200, 0, 0))
    file = out / f"{path.stem}-oversigt.png"
    if max(sheet.size) > MAX_PX * 2:
        sheet.thumbnail((MAX_PX * 2, MAX_PX * 2))
    sheet.save(file)
    print(f"{file}  {len(thumbs)} sider – vælg tegningssider og kør: bim.py pdf {path} --pages <n,…> --dpi 200")
    return 0


def pdf(path: pathlib.Path, pages, dpi, out, show_overview=False) -> int:
    import pymupdf
    doc = pymupdf.open(str(path))
    out = pathlib.Path(out) if out else path.parent / "png"
    out.mkdir(parents=True, exist_ok=True)
    if show_overview:
        return overview(doc, path, out)
    for s in _pages(pages, doc.page_count):
        page = doc[s - 1]
        scan = ""
        try:
            info = page.get_image_info()
            if info:
                st = max(info, key=lambda i: i["width"] * i["height"])
                bb = st["bbox"]
                ppi = st["width"] / ((bb[2] - bb[0]) / 72) if bb[2] > bb[0] else 0
                scan = f" · scanning ca. {ppi:.0f} ppi"
                if dpi > ppi * 1.1 and ppi > 0:
                    scan += f" (dpi over {ppi:.0f} tilføjer ingen detaljer)"
        except Exception:
            pass
        pix = page.get_pixmap(dpi=dpi)
        file = out / f"{path.stem}-s{s}.png"
        pix.save(str(file))
        w_mm, h_mm = page.rect.width / 72 * 25.4, page.rect.height / 72 * 25.4
        print(f"{file}  {pix.width}×{pix.height} px · side {w_mm:.0f}×{h_mm:.0f} mm · {dpi} dpi{scan}")
        if max(pix.width, pix.height) > MAX_PX:
            print(f"  for stort til at læse i ét billede – brug: bim.py grid {file} --crop x0,y0,x1,y1")
    return 0


def grid(path: pathlib.Path, step, crop, zoom, out) -> int:
    from PIL import Image, ImageDraw, ImageFont
    img = Image.open(path).convert("RGB")
    x0, y0 = 0, 0
    if crop:
        x0, y0, x1, y1 = map(int, crop.split(","))
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
    # lines in ORIGINAL pixel coordinates, so readings can be used directly in --cal and scale
    start_x = (x0 // step + 1) * step
    start_y = (y0 // step + 1) * step
    for gx in range(start_x, x0 + int(img.width / z) + 1, step):
        px = (gx - x0) * z
        d.line([(px, 0), (px, img.height)], fill=(255, 0, 0, 90), width=1)
        d.text((px + 2, 2), str(gx), fill=(200, 0, 0, 255), font=font)
    for gy in range(start_y, y0 + int(img.height / z) + 1, step):
        py = (gy - y0) * z
        d.line([(0, py), (img.width, py)], fill=(0, 0, 255, 90), width=1)
        d.text((2, py + 2), str(gy), fill=(0, 0, 200, 255), font=font)
    name = path.stem + "-gitter" + (f"-{crop.replace(',', '-')}" if crop else "") + ".png"
    if out and str(out).lower().endswith(".png"):
        file = pathlib.Path(out)
        file.parent.mkdir(parents=True, exist_ok=True)
    else:
        out_dir = pathlib.Path(out) if out else path.parent
        out_dir.mkdir(parents=True, exist_ok=True)
        file = out_dir / name
    img.save(file)
    print(f"{file}  {img.width}×{img.height} px · gitter hver {step} px (originale koordinater) · zoom {z:.2f}")
    return 0


def lines(path: pathlib.Path, crop, fraction=0.5, threshold=128) -> int:
    """Precise pixel positions of vertical and horizontal strokes in a crop (projection profile).
    Used for calibration points and the foot of extension lines: a stroke covering at least `fraction` of the crop's
    height (vertical) or width (horizontal) is reported with centre and width in original coordinates."""
    import numpy as np
    from PIL import Image
    img = Image.open(path).convert("L")
    x0, y0 = 0, 0
    if crop:
        x0, y0, x1, y1 = map(int, crop.split(","))
        img = img.crop((x0, y0, x1, y1))
    a = np.asarray(img) < threshold
    h, w = a.shape

    def runs(profile, n, off):
        idx = np.where(profile >= fraction * n)[0]
        out, start = [], None
        for i, j in zip(idx, list(idx[1:]) + [None]):
            start = i if start is None else start
            if j is None or j != i + 1:
                out.append(((start + i) / 2 + off, i - start + 1, float(profile[start:i + 1].max()) / n))
                start = None
        return out

    vertical = runs(a.sum(axis=0), h, x0)
    horizontal = runs(a.sum(axis=1), w, y0)
    print(f"{path.name} udsnit {crop or 'hele'} ({w}×{h} px), streger der dækker ≥ {fraction:.0%}:")
    print("  lodrette (x): " + (", ".join(f"{x:.1f} ({b} px, {d:.0%})" for x, b, d in vertical) or "ingen"))
    print("  vandrette (y): " + (", ".join(f"{y:.1f} ({b} px, {d:.0%})" for y, b, d in horizontal) or "ingen"))
    if not vertical and not horizontal:
        print("  tip: gør udsnittet smallere omkring stregen, eller sænk --fraction")
    return 0


def _pairs(text, with_dim=True):
    out = []
    for part in (text or "").split(";"):
        part = part.strip()
        if not part:
            continue
        if with_dim:
            a, b = part.split("=")
            out.append((tuple(map(float, a.split(","))), float(b)))
        else:
            out.append(tuple(map(float, part.split(","))))
    return out


def scale(cal, dims) -> int:
    """--cal "x1,y1,x2,y2=mm;…": known dimensions in the image. With dimensions in different directions the X and Y scale
    are determined separately (mm² = (sx·dx)² + (sy·dy)²)."""
    import numpy as np
    k = _pairs(cal)
    if not k:
        print("--cal mangler: \"x1,y1,x2,y2=mm;…\"")
        return 1
    rows, rhs = [], []
    for (x1, y1, x2, y2), mm in k:
        dx, dy = x2 - x1, y2 - y1
        L = math.hypot(dx, dy)
        print(f"  kendt mål {mm:.0f} mm = {L:.1f} px → {mm / L:.3f} mm/px (retning {math.degrees(math.atan2(dy, dx)):.0f}°)")
        rows.append([dx * dx, dy * dy])
        rhs.append(mm * mm)
    A, b = np.array(rows), np.array(rhs)
    if len(k) >= 2 and np.linalg.cond(A) < 50:  # dimensions in at least two directions
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
    for x1, y1, x2, y2 in _pairs(dims, with_dim=False):
        print(f"  mål ({x1:.0f},{y1:.0f})→({x2:.0f},{y2:.0f}): {math.hypot((x2 - x1) * sx, (y2 - y1) * sy):.0f} mm")
    return 0
