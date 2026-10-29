# Statiker – rammer for standardløsninger

En **ramme** er en standardsituation, hvor en erfaren ingeniør ved, at svaret ikke afhænger af en beregning: løsningen står i en verificeret tabel eller er anerkendt praksis med kendte forudsætninger. Ligger opgaven klart inden for en ramme, så svar kort med standardløsningen og rammens kilde (fælles protokol, afsnit 4 "Triage"). **Der regnes ikke, og der laves ingen FEM-model.**

| Triage | Hvornår | Hvad du gør |
|---|---|---|
| **Inden for** | Alle betingelser i en række er kendt og opfyldt | Kort svar med rammens ID og kilde. Ingen beregning, ingen FEM |
| **På grænsen** | Én betingelse er tæt på grænsen, eller rammen dækker kun en del af lastvejen | Regn den del, der ikke er dækket (FEM og `statik.py` efter `fem.md`). Resten henviser til rammen |
| **Uden for** | En betingelse er ikke opfyldt, eller ingen ramme passer | Normal arbejdsgang: screening, FEM, overslag, eller henvis til ansvarlig statiker med konkret grund |

Ukendte betingelser (fx om væggen er bærende, om der er punktlast ovenover) gør ikke situationen "på grænsen". Skriv, hvad der skal afklares, og hvad svaret bliver i hvert tilfælde.

**Status i kildekolonnen:** som i masonry-knowledge `references/frames.md`: **V** verificeret (dato) · **T** skal verificeres før brug som ramme (giver ikke et kort svar alene) · **P** anerkendt praksis godkendt af en navngiven fagrolle (dato), formuleret som "almindelig praksis er …" · **P – mangler** pladsholder.

