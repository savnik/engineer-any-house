# byg-eksperter

Danske byggefaglige ekspertagenter til Claude Code og Claude Cowork: en **projektleder**, der interviewer, planlægger og koordinerer, **fagagenter på mesterniveau** (vvs, el, murer, ventilation, maler, tømrer, statiker, BIM) og en **uafhængig kvalitetskontrol** med én kontrolagent pr. fag. Hver leverance kontrolleres hårdt og kildebaseret. Afviste leverancer sendes retur med fund, og efter 3 afviste forsøg stoppes der med root cause-analyse.

> Agenterne rådgiver og planlægger. De erstatter ikke autoriserede håndværkere, certificerede rådgivere, lovpligtige kontroller eller kommunens byggesagsbehandling. Viden markeret **T** skal verificeres, før den bruges som krav.

## Plugins
| Plugin | Indhold |
|---|---|
| `byg-team` | Meta-plugin – installerer alle nedenstående |
| `byg` | Projektleder-skill og -agent, kommandoer `/byg:…`, sagsmappe og videnbank |
| `byg-kontrol` | 9 kontrolagenter (8 fag + projekt), kontrolviden, hooks der håndhæver loopet |
| `byg-data` | Skill `ejendomsdata`: henter BBR, matrikel, lokalplan, fredning, jordforurening, grundvand, klima, energimærke og vurdering ud fra en adresse (Python-stdlib-script, ingen persondata). Valgfri gratis Datafordeler-nøgle i `DATAFORDELER_API_KEY` eller `~/.config/byg-data/datafordeler_api_key` – aldrig i repoet |
| `byg-vvs` · `byg-el` · `byg-murer` · `byg-ventilation` · `byg-maler` · `byg-toemrer` | Fagagent, videnbase (normgrundlag, faglig praksis, tjeklister, erfaringsblade), hukommelse og evals |
| `byg-statik` | Statiker (`statiker`): rådgivende om bærende konstruktioner – hvad er bærende, vægfjernelse, bjælker og vederlag, bjælkelag, tag, fundering, revner og sætninger, midlertidig understøtning og review af statisk dokumentation. Alle konkrete beregninger i en FEM-model med `fem.py` (PyNite: PNG-tegninger og interaktiv HTML, eget Python-miljø), lastopgørelse og håndkontrol med `statik.py` (Python-stdlib). Overslag mærkes altid som overslag; den statiske dokumentation til byggesagen udarbejdes af den ansvarlige statiker |
| `byg-bim` | BIM-modellør (`bim-modelloer`) og uafhængig sammenligner (`bim-sammenligner`), værktøjet `bim.py` (modelspec i YAML → IFC4 med IfcOpenShell, kontrol mod buildingSMART-regler/IDS/BBR, planer, snit, facader og 3D som PNG, afkodning af PDF-tegninger og sammenligning af tegning og model) og skill `tegningsimport`. Værktøjet opretter selv sit Python-miljø i `~/.local/share/byg-bim/venv` (`bim.py opsaet`, kræver netværk første gang) |

Fag-plugins og `byg` afhænger af `byg-kontrol`, så kontrollen altid følger med.

## Installation

**Claude Code (anbefalet)** – fra en lokal mappe eller et git-repo:
```
/plugin marketplace add ./byg-eksperter
/plugin install byg-team@byg-eksperter
```
eller i terminalen: `claude plugin marketplace add ./byg-eksperter` og `claude plugin install byg-team@byg-eksperter`. Genstart sessionen efter installation.

**Claude Cowork** – upload den samlede pakke `byg.plugin` (bygges med `python3 scripts/pak.py`). Den indeholder alle agenter, skills og hooks i ét plugin ved navn `byg`, så navnene bliver `byg:vvs-mester`, `byg:vvs-kontrol` og kommandoerne `/byg:nyt-projekt` osv.

Installér **enten** marketplacet **eller** den samlede pakke – ikke begge (begge hedder `byg`).

**Krav:** `python3` på PATH til hooks. Uden python3 fejler hooks ikke-blokerende; kontrol-loopet følges så kun via instruktionerne og håndhæves ikke.

## Brug
| Kommando | Formål |
|---|---|
| `/byg:nyt-projekt <beskrivelse>` | Interview → sagsmappe → kontrolleret projektgrundlag → fagplan |
| `/byg:koordiner [sag]` | Fagforespørgsler med kvalitetskontrol, integration og samlet plan |
| `/byg:status [sag]` | Fase, næste skridt, åbne spørgsmål og kontrolstatus |
| `/byg:spoerg <fag> <spørgsmål>` | Hurtigt fagspørgsmål med kontrolleret svar |
| `/byg:erfaring [sag]` | Høst erfaringer og RCA-læring til videnbanken |
| `/byg:nyt-fag <fag-id>` | Opret nyt fag med kontrolagent |

Projektlederen kan også køre som hovedagent: `claude --agent byg:projektleder`. Fagagenterne kan kaldes direkte (fx `@byg-vvs:vvs-mester`), men kaldet skal have en `LEVERANCE:`-linje, og svaret kontrolleres – hooken fortæller hvordan.

