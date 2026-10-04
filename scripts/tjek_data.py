#!/usr/bin/env python3
"""Dataseparation: sikrer, at konkrete sager, brugerdata og hemmeligheder ikke havner i plugin-repoet.

Brug:  python3 scripts/tjek_data.py        (kører også fra valider.py og git pre-commit-hooken)

Tjek:
  1. Struktur   – ingen sagsmapper (byg-sager/), sagsfiler, ejendomsrapporter, PDF'er eller kontroltilstand i repoet.
  2. Hemmeligheder – ingen API-nøgler: den lokale Datafordeler-nøgle og generiske nøglemønstre.
  3. Private termer – ingen sag-id'er fra den lokale videnbank og ingen termer fra ~/.config/byg-eksperter/private-termer.txt.
  4. Fingeraftryk – ingen tekstlinjer (≥ 60 tegn) kopieret fra de lokale sagsmapper.

De lokale kilder (videnbank, sagsmapper, nøgle, private termer) læses kun på udviklerens maskine og findes ikke i
repoet. Mangler de (fx i CI), springes tjek 3–4 over. Testdata (evals, testadresser, fixtures) er tilladt.
Værdier af hemmeligheder udskrives aldrig.
"""
import os
import pathlib
import re
import sys

ROD = pathlib.Path(os.environ.get("BYG_REPO_ROD") or pathlib.Path(__file__).resolve().parent.parent)
HJEM = pathlib.Path.home()
KONFIG = HJEM / ".config" / "byg-eksperter"
SPRING_OVER = {".git", "dist", "__pycache__", "results", "node_modules", ".DS_Store"}
TEKST = {".md", ".json", ".py", ".txt", ".yml", ".yaml", ".toml", ".sh", ".html", ".csv", ""}

# Filer, der kun hører hjemme i en sagsmappe eller pluginets datamappe
SAGSFILER = {"projektgrundlag.md", "beslutningslog.md", "kontrollog.md", "budget.md", "tidsplan.md", "risici.md",
             "graenseflader.md", "kontrolplan.md", "erfaringer.md", "status.md", "ejendomsdata.json",
             "ejendomsdata.md", "tilstand.json", "forankringskoe.md", "sager.md"}
SAGSMAPPER = {"byg-sager", "fagnotater", "kvalitet", "bilag", "videnbank", "ejendomme"}
NOEGLE_MOENSTRE = [re.compile(r"apiKey=[A-Za-z0-9_\-]{20,}"),
                   re.compile(r"(?i)(api[_-]?key|secret|password|token)\s*[:=]\s*['\"]?[A-Za-z0-9_\-]{32,}")]
SAG_ID = re.compile(r"\b\d{4}-\d{2}-\d{2}-[a-z0-9æøå-]+\b")


def repo_filer():
    for f in sorted(ROD.rglob("*")):
        rel = f.relative_to(ROD)
        if f.is_file() and not SPRING_OVER & set(rel.parts):
            yield f, rel


def norm(t):
    return re.sub(r"\s+", " ", re.sub(r"[*_`|#>\-]+", " ", t)).strip().lower()


def lokale_hemmeligheder():
    ud = []
    k = HJEM / ".config" / "byg-data" / "datafordeler_api_key"
    if k.exists() and k.read_text(encoding="utf-8").strip():
        ud.append(("Datafordeler-nøglen", k.read_text(encoding="utf-8").strip()))
    return ud


def videnbanker():
    return sorted((HJEM / ".claude" / "plugins" / "data").glob("*/videnbank"))


def private_termer():
    """Sag-id'er fra videnbankens sager.md + brugerens egne termer (adresse, navne, firmaer …)."""
    termer = set()
    for vb in videnbanker():
        s = vb / "sager.md"
        if s.exists():
            for l in s.read_text(encoding="utf-8").splitlines():
                celle = l.split("|")[1].strip() if l.startswith("|") and l.count("|") > 2 else ""
                if celle and not set(celle) <= set("-: ") and celle.lower() != "sag-id":
                    termer.add(celle)  # første kolonne = sag-id, uanset navneformat
            termer |= set(SAG_ID.findall(s.read_text(encoding="utf-8")))
    f = KONFIG / "private-termer.txt"
    if f.exists():
        termer |= {l.strip() for l in f.read_text(encoding="utf-8").splitlines() if l.strip() and not l.startswith("#")}
    return sorted(termer, key=len, reverse=True)