| ID | Situation | Ramme (alle betingelser) | Standardløsning | Uden for rammen | Kilde |
|---|---|---|---|---|---|
| R-STAT-01 | Kræver indgrebet en certificeret statiker? | Enfamiliehus, dobbelthus, rækkehus eller sommerhus uden vandret lejlighedsskel, højst 1 etage under og 2 over terræn | KK1: ingen certificeret statiker. Ombygning uden væsentlig anvendelsesændring eller udvidelse af etagearealet kræver ikke byggetilladelse (BR18 § 5 nr. 3), men BR18 skal overholdes. Bærende indgreb dimensioneres efter BR18 kap. 15 og dokumenteres (relevante dele af A1–A4 og B1; egenkontrol, §§ 503–504) | Andre bygninger, etageboliger, væsentlig anvendelsesændring eller udvidelse af etagearealet → klasseindplacering efter § 489 | V 2026-10-11 – se `standards.md`, kap. 26 og 28. V 2026-10-24: vejledning til kap. 28 (23-01-2025) § 3.1 – dokumentationen må henvise til dokumenterede løsninger med redegørelse for, at forudsætningerne passer, men "kan ikke alene være baseret på produktspecifik dokumentation" |
| R-STAT-02 | Ny åbning i bærende murværk med præfabrikeret tegloverligger | Murer-rammen R-MUR-02 er opfyldt (overligger og last inden for bjælkeskemaet, vederlag og murværk under vederlag som anvist, ingen punktlast i lastområdet) | Overligger efter producentens bjælkeskema. Dokumentationen henviser til skemaet og redegør kort for, at forudsætningerne passer: last, lysning, vederlag og murværk ovenpå og under vederlag (vurderet visuelt: fuldt, uden revner) | Punktlast fra bjælkeende, rem eller søjle i lastområdet; revnet eller svagt murværk under vederlag; last ukendt eller uden for skemaet → opgør lasten med `statik.py` (på grænsen) eller ansvarlig statiker | V 2026-10-24 – Egernsund montagevejledning og DoP, se masonry-knowledge `references/frames.md` R-MUR-02 (diagramværdier T) |
| R-STAT-03 | Riller i bærende murværk | Murer-rammerne R-MUR-05/06 er opfyldt | Ingen beregning | Uden for tabel 8.2/8.3, eller vandret rille med excentricitet ≥ t/3 → beregning efter DS/EN 1996-1-1 | V 2026-10-24 – EN 1996-1-1:2005 § 8.6 (EN-tekst; DK NA:2019 uændret), se masonry-knowledge `references/frames.md` |
| R-STAT-04 | Fjerne væg, der efter screening er **usandsynligt bærende** | Mindst tre indikatorer taler imod bærende funktion (`practice.md` afsnit 1), og væggen er ikke stabiliserende (ikke tværvæg i lang bygning, ikke ved trappehul eller gavl) | Ingen statisk ydelse. Åbn loft eller gulv ved væggen og se efter, før nedrivning | Én indikator taler for bærende, eller væggen er stabiliserende → uden for | P – mangler (screeningen er fra `practice.md`; rammen skal godkendes af ingeniør) |
| R-STAT-05 | Bjælkelag eller etagebjælke af limtræ GL30c i bolig | Alle forudsætninger i tabellen "Limtræ – Lilleheden" nedenfor er opfyldt: bolig, ingen flisebad eller tung gulvopbygning, ingen punktlast, ingen brandkrav, sideværts afstivning ≤ 1,0 m | Dimension efter tabellen | Flisebad, tung gulvopbygning, punktlast, lerindskud, brandkrav, tag- eller væglast på etagebjælken → regn. Konstruktionstræ C24 → P – mangler (ingen dansk offentlig spændtabel fundet 2026-10) | V 2026-10-24 – Lilleheden spændviddetabeller (pr. 4. september 2023, "vejledende og uden ansvar") |
| R-STAT-06 | Midlertidig understøtning ved ny åbning i 1–2-etagers hus | P – mangler: nåle- og stempelafstand for typiske vægge og bjælkelag | Stempellast opgøres med `statik.py` (på grænsen) og sammenholdes med stemplets mindste bæreevne. Doka Eurex 20 top: mindst 20 kN, Eurex 30 top: mindst 30 kN ved enhver udtrækslængde | Mere end 2 etager over, lerindskud, punktlaster, svagt underlag → regn stempellast og underlag | P – mangler for afstande. V 2026-10-24 – Doka Eurex top (03/2025), mindsteværdier. Bæreevne pr. udtrækslængde er T (godkendelse Z-8.311-905). Montage under tilsyn af udpeget person (BEK 2107/2021 § 27, V 2026-10-24) |
| R-STAT-07 | Stålbjælke (IPE/HEB) over åbning i bolig | P – mangler: tabel over typiske spænd og profiler for 1–2 etager med træbjælkelag | P – mangler | Uden for tabellen → regn | P – mangler (ingen offentlig tabel fundet 2026-10) |
| R-STAT-08 | Ny åbning i bærende indervæg af porebeton med H+H bærende porebetonbjælke | Indervæg (ikke facade); bjælketype efter vægtykkelse og lysning i tabellen "Porebetonbjælker – H+H" nedenfor; vederlag som tabellen; ingen punktlast i lastområdet | Opgør linjelasten med `statik.py` (på grænsen) og sammenhold med qd fratrukket bjælkens egenvægt | Facade, vederlag på kalksandsten uden rådgivers godkendelse, punktlast, lysning over tabellen → regn eller ansvarlig statiker | V 2026-10-24 – H+H DoP porebetonbjælker bærende, EN 12602:2016 (02.01.2023; vejledning 16-10-2024) |

## Limtræ – Lilleheden (V 2026-10-24)
Kilde: Lilleheden spændviddetabeller (pr. 4. september 2023). Tabellen er "vejledende og uden ansvar". Den kan henvises til, når det dokumenteres, at forudsætningerne passer (R-STAT-01).

**Forudsætninger:** GL30c; egenlast 0,50 kN/m² + lette skillevægge 0,50 kN/m²; nyttelast bolig A1 1,50 kN/m²; anvendelsesklasse 1; CC2; nedbøjning w_fin ≤ L/400 og w_inst ≤ L/600; egenfrekvens ≥ 8 Hz; sideværts afstivning ≤ 1,0 m; ingen brandkrav.

**Gulvbjælke (s. 10) – største spænd i m ved bjælkeafstand a:**

| Dimension (mm) | a = 0,3 | 0,4 | 0,5 | 0,6 | 0,8 | 1,0 |
|---|---|---|---|---|---|---|
| 65 × 200 | 5,0 | 4,7 | 4,4 | 4,2 | 3,8 | 3,5 |
| 65 × 233 | 5,6 | 5,2 | 4,9 | 4,7 | 4,4 | 4,1 |
| 65 × 266 | 6,2 | 5,8 | 5,5 | 5,2 | 4,9 | 4,6 |
| 65 × 300 | 6,8 | 6,4 | 6,0 | 5,7 | 5,3 | 5,0 |
| 90 × 200 | 5,4 | 5,1 | 4,8 | 4,6 | 4,2 | 3,9 |
| 90 × 266 | 6,8 | 6,3 | 6,0 | 5,7 | 5,3 | 5,0 |
| 115 × 200 | 5,8 | 5,4 | 5,1 | 4,9 | 4,5 | 4,2 |

