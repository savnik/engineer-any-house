# Arkitektur – byg-eksperter

## Krav → design
| Krav | Design |
|---|---|
| Projektleder som tovholder, der interviewer til projektet er veldefineret | `byg`: projektleder-skill (model-invocable) + agent; interviewblokke A–F og Definition of Ready; projektgrundlaget kontrolleres af `projekt-kontrol` |
| Fagagenter på mesterniveau efter danske standarder | Ét plugin pr. fag: agent (persona, fagområde, kerneprincipper, screening, fejlfinding) + videnbase med normgrundlag markeret V/T med kilde og dato |
| Selvbærende | Hvert fag-plugin virker alene (med `byg-kontrol`); skill-fallback til claude.ai uden subagenter |
| Opbygge viden over tid, forankret til hurtig genbrug | Fire videnlag: kanon, agenthukommelse, videnbank, sagsmappe; `/byg:erfaring` og forankringskø |
| Modsvarende kvalitetskontrolagent pr. fag | `byg-kontrol`: én kontrolagent pr. fag + `projekt-kontrol` |
| Hårdt og kritisk review, adskilt fra den udførende | Egen agent, egen kontrolviden, kun læse-/søgeværktøjer, ingen hukommelse, ingen adgang til fagagentens ræsonnement; efterprøvning mod primærkilder |
| Projektlederen sikrer kontrol af hver leverance og looper til godkendelse | Skill `kvalitetskontrol` + hooks (PreToolUse, SubagentStop, Stop) |
| BIM-model af huset (IFC), effektiv og af høj kvalitet | `byg-bim`: deterministisk værktøjskæde (spec → IFC4), kontrol og tegninger som kode; agenten redigerer kun spec'en |
| Tegninger afkodes grundigt før modellen bygges; separat agent sammenligner original og model; fejl retur, indtil de er rettet | Skill `tegningsimport`: afkodning med deterministisk kontrol, hjælpeagent `bim-sammenligner` (skrivebeskyttet), hook-understøttet sammenligningsloop (højst 3) før den formelle kontrol |
| Maks. 2 forsøg pr. runde, derefter eskalering til brugeren; RCA, forbedring af fagagenten og ny runde kun efter brugerens beslutning (maks. 2 runder; ændret fra 3/3 i 2026-10, se Tokenbudget) | Hook-tilstand pr. leverance-ID med runde og forsøg (`maks_forsoeg`/`maks_runder` i fagregistret); 3. forsøg afvises; Stop blokerer én gang for eskaleringen; ny runde kræver brugerens `Ny runde <id>` og en 5 Why-kæde (≥ 5 hvorfor-niveauer og en grundårsag) og 'Forbedring implementeret: ja' i RCA'en; 4. runde afvises og eskaleres; RCA-skabelonen fokuserer på, hvorfor forsøg 1 ikke var korrekt |

## Komponenter
```
byg-team ──(dependencies)──► byg, byg-kontrol, byg-data, byg-vvs, byg-el, byg-murer, byg-ventilation, byg-maler, byg-toemrer, byg-statik, byg-bim
byg ─────────────────────────► byg-kontrol
byg-<fag> ───────────────────► byg-kontrol
```
- **Hovedtråden** (projektlederen eller Claude ved direkte brug) orkestrerer. Fagagenter har ikke Agent-værktøjet og kalder aldrig kontrollen selv.
- **Fagagenter:** `model: opus`, `effort: high`, `memory: user`, værktøjer Read/Write/Edit/Glob/Grep/WebSearch/WebFetch (`bim-modelloer` og `statiker` har desuden Bash til deres værktøj). Fælles protokol indsættes fra `faelles/protokol.md`.
- **Modelvalg (2026-09-26):** Fagagenterne kører på Opus med `effort: high`, fordi et afvist første forsøg koster en hel ekstra fag- og kontrolrunde (målt i en rigtig sag: Sonnet-fagagent 10 min, afvist med 8 væsentlige fund, rettelse 21 min). Kontrolagenterne har eksplicit `effort: high`. **Ændret 2026-10 (Tokenbudget):** kontrol på niveau `let`, `bim-sammenligner` og produktopslag kører på Sonnet/Haiku; Opus bruges til fagagenterne og til `fuld` kontrol. Uafhængigheden sikres af adskilt kontekst, kontrolviden og værktøjer – ikke af modelforskel.
- **Kontrolagenter:** `model: sonnet` (ved `KONTROLNIVEAU: fuld` kaldt med `model: opus`, håndhævet af hooken), `effort: high`, `maxTurns: 60`, `color: red`, værktøjer Read/Glob/Grep/WebSearch/WebFetch (`statik-kontrol` desuden Bash, låst til regneværktøjet), ingen `memory` (som ellers giver Write/Edit). Fælles kontrolprotokol indsættes fra `faelles/kontrolprotokol.md`.

## Kvalitetskontrol-laget
**Leverance-ID** `<sag-id>/<fag-id>/<nr>` binder fagkald, kontrolkald, domme og RCA sammen. Godkendte leverancer ændres kun under nyt ID (`-r2`). `ekstern/<emne>` bruges til rådgivende review af eksternt materiale uden loop.

