# Ændringslog

## 2.1.0 – 2026-11-21

- `byg` 1.0.0 → 1.1.0
- `byg-architecture` 1.0.0 → 1.0.1
- `byg-bim` 1.0.0 → 1.0.1
- `byg-carpentry` 1.0.0 → 1.0.1
- `byg-electrical` 1.0.0 → 1.0.1
- `byg-landscape` 1.0.0 → 1.0.1
- `byg-masonry` 1.0.0 → 1.0.1
- `byg-painting` 1.0.0 → 1.0.1
- `byg-plumbing` 1.0.0 → 1.0.1
- `byg-review` 1.0.0 → 1.1.0
- `byg-structural` 1.0.0 → 1.0.1
- `byg-ventilation` 1.0.0 → 1.0.1

### user-decisions-stand (byg, byg-architecture, byg-bim, byg-carpentry, byg-electrical, byg-landscape, byg-masonry, byg-painting, byg-plumbing, byg-review, byg-structural, byg-ventilation)
Pluginet spørger ikke om det samme igen. Nyt register `closed-by-user.md` i hovedsagen (branches deler det) holder brugerens svar, fravalg og accepterede risici med brugerens ord. Det gælder frem for ældre fagnotater, hold points, risici og domme, også godkendte. Hooken genindlæser registret efter compact, og `/byg:status`, projektlederen, fagagenterne og kontrollen filtrerer åbne punkter og spørgsmål mod det. Det, brugeren oplyser (også et gengivet myndighedssvar), er grundlag uden krav om dokumentation, og valg logges, som brugeren traf dem, uden projektlederens anbefalinger som betingelser. RCA: `docs/rca-2026-11-21-repeated-questions.md`.

## 2.0.0 – 2026-11-21

- `byg` 0.13.2 → 1.0.0
- `byg-architecture` 0.1.3 → 1.0.0
- `byg-bim` 0.9.0 → 1.0.0
- `byg-carpentry` 0.1.14 → 1.0.0
- `byg-data` 0.1.1 → 0.1.2
- `byg-electrical` 0.2.5 → 1.0.0
- `byg-landscape` 0.1.3 → 1.0.0
- `byg-masonry` 0.2.3 → 1.0.0
- `byg-painting` 0.1.14 → 1.0.0
- `byg-plumbing` 0.2.5 → 1.0.0
- `byg-review` 0.16.2 → 1.0.0
- `byg-structural` 0.5.0 → 1.0.0
- `byg-team` 0.4.2 → 1.0.0
- `byg-ventilation` 0.1.15 → 1.0.0

### 3d-demo-same-house (byg-bim, byg-plumbing, byg-structural)
Eksempelhuset er nu det samme i BIM og FEM. BIM: nyt afsnit `ovenlys` til tagvinduer i tagfladen, `farve` på systemer, `bim.py eksport --gennemsigtig/--alfa` til gennemsigtige facader og en komplet VVS-installation i eksemplet (centralvarme, radiatorer, varmtvandsbeholder, koldt og varmt brugsvand, spildevand til brønd). Statik: nyt FEM-eksempel `fem-example-house.yaml` med husets vægge og dæk. Nyt felt `spaer` på tage: spær, veksler om ovenlys og skorsten samt hanebånd som IfcMember i taget, og eksemplet viser spærkonstruktionen gennem den gennemsigtige tagflade. FEM-eksemplet: bjælkelaget er nu leddet på murkronen, og dækket over kælderen holder kældervæggenes top. Det fjerner de urealistiske spændingsspring ved væghjørnerne. fem.md beskriver begge modelleringsregler. VVS: ny reference `schematic.md` med indhold, layout, farver (samme som BIM-systemerne), SVG-symbolbibliotek og tjekliste, så plumber kan tegne et principdiagram over varme, brugsvand og afløb, samt et færdigt eksempel for eksempelhuset (`assets/principdiagram-eksempelhus.svg`).

### 3d-demo (byg-bim, byg-structural)
3D-visning på GitHub Pages: `bim.py eksport` skriver modellen som glTF (.glb) i modellens farver, og `fem.py vis --cdn` laver en lille HTML, der henter plotly fra nettet. `scripts/demo_site.py` og workflowet Pages bygger eksempelhuset og FEM-eksemplet som interaktive 3D-sider, som README viser.

### el-plan (byg-bim, byg-electrical, byg-review)
El-plan efter gennemgang af elplanen.dk:

- **Ny kommando `bim.py elplan`.** Den laver en punktliste pr. rum og kontrollerer antallet af stikkontakter mod § 57 i BEK 1082/2016:
  - stk. 1: 1 pr. påbegyndt 4 m², højst 10
  - køkken: mindst 3 på mindst 2 kredse
  - bad/wc: mindst 1
  - garage, carport, loft og depot er undtaget

  Kommandoen udleder også afbrydertypen pr. lysgruppe (1-polet, korrespondance, kryds eller krone) og finder lamper uden gruppe.
