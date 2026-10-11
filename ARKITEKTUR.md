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
| Maks. 3 forsøg pr. runde, derefter RCA, forbedring af fagagenten og ny runde (maks. 3 runder) | Hook-tilstand pr. leverance-ID med runde og forsøg; 4. forsøg afvises; Stop blokeres, indtil RCA-filen for runden findes; ny runde kræver en 5 Why-kæde (≥ 5 hvorfor-niveauer og en grundårsag) og 'Forbedring implementeret: ja' i RCA'en; 4. runde afvises og eskaleres; RCA-skabelonen fokuserer på, hvorfor forsøg 1 ikke var korrekt |

## Komponenter
```
byg-team ──(dependencies)──► byg, byg-kontrol, byg-vvs, byg-el, byg-murer, byg-ventilation, byg-maler, byg-toemrer
byg ─────────────────────────► byg-kontrol
byg-<fag> ───────────────────► byg-kontrol
```
- **Hovedtråden** (projektlederen eller Claude ved direkte brug) orkestrerer. Fagagenter har ikke Agent-værktøjet og kalder aldrig kontrollen selv.
- **Fagagenter:** `model: opus`, `effort: high`, `memory: user`, værktøjer Read/Write/Edit/Glob/Grep/WebSearch/WebFetch. Fælles protokol indsættes fra `faelles/protokol.md`.
- **Modelvalg (2026-09-26):** Fagagenterne kører på Opus med `effort: high`, fordi et afvist første forsøg koster en hel ekstra fag- og kontrolrunde (målt i en rigtig sag: Sonnet-fagagent 10 min, afvist med 8 væsentlige fund, rettelse 21 min). Kontrolagenterne har eksplicit `effort: high`, fordi Opus 5.5 ellers kører på `medium` som standard. Uafhængigheden sikres af adskilt kontekst, kontrolviden og værktøjer – ikke af modelforskel.
- **Kontrolagenter:** `model: opus`, `effort: high`, `color: red`, værktøjer Read/Glob/Grep/WebSearch/WebFetch, ingen `memory` (som ellers giver Write/Edit). Fælles kontrolprotokol indsættes fra `faelles/kontrolprotokol.md`.

## Kvalitetskontrol-laget
**Leverance-ID** `<sag-id>/<fag-id>/<nr>` binder fagkald, kontrolkald, domme og RCA sammen. Godkendte leverancer ændres kun under nyt ID (`-r2`). `ekstern/<emne>` bruges til rådgivende review af eksternt materiale uden loop.

**Dom** (sidste JSON-blok i kontrolagentens svar): `leverance_id, fag, forsoeg, dom, rubric_version, sagsmappe, fund[id, klasse, status, sted, paastand, krav, kilde, evidens, handling, eskaler], regressioner, efterproevet_mod_primaerkilde, usikkerheder, kontrolsvigt`. Godkendt ⇔ ingen åbne kritiske/væsentlige fund. Blokerende fund kræver krav, kilde og evidens.

**Faser og gates:** projektet går gennem fase 0 (afklaring og Definition of Ready pr. fag), 1 (dispositionsforslag), 2 (design → design freeze) og 3 (én samlet plan), derefter 4 (udførelse, ændringsstyring). Kontrolniveau `let` eller `fuld` efter fase og risiko. Formålet er, at planer ikke revideres, hver gang designet ændres, og at ændringer samles.

**Stabilitet og fund-fastlåsning:** rubric fryses i forsøg 1, som er det fulde review. Forsøg 2–3 tager kun stilling til tidligere fund og regressioner i ændrede afsnit. Et nyt blokerende fund kræver `nyt_grundlag` (regression / aendret_tekst / kritisk_sikkerhed), ellers sender hooken dommen retur. Oversete forhold rejses som mindre og under kontrolsvigt. Bestridte kritiske fund eskaleres til brugeren.

**Hooks** (`plugins/byg-kontrol/hooks/kontrol_gate.py`, python3, fail-safe):
| Hændelse | Regel |
|---|---|
| PreToolUse (Write/Edit) | Godkendte leverancer (sti fra kontrolkaldet) beskyttes: afvises for subagenter, advarsel i hovedtråden |
| PreToolUse (Agent/Task) | Kræver `LEVERANCE:`; fagkald → "afventer_kontrol"; ny fagversion før dom, forkert kontrolagent, 4. forsøg og ændring af godkendt leverance afvises; projektkontrol kræver `FASE:`, og i fase 3+ `DESIGNGRUNDLAG:` med godkendte fagleverancer |
| SubagentStop (fagagenter) | `fagkald_igang` → `afventer_kontrol` ved aflevering (leverance-ID fra agentens prompt). Genforsøg af afbrudt fagkald tæller ikke |
| SubagentStop (kontrolagenter) | Validerer dommen (inkl. `nyt_grundlag` på nye blokerende fund i forsøg 2–3); ugyldig dom sendes retur én gang; opdaterer status (godkendt / afvist / stoppet); gemmer dommen i `<sagsmappe>/kvalitet/` |
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
| Fuld indlæsning af sagsmappen og gentagne opslag af de samme kilder | **Målrettet læsning og genbrug:** Grep og relevante afsnit; fagforespørgslen peger på afsnit; `normer.md` og sagens domme før nye opslag. Kontrollen genbruger sine egne efterprøvede kilder og slår kun op i forsøg 2–3 ved nyt grundlag |
| Kontrol i baggrunden gav status-polling i hovedtråden | **Forgrund:** fag- og kontrolkald køres parallelt i forgrunden (flere Agent-kald i samme besked) |

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
Repoet er offentligt. Konkrete sager, brugerens data og hemmeligheder må aldrig komme i det.

| Zone | Hvor | Må indeholde | Må aldrig |
|---|---|---|---|
| **Repo (offentligt)** | Dette repo | Generisk faglig viden, skabeloner, kode og testdata (evals, testadresser, fixtures) | Sager, sag-id'er, tekst fra sagsmapper, ejeroplysninger, hemmeligheder |
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
2. Kør evals for alle plugins og loop-evalen med `byg-team` installeret; tilføj eval-cases fra første RCA'er.
3. Test hooks i Cowork med den samlede pakke.
4. Kalibrér kontrollen: mål afvisningsrate, antal runder og kontrolsvigt pr. fag; justér rubric-versioner.
5. Nye fag via `scripts/nyt_fag.py` (fx kloak, tag, gulv, statik-rådgivning) – altid med kontrolagent.
