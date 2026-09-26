# Root cause-analyse (RCA) – efter 3 afviste forsøg

Skrives af orkestratoren (projektlederen) til `<sagsmappe>/kvalitet/RCA-<leverance-id med / erstattet af __>.md`. Blameless: systemet fejlede, ikke "agenten".

```
# RCA – <leverance-id> – <fag> – <dato>

## 1. Hændelse
- Opgave: <kort>
- Forsøg og domme: 1 <afvist, fund F…> · 2 <…> · 3 <…> (stier til dommene)
- Fund pr. runde: åbnet / lukket / nye / bestridt

## 2. Tidslinje
<forsøg → ændringer → nye fund>

## 3. Fem gange hvorfor (for det mest vedvarende fund)
1. Hvorfor …? → …
2. …
5. Grundårsag: …

## 4. Årsagskategori (én primær, evt. sekundære)
- [ ] K1 Krav/input – uklart eller mangelfuldt projektgrundlag; spørgsmål til bruger ikke stillet
- [ ] K2 Fagviden – videnbase mangler, er forældet eller forkert (fx gammel normudgave)
- [ ] K3 Fagagentens metode – fund ignoreret, delvist rettet, regression
- [ ] K4 Kontrolkalibrering – rubric for streng eller uklar, fund uden kilde, nye fund hver runde
- [ ] K5 Kildeadgang – norm bag betalingsmur, kilde utilgængelig
- [ ] K6 Grænseflade – uafklaret snitflade mellem fag
- [ ] K7 Platform/værktøj – hook, værktøjsadgang, baggrundskørsel

## 5. Konklusion (blameless)

## 6. Læring tilbage (ejer · frist)
- K1 → nyt afklaringsspørgsmål i interviewet (byg/projektleder references/interview.md)
- K2 → rettelse i fagets videnbase (forslag i forankringskøen)
- K3 → præcisering i fagagentens prompt
- K4 → ny rubric-version i kontrol-viden/references/fag/<fag>.md
- K5 → markér emnet "kræver menneskelig verifikation / normadgang"
- K6 → nyt tværfagligt tjekpunkt i koordineringen
- Alle → ny eval-case, der reproducerer fejlen

## 7. Eskalering til brugeren
- Status i én sætning
- Beslutning brugeren skal træffe (fx acceptere risiko, skaffe oplysning, hente fagperson)
- Anbefaling
```
