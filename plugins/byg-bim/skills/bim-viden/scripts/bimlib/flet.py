"""Hovedmodel og forslag: én source of truth (hovedmodellen), ændringer laves i en forslagsfil oven på den
og flettes først ind, når forslaget er godkendt.

  forslag <hoved.yaml> <navn>   → <hovedmappe>/forslag/<navn>.yaml med basis og basis_sha256
  flet <forslag.yaml> [--proev] → forslaget føres ind i hovedmodellen; kun de berørte elementer skrives om,
                                  alle andre linjer og kommentarer står urørt. Hovedmodellen før og efter
                                  gemmes i historik/, forslaget flyttes til historik/forslag/, og fletningen
                                  logges i historik/flettelog.md.

Sikkerhed: resultatet læses tilbage og skal give præcis samme model som forslaget gav oven på hovedmodellen
(det, kontrollen godkendte). Er hovedmodellen ændret siden forslaget blev oprettet, sammenlignes med den
version, forslaget byggede på (historik/), og fletningen stoppes, hvis de samme elementer er ændret begge steder.
"""
import datetime
import hashlib
import pathlib
import re
import shutil

import yaml

from .spec import FORSLAGSFELTER, IDLISTER, SpecFejl, _flet, _laes, indlaes

LISTER = IDLISTER


def _sha(sti: pathlib.Path) -> str:
    return hashlib.sha256(sti.read_bytes()).hexdigest()


def _historik(hoved: pathlib.Path) -> pathlib.Path:
    return hoved.parent / "historik"


def _gem_version(hoved: pathlib.Path) -> pathlib.Path:
    h = _historik(hoved)
    h.mkdir(exist_ok=True)
    mål = h / f"{hoved.stem}.{_sha(hoved)[:12]}.yaml"
    if not mål.exists():
        shutil.copy2(hoved, mål)
    return mål


def _flow(v) -> str:
    return yaml.safe_dump(v, default_flow_style=True, allow_unicode=True, sort_keys=False, width=10**9).removesuffix("\n...\n").strip()


# ------------------------------------------------------------------ tekstblokke i hovedmodellen
def _sektion(linjer, navn):
    """(start, slut) for linjerne under topnøglen `navn:` (slut eksklusiv) eller None."""
    start = next((i for i, l in enumerate(linjer) if re.match(rf"{re.escape(navn)}:(\s|$)", l)), None)
    if start is None:
        return None
    slut = next((i for i in range(start + 1, len(linjer)) if re.match(r"[^\s#]", linjer[i])), len(linjer))
    return start, slut


def _blokke(linjer, start, slut, liste: bool, ind: int = 2):
    """Elementblokke i en sektion: [(fra, til)] i filens rækkefølge. Et element er en linje på indrykning `ind`
    ('- ' eller 'nøgle:') plus fortsættelseslinjer med større indrykning. Tomme linjer og kommentarer inde i
    et element hører med; tomme linjer og kommentarer lige før næste element gør ikke."""
    mønster = re.compile(" " * ind + (r"- " if liste else r"[^\s#-][^:]*:"))
    ud, i = [], start + 1
    while i < slut:
        if mønster.match(linjer[i]):
            j = i + 1
            while j < slut and (not linjer[j].strip() or linjer[j].lstrip().startswith("#")
                                or len(linjer[j]) - len(linjer[j].lstrip()) > ind):
                j += 1
            while j > i + 1 and (not linjer[j - 1].strip() or linjer[j - 1].lstrip().startswith("#")):
                j -= 1
            ud.append((i, j))
            i = j
        else:
            i += 1
    return ud


