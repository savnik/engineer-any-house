---
name: tegningsimport
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
| Modellør | `bim-modelloer` | Afkoder tegningen grundigt, bygger/udvider modellen, retter efter afvigelser |
| Sammenligner | `bim-sammenligner` | Uafhængig: original mod model, finder alle afvigelser og afkodningsfejl. Skrivebeskyttet |
| Kontrol | `bim-kontrol` | Formel, uafhængig kvalitetskontrol – kun når modellen indarbejder andre fags indhold eller er beslutningsgrundlag (se afsnit 5) |

Brug de fulde navne fra din agentliste (`byg-bim:bim-modelloer`, `byg-bim:bim-sammenligner`, `byg-kontrol:bim-kontrol`, eller `byg:…` i den samlede pakke). `BIM="${CLAUDE_PLUGIN_ROOT}/skills/bim-viden/scripts/bim.py"`.

## 0. Forberedelse (hovedtråden)
1. Sagsmappe `byg-sager/<sag-id>/` = **ejendommens hovedsag** (BIM-hovedmodellen ligger i hovedsagen, `<sag-id>/bim/model.yaml` – ingen separat BIM-sag) med en kort `projektgrundlag.md` (formål med modellen, LOIN, kilder) – ellers opret den (skill `projektleder`). Undersøger en undersag en ændring af modellen (fx VVS), er den en branch-sag `<sag-id>--<emne>/`, og forslaget oprettes i branchen: `python3 "$BIM" forslag byg-sager/<sag-id>/bim/model.yaml <navn> --ud byg-sager/<sag-id>--<emne>/bim/forslag` (projektleder `references/sagsmappe.md`). Første gang på maskinen: `python3 "$BIM" opsaet`.
2. Kilder: `python3 "$BIM" pdf <fil.pdf> --oversigt --ud byg-sager/<sag-id>/bim/kilder` og se kontaktarket. Udvælg tegningssiderne, og giv hver tegning et kilde-id (K1, K2 …). Notér dem i projektgrundlaget.
3. **Én leverance pr. tegning (side) eller pr. etage:** `LEVERANCE: <sag-id>/bim/<nr>`. Rækkefølge: den plan, der fastlægger husets ydre (oftest stueplanen eller kælderplanen) → de øvrige planer → snit → facader. Første leverance fastlægger origo, akser, etager, koter og typer.

## Kontrolniveau – vælg ved første fagkald
| Leverancen | Niveau | Kontrol |
|---|---|---|
| Ren tegningsimport og geometri (vægge, åbninger, rum, trapper, koter fra tegning, foto eller opmåling) | `KONTROLNIVEAU: værktøj` | Sammenligneren og `bim.py tjek`. Hooken godkender, når sammenligningen er `ok`, og `tjek` har 0 fejl og 0 sporbarhed. Ingen `bim-kontrol` |
| Modellen indarbejder andre fags indhold (rør, el, ventilation, bærende dele fra et godkendt fagnotat, kilde K) | `KONTROLNIVEAU: let` | Som værktøj + `bim-kontrol`, som tjekker modellen mod de godkendte fagnotater (rørføring, udeladelser) |
| Modellen er beslutningsgrundlag: arealer til byggesag eller BBR, geometri til statikeren, mængder til tilbud | `KONTROLNIVEAU: let` (`fuld` ved en sikkerhedsfunktion) | Som ovenfor |

Begrundelse (ARKITEKTUR.md, "Multi-agent-arkitektur"): bim-kontrollens fund i rigtige sager var overvejende kildemærkning, som `bim.py tjek` nu kontrollerer deterministisk, og modstrid med andre fags notater. Geometrien kontrolleres allerede af sammenligneren og `tjek`.

## 1. Fagkald: afkodning og modelbygning (forgrund)
```
LEVERANCE: <sag-id>/bim/<nr>
KONTROLNIVEAU: <værktøj|let|fuld>
OPGAVE: Tegningsimport af K<m> – trin 1 afkodning, trin 2 modelbygning (se "Tegningsimport" i din agentbeskrivelse).
Sagsmappe: byg-sager/<sag-id>/ · Ejendomskort: byg-sager/ejendomme/<ejendom-id>.md
Kilde: <sti til pdf> side <n> → byg-sager/<sag-id>/bim/kilder/K<m>/
Visning(er): <fx stueplan 1:100>
Model: byg-sager/<sag-id>/bim/model.yaml (<findes → arbejd i forslag/bim-<nr>.yaml | oprettes>)
Leverance: byg-sager/<sag-id>/fagnotater/bim-<nr>.md
```
Modelløren afleverer: `afkodning.yaml` med `afkod tjek` = 0 fejl, forslagsfilen `bim/forslag/bim-<nr>.yaml` (hovedmodellen er urørt) med `tjek` = 0 FEJL og modelnotatet. Sammenligning og kontrol kører på forslagets IFC.

