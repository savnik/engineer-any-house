# BIM-modellør – faglig praksis

Værdier markeret **(T)** er typiske branche- eller erfaringsværdier, ikke krav.

## Formål → detaljeringsniveau (LOIN)
Fastlæg formålet først. Det afgør, hvad der modelleres (ISO 7817-1 "Level of Information Need": geometri, information og dokumentation efter formål).

| Formål | Geometri | Information |
|---|---|---|
| **Eksisterende forhold (opmåling) – standard** | Vægge med lag, dæk, tag, åbninger, trapper, skorsten, søjler/bjælker der ses eller er kendt, rum | Status EXISTING, kilde og usikkerhed, materialer, IsExternal/LoadBearing hvor kendt, rumnavne og arealer |
| Renoveringsprojekt (fx kælderisolering) | Som ovenfor + nye/nedrevne dele i projektområdet | Status NEW/DEMOLISH, U-værdier, henvisning til fagnotat |
| Installationer (VVS/el/ventilation) | Komponenter som kasse/cylinder i rigtig størrelse og placering, rør med diameter | System, producent/model, typeskilt |
| Mængder/tilbud | Som opmåling, men med kendte lagtykkelser | Qto (beregnes af værktøjet) |

Modellér ikke spær, lægter, armering, møbler, fliser, lister eller terræn uden et formål. Hvert ekstra element skal have én linje med begrundelse (fælles protokol, afsnit 3).

## Koordinater, origo og koter
- Origo: et veldefineret ydre hjørne (yderside af murværk), som kan genfindes på tegninger og på stedet. +x langs gadefacaden.
- ±0 = færdigt gulv i stueetagen. Etagekoter relativt til ±0. Etagehøjde = gulv til gulv.
- Georeference (`model.geo`): EPSG:25832 (ETRS89/UTM32N) for origo og DVR90-koten for ±0. Koordinater kan tages fra matrikelkort, bygningens adgangspunkt eller landmåler. Er de omtrentlige, så kilde A i modelnotatet.
- `x_retning`: kompasretningen af +x (fx 100° = mod ØSØ). Kan aflæses af nordpilen på tegningen eller af et ortofoto.

## Mål og tolerancer
- Kildehierarki: påskrevet mål (D) > målt på stedet (M) > skaleret fra tegning (D, `usikkerhed`) > foto/skøn (A).
- Tolerancer (T): påskrevne mål ±50 mm i sammenligningen. Opmåling med laser ±10 mm. Skalering fra 1:100-scanning ±3 px × skala (typisk 30–60 mm).
- Gamle tegninger er råhusmål til murværk. Pudslag (10–20 mm (T)) indgår i lagopbygningen, ikke i væggens placering.
- Bruttoareal (BBR) måles til ydervæggenes yderside. `tjek` sammenligner med `model.kontrol.areal`. Afvigelser over 5 % skal forklares (BBR-fejl, tilbygning, forkert ydermål).

## Modelleringsregler, som giver brugbare modeller
1. **Rigtige klasser:** IfcWall, IfcSlab, IfcRoof (aggregerer tagflader), IfcWindow/IfcDoor i IfcOpeningElement, IfcStair, IfcColumn, IfcBeam, IfcSpace, IfcChimney, VVS-klasser. Proxy er nødudgang.
2. **Typer bærer lagopbygningen.** Forekomsterne har IfcMaterialLayerSetUsage, og samme konstruktion skal have samme type.
3. **Status på alt** (EXISTING/NEW/DEMOLISH/TEMPORARY). Det er grundlaget for renoveringsversioner.
4. **Etagedæk** ligger mellem ydervæggene (kant: inderside af den bærende løkke). Indervægge og søjler slutter under dækket (værktøjets standard).
5. **Rum** findes fra væggene (punkt-rum). Lukker rummet ikke, så mangler der en væg eller en afgrænsning.
6. **Åbninger** placeres ud fra vægsegmentets start. Kontrollér altid i planen (`tegn plan --id`), at de sidder i den rigtige side og væg.
7. **Gennemføringer:** skorsten gennem etagedæk skal have `huller` i dækkene. Rør gennem vægge er info ved LOIN 2.
8. **Ingen persondata** i modellen (ejer, beboere, håndværkere). Arkitektnavne fra tegningen hører til kildelisten, ikke til modellen.

## Arbejdsrytme (effektivitet)
- Én etage eller én tegning ad gangen: byg → tjek → tegn/sammenlign → ret. Små spec-ændringer og hurtige genbygninger (< 1 s).
- Læs udskrifterne. Åbn kun `tjek.md` eller `auto.md`, når udskriften henviser dertil. Læs kun de PNG'er, der skal bruges til en beslutning (planen for den etage, du arbejder på, og overlay).
- Ret spec'en med Edit (små ændringer) frem for at skrive hele filen igen.
- Gentag ikke værktøjets arbejde i hovedet: arealer, mængder og mål beregnes af værktøjet.

## Leverancer til fagfolk
- IFC4-fil fra `ud/` + `tjek.md` + tegninger (PNG) + modelnotat (kilder, LOIN, usikkerheder).
- Upload til validate.buildingsmart.org før aflevering. Fejl dér skal rettes eller forklares.
- Modtagerens ønsker går forud: IFC2X3 eller IFC4X3 efter aftale (IFC2X3 kræver konvertering med ifcpatch, se `rediger.md`), klassifikation (BIM7AA/BIMTypeCode, CCS/CCI) som `klassifikation`/`egenskaber` på typerne.
