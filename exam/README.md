# Eksamenslaget

Et fast opgavesæt pr. fag, som fagagenten testes mod. Opgaverne er bygget på de **officielle læringsmål** (uddannelsesordningen for svendeuddannelsen og indholdskravene til autorisation), ikke på videnbasen. Eksamenslaget måler, hvad agenten kan. Evals (`plugins/*/evals/`) tester enkelte scenarier og uddelegering.

Laget ligger uden for `plugins/`, så det aldrig pakkes med pluginet, og agenten kan ikke læse facit under kørslen.

## Formål
1. **Dækning:** hvert læringsmål i agentens rolle har opgaver. Mål uden for rollen står med en begrundelse.
2. **Huller:** opgaver, agenten ikke består i udviklingssættet, er kandidater til ny tekst i videnbasen.
3. **Måling:** basismodellen (uden plugin) sammenlignes med fagagenten (med videnbase). Det giver gevinst, huller og regressioner (hvor videnbasen vildleder).
4. **Regressionstest:** sættet køres igen, når videnbasen eller agentprompten ændres.

## Regler
- **Holdout bruges kun til måling.** Holdout-opgaver må aldrig være grundlag for ny tekst i videnbasen eller i agentprompten. Ellers måler sættet kun hukommelse. Hvert læringsmål har mindst én opgave i hvert sæt. En holdout-opgave skal teste en anden regel, formel eller situation end udviklingsopgaverne til samme mål. Ellers lærer videnbasen svaret via udviklingssættet. Det gælder også på tværs af mål: et holdout-kriterium må ikke stå som facit, distraktor eller begrundelse i en udviklingsopgave.
- **Svaret må ikke kunne gættes.** Valgmulighederne blandes ved kørsel (stabilt pr. opgave-ID), så facits bogstav betyder ikke noget. Facit må ikke være systematisk den længste eller mest nuancerede mulighed. `check` advarer, når det gælder for mere end 40 % af valgopgaverne.
- **Viden skrives kun, hvor agenten fejler.** Det gælder udviklingssættet, og teksten skrives efter normal forankring: primærkilde, V/T og review. Opgaven må ikke skrives af.
- **Facit skal være efterprøvet** mod en primærkilde (retsinformation.dk, bygningsreglementet.dk, sik.dk osv.). `status` er `V <dato>` når facit er efterprøvet, ellers `T`. T-opgaver giver en advarsel og skal verificeres eller omformuleres.
- **Egne formuleringer.** Opgaverne er skrevet til dette repo. Der er ikke kopieret fra lærebøger eller officielle prøvesæt (de er fortrolige). Repoet offentliggøres.
- **Ét skriver pr. fil.** Opgaverne kan ligge i flere `tasks*.json`, som valideres samlet.

## Filer
```
exam/<fag>/
  learning-goals.json   kilder og læringsmål (ordret med kilde), rolle i/uden
  tasks*.json       {"opgaver": [...]}
  results/            kørselsresultater (ignoreres af git)
```

### Læringsmål
`{"id": "EL-KM-01", "kilde": "<kilde-id> <sted>", "niveau": "svend|mester", "tekst": "...", "rolle": "i|uden", "begrundelse": "..."}`. `begrundelse` er krævet ved `uden`.

### Opgave
| Felt | Indhold |
|---|---|
| `id` | Unikt, fx `EL-001` |
| `maal` | Liste af læringsmål-ID'er, opgaven tester |
| `saet` | `udvikling` eller `holdout` |
| `type` | `valg` (ét rigtigt svar), `tal` (beregning), `fri` (fagligt skøn, bedømt af censor-LLM) eller `case` (mesteropgave i flere dele) |
| `niveau` | `svend` eller `mester` |
| `spoergsmaal` | Selvstændig opgavetekst med alle nødvendige data |
| `valgmuligheder` | `valg`: `{"A": "...", "B": "...", "C": "...", "D": "..."}` |
| `facit` | `valg`: bogstav · `tal`: `{"vaerdi": 10.2, "enhed": "A", "tolerance_pct": 3}` · `fri`: `null` |
| `kriterier` | `fri`: liste af krav, der alle skal være opfyldt for bestået. Kriterierne kræver fagligt indhold. En henvisning i parentes er censorens kilde og skal ikke citeres. Skal svaret nævne en bestemt regel, så skriv det udtrykkeligt ("henviser til …") og kun der, hvor henvisningen er det, der testes |
| `fail_hvis` | `fri` (valgfri): forhold, der giver ikke bestået |
| `begrundelse` | Kort forklaring af facit |
| `kilde` | Primærkilde med sted og URL |
| `status` | `V 2026-10-17` (efterprøvet) eller `T` |