def _dict_tekst(linjer, fra, til, ind, g, n, erstat, indsæt, sti, fx):
    """Skriv kun de ændrede nøgler i en mapping om. En undermapping i blokform skrives om nøgle for nøgle.
    Står nøglen i forslaget med samme værdi, bruges forslagets tekst ordret – og har den kommentarer lige over sig,
    erstatter de hovedmodellens kommentarer over nøglen. Ellers skrives værdien på én linje, og kommentarerne står."""
    bl = _blokke(linjer, fra, til, False, ind)
    if len(bl) != len(g):
        raise SpecFejl([f"flet: kan ikke afgrænse nøglerne i '{'.'.join(sti)}' ({len(bl)} blokke, {len(g)} nøgler)"
                        f" – skriv hver nøgle på sin egen linje med {ind} mellemrums indrykning"])

    def ny_tekst(nøgle, værdi):
        f = fx.nøgle([*sti, nøgle], værdi)
        if f:
            return f[0] and [" " * ind + x for x in f[0]], [" " * ind + x if x.strip() else x for x in f[1]]
        return None, [" " * ind + f"{nøgle}: {_flow(værdi)}"]

    forrige = fra + 1
    for nøgle, (a, b) in zip(list(g), bl):
        lead = a
        while lead > forrige and linjer[lead - 1].lstrip().startswith("#"):
            lead -= 1
        forrige = b
        if nøgle not in n:
            erstat[lead] = (b, [])
        elif n[nøgle] != g[nøgle]:
            blokform = re.match(rf"\s*{re.escape(str(nøgle))}:\s*(#.*)?$", linjer[a])
            barn = next((len(x) - len(x.lstrip()) for x in linjer[a + 1:b] if x.strip() and not x.lstrip().startswith("#")),
                        None)
            if isinstance(g[nøgle], dict) and isinstance(n[nøgle], dict) and blokform and barn and barn > ind:
                _dict_tekst(linjer, a, b, barn, g[nøgle], n[nøgle], erstat, indsæt, [*sti, nøgle], fx)
            else:
                kom, tekst = ny_tekst(nøgle, n[nøgle])
                erstat[lead if kom else a] = (b, (kom or []) + tekst)
    nye = [x for x in n if x not in g]
    if nye:
        sidste = bl[-1][1] if bl else fra + 1
        for x in nye:
            kom, tekst = ny_tekst(x, n[x])
            indsæt.setdefault(sidste, []).extend((kom or []) + tekst)


def _ændringer(gammel: dict, ny: dict) -> set:
    """ID'er (og topnøgler) der er forskellige mellem to rå modeller."""
    ud = set()
    for k in set(gammel) | set(ny):
        if k in LISTER:
            g = {str(e.get("id")): e for e in gammel.get(k) or []}
            n = {str(e.get("id")): e for e in ny.get(k) or []}
            ud |= {i for i in set(g) | set(n) if g.get(i) != n.get(i)}
        elif isinstance(gammel.get(k), dict) and isinstance(ny.get(k), dict):
            ud |= {f"{k}.{f}" for f in set(gammel[k]) | set(ny[k]) if gammel[k].get(f) != ny[k].get(f)}
        elif gammel.get(k) != ny.get(k):
            ud.add(k)
    return ud


def _berørt(forslag: dict) -> set:
    ud = {str(x) for x in (forslag.get("nedrives") or []) + (forslag.get("slet") or [])}
    for k, v in forslag.items():
        if k in FORSLAGSFELTER:
            continue
        if k in LISTER:
            ud |= {str(e.get("id")) for e in v or []}
        elif isinstance(v, dict):
            ud |= {f"{k}.{f}" for f in v}
        else:
            ud.add(k)
    return ud


