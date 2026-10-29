# Sagsmappe

## Placering og ID
- `byg-cases/<ÅÅÅÅ-MM-DD>-<kort-navn>/` i arbejdsmappen, fx `byg-cases/2025-03-14-bad-1970/`.
- Sagsmappen må aldrig ligge i plugin-repoet eller i `${CLAUDE_PLUGIN_ROOT}`. Er arbejdsmappen et plugin-repo (den har `.claude-plugin/`), så spørg brugeren om en anden placering.
- Ved oprettelse registreres sagen i videnbankens `cases.md` med sag-id, absolut sti og emne. Stien bruges af `check_data.py` til at sikre, at sagstekst aldrig havner i repoet.
- Sag-id = mappenavnet. Leverance-ID = `<case-id>/<trade-id>/<nr>` (fx `2025-03-14-bad-1970/plumbing/01`); projektlederens egne: `<case-id>/project/<nr>`.
- Hver sag hører til en ejendom. Ejendommens faste fakta står i **ejendomskortet** `byg-cases/properties/<property-id>.md` (se nedenfor). Det deles af alle sager på samme ejendom, og projektgrundlag og `status.md` henviser til det med linjen `**Ejendom:** <sti>`.

## Permanent og midlertidigt
`byg-cases/` holder kun permanente data: **hovedsager**, **aktive branch-sager**, `properties/` og `archive/`. Alt midlertidigt ligger uden for strukturen.
- **Hovedsag** (`<case-id>/`): sandheden for ejendommens projekt. Har ejendommen en BIM-hovedmodel, ligger den i hovedsagen: `<case-id>/bim/model.yaml` med `history/`, `proposals/` og `out/`. Der findes ingen separat BIM-sag.
- **Branch-sag** (`<hovedsag-id>--<emne>/`, flad søskendemappe): undersøger en ændring (fx VVS-omlægning) som en git-branch. Den har sin egen `status.md`, `project-basis.md`, `trade-notes/` og `quality/` og sine modelændringer som forslag (`bim.py propose <hovedsag>/bim/model.yaml <navn> --out <branch>/bim/proposals`), hvor `basis` peger på hovedsagens model med sha256. Branchen ændrer aldrig hovedsagens filer direkte. Ved godkendelse flettes forslaget ind (`bim.py merge`); er hovedmodellen ændret siden (sha-konflikt), laves forslaget om oven på den nye model ("rebase"). Godkendte leverancer og beslutninger løftes ind i hovedsagens `decision-log.md`/`status.md`, og branchen flyttes til `archive/`.
- **Spørgsmål** (`/byg:ask`) opretter ingen sagsmappe. Kræver de filer, bruges `~/byg-tmp/<ÅÅÅÅ-MM-DD>-<emne>/`, som ikke er under revisionsstyring og må slettes. Et svar, der skal gemmes, løftes ind i hovedsagen eller en branch.
- **Store rådata** (FEM-output, renderinger, mellemresultater) ligger i `~/byg-tmp/`; kun det, der indgår i en godkendt leverance, gemmes i sagen. Husets dokumenter går til `properties/<property-id>/attachments/`.
- **Arkiv** (`archive/`): afsluttede/flettede sager og gamle strukturer. Læses kun, når der henvises dertil; `archive/README.md` har en sti-tabel (gammel → ny sti). Stier i `quality/` og i godkendte leverancer rettes ikke ved flytning.

## Struktur
```
byg-cases/.git/                       lokal revisionsstyring (oprettes og committes af byg-reviews hook; pushes aldrig)
byg-cases/properties/<property-id>.md   ejendomskort: husets faste fakta, fælles for alle sager på ejendommen
byg-cases/archive/                      afsluttede og flettede sager (sti-tabel i README.md)
byg-cases/<case-id>--<emne>/           branch-sag (samme struktur, forslag oven på hovedsagens model)
byg-cases/<case-id>/
├── project-basis.md      formål, omfang, rammer, antagelser (skabelon i interview.md); husets fakta henvises fra ejendomskortet
├── decision-log.md       beslutninger med begrundelse
├── solution-presentation.md  løsningen til brugerens manuelle godkendelse efter fase 2 (Approve G2 <case-id>)
├── changes.md           ændringslog efter design freeze: ændring, kilde, konsekvensanalyse, batch
├── status.md               fase, næste skridt, åbne spørgsmål, kontrolstatus
├── trade-notes/<trade-id>.md  ét notat pr. fag (fælles protokol)
├── interfaces.md        grænsefladematrix
├── budget.md               samlet budget (ejes af projektlederen; detaljer først i fase 3)
├── schedule.md             aktiviteter, afhængigheder, hold points (først i fase 3)
├── risks.md               risikoregister
├── review-plan.md          hold points og lovpligtige kontroller
├── lessons.md           kandidater til forankring
├── proposals/                fagenes forslag til graenseflader, risici, kontrolplan og ejendomskort
│   ├── <trade-id>-<nr>__<mål>.md   flettes ind af hooken, når leverancen godkendes
│   ├── merged/  ·  merge-log.md  ·  .base/ (målfilen, da forslaget blev skrevet)
├── quality/
│   ├── review-log.md       én linje pr. dom
│   ├── <deliverable>__attempt-<n>.json   kontroldomme (gemmes af hooken)
│   └── RCA-<deliverable>[__round-<n>].md  root cause-analyser (én pr. stoppet runde)
├── bim/                    BIM-hovedmodel (model.yaml, history/, proposals/, out/) – kun i hovedsagen
└── attachments/                  fotos, tilbud, rapporter, tegninger
```