### Case (mesterniveau)
En case er ét scenarie med 2–8 dele, fx projektering eller dimensionering i flere trin, valg af beskyttelse og ansvar og tilsyn. `spoergsmaal` er scenariet med alle data. `dele` er en liste af `{"del": "a", "type": "tal|valg|fri", "spoergsmaal": "...", ...}` med samme facit- og kriteriefelter som de enkelte typer. Regne- og valgdele rettes deterministisk ud fra `SVAR a:` osv. Fri-delene bedømmes samlet af censor-LLM'en, del for del. Casen er bestået, når andelen af beståede dele er mindst `bestaa_andel` (standard 0,6, som ca. 60 af 100 point ved de skriftlige prøver). Rapporten gemmer hver dels resultat og casens point. Alle dele vises samtidig. En senere del må derfor ikke afsløre facit i en tidligere del, fx ved at nævne den rigtige løsning.

## Kørsel
```
python3 scripts/exam.py check                         # format og dækning (kører også i validate.py)
python3 scripts/exam.py show electrical --answer-key > /tmp/el.md
python3 scripts/exam.py run electrical                        # udviklingssættet, kun plugin-armen; basis genbruges
python3 scripts/exam.py run electrical --only-failed          # kun de opgaver, plugin-armen ikke bestod sidst
python3 scripts/exam.py run electrical --repeat-free 3        # fri-opgaverne tre gange (majoritet), mod støj
python3 scripts/exam.py run electrical --set holdout --release --plugin-rev <før>   # før/efter en ændring
python3 scripts/exam.py run electrical --arm base             # kun når modellen er skiftet
python3 scripts/exam.py report exam/electrical/results/<fil>.json
python3 scripts/exam.py regrade exam/electrical/results/<fil>.json --only-free   # ret gemte svar igen efter ændret rettemaske
```

### Effektiv brug
- **Basis genbruges.** Basis-armen afhænger ikke af videnbasen. `run` kører derfor kun plugin-armen, og rapporten bruger det nyeste basis-svar pr. opgave. Basis køres kun igen, når modellen skiftes.
- **Luk et hul med `--only-failed`.** Kør kun de opgaver, der fejlede. Det koster få cent i stedet for ca. 6 $ for hele sættet.
- **Holdout kun ved udgivelse.** Holdout kræver `--release`. Kør det før og efter en ændring af videnbasen med `--plugin-rev`, så sammenligningen sker på lige vilkår. Rapporten viser aldrig ID'erne på holdout-fejl.
- **Kontekst.** Rapporten viser videnbasens størrelse, input-tokens, tid og ture pr. opgave samt pris pr. bestået opgave. Ny viden skal forbedre bestået-andelen mere, end den øger prisen pr. bestået opgave. Er det ikke tilfældet, skal teksten skæres ned.
- **Rigtige sager.** Eksamen måler ikke returer i kontrol-loopet. Sammenlign derfor returandelen før og efter en udgivelse med `python3 scripts/usage.py --until <udgivelsesdato>` og `--since <udgivelsesdato>`.

`run` kører hver opgave headless (`claude -p`) i en tom mappe uden brugerens plugins og uden internet. `basis` (`--arm base`) er modellen alene. `plugin` er fagagenten (`--agent`) med en kopi af pluginet uden afhængigheder. Valg- og talopgaver rettes deterministisk ud fra linjen `SVAR:`. Fri opgaver bedømmes af en censor-LLM efter kriterierne. Kørslen koster tokens.

Plugin-armen får læseadgang til sin plugin-kopi (`--add-dir`), men ikke til resten af filsystemet, så facit i `exam/` kan ikke læses. `--plugin-rev <commit>` kører pluginet, som det var i en git-revision. Det bruges til at måle en ændring af videnbasen før og efter under samme vilkår.

Plugin-armen kører som standard **uden** fagagentens lokale hukommelse (`memory: user` fjernes i kopien). Eksamen måler altså pluginet alene: det, der er forankret i repoet, og ikke erfaringer fra brugerens egne sager i `~/.claude/agent-memory/`. `--med-hukommelse` måler plugin og lokal hukommelse samlet, fx for at se, hvad hukommelsen bidrager med, før den forankres. Agenten har under eksamen kun læseværktøjer, så den kan ikke skrive i hukommelsen.

## Kontrol-armen
Eksamen måler fagagenten alene. `scripts/review_ab.py` måler, hvad kvalitetskontrollen lægger oven i: fagagenten svarer, fagets kontrolagent dømmer svaret uden at kende facit, og ved afvisning retter fagagenten én gang ud fra de blokerende fund. Både første og rettede svar rettes efter facit.

