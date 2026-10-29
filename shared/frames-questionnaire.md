# Spørgeliste til fagfolk – rammer for standardløsninger

Svarene bliver til **P-rækker** (anerkendt praksis) i `plugins/byg-masonry/skills/masonry-knowledge/references/frames.md` og `plugins/byg-structural/skills/structural-knowledge/references/frames.md`. Skriv for hvert svar: rolle (murermester / ingeniør), dato og eventuel kilde (producentanvisning, firmaets standard, egen praksis). Skriv aldrig navne på kunder eller adresser.

Spørg efter **hvad I gør i praksis i et almindeligt 1–2-etagers parcelhus**, og **hvad der får jer til at ringe til en ingeniør**.

Nogle rækker har nu en primærkilde (V 2026-10-24): Egernsund tegloverliggere, Sika Murma, EN 1996-1-1 § 8.6 (riller), Lilleheden limtræ, H+H porebetonbjælker og Doka-stempler (mindste bæreevne). Ved dem er spørgsmålet ikke, hvad værdien er, men **om I følger kilden i praksis, eller hvornår I afviger**.

## Murermester
1. **Soldaterskifte (R-MUR-04):** Hvor stor en lysning laver I med et uarmeret soldaterskifte uden bærejern? (Armeret stik med Murma er dækket af R-MUR-09.) Hvornår lægger I bærejern eller fladjern i? Hvor meget murværk skal der være ovenover, og må der ligge bjælkelag eller spær på?
2. **Tegloverliggere (R-MUR-02):** Egernsunds montagevejledning kræver ½ sten vederlag under 1 m, 1 sten op til 2 m og 1½ sten derover, men bæreevnediagrammerne forudsætter 228 mm. Hvilket vederlag bruger I i praksis? Hvor stor en lysning laver I uden ingeniør?
3. **Små huller (R-MUR-03):** Hvor stort et hul (fx kerneboring til ventilation eller rør) laver I i en bærende væg uden ny overligger? Hvor tæt på en åbning eller et vederlag må det sidde?
4. **Ny dør i bærende indervæg:** Hvornår laver I selv en dør i en bærende ½-stens- eller 1-stens-væg, og hvornår skal der en ingeniør på?
5. **Midlertidig understøtning (R-MUR-08):** Hvordan understøtter I ved en ny åbning – nåle eller stempler, hvilken afstand og størrelse, og hvornår er det nok med et stempel under bjælkelaget?
6. **Understøbning (R-MUR-07):** Hvor lange etaper understøber I ad gangen, i hvilken rækkefølge, og hvornår kræver I en ingeniør eller geotekniker?
7. **Riller (R-MUR-05/06):** Tabellerne er nu verificeret. Følger I dem, eller har I en enklere tommelfingerregel? Hvornår siger I nej til en vandret rille?
8. **Ikke-bærende væg (R-MUR-01):** Hvad tjekker I, før I river en væg ned, som "ikke er bærende"? Hvad har overrasket jer?
9. **Grænsen:** Hvad er de tre-fire situationer, hvor I altid siger "det skal en ingeniør se på"?

## Ingeniør (konstruktioner)
10. **Stålbjælker (R-STAT-07):** Har I en tommelfingerregel eller tabel for IPE/HEB over en åbning i en bærende væg i et 1–2-etagers hus med træbjælkelag (fx spænd op til 3 m)? Hvornår skal det regnes?
11. **Træbjælkelag (R-STAT-05):** Lillehedens limtrætabel dækker GL30c. Hvilke spænd bruger I uden beregning for C24-bjælker i bolig (dimension, afstand)? Kender I en dansk spændtabel for C24, der må henvises til?
12. **Vederlag og punktlast (R-STAT-02):** Hvornår er en punktlast fra en ny bjælke på eksisterende murværk så lille, at I ikke regner vederlag og fundament?
13. **Stempler (R-STAT-06):** Hvilken stempelafstand er standard ved en ny åbning under et almindeligt træbjælkelag? Regner I stempellasten, eller er der en fast praksis (fx Eurex 20 for hver x m)?
14. **Ikke-bærende væg (R-STAT-04):** Hvornår godkender I, at en væg er ikke-bærende ud fra en screening uden at åbne? Hvilke indikatorer er afgørende?
15. **Dokumentation i KK1 (R-STAT-01):** Vejledningen til BR18 kap. 28 § 3.1 siger, at dokumentationen ikke alene må bygge på produktspecifik dokumentation. Hvad er det mindste, I vil levere for en standardåbning i et parcelhus ud over producentens tabel?
16. **Grænsen:** Hvilke situationer i parcelhuse ser I oftest blive overdimensioneret eller overregnet – og hvilke bliver undervurderet?

## Sådan tilføjes eller opdateres en række
Rammerne virker, selv om rækker mangler: en række med **T** eller **P – mangler** er ikke en ramme, og agenten bruger da den normale arbejdsgang. Rækker kan derfor udfyldes én ad gangen.
- **P** skrives kun efter svar fra en fagperson, aldrig af en agent alene: `P – <rolle>, <ÅÅÅÅ-MM-DD>` (fx `P – murermester, 2026-11-02`), eventuelt efterfulgt af kilden.
- **V** kræver en primærkilde og dato: `V <ÅÅÅÅ-MM-DD> – <kilde>`.
- Ny standardsituation: tilføj en række med næste ledige ID. ID'er omnummereres aldrig, og en udgået række får status `P – mangler` i stedet for at blive slettet. Agenternes videnslog foreslår kandidater som "Ramme-kandidat: …".
- Kør `python3 scripts/check_frames.py` (indgår i `scripts/validate.py`). Det tjekker format, status og ID'er.
