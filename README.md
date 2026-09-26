# byg-eksperter

Danske byggefaglige ekspertagenter til Claude Code og Claude Cowork: en **projektleder**, der interviewer, planlægger og koordinerer, **fagagenter på mesterniveau** (vvs, el, murer, ventilation, maler, tømrer) og en **uafhængig kvalitetskontrol** med én kontrolagent pr. fag. Hver leverance kontrolleres hårdt og kildebaseret. Afviste leverancer sendes retur med fund, og efter 3 afviste forsøg stoppes der med root cause-analyse.

> Agenterne rådgiver og planlægger. De erstatter ikke autoriserede håndværkere, certificerede rådgivere, lovpligtige kontroller eller kommunens byggesagsbehandling. Viden markeret **T** skal verificeres, før den bruges som krav.

## Plugins
| Plugin | Indhold |
|---|---|
| `byg-team` | Meta-plugin – installerer alle nedenstående |
| `byg` | Projektleder-skill og -agent, kommandoer `/byg:…`, sagsmappe og videnbank |
| `byg-kontrol` | 7 kontrolagenter (6 fag + projekt), kontrolviden, hooks der håndhæver loopet |
| `byg-data` | Skill `ejendomsdata`: henter BBR, matrikel, lokalplan, fredning, jordforurening, grundvand, klima, energimærke og vurdering ud fra en adresse (Python-stdlib-script, ingen persondata). Valgfri gratis Datafordeler-nøgle i `DATAFORDELER_API_KEY` eller `~/.config/byg-data/datafordeler_api_key` – aldrig i repoet |
| `byg-vvs` · `byg-el` · `byg-murer` · `byg-ventilation` · `byg-maler` · `byg-toemrer` | Fagagent, videnbase (normgrundlag, faglig praksis, tjeklister, erfaringsblade), hukommelse og evals |

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
1. Hver opgave får et leverance-ID `<sag-id>/<fag-id>/<nr>` (første linje i prompten: `LEVERANCE: …`).
2. Fagagenten leverer et fagnotat med kilder.
3. Fagets kontrolagent (Opus, kun læse- og søgeværktøjer, egen kontrolviden, ingen adgang til fagagentens ræsonnement) laver et hårdt review og afgiver en JSON-dom: **godkendt** eller **afvist** med fund klassificeret som kritisk, væsentlig eller mindre – blokerende fund skal have krav, kilde og evidens.
4. Afvist → fundene sendes ordret retur til fagagenten. Højst 3 forsøg.
5. 3. afvisning → stop, root cause-analyse i `kvalitet/RCA-….md`, eskalering til brugeren og læring i forankringskøen.
6. Projektlederens egne leverancer (projektgrundlag, samlet plan) kontrolleres af `projekt-kontrol`.

Hooks i `byg-kontrol` håndhæver: leverance-ID, rækkefølge (fag før kontrol), korrekt kontrolagent, gyldig dom, maks. 3 forsøg, ingen ændring af godkendte leverancer uden nyt ID, og ingen afslutning af sessionen med ukontrollerede eller afviste leverancer eller manglende RCA. Domme gemmes i `<sagsmappe>/kvalitet/`, tilstand og log i pluginets datamappe. Status: `python3 <byg-kontrol>/hooks/kontrol_gate.py status`.

I **claude.ai-chat** kører hverken subagenter eller hooks; der markeres svar som "IKKE UAFHÆNGIGT KVALITETSKONTROLLERET".

## Viden og forankring
1. **Kanon** i pluginenes `references/` (normgrundlag med status V/T, faglig praksis, tjeklister, erfaringsblade) og kontrolviden i `byg-kontrol`.
2. **Agenthukommelse** pr. fagagent (`memory: user`).
3. **Videnbank** i projektlederens datamappe: sagsindeks, lokale erfaringsblade, forankringskø.
4. **Sagsmappe** pr. projekt.

`/byg:erfaring` høster erfaringer og RCA-læring; accepterede kanon-kandidater indarbejdes i repoet med ny version.

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
tests/test_kontrol_gate.py   tests af kontrol-hooken
tests/test_tjek_data.py      tests af dataseparationen
tests/live-testsag.md        end-to-end testsag med tjekpunkter til en rigtig Claude Code-session
```
Efter ændringer: `python3 scripts/sync_protokol.py && python3 scripts/valider.py --claude`.

Evals (kræver login og koster tokens): `claude plugin eval ./plugins/byg-vvs`. Loop-evalen `plugins/byg/evals/kontrol-loop-vvs` kræver, at `byg-team` er installeret.

Se `ARKITEKTUR.md` for designbeslutninger, platformnoter og roadmap.