**Dom** (sidste JSON-blok i kontrolagentens svar): `leverance_id, fag, forsoeg, dom, rubric_version, sagsmappe, fund[id, klasse, status, sted, paastand, krav, kilde, evidens, handling, eskaler], regressioner, efterproevet_mod_primaerkilde, usikkerheder, kontrolsvigt`. Godkendt ⇔ ingen åbne kritiske/væsentlige fund. Blokerende fund kræver krav, kilde og evidens.

**Faser og gates:** projektet går gennem fase 0 (afklaring og Definition of Ready pr. fag), 1 (dispositionsforslag), 2 (design → design freeze) og 3 (én samlet plan), derefter 4 (udførelse, ændringsstyring). Kontrolniveau `let` eller `fuld` efter fase og risiko. Formålet er, at planer ikke revideres, hver gang designet ændres, og at ændringer samles.

**Stabilitet og fund-fastlåsning:** rubric fryses i forsøg 1, som er det fulde review. Forsøg 2–3 tager kun stilling til tidligere fund og regressioner i ændrede afsnit. Et nyt blokerende fund kræver `nyt_grundlag` (regression / aendret_tekst / kritisk_sikkerhed), ellers sender hooken dommen retur. Oversete forhold rejses som mindre og under kontrolsvigt. Bestridte kritiske fund eskaleres til brugeren.

**Hooks** (`plugins/byg-kontrol/hooks/kontrol_gate.py`, python3, fail-safe):
| Hændelse | Regel |
|---|---|
| PreToolUse (Write/Edit) | **Skriveret:** en fagagent må i `byg-sager/` kun skrive sine egne filer (fagregister `skriv_alle`, `skriv`, `skriv_ny`); et forslag skal hedde efter en igangværende leverance (ellers ville det aldrig blive flettet), og stier normaliseres (`..`). Godkendte leverancer (sti fra kontrolkaldet) beskyttes: afvises for subagenter, advarsel i hovedtråden |
| PreToolUse (Agent/Task) | Kræver `LEVERANCE:`; fagkald → "afventer_kontrol"; ny fagversion før dom, forkert kontrolagent, forsøg ud over `maks_forsoeg`, `KONTROLNIVEAU: fuld` uden `model: opus` og ændring af godkendt leverance afvises; projektkontrol kræver `FASE:`, og i fase 3+ `DESIGNGRUNDLAG:` med godkendte fagleverancer |
| SubagentStop (fagagenter) | `fagkald_igang` → `afventer_kontrol` ved aflevering (leverance-ID fra agentens prompt). Genforsøg af afbrudt fagkald tæller ikke |
| SubagentStop (kontrolagenter) | Validerer dommen (inkl. `nyt_grundlag` på nye blokerende fund i forsøg 2 og senere); ugyldig dom sendes retur én gang; opdaterer status (godkendt / afvist / stoppet); gemmer dommen i `<sagsmappe>/kvalitet/` |
| UserPromptSubmit | Brugerens egen `Godkend G2 <sag-id>` registrerer den manuelle løsningsgodkendelse, bundet til de godkendte fagleverancer. Fase 3 (projektkontrol og fagkald med FASE ≥ 3) kræver den. **Kontekstbudget:** i en session med byg-leverancer får brugeren og projektlederen én påmindelse, når hovedtrådens kontekst passerer 200k tokens, og derefter for hver 100k: afslut opgaven, og fortsæt i en ny session med `/byg:status <sag-id>` |
| Stop (hovedtråd) | Blokerer én gang, hvis sessionens leverancer afventer kontrol, er afvist eller mangler RCA |

Agentnavne matches på basisnavnet, så både `byg-vvs:vvs-mester` (marketplace) og `byg:vvs-mester` (samlet pakke) virker; fag→kontrol-mapping ligger i `hooks/fagregister.json`.

**Læring:** RCA → forbedring af fagagenten straks (agentens hukommelse) og varigt (repoet: prompt/videnbase, commit og versionsløft) → ny runde. Desuden forankringskø → ny tekst i fagets videnbase, ny `rubric_version` i kontrolviden, præciseret prompt, nyt interviewspørgsmål eller ny eval-case.

## Effektivitet (RCA 2026-10-04)
Hvert API-kald læser hele agentens kontekst igen, så prisen pr. svar følger kontekstens størrelse. En måling på rigtige sager fandt fire kilder til spild omkring kontrollen, ikke i den, og dertil designet:

