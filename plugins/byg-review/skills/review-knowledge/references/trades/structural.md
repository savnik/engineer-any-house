# Kontrol – statiker

**rubric_version:** `kontrol-statik@1.3` (2026-10-24)

## Kontrolpunkter (typisk klasse ved afvigelse)
1. **Mandat:** leverancen fremstår ikke som statisk dokumentation til byggesagen. Hvert beregnet tal er mærket "OVERSLAG – skal eftervises af den ansvarlige statiker", og det er angivet, hvem der skal udarbejde dokumentationen (statiker, certificeret statiker efter konstruktionsklassen, geotekniker) (kritisk).
2. **Myndighed:** tilladelse eller undtagelse, konstruktionsklasse og krav til statisk dokumentation korrekt efter aktuel BR18 – også at kravene til bærende konstruktioner gælder ved ombygning uden tilladelse (væsentlig–kritisk).
3. **Lastvej til jord:** vederlag, pille/søjle, punktlast på underlag og fundament er vurderet – ikke kun bjælken (kritisk).
4. **Stabilitet:** afstivende vægge, hanebånd og spærfod er vurderet, når de ændres eller fjernes (kritisk).
5. **Midlertidig understøtning og rækkefølge** er beskrevet for ethvert indgreb i bærende dele (kritisk).
6. **Laster og koefficienter:** nyttelast, sne, egenlast, KFI og partialkoefficienter svarer til DK NA og er kildebelagt; egenlaster af eksisterende konstruktioner er undersøgt eller markeret som antagelse (væsentlig).
7. **Al regning med værktøjerne:** hvert beregnet tal (også summer, opland og omregninger) stammer fra en kørsel af `fem.py` eller `statik.py`, hvis kommando og resultat står i bilaget. **Snitkræfter, reaktioner og nedbøjninger kommer fra FEM-modellen** (`<sagsmappe>/fem/fem.yaml`, spec-sha i bilaget, ligevægt OK), og mindst ét afgørende resultat er håndkontrolleret med `statik.py` (afvigelse over 2 % forklaret). Kontrollen genkører de afgørende kommandoer og regner med egne input, hvor de er uenige – aldrig i hovedet. Et tal uden kørsel er væsentligt; en afvigelse over ca. 5 % i et afgørende resultat er væsentlig–kritisk. **Undtagelse:** et svar inden for en ramme i structural-knowledge `frames.md` kræver ingen kørsel – kontrollér rammen efter kontrolprotokollens afsnit 5b.
13. **Rammer:** henviser leverancen til en ramme (`R-STAT-…`, `R-MUR-…`), så er hver betingelse opfyldt, og ligger fundament, stabilitet og punktlaster, som rammen ikke dækker, uden for svaret eller er vurderet (kritisk, hvis en ramme bruges, hvor en betingelse ikke er opfyldt).
8. **Deformation:** nedbøjningskrav er valgt, så de efterfølgende overflader tåler det (fliser, gips, døre) (væsentlig).
9. **Eksisterende forhold:** antagelser om dimensioner, materialer, råd og fundament er markeret og knyttet til et hold point for afdækning (HP-STAT-1), før endelig dimensionering (væsentlig).
10. **Skader:** revner og sætninger er klassificeret, og der er plan for overvågning, før der udbedres; aktive sætninger henvises til geotekniker (væsentlig).
11. **Grænseflader:** brand (bærende dele med brandkrav), føringsveje gennem bærende dele, murer- og tømrerudførelse, geoteknik (væsentlig).
12. **Betonskader:** det er afgjort, om den skadede del er bærende, og hvad der ligger på den; dybden er vurderet mod tværsnittet; mekanismen er sandsynliggjort eller sat på prøve; vandkilden er adresseret før reparation; udfaldet (overfladisk / lokal konstruktiv / sætning) og den udførende er angivet; reparationsmaterialets klasse (DS/EN 1504-3) passer til udfaldet; aktive revner lukkes ikke (væsentlig – kritisk, når en bærende del under åbning eller vederlag behandles som overfladisk).

## Fejlkatalog
- Bjælken eftervist, men vederlag, pille og fundament ikke – punktlast på strøgulv eller smalt gammelt fundament.
- "Ikke-bærende" væg, der var stabiliserende; fjernede hanebånd uden ny trækforbindelse.
- Overslag uden mærkning, brugt som udførelsesgrundlag.
- Tal regnet i hovedet (summer, opland, omregning) i stedet for med værktøjet – regnefejl i lastopgørelsen slår igennem i alt efterfølgende.
- FEM-model med forkert understøtning (rulle i begge ender, indspænding hvor der kun er vederlag), lasten på det forkerte element eller i forkert retning, eller linjelast angivet som vandret projektion på et skråt element – tjek `fem.yaml` og `model`-billedet, ikke kun tallene.
- Forkert lastniveau: nyttelast eller sne fra en anden norm eller et andet land; KFI glemt; egenlast af gammelt bjælkelag med lerindskud undervurderet.
- Kipning af slanke træbjælker og stålbjælker uden afstivet trykflange ikke nævnt.
- Smuldrende beton under vindue eller vederlag behandlet som en pudsreparation; ikke-bærende reparationsmørtel i et bærende tværsnit.
- Revne lukket med injektion eller puds, før det er vist, at den er hvilende.
- Reparation uden at fjerne vandkilden (nedløb, terræn, dræn).
- Rebound-hammer brugt som trykstyrke i gammel, inhomogen beton.
- Udgravning under fundamentets underkant uden etapeplan og underfundering.
- Tømrerens eller leverandørens dimension accepteret uden egen vurdering.

## Primærkilder
bygningsreglementet.dk (BR18 kap. 15 og 26, vejledninger om konstruktioner og statisk dokumentation, nationale annekser), retsinformation.dk, ds.dk (udgaver og metadata for Eurocodes), at.dk (nedrivning og midlertidig afstivning), build.dk, byg-erfa.dk, traeinfo.dk (træ og limtræ – sekundær).
