# Root cause-analyse (RCA) – efter 3 afviste forsøg i en runde

Skrives af orkestratoren (projektlederen) til `<sagsmappe>/quality/RCA-<leverance-id med / erstattet af __>.md`. Fra runde 2 lægges `__round-<n>` til filnavnet.

**Formål:** Find ud af, **hvorfor fagagenten ikke kunne levere korrekt i første forsøg**, og gør fagagenten bedre, så det samme ikke sker igen. Analysen er blameless: fejlen ligger i systemet (agentens viden, metode, prompt og input), ikke i "agenten". Der ledes efter det, der skal ændres i fagagenten, ikke efter en skyldig.

**Metode: 5 Why (fem gange hvorfor) er obligatorisk.** Hver RCA skal have mindst én fuld 5 Why-kæde. Reglerne:
- **Start** i det konkrete problem: hvad forsøg 1 manglede (afsnit 2). Grupper fund med samme årsag i én kæde. Fund med forskellige årsager får hver sin kæde.
- **Hvert "hvorfor"** besvarer det foregående svar, ikke det oprindelige problem. Svaret skal være et faktum med evidens: en dom, fagnotatet, agentens prompt eller videnbase, eller fagforespørgslen. Et gæt tæller ikke. Mangler evidensen, så skriv "utilstrækkeligt grundlag – mangler: <hvad, og hvor det findes>", og stop kæden dér. Skriv aldrig, at noget er genskabt, målt eller afprøvet, hvis det ikke er gjort.
- **Mindst fem niveauer.** Stop ikke ved symptomet ("agenten glemte X"). Fortsæt, til svaret peger på noget i systemet, der kan ændres: fagagentens viden, metode, prompt eller input. Gå videre end fem, hvis femte svar ikke er handlingsbart.
- **Grundårsagen** skrives på sin egen linje efter kæden og kobles til en årsagskategori (afsnit 4) og mindst én forbedring (afsnit 6).
- **Kontrol af kæden:** læs den baglæns med "derfor". Hænger kæden ikke logisk sammen fra grundårsag til problem, er den ikke færdig.
- Hooken kræver mindst fem nummererede "Hvorfor"-linjer og en linje med "Grundårsag", før en ny runde må starte.

**Forløb:**
1. RCA med 5 Why.
2. Forbedringen implementeres i fagagenten.
3. Linjen `Forbedring implementeret: ja` skrives i RCA'en.
4. Ny runde under **samme leverance-ID** med højst 3 nye forsøg.

RCA'en skrives kun, når brugeren har bedt om en ny runde (`New round <leverance-id>`). Der er højst 2 runder. Hooken håndhæver det.

```
# RCA – <leverance-id> – <fag> – runde <n> – <dato>

## 1. Hændelse
- Opgave: <kort>
- Forsøg og domme i runden: 1 <afvist, fund F…> · 2 <…> · 3 <…> (stier til dommene)
- Fund pr. forsøg: åbnet / lukket / nye / bestridt / regressioner

## 2. Hvad forsøg 1 manglede
For hvert blokerende fund i runden, også dem der først blev rejst i forsøg 2–3: var fejlen eller manglen
allerede til stede i forsøg 1?
| Fund | Til stede i forsøg 1? | Hvad skulle fagagenten have vidst eller gjort for at ramme rigtigt første gang? |
|---|---|---|

## 3. 5 Why: hvorfor ramte fagagenten ikke rigtigt første gang?
### Kæde A – <fund eller fundgruppe, fx F1, F3>
1. Hvorfor <problem: hvad forsøg 1 manglede>? → <svar> (evidens: <kilde>)
2. Hvorfor <svar 1>? → <svar> (evidens: …)
3. Hvorfor <svar 2>? → <svar> (evidens: …)
4. Hvorfor <svar 3>? → <svar> (evidens: …)
5. Hvorfor <svar 4>? → <svar> (evidens: …)
**Grundårsag A:** <handlingsbar årsag i fagagentens viden, metode, prompt eller input> → kategori <F…> → forbedring #<n>
Kontrol baglæns: <grundårsag> → derfor <svar 4> → … → derfor <problem>.

### Kæde B – <nødvendig ved fund med en anden årsag>
…

## 4. Årsagskategori (én primær, eventuelt sekundære)
- [ ] F1 Fagviden: videnbasen mangler, er forældet eller forkert (fx gammel normudgave)
- [ ] F2 Metode: agentens arbejdsgang mangler et trin (fx samlet fejltilstandsgennemgang, funktionstjek af en sikkerhedskæde eller efterregning)
- [ ] F3 Prompt og rolle: agentens instruktion er uklar eller leder i en forkert retning
- [ ] F4 Input: fagforespørgslen eller projektgrundlaget manglede noget, og agenten spurgte ikke eller markerede ikke antagelsen
- [ ] F5 Kildeadgang: normen ligger bag betalingsmur eller kilden er utilgængelig, og agenten markerede ikke usikkerheden
- [ ] K4 Kontrolkalibrering: rubric for streng eller uklar, fund uden kilde eller nye fund hver runde. Forbedringen gælder så kontrollen, men fagagenten skal stadig have læringen
- [ ] K7 Platform og værktøj: hook, værktøjsadgang eller baggrundskørsel

## 5. Konklusion (blameless)

## 6. Forbedring af fagagenten
Mindst én forbedring pr. grundårsag. Hver forbedring skal kunne efterprøves.
| # | Forbedring (generaliseret, uden sagsdata) | Hvor | Status |
|---|---|---|---|
| 1 | … | Agentens hukommelse: `~/.claude/agent-memory/<plugin>-<agent>/<fil>.md` (virker fra næste kald) | implementeret |
| 2 | … | Repoet: `plugins/<fag-plugin>/agents/<agent>.md` eller `skills/<trade>-knowledge/references/…` (commit `<hash>`, ny plugin-version) | implementeret |
| 3 | Eval-case, der reproducerer fejlen | `plugins/<fag-plugin>/evals/…` | implementeret / i forankringskøen |

Regler:
- **Hukommelsen** virker med det samme, fra næste runde. Filen skal ligge i agentens egen hukommelsesmappe og stå i dens `MEMORY.md`.
- **Repoet** giver varig effekt. Teksten skal være generaliseret og må ikke indeholde sag-id, adresse eller navne (`scripts/validate.py`). Commit, løft versionen og kør `claude plugin update`. En ny agentprompt virker først efter genstart, så hukommelsen bærer læringen i den igangværende runde.
- Ligger grundårsagen hos projektlederen (F4) eller kontrollen (K4), rettes den også dér: interviewet eller koordineringen i `byg`, eller rubric-versionen i `review-knowledge`.

**Forbedring implementeret:** ja

## 7. Ny runde
- Runde <n+1> starter med et nyt fagkald under samme leverance-ID. Prompten indeholder: "Runde <n+1> efter RCA: <sti>. Læs din opdaterede hukommelse. Løs opgaven forfra."
- Fagkaldet får den oprindelige opgave, RCA'ens afsnit 2 og 6 og fundene fra den seneste dom.
- Efter runde 3: eskalér til brugeren med status i én sætning, den beslutning brugeren skal træffe, og en anbefaling.
```
