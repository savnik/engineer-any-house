# Ændringslog

## 0.15.0 – 2026-10-24

- `byg` 0.11.0 → 0.12.0
- `byg-bim` 0.7.0 → 0.7.1
- `byg-el` 0.2.1 → 0.2.2
- `byg-kontrol` 0.14.0 → 0.15.0
- `byg-maler` 0.1.10 → 0.1.11
- `byg-murer` 0.1.10 → 0.2.0
- `byg-statik` 0.3.4 → 0.4.0
- `byg-team` 0.3.0 → 0.4.0
- `byg-toemrer` 0.1.10 → 0.1.11
- `byg-ventilation` 0.1.11 → 0.1.12
- `byg-vvs` 0.2.1 → 0.2.2

### anlaeg (byg, byg-kontrol, byg-team)
Ny fagagent `anlaegsgartner` (plugin `byg-anlaeg` 0.1.0): belægning og terrasser (opbygning, fald væk fra huset, fri sokkel, træterrasser), regnvand og LAR (faskine, nedsivningstest, afstandskrav og tilladelse), terrænfald og omfangsdræn, terrænregulering og støttemure, hegn og hække (hegnsloven), træer, beplantning og pleje. Kloakarbejde henvises til autoriseret kloakmester. Ny kontrolagent `anlaeg-kontrol` med rubric `kontrol-anlaeg@1.0`, hold points HP-ANL, projektlederens fagvalg, koordinering og definition of ready udvidet, og `byg-team` installerer anlægsgartneren.

### arkitekt (byg, byg-kontrol, byg-team)
Ny fagagent `arkitekt` (plugin `byg-arkitekt` 0.1.0): rådgivende om planløsning og disposition, tilbygning, kvist, tagetage og facade samt myndighedsscreening (byggetilladelse eller undtagelse efter BR18 § 5, byggeret, etageareal og bebyggelsesprocent, højde og afstand til skel, lokalplan, servitutter, bevaring). Beskriver planen til BIM-forslag via `bim-modelloer`. Ny kontrolagent `arkitekt-kontrol` med rubric `kontrol-arkitekt@1.0`, hold points HP-ARK, projektlederens fagvalg og definition of ready udvidet, og `byg-team` installerer arkitekten.

### forsoeg-F-023-ce-snelast (byg-statik)
Statik-videnbasen har nu eksponeringsfaktoren C_e for snelast efter DS/EN 1991-1-3 DK NA:2024 5.2(7): C_e = C_top·C_s, og afskærmet terræn giver 1,25. Den erstatter grundstandardens tabel 5.1 (F-023).

### rammer-standardloesninger (byg, byg-bim, byg-el, byg-kontrol, byg-maler, byg-murer, byg-statik, byg-toemrer, byg-ventilation, byg-vvs)
Rammer for standardløsninger (pilot på murer og statik): ny `rammer.md` i murer-viden og statik-viden med standardsituationer, betingelser og kildestatus V/T/P (P = anerkendt praksis godkendt af en fagperson). Fælles protokol har fået triage som første skridt: inden for en ramme svarer fagagenten kort uden beregning og uden fuldt fagnotat. Statikerens FEM-krav gælder kun på grænsen af eller uden for en ramme. Kontrollen godtager en ramme som dokumentation, når betingelserne er opfyldt, og rejser "overkompliceret" som mindre fund. Spørgeliste til fagfolk i `faelles/rammer-spoergeliste.md`. Rammerne er udfyldt med primærkilder, hvor de findes (V 2026-10-24): Egernsund tegloverliggere, nyt armeret stik med Sika Murma (R-MUR-09), EN 1996-1-1 § 8.6 for riller med alle noter, Lilleheden limtræ GL30c, ny H+H porebetonbjælke (R-STAT-08), Doka-stempler og BEK 2107 om midlertidig understøtning. Vejledningen til BR18 kap. 28 § 3.1 er skrevet ind: en producenttabel er ikke alene dokumentation, men kræver en redegørelse for, at forudsætningerne passer. Uarmeret stik, kerneboring, understøbning, stempelafstand, C24 og IPE/HEB er fortsat P – mangler. Rammerne virker med huller: rækker med T eller P – mangler er ikke rammer, og agenten bruger den normale arbejdsgang uden at nævne det. Manglende ramme er aldrig et kontrolfund, og "overkompliceret" rejses kun ved V- og P-rækker. Agenten skriver "Ramme-kandidat: …" i videnslog, når en standardsituation mangler en række. Nyt `scripts/tjek_rammer.py` (i `valider.py`) tjekker format, status og ID'er, så rækker kan tilføjes over tid.