## 2. Sammenligning (forgrund)
```
LEVERANCE: <sag-id>/bim/<nr>
SAMMENLIGNING: <n>
Sagsmappe: byg-sager/<sag-id>/
IFC: byg-sager/<sag-id>/bim/ud/<ejendom-id>.ifc
Afkodning: byg-sager/<sag-id>/bim/kilder/K<m>/afkodning.yaml · Visning(er): <V1, …>
Tidligere sammenligninger: <stier til JSON> (kun runde ≥ 2)
```
Giv kun filerne, ikke modellørens ræsonnement. Gem sammenlignerens JSON-blok som `byg-sager/<sag-id>/bim/sammenligning/K<m>-r<n>.json`, og skriv én linje i `…/sammenligning/log.md` (første linje i en ny log er feltoverskriften):
```
dato · leverance · runde · resultat · åbne væsentlige/mindre · afkodningsfejl
```

## 3. Retur til modelløren (ved `resultat: ret`)
```
LEVERANCE: <sag-id>/bim/<nr>
RETUR: sammenligning <n>
Sagsmappe: byg-sager/<sag-id>/
Afvigelser (væsentlige og afkodningsfejl, ordret JSON): <…>
Sammenligningsbilleder: byg-sager/<sag-id>/bim/sammenligning/K<m>-r<n>/
Ret afkodningen først, hvor afvigelsen skyldes en afkodningsfejl, og derefter modellen. Svar pr. afvigelse:
lukket eller bestridt (med evidens fra originalen). Opdatér "Kontrolrespons" i modelnotatet.
```
Send ikke de mindre afvigelser retur, medmindre de er trivielle at lukke. Kald derefter sammenligning n+1 med de tidligere JSON'er.

## 4. Stopkriterier
- **`resultat: ok`** (ingen åbne væsentlige afvigelser) → trin 5.
- **3 sammenligninger nået** (hooken afviser den 4.): stop loopet. Resterende afvigelser skal stå i modelnotatet under "Afvigelser og usikkerheder" med status. Afvigelser af typen `tegning_inkonsistent` eller ulæselige steder går på **opmålingslisten**: spørg brugeren, om de kan måles på stedet, i stedet for at gætte. Er den samme afvigelse ikke blevet lukket i 3 runder, så skriv en kort årsagsnote (værktøj, afkodning eller tegning) og en kandidat til `references/erfaringsblade.md`.
- **Bestridt afvigelse:** sammenligneren tager stilling i næste runde. Er den stadig bestridt, så vis brugeren udsnittet fra originalen og modellen, og lad brugeren afgøre den.

## 5. Formel kontrol (kun `let`/`fuld`)
Ved `KONTROLNIVEAU: værktøj` er leverancen godkendt, når hooken har registreret sammenligningen med `resultat: ok` og et rent `tjek` – gå direkte til afsnit 6. Når 3 sammenligninger er brugt uden et rent resultat, eller modellen undervejs har fået andre fags indhold, så kør den formelle kontrol nedenfor.
1. Kør selv den deterministiske kontrol i hovedtråden: `python3 "$BIM" tjek <ifc> --tegn --ud byg-sager/<sag-id>/kvalitet/bim-<nr>-tjek`.
2. Kald `bim-kontrol` efter skill `kvalitetskontrol`: `LEVERANCE: <id>`, modelnotatet, tjek-rapporten, sammenligningernes JSON, afkodningen og forslagsfilen (`bim/forslag/bim-<nr>.yaml`, bygget oven på `model.yaml`). `KONTROLNIVEAU: let`, medmindre modellen fastlægger en sikkerhedsfunktion.
3. Afvisning følger kvalitetskontrollens loop. Kør kun en ny sammenligning, hvis rettelsen ændrer geometri eller afkodede mål. Rene egenskabsrettelser (kilde, IsExternal, typenavne, notat) kræver ingen ny sammenligning. Kontrollen ser dem i `tjek` og modelnotatet.

## 6. Efter godkendelse
- Vis brugeren `overlay.png` fra sidste sammenligning, en plan og 3D-visningen. Fortæl andelen af elementer med kilde A og opmålingslisten.
- **Flet ind:** `python3 "$BIM" flet byg-sager/<sag-id>/bim/forslag/bim-<nr>.yaml --note "bim/<nr> godkendt"`. Fletningen stopper, hvis hovedmodellen siden er ændret i de samme elementer – så opdaterer modelløren forslaget, og kontrollen ser ændringen igen. Byg og `tjek` derefter hovedmodellen (0 FEJL).
- Projektlederen opdaterer ejendomskortet (er det genereret fra hovedmodellen: i samme forslag som leverancen, under `fakta:`): `BIM-model: <sti til model.yaml og IFC>, version/dato, LOIN, kilder K1–Kn`.
- Næste tegning bliver næste leverance (`<nr>+1`) i samme model.

## Effektivitet
- Små leverancer (én side eller én etage) holder agenternes kontekst lille. Typisk forløb: 1 fagkald, 1–2 sammenligninger og 1–2 kontrolforsøg pr. side. Målt på en enkel plan: ca. 20 minutter i alt.
- Hovedtråden læser kun resuméer og JSON, aldrig fliserne. Det er sammenlignerens arbejde.
- Kald agenterne i forgrunden, én ad gangen. Hvert trin afhænger af det forrige.
