# Murer – rammer for standardløsninger

En **ramme** er en standardsituation, hvor en erfaren murermester ved, hvad løsningen er, uden at der skal regnes. Ligger opgaven klart inden for en ramme, så svar kort med standardløsningen og rammens kilde (fælles protokol, afsnit 4 "Triage"). Ligger den på grænsen eller uden for, så gælder den normale arbejdsgang: statiker, beregning og fagnotat.

**Status i kildekolonnen:**
- **V** = verificeret mod primærkilde (dato).
- **T** = værdien er fundet, men skal verificeres mod primærkilden, før den bruges som ramme. En T-række giver ikke et kort svar: brug den som orientering, og henvis til kilden.
- **P** = anerkendt praksis, godkendt af en navngiven fagrolle (murermester, ingeniør) med dato. Formuleres som "almindelig praksis er …", aldrig som et krav. Kræver ikke webopslag. En P-række må kun tilføjes efter godkendelse af en fagperson, aldrig af en agent alene.
- **P – mangler** = pladsholder. Rammen findes i praksis, men er endnu ikke udfyldt. Brug den normale arbejdsgang.

**Rammer gælder kun, når alle betingelser er opfyldt.** Er én betingelse ukendt (fx om væggen er bærende), så er situationen ikke inden for rammen. Skriv da, hvad der skal afklares, og hvad svaret bliver, hvis betingelsen er opfyldt.

| ID | Situation | Ramme (alle betingelser) | Standardløsning | Uden for rammen | Kilde |
|---|---|---|---|---|---|
| R-MUR-01 | Fjerne ikke-bærende væg | Væggen er afklaret som ikke-bærende og ikke-stabiliserende (statik-viden, faglig praksis afsnit 1: mindst tre indikatorer); ingen skorsten eller installationer i væggen; ingen væg eller last ovenpå | Nedbryd ovenfra, afdæk installationer, screen for asbest/PCB/bly i puds og fuger før nedrivning (ældre huse) | Tvivl om bærende eller stabiliserende funktion → statiker | P – mangler (ingen offentlig tjekliste fundet 2026-10). Nedrivning skal planlægges og tilrettelægges forsvarligt (BEK 2107/2021 § 36, V 2026-10-24) |
| R-MUR-02 | Ny dør- eller vinduesåbning i bærende teglvæg med præfabrikeret tegloverligger (Egernsund, EN 845-2) | Overligger og last inden for producentens bjælkeskema; vederlag efter tabellen "Tegloverligger – Egernsund" nedenfor; fuldt, urevnet murværk under vederlagene; murværk ovenpå er overliggende element (≥ 108 mm bredt, 2–9 skifter); ingen punktlast (bjælkeende, søjle, rem) inden for overliggerens lastområde | Tegloverligger efter bjælkeskemaet; midlertidig understøtning efter tabellen nedenfor, indtil mørtlen i vederlagsfugen har tilstrækkelig styrke; midlertidig understøtning af væggen ovenover under udførelse (R-MUR-08) | Last ukendt eller uden for skemaet, punktlast over åbningen, revnet eller svagt murværk under vederlag → statiker (R-STAT-02). Indervæg af porebeton → R-STAT-08 | V 2026-10-24 – Egernsund montagevejledning tegloverligger og DoP THT-01-01-03-2014 Rev2025-09. Bæreevnediagrammernes tal er T (aflæst af kurver). Producentens tabel er ikke alene statisk dokumentation (se "Myndighed") |
| R-MUR-03 | Lille åbning i bærende væg uden ny overligger (fx ventilationshul, rørgennemføring) | P – mangler: største størrelse og afstand til vederlag og andre åbninger | Kerneboring; ingen bortbrydning af sten over hullet | Over grænsen, nær vederlag eller over/under en åbning → statiker | P – mangler (DS/EN 1996-1-1 § 8.6 dækker riller og udsparinger, ikke gennemgående huller; ingen offentlig kilde fundet 2026-10) |
| R-MUR-04 | Uarmeret soldaterskifte (stik) over åbning i facade | P – mangler: største lysning uden bærejern, murværkets højde ovenover, last fra bjælkelag eller spær | P – mangler | Større lysning, last fra bjælkelag, eller revner i eksisterende stik → armeret stik (R-MUR-09), tegloverligger (R-MUR-02) eller statiker | P – mangler (ingen offentlig spændgrænse for uarmeret stik fundet 2026-10) |
| R-MUR-05 | Lodret rille i bærende væg (el, vvs) udført efter opmuring | Dybde og bredde inden for DS/EN 1996-1-1 tabel 8.2 for vægtykkelsen; alle noter til tabellen overholdt; ikke gennem overligger eller andet indmuret bærende element; ikke i armeret murværk; i hulmur vurderes hver vange for sig; ikke i skillevægge med brandkrav uden brandvurdering | Rille med rillefræser (støvsug), ikke mejsel; luk med mørtel svarende til murværket | Uden for tabellen eller i en slank, højt belastet pille → statiker | V 2026-10-24 – EN 1996-1-1:2005 § 8.6.1–8.6.2, tabel 8.2 (teksten læst i en national udgave af EN-teksten, ikke DS-udgaven); DK NA:2019 ændrer ikke 8.6.2(1) |
| R-MUR-06 | Vandret eller skrå rille i bærende væg | Dybde inden for DS/EN 1996-1-1 tabel 8.3; inden for en ottendedel af den frie etagehøjde over eller under et dæk; ≥ 500 mm vandret fra åbninger; last uden stor excentricitet (< t/3) | Undgå om muligt (forsatte eller overflademonterede føringer); ellers som tabellen | Uden for tabellen, vægge 85–115 mm (ingen vandrette riller uden beregning), excentrisk last → statiker eller anden føringsvej | V 2026-10-24 – EN 1996-1-1:2005 § 8.6.3, tabel 8.3 (som R-MUR-05); DK NA:2019 ændrer ikke 8.6.3(1) |
| R-MUR-07 | Understøbning af fundament i etaper | P – mangler: etapelængde, rækkefølge, afstand mellem samtidige etaper | P – mangler | Sætningsskader, høj grundvandsstand, dybde under nabofundament → statiker og geotekniker | P – mangler (ingen dansk kilde fundet 2026-10). T, kun til orientering: DIN 4123:2000 (tysk, erstattet) anviser etaper ≤ 1,25 m og samtidige etaper mindst 3 × etapebredden fra hinanden |
| R-MUR-08 | Midlertidig understøtning ved ny åbning | P – mangler: nåle- og stempelafstand for typiske vægge i 1–2-etagers huse | P – mangler | Mere end 2 etager over, tunge bjælkelag med lerindskud, punktlaster → statiker (R-STAT-06) | P – mangler for afstande. V 2026-10-24: midlertidige understøtninger og afstivninger må kun monteres og demonteres under tilsyn af en udpeget, instrueret person (BEK 2107/2021 § 27); arbejdsgiveren skal sikre mod midlertidig ustabilitet, fx ved afstivning (§ 40) |
| R-MUR-09 | Armeret stik (rulle-, stander- eller liggende skifte) med Sika Murma overliggersystem | Ubelastet murværk (ingen bjælkelag, spær eller punktlast); teglsten i normalformat, klasse ≥ 15 (15–35 MPa), væg 60–120 mm; mørtel KC 50/50/700 eller stærkere; profilet går 100 mm ind over hver side af åbningen; antal skifter over åbningen mindst som tabellen "Murma" nedenfor | Murma-profil og Brictec-armering efter producentens anvisning; understøtning ca. hver meter, indtil mørtlen er hærdet | Belastet murværk, lysning > 3800 mm, kalksandsten over 2800 mm, andet stenformat → tegloverligger (R-MUR-02) eller statiker | V 2026-10-24 – Sika Danmark, MURMA overliggersystem (08.2025). Producentens anvisning er ikke alene statisk dokumentation (se "Myndighed") |

