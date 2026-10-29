# Kontrol – BIM

**rubric_version:** `kontrol-bim@1.0` (2026-10-11)

## Kontrolpunkter (typisk klasse ved afvigelse)
1. **Kildegrundlag og sporbarhed:** hvert element har kilde (D/M/F/B/K/A) og ref. Påskrevne mål er brugt frem for skalering. Andelen med kilde A står i konklusionen. Usikre steder og `tegning_inkonsistent` er på opmålingslisten (væsentlig).
2. **Tegningsimport:** afkodning med `decode check` = 0 fejl og kalibreringsrest ≤ 40 mm. Uafhængig sammenligning er udført, og resultatet er `ok`, eller resterende væsentlige afvigelser er forklaret, og brugeren er spurgt (væsentlig). Ingen sammenligning udført = væsentlig.
3. **Gyldig IFC:** `check` med 0 FEJL (skema/EXPRESS, SPS/GEM/PSE/QTY/GRF-regler, geometri, kollisioner). Advarsler forklaret. IDS `byg-bolig.ids` bestået. IFC4, medmindre andet er aftalt (væsentlig).
4. **Geometri mod kilde:** ydermål og bruttoareal mod tegning/BBR (±5 % eller forklaret), etagekoter og -højder, trapper (stigninger × stigning = etagehøjde), åbninger og dørslag mod tegningen (væsentlig).
5. **Semantik:** rigtige klasser (proxy kun med begrundelse), typer med lagopbygning, Status på alt, IsExternal/LoadBearing hvor kendt, rum med navn og areal, georeference (EPSG:25832/DVR90) eller begrundet udeladt (væsentlig–mindre).
6. **Formål og LOIN:** modellen dækker formålet og er ikke overdetaljeret uden grund. Renoveringselementer har NEW/DEMOLISH med henvisning til godkendt fagnotat (væsentlig–mindre).
7. **Mandat:** modellen gengiver kun godkendte fagløsninger og fremstår ikke som myndighedstegning, statik eller landinspektøropmåling (væsentlig).
8. **Persondata og dataseparation:** ingen navne, CPR eller ejeroplysninger i modellen (væsentlig).
9. **Modelnotat:** formål/LOIN, kildeliste, model, kontrol, afvigelser, tegninger, videnslog og kontrolrespons (mindre).

## Fejlkatalog
- Mål "pænt afrundet" uden kilde (fx alle vægge 300/100 mm, rum præcis 4,00 × 3,00 m) og kilde A skjult af `standard: {kilde: A}`.
- Afkodning med punkter på målelinjen uden `paa_maalelinje`, eller kalibrering ud fra skalering i stedet for påskrevne mål.
- Sammenligning kun på automatikken (`auto.md`) uden gennemgang af fliser, så dørslag, manglende skillevægge og trapper overses.
- Døre i forkert side (venstre/højre forvekslet). Vægge uden for huset ved forkert justering.
- Indervægge og søjler gennem etagedæk. Skorsten gennem dæk uden huller.
- IfcSpace contained i stedet for aggregeret. Status som tekst i stedet for enumereret værdi. Egne sæt med "Pset_".
- Georeference med Scale 1 i et mm-projekt (GRF005).
- Model bygget direkte i IfcOpenShell-kode (ikke reproducerbar) eller håndredigeret IFC.

## Primærkilder
buildingSMART: ifc-gherkin-rules (github.com/buildingSMART/ifc-gherkin-rules), IFC4 ADD2 TC1 og IFC 4.3-dokumentation (standards.buildingsmart.org), IDS 1.0 (github.com/buildingSMART/IDS), Validation Service (validate.buildingsmart.org). ISO 7817-1:2024 (LOIN), epsg.io (25832, 5799, 7416), molio.dk (CCS/CCI), bimtypecode.com, retsinformation.dk (IKT-bekendtgørelsen BEK 118/2013).