| Kilde | Design |
|---|---|
| Hovedtråden voksede til 300–500k tokens, fordi én session blev brugt til mange opgaver over dage, og projektlederen lavede research selv | **Kontekstbudget:** én opgave pr. session; sagsmappen er hukommelsen, og `/byg:status <sag-id>` genoptager. Research (priser, marked, datablade) går til en subagent; rene prisopslag er ikke en fagleverance. Hook-påmindelse fra 200k |
| Returer med alle fund, også mindre, og fuld kontrol på lavrisiko-opgaver | **Kontrol i forhold til risikoen:** kun blokerende fund sendes retur. Nye ønsker bliver en ny leverance. Kontrolniveauet følger opgavens risiko: `fuld` kun når en sikkerhedsfunktion fastlægges eller ændres; indkøb, priser og styklister får `let` |
| Fuld indlæsning af sagsmappen og gentagne opslag af de samme kilder | **Målrettet læsning og genbrug:** Grep og relevante afsnit; fagforespørgslen peger på afsnit; `normer.md` og sagens domme før nye opslag. Kontrollen genbruger sine egne efterprøvede kilder og slår kun op i forsøg 2 og senere ved nyt grundlag |
| Kontrol i baggrunden gav status-polling i hovedtråden | **Forgrund:** fag- og kontrolkald køres parallelt i forgrunden (flere Agent-kald i samme besked) |

### Tokenbudget (måling 2026-10-17)
Måling af 437 transskripter: subagenter 59 %, hovedtråd 35 %, workflows 6 % (men halvdelen af en dags forbrug). Ca. 40 % af leverancerne blev afvist, statikeren brugte 150–276 skridt pr. kald (kontekst 21k → 215k), samme fil blev læst op til 31 gange, og "Fortsæt" startede workflows med 39 agenter.

| Kilde | Design |
|---|---|
| Workflows startet på "Fortsæt" | PreToolUse-hook på `Workflow`: afvises i byg-sager, medmindre brugerens seneste besked nævner "workflow" |
| Opus på alt | Kontrol (`let`) og `bim-sammenligner` på Sonnet, produktopslag på Haiku; `fuld` kontrol kræver `model: opus` i kaldet |
| Lange kontrolloop | 2 forsøg pr. runde; derefter eskalering til brugeren; ny runde (med RCA) kun efter brugerens `Ny runde <id>`; højst 2 runder |
| Lange fagkald og genlæsning | `maxTurns` (fag 150, kontrol 60, sammenligner 50) og "Tokenbudget" i de fælles protokoller: hver fil én gang, ingen scannede PDF'er, resuméer frem for rå resultater, ét Write, arbejdsfil til genforsøg |
| Mange leverancer pr. sag | Projektlederen viser status og spørger efter 3 fagleverancer; `let` er standardniveau, `fuld` for statik kun ved dimensionering eller ændring af en bærende del |

`scripts/forbrug.py` måler effekten: vægtet forbrug pr. del, hovedtrådens kontekst, retur-andel, gentagne opslag og statuskald.