```
python3 scripts/review_ab.py run electrical --parallel 2                  # hele udviklingssættet (ca. 2–3 × plugin-armen)
python3 scripts/review_ab.py run electrical --id EL-045,EL-221             # udvalgte opgaver
python3 scripts/review_ab.py run electrical --review-model opus --level full
python3 scripts/review_ab.py report exam/electrical/results/review/<fil>.json
```

Rapporten krydser dom og facit: **fanget** (forkert svar afvist, rettet eller ej), **overset** (forkert svar godkendt), **falsk afvisning** (rigtigt svar afvist, bevaret eller skadet af returen) og godkendt korrekt. Dertil præcision (andel afvisninger, der ramte en reel fejl), recall (andel forkerte svar, kontrollen fangede), netto (rettet − skadet) og pris pr. bestået opgave med og uden kontrol. Kun udviklingssættet bruges. Kontrollen kører på en kopi af `byg-review` uden hooks og uden internet, så den kan ikke efterprøve mod primærkilder som i rigtige sager. Resultaterne ligger i `results/review/` og indgår ikke i `exam.py`'s rapporter.

Fortolkning: fagagenten består allerede ca. 90 % eller mere, så der er få forkerte svar at fange, og recall er usikker på ét fag. Præcisionen (falske afvisninger) er det stabile tal. Kør mindst to fag, før kontrolniveauet ændres, og sammenlign med returandelen i rigtige sager.

## Forbedringsforsøg
Forbedringer laves som forsøg med CI-agenten (`claude --agent ci-improvement`) eller i hånden med `scripts/experiment.py`.
Hvert forsøg har én hypotese, én variabel, en måling før og efter, en beslutning og en læring.

| Fil | Indhold |
|---|---|
| `experiments.json` | Forsøgsloggen: alt, der er afprøvet. Felterne er hypotese, kategori, målopgaver, `rev_foer` og `rev_efter`, målinger pr. fag og gruppe, beslutning, begrundelse og læring. Forslag står der også |
| `benchmark.json` | Det aktuelle udgangspunkt pr. fag og gruppe (sæt × opgavefil), med kilde (forsøg @ revision). Det opdateres, når et forsøg afsluttes med `behold` |

En gruppe er `<sæt>/<opgavefil>`, fx `udvikling/opgaver-c` (AK). For holdout gemmes kun antal, beståede, pris og
en hash af ID-listen. For udvikling gemmes også de fejlede ID'er, så `status` kan vise udestående huller, og hvilke
forsøg der allerede har ramt dem.

```
python3 scripts/experiment.py status                      # benchmark, åbne forsøg, forslag og huller
python3 scripts/experiment.py search varmepumpe            # er idéen afprøvet før?
python3 scripts/experiment.py new --trade plumbing --category videnbase --hypothesis "…" --tasks VVS-035
python3 scripts/experiment.py measure F-012 --before <resultatfiler>    # og senere --after
python3 scripts/experiment.py assess F-012                 # beslutningsreglen
python3 scripts/experiment.py close F-012 --decision keep --learning "…"
python3 scripts/exam.py answers plumbing --id VVS-035       # agentens svar og censorens bedømmelse (kun udvikling)
```

**Beslutningsreglen** (`assess` i `experiment.py`) gælder for kategorierne videnbase, prompt og model. Den sammenligner
plugin-armen før og efter på de samme opgaver. Er det ikke de samme opgaver, indgår gruppen ikke.
- **behold:** mindst 2 flere beståede i alt, holdout målt før og efter, ingen gruppe faldet 2 eller flere, og prisen
  pr. bestået steget højst 10 %. Eller samme kvalitet og prisen pr. bestået faldet mere end 10 %.
- **forkast:** en gruppe er faldet 2 eller flere (også AK-sættene), eller prisen er steget uden gevinst.
- **uafklaret:** inden for støj, holdout mangler, eller der er forskellige opgaver før og efter. Gentag med
  `--repeat-free 3`, eller forkast.

Rettemaske, opgaver, værktøj og nulmåling afgøres med en skriftlig begrundelse. Afviger beslutningen fra reglen,
kræves `--begrundelse`. Grænserne (`NOISE_TASKS = 2`, `PRICE_TOLERANCE = 10 %`) bygger på én kørsels støj, og
forslag F-007 skal fastlægge dem empirisk. Holdout har et budget på 8 målinger pr. fag (`HOLDOUT_BUDGET`). Hver
beslutning på holdout lækker lidt, så når budgettet er brugt, skal der skrives nye holdout-opgaver.

