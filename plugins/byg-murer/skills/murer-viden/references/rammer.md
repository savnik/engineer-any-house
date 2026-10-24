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
| R-MUR-01 | Fjerne ikke-bærende væg | Væggen er afklaret som ikke-bærende og ikke-stabiliserende (statik-viden, faglig praksis afsnit 1: mindst tre indikatorer); ingen skorsten eller installationer i væggen; ingen væg eller last ovenpå | Nedbryd ovenfra, afdæk installationer, screen for asbest/PCB/bly i puds og fuger før nedrivning (ældre huse) | Tvivl om bærende eller stabiliserende funktion → statiker | P – mangler |
| R-MUR-02 | Ny dør- eller vinduesåbning i bærende teglvæg med præfabrikeret tegloverligger | Lysning inden for producentens bæreevnetabel for den aktuelle last; vederlag, murværk ovenpå og understøtning under hærdning som i producentens anvisning; fuldt murværk under vederlagene; ingen punktlast (bjælkeende, søjle) inden for overliggerens lastområde | Tegloverligger efter producentens tabel; midlertidig understøtning (nåle/stempler) under udførelse | Lysning eller last uden for tabellen, punktlast over åbningen, revnet eller svagt murværk under vederlag → statiker | T – Wienerberger (Egernsund) tegloverliggere: spænd ca. 0,6–4,5 m efter bæreevnetabel, vederlag ≥ 228 mm, mindst 108 mm murværk ovenpå, understøtning ca. hver 60 cm i hærdetiden (28 døgn). Producentens PDF skal genfindes og verificeres |
| R-MUR-03 | Lille åbning i bærende væg uden ny overligger (fx ventilationshul, rørgennemføring) | P – mangler: største størrelse og afstand til vederlag og andre åbninger | Kerneboring; ingen bortbrydning af sten over hullet | Over grænsen, nær vederlag eller over/under en åbning → statiker | P – mangler |
| R-MUR-04 | Soldaterskifte (stik) over åbning i facade | P – mangler: største lysning uden bærejern, murværkets højde ovenover, last fra bjælkelag eller spær | P – mangler | Større lysning, last fra bjælkelag, eller revner i eksisterende stik → overligger efter producentens tabel (R-MUR-02) eller statiker | P – mangler (ikke fundet i offentlige kilder 2026-10) |
| R-MUR-05 | Lodret rille i bærende væg (el, vvs) udført efter opmuring | Dybde og bredde inden for DS/EN 1996-1-1 tabel 8.2 for vægtykkelsen; afstand og samlet bredde inden for tabellens noter; ikke i skillevægge med brandkrav uden brandvurdering | Rille med rillefræser (støvsug), ikke mejsel; luk med mørtel svarende til murværket | Uden for tabellen eller i en slank, højt belastet pille → statiker | T – DS/EN 1996-1-1 § 8.6.2, tabel 8.2 (DK NA:2019 ændrer ikke 8.6.2(1), V 2026-10 bygningsreglementet.dk). Tabelværdier fra sekundærkilde, se nedenfor |
| R-MUR-06 | Vandret eller skrå rille i bærende væg | Dybde og længde inden for DS/EN 1996-1-1 tabel 8.3; ≥ 500 mm fra åbninger; kun i den øverste eller nederste ottendedel af etagehøjden | Undgå om muligt (forsatte eller overflademonterede føringer); ellers som tabellen | Uden for tabellen, vægge ≤ 115 mm (ingen vandrette riller tilladt) → statiker eller anden føringsvej | T – DS/EN 1996-1-1 § 8.6.3, tabel 8.3 (DK NA:2019 ændrer ikke 8.6.3(1)). Tabelværdier fra sekundærkilde |
| R-MUR-07 | Understøbning af fundament i etaper | P – mangler: etapelængde, rækkefølge, afstand mellem samtidige etaper | P – mangler | Sætningsskader, høj grundvandsstand, dybde under nabofundament → statiker og geotekniker | P – mangler |
| R-MUR-08 | Midlertidig understøtning ved ny åbning | P – mangler: nåle- og stempelafstand for typiske vægge i 1–2-etagers huse | P – mangler | Mere end 2 etager over, tunge bjælkelag med lerindskud, punktlaster → statiker | P – mangler |

## Riller – DS/EN 1996-1-1 § 8.6 (T, sekundærkilde)
Værdierne er fra en sekundærkilde og skal verificeres mod standarden (ds.dk), før R-MUR-05 og R-MUR-06 bruges som ramme. Mål i mm.

**Tabel 8.2 – lodrette riller uden beregning:**

| Vægtykkelse | Efter opmuring: maks. dybde | Efter opmuring: maks. bredde | Udsparet ved opmuring: min. restvæg | Udsparet ved opmuring: maks. bredde |
|---|---|---|---|---|
| 85–115 | 30 | 100 | 70 | 300 |
| 116–175 | 30 | 125 | 90 | 300 |
| 176–225 | 30 | 150 | 140 | 300 |
| 226–300 | 30 | 175 | 175 | 300 |
| > 300 | 30 | 200 | 215 | 300 |

Noter: i vægge ≥ 225 mm må riller på 80 mm dybde og 120 mm bredde gå op til en tredjedel af etagehøjden; afstand mellem riller og til åbninger ≥ 225 mm; samlet bredde af lodrette riller ≤ 0,13 × væglængden.

**Tabel 8.3 – vandrette og skrå riller uden beregning (maks. dybde):**

| Vægtykkelse | Ubegrænset længde | Længde ≤ 1250 |
|---|---|---|
| 85–115 | 0 | 0 |
| 116–175 | 0 | 15 |
| 176–225 | 10 | 20 |
| 226–300 | 15 | 25 |
| > 300 | 20 | 30 |

Noter: ≥ 500 mm vandret afstand til åbninger; ved maskinel fræsning med præcis dybde må dybden øges med 10 mm i vægge > 175 mm; bredden højst halvdelen af den resterende vægtykkelse.

## Myndighed – hvornår kræves en certificeret statiker
Se statik-viden `references/normgrundlag.md` (konstruktionsklasser, V 2026-10-11). Kort: et enfamiliehus i KK1 kræver ikke certificeret statiker, men bærende indgreb skal stadig dimensioneres og dokumenteres (BR18 kap. 15). En producents bæreevnetabel brugt inden for sine forudsætninger er dokumentation for selve overliggeren, ikke for vederlag og fundament.