## Tegloverligger – Egernsund (V 2026-10-24)
Kilde: Egernsund montagevejledning for tegloverliggere og DoP THT-01-01-03-2014 Rev2025-09 (EN 845-2). Bæreevnen opstår kun sammen med det ovenliggende murværk.

| Lysning | Mindste vederlag (fuldt tværsnit) |
|---|---|
| < 1,0 m | ½ sten |
| 1,0 m til < 2,0 m | 1 sten |
| ≥ 2,0 m | 1½ sten |

| Overliggerens højde | Afstand mellem midlertidige understøtninger |
|---|---|
| 1 skifte | 0,6 m |
| 2 skifter | 0,9 m |
| 3 skifter (selvbærende) | 1,2 m |

- **Hærdning:** understøtningen bliver stående, til mørtlen i vederlagsfugen har tilstrækkelig styrke. Fuld hærdning tager 28 døgn ved 20 °C, og under +5 °C hærder mørtlen ikke. For FM5 er ca. 1 uge ved 20 °C en tommelfingerregel.
- **Uoverensstemmelse:** DoP'en angiver mindst 108 mm vederlag og understøtning mindst hver 60 cm. Bæreevnediagrammerne forudsætter 228 mm vederlag. Brug montagevejledningens tabel, og mindst 228 mm vederlag, når bæreevnen tages fra diagrammerne.
- **Uden for skemaet** regnes efter DS/EN 1996-1-1 (statiker). Brandklasse R0: ved brandkrav skal statiker eller brandrådgiver vurdere.

