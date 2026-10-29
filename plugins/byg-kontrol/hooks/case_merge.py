"""Forslag og fletning: fagagenter bidrager til fælles sagsfiler uden at skrive i dem.

Én skriver pr. fil: de fælles sagsfiler (graenseflader.md, risici.md, kontrolplan.md og ejendomskortet) ejes af
projektlederen. En fagagent, der vil ændre eller tilføje rækker, skriver et forslag:

    <sagsmappe>/forslag/<fag>-<nr>__<mål>.md        fx forslag/vvs-03__graenseflader.md

med de rækker, der ændres eller tilføjes, i tabeller under samme ##-overskrift som i målfilen. Rækker matches på
første kolonne (ID). Samme ID = rækken erstattes, nyt ID = rækken tilføjes sidst i afsnittets tabel. Tekst uden for
tabellerne ignoreres (begrundelsen står i fagnotatet).

Hooken gemmer målfilerne som basis (forslag/.basis/<forslag>), når fagkaldet starter – det, fagagenten læser –
og fletter forslaget,
når leverancen godkendes. Konflikt: en række er ændret i målfilen siden basis, og forslaget ændrer den anderledes –
så skrives intet, og forslaget bliver liggende til projektlederen. Ændres en værdi i ejendomskortet, flyttes den gamle
værdi til "Erstattede oplysninger" (sagsmappe.md: rettelser slettes ikke). En kolonne, hvis overskrift starter med "Ejer",
ændres aldrig af et forslag – ejeren af en snitflade afgør projektlederen (koordinering.md).
"""
import os
import pathlib
import re
import shutil
import time

MAAL = ("graenseflader", "risici", "kontrolplan", "ejendomskort")
FORSLAG_RE = re.compile(r"^(?P<praefiks>[a-z0-9æøå-]+-[A-Za-z0-9._-]+)__(?P<maal>[a-z]+)\.md$")
SEP_RE = re.compile(r"^\s*\|?\s*:?-{3,}")
GENERERET = "<!-- GENERERET"


def forslag_praefiks(lev: str) -> str:
    """'<sag>/vvs/03' → 'vvs-03' (filnavnets præfiks for leverancens forslag)."""
    return lev.split("/", 1)[1].replace("/", "-") if "/" in lev else lev


def celler(linje: str) -> list:
    s = linje.strip()
    if s.startswith("|"):
        s = s[1:]
    if s.endswith("|"):
        s = s[:-1]
    return [c.strip() for c in s.split("|")]


def norm(linje) -> str:
    return "|".join(celler(linje)) if linje else ""


def er_raekke(linje: str) -> bool:
    return linje.lstrip().startswith("|")


def tabeller(linjer: list) -> list:
    """[{afsnit, hoved, start, slut, raekker: [(idx, id)]}] – start/slut er indeks for datarækkerne (slut eksklusiv)."""
    ud, afsnit, i = [], "", 0
    while i < len(linjer):
        l = linjer[i]
        if re.match(r"^#{2,6}\s", l):
            afsnit = l.lstrip("#").strip()
        if er_raekke(l) and i + 1 < len(linjer) and er_raekke(linjer[i + 1]) and SEP_RE.match(linjer[i + 1]):
            t = {"afsnit": afsnit, "hoved": celler(l), "start": i + 2, "raekker": []}
            j = i + 2
            while j < len(linjer) and er_raekke(linjer[j]):
                rid = celler(linjer[j])[0]
                if rid:
                    t["raekker"].append((j, rid))
                j += 1
            t["slut"] = j
            ud.append(t)
            i = j
            continue
        i += 1
    return ud


HISTORIK = "erstattede oplysninger"


def levende(tabs: list) -> list:
    """Tabeller, hvis rækker matches på ID – historiktabellen gentager ID'erne og er kun til tilføjelser."""
    return [t for t in tabs if HISTORIK not in t["afsnit"].lower()]


def raekker_efter_id(linjer: list) -> dict:
    return {rid: linjer[idx] for t in levende(tabeller(linjer)) for idx, rid in t["raekker"]}


