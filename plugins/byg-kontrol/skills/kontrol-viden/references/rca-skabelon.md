# Root cause-analyse (RCA) – efter 3 afviste forsøg i en runde

Skrives af orkestratoren (projektlederen) til `<sagsmappe>/kvalitet/RCA-<leverance-id med / erstattet af __>.md`. Fra runde 2 lægges `__runde-<n>` til filnavnet.

**Formål:** Find ud af, **hvorfor fagagenten ikke kunne levere korrekt i første forsøg**, og gør fagagenten bedre, så det samme ikke sker igen. Analysen er blameless: fejlen ligger i systemet (agentens viden, metode, prompt og input), ikke i "agenten". Der ledes efter det, der skal ændres i fagagenten, ikke efter en skyldig.

**Forløb:**
1. RCA.
2. Forbedringen implementeres i fagagenten.
3. Linjen `Forbedring implementeret: ja` skrives i RCA'en.
4. Ny runde under **samme leverance-ID** med højst 3 nye forsøg.

Der er højst 3 runder. Efter 3. runde eskaleres der til brugeren. Hooken håndhæver det.

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

## 3. Fem gange hvorfor: hvorfor ramte fagagenten ikke rigtigt første gang?
1. Hvorfor indeholdt forsøg 1 <mangel>? → …
2. …
5. Grundårsag (i fagagenten eller dens input): …

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
| 2 | … | Repoet: `plugins/<fag-plugin>/agents/<agent>.md` eller `skills/<fag>-viden/references/…` (commit `<hash>`, ny plugin-version) | implementeret |
| 3 | Eval-case, der reproducerer fejlen | `plugins/<fag-plugin>/evals/…` | implementeret / i forankringskøen |

Regler:
- **Hukommelsen** virker med det samme, fra næste runde. Filen skal ligge i agentens egen hukommelsesmappe og stå i dens `MEMORY.md`.
- **Repoet** giver varig effekt. Teksten skal være generaliseret og må ikke indeholde sag-id, adresse eller navne (`scripts/valider.py`). Commit, løft versionen og kør `claude plugin update`. En ny agentprompt virker først efter genstart, så hukommelsen bærer læringen i den igangværende runde.
- Ligger grundårsagen hos projektlederen (F4) eller kontrollen (K4), rettes den også dér: interviewet eller koordineringen i `byg`, eller rubric-versionen i `kontrol-viden`.

**Forbedring implementeret:** ja

## 7. Ny runde
- Runde <n+1> starter med et nyt fagkald under samme leverance-ID. Prompten indeholder: "Runde <n+1> efter RCA: <sti>. Læs din opdaterede hukommelse. Løs opgaven forfra."
- Fagkaldet får den oprindelige opgave, RCA'ens afsnit 2 og 6 og fundene fra den seneste dom.
- Efter runde 3: eskalér til brugeren med status i én sætning, den beslutning brugeren skal træffe, og en anbefaling.
```
