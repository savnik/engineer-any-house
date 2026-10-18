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
- **Svaret må ikke kunne gættes.** Valgmulighederne blandes ved kørsel (stabilt pr. opgave-ID), så facits bogstav betyder ikke noget. Facit må ikke være systematisk den længste eller mest nuancerede mulighed. `tjek` advarer, når det gælder for mere end 40 % af valgopgaverne.
- **Viden skrives kun, hvor agenten fejler.** Det gælder udviklingssættet, og teksten skrives efter normal forankring: primærkilde, V/T og review. Opgaven må ikke skrives af.
- **Facit skal være efterprøvet** mod en primærkilde (retsinformation.dk, bygningsreglementet.dk, sik.dk osv.). `status` er `V <dato>` når facit er efterprøvet, ellers `T`. T-opgaver giver en advarsel og skal verificeres eller omformuleres.
- **Egne formuleringer.** Opgaverne er skrevet til dette repo. Der er ikke kopieret fra lærebøger eller officielle prøvesæt (de er fortrolige). Repoet offentliggøres.
- **Ét skriver pr. fil.** Opgaverne kan ligge i flere `opgaver*.json`, som valideres samlet.

## Filer
```
eksamen/<fag>/
  laeringsmaal.json   kilder og læringsmål (ordret med kilde), rolle i/uden
  opgaver*.json       {"opgaver": [...]}
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
| `type` | `valg` (ét rigtigt svar), `tal` (beregning) eller `fri` (fagligt skøn, bedømt af censor-LLM) |
| `niveau` | `svend` eller `mester` |
| `spoergsmaal` | Selvstændig opgavetekst med alle nødvendige data |
| `valgmuligheder` | `valg`: `{"A": "...", "B": "...", "C": "...", "D": "..."}` |
| `facit` | `valg`: bogstav · `tal`: `{"vaerdi": 10.2, "enhed": "A", "tolerance_pct": 3}` · `fri`: `null` |
| `kriterier` | `fri`: liste af krav, der alle skal være opfyldt for bestået. Kriterierne kræver fagligt indhold. En henvisning i parentes er censorens kilde og skal ikke citeres. Skal svaret nævne en bestemt regel, så skriv det udtrykkeligt ("henviser til …") og kun der, hvor henvisningen er det, der testes |
| `fail_hvis` | `fri` (valgfri): forhold, der giver ikke bestået |
| `begrundelse` | Kort forklaring af facit |
| `kilde` | Primærkilde med sted og URL |
| `status` | `V 2026-10-17` (efterprøvet) eller `T` |

## Kørsel
```
python3 scripts/exam.py tjek                       # format og dækning (kører også i valider.py)
python3 scripts/exam.py vis el --facit > /tmp/el.md
python3 scripts/exam.py koer el --arm begge --saet udvikling --parallel 4
python3 scripts/exam.py koer el --saet holdout     # kun ved udgivelse eller større ændringer
python3 scripts/exam.py rapport eksamen/el/results/<fil>.json
python3 scripts/exam.py rebedoem eksamen/el/results/<fil>.json --kun-fri   # ret gemte svar igen efter ændret rettemaske
```
`koer` kører hver opgave headless (`claude -p`) i en tom mappe uden brugerens plugins og uden internet. `basis` er modellen alene. `plugin` er fagagenten (`--agent`) med en kopi af pluginet uden afhængigheder. Valg- og talopgaver rettes deterministisk ud fra linjen `SVAR:`. Fri opgaver bedømmes af en censor-LLM efter kriterierne. Kørslen koster tokens.

Plugin-armen får læseadgang til sin plugin-kopi (`--add-dir`), men ikke til resten af filsystemet, så facit i `eksamen/` kan ikke læses. `--plugin-rev <commit>` kører pluginet, som det var i en git-revision. Det bruges til at måle en ændring af videnbasen før og efter under samme vilkår.

Plugin-armen kører som standard **uden** fagagentens lokale hukommelse (`memory: user` fjernes i kopien). Eksamen måler altså pluginet alene: det, der er forankret i repoet, og ikke erfaringer fra brugerens egne sager i `~/.claude/agent-memory/`. `--med-hukommelse` måler plugin og lokal hukommelse samlet, fx for at se, hvad hukommelsen bidrager med, før den forankres. Agenten har under eksamen kun læseværktøjer, så den kan ikke skrive i hukommelsen.