class _Forslagstekst:
    """Forslagets egen tekst for en sektion eller et element – bruges ordret (med kommentarer), når den giver
    præcis den flettede værdi; ellers skrives elementet på én linje."""

    def __init__(self, tekst):
        self.linjer = (tekst or "").split("\n")

    def sektion(self, k, værdi):
        sek = _sektion(self.linjer, k)
        if sek is None:
            return None
        bid = self.linjer[sek[0]:sek[1]]
        while bid and (not bid[-1].strip() or bid[-1].startswith("#")):
            bid.pop()
        return bid if _læs_tekst(bid) == {k: værdi} else None

    def nøgle(self, sti, værdi):
        """(ledende kommentarer, linjer) for nøglen sti[-1] i mappingen sti[:-1] – kun hvis de giver `værdi`."""
        sek = _sektion(self.linjer, sti[0])
        if sek is None:
            return None
        fra, til, ind = sek[0], sek[1], 2
        for i, k in enumerate(sti[1:]):
            bl = [(a, b) for a, b in _blokke(self.linjer, fra, til, False, ind)
                  if re.match(rf"\s*{re.escape(str(k))}:(\s|$)", self.linjer[a])]
            if not bl:
                return None
            a, b = bl[0]
            if i == len(sti) - 2:
                bid = [x[ind:] for x in self.linjer[a:b]]
                if _læs_tekst(bid) != {k: værdi}:
                    return None
                lead = a
                while lead > fra + 1 and self.linjer[lead - 1].lstrip().startswith("#"):
                    lead -= 1
                return [x[ind:] for x in self.linjer[lead:a]], bid
            ind = next((len(x) - len(x.lstrip()) for x in self.linjer[a + 1:b]
                        if x.strip() and not x.lstrip().startswith("#")), None)
            if ind is None:
                return None
            fra, til = a, b
        return None

    def element(self, k, nøgle, værdi, liste):
        sek = _sektion(self.linjer, k)
        if sek is None:
            return None
        for fra, til in _blokke(self.linjer, *sek, liste):
            bid = self.linjer[fra:til]
            v = _læs_tekst([f"{k}:"] + bid)
            v = (v or {}).get(k)
            if liste and isinstance(v, list) and len(v) == 1 and v[0] == værdi:
                return bid
            if not liste and isinstance(v, dict) and v == {nøgle: værdi}:
                return bid
        return None


def _læs_tekst(linjer):
    try:
        return yaml.safe_load("\n".join(linjer))
    except yaml.YAMLError:
        return None


def _skriv_tekst(tekst: str, gammel: dict, ny: dict, ftekst: str = None) -> str:
    """Skriv kun de ændrede elementer om i hovedmodellens tekst."""
    fx = _Forslagstekst(ftekst)
    linjer = tekst.split("\n")
    erstat = {}   # linjeindeks (fra) -> (til, nye linjer)
    indsæt = {}   # linjeindeks -> nye linjer (indsættes før)
    nye_sektioner = []
    for k in ny:
        if k in FORSLAGSFELTER:
            continue
        g, n = gammel.get(k), ny.get(k)
        if g == n:
            continue
        sek = _sektion(linjer, k)
        liste = k in LISTER
        if sek is None or not isinstance(n, (list, dict)) or (liste and not isinstance(g, list)) \
                or (not liste and not isinstance(g, dict)):
            if sek is not None:
                erstat[sek[0]] = (sek[1], [f"{k}: {_flow(n)}" if not isinstance(n, (list, dict))
                                           else f"{k}:"] + _render(n, liste))
            else:
                nye_sektioner += fx.sektion(k, n) or ([f"{k}:"] + _render(n, liste) if isinstance(n, (list, dict))
                                                     else [f"{k}: {_flow(n)}"])
                nye_sektioner.append("")
            continue
        if not liste:
            _dict_tekst(linjer, *sek, 2, g, n, erstat, indsæt, [k], fx)
            continue
        bl = _blokke(linjer, *sek, liste)
        nøgler = [str(e.get("id")) for e in g] if liste else list(g)
        if len(bl) != len(nøgler):
            raise SpecFejl([f"flet: kan ikke afgrænse elementerne i '{k}' ({len(bl)} blokke, {len(nøgler)} elementer)"
                            " – skriv hvert element på sin egen linje ('  - {id: …}' / '  nøgle: …')"])
        gpos = dict(zip(nøgler, bl))
        nmap = {str(e.get("id")): e for e in n} if liste else n
        gmap = {str(e.get("id")): e for e in g} if liste else g
        for nøgle, (fra, til) in gpos.items():
            if nøgle not in nmap:
                erstat[fra] = (til, [])
            elif nmap[nøgle] != gmap[nøgle]:
                erstat[fra] = (til, fx.element(k, nøgle, nmap[nøgle], liste)
                               or _render({nøgle: nmap[nøgle]} if not liste else [nmap[nøgle]], liste))
        nye = [x for x in nmap if x not in gpos]
        if nye:
            sidste = bl[-1][1] if bl else sek[0] + 1
            for x in nye:
                indsæt.setdefault(sidste, []).extend(fx.element(k, x, nmap[x], liste)
                                                     or _render([nmap[x]] if liste else {x: nmap[x]}, liste))
    ud = []
    i = 0
    while i < len(linjer):
        if i in indsæt:
            ud += indsæt.pop(i)
        if i in erstat:
            til, nye = erstat.pop(i)
            ud += nye
            i = til
            continue
        ud.append(linjer[i])
        i += 1
    for x in indsæt.values():
        ud += x
    if nye_sektioner:
        while ud and ud[-1] == "":
            ud.pop()
        ud += [""] + nye_sektioner
    return "\n".join(ud)