def find_ejendomskort(sm: pathlib.Path):
    for navn in ("projektgrundlag.md", "status.md"):
        f = sm / navn
        if not f.is_file():
            continue
        m = re.search(r"\*\*Ejendom(?:skort)?:\*\*\s*`?([^\s`·]+\.md)", f.read_text(encoding="utf-8", errors="replace"))
        if m:
            p = pathlib.Path(m.group(1)).expanduser()
            for kand in ([p] if p.is_absolute() else [sm.parent.parent / p, sm / p, sm.parent / p]):
                if kand.is_file():
                    return kand.resolve()
    kort = sorted((sm.parent / "ejendomme").glob("*.md"))
    return kort[0] if len(kort) == 1 else None


def maal_for(forslag: pathlib.Path, sm: pathlib.Path):
    m = FORSLAG_RE.match(forslag.name)
    if not m or m.group("maal") not in MAAL:
        return None
    if m.group("maal") == "ejendomskort":
        return find_ejendomskort(sm)
    return sm / f"{m.group('maal')}.md"


def basis_sti(forslag: pathlib.Path) -> pathlib.Path:
    return forslag.parent / ".basis" / forslag.name


def gem_basis_for_leverance(sm: pathlib.Path, lev: str) -> None:
    """Kaldes, når fagkaldet starter: målfilerne, som fagagenten læser, er basis for konfliktkontrollen.
    En eksisterende basis (fra et tidligere forsøg) bevares – den ældste basis giver aldrig en overset konflikt."""
    for m in MAAL:
        gem_basis(sm / "forslag" / f"{forslag_praefiks(lev)}__{m}.md", sm)


def ryd_basis(sm: pathlib.Path, lev: str) -> None:
    for b in (sm / "forslag" / ".basis").glob(f"{forslag_praefiks(lev)}__*.md"):
        b.unlink()


def gem_basis(forslag: pathlib.Path, sm: pathlib.Path) -> None:
    """Gemmer målfilen som basis, hvis der ikke allerede er en (normalt fra fagkaldets start)."""
    b = basis_sti(forslag)
    maal = maal_for(forslag, sm)
    if b.exists() or not maal or not maal.is_file():
        return
    b.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(maal, b)


class _Laas:
    def __init__(self, sm: pathlib.Path):
        self.sti = sm / ".byg-flet.laas"

    def __enter__(self):
        self.fh = open(self.sti, "a+")
        try:
            import fcntl
            fcntl.flock(self.fh, fcntl.LOCK_EX)
        except Exception:
            pass
        return self

    def __exit__(self, *_):
        self.fh.close()