## Ejendomskort – byg-cases/properties/<property-id>.md
**Ejendomskortet** er ejendommens langtidshukommelse. Det holder husets og anlæggenes faste fakta, som gælder på tværs af sager: opførelsesår, konstruktion, installationer, målinger og kendte skader. Sagsmappen er projektets korttidshukommelse og holder omfang, beslutninger, leverancer og status. Et faktum om huset skrives kun ét sted, nemlig i ejendomskortet.

**Regler:**
- **Ejer:** kun projektlederen skriver i kortet. Fagagenter citerer fakta med ID (fx `E-VVS-03`). Finder de en ny eller modstridende oplysning, lægger de den i et forslag (`proposals/<trade-id>-<nr>__property-card.md`) med kilde og dato, og hooken fletter den ind, når leverancen godkendes – den gamle værdi flyttes til "Erstattede oplysninger". Er kortet genereret fra BIM-modellen, står oplysningen i stedet under "Til ejendomskortet" i rapporten, og projektlederen fører den ind via et BIM-forslag.
- **Genereret kort (BIM-hovedmodel):** står der `<!-- GENERATED … -->` øverst, er kortet afledt af hovedmodellens `fakta:` (bim-knowledge `references/spec.md`, "Ejendomskort fra hovedmodellen"). Ret så aldrig i kortet. Skriv ændringen i et forslag (`bim.py propose model.yaml <navn>`: ny række, rettet felt, `slet:`), og flet det (`bim.py merge`). Kortet skrives om ved fletningen. Bygherrens egne oplysninger (kilde B) må flettes med det samme (`--note "B <dato>"`). Fakta fra tegninger og fagløsninger flettes først efter kontrol. En erstattet værdi bliver en ny række i afsnittet `erstattede_oplysninger` med id `<id>@<n>`. `bim.py property-card model.yaml --check` afslører håndrettelser.
- **Kilde og dato er obligatoriske.** En oplysning uden dato og kilde er ikke et faktum; den hører under "Åbne spørgsmål". En antagelse (A) må aldrig være grundlag for et sikkerhedskrav.
- **Fag-afgrænsning:** et fag læser "Fælles", sit eget afsnit og "Problemstoffer og kendte skader". Andre afsnit læses kun, når en grænseflade kræver det.
- **Anlægsregistre er master.** Har et anlæg sit eget register (fx et installationsregister for et pillefyr), står der højst én linje i kortet med de afgørende fakta og en henvisning. Ved modstrid gælder registret.
- **Rettelser:** en ændret oplysning flyttes til "Erstattede oplysninger" med dato og grund. Den slettes ikke.
- **Størrelse:** sigt efter højst ca. 150 linjer. Fotos, rapporter og datablade bliver i sagens `attachments/` med en henvisning.
- **Livsforløb:** kortet oprettes i fase 0 i ejendommens første sag ud fra Definition of Ready og eventuelle BBR-data. Det opdateres, når fakta bekræftes. Ved erfaringshøsten flyttes sagens nye fakta om huset hertil.

```
# Ejendomskort – <property-id>
**Opdateret:** <dato> · **Sager:** <case-id'er> · **Anlægsregistre:** <stier eller "ingen">
**Kilder:** F foto · D dokument (typeskilt, manual, rapport, BBR) · M måling · B bygherren · K godkendt fagnotat (leverance-ID) · A antagelse

## Fælles (alle fag)
| ID | Emne | Værdi | Dato | Kilde |
|---|---|---|---|---|
| E-F-01 | Opførelsesår | … | … | D BBR |

## VVS og varme
## El
## Murer: konstruktion, fugt og puds
## Tømrer: tag, klimaskærm og træ
## Ventilation
## Maler: overflader
## Statik: bærende konstruktioner og fundering
## Problemstoffer og kendte skader
(Samme tabel i hvert afsnit. ID-præfiks: E-F, E-VVS, E-EL, E-MUR, E-TØM, E-VENT, E-MAL, E-STAT, E-SKADE.)

## Åbne spørgsmål
| ID | Spørgsmål | Hvem afklarer | Sag |
|---|---|---|---|

## Erstattede oplysninger
| ID | Tidligere værdi | Erstattet (dato) | Grund |
|---|---|---|---|
```

## status.md
```
# Status – <case-id>
**Fase:** <0–4> · **Gate:** <G0–G3 opnået> · **Design freeze:** <ja/nej, dato> · **Opdateret:** <dato>
**Ejendom:** <sti til ejendomskort> · **Erfaringshøst:** <ikke udført | dato>
## Næste skridt
## Åbne spørgsmål (til bruger / til fag)
## Kontrolstatus
| Leverance | Fag | Forsøg | Dom | Åbne fund |
|---|---|---|---|---|
```

## quality/review-log.md
`<dato> · <deliverable-id> · forsøg <n>/2 · <godkendt|afvist|stoppet> · åbne fund K/V/M: <x/y/z> · ikke kontrolleret: <kort, eller "–"> · <sti til dom>`

## Regler
- Én sandhed: opdatér filer i stedet for at lave kopier; skriv ændringer i beslutningslog eller "Revisioner". Historikken ligger i git (`git -C byg-cases log -- <fil>`), så lav aldrig kopier som `notat-v2.md`.
- **Én skriver pr. fil:** hvert fag skriver kun sine egne filer (fagnotat, bilag, forslag, fagets egne mapper); alt andet ejer projektlederen. Se skill `quality-review`, afsnit 8.
- Datoer som ÅÅÅÅ-MM-DD.
- Ingen CPR-numre, kontonumre eller andre unødvendige persondata. Navne på håndværkere kun, når brugeren ønsker det.
- Kendes arbejdsmappen ikke, så spørg brugeren, hvor sagerne skal ligge, første gang.
