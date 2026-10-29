---
name: drawing-import
description: >-
  Metode til at importere tegninger (PDF, scanninger, byggesagsarkiv) til husets BIM/IFC-model:
  grundig afkodning af al information på tegningen, modelbygning, uafhængig sammenligning af
  originaltegningen med samme visning tegnet fra modellen, og retur af afvigelser til modelløren,
  indtil der ikke er væsentlige afvigelser (højst 3 sammenligninger pr. leverance) – derefter formel
  kvalitetskontrol. Brug ALTID, når tegninger skal danne grundlag for eller indgå i en BIM- eller
  IFC-model, også gamle kommunale tegninger og arkitekttegninger.
---

# Tegningsimport – afkod → byg → sammenlign → ret → kontrol

Hovedtråden (projektlederen eller Claude) orkestrerer. Fagagenter kalder ikke hinanden.

| Rolle | Agent | Gør |
|---|---|---|
| Orkestrator | hovedtråden | Leverancer, kald i forgrunden, gemmer sammenligninger, stopper loopet, viser brugeren resultatet |
| Modellør | `bim-modeller` | Afkoder tegningen grundigt, bygger/udvider modellen, retter efter afvigelser |
| Sammenligner | `bim-comparer` | Uafhængig: original mod model, finder alle afvigelser og afkodningsfejl. Skrivebeskyttet |
| Kontrol | `bim-review` | Formel, uafhængig kvalitetskontrol – kun når modellen indarbejder andre fags indhold eller er beslutningsgrundlag (se afsnit 5) |

Brug de fulde navne fra din agentliste (`byg-bim:bim-modeller`, `byg-bim:bim-comparer`, `byg-review:bim-review`, eller `byg:…` i den samlede pakke). `BIM="${CLAUDE_PLUGIN_ROOT}/skills/bim-knowledge/scripts/bim.py"`.

## 0. Forberedelse (hovedtråden)
1. Sagsmappe `byg-cases/<sag-id>/` = **ejendommens hovedsag** (BIM-hovedmodellen ligger i hovedsagen, `<sag-id>/bim/model.yaml` – ingen separat BIM-sag) med en kort `project-basis.md` (formål med modellen, LOIN, kilder) – ellers opret den (skill `project-manager`). Undersøger en undersag en ændring af modellen (fx VVS), er den en branch-sag `<sag-id>--<emne>/`, og forslaget oprettes i branchen: `python3 "$BIM" propose byg-cases/<sag-id>/bim/model.yaml <navn> --out byg-cases/<sag-id>--<emne>/bim/proposals` (project-manager `references/case-dir.md`). Første gang på maskinen: `python3 "$BIM" setup`.
2. Kilder: `python3 "$BIM" pdf <fil.pdf> --overview --out byg-cases/<sag-id>/bim/sources` og se kontaktarket. Udvælg tegningssiderne, og giv hver tegning et kilde-id (K1, K2 …). Notér dem i projektgrundlaget.
3. **Én leverance pr. tegning (side) eller pr. etage:** `DELIVERABLE: <sag-id>/bim/<nr>`. Rækkefølge: den plan, der fastlægger husets ydre (oftest stueplanen eller kælderplanen) → de øvrige planer → snit → facader. Første leverance fastlægger origo, akser, etager, koter og typer.

## Kontrolniveau – vælg ved første fagkald
| Leverancen | Niveau | Kontrol |
|---|---|---|
| Ren tegningsimport og geometri (vægge, åbninger, rum, trapper, koter fra tegning, foto eller opmåling) | `REVIEW-LEVEL: tool` | Sammenligneren og `bim.py check`. Hooken godkender, når sammenligningen er `ok`, og `tjek` har 0 fejl og 0 sporbarhed. Ingen `bim-review` |
| Modellen indarbejder andre fags indhold (rør, el, ventilation, bærende dele fra et godkendt fagnotat, kilde K) | `REVIEW-LEVEL: light` | Som værktøj + `bim-review`, som tjekker modellen mod de godkendte fagnotater (rørføring, udeladelser) |
| Modellen er beslutningsgrundlag: arealer til byggesag eller BBR, geometri til statikeren, mængder til tilbud | `REVIEW-LEVEL: light` (`full` ved en sikkerhedsfunktion) | Som ovenfor |

Begrundelse (ARCHITECTURE.md, "Multi-agent-arkitektur"): bim-kontrollens fund i rigtige sager var overvejende kildemærkning, som `bim.py check` nu kontrollerer deterministisk, og modstrid med andre fags notater. Geometrien kontrolleres allerede af sammenligneren og `check`.

## 1. Fagkald: afkodning og modelbygning (forgrund)
```
DELIVERABLE: <sag-id>/bim/<nr>
REVIEW-LEVEL: <tool|light|full>
TASK: drawing-import af K<m> – trin 1 afkodning, trin 2 modelbygning (se "Tegningsimport" i din agentbeskrivelse).
Sagsmappe: byg-cases/<sag-id>/ · Ejendomskort: byg-cases/properties/<property-id>.md
Kilde: <sti til pdf> side <n> → byg-cases/<sag-id>/bim/sources/K<m>/
Visning(er): <fx stueplan 1:100>
Model: byg-cases/<sag-id>/bim/model.yaml (<findes → arbejd i proposals/bim-<nr>.yaml | oprettes>)
Deliverable: byg-cases/<sag-id>/trade-notes/bim-<nr>.md
```
Modelløren afleverer: `decoding.yaml` med `decode check` = 0 fejl, forslagsfilen `bim/proposals/bim-<nr>.yaml` (hovedmodellen er urørt) med `check` = 0 FEJL og modelnotatet. Sammenligning og kontrol kører på forslagets IFC.