## 0.14.0 – 2026-10-20

- `byg` 0.10.1 → 0.11.0
- `byg-bim` 0.6.0 → 0.7.0
- `byg-kontrol` 0.13.0 → 0.14.0

### sager-som-branches (byg, byg-bim, byg-kontrol)
Sager som branches: `byg-sager/` holder kun permanente data (hovedsager, aktive branch-sager `<hovedsag>--<emne>/`, `ejendomme/`, `arkiv/`). Spørgsmål opretter ingen sagsmappe – midlertidige filer i `~/byg-tmp/` (gaten finder sager og RCA'er der og håndhæver én skriver pr. fil). BIM-hovedmodellen ligger i hovedsagen; en branch-sag har sine forslag lokalt (`bim.py forslag … --ud <branch>/bim/forslag`, basis relativ med sha256) og flettes ind ved godkendelse.

## 0.13.0 – 2026-10-20

- `byg` 0.10.0 → 0.10.1
- `byg-bim` 0.5.1 → 0.6.0
- `byg-kontrol` 0.12.0 → 0.13.0

### bim-kontrol-slank (byg, byg-bim, byg-kontrol)
BIM: `bim.py tjek` kontrollerer sporbarhed (kilde uden reference, K uden leverance-ID, A uden usikkerhed, `--notat` for modelnotatets andel af kilde A). Nyt kontrolniveau `værktøj` for ren tegningsimport og geometri: hooken godkender leverancen, når bim-sammenligneren melder `resultat: ok` og et rent `tjek`, uden bim-kontrol. bim-kontrol bruges, når modellen indarbejder andre fags indhold eller er beslutningsgrundlag.

## 0.12.0 – 2026-10-20

- `byg` 0.9.0 → 0.10.0
- `byg-bim` 0.5.0 → 0.5.1
- `byg-el` 0.2.0 → 0.2.1
- `byg-kontrol` 0.11.0 → 0.12.0
- `byg-maler` 0.1.9 → 0.1.10
- `byg-murer` 0.1.9 → 0.1.10
- `byg-statik` 0.3.3 → 0.3.4
- `byg-toemrer` 0.1.9 → 0.1.10
- `byg-ventilation` 0.1.10 → 0.1.11
- `byg-vvs` 0.2.0 → 0.2.1

### multiagent-forskning (byg, byg-bim, byg-el, byg-kontrol, byg-maler, byg-murer, byg-statik, byg-toemrer, byg-ventilation, byg-vvs)
Domæneforrang ved konflikter mellem fag (ejerfaget har forrang, ingen mellemløsninger) med to nye eval-cases. Nyt kontrolniveau `stikprøve` for enkeltstående fagspørgsmål uden sag (aldrig el, statik eller sikkerhedsfunktioner): hooken udtager ca. hver tredje. Kildedisciplin i de fælles protokoller: "efterprøvet" kun ved eget opslag, og kontrollen bedømmer reglen, ikke påstanden. Udvikling: kontrol-armen `scripts/kontrol_ab.py`. Baggrund og målinger i ARKITEKTUR.md, "Multi-agent-arkitektur i lyset af forskningen".

## 0.11.0 – 2026-10-18

- `byg-el` 0.1.14 → 0.2.0
- `byg-vvs` 0.1.10 → 0.2.0

### eksamen-huller (byg-el, byg-vvs)
Videnbasen udbygget ud fra eksamenslagets huller (udviklingssættet), efterprøvet mod primærkilder. **El:** centrale krav i installationsbekendtgørelsen (RCD ≤ 30 mA, type AC forbudt i boliger, 13 A foran 10/13 A-stikkontakter, beskyttelsesleder ved udvidelse, tavleplacering og -flytning), ejerens ansvar (elsikkerhedsloven § 10), Fællesregulativets Ik min og Ik max samt tilslutning af solceller. Gør-det-selv-reglen er rettet: udskiftning af stikkontakter kræver HFI/HPFI, også uden jord (BEK 560/2017 § 1). **VVS:** fyringsanlæg og aftræk (BR18 kap. 12: temperaturklasser, lysningsareal, undertryk), eftersyn af gasinstallationer (BEK 247/2018: CO ≤ 500 ppm, fejl udbedres før afslutning), jordvarme (BEK 240/2017 med ændring 2025) og forbuddet mod rørgennemføringer i gulvet i den vandbelastede del (BR18 § 339).

## 0.10.0 – 2026-10-18

- `byg` 0.8.0 → 0.9.0
- `byg-bim` 0.4.2 → 0.5.0
- `byg-el` 0.1.13 → 0.1.14
- `byg-kontrol` 0.10.0 → 0.11.0
- `byg-maler` 0.1.8 → 0.1.9
- `byg-murer` 0.1.8 → 0.1.9
- `byg-statik` 0.3.2 → 0.3.3
- `byg-toemrer` 0.1.8 → 0.1.9
- `byg-ventilation` 0.1.9 → 0.1.10
- `byg-vvs` 0.1.9 → 0.1.10

### token-effektivitet (byg, byg-bim, byg-el, byg-kontrol, byg-maler, byg-murer, byg-statik, byg-toemrer, byg-ventilation, byg-vvs)
Tokenbudget: workflows i byg-sager kun på brugerens udtrykkelige ønske (hook); kontrolagenter og bim-sammenligner på Sonnet, `KONTROLNIVEAU: fuld` kræver `model: opus`; højst 2 forsøg pr. runde og eskalering til brugeren, ny runde med RCA kun efter `Ny runde <id>` (højst 2 runder); `maxTurns` på alle agenter; fælles "Tokenbudget"-regler for fag- og kontrolagenter; projektlederen spørger efter 3 fagleverancer i samme sag; status-skillen læser mindre.

## 0.9.0 – 2026-10-16

- `byg` 0.7.2 → 0.8.0
- `byg-bim` 0.4.1 → 0.4.2
- `byg-el` 0.1.12 → 0.1.13
- `byg-kontrol` 0.9.1 → 0.10.0
- `byg-maler` 0.1.7 → 0.1.8
- `byg-murer` 0.1.7 → 0.1.8
- `byg-statik` 0.3.1 → 0.3.2
- `byg-toemrer` 0.1.7 → 0.1.8
- `byg-ventilation` 0.1.8 → 0.1.9
- `byg-vvs` 0.1.8 → 0.1.9

### parallel-skrivning (byg, byg-bim, byg-el, byg-kontrol, byg-maler, byg-murer, byg-statik, byg-toemrer, byg-ventilation, byg-vvs)
Parallelitet og revisionsstyring: én skriver pr. fil i sagerne (skriveret pr. fag håndhævet af hooken), forslag til grænseflader, risici, kontrolplan og ejendomskort, der flettes på rækkeniveau ved godkendelse (med konfliktstop), lokalt git-repo i byg-sager/ med commits pr. aflevering, dom og fletning og en diff til kontrollens forsøg 2–3. I repoet: versionsnoter og scripts/udgiv.py i stedet for versionshævning i grenene.