def flet(forslag: pathlib.Path, sm: pathlib.Path, lev: str = "", proev: bool = False, tving: bool = False) -> dict:
    """Fletter forslaget ind i målfilen. Returnerer {ok, besked, maal, aendret, nye, konflikter}."""
    res = {"ok": False, "maal": None, "aendret": [], "nye": [], "konflikter": []}
    maal = maal_for(forslag, sm)
    if maal is None:
        res["besked"] = (f"{forslag.name}: ukendt mål – navnet skal være <fag>-<nr>__<mål>.md med mål "
                         f"{', '.join(MAAL)} (ejendomskortet kræver '**Ejendom:** <sti>' i projektgrundlaget).")
        return res
    res["maal"] = str(maal)
    if not maal.is_file():
        res["besked"] = f"Målfilen {maal} findes ikke – projektlederen opretter den, før forslag kan flettes."
        return res
    with _Laas(sm):
        tekst = maal.read_text(encoding="utf-8")
        if GENERERET in tekst.split("\n", 1)[0]:
            res["besked"] = (f"{maal.name} er genereret (fx fra BIM-hovedmodellen) og rettes ikke her – lav et "
                             "BIM-forslag og flet det med bim.py flet.")
            return res
        linjer = tekst.split("\n")
        b = basis_sti(forslag)
        basis = raekker_efter_id(b.read_text(encoding="utf-8").split("\n")) if b.is_file() else None
        f_linjer = forslag.read_text(encoding="utf-8").split("\n")
        f_raekker = [(t["afsnit"], rid, f_linjer[idx], len(t["hoved"])) for t in tabeller(f_linjer) for idx, rid in t["raekker"]]
        if not f_raekker:
            res["besked"] = f"{forslag.name}: ingen tabelrækker (husk overskriftsrækken og |---|-linjen)."
            return res
        tabs = tabeller(linjer)
        nu_raekker, fejl = {}, []
        for t in levende(tabs):
            for idx, rid in t["raekker"]:
                if rid in nu_raekker:
                    fejl.append(f"{rid}: står flere gange i {maal.name} – projektlederen retter dubletten først")
                nu_raekker[rid] = (idx, t)
        erstat, tilfoej = {}, {}
        for afsnit, rid, linje, ncol in f_raekker:
            cur = nu_raekker.get(rid)
            cur_linje = linjer[cur[0]] if cur else None
            if basis is not None and not tving and norm(cur_linje) != norm(basis.get(rid)) and norm(linje) != norm(cur_linje):
                res["konflikter"].append(rid)
                continue
            if cur:
                ejer = [i for i, h in enumerate(cur[1]["hoved"]) if h.strip("* ").lower().startswith("ejer")]
                if ncol != len(cur[1]["hoved"]):
                    fejl.append(f"{rid}: {ncol} kolonner i forslaget, {len(cur[1]['hoved'])} i {maal.name}")
                elif any(i < ncol and celler(linje)[i] != celler(cur_linje)[i] for i in ejer):
                    fejl.append(f"{rid}: ejeren ændres kun af projektlederen (meld afvigelsen i notatet)")
                elif norm(linje) != norm(cur_linje):
                    erstat[cur[0]] = (rid, linje, cur[1])
                continue
            t = next((t for t in tabs if t["afsnit"].lower() == afsnit.lower()), None)
            if t is None:
                fejl.append(f"{rid}: afsnittet '{afsnit}' har ingen tabel i {maal.name}")
            elif ncol != len(t["hoved"]):
                fejl.append(f"{rid}: {ncol} kolonner i forslaget, {len(t['hoved'])} i afsnittet '{afsnit}'")
            else:
                tilfoej.setdefault(t["slut"], []).append(linje)
                res["nye"].append(rid)
        if res["konflikter"] or fejl:
            dele = []
            if res["konflikter"]:
                dele.append(f"konflikt i {', '.join(res['konflikter'])} (ændret i {maal.name}, siden forslaget blev skrevet)")
            dele += fejl
            res["besked"] = f"{forslag.name} → {maal.name}: intet flettet – " + "; ".join(dele)
            return res
        dato = time.strftime("%Y-%m-%d")
        erstattede = next((t for t in tabs if HISTORIK in t["afsnit"].lower()), None)
        for idx, (rid, linje, t) in erstat.items():
            res["aendret"].append(rid)
            vk = next((i for i, h in enumerate(t["hoved"]) if h.lower() == "værdi"), None)
            if erstattede is not None and vk is not None:
                gl, ny = celler(linjer[idx]), celler(linje)
                if vk < len(gl) and vk < len(ny) and gl[vk] != ny[vk]:
                    raekke = ([rid, gl[vk], dato, f"forslag {lev or forslag.stem}"] + [""] * 10)[:len(erstattede["hoved"])]
                    tilfoej.setdefault(erstattede["slut"], []).append("| " + " | ".join(raekke) + " |")
            linjer[idx] = linje
        for pos in sorted(tilfoej, reverse=True):
            linjer[pos:pos] = tilfoej[pos]
        res["ok"] = True
        res["besked"] = (f"{forslag.name} → {maal.name}: {len(res['aendret'])} ændret, {len(res['nye'])} nye"
                         + ("" if basis is not None else " (uden basis – ingen konfliktkontrol)"))
        if proev:
            return res
        tmp = maal.with_name(maal.name + ".tmp")
        tmp.write_text("\n".join(linjer), encoding="utf-8")
        os.replace(tmp, maal)
        flettet = forslag.parent / "flettet"
        flettet.mkdir(exist_ok=True)
        shutil.move(str(forslag), str(flettet / forslag.name))
        if b.is_file():
            b.unlink()
        log = forslag.parent / "flettelog.md"
        with open(log, "a", encoding="utf-8") as fh:
            fh.write(f"{dato} · {lev or '-'} · {forslag.name} → {maal.name} · ændret: {', '.join(res['aendret']) or '-'} · "
                     f"nye: {', '.join(res['nye']) or '-'}\n")
    return res


def leverancens_forslag(sm: pathlib.Path, lev: str) -> list:
    d = sm / "forslag"
    return sorted(d.glob(f"{forslag_praefiks(lev)}__*.md")) if d.is_dir() else []