def _render(v, liste: bool):
    if liste:
        return [f"  - {_flow(e)}" for e in v]
    return [f"  {k}: {_flow(x)}" for k, x in v.items()]


# ------------------------------------------------------------------ kommandoer
def opret(hoved, navn, note=None) -> int:
    hoved = pathlib.Path(hoved).resolve()
    if not hoved.exists():
        print(f"Hovedmodellen findes ikke: {hoved}")
        return 1
    if _laes(hoved).get("basis"):
        print(f"{hoved.name} har selv en basis – et forslag skal bygge direkte på hovedmodellen")
        return 1
    mappe = hoved.parent / "forslag"
    mappe.mkdir(exist_ok=True)
    sti = mappe / f"{navn}.yaml"
    if sti.exists():
        print(f"Findes allerede: {sti}")
        return 1
    _gem_version(hoved)
    rel = pathlib.Path("..") / hoved.name
    sti.write_text(
        f"# Forslag '{navn}' oven på hovedmodellen {hoved.name} ({datetime.date.today()}). Ret KUN her – aldrig i {hoved.name}.\n"
        + (f"# {note}\n" if note else "")
        + "# Skriv kun det, der ændres: elementer med samme id overskriver felterne (null fjerner et felt), nye id'er\n"
          "# tilføjes, 'nedrives: [id, …]' = renovering, 'slet: [id, …]' = modelrettelse. Byg/kontrollér forslaget med\n"
          f"#   bim.py byg forslag/{navn}.yaml   ·   flet først ind efter godkendelse: bim.py flet forslag/{navn}.yaml\n"
        f"basis: {rel.as_posix()}\n"
        f"basis_sha256: {_sha(hoved)}\n",
        encoding="utf-8")
    print(f"OPRETTET {sti}")
    print(f"  basis {hoved.name} ({_sha(hoved)[:12]}); version gemt i historik/")
    return 0