Sager gemmes i `byg-sager/<ÅÅÅÅ-MM-DD>-<navn>/` i arbejdsmappen.

## Kvalitetskontrol-loopet
0. Projektet kører i faser med gates (`byg/skills/projektleder/references/faser-og-gates.md`): **0** afklaring og Definition of Ready pr. fag → **1** dispositionsforslag → **2** design og design freeze → **manuel gate: brugeren godkender løsningen (`Godkend G2 <sag-id>`)** → **3** samlet plan (tidsplan, budget, montage) → **4** udbud og udførelse. Ændringer efter design freeze samles i `aendringer.md`. Ved G1 laver projektlederen grænsefladeregistret og prissætter fag uden agent. G2 kræver brugerens accept af åbne punkter. Hold points hedder `HP-<FAG>-n` fra start. Kontrolniveau `let` eller `fuld` efter fase og risiko.
1. Hver opgave får et leverance-ID `<sag-id>/<fag-id>/<nr>` (første linje i prompten: `LEVERANCE: …`).
2. Fagagenten leverer et fagnotat med kilder.
3. Fagets kontrolagent (Opus, kun læse- og søgeværktøjer, egen kontrolviden, ingen adgang til fagagentens ræsonnement) laver et hårdt review og afgiver en JSON-dom: **godkendt** eller **afvist** med fund klassificeret som kritisk, væsentlig eller mindre – blokerende fund skal have krav, kilde og evidens.
4. Afvist → de blokerende fund (kritisk og væsentlig) sendes ordret retur til fagagenten, som kun retter de berørte afsnit. Mindre fund sendes ikke retur. Højst 2 forsøg pr. runde. Forsøg 1 er det fulde review. Forsøg 2 tjekker kun lukning og regressioner (fund-fastlåsning). Kontrolniveauet (`let` eller `fuld`) følger opgavens risiko.
5. 2. afvisning → eskalering til brugeren. Skriver brugeren `Ny runde <leverance-id>`, følger en root cause-analyse med 5 Why-metoden i `kvalitet/RCA-….md`, læringen implementeres i fagagenten (hukommelse og repo), og en ny runde med 2 forsøg starter under samme leverance-ID. Højst 2 runder.
6. Projektlederens egne leverancer (projektgrundlag, samlet plan) kontrolleres af `projekt-kontrol`.
7. **BIM og tegningsimport:** en tegning afkodes først grundigt (`afkodning.yaml`, kontrolleret mod tegningen selv), derefter bygges modellen. Hjælpeagenten `bim-sammenligner` holder originalen op mod samme visning tegnet fra modellen og sender afvigelser retur til `bim-modelloer` (højst 3 sammenligninger, rettelser bruger ikke af kontrolforsøgene). Til sidst den formelle kontrol med `bim-kontrol`. Se skill `tegningsimport`.

Hooks i `byg-kontrol` håndhæver: leverance-ID, rækkefølge (fag før kontrol), korrekt kontrolagent, gyldig dom, fase-gate (plan i fase 3+ kun med godkendt designgrundlag), fund-fastlåsning (nye blokerende fund i forsøg 2–3 kræver `nyt_grundlag`), maks. 3 forsøg pr. runde og 3 runder, ny runde kun efter RCA med implementeret forbedring, ingen ændring af godkendte leverancer uden nyt ID, og ingen afslutning af sessionen med ukontrollerede eller afviste leverancer eller manglende RCA. Domme gemmes i `<sagsmappe>/kvalitet/`, tilstand og log i pluginets datamappe.

**Parallelle fag uden skrivekonflikter:** hver fil i sagen har én ejer. Et fag skriver kun sit eget notat, bilag og sine egne mapper. Ændringer i grænseflader, risici, kontrolplan og ejendomskort lægger faget som forslag i `forslag/`, og hooken fletter dem ind på rækkeniveau, når leverancen godkendes (med konfliktstop, hvis projektlederen har ændret de samme rækker imens). `byg-sager/` er et lokalt git-repo, som hooken committer til ved hver aflevering, dom og fletning. Kontrollens forsøg 2–3 får diffen siden sidste kontrollerede version. Repoet pushes aldrig; slå det fra med `BYG_GIT=0`. Status: `python3 <byg-kontrol>/hooks/kontrol_gate.py status`.

I **claude.ai-chat** kører hverken subagenter eller hooks; der markeres svar som "IKKE UAFHÆNGIGT KVALITETSKONTROLLERET".

**Hold sessionerne korte.** Hvert svar læser hele samtalen igen, så en lang session gør selv korte spørgsmål dyre. Brug én session pr. opgave, og fortsæt en sag i en ny session med `/byg:status <sag-id>`. Sagsmappen husker resten. Hooken minder dig om det, når samtalen passerer ca. 200k tokens. Mål forbruget ved at køre `python3 <byg-eksperter>/scripts/forbrug.py --siden <dato>` fra din arbejdsmappe.