## Murma – mindste antal skifter over åbningen (V 2026-10-24)
Kilde: Sika Danmark, MURMA overliggersystem (08.2025). Gælder teglsten 15–35 MPa og væg 60–120 mm. Mål i mm.

| Lysning | Rulleskifte | Standerskifte |
|---|---|---|
| ≤ 1600 | 2 | 2 |
| 1610–1900 | 3 | 2 |
| 1910–2200 | 6 | 4 |
| 2210–2500 | 8 | 6 |
| 2510–2800 | 13 | 11 |
| 2810–3300 | 16 | 14 |
| 3310–3800 | 21 | 19 |

Liggende skifte: 3 skifter op til 2800 mm (T, ikke fuldt verificeret). Kalksandsten anbefales ikke over 2800 mm.

## Riller – EN 1996-1-1:2005 § 8.6 (V 2026-10-24)
Kilde: EN 1996-1-1:2005 § 8.6, læst i en national udgave af EN-teksten. DS-udgaven er ikke set, men DK NA:2019 ændrer ikke 8.6.2(1) og 8.6.3(1). Mål i mm.

**Generelt (8.6.1):** riller og udsparinger må ikke svække stabiliteten. De må ikke gå gennem overliggere eller andre indmurede bærende elementer, og ikke i armeret murværk, medmindre den projekterende tillader det. I hulmure vurderes hver vange for sig.

**Tabel 8.2 – lodrette riller uden beregning:**

| Vægtykkelse | Efter opmuring: maks. dybde | Efter opmuring: maks. bredde | Udsparet ved opmuring: min. restvæg | Udsparet ved opmuring: maks. bredde |
|---|---|---|---|---|
| 85–115 | 30 | 100 | 70 | 300 |
| 116–175 | 30 | 125 | 90 | 300 |
| 176–225 | 30 | 150 | 140 | 300 |
| 226–300 | 30 | 175 | 175 | 300 |
| > 300 | 30 | 200 | 215 | 300 |

Noter til tabel 8.2:
1. Dybden omfatter huller i stenene, som rillen når ind i.
2. I vægge ≥ 225 mm må riller på 80 mm dybde og 120 mm bredde gå op til en tredjedel af etagehøjden over gulvet.
3. Mindst 225 mm vandret afstand mellem riller, og fra en rille til en udsparing eller åbning.
4. Udsparinger skal ligge mindst to gange den bredeste udsparings bredde fra hinanden, og lige så langt fra åbninger.
5. Den samlede bredde af lodrette riller og udsparinger må højst være 0,13 × væggens længde.

**Tabel 8.3 – vandrette og skrå riller uden beregning (maks. dybde):** gælder kun inden for en ottendedel af den frie højde over eller under et dæk, og kun når excentriciteten ved rillen er under t/3. Ellers regnes.

| Vægtykkelse | Ubegrænset længde | Længde ≤ 1250 |
|---|---|---|
| 85–115 | 0 | 0 |
| 116–175 | 0 | 15 |
| 176–225 | 10 | 20 |
| 226–300 | 15 | 25 |
| > 300 | 20 | 30 |

Noter til tabel 8.3:
1. Dybden omfatter huller i stenene, som rillen når ind i.
2. Mindst 500 mm vandret afstand fra rillens ende til en åbning.
3. Riller med begrænset længde skal ligge mindst to gange den længste rilles længde fra hinanden.
4. I vægge > 175 mm må dybden øges med 10 mm, når rillen fræses maskinelt med præcis dybde. Ved maskinel fræsning må der laves riller på højst 10 mm dybde på begge sider af vægge ≥ 225 mm.
5. Bredden må højst være halvdelen af den resterende vægtykkelse.

## Myndighed – hvornår kræves en certificeret statiker
Se statik-viden `references/normgrundlag.md` (konstruktionsklasser, V 2026-10-11). Kort: et enfamiliehus i KK1 kræver ikke certificeret statiker, men bærende indgreb skal stadig dimensioneres og dokumenteres (BR18 kap. 15).

Producentens tabel er ikke alene dokumentation. Vejledningen til BR18 kap. 28 (23-01-2025) § 3.1 siger, at KK1-dokumentation kan henvise til dokumenterede løsninger, når det dokumenteres, at deres forudsætninger svarer til den aktuelle konstruktion. Men den "kan ikke alene være baseret på produktspecifik dokumentation af de enkelte konstruktionsdele" (V 2026-10-24). En bæreevnetabel skal altså ledsages af en redegørelse for, at last, vederlag og murværk passer med tabellens forudsætninger (R-STAT-01, R-STAT-02).
