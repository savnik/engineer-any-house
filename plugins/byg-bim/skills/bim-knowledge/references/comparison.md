# Sammenligning af tegning og model

Formål: at finde **enhver** forskel mellem originaltegningen og den samme visning tegnet fra modellen, og at afgøre, om fejlen ligger i modellen, i afkodningen eller i tegningen selv.

## Grundlaget (`bim.py compare`)
- Modellen tegnes i **originalens pixelramme** via afkodningens kalibrering. `original.png`, `model.png` og `overlay.png` har samme størrelse og flugter.
- Plan: snit i +1 m (eller visningens `snithoejde`). Snit og facade: z-buffer af modellen. Døre vises med blad og slagbue.
- `auto.md` sammenligner automatisk:

| Art | Hvordan | OK når |
|---|---|---|
| mål | modelflader ud for målets endepunkter (hjælpelinjens fod); afstanden langs målet | afvigelse ≤ max(50 mm; 1,5 %) |
| rum | modelrum, der indeholder punktet; navn og areal | navn passer, areal ±5 % (mindst 0,5 m²) |
| åbning | nærmeste dør/vindue ≤ 400 mm; type og bredde | samme type, bredde ±50 mm |
| væg | væg ved punktet; tykkelse | ±20 mm |
| kote | nærmeste etagekote: `datum: relativ` mod ±0, ellers DVR90 via georeference | ±30 mm |
| EKSTRA | åbninger i modellen inden for visningen, som ikke er afkodet | – (enten mangler afkodningen dem, eller modellen har for mange) |

"NB tegningen selv viser …" betyder, at afkodningen ikke passer med tegningens geometri. Det peger på en afkodningsfejl.

## Den visuelle gennemgang – tjekliste pr. flise
Overlay: originalen lysnet, modellen **rød**. Rødt, der ikke dækker en streg i originalen, er en afvigelse eller et modelelement i overskud. En streg i originalen uden rødt er noget, der mangler i modellen.

1. **Ydervægge:** forløb, knæk og fremspring, tykkelse (begge flader flugter), hjørner.
2. **Indervægge:** placering (begge flader), tykkelse, hvor de ender (T-samling eller fri ende), åbninger i dem.
3. **Åbninger:** antal pr. væg, placering (lysningernes flader), bredde, vindue eller dør, **dørslag** (hvilken side bladet slår mod, og hvilken ende hængslet sidder i – sammenlign blad og bue), brystningshøjde i snit/facade.
4. **Trapper:** placering, løbsretning, bredde, antal trin (tæl dem), op/ned-pil.
5. **Skorsten, søjler, bjælker** (stiplede linjer i plan), aftræk, nicher og fremspring.
6. **Rum:** navn, afgrænsning (findes alle skillevægge?), areal.
7. **Snit/facade:** etagehøjder, gulv- og loftlinjer, tagfod, kip, taghældning, vinduers over- og underkant, terrænlinje (ikke modelleret ved LOIN 2: info).
8. **Tekster:** materialer, "bærende" og koter, som modellen skal afspejle (fx vægtype).

## Alvor og tolerancer
- **Påskrevet mål:** tolerance 50 mm. **Skaleret** (intet påskrevet mål): 1,5 % eller 3 px × skala, det største.
- **væsentlig:** over tolerancen på ydervægge, indervægge, åbninger, trapper og bærende dele. Manglende eller overskydende element. Byttet dør/vindue. Forkert dørslag eller hængsel. Forkert etage, kote eller rumnavn. En afkodningsfejl, der har givet en modelfejl.
- **mindre:** under 2 × tolerancen på detaljer uden betydning for brug, kosmetik, tekstplacering.
- **info:** bevidst udeladt (LOIN), forhold til afklaring på stedet.

## Fejlens årsag
| Fund | Kategori | Hvem retter |
|---|---|---|
| Modellen afviger fra en korrekt afkodning | `geometri`, `aabning`, `trappe`, `rum`, `hoejde_kote`, `mangler_i_model`, `ekstra_i_model` | modelløren (model.yaml) |
| Afkodningen er fejllæst eller ufuldstændig | `afkodningsfejl` | modelløren (afkodning først, så model) |
| Originalen er indbyrdes uenig (kæden summerer ikke, plan ≠ snit) | `tegning_inkonsistent` | ingen – til opmålingslisten og brugeren |
| Kalibreringen er dårlig (overlay forskudt overalt, rest > 40 mm) | `afkodningsfejl` (kalibrering) | modelløren |

## Runde ≥ 2
1. Tag stilling til hver tidligere afvigelse: `lukket` eller `aaben` (genbrug id'et), med evidens.
2. Kør `compare` med `--previous <forrige rundes mappe>`. `tiles.md` markerer så de fliser, hvor modeltegningen er ændret (`model ændret`), og dem, der er pixel for pixel uændrede (`uændret`). Se efter **regressioner** i de ændrede fliser; de uændrede er dækket af forrige runde, medmindre en åben afvigelse ligger i dem. Fliser med auto-fund gennemgås altid. (`bim.py diff` er ikke tilladt for sammenligneren.)
3. Nye væsentlige fund uden for de ændrede områder er `overset: true`.
4. `resultat: ok`, når ingen væsentlige er åbne. Bestridte afvigelser vurderes på originalens evidens.