## 2. Sammenligning (forgrund)
```
DELIVERABLE: <sag-id>/bim/<nr>
COMPARISON: <n>
Sagsmappe: byg-cases/<sag-id>/
IFC: byg-cases/<sag-id>/bim/out/<property-id>.ifc
Afkodning: byg-cases/<sag-id>/bim/sources/K<m>/decoding.yaml · Visning(er): <V1, …>
Tidligere sammenligninger: <stier til JSON> (kun runde ≥ 2)
```
Giv kun filerne, ikke modellørens ræsonnement. Gem sammenlignerens JSON-blok som `byg-cases/<sag-id>/bim/comparison/K<m>-r<n>.json`, og skriv én linje i `…/comparison/log.md` (første linje i en ny log er feltoverskriften):
```
dato · leverance · runde · resultat · åbne væsentlige/mindre · afkodningsfejl
```

## 3. Retur til modelløren (ved `resultat: ret`)
```
DELIVERABLE: <sag-id>/bim/<nr>
RETURN: comparison <n>
Sagsmappe: byg-cases/<sag-id>/
Afvigelser (væsentlige og afkodningsfejl, ordret JSON): <…>
Sammenligningsbilleder: byg-cases/<sag-id>/bim/comparison/K<m>-r<n>/
Ret afkodningen først, hvor afvigelsen skyldes en afkodningsfejl, og derefter modellen. Svar pr. afvigelse:
lukket eller bestridt (med evidens fra originalen). Opdatér "Kontrolrespons" i modelnotatet.
```
Send ikke de mindre afvigelser retur, medmindre de er trivielle at lukke. Kald derefter sammenligning n+1 med de tidligere JSON'er.

## 4. Stopkriterier
- **`resultat: ok`** (ingen åbne væsentlige afvigelser) → trin 5.
- **3 sammenligninger nået** (hooken afviser den 4.): stop loopet. Resterende afvigelser skal stå i modelnotatet under "Afvigelser og usikkerheder" med status. Afvigelser af typen `tegning_inkonsistent` eller ulæselige steder går på **opmålingslisten**: spørg brugeren, om de kan måles på stedet, i stedet for at gætte. Er den samme afvigelse ikke blevet lukket i 3 runder, så skriv en kort årsagsnote (værktøj, afkodning eller tegning) og en kandidat til `references/lessons.md`.
- **Bestridt afvigelse:** sammenligneren tager stilling i næste runde. Er den stadig bestridt, så vis brugeren udsnittet fra originalen og modellen, og lad brugeren afgøre den.

## 5. Formel kontrol (kun `light`/`full`)
Ved `REVIEW-LEVEL: tool` er leverancen godkendt, når hooken har registreret sammenligningen med `resultat: ok` og et rent `tjek` – gå direkte til afsnit 6. Når 3 sammenligninger er brugt uden et rent resultat, eller modellen undervejs har fået andre fags indhold, så kør den formelle kontrol nedenfor.
1. Kør selv den deterministiske kontrol i hovedtråden: `python3 "$BIM" check <ifc> --draw --out byg-cases/<sag-id>/quality/bim-<nr>-check`.
2. Kald `bim-review` efter skill `quality-review`: `DELIVERABLE: <id>`, modelnotatet, tjek-rapporten, sammenligningernes JSON, afkodningen og forslagsfilen (`bim/proposals/bim-<nr>.yaml`, bygget oven på `model.yaml`). `REVIEW-LEVEL: light`, medmindre modellen fastlægger en sikkerhedsfunktion.
3. Afvisning følger kvalitetskontrollens loop. Kør kun en ny sammenligning, hvis rettelsen ændrer geometri eller afkodede mål. Rene egenskabsrettelser (kilde, IsExternal, typenavne, notat) kræver ingen ny sammenligning. Kontrollen ser dem i `check` og modelnotatet.

## 6. Efter godkendelse
- Vis brugeren `overlay.png` fra sidste sammenligning, en plan og 3D-visningen. Fortæl andelen af elementer med kilde A og opmålingslisten.
- **Flet ind:** `python3 "$BIM" merge byg-cases/<sag-id>/bim/proposals/bim-<nr>.yaml --note "bim/<nr> godkendt"`. Fletningen stopper, hvis hovedmodellen siden er ændret i de samme elementer – så opdaterer modelløren forslaget, og kontrollen ser ændringen igen. Byg og `check` derefter hovedmodellen (0 FEJL).
- Projektlederen opdaterer ejendomskortet (er det genereret fra hovedmodellen: i samme forslag som leverancen, under `fakta:`): `BIM-model: <sti til model.yaml og IFC>, version/dato, LOIN, kilder K1–Kn`.
- Næste tegning bliver næste leverance (`<nr>+1`) i samme model.

## Effektivitet
- Små leverancer (én side eller én etage) holder agenternes kontekst lille. Typisk forløb: 1 fagkald, 1–2 sammenligninger og 1–2 kontrolforsøg pr. side. Målt på en enkel plan: ca. 20 minutter i alt.
- Hovedtråden læser kun resuméer og JSON, aldrig fliserne. Det er sammenlignerens arbejde.
- Kald agenterne i forgrunden, én ad gangen. Hvert trin afhænger af det forrige.