**Holdout-vagten** (`scripts/hooks/holdout_guard.py`, en hook i CI-agentens frontmatter) afviser direkte læsning af
`tasks*.json` og `results/`, Grep med indhold i `exam/` og rekursiv søgning uden sti. Agenten ser kun
udviklingssættet, gennem `exam.py show --set development`, `exam.py answers`, `report` og `experiment.py`. Rettelser i
opgavefilerne uddelegerer den til en anden agent.

## Erfaringer: læs før du udbygger eller måler pluginet
Målt 17.–18. okt. 2026 på el, vvs og ventilation (svende- og AK-niveau). Tallene står i `ARCHITECTURE.md`, afsnittet "Eksamenslag".

### Hvad pluginet bidrager med
- **Gevinsten kommer fra videnbasen og fra konkrete danske regler.** Det gælder grænseværdier, paragraffer og gør-det-selv-grænser, fx CO ≤ 500 ppm, 13 A foran 10 A-stikkontakter, T250-aftræk og Ik min = 5 × In. Dem gætter basismodellen forkert, og de koster dyrt i en sag. På svendesættene steg pluginet fra 80–86 % til 94 %. På holdout gik el fra 71 % i basis til 87 %.
- **Agentprompten alene giver næsten intet.** Plugin uden adgang til videnbasen lå på niveau med basis.
- **Mesterniveauet (AK) giver ingen gevinst.** Basis og plugin ligger ens, 86–94 %. Projektering, dimensionering og skøn kan modellen i forvejen. Byg ikke videnbase til mesterniveauet. Brug AK-sættene som regressionsværn.
- **Pluginet koster næsten intet ekstra.** Det er lidt billigere pr. opgave end basis og ca. 3 s langsommere. Prisen pr. bestået opgave er den rigtige målestok for, om ny viden betaler sig.
- **Eksamen måler ikke det hele.** Kontrol-loopet, sagsmappen og koordineringen mellem fag indgår ikke. Den værdi måles på rigtige sager med `usage.py --until/--since` omkring en udgivelse, som returandel og forbrug.

### Fremgangsmåde, når videnbasen skal udbygges
1. Kør `run <fag>` for udviklingssættet. Basis genbruges.
2. Gennemgå hvert hul, og afgør, om det er et **reelt videnshul** eller en **fejl i rettemasken**: et kriterium, der er for snævert, sammensat eller fagligt forkert. Ca. halvdelen af hullerne i fri-opgaver var fejl i rettemasken. Når basis og plugin begge vælger samme forkerte svar, har modellen typisk en fast fejlopfattelse, men tjek facit først.
3. Giv kun forfatteren af videnbasen udviklingsopgaverne, aldrig `exam/` og aldrig holdout. Udtræk hullerne til en fil.
4. Efterprøv hver regel selv mod primærkilden. Skriv den generaliseret og kort, med V-mærke. Uden primærkilde skrives intet.
5. **Tjek indgangene.** Agenten skal faktisk læse reglen. Gasreglerne blev fx først brugt, da agentprompten og `SKILL.md` pegede på dem, fordi agenten opfattede gas som uden for sit mandat.
6. Kør `run <fag> --only-failed`. Kør derefter holdout med `--release --plugin-rev <før>` og igen med den nye version, så før og efter måles på lige vilkår.
7. Stop, når prisen pr. bestået opgave ikke længere falder.