def flet(forslag, proev=False, tving=False, note=None) -> int:
    fsti = pathlib.Path(forslag).resolve()
    fr = _laes(fsti)
    if not fr.get("basis"):
        print("Forslaget har ingen 'basis:' – det er ikke et forslag oven på en hovedmodel")
        return 1
    hoved = (fsti.parent / fr["basis"]).resolve()
    if not hoved.exists():
        print(f"Hovedmodellen findes ikke: {hoved}")
        return 1
    tekst = hoved.read_text(encoding="utf-8")
    gammel = _laes(hoved)
    if gammel.get("basis"):
        print(f"{hoved.name} har selv en basis – flet kun ind i en hovedmodel")
        return 1

    # Er hovedmodellen ændret, siden forslaget blev oprettet?
    sha_nu = _sha(hoved)
    sha_f = str(fr.get("basis_sha256") or "")
    konflikt = set()
    if sha_f and sha_f != sha_nu:
        før = _historik(hoved) / f"{hoved.stem}.{sha_f[:12]}.yaml"
        if not før.exists():
            print(f"STOP: {hoved.name} er ændret siden forslaget, og versionen {sha_f[:12]} findes ikke i historik/.")
            if not tving:
                return 1
        else:
            konflikt = _ændringer(_laes(før), gammel) & _berørt(fr)
            if konflikt:
                print(f"KONFLIKT: {hoved.name} er ændret siden forslaget, og de samme elementer er ændret begge steder:")
                for x in sorted(konflikt):
                    print("  - " + x)
                print("  Opdatér forslaget mod den nuværende hovedmodel (og kontrollér igen), eller brug --tving.")
                if not tving:
                    return 1
            else:
                print(f"  Hovedmodellen er ændret siden forslaget ({sha_f[:12]} → {sha_nu[:12]}), men ikke i de samme elementer.")

    ny = _flet(gammel, fr)
    fejl = ny.pop("_fejl", [])
    if fejl:
        print(f"FLET-FEJL ({len(fejl)}):")
        for x in fejl:
            print("  - " + x)
        return 1
    ny_tekst = _skriv_tekst(tekst, gammel, ny, fsti.read_text(encoding="utf-8"))
    ændret = _ændringer(gammel, ny)
    if not ændret:
        print("Forslaget ændrer intet i hovedmodellen.")
        return 0

    # Kontrol 1: teksten giver præcis den flettede model. Kontrol 2: den validerer som spec.
    if yaml.safe_load(ny_tekst) != ny:
        print("STOP: den omskrevne tekst giver ikke den forventede model (fejl i flet) – intet er skrevet.")
        return 1
    tmp = hoved.with_name(f".{hoved.stem}.flet-tjek.yaml")
    tmp.write_text(ny_tekst, encoding="utf-8")
    try:
        indlaes(tmp)
    except SpecFejl as e:
        print(f"SPEC-FEJL efter fletning ({len(e.fejl)}) – intet er skrevet:")
        for x in e.fejl[:40]:
            print("  - " + x)
        return 1
    finally:
        tmp.unlink(missing_ok=True)

    g_ids = {str(e.get("id")) for k in LISTER for e in gammel.get(k) or []}
    n_ids = {str(e.get("id")) for k in LISTER for e in ny.get(k) or []}
    nye, slettet = sorted(n_ids - g_ids), sorted(g_ids - n_ids)
    rettet = sorted(ændret - set(nye) - set(slettet))
    print(f"{'PRØVE – intet skrevet' if proev else 'FLETTET'}: {fsti.name} → {hoved.name}")
    print(f"  rettet {len(rettet)}: {', '.join(rettet[:30])}{' …' if len(rettet) > 30 else ''}")
    print(f"  nye {len(nye)}: {', '.join(nye[:30])}{' …' if len(nye) > 30 else ''}")
    if slettet:
        print(f"  slettet {len(slettet)}: {', '.join(slettet)}")
    if proev:
        return 0

    dato = datetime.date.today().isoformat()
    _gem_version(hoved)
    linjer = ny_tekst.split("\n")
    pos = next((i for i, l in enumerate(linjer) if not l.startswith("#")), 0)
    linjer.insert(pos, f"# Flettet {dato}: {fsti.name}{' – ' + note if note else ''} (rettet {len(rettet)}, nye {len(nye)}, slettet {len(slettet)}).")
    hoved.write_text("\n".join(linjer), encoding="utf-8")
    efter = _gem_version(hoved)
    h = _historik(hoved)
    (h / "forslag").mkdir(exist_ok=True)
    arkiv = h / "forslag" / f"{fsti.stem}.{dato}.yaml"
    n = 2
    while arkiv.exists():
        arkiv = h / "forslag" / f"{fsti.stem}.{dato}-{n}.yaml"
        n += 1
    shutil.move(str(fsti), arkiv)
    log = h / "flettelog.md"
    if not log.exists():
        log.write_text(f"# Flettelog – {hoved.name}\n| Dato | Forslag | Før | Efter | Rettet | Nye | Slettet | Note |\n|---|---|---|---|---|---|---|---|\n",
                       encoding="utf-8")
    with log.open("a", encoding="utf-8") as f:
        f.write(f"| {dato} | {fsti.name} | {sha_nu[:12]} | {efter.stem.split('.')[-1]} | {', '.join(rettet)} | "
                f"{', '.join(nye)} | {', '.join(slettet)} | {note or ''} |\n")
    print(f"  før/efter gemt i historik/, forslaget flyttet til {arkiv.relative_to(hoved.parent)}")
    if (yaml.safe_load(ny_tekst).get("ejendomskort") or {}).get("fil"):
        from .ejendomskort import generer
        generer(hoved)
    print(f"  næste: bim.py byg {hoved.name} og tjek – IFC'en er ikke bygget om")
    return 0