## Viden og forankring
1. **Kanon** i pluginenes `references/` (normgrundlag med status V/T, faglig praksis, tjeklister, erfaringsblade) og kontrolviden i `byg-kontrol`.
2. **Agenthukommelse** pr. fagagent (`memory: user`).
3. **Videnbank** i projektlederens datamappe: sagsindeks, lokale erfaringsblade, forankringskø.
4. **Ejendomskort** pr. hus (`byg-sager/ejendomme/<ejendom-id>.md`): husets faste fakta med kilde og dato, delt i afsnit pr. fag og fælles for alle sager på ejendommen.
5. **Sagsmappe** pr. projekt.

Fagviden og sagsviden holdes adskilt: agenternes hukommelse er kun til fagviden. Når en sag afsluttes, høster projektlederen den (`/byg:erfaring`): husets fakta går til ejendomskortet, og fagviden går til videnbanken og forankringskøen. Accepterede kanon-kandidater indarbejdes i repoet med ny version.

## Data og privatliv
Sager og brugerdata ligger kun lokalt: sagsmapper i `byg-sager/` i din arbejdsmappe, videnbank og kontroltilstand i pluginets datamappe og API-nøgler i `~/.config/`. Intet af det kommer i pluginet. Læring fra sager kommer kun i repoet som generaliseret viden via `/byg:erfaring`. Se "Dataseparation" i `ARKITEKTUR.md`.

## Udvikling
```
faelles/protokol.md          fælles protokol for fagagenter
faelles/kontrolprotokol.md   fælles protokol for kontrolagenter
plugins/<plugin>/            plugins
skabelon/                    skabelon til nye fag (fag-plugin + kontrolagent + kontrolfil)
scripts/sync_protokol.py     indsætter protokollerne i agentfilerne (--check i CI)
scripts/nyt_fag.py           opretter et nyt fag og registrerer det overalt
scripts/valider.py           strukturtjek, navne, stier, protokoller, evals og hook-tests
scripts/tjek_data.py         dataseparation: ingen sager, brugerdata eller nøgler i repoet
scripts/hooks/pre-commit     kører tjek_data.py før hvert commit (git config core.hooksPath scripts/hooks)
scripts/pak.py               bygger dist/cowork/*.plugin, samlet byg.plugin og repo-zip
scripts/udgiv.py             udgivelse på main: hæver versioner ud fra versionsnoter/ og skriver CHANGELOG.md
versionsnoter/               én note pr. gren: hvilke plugins der ændres (patch/minor/major) og hvorfor
scripts/forbrug.py           måler token- og tidsforbrug fra de lokale transskripter (hovedtråd, fag, kontrol, retur, svarlængde)
scripts/effort_ab.py         A/B-test af agenternes effort med pluginets evals (koster tokens)
scripts/eval_fag.py          kører et fag-plugins evals uden byg-kontrol-afhængigheden (koster tokens)
tests/test_kontrol_gate.py   tests af kontrol-hooken
tests/test_tjek_data.py      tests af dataseparationen
tests/test_sagsflet.py       tests af skriveret pr. fag, forslag og fletning og git i byg-sager/
tests/test_regne_vagt.py     tests af regnevagten (statiker og statik-kontrol må kun køre statik.py og fem.py)
tests/live-testsag.md        end-to-end testsag med tjekpunkter til en rigtig Claude Code-session
```
Efter ændringer: `python3 scripts/sync_protokol.py && python3 scripts/valider.py --claude`.

**Parallelle sessioner** (flere Claude-sessioner i hver sin worktree):
- Én opgave = én worktree = én kortlivet gren. Rebase på `origin/main` før PR, og merge PR'erne én ad gangen.
- **Hæv aldrig versioner i en gren.** Læg en note i `versionsnoter/<gren>.md` (se `versionsnoter/README.md`). Efter merge kører du `python3 scripts/udgiv.py` på main. Pre-commit-hooken afviser versionsændringer uden for main (`BYG_UDGIV=1` tilsidesætter).
- `faelles/` og agentfilernes protokolblokke: konflikter i de genererede blokke løses ikke i hånden. Løs konflikten i `faelles/`, og kør `python3 scripts/sync_protokol.py`.
- Opgaver, der begge ændrer `faelles/`, `fagregister.json` eller `kontrol_gate.py`, køres efter hinanden, ikke parallelt.

Evals (kræver login og koster tokens): `python3 scripts/eval_fag.py byg-vvs`. Kør ikke `claude plugin eval ./plugins/byg-vvs` direkte: fag-plugins afhænger af `byg-kontrol`, som ikke findes i eval-sandkassen, og så indlæses pluginet slet ikke (evalen tester kun den bare model). Effort-sammenligning: `python3 scripts/effort_ab.py byg-vvs --effort medium`. Loop-evalen `plugins/byg/evals/kontrol-loop-vvs` kræver, at `byg-team` er installeret.

Se `ARKITEKTUR.md` for designbeslutninger, platformnoter og roadmap.