**Etagebjælke (s. 11) – 1 fag, kun last fra etagedæk, største spænd i m ved husbredde:**

| Dimension (mm) | 4 m | 5 m | 6 m | 7 m | 8 m | 9 m |
|---|---|---|---|---|---|---|
| 115 × 200 | 3,3 | 3,1 | 2,9 | 2,7 | 2,6 | 2,5 |
| 115 × 266 | 4,4 | 4,1 | 3,9 | 3,7 | 3,5 | 3,4 |
| 115 × 300 | 4,8 | 4,5 | 4,3 | 4,2 | 4,0 | 3,8 |
| 140 × 266 | 4,6 | 4,3 | 4,1 | 4,0 | 3,8 | 3,6 |
| 165 × 300 | 5,2 | 4,9 | 4,7 | 4,5 | 4,4 | 4,3 |

## Porebetonbjælker – H+H (V 2026-10-24)
Kilde: H+H DoP porebetonbjælker bærende 575, EN 12602:2016. qd er den regningsmæssige bæreevne. Bjælkens egenvægt skal trækkes fra qd. Brandmodstand R60, fck 4,5 MPa. Bredde: 10 = 100, 15 = 150, 17,5 = 175, 21 = 210 mm. Højde: M19 = 189, M26 = 259 mm. Mål i mm.

| Type | Maks. lysning | qd (kN/m) | Vederlag |
|---|---|---|---|
| 10M19-81 | 610 | 22,8 | ≥ 100 |
| 10M19-117 | 970 | 14,8 | ≥ 100 |
| 10M19-141 | 1210 | 12,0 | ≥ 100 |
| 10M26-117 | 970 | 21,8 | ≥ 100 |
| 10M26-141 | 1210 | 17,5 | ≥ 100 |
| 10M26-153 | 1330 | 15,0 | ≥ 100 |
| 10M26-171 | 1510 | 12,4 | ≥ 100 |
| 10M26-240 | 2110 | 8,4 | ≥ 145 |
| 15M26-117 | 970 | 34,1 | ≥ 100 |
| 15M26-141 | 1210 | 26,6 | ≥ 100 |
| 15M26-171 | 1510 | 19,8 | ≥ 100 |
| 15M26-211 | 1810 | 15,3 | ≥ 150 |
| 15M26-270 | 2410 | 8,9 | ≥ 145 |
| 17,5M19-81 | 610 | 40,0 | ≥ 100 |
| 17,5M19-117 | 970 | 19,1 | ≥ 100 |
| 17,5M19-141 | 1210 | 18,7 | ≥ 100 |
| 17,5M19-153 | 1330 | 15,8 | ≥ 100 |
| 17,5M19-201 | 1810 | 11,5 | ≥ 100 |
| 17,5M19-270 | 2410 | 4,9 | ≥ 145 |
| 17,5M26-117 | 970 | 35,6 | ≥ 100 |
| 17,5M26-141 | 1210 | 30,6 | ≥ 100 |
| 17,5M26-153 | 1330 | 26,5 | ≥ 100 |
| 17,5M26-171 | 1510 | 22,6 | ≥ 100 |
| 17,5M26-371 | 3210 | 5,3 | ≥ 250 |
| 21M19-171 | 1510 | 15,7 | ≥ 100 |
| 21M26-201 | 1810 | 20,1 | ≥ 100 |
| 21M26-231 | 2110 | 17,0 | ≥ 100 |
| 21M26-270 | 2410 | 14,1 | ≥ 145 |

## Det, rammer ikke dækker
- Fundament under nye punktlaster, stabilitet ved fjernede stabiliserende vægge, hanebånd og spærfod, og aktive revner eller sætninger ligger altid uden for rammerne.
- En ramme er ikke statisk dokumentation til byggesagen. Ligger indgrebet inden for en ramme, skal svaret stadig nævne, at ejeren har ansvaret, og hvad der skal dokumenteres (R-STAT-01). En producenttabel kan henvises til, men kun med redegørelse for, at forudsætningerne passer (vejledning til kap. 28 § 3.1).