- **BIM-spec.** Nye el-arter: `kraftstik`, `data` og `pir`. Nye felter: `lysgruppe`, `kreds` og `dimmer`, som gemmes i `Byg_El`. `geometri` kan nu udelades for el-punkter.
- **El-videnbasen** har fået:
  - behov pr. rumtype
  - logikken for afbrydertype
  - typiske placeringer (markeret T, ikke krav)
  - tjeklisten "El-plan rum for rum"
  - § 57, stk. 5 (verificeret)
- **El-fejlkataloget** (kontrol-el@1.3) har fået typiske misforståelser i el-planlægningsværktøjer, fx forældet zone 3, stik i område 2 og montagehøjder fremstillet som krav.

### electrical-calc-tool (byg-bim, byg-electrical, byg-review)
El får et regneværktøj og et tavlediagram, og eksempelhuset får en komplet el-installation. El: nyt `scripts/el.py` (kun standardbiblioteket) regner strømværdi Iz med korrektion for forlægning, samlet fremføring og kabel i isolering, spændingsfald, Ik,min og Ik,max mod Fællesregulativet 2026 og laver tavlekontrol med et fast gruppeskema og fund (`el.py panel`). Det gælder bl.a. RCD-kæde og -typer, mindst to 30 mA-RCD'er, selektivitet, faselast og reserve. Nyt `scripts/diagram.py` tegner et enstregsdiagram (SVG) af tavlen, og `references/schematic.md` beskriver det med et eksempel i `assets/`. Videnbasen har V-mærkede regler om badeværelsesområder efter 701:2024, RCD-typer (elbil, frekvensomformer, type B i kæde), TT/TN og SPD som betinget krav. Dimensioneringsgrundlaget ligger samlet i `references/calc-tools.md`, som kun læses ved dimensionering. electrician har Bash, låst til `el.py`. BIM: eksempelhuset har kabelskab, stikledning, hovedtavle med måler, SPD og tre RCD'er samt ti grupper som IfcDistributionCircuit med kabellængder. Nye felter i spec'en (`systemer.under`, `installationer.del_af`, art kabel og belysning), og `bim.py panel` eksporterer tavlen i el.py's tavleformat. Review: calc_guard låser også electrical-review til `el.py`, og rubrikken `kontrol-el@1.3` har et nyt punkt 16 om dimensionering og gruppeskema samt verificerede punkter om RCD-typer og badeværelse.

Rettelser i `el.py`: `ikmin` har `--feeder-insulation pvc/xlpe` (stikledningen blev altid regnet som XLPE 90 °C), og næste tværsnit regnes nu med samme stikledningstemperatur og isolering. `el.py panel` giver advarsel ved sikring over 13 A foran 10/13 A-stikkontakter og over 16 A foran 16 A (BEK 1082 § 45, nyt felt `stikkontakt_a`, 13 A antages ved `stik`). `calc-tools.md` dokumenterer, at modstanden regnes efter IEC 60228 pr. tværsnit (ρ70 ≈ 0,0217–0,0222), lidt under håndregningskonventionen 0,0225.

electrician-prompten viser den eneste tilladte Bash-kaldform for `el.py` (én kommando, uden `cd`, `;`, `&&`, `|` og flag før stien) og siger, at filer læses med Read og Grep. Agenten forsøgte før at læse videnbasen med sammensatte Bash-kommandoer, som vagten afviste (F-035: 0 afviste kald, −11 % pris pr. bestået ved uændret kvalitet på udvikling og holdout). Den samlede gren med regneværktøj og el-plan består 32 af 40 gamle opgaver mod mains 33 af 40, inden for støj, ved samme pris pr. bestået (F-038).

### english-code (byg, byg-architecture, byg-bim, byg-carpentry, byg-data, byg-electrical, byg-landscape, byg-masonry, byg-painting, byg-plumbing, byg-review, byg-structural, byg-team, byg-ventilation)
Koden er oversat til engelsk: Python-moduler, funktioner, variabler, kommentarer og docstrings har engelske navne (fx `review_gate.py`, `bimlib/decode.py`, `femlib/shells.py`). CLI-kommandoer, flag og valgmuligheder er også engelske – fx `bim.py decode check`, `bim.py check … --draw`, `bim.py merge … --dry-run`, `fem.py calc … --no-files`, `fem.py result`, `statik.py beam --span …` og `bim.py draw … all --out …`. De gamle danske kommandonavne virker ikke længere. Resten af produktet er uændret dansk – hjælpetekster og al tekst til brugere og agenter, YAML/JSON-nøgler, og værdier i gemte data (domme, hændelser) er de samme som før.

