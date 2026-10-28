# Ændringslog

## 1.0.0 – 2026-10-28

Første stabile udgivelse af Engineer Any House-marketplacet (MIT-licens). Marketplacet går fra 0.16.1 til 1.0.0; de enkelte plugins følger deres egne versionsnoter.

- `byg` 0.13.1 → 0.13.2
- `byg-anlaeg` 0.1.2 → 0.1.3
- `byg-arkitekt` 0.1.2 → 0.1.3
- `byg-bim` 0.8.1 → 0.9.0
- `byg-data` 0.1.0 → 0.1.1
- `byg-el` 0.2.4 → 0.2.5
- `byg-kontrol` 0.16.1 → 0.16.2
- `byg-maler` 0.1.13 → 0.1.14
- `byg-murer` 0.2.2 → 0.2.3
- `byg-statik` 0.4.2 → 0.5.0
- `byg-team` 0.4.1 → 0.4.2
- `byg-toemrer` 0.1.13 → 0.1.14
- `byg-ventilation` 0.1.14 → 0.1.15
- `byg-vvs` 0.2.4 → 0.2.5

### bim-opslag (byg, byg-bim, byg-kontrol)
Hurtige opslag i BIM-modellen: ny kommando `bim.py maal` (mål på vægge, rum og åbninger, afstande og etageoversigt med kilde – bygger model.yaml frisk, så målet aldrig kommer fra en forældet IFC) og ny skrivebeskyttet opslagsagent `bim-opslag` på Haiku. Projektlederen sender rene spørgsmål til en eksisterende model dertil uden leverance og kontrol; ændringer går stadig til `bim-modelloer`.

### licens-og-engelsk-readme (byg, byg-anlaeg, byg-arkitekt, byg-bim, byg-data, byg-el, byg-kontrol, byg-maler, byg-murer, byg-statik, byg-team, byg-toemrer, byg-ventilation, byg-vvs)
Projektet er udgivet under MIT-licensen (`LICENSE`), og alle plugins angiver `"license": "MIT"`. `README.md` er nu på engelsk til et internationalt publikum, og den danske README ligger i `README.da.md`. Cowork-pakken får stadig den danske README.

### python-miljoe (byg-bim, byg-statik)
Værktøjernes Python-miljøer er nu fuldt låst (alle pakker, også transitive, for Python ≥ 3.11 på alle platforme), så alle får samme versioner. `opsaet` bruger uv, hvis det er installeret, ellers pip, og giver en klar fejl ved for gammel Python. pytest ligger ikke længere i brugernes BIM-miljø (`bim.py opsaet --test`). Opsætningen deles via `faelles/miljoe.py`.

### statik-resultat (byg, byg-kontrol, byg-statik)
Opslag i en statisk beregning uden ny beregning: `fem.py resultat <fem.yaml> [--element] [--kombi]` viser det gemte resultat med kombination, spec-sha og overslagsforbehold og afviser det, hvis `fem.yaml` er ændret siden eller resultatet er regnet med `--saet`. Statik-kontrollen må bruge kommandoen. Projektlederen svarer på spørgsmål til en færdig beregning ud fra det godkendte statiknotat; nye tal og ændrede input går til statikeren som leverance.

## 0.16.1 – 2026-10-28

- `byg` 0.13.0 → 0.13.1
- `byg-anlaeg` 0.1.1 → 0.1.2
- `byg-arkitekt` 0.1.1 → 0.1.2
- `byg-bim` 0.8.0 → 0.8.1
- `byg-el` 0.2.3 → 0.2.4
- `byg-kontrol` 0.16.0 → 0.16.1
- `byg-maler` 0.1.12 → 0.1.13
- `byg-murer` 0.2.1 → 0.2.2
- `byg-statik` 0.4.1 → 0.4.2
- `byg-team` 0.4.0 → 0.4.1
- `byg-toemrer` 0.1.12 → 0.1.13
- `byg-ventilation` 0.1.13 → 0.1.14
- `byg-vvs` 0.2.3 → 0.2.4

### navneskift-engineer-any-house (byg, byg-anlaeg, byg-arkitekt, byg-bim, byg-el, byg-kontrol, byg-maler, byg-murer, byg-statik, byg-team, byg-toemrer, byg-ventilation, byg-vvs)
Projektet hedder nu Engineer Any House. Marketplace hedder `engineer-any-house` (før `byg-eksperter`), og GitHub-repoet bliver `savnik/engineer-any-house`. Plugin-, agent- og skillnavne er uændrede (`byg`, `byg-kontrol`, `byg-vvs` …), og sagsmapper i `byg-sager/` virker som før. Installer fra den nye marketplace med `claude plugin marketplace add <sti>/engineer-any-house` og `claude plugin install byg-team@engineer-any-house`. Claude Code navngiver pluginernes datamapper efter marketplace, så videnbanken og kontroltilstanden skal kopieres fra `~/.claude/plugins/data/<plugin>-byg-eksperter` til `<plugin>-engineer-any-house` ved skiftet. `scripts/tjek_data.py` læser private termer og sagsmapper fra `~/.config/engineer-any-house/` og stadig fra den gamle `~/.config/byg-eksperter/`.

