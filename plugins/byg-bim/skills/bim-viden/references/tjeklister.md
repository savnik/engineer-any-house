# BIM-modellør – tjeklister

## Før modellering (Definition of Ready)
- [ ] Formål og LOIN skrevet i projektgrundlaget (hvad skal modellen bruges til, af hvem).
- [ ] Kilder listet (K1 …): tegninger med side og målestok, opmåling, fotos, BBR, ejendomskort.
- [ ] Origo, akser og ±0 fastlagt. DVR90-kote og EPSG:25832 for origo, hvis kendt (ellers ingen georeference).
- [ ] Etager og koter, og BBR-arealer til `model.kontrol`.
- [ ] Modtagerens krav (skema, klassifikation, IDS), hvis modellen skal videre.

## Pr. tegning (tegningsimport)
- [ ] Kontaktark set. Tegningssiden rasteriseret i ca. scanningens dpi.
- [ ] Alle visninger, målkæder, rum, åbninger, vægtykkelser, trapper, koter, tekster og ulæselige steder afkodet.
- [ ] Kalibrering med ≥ 3 punkter fra påskrevne mål. `afkod tjek` = 0 fejl.
- [ ] Model bygget, `tjek` = 0 FEJL, egen `sammenlign` uden AFVIGER/MANGLER, der skyldes modellen.
- [ ] Uafhængig sammenligning `resultat: ok`, eller resterende afvigelser beskrevet og på opmålingslisten.

## Pr. etage
- [ ] Ydervægsløkke lukket. Ydermål = tegning. Bruttoareal mod BBR (±5 %).
- [ ] Indervægge med rigtig tykkelse. Rummene lukker, og deres arealer er plausible.
- [ ] Åbninger: antal, placering, bredde, brystning og dørslag tjekket i planen (`tegn plan --id`).
- [ ] Trapper: stigninger × stigning = etagehøjde, og 2·s + g mellem 590 og 650 mm (ellers forklaret).
- [ ] Snit gennem trappe og tag uden kollisioner, gennembrud eller huller.

## Før aflevering
- [ ] `tjek --tegn` = 0 FEJL. Hver ADVARSEL rettet eller forklaret i modelnotatet.
- [ ] IDS bestået (`byg-bolig.ids` og modtagerens IDS).
- [ ] Andelen af elementer med kilde A står i konklusionen, og opmålingslisten er udfyldt.
- [ ] Ingen persondata i modellen.
- [ ] Modelnotat med formål/LOIN, kildeliste, model, kontrol, afvigelser og usikkerheder, tegninger og videnslog.
- [ ] Ved aflevering til fagfolk: validate.buildingsmart.org uden fejl. Filen åbnet i en viewer (BIMcollab Zoom/Open IFC Viewer).

## Fremmed IFC-fil
- [ ] Original i `bim/ind/`, urørt. Arbejd på en kopi.
- [ ] `info` og `tjek` som baseline (skema, enheder, georeference, etager, klasser).
- [ ] Ændringer med `ifcedit` eller script efter `rediger.md`, aldrig i STEP-teksten.
- [ ] `diff` original/kopi = kun de tilsigtede ændringer. `tjek` uden nye fejl.