### Faldgruber ved måling
- **`dontAsk` og `--add-dir`.** `claude -p` i `dontAsk` afviser Read og Grep uden for arbejdsmappen. Uden `--add-dir` til plugin-kopien kan agenten ikke læse sin videnbase, og målingen tester kun prompten. Det er sket én gang. Testen `test_plugin_arm_can_read_its_plugin` dækker det nu.
- **Agentens hukommelse.** Den indlæses kun med `--med-hukommelse`. Ellers måles pluginet med lokale erfaringer fra sagerne.
- **Kontogrænsen.** Headless-kørsler deler kvote med sessionerne. Kør med højst `--parallel 2–3`. Ramte grænser markeres som kørselsfejl og tælles ikke med. Kør dem igen med `--id`.
- **Støj.** Én kørsel giver ±2 fri-opgaver pr. sæt. Forskelle på en enkelt opgave er støj. Brug `--repeat-free 3`, før du konkluderer. Tre kørsler af vvs under ens betingelser gav 28, 29 og 27 af 30 i samme gruppe (F-015/F-016), så én kørsel kan give et falsk forkast.
- **Effort i frontmatter virker ikke i eksamen.** `claude -p --agent` ignorerer `effort:` i agentfilen, så plugin-armen kører med modellens standard (Opus 5.5: medium). I rigtige sager kører fagagenten som subagent med frontmatter-effort. Et effort-forsøg er derfor tomt, indtil `exam.py` sender `--effort` videre (F-016, forslag F-017).
- **Hastighed i sager måles ikke af eksamen.** Eksamen er enkeltspørgsmål uden web, uden Write og med ca. 2 ture. Forsinkelse i sager (lange Write-blokke, web-opslag, kontrol-loop) skal måles med `usage.py` omkring en udgivelse (F-015). Én prompt kan svinge fra 1,6k til 68k output-tokens, så lange kald er en hale, der kun ses over mange kørsler.
- **Censor-LLM'en.** Den krævede paragrafcitater, til det blev forbudt i censorprompten. Sammensatte kriterier får fagligt gode svar til at dumpe. Hold ét krav pr. kriterium. Brug `regrade`, når rettemasken ændres.
- **Talparseren.** `parse_number` læser et dansk decimaltal med præcis tre decimaler (`0,867`) som tusindtal (867). Et korrekt svar kan derfor dumpe. Se `exam.py answers`, før et fald på en talopgave tolkes som en regression (F-023, forslag F-024).
- **Holdout-vagten gælder også underagenter.** CI-agenten kan i dag ikke få en underagent til at rette opgavefilerne, fordi vagten blokerer den også. Rettemaske- og opgaveforsøg kræver derfor en anden vej (F-021, forslag F-022).
- **Ufuldstændige målinger.** En måling, hvor opgaver mangler (kørselsfejl, afbrudt kørsel, `--only-failed`), siger kun noget om de opgaver, der blev kørt. Skriv i læringen, hvad der ikke blev målt. Et anslået tal (pris, tokens, tid) skal stå som "anslået" og må ikke afgøre et forsøg. Prisen tæller hele opgaven, også gentagne kald og censorens rettelse.
- **Regneværktøjer måles ikke.** Eksamensarmen har ingen Bash, så et script som `el.py` eller `statik.py` kører aldrig i eksamen. Eksamen måler kun pegerne og videnteksten om værktøjet, og de kan koste. I F-029 skrev agenten "dimensioneres med el.py" i en opgave om tavleudskiftning og glemte tilmeldingsspørgsmålet (EL-141 bestod 0 af 3 efter mod 2 af 3 før). Hold værktøjsteksten i en fil, der kun læses ved beregning. Værdien af selve værktøjet kræver opgaver, der faktisk kræver beregningen. Med `exam.py run --calc-tool` får plugin-armen Bash, låst af `scripts/hooks/exam_calc_guard.py` til fagets regneværktøj fra `trade-registry.json`, og Write til en .json-inputfil i opgavemappen. Resultatfilen får `-regn` i navnet. Standardmålingen er uændret uden Bash, så benchmarket kan stadig sammenlignes.
- **Loftet.** Opgaverne er skrevet af samme modelfamilie, som tager eksamen. Især mesteropgaver bliver derfor nemme for modellen. Konkrete tal og paragraffer er sværere at gætte og giver bedre adskillelse. Vil du have et reelt mål på mesterniveau, skal opgaverne skrives eller gennemgås af en fagperson.

### Faldgruber ved opgaveskrivning
To uafhængige kontrolrunder pr. sæt er nødvendige. Første runde fandt 1–4 fagligt forkerte kriterier pr. sæt og mange lækager. Typiske fejl:
- **Facit kan aflæses af formen.** Det er længst, det eneste med forbehold, eller altid B. Valgmulighederne blandes ved kørsel, og `check` advarer om længdebias.
- **Lækage til holdout.** Et holdout-krav står som facit, distraktor eller begrundelse i en udviklingsopgave, også under et andet mål.
- **En case afslører sig selv.** En senere del nævner svaret på en tidligere. `check` fanger direkte gentagelser, men ikke omskrivninger.
- **Et kriterium forbyder et anerkendt råd.** Eksemplet er en midlertidig prop i gulvafløbet under skybrud.
- **Forældede eller sekundære kilder.** Fx Bolius' gengivelse af gør-det-selv-reglerne, BEK-numre der er afløst, og regler med kommende udløbsdato (maskinforordningen 20/1-2027).

### Pris (oktober 2026)
| Hvad | Pris |
|---|---|
| Én opgave i én arm | ca. 0,07 $ |
| Fuldt udviklingssæt pr. fag og arm | ca. 4–6 $ |
| Før/efter for to fag på alle sæt | ca. 25 $ |
| `--only-failed` | cents |
| Opgaveskrivning med to kontrolrunder | ca. 6–8 agentkørsler pr. sæt |