## 0.16.0 – 2026-10-28

- `byg` 0.12.0 → 0.13.0
- `byg-anlaeg` 0.1.0 → 0.1.1
- `byg-arkitekt` 0.1.0 → 0.1.1
- `byg-bim` 0.7.1 → 0.8.0
- `byg-el` 0.2.2 → 0.2.3
- `byg-kontrol` 0.15.0 → 0.16.0
- `byg-maler` 0.1.11 → 0.1.12
- `byg-murer` 0.2.0 → 0.2.1
- `byg-statik` 0.4.0 → 0.4.1
- `byg-toemrer` 0.1.11 → 0.1.12
- `byg-ventilation` 0.1.12 → 0.1.13
- `byg-vvs` 0.2.2 → 0.2.3

### effektivitet-fliser-og-kilder (byg-anlaeg, byg-arkitekt, byg-bim, byg-el, byg-kontrol, byg-maler, byg-murer, byg-statik, byg-toemrer, byg-ventilation, byg-vvs)
Mindre genlæsning. `bim.py sammenlign` skriver nu `fliser.md` og `fliser.json`, som siger, hvilke fliser der skal gennemgås. Tomme fliser springes over. Med `--forrige <forrige rundes mappe>` springes fliser over, hvis modeltegningen er pixel for pixel uændret siden forrige runde. Fliser med automatiske fund gennemgås altid. Sammenligneren læser kun de markerede fliser og fører de uændrede i `daekning.fliser_uaendret`. I en prøve på en lokal sag faldt det, der skulle gennemgås i runde 2 med uændret model, fra 16 til 5 fliser (V1) og fra 25 til 3 (V2). Fællesprotokollen har fået et kilderegister pr. fag og sag, `bilag/<fag-id>/kilder.md` (URL, dato, udgave og side/§, parafrase). Fagene søger i alle fags registre, før de henter en side, og kan genbruge en linje med "jf. kilderegister". Kontrollen må kun bruge registret til at finde kilden og efterprøver stadig selv. Målingen viste, at 23 % af sidehentningerne gentog en side, der allerede var hentet i en anden kørsel. `scripts/forbrug.py` viser nu forbrug pr. agenttype, billed- og PDF-læsninger og Edit-runder pr. kørsel målt mod protokollens lofter, og gentagne hentninger delt op i samme kørsel og på tværs af kørsler. Edit-loftet tæller nu runder, ikke enkelte Edits. Fagagenterne lagde i gennemsnit ca. 4 Edits i samme kald, og kald med kun notat-Edits udgjorde 5 % af fagagenternes forbrug. Når notatet allerede findes, er Edits billigere end at skrive det om. Reglen siger derfor nu: ret et eksisterende notat med Edits, saml dem i samme svar, og brug højst ca. 5 runder. Et loft håndhævet af en hook ville presse agenterne til at skrive hele notatet om eller stoppe midt i en revision, så det er fravalgt.

### fravaer-og-daekning (byg, byg-anlaeg, byg-arkitekt, byg-bim, byg-el, byg-kontrol, byg-maler, byg-murer, byg-statik, byg-toemrer, byg-ventilation, byg-vvs)
Ærlighed om fravær og dækning. "Ikke fundet" behandles som ukendt, ikke som "findes ikke": det står i fællesprotokollen, og i kontrolprotokollen er en fraværskonklusion uden kilde nu et fund. Et delvist besvaret notat skal skrive "Delvist besvaret – mangler: …". Kontrollens dom har et nyt felt, `ikke_kontrolleret`. Hooken validerer og gemmer det, og ved godkendelse siger den, hvad godkendelsen ikke dækker. Feltet føres også i kontrolloggen. Projektlederen laver en opgørelse ved G1–G3: hvert succeskriterie, krav, ramme og åbent spørgsmål markeres besvaret, delvis eller åben, og gaten passeres ikke med punkter, brugeren ikke har accepteret. Det giver kontrolpunkt 1e i kontrol-projekt@1.4. RCA-skabelonen kræver "utilstrækkeligt grundlag", når evidensen mangler.

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