## BIM og tegningsimport (2026-10-11)
**Valg af arkitektur (research 2026-10-10):** fri IfcOpenShell-kodegenerering har høj fejlrate (BIM-Edit 2026: 3,4 % fuldt løste redigeringsopgaver; API-misbrug er den største fejlkilde), og MCP-værktøjskataloger koster mange tokens (MCP4IFC ca. 40k). Derfor er BIM-faget bygget som **spec → deterministisk generator → automatisk kontrol → tegninger**. Agenten skriver en kort YAML-spec. `bim.py` (IfcOpenShell 0.9) bygger IFC4 efter buildingSMART-reglerne (rumlig struktur, IfcSpace aggregeret, typer med lag, enumereret Status, Qto_ med BaseQuantities, georeference med Scale 0,001, stabile GlobalId'er) og kontrollerer modellen (skema/EXPRESS, udvalgte normative regler, geometri, snitbaseret kollisionstjek, arealer mod BBR, IDS). Plan, snit, facade og 3D tegnes fra selve IFC-filen. Fremmede filer redigeres med `ifcedit`/scripts efter `rediger.md`.

| Komponent | Design |
|---|---|
| `bim-modelloer` | Fagagent med **Bash** (undtagelse fra de øvrige fag: værktøjet skal køres). Afkoder, bygger og retter. Skriver modelnotat |
| `bim-sammenligner` | **Hjælpeagent** (fagregister `hjaelpere`): Read/Glob/Grep/Bash, ingen hukommelse. Hooken `byg-bim/hooks/sammenligner_vagt.py` tillader kun læsende `bim.py`-kommandoer |
| `bim.py afkod tjek` | Afkodningen kontrolleres mod tegningen selv: kalibreringsrest, skala mod målestok, hvert aflæst mål mod afstanden mellem dets endepunkter og målkædernes sum. Fanger fejllæste tal |
| `bim.py sammenlign` | Modellen tegnes i originalens pixelramme (kalibreret). Original, model og overlay pr. visning og i fliser, plus automatisk sammenligning af alle afkodede mål (mod modelfladerne ud for hjælpelinjernes fod), rum, åbninger, vægtykkelser og koter |
| Hook (`kontrol_gate.py`) | Hjælpekald kræver en afleveret fagversion og sætter `under_sammenligning` → `sammenlignet`. Et fagkald efter en sammenligning er en **rettelse**, som ikke bruger kontrolforsøg. Højst `maks_sammenligninger` (3). Kontrollen kan kaldes efter sammenligningen, og Stop minder om uafsluttede sammenligninger |
| `bim-kontrol` | Kun læse- og søgeværktøjer som de øvrige kontrolagenter. Hovedtråden kører `bim.py tjek` (deterministisk) før kontrolkaldet, og kontrollen efterprøver IFC-filen med Grep og PNG'erne |

**Uafhængighed:** sammenligneren ser kun filerne (original, afkodning, IFC), ikke modellørens ræsonnement, og tegner selv modellen fra IFC-filen. Afkodningsfejl er en egen kategori, fordi en model, der svarer til en fejllæst afkodning, ellers ville bestå.

**Miljø:** værktøjet kører i sit eget venv (`~/.local/share/byg-bim/venv`, fastlåste versioner i `requirements.txt`). `bim.py` skifter selv til det. Kendte fejl i IfcOpenShell 0.9.0 er omgået og dokumenteret i `erfaringsblade.md` (EB-BIM-02).

## Statik (2026-10-11)
**Rolle:** `statiker` er en **rådgivende** fagagent. Den screener (er væggen bærende?), laver overslag, skriver konstruktionsgrundlag og opgavebeskrivelser og reviewer statisk dokumentation fra rådgivere. Den udarbejder ikke statisk dokumentation til byggesagen og underskriver ikke – BR18 lægger ansvaret hos den ansvarlige statiker, i de højere konstruktionsklasser en certificeret statiker. Derfor er "ansvarlig statiker" stadig et fag uden agent i projektlederens fagvalg.

| Komponent | Design |
|---|---|
| `statik.py` | Overslag som kode (Python-stdlib): simpelt understøttet bjælke i stål, træ og limtræ (moment, forskydning, nedbøjning, reaktioner, lastkombinationer efter DK NA) og kontakttryk. Tværsnitsværdier for IPE/HEA/HEB regnes fra geometrien og selvtestes mod tabelværdier. Partialkoefficienter står samlet med kilde og kan overskrives |
| `fem.py` (FEM-model) | Krav fra brugeren (2026-10-16): statikeren laver alle konkrete beregninger i en FEM-model. PyNite (MIT) i eget miljø som `bim.py`: modelspec `fem.yaml` i sagsmappen → reaktioner, N/V/M og nedbøjning pr. kombination med ligevægtskontrol, PNG-tegninger til agenten og notatet og én offline HTML (plotly) til bygherren. `statik.py` bruges til lastopgørelse, udnyttelse og håndkontrol. Kontrollen genkører med `regn --ingen-filer` og egne input via `--saet`; `regne_vagt.py` håndhæver, at kontrollen ikke kan skrive filer. Valgt frem for OpenSees (licens kræver betaling ved kommerciel brug), anaStruct (kun 2D) og CalculiX/Code_Aster (net af massive emner, overkill for huse) |
| Al regning i Python | Krav fra brugeren (2026-10-11): ingen tal regnes i hovedet. `statik.py` har `regn` (sikker aritmetik via ast) og `last` (lastopgørelse og opland) ud over `bjaelke` og `tryk`, og hvert output indeholder sin kommando med absolut sti, så bilaget kan genkøres |
| Bash, låst | `statiker` og `statik-kontrol` har Bash, men `byg-kontrol/hooks/regne_vagt.py` tillader kun én kørsel af fagets registrerede regneværktøj (`"regnevaerktoej"` i fagregistret). Kontrolagenten kan derfor regne uden at kunne skrive; validatoren tillader kun Bash for kontrolagenter i fag med regneværktøj |
| Mærkning | Hvert beregnet tal mærkes "OVERSLAG – skal eftervises af den ansvarlige statiker"; kontrollen afviser umærkede overslag (kritisk) |
| `statik-kontrol` | Læse- og søgeværktøjer plus låst Bash. Genkører bilagets kommandoer og regner med egne input, hvor den er uenig; tjekker lastvejen til jord, stabilitet og midlertidig understøtning |

## Parallelitet og revisionsstyring (2026-10-16)
**Problem:** fag og sessioner, der kører parallelt, skrev i de samme filer. I sagerne gjaldt det grænseflader, risici, kontrolplan og ejendomskort, og i repoet versionsnumre, `ARKITEKTUR.md`, README og de genererede protokolblokke. Reglen "kun projektlederen skriver" sendte alt gennem hovedtråden.

**Tre principper:** én skriver pr. fil; parallelt arbejde med fletning én ad gangen; git som revisionsstyring – også for sagerne.

| Komponent | Design |
|---|---|
| Skriveret (`kontrol_gate.py beskyt`) | Fagregistret giver hvert fag dets skrivestier i sagen: `skriv_alle` (fagnotat, bilag, `forslag/<fag>-*__*.md`), `skriv` (fx `bim/forslag/*`, `fem/*`) og `skriv_ny` (kun oprettelse, fx `bim/model.yaml`). Subagenters Write/Edit uden for dem afvises med vejledning. Hovedtråden, kontrol og filer uden for `byg-sager/` berøres ikke. Bash-skrivninger (bim.py, fem.py) dækkes af fagets egne mapper og af regnevagten |
| Forslag og fletning (`sagsflet.py`) | Samme mønster som `bim.py forslag/flet`, men til markdown-tabeller: forslaget har kun de ændrede eller nye rækker under samme overskrift, og rækker matches på ID i første kolonne. Basis (målfilerne) gemmes, når fagkaldet starter, så en fletning, der lander, mens faget arbejder, giver konflikt i stedet for overskrivning. Historiktabellen "Erstattede oplysninger" indgår ikke i ID-opslaget. Hooken fletter, når kontrollen godkender. Konflikt (samme række ændret begge steder) giver intet skrevet og vises af Stop. En ejer-kolonne ændres aldrig af et forslag, og et genereret ejendomskort afvises (det rettes via BIM-forslag). Ændrede værdier i ejendomskortet flyttes til "Erstattede oplysninger" |
| Git i `byg-sager/` (`sagsgit.py`) | Lokalt repo, der oprettes automatisk (kun i en mappe ved navn `byg-sager`, aldrig i et plugin-repo) og aldrig pushes. Commits ved fagaflevering (kun fagets stier, så parallelle fag ikke blandes), dom og fletning og hovedtrådens Stop. Besked = leverance-ID. Diff fra den kontrollerede version til en ny fagversion skrives til `kvalitet/<leverance>__aendringer.diff`, så forsøg 2 og senere tjekker præcis det ændrede. Genererede filer (PNG, HTML, `bim/ud/`) ignoreres. Hvert commit har et tidsbudget (12 s) og kører uden for tilstandslåsen; en dræbt git-proces' `index.lock` fjernes, og fejl logges. `BYG_GIT=0` slår det fra |
| Versionsnoter (`versionsnoter/`, `scripts/udgiv.py`) | Grenene hæver ikke versioner (plugin.json og marketplace var de filer, der oftest var ændret i historikken). Hver gren lægger en note med plugin og niveau. `udgiv.py` på main hæver det højeste niveau pr. plugin og marketplacet og skriver `CHANGELOG.md`. Pre-commit afviser versionsændringer uden for main, og `valider.py` validerer noterne |

**Fravalgt:** fillåse under hele fagkaldet (serialiserer det, vi ville parallelisere) og en tabel pr. fag (fragmenterer registrene, som projektlederen og kontrollen skal se samlet). Kun-tilføj-logge for beslutningslog og kontrollog er ikke nødvendige, så længe kun hovedtråden skriver dem.

## Eksamenslag (2026-10-17)
**Problem:** fagviden blev kun testet med 1–2 scenarie-evals pr. fag. Der var ingen måling af bredde og intet grundlag for at sige, hvor videnbasen mangler noget, eller hvor den vildleder.

**Valg:** Uddannelsesmaterialet gemmes ikke som videnbase. Det ville fylde konteksten og bringe forældede lærebogsværdier og ophavsretligt stof ind i et repo, der skal offentliggøres. I stedet bruges de **officielle læringsmål** som dækningskort, og hvert mål får egne eksamensopgaver med efterprøvet facit. Officielle prøvesæt er ikke offentlige (EVU's prøvebank og autorisationsprøverne er fortrolige). Opgaverne er derfor skrevet til repoet ud fra prøveformerne.

| Komponent | Design |
|---|---|
| `eksamen/<fag>/laeringsmaal.json` | Kompetencemål ordret fra uddannelsesordningen (STIL, gældende fra 1/8-2026; målene er flyttet fra bekendtgørelsen til uddannelsesordningen), el: EVU's 11 el-teoretiske temaer, mesterniveau: autorisationsprøvens indhold (el: Sikkerhedsstyrelsens tre hovedområder; vvs: de kompetencegivende AK-fagelementer). Mål uden for rollen har en begrundelse |
| `opgaver*.json` | `valg`, `tal` og `fri` med facit, kilde og V/T. Hvert mål i rollen har opgaver i både `udvikling` og `holdout` |
| `scripts/exam.py` | `tjek` (format og dækning, i `valider.py`), `vis` (sæt og dækningskort som markdown), `koer` (headless `claude -p` i tom mappe, uden brugerens plugins og internet; arm `basis` mod `plugin` med `--agent`), `rapport` (gevinst, huller og regressioner, tid, tokens og pris pr. bestået opgave) |
| Rettelse | `valg` og `tal` deterministisk fra linjen `SVAR:`; `fri` af en censor-LLM efter opgavens kriterier |
| Placering | Uden for `plugins/`, så facit hverken pakkes eller kan læses af agenten |
| Kun pluginet | Plugin-armen fjerner `memory: user` i plugin-kopien, så målingen dækker det, der er forankret i repoet, og ikke agenthukommelsen med erfaringer fra brugerens sager. `--med-hukommelse` er et tilvalg. Agenten har kun læseværktøjer under eksamen |

**Målt effekt (2026-10-18, én kørsel, før `0a506d5` og efter `dce258f`):**

| Fag | Bestået, hele sættet | Holdout | Pris pr. bestået opgave | Ture pr. opgave |
|---|---|---|---|---|
| el | 80 % → 94 % (basis 82 %) | 77 % → 87 % (basis 71 %) | 0,086 → 0,077 $ | 2,0 → 2,1 |
| vvs | 86 % → 94 % (basis 81 %) | 86 % → 89 % (basis 86 %) | 0,074 → 0,072 $ | 1,9 → 2,2 |

Videnbasen voksede ca. 9 KB pr. fag (ca. 7 % dyrere pr. kald), men prisen pr. rigtigt svar faldt. I sagerne ligger gevinsten i undgåede returer fra kontrollen. Den måles med `forbrug.py --til/--siden` omkring udgivelsen.

**Installatøruddannelsen (AK) og ventilation (2026-10-18, én kørsel, basis mod plugin):** el AK 27 opgaver, 93 % mod 93 %. Vvs AK 22 opgaver, 86 % mod 86 %. Ventilation 32 opgaver, 91 % mod 94 %. Mesteropgaverne ligger tæt på loftet for begge arme. Modellen klarer projektering og ansvar godt, og hullerne er få, enkelte kriterier i fri-opgaver (tegningssymboler, P2X-tab). De er ikke lukket i videnbasen, fordi der ikke var en efterprøvelig primærkilde, og gevinsten er for lille til at betale for mere kontekst. AK-sættene bruges som regressionsværn: de skal blive ved med at bestå, når videnbasen ændres.

**Effektiv drift:** `koer` kører som standard kun plugin-armen og genbruger det nyeste basis-svar. Holdout kræver `--udgivelse`. `--kun-fejlede` kører kun de opgaver, der fejlede. `--gentag-fri` gentager fri-opgaverne for at dæmpe støj. Rapporten viser tid, ture, input-tokens, videnbasens størrelse og pris pr. bestået opgave.

**Kendt faldgrube:** I `dontAsk`-tilstand afviser `claude -p` Read og Grep uden for arbejdsmappen. Uden `--add-dir` til plugin-kopien kan agenten ikke læse sin egen videnbase. De første målinger målte derfor kun agentprompten.

**Konklusion og erfaringer:** Pluginet betaler sig gennem videnbasens konkrete danske regler, ikke gennem agentprompten og ikke på mesterniveau. Fremgangsmåde og faldgruber ved udbygning og måling står i `eksamen/README.md`, afsnittet "Erfaringer".

**CI-agent og forsøgslog (2026-10-18):** Forbedringerne var blevet komplicerede at holde styr på: hvad er afprøvet,
på hvilken revision, og hvad gav det? Projektagenten `.claude/agents/ci-forbedring.md` laver derfor ét forsøg ad gangen
efter en fast cyklus: vælg, formulér hypotesen, mål før, ændr, mål efter (billigt først), afgør og aflevér som
draft-PR. `scripts/forsoeg.py` fører forsøgslog og benchmark i repoet og anvender beslutningsreglen. Agenten er ikke
et plugin, fordi den arbejder på repoet og ikke i sagerne. Den ser aldrig holdout: en PreToolUse-hook afviser direkte
adgang, og alle sammendrag gemmer holdout kun som antal og hash. Loggen er indledt med de forsøg, der allerede var
gennemført (F-001–F-006), og med de åbne idéer som forslag (F-007–F-011).

**Læringsløkke:** huller i udviklingssættet → ny tekst i videnbasen via normal forankring (primærkilde, V/T, review) → ny kørsel. Holdout-sættet bruges kun til måling, så forbedringen kan måles på opgaver, videnbasen ikke er skrevet efter. Regressioner (basis består, plugin ikke) peger på tekst i videnbasen, der vildleder.

## Multi-agent-arkitektur i lyset af forskningen (2026-10-20)
**Grundlag:** Google Research/MIT, "Towards a Science of Scaling Agent Systems" (dec. 2025, 180 konfigurationer): central orkestrator med validering holder fejlforstærkningen på ca. 4,4× mod 17× for uafhængige agenter; multi-agent giver +81 % på opgaver, der kan deles op, men −39 til −70 % på sekventiel planlægning; gevinsten falder, når én agent allerede løser over ca. 45 %, og koordineringen koster mest i værktøjstunge opgaver. Apple/Stanford, "Multi-Agent Teams Hold Experts Back" (ICML 2026): selvorganiserende hold ender op til 41 % under deres bedste ekspert, fordi de mægler kompromiser mellem eksperten og de andre i stedet for at følge eksperten. Apple/EPFL (sep. 2026): en minimal enkeltagent slog fire multi-agent-systemer på MLE-bench.

| Princip fra forskningen | Sådan er byg-eksperter bygget |
|---|---|
| Central orkestrator med validering | Projektlederen orkestrerer; fagagenter taler aldrig med hinanden; hver leverance valideres af en uafhængig kontrolagent |
| Parallelt kun, hvor opgaven kan deles op | Fase 1 og uafhængige fag kører parallelt; afhængige fag og returer på samme snitflade i rækkefølge |
| Sekventiel planlægning i én agent | Tidsplan, montage, budget og kontrolplan (fase 3) laves af projektlederen alene, ikke af fagene |
| Følg eksperten, mægl ikke | **Ny:** domæneforrang ved konflikter mellem fag (`koordinering.md`): ejerfaget har forrang i sit domæne, ingen mellemløsninger eller gennemsnit, og indvendinger går til ejerfaget – ikke til debat mellem fagene. Eval-casen `byg/evals/konflikt-domaeneforrang` |
| Værktøjstunge opgaver i én agent | `statiker` og `bim-modelloer` deles ikke op i flere agenter. Deterministiske værktøjer er kontrollen (`fem.py`/`statik.py`-genkørsel, `bim.py tjek` og `sammenlign`); hjælpeagenter kun til uafhængig verifikation |
| Ekstra agenter skal fange fejl, den enkelte ikke fanger | **Ny:** kontrol-armen (`scripts/kontrol_ab.py`) måler kontrollens præcision, recall og nettogevinst på eksamenssættet, så kontrolniveauet pr. fag kan sættes efter data |

**Målt (2026-10-20, F-012, én kørsel af udviklingssættet, kontrol på Sonnet uden internet):**

| Fag | Bestået uden → med kontrol | Forkerte svar fanget | Rigtige svar afvist (heraf skadet af returen) | Pris pr. bestået |
|---|---|---|---|---|
| el | 72 → 70 af 75 | 0 af 3 | 4 (2) | 0,071 → 0,132 $ |
| vvs | 68 → 68 af 72 | 0 af 4 | 2 (0) | 0,074 → 0,108 $ |

Kontrollen fangede ingen af de 7 forkerte svar, og alle 6 afvisninger ramte rigtige svar. Halvdelen af de falske fund gjaldt fagagentens påstand om, at en regel var "efterprøvet mod sik.dk/bygningsreglementet.dk", som kontrollen ikke kunne efterprøve. Ét fund var en faglig fejl i kontrollen selv (RCD-krav i eksisterende installationer). Forbehold: eksamen er korte opgaver med facit, og kontrollen kørte uden internet. I rigtige sager kan kontrollen efterprøve mod primærkilder og fange fejl i grænseflader, sagsforhold og helhed, som eksamen ikke måler. Næste skridt: sammenlign med returandelen i rigtige sager (`forbrug.py`), og lad fagagenten kun skrive "efterprøvet", når den selv har efterprøvet i denne leverance.

**Konsekvens for kontrolniveauet:** Eksamen viser, at fagagenten består 87–100 % af udviklingsopgaverne. Over Googles tærskel på ca. 45 % skal kontrollen bevise sin værdi: lav præcision betyder returer for intet. Kontrol-armen afgør pr. fag, om `let` kontrol skal beholdes, gøres til stikprøve eller kun bruges ved sikkerhedsfunktioner. Ændringer i kontrolniveau besluttes først ud fra målingen (forsøgsloggen) og returandelen i rigtige sager (`forbrug.py`).

## Videnmodel
Fagviden (gælder alle huse) og sagsviden (gælder ét hus) holdes adskilt. Hver oplysning står ét sted med kilde og dato.

| Lag | Slags | Placering | Livscyklus |
|---|---|---|---|
| Kanon | Fagviden | `plugins/*/skills/*/references/` | Versioneret i repoet; review før ændring |
| Agenthukommelse | Fagviden, ikke forankret endnu | `~/.claude/agent-memory/<agent>/` (memory: user), én mappe pr. fag | Fagagenten kuraterer selv; aldrig sagsdata |
| Videnbank | Lokal fagviden og sagsindeks | `${CLAUDE_PLUGIN_DATA}/videnbank/` (byg) | Overlever plugin-opdateringer; brugeren accepterer |
| Ejendomskort | Sagsviden om huset (lang) | `byg-sager/ejendomme/<ejendom-id>.md` | Så længe huset; kun projektlederen skriver; afsnit pr. fag |
| Sagsmappe | Sagsviden om projektet (kort) | `byg-sager/<sag-id>/` i arbejdsmappen | Pr. projekt; høstes ved afslutning |

**Lagdeling uden ekstra mekanik (vurderet 2026-10-04):** kun indekset (agentens `MEMORY.md`, skill-indgangen) ligger i konteksten; resten læses afsnitsvis. Platformen giver hver fagagent sin egen hukommelsesmappe, og et fag læser kun sit eget afsnit af ejendomskortet. En fuld lagmodel med budgetter, forfremmelse og hook-håndhævelse blev fravalgt: hukommelse er 3–5k tokens pr. fagkørsel, og der var ingen krydslæsninger mellem fag. Den bygges først, hvis `scripts/forbrug.py` viser et reelt problem. Gevinsten ligger i korrekthed: husets fakta ét sted og fast erfaringshøst, når en sag afsluttes.

## Dataseparation
Repoet er privat indtil videre (GitHub: `savnik/byg-eksperter`), men det skal offentliggøres på sigt, og hele historikken følger med. Reglerne gælder derfor allerede nu, som var det offentligt. Konkrete sager, brugerens data og hemmeligheder må aldrig komme i det.

| Zone | Hvor | Må indeholde | Må aldrig |
|---|---|---|---|
| **Repo (privat, offentliggøres)** | Dette repo | Generisk faglig viden, skabeloner, kode og testdata (evals, testadresser, fixtures) | Sager, sag-id'er, tekst fra sagsmapper, ejeroplysninger, hemmeligheder |
| **Brugerdata (lokalt)** | Sagsmapper: `byg-sager/` i brugerens arbejdsmappe · Videnbank: `${CLAUDE_PLUGIN_DATA}/videnbank/` · Agenthukommelse: `~/.claude/agent-memory/` · Kontroltilstand: `${CLAUDE_PLUGIN_DATA}/kontrol/` | Alt om de konkrete sager | Ligge i repoet eller i `${CLAUDE_PLUGIN_ROOT}` |
| **Hemmeligheder (lokalt)** | `~/.config/<plugin>/` (chmod 600) eller miljøvariabler | API-nøgler | Stå i kode, logs, output, sagsmapper, commits eller PR'er |

**Overgangen sag → kanon** er det eneste sted, hvor viden flytter fra brugerdata til repoet. Den sker via forankringskøen (`/byg:erfaring`), og forslaget skal være generaliseret. Det må ikke indeholde sag-id, adresse, navne, firmaer, datoer, beløb eller mål fra sagen, kun den faglige pointe og kilden (norm, RCA-kategori). Sag-id'et står i forankringskøen, som er lokal, ikke i repoet.

**Håndhævelse:** `scripts/tjek_data.py` kører i `valider.py` og som git pre-commit-hook (`git config core.hooksPath scripts/hooks`). Den afviser:
- sagsmapper, sagsfiler, rapporter og PDF'er i repoet
- API-nøgler (den lokale nøgle og generiske mønstre)
- sag-id'er fra den lokale videnbank og termer fra `~/.config/byg-eksperter/private-termer.txt`
- tekstlinjer kopieret fra de sagsmapper, der er registreret i videnbankens `sager.md` (kolonnen Sti) eller i `~/.config/byg-eksperter/sagsmapper.txt`

De lokale kilder findes ikke i CI. Der kører kun strukturtjek og nøglemønstre. Tjek derfor altid lokalt før push.

## Platformnoter (verificeret september 2026, Claude Code 2.1.282)
- Plugin-agenter ignorerer `hooks`, `mcpServers`, `permissionMode` og `initialPrompt` i frontmatter → håndhævelse sker via pluginets `hooks/hooks.json`.
- `memory` på en agent tilføjer automatisk Write/Edit → kontrolagenter har ingen memory.
- Subagenter kan nestes (standard 3 lag); plugin-agenter hedder `<plugin>:<agent>`.
- PreToolUse kan afvise via `permissionDecision: deny`; SubagentStop/Stop kan blokere med `decision: block`; `stop_hook_active` forhindrer uendelige løkker; exit 1 blokerer ikke.
- claude.ai-chat kører hverken subagenter eller hooks; Cowork kører begge (hooks bør testes manuelt).
- Cowork installerer `.plugin`-filer (zip af plugin-mappen) uden afhængighedsopløsning → samlet pakke `byg`.
- Plugins med `bin/` kan ikke bruges i Cowork → ingen `bin/`.

## Begrænsninger og risici
- Normer bag betalingsmur (DS m.fl.) kan ikke efterprøves direkte; kontrollen skal da skrive det under `usikkerheder`.
- Punkter markeret T er ikke verificeret; se "Roadmap".
- Hooks kræver python3; uden python3 er loopet kun instruktionsbaseret.
- Stop-hooken blokerer én gang pr. stop (for at undgå uendelige løkker) – en model kan i princippet afslutte ved andet forsøg.
- Kontrolagentens strenghed skal kalibreres på rigtige sager (afvisningsrate, fund pr. runde, kontrolsvigt).
- Agentkontrol er ikke lovpligtig kontrol og ændrer ikke ansvarsforhold.

## Roadmap
1. Verificér T-punkter (murer: KC-recepter, DS/EN-udgaver, riller, kvartsstøv; tømrer: C18/C24, NTR, vinduesmontage, brand i småhuse; netselskab; skorstensfejer) og markér V med dato.
2. Forbedringer via CI-agenten (`claude --agent ci-forbedring`), først F-007 (mål støjen, så beslutningsreglens grænser bliver empiriske). Udbyg eksamenslaget til de øvrige fag; kør evals for alle plugins og loop-evalen med `byg-team` installeret; tilføj eval-cases fra første RCA'er.
3. Test hooks i Cowork med den samlede pakke.
4. Kalibrér kontrollen: mål afvisningsrate, antal runder og kontrolsvigt pr. fag; justér rubric-versioner.
5. Nye fag via `scripts/nyt_fag.py` (fx kloak, tag, gulv) – altid med kontrolagent.
