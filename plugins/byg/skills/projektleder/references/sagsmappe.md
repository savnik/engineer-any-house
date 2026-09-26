# Sagsmappe

## Placering og ID
- `byg-sager/<ÅÅÅÅ-MM-DD>-<kort-navn>/` i arbejdsmappen, fx `byg-sager/2025-03-14-bad-1970/`.
- Sagsmappen må aldrig ligge i plugin-repoet eller i `${CLAUDE_PLUGIN_ROOT}`. Er arbejdsmappen et plugin-repo (den har `.claude-plugin/`), så spørg brugeren om en anden placering.
- Ved oprettelse registreres sagen i videnbankens `sager.md` med sag-id, absolut sti og emne. Stien bruges af `tjek_data.py` til at sikre, at sagstekst aldrig havner i repoet.
- Sag-id = mappenavnet. Leverance-ID = `<sag-id>/<fag-id>/<nr>` (fx `2025-03-14-bad-1970/vvs/01`); projektlederens egne: `<sag-id>/projekt/<nr>`.

## Struktur
```
byg-sager/<sag-id>/
├── projektgrundlag.md      formål, bygning, omfang, rammer, antagelser (skabelon i interview.md)
├── beslutningslog.md       beslutninger med begrundelse
├── status.md               fase, næste skridt, åbne spørgsmål, kontrolstatus
├── fagnotater/<fag-id>.md  ét notat pr. fag (fælles protokol)
├── graenseflader.md        grænsefladematrix
├── budget.md               samlet budget (ejes af projektlederen)
├── tidsplan.md             aktiviteter, afhængigheder, hold points
├── risici.md               risikoregister
├── kontrolplan.md          hold points og lovpligtige kontroller
├── erfaringer.md           kandidater til forankring
├── kvalitet/
│   ├── kontrollog.md       én linje pr. dom
│   ├── <leverance>__forsoeg-<n>.json   kontroldomme (gemmes af hooken)
│   └── RCA-<leverance>.md  root cause-analyser
└── bilag/                  fotos, tilbud, rapporter, tegninger
```

## status.md
```
# Status – <sag-id>
**Fase:** <1–7> · **Opdateret:** <dato>
## Næste skridt
## Åbne spørgsmål (til bruger / til fag)
## Kontrolstatus
| Leverance | Fag | Forsøg | Dom | Åbne fund |
|---|---|---|---|---|
```

## kvalitet/kontrollog.md
`<dato> · <leverance-id> · forsøg <n>/3 · <godkendt|afvist|stoppet> · åbne fund K/V/M: <x/y/z> · <sti til dom>`

## Regler
- Én sandhed: opdatér filer i stedet for at lave kopier; skriv ændringer i beslutningslog eller "Revisioner".
- Datoer som ÅÅÅÅ-MM-DD.
- Ingen CPR-numre, kontonumre eller andre unødvendige persondata. Navne på håndværkere kun, når brugeren ønsker det.
- Kendes arbejdsmappen ikke, så spørg brugeren, hvor sagerne skal ligge, første gang.