def sagsmapper():
    """Stier fra videnbankens sager.md (kolonnen Sti) og fra ~/.config/byg-eksperter/sagsmapper.txt,
    plus ejendomskortene i byg-sager/ejendomme/ ved siden af sagsmapperne."""
    stier = set()
    for vb in videnbanker():
        s = vb / "sager.md"
        if s.exists():
            stier |= {pathlib.Path(m).expanduser() for m in re.findall(r"`(/[^`]+|~/[^`]+)`", s.read_text(encoding="utf-8"))}
    f = KONFIG / "sagsmapper.txt"
    if f.exists():
        stier |= {pathlib.Path(l.strip()).expanduser() for l in f.read_text(encoding="utf-8").splitlines()
                  if l.strip() and not l.startswith("#")}
    stier |= {p.parent / "ejendomme" for p in list(stier)}
    return sorted(p for p in stier if p.is_dir() and ROD not in (p, *p.parents))


def fingeraftryk(mapper):
    linjer = set()
    for m in mapper:
        for f in m.rglob("*.md"):
            if "bilag" in f.relative_to(m).parts:
                continue  # eksterne og genererede dokumenter (fx ejendomsdata.md fra pluginets eget script)
            rækker = f.read_text(encoding="utf-8", errors="ignore").splitlines()
            for i, l in enumerate(rækker):
                naeste = rækker[i + 1] if i + 1 < len(rækker) else ""
                if l.lstrip().startswith("|") and re.match(r"^\s*\|[\s:|-]+\|\s*$", naeste):
                    continue  # tabeloverskrift – typisk fra en skabelon i repoet
                n = norm(l)
                if len(n) >= 60:
                    linjer.add(n)
                if l.lstrip().startswith("|"):
                    # tabelceller for sig (fx et faktum i ejendomskortet), så en kopieret værdi også fanges
                    linjer |= {c for c in (norm(x) for x in l.split("|")) if len(c) >= 60}
    return linjer


def main() -> int:
    fejl = []
    hemmeligheder = lokale_hemmeligheder()
    mapper = sagsmapper()
    # ejendom-id'er (filnavnet på ejendomskortet) er typisk en adresse
    ejendomme = {f.stem for m in mapper if m.name == "ejendomme" for f in m.glob("*.md")}
    termer = sorted(set(private_termer()) | ejendomme, key=len, reverse=True)
    aftryk = fingeraftryk(mapper)

    for f, rel in repo_filer():
        # 1. Struktur
        if SAGSMAPPER & set(rel.parts[:-1]) and "skabelon" not in rel.parts:
            fejl.append(f"{rel}: ligger i en sags-/datamappe – hører ikke hjemme i repoet")
        elif f.name in SAGSFILER and not {"skabelon", "evals", "tests"} & set(rel.parts):
            fejl.append(f"{rel}: sagsfil – hører hjemme i en sagsmappe eller pluginets datamappe")
        elif f.suffix.lower() in (".pdf", ".docx", ".xlsx", ".jpg", ".jpeg", ".heic", ".png") and "evals" not in rel.parts:
            fejl.append(f"{rel}: bilag/dokument – hører hjemme i sagsmappens bilag/")
        if f.suffix.lower() not in TEKST:
            continue
        tekst = f.read_text(encoding="utf-8", errors="ignore")
        # 2. Hemmeligheder (værdien udskrives aldrig)
        for navn, v in hemmeligheder:
            if v in tekst:
                fejl.append(f"{rel}: indeholder {navn}")
        for m in NOEGLE_MOENSTRE:
            for hit in m.finditer(tekst):
                fejl.append(f"{rel}:{tekst.count(chr(10), 0, hit.start()) + 1}: ligner en API-nøgle/hemmelighed")
        # 3. Private termer
        lav = tekst.lower()
        for t in termer:
            i = lav.find(t.lower())
            if i >= 0:
                fejl.append(f"{rel}:{tekst.count(chr(10), 0, i) + 1}: privat term fra sag/videnbank ('{t}')")
        # 4. Fingeraftryk fra sagsmapper
        if aftryk:
            n = norm(tekst)
            for l in aftryk:
                if l in n:
                    fejl.append(f"{rel}: indeholder tekst fra en sagsmappe: \"{l[:70]}…\"")

    lokalt = f"{len(termer)} private termer, {len(mapper)} sagsmappe(r), {len(aftryk)} fingeraftryk"
    for x in fejl:
        print("FEJL  " + x)
    print(f"Dataseparation: {len(fejl)} fejl ({lokalt})")
    return 1 if fejl else 0


if __name__ == "__main__":
    sys.exit(main())
