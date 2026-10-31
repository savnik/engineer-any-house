# El – tjeklister

## Projektering
- [ ] Behovsanalyse rum for rum; fremtidige behov (elbil, varmepumpe, solceller)
- [ ] Kapacitet: hovedsikring, stikledning, samtidighed; evt. laststyring
- [ ] Gruppeplan, RCD ≤ 30 mA (ikke type AC) og -opdeling, overspændingsbeskyttelse; sikring ≤ 13 A til 10/13 A-stikkontakter
- [ ] Ved ændring: hvad ændres (nye regler)? Flere end 2 tilslutningssteder → beskyttelsesleder; køkken → ≥ 3 stikkontakter på ≥ 2 grupper; tavle flyttes → nugældende krav, højst 2,2 m (under 1 m aflåst)
- [ ] Kabeldimensionering (forlægning, korrektion, spændingsfald, kortslutning); Ik max/Ik min fra netselskabet, ellers Fællesregulativets standardværdier – regnet med `el.py panel`, fast gruppeskema i notatet
- [ ] Pr. gruppe: Iz efter værste del af ruten (Ci, hvor kablet ligger i isolering – også efter efterisolering af loft), ΔU, Ik,min i kredsens ende ≥ Ia; Ik,max ved tavlen ≤ brydeevne eller dokumenteret back-up
- [ ] Tavle: mindst 2 × RCD 30 mA, ingen type B efter type A/F, ingen to 30 mA i serie (undertavle), elbil/varmepumpe med rette RCD-type, faselast fordelt, ≥ 20 % reserve, LED-spots pr. gruppe efter driverens indkoblingsstrøm
- [ ] Særlige rum: badeværelse (områder efter 701:2024 målt på planen), udendørs, køkken
- [ ] Føringsveje: installationszone, lufttætte dåser, brandtætning
- [ ] Tilmelding til netselskab før arbejdet påbegyndes (solceller, batteri, varmepumpe, lader, ændring)
- [ ] Grænseflader aftalt med tømrer, murer, vvs, ventilation

## Hold point – før lukning
- [ ] Kabelføring og dåser fotodokumenteret med mål
- [ ] Gennemføringer i dampspærre og brandadskillelser tætnet
- [ ] Ingen samlinger skjult uden adgang

## Verifikation (DS/HD 60364-6)
- [ ] Eftersyn: materielvalg, IP-klasser, mærkning, afstande, beskyttelse
- [ ] Afprøvning: beskyttelseslederes kontinuitet, isolationsmodstand, polaritet, sløjfeimpedans/kortslutningsstrøm, RCD (udløsestrøm og -tid), funktion
- [ ] Rapportering af verifikationen udleveret til ejer

## Aflevering
- [ ] Gruppefortegnelse i tavlen; solcelleskilt og mærkning "spændingsførende efter adskillelse" ved solceller
- [ ] Fund i den eksisterende installation meddelt ejeren skriftligt (pligt til afhjælpning snarest muligt)
- [ ] Dokumentation, datablade, brugsvejledninger (lader, solceller, styring)
- [ ] Instruktion i RCD-test og tavle