Også navne er nu engelske: filnavne, plugins, agenter, skills, fag-id'er og markører. Plugins: byg-kontrol→byg-review, byg-anlaeg→byg-landscape, byg-arkitekt→byg-architecture, byg-el→byg-electrical, byg-maler→byg-painting, byg-murer→byg-masonry, byg-statik→byg-structural, byg-toemrer→byg-carpentry, byg-vvs→byg-plumbing. Agenter fx projektleder→project-manager (`claude --agent byg:project-manager`), statiker→structural-engineer, vvs-mester→plumber og `<fag>-kontrol`→`<trade>-review`; skills fx kvalitetskontrol→quality-review, tegningsimport→drawing-import, koordiner→coordinate og `<fag>-viden`→`<trade>-knowledge`. Fag-id'er: vvs→plumbing, el→electrical, murer→masonry, maler→painting, toemrer→carpentry, statik→structural, arkitekt→architecture, anlaeg→landscape, projekt→project. Sagsmappen hedder nu `byg-cases/` (før `byg-sager/`) med engelske filnavne: projektgrundlag.md→project-basis.md, beslutningslog.md→decision-log.md, fagnotater/→trade-notes/, forslag/→proposals/, kvalitet/kontrollog.md→quality/review-log.md, bilag/→attachments/, ejendomme/→properties/, erfaringer.md→lessons-learned.md, tilstand.json→state.json m.fl.; videnbanken hedder knowledge-bank/ (sager.md→cases.md). Markører i prompts: LEVERANCE:→DELIVERABLE:, FASE:→PHASE:, KONTROLNIVEAU: let|fuld→REVIEW-LEVEL: light|full, DESIGNGRUNDLAG:→DESIGN-BASIS:, GENFORSØG→RETRY, `<!-- GENERERET`→`<!-- GENERATED`, og godkendelsen "Godkend G2 <sag-id>" hedder nu "Approve G2 <case-id>". I repoet: eksamen/→exam/, faelles/→shared/, skabelon/→template/, versionsnoter/→release-notes/, ARKITEKTUR.md→ARCHITECTURE.md, og udgivelsesgrene hedder `release/<version>`.

Det kræver handling: afinstallér de gamle plugins og installér dem igen under de nye navne (fx `byg-plumbing` i stedet for `byg-vvs`). Eksisterende sagsmapper og videnbanker skal omdøbes til de nye mappe- og filnavne – der er ingen danske aliaser, så hooks og agenter genkender ikke de gamle navne. Regnemiljøet til statik flytter til `~/.local/share/byg-structural` og installeres igen automatisk ved første kørsel.

### glb-contrast (byg-bim)
BIM: `bim.py export` skriver nu farverne korrekt til glTF (IFC-farver er sRGB, glTF lineære), så tegl, træ og beton ikke længere ser udvaskede og pastelagtige ud i 3D-visningen. Materialerne får navn efter IFC-stilen, rør og kanaler i systemfarver lyser svagt, så de tynde rør kan ses, og standarddækkevnen for `--transparent` er sænket fra 0,25 til 0,15, så det indvendige står tydeligere. 3D-demoen har tættere kamera, retningsbestemt lys og kraftigere skygger.

### no-diy-assessment (byg, byg-architecture, byg-bim, byg-carpentry, byg-electrical, byg-landscape, byg-masonry, byg-painting, byg-plumbing, byg-review, byg-structural, byg-ventilation)
Agenterne tager ikke længere stilling til, om brugeren selv må udføre arbejdet, eller hvem der må (autorisation, gør-det-selv-grænser), fordi pluginet hverken kender brugerens faglige baggrund eller land. De beskriver løsning og udførelse fuldt ud uden forbehold og svarer kun på spørgsmålet, når brugeren spørger direkte. Kontrollen giver ikke længere fund for manglende autorisationsforbehold, men et uopfordret forbehold er et mindre fund. En generel ansvarsfraskrivelse står i README. Sikkerhedsadvarsler og projektets egne krav (byggetilladelse, statisk dokumentation, screening) er uændrede.

### wind-braces (byg-bim)
BIM: nyt felt `vindbaand` under `spaer` på tage (true eller `{b, t}`, standard 100 × 25). Det sætter to vindbånd (IfcMember BRACE) under spærene i hver skrå tagflade, i 45° mellem murrem og kip fra hver gavl, inden for omridset og uden om ovenlys og skorsten. Eksempelhuset og 3D-demoen viser nu vindbåndene i tagkonstruktionen.

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
