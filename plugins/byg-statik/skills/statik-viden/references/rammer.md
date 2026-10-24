# Statiker – rammer for standardløsninger

En **ramme** er en standardsituation, hvor en erfaren ingeniør ved, at svaret ikke afhænger af en beregning: løsningen står i en verificeret tabel eller er anerkendt praksis med kendte forudsætninger. Ligger opgaven klart inden for en ramme, så svar kort med standardløsningen og rammens kilde (fælles protokol, afsnit 4 "Triage"). **Der regnes ikke, og der laves ingen FEM-model.**

| Triage | Hvornår | Hvad du gør |
|---|---|---|
| **Inden for** | Alle betingelser i en række er kendt og opfyldt | Kort svar med rammens ID og kilde. Ingen beregning, ingen FEM |
| **På grænsen** | Én betingelse er tæt på grænsen, eller rammen dækker kun en del af lastvejen | Regn den del, der ikke er dækket (FEM og `statik.py` efter `fem.md`). Resten henviser til rammen |
| **Uden for** | En betingelse er ikke opfyldt, eller ingen ramme passer | Normal arbejdsgang: screening, FEM, overslag, eller henvis til ansvarlig statiker med konkret grund |

Ukendte betingelser (fx om væggen er bærende, om der er punktlast ovenover) gør ikke situationen "på grænsen". Skriv, hvad der skal afklares, og hvad svaret bliver i hvert tilfælde.

**Status i kildekolonnen:** som i murer-viden `references/rammer.md`: **V** verificeret (dato) · **T** skal verificeres før brug som ramme (giver ikke et kort svar alene) · **P** anerkendt praksis godkendt af en navngiven fagrolle (dato), formuleret som "almindelig praksis er …" · **P – mangler** pladsholder.

| ID | Situation | Ramme (alle betingelser) | Standardløsning | Uden for rammen | Kilde |
|---|---|---|---|---|---|
| R-STAT-01 | Kræver indgrebet en certificeret statiker? | Enfamiliehus, dobbelthus, rækkehus eller sommerhus uden vandret lejlighedsskel, højst 1 etage under og 2 over terræn | KK1: ingen certificeret statiker. Bærende indgreb skal stadig dimensioneres efter BR18 kap. 15 og dokumenteres (relevante dele af A1–A4, B1; egenkontrol) | Andre bygninger, etageboliger, væsentlig anvendelsesændring eller udvidelse af etagearealet → klasseindplacering efter § 489 | V 2026-10-11 – se `normgrundlag.md`, kap. 26 og 28 |
| R-STAT-02 | Ny åbning i bærende murværk med præfabrikeret tegloverligger | Murer-rammen R-MUR-02 er opfyldt (lysning og last inden for producentens tabel, vederlag og murværk under vederlag som anvist, ingen punktlast i lastområdet) | Overligger efter producentens tabel. Lastvejen er dokumenteret af tabellen; vederlagets murværk vurderes visuelt (fuldt, uden revner) | Punktlast fra bjælkeende, rem eller søjle i lastområdet; revnet eller svagt murværk under vederlag; lysning over tabellen → regn (på grænsen) eller ansvarlig statiker | T – producentens bæreevnetabel, se murer-viden `references/rammer.md` R-MUR-02 |
| R-STAT-03 | Riller i bærende murværk | Murer-rammerne R-MUR-05/06 er opfyldt | Ingen beregning | Uden for tabel 8.2/8.3 → beregning efter DS/EN 1996-1-1 | T – DS/EN 1996-1-1 § 8.6 (tabelværdier fra sekundærkilde) |
| R-STAT-04 | Fjerne væg, der efter screening er **usandsynligt bærende** | Mindst tre indikatorer taler imod bærende funktion (`faglig-praksis.md` afsnit 1), og væggen er ikke stabiliserende (ikke tværvæg i lang bygning, ikke ved trappehul eller gavl) | Ingen statisk ydelse. Åbn loft eller gulv ved væggen og se efter, før nedrivning | Én indikator taler for bærende, eller væggen er stabiliserende → uden for | P – mangler (screeningen er fra `faglig-praksis.md`; rammen skal godkendes af ingeniør) |
| R-STAT-05 | Træbjælkelag eller bjælke af C24 i bolig | P – mangler: spændtabel for typiske dimensioner, afstand og nyttelast (bolig, uden flisebad) | P – mangler | Flisebad, tung gulvopbygning, punktlast, lerindskud → regn | P – mangler (ingen dansk offentlig spændtabel fundet 2026-10) |
| R-STAT-06 | Midlertidig understøtning ved ny åbning i 1–2-etagers hus | P – mangler: nåle- og stempelafstand og stempelstørrelse for typiske vægge og bjælkelag | P – mangler | Mere end 2 etager over, lerindskud, punktlaster, svagt underlag → regn stempellast | P – mangler |
| R-STAT-07 | Stålbjælke (IPE/HEB) over åbning i bolig | P – mangler: tabel over typiske spænd og profiler for 1–2 etager med træbjælkelag | P – mangler | Uden for tabellen → regn | P – mangler |

## Det, rammer ikke dækker
- Fundament under nye punktlaster, stabilitet ved fjernede stabiliserende vægge, hanebånd og spærfod, og aktive revner eller sætninger ligger altid uden for rammerne.
- En ramme er ikke statisk dokumentation til byggesagen. Ligger indgrebet inden for en ramme, skal svaret stadig nævne, at ejeren har ansvaret, og hvad der skal dokumenteres (R-STAT-01).
